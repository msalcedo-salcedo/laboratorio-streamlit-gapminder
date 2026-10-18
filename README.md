# Laboratorio Streamlit - Observatorio Gapminder

Medalit Nieves Salcedo Rodriguez · UPeU · Visualización de Datos · Sesión 8.

Implementa el laboratorio guiado del aula con su CSV Gapminder: filtros en formulario, estado aplicado, caché, carga validada de CSV, cuatro KPI, Plotly, Altair, tabla, descarga y navegación Dashboard/Metodología.

## Ejecución

Python 3.12 recomendado.

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

En Streamlit Community Cloud: rama main, entrada streamlit_app.py, Python 3.12. No requiere secretos.

La pantalla muestra la fecha/hora real del servidor convertida a America/Lima al ejecutar la vista; no es una fecha insertada en la captura.

Datos: archivo dataset Gapminder.csv proporcionado en la sesión 8 (142 países, 1952-2007). Los promedios son simples por país y no ponderados por población. No se afirma causalidad.

Mejora de usabilidad: Restablecer filtros y resumen de selección aplicada. La prueba cruzada con otro equipo queda pendiente; no se simula una evaluación humana. Implementación con asistencia de Codex.
