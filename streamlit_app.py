from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import io

import altair as alt
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Observatorio Gapminder | Medalit", layout="wide")
ROOT = Path(__file__).resolve().parent
REQUIRED = {'country', 'continent', 'year', 'lifeExp', 'pop', 'gdpPercap', 'iso_alpha'}


def validate(raw):
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError('Faltan columnas: ' + ', '.join(sorted(missing)))
    df = raw.copy()
    if df.empty:
        raise ValueError('El archivo no contiene filas.')
    for c in ['year', 'lifeExp', 'pop', 'gdpPercap']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        if df[c].isna().any() or not np.isfinite(df[c]).all():
            raise ValueError(f'La columna {c} debe contener números finitos sin vacíos.')
    if (df['year'] % 1 != 0).any() or not df['year'].between(1800, 2200).all():
        raise ValueError('year debe contener años enteros entre 1800 y 2200.')
    if (df[['lifeExp', 'pop', 'gdpPercap']] <= 0).any().any():
        raise ValueError('lifeExp, pop y gdpPercap deben ser mayores que cero.')
    for c in ['country', 'continent', 'iso_alpha']:
        if df[c].isna().any() or df[c].astype(str).str.strip().eq('').any():
            raise ValueError(f'La columna {c} contiene etiquetas vacías.')
        df[c] = df[c].astype(str).str.strip()
    if df.duplicated(['country', 'year']).any():
        raise ValueError('Hay filas repetidas para el mismo país y año.')
    df['year'] = df['year'].astype(int)
    df['date'] = pd.to_datetime(df['year'].astype(str) + '-01-01')
    return df.sort_values(['year', 'country']).reset_index(drop=True)


@st.cache_data
def load_base():
    return validate(pd.read_csv(ROOT / 'gapminder.csv'))


@st.cache_data
def load_csv(content):
    return validate(pd.read_csv(io.BytesIO(content)))


def apply_filters(df, f):
    mask = df['date'].dt.date.between(*f['periodo']) & (df['pop'] >= f['poblacion_min'])
    if f['continente'] != 'Todos':
        mask &= df['continent'].eq(f['continente'])
    if f['paises']:
        mask &= df['country'].isin(f['paises'])
    return df.loc[mask].copy()


