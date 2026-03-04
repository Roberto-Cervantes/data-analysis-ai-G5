Especificación Funcional (MVP) – Sistema Inteligente de Análisis Automatizado y Exploratorio de Datos
Basado en “Propuesta proyecto I-2026” (carga CSV/Excel, EDA + IA, visualizaciones y reporte).

1. Objetivo del software
Permitir al usuario cargar uno o varios archivos tabulares (CSV/Excel), confirmar/corregir el tipo de dato autodetectado por columna, definir relaciones entre tablas (estilo Power BI) y, luego, ejecutar análisis exploratorio automatizado (EDA) + técnicas de IA (clustering/outliers) con visualizaciones y reporte.
2. Alcance (pantallas y flujo)
Flujo acordado: Usuario → Interfaz Web → Procesamiento → Motor (EDA + IA) → Visualización/Reporte.
2.1 Pantalla A – Carga de archivos (Data Sources)
Funciones mínimas:
•	Botón para cargar múltiples archivos: .csv, .xlsx, .xls.
•	Listado de archivos cargados con: nombre, tamaño, número de filas/columnas, fecha/hora de carga.
•	Vista previa por archivo (primeras N filas) y opción de eliminar/reemplazar archivo.
2.2 Pantalla B – Confirmación de tipos de datos por columna (Schema)
Requisito clave: autodetección + corrección manual. Funciones:
•	Autodetección de tipo por columna: numérico, categórico, fecha/hora, booleano, texto.
•	Tabla ‘Diccionario de datos’ por archivo: Columna | Tipo detectado | Tipo confirmado | % nulos | Ejemplo.
•	El usuario puede cambiar el ‘Tipo confirmado’ (dropdown).
•	Al confirmar, el sistema aplica conversión (si posible) y registra advertencias (p.ej. valores inválidos).
2.3 Pantalla C – Modelado y relaciones (Model) estilo Power BI
Funciones mínimas:
•	Selector de tablas cargadas y creación de relaciones: TablaA.Columna ↔ TablaB.Columna.
•	Tipo de relación: 1-1, 1-N, N-1 (N-N opcional/MVP fuera).
•	Validación: cardinalidad (duplicados), nulos en claves, tipos compatibles.
•	Vista ‘modelo’ (diagrama simple) y lista de relaciones creadas (con opción de editar/borrar).
•	Botón ‘Confirmar modelo’ para habilitar análisis multi-tabla (joins) y dashboard.
2.4 Pantalla D – Dashboard principal (Report) estilo Power BI (simplificado)
Componentes mínimos:
•	Panel izquierdo (menú): EDA, Correlación, Outliers, Clustering, Relación entre variables, Exportar reporte.
•	Área central: ‘lienzo’ de visualizaciones (cards/gráficos) alimentadas por selección del usuario.
•	Selector de ‘dataset’ (tabla o vista) y campos (columnas) para construir gráficos.
•	Galería de gráficos: barras, líneas, dispersión, histograma, boxplot, heatmap correlación.
•	Sección de ‘insights’ en texto (automático) con hallazgos principales.
3. Requisitos funcionales mínimos (MVP)
ID	Requisito	Criterio de aceptación (mínimo)
RF-01	Carga de múltiples archivos CSV/Excel.	Permite subir >=2 archivos; muestra lista y preview por archivo.
RF-02	Autodetección de tipos por columna.	Clasifica columnas y muestra en diccionario de datos.
RF-03	Edición/confirmación de tipos.	Usuario puede cambiar tipo y el sistema intenta convertir; reporta errores.
RF-04	Definición de relaciones entre tablas.	Permite crear relaciones; valida tipos y duplicados; guarda modelo.
RF-05	EDA automático.	Genera descriptivos, nulos, distribución para variables relevantes.
RF-06	Correlación.	Matriz + heatmap para numéricas (Pearson o Spearman).
RF-07	Outliers.	Detecta outliers (IQR o Z-score) y reporta % + boxplots.
RF-08	Clustering.	Ejecuta K-Means o DBSCAN sobre numéricas (con escalado) y muestra clusters.
RF-09	Constructor de visualizaciones.	Usuario selecciona campos y tipo de gráfico; se renderiza en el lienzo.
RF-10	Exportación de reporte.	Genera HTML (mínimo) con hallazgos, gráficos y diccionario; descarga.

4. Requisitos no funcionales
•	Sin tiempo real; análisis bajo demanda (al presionar ‘Analizar’).
•	Sin base de datos obligatoria (persistencia opcional a archivos locales).
•	Tiempos razonables: datasets medianos (p.ej. hasta ~200k filas) deben procesar sin colgar la UI.
•	Trazabilidad: mostrar logs/advertencias de conversiones de tipos y validaciones de relaciones.
•	Código modular: UI separada de servicios de análisis (para cumplir ‘código limpio’).
5. Propuesta tecnológica (implementación sugerida)
Implementación sugerida para cumplir rápido y bien la rúbrica:
•	UI web: Streamlit (tabs, sidebar, file_uploader, session_state).
•	Procesamiento/EDA: pandas, numpy.
•	IA/ML: scikit-learn (StandardScaler, KMeans, DBSCAN, IsolationForest opcional).
•	Visualización: Plotly (recomendado) o Matplotlib.
•	Reporte: HTML (Jinja2 + export de gráficas a imágenes) y PDF opcional (WeasyPrint).
6. Datos y modelo interno (resumen)
Estructuras mínimas:
•	DatasetRegistry: lista de datasets cargados (nombre, df, metadatos).
•	SchemaMap por dataset: {columna: tipo_detectado, tipo_confirmado, warnings}.
•	RelationshipGraph: lista de relaciones (tablaA.colA, tablaB.colB, cardinalidad).
•	SemanticViews (opcional): vistas materializadas por joins según el modelo.
7. Entregables
•	Aplicación web funcionando con el flujo A→B→C→D.
•	Demo con al menos 2 archivos relacionados (caso tipo ‘clientes’ + ‘ventas’).
•	Reporte exportable (HTML mínimo).
