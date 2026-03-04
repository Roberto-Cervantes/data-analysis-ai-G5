# Data Analysis AI

MVP en Python y Streamlit para carga de multiples archivos tabulares, confirmacion de tipos, modelado de relaciones, EDA automatizado, visualizaciones y reporte HTML.

## Stack

- Python
- Streamlit
- Pandas
- Plotly
- Scikit-learn

## Ejecucion

1. Cree y active un entorno virtual.
2. Instale dependencias con `pip install -r requirements.txt`.
3. Ejecute `streamlit run app.py`.

## Flujo implementado

- `Data Sources`: carga de archivos CSV/XLS/XLSX, listado, preview y eliminacion.
- `Schema`: autodeteccion de tipos, confirmacion manual y conversion con advertencias.
- `Model`: creacion de relaciones entre tablas, validacion y vista simple del modelo.
- `Dashboard`: EDA, correlacion, outliers, clustering, constructor de graficos y exportacion HTML.

## Estructura

- `app.py`: interfaz Streamlit y flujo A->B->C->D.
- `services/data_utils.py`: carga, inferencia de tipos, conversiones y relaciones.
- `services/analysis.py`: EDA, correlacion, outliers, clustering y datos para graficos.
- `services/reporting.py`: generacion de reporte HTML.