def dashboard():
    st.title('Observatorio Gapminder')
    st.write('Compara países y continentes para explorar cómo cambian la esperanza de vida y el ingreso entre 1952 y 2007.')
    st.caption('Laboratorio Streamlit · Medalit Nieves Salcedo Rodriguez · Visualización de Datos')
    now = datetime.now(ZoneInfo('America/Lima'))
    st.info('Fecha y hora de ejecución: ' + now.strftime('%d/%m/%Y %H:%M:%S') + ' · America/Lima (UTC−05:00)')
    uploaded = st.sidebar.file_uploader('Cargar CSV alternativo', type=['csv'])
    try:
        content = uploaded.getvalue() if uploaded is not None else None
        df = load_csv(content) if content is not None else load_base()
    except Exception as e:
        st.error('No se pudo utilizar el CSV. ' + str(e))
        st.stop()
    source = hashlib.sha256(content).hexdigest() if content is not None else 'base'
    min_date, max_date = df['date'].min().date(), df['date'].max().date()
    defaults = {'continente': 'Todos', 'paises': [], 'periodo': (min_date, max_date), 'poblacion_min': 0}
    if st.session_state.get('source') != source:
        st.session_state.source = source
        st.session_state.filtros = defaults.copy()
        st.session_state['continente'] = 'Todos'
        st.session_state['paises'] = []
        st.session_state['periodo'] = (min_date, max_date)
        st.session_state['poblacion_min'] = 0
    def reset():
        st.session_state.filtros = defaults.copy()
        st.session_state.continente = 'Todos'
        st.session_state.paises = []
        st.session_state.periodo = (min_date, max_date)
        st.session_state.poblacion_min = 0
    st.sidebar.header('Filtros')
    st.sidebar.caption('Ajusta las opciones y pulsa Aplicar filtros. Para recuperar todos los datos, usa Restablecer.')
    with st.sidebar.form('form_filtros'):
        continent = st.selectbox('Continente', ['Todos'] + sorted(df['continent'].unique()), key='continente')
        countries = st.multiselect('Países (opcional)', sorted(df['country'].unique()), key='paises')
        period = st.date_input('Periodo', min_value=min_date, max_value=max_date, key='periodo')
        minimum = st.slider('Población mínima (millones)', 0, max(1, int(np.ceil(df['pop'].max() / 1e6))), key='poblacion_min')
        submit = st.form_submit_button('Aplicar filtros', type='primary')
    st.sidebar.button('Restablecer filtros', on_click=reset)
    if submit:
        if len(period) != 2 or period[0] > period[1]:
            st.error('Selecciona las fechas de inicio y fin. Se conserva el último filtro válido.')
        else:
            st.session_state.filtros = {'continente': continent, 'paises': countries, 'periodo': tuple(period), 'poblacion_min': minimum * 1e6}
    f = st.session_state.filtros
    filtered = apply_filters(df, f)
    st.caption(f"Fuente: {'CSV alternativo' if uploaded is not None else 'CSV de la sesión 8'} · Filtro aplicado: {f['continente']} · {f['periodo'][0]} a {f['periodo'][1]} · Población mínima: {f['poblacion_min']/1e6:g} millones")
    if filtered.empty:
        st.warning('No hay datos para esta combinación de filtros. Cambia las opciones o pulsa Restablecer filtros.')
        st.stop()
    last, first = int(filtered.year.max()), int(filtered.year.min())
    actual, initial = filtered[filtered.year.eq(last)], filtered[filtered.year.eq(first)]
    with st.container():
        st.subheader('Resumen de la selección')
        st.caption(f'Indicadores del último año disponible: {last}. Medias simples entre países; no ponderadas por población.')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Países', actual.country.nunique())
        c2.metric('Esperanza de vida', f'{actual.lifeExp.mean():.1f} años', f'{actual.lifeExp.mean()-initial.lifeExp.mean():+.1f} años vs. {first}')
        c3.metric('Población', f'{actual["pop"].sum()/1e9:.2f} mil millones')
        c4.metric('PIB per cápita medio', f'USD {actual.gdpPercap.mean():,.0f}')
    with st.expander('Ver definición de los KPI'):
        st.write('Países: número de países del último año. Esperanza de vida y PIB per cápita: media aritmética de países, sin ponderar. Población: suma en ese año. El delta compara las medias del último y primer año del filtro; si cambia la cobertura, también puede cambiar la composición de países.')
    relation, trend, table = st.tabs(['Relación', 'Tendencia', 'Datos'])
    with relation:
        fig = px.scatter(actual, x='gdpPercap', y='lifeExp', size='pop', color='continent', hover_name='country', log_x=True,
                         labels={'gdpPercap': 'PIB per cápita (USD, PPA)', 'lifeExp': 'Esperanza de vida (años)', 'continent': 'Continente', 'pop': 'Población'},
                         title=f'Ingreso y esperanza de vida por país · {last}')
        fig.update_layout(height=440, margin=dict(t=65, b=30))
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Cada burbuja es un país; su tamaño representa población. El eje del ingreso es logarítmico. La asociación observada no demuestra causalidad.')
    with trend:
        top = actual.nlargest(8, 'pop').country.tolist()
        line = filtered if f['paises'] else filtered[filtered.country.isin(top)]
        st.caption('Países seleccionados' if f['paises'] else 'Ocho países con mayor población en el último año del filtro.')
        chart = alt.Chart(line).mark_line(point=True).encode(
            x=alt.X('year:O', title='Año'), y=alt.Y('lifeExp:Q', title='Esperanza de vida (años)', scale=alt.Scale(zero=False)),
            color=alt.Color('country:N', title='País'), tooltip=['country:N', 'year:O', alt.Tooltip('lifeExp:Q', format='.1f')]
        ).properties(height=400, title='Evolución de la esperanza de vida')
        st.altair_chart(chart, use_container_width=True)
    with table:
        st.caption(f'{len(filtered):,} registros país-año después de aplicar los filtros.')
        st.dataframe(filtered.drop(columns='date'), hide_index=True, use_container_width=True)
        st.download_button('Descargar selección CSV', filtered.drop(columns='date').to_csv(index=False).encode('utf-8'), 'gapminder_filtrado.csv', 'text/csv')


def methodology():
    st.title('Metodología y comprobaciones')
    st.write('Fuente: CSV Gapminder proporcionado en la sesión 8 de Visualización de Datos. Copia local del aula, sin servicios externos ni credenciales.')
    st.write('Unidad: país-año. El conjunto base incluye 142 países, 12 años y 1.704 registros entre 1952 y 2007. Los valores históricos no describen la situación actual.')
    with st.expander('Esquema y validación de CSV'):
        st.write('Columnas: country, continent, year, lifeExp, pop, gdpPercap, iso_alpha. Se rechazan columnas faltantes, números no finitos, valores no positivos, etiquetas vacías y duplicados país-año. Al cambiar de fuente se reinician los filtros para evitar selecciones incompatibles.')
    st.subheader('Estado, rendimiento y estructura')
    st.write('cache_data conserva la lectura validada; session_state conserva los filtros aplicados; form retrasa el cambio hasta pulsar Aplicar filtros. st.Page y st.navigation separan Dashboard de Metodología. Los tres tabs comparten el mismo conjunto filtrado.')
    st.subheader('Usabilidad')
    st.write('Mejora incorporada durante la revisión técnica: botón Restablecer filtros y resumen visible de los filtros aplicados. Evitan quedar atrapado en una selección vacía y distinguen los cambios preparados de los ya aplicados.')
    st.warning('Prueba cruzada con otro equipo: pendiente. Las verificaciones técnicas no sustituyen la observación de una persona externa; no se inventan participantes ni comentarios.')
    st.write('Limitaciones: promedios simples por país; cobertura limitada al conjunto Gapminder y a las fechas presentes. El PIB per cápita está expresado en dólares internacionales ajustados por poder adquisitivo. No se estima causalidad.')
    st.caption('Implementación del laboratorio guiado con asistencia de Codex. Estudiante: Medalit Nieves Salcedo Rodriguez.')


if __name__ == '__main__':
    page = st.navigation([st.Page(dashboard, title='Dashboard', default=True), st.Page(methodology, title='Metodología')])
    page.run()
