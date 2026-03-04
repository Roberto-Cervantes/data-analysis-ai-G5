from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.analysis import (
    chart_ready_frame,
    clustering_analysis,
    correlation_analysis,
    distribution_for_column,
    outlier_analysis,
    summarize_dataset,
)
from services.data_utils import (
    TYPE_OPTIONS,
    DatasetRecord,
    apply_schema_to_dataset,
    build_joined_view,
    load_uploaded_file,
    validate_relationship,
)
from services.reporting import generate_html_report


st.set_page_config(page_title="Data Analysis AI", layout="wide")


def init_state() -> None:
    defaults: dict[str, Any] = {
        "datasets": {},
        "relationships": [],
        "model_confirmed": False,
        "logs": [],
        "joined_view": None,
        "analysis_cache": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_log(message: str) -> None:
    st.session_state.logs.append(message)


def render_sidebar() -> str:
    st.sidebar.title("Data Analysis AI")
    selected = st.sidebar.radio(
        "Modules",
        ["EDA", "Correlation", "Outliers", "Clustering", "Relationship Explorer", "Export Report"],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Use the tabs to load data, confirm schema, model relationships and analyze.")
    return selected


def render_data_sources() -> None:
    st.header("A. Data Sources")
    uploaded_files = st.file_uploader(
        "Upload CSV or Excel files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name in st.session_state.datasets:
                continue
            try:
                record = load_uploaded_file(uploaded_file)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not load {uploaded_file.name}: {exc}")
                continue
            st.session_state.datasets[record.name] = record
            add_log(f"Loaded dataset {record.name} ({record.rows} rows, {record.columns} columns).")

    if not st.session_state.datasets:
        st.info("Upload at least one file to start.")
        return

    overview = pd.DataFrame(
        [
            {
                "dataset": name,
                "size_bytes": record.size_bytes,
                "rows": record.rows,
                "columns": record.columns,
                "loaded_at": record.loaded_at,
            }
            for name, record in st.session_state.datasets.items()
        ]
    )
    st.dataframe(overview, use_container_width=True)

    for name, record in list(st.session_state.datasets.items()):
        with st.expander(f"Preview: {name}"):
            st.dataframe(record.dataframe.head(10), use_container_width=True)
            if st.button(f"Remove {name}", key=f"remove_{name}"):
                del st.session_state.datasets[name]
                st.session_state.relationships = [
                    rel
                    for rel in st.session_state.relationships
                    if rel["left_table"] != name and rel["right_table"] != name
                ]
                st.session_state.joined_view = None
                st.session_state.model_confirmed = False
                add_log(f"Removed dataset {name}.")
                st.rerun()


def render_schema() -> None:
    st.header("B. Schema")
    if not st.session_state.datasets:
        st.info("Load data first.")
        return

    dataset_name = st.selectbox("Select dataset", list(st.session_state.datasets.keys()), key="schema_dataset")
    record: DatasetRecord = st.session_state.datasets[dataset_name]

    with st.form(f"schema_form_{dataset_name}"):
        st.subheader("Data Dictionary")
        confirmed_types: dict[str, str] = {}
        for column, meta in record.schema.items():
            cols = st.columns([2, 1, 1, 1, 2])
            cols[0].markdown(f"**{column}**")
            cols[1].write(meta["detected_type"])
            confirmed_types[column] = cols[2].selectbox(
                f"Type for {column}",
                TYPE_OPTIONS,
                index=TYPE_OPTIONS.index(str(meta["confirmed_type"])),
                key=f"{dataset_name}_{column}_type",
                label_visibility="collapsed",
            )
            cols[3].write(f"{meta['null_pct']}%")
            cols[4].write(meta["example"] or "-")
        submitted = st.form_submit_button("Confirm schema and convert")

    if submitted:
        converted_df, updated_schema, warnings = apply_schema_to_dataset(record, confirmed_types)
        record.dataframe = converted_df
        record.schema = updated_schema
        record.warnings = warnings
        st.session_state.datasets[dataset_name] = record
        add_log(f"Schema confirmed for {dataset_name}.")
        if warnings:
            st.warning("Some conversions produced warnings.")
            for warning in warnings:
                st.write(f"- {warning}")
        else:
            st.success("Schema applied without warnings.")

    if record.warnings:
        st.subheader("Warnings")
        for warning in record.warnings:
            st.write(f"- {warning}")


def render_model() -> None:
    st.header("C. Model")
    if len(st.session_state.datasets) < 2:
        st.info("Load at least two datasets to define relationships.")
        return

    dataset_names = list(st.session_state.datasets.keys())
    with st.form("relationship_form"):
        left_table = st.selectbox("Left table", dataset_names)
        right_table = st.selectbox("Right table", [name for name in dataset_names if name != left_table])
        left_column = st.selectbox("Left key", list(st.session_state.datasets[left_table].dataframe.columns))
        right_column = st.selectbox("Right key", list(st.session_state.datasets[right_table].dataframe.columns))
        relationship_type = st.selectbox("Relationship type", ["1-1", "1-N", "N-1"])
        submitted = st.form_submit_button("Add relationship")

    if submitted:
        warnings = validate_relationship(
            st.session_state.datasets,
            left_table,
            left_column,
            right_table,
            right_column,
            relationship_type,
        )
        st.session_state.relationships.append(
            {
                "left_table": left_table,
                "left_column": left_column,
                "right_table": right_table,
                "right_column": right_column,
                "relationship_type": relationship_type,
                "warnings": warnings,
            }
        )
        st.session_state.model_confirmed = False
        add_log(f"Created relationship {left_table}.{left_column} {relationship_type} {right_table}.{right_column}.")
        if warnings:
            st.warning("Relationship saved with validation warnings.")
            for warning in warnings:
                st.write(f"- {warning}")
        else:
            st.success("Relationship validated and saved.")

    if not st.session_state.relationships:
        return

    st.subheader("Relationships")
    st.dataframe(pd.DataFrame(st.session_state.relationships), use_container_width=True)
    render_relationship_graph(dataset_names)

    remove_index = st.selectbox(
        "Delete relationship",
        options=list(range(len(st.session_state.relationships))),
        format_func=lambda idx: (
            f"{st.session_state.relationships[idx]['left_table']}.{st.session_state.relationships[idx]['left_column']} -> "
            f"{st.session_state.relationships[idx]['right_table']}.{st.session_state.relationships[idx]['right_column']}"
        ),
    )
    if st.button("Delete selected relationship"):
        removed = st.session_state.relationships.pop(remove_index)
        st.session_state.joined_view = None
        st.session_state.model_confirmed = False
        add_log(
            f"Deleted relationship {removed['left_table']}.{removed['left_column']} -> "
            f"{removed['right_table']}.{removed['right_column']}."
        )
        st.rerun()

    if st.button("Confirm model"):
        st.session_state.joined_view = build_joined_view(st.session_state.datasets, st.session_state.relationships)
        st.session_state.model_confirmed = True
        add_log("Model confirmed for multi-table analysis.")
        st.success("Model confirmed.")


def render_relationship_graph(dataset_names: list[str]) -> None:
    positions = {name: index for index, name in enumerate(dataset_names)}
    fig = go.Figure()
    for relation in st.session_state.relationships:
        fig.add_trace(
            go.Scatter(
                x=[positions[relation["left_table"]], positions[relation["right_table"]]],
                y=[1, 1],
                mode="lines",
                line={"width": 2, "color": "#64748b"},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=[positions[name] for name in dataset_names],
            y=[1 for _ in dataset_names],
            mode="markers+text",
            text=dataset_names,
            textposition="top center",
            marker={"size": 26, "color": "#2563eb"},
            showlegend=False,
        )
    )
    fig.update_layout(height=260, xaxis={"visible": False}, yaxis={"visible": False}, margin={"l": 8, "r": 8, "t": 8, "b": 8})
    st.plotly_chart(fig, use_container_width=True)


def get_available_views() -> dict[str, pd.DataFrame]:
    views = {name: record.dataframe for name, record in st.session_state.datasets.items()}
    if st.session_state.model_confirmed and st.session_state.joined_view:
        view_name, dataframe = st.session_state.joined_view
        views[f"[Model] {view_name}"] = dataframe
    return views


def render_dashboard(selected_module: str) -> None:
    st.header("D. Report")
    views = get_available_views()
    if not views:
        st.info("Load and prepare a dataset first.")
        return

    dataset_name = st.selectbox("Dataset / view", list(views.keys()), key="dashboard_dataset")
    dataframe = views[dataset_name]
    numeric_columns = list(dataframe.select_dtypes(include=["number"]).columns)

    if st.button("Run analysis"):
        st.session_state.analysis_cache[dataset_name] = summarize_dataset(dataframe)
        add_log(f"Executed EDA for {dataset_name}.")

    eda_results = st.session_state.analysis_cache.get(dataset_name)
    if not eda_results:
        eda_results = summarize_dataset(dataframe)
        st.session_state.analysis_cache[dataset_name] = eda_results

    left, right = st.columns([2, 1])
    with right:
        st.subheader("Insights")
        for item in eda_results["insights"]:
            st.write(f"- {item}")

    with left:
        if selected_module == "EDA":
            render_eda_section(dataframe, eda_results)
        elif selected_module == "Correlation":
            render_correlation_section(dataframe)
        elif selected_module == "Outliers":
            render_outlier_section(dataframe, numeric_columns)
        elif selected_module == "Clustering":
            render_clustering_section(dataframe)
        elif selected_module == "Relationship Explorer":
            render_relationship_section(dataframe, numeric_columns)
        else:
            render_export_section(dataset_name, dataframe, eda_results)


def render_eda_section(dataframe: pd.DataFrame, eda_results: dict[str, Any]) -> None:
    st.subheader("EDA")
    metrics = st.columns(4)
    metrics[0].metric("Rows", dataframe.shape[0])
    metrics[1].metric("Columns", dataframe.shape[1])
    metrics[2].metric("Numeric", dataframe.select_dtypes(include=["number"]).shape[1])
    metrics[3].metric("Missing cells", int(dataframe.isna().sum().sum()))
    st.markdown("**Missing values**")
    st.dataframe(eda_results["missing_summary"], use_container_width=True)
    if not eda_results["numeric_summary"].empty:
        st.markdown("**Numeric summary**")
        st.dataframe(eda_results["numeric_summary"], use_container_width=True)

    selected_column = st.selectbox("Distribution column", list(dataframe.columns), key="eda_distribution_column")
    dist_df = distribution_for_column(dataframe, selected_column)
    fig = px.bar(dist_df, x=dist_df.columns[0], y=dist_df.columns[1], title=f"Distribution of {selected_column}")
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_section(dataframe: pd.DataFrame) -> None:
    st.subheader("Correlation")
    method = st.radio("Method", ["pearson", "spearman"], horizontal=True)
    corr = correlation_analysis(dataframe, method=method)
    if corr.empty:
        st.info("At least two numeric columns are required.")
        return
    st.plotly_chart(
        px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1),
        use_container_width=True,
    )
    st.dataframe(corr, use_container_width=True)


def render_outlier_section(dataframe: pd.DataFrame, numeric_columns: list[str]) -> None:
    st.subheader("Outliers")
    if not numeric_columns:
        st.info("No numeric columns available.")
        return
    results, _ = outlier_analysis(dataframe)
    if results.empty:
        st.info("No outlier computation available.")
        return
    st.dataframe(results, use_container_width=True)
    column = st.selectbox("Boxplot column", numeric_columns, key="outlier_column")
    st.plotly_chart(
        px.box(dataframe, y=column, points="outliers", title=f"Outlier analysis for {column}"),
        use_container_width=True,
    )


def render_clustering_section(dataframe: pd.DataFrame) -> None:
    st.subheader("Clustering")
    algorithm = st.selectbox("Algorithm", ["kmeans", "dbscan"], key="cluster_algorithm")
    if algorithm == "kmeans":
        clustered, details = clustering_analysis(
            dataframe,
            algorithm=algorithm,
            n_clusters=st.slider("Clusters", min_value=2, max_value=8, value=3),
        )
    else:
        clustered, details = clustering_analysis(
            dataframe,
            algorithm=algorithm,
            eps=st.slider("EPS", min_value=0.1, max_value=3.0, value=0.5, step=0.1),
            min_samples=st.slider("Min samples", min_value=2, max_value=20, value=5),
        )

    if "error" in details:
        st.warning(details["error"])
        return

    st.write("Cluster sizes")
    st.json(details["cluster_counts"])
    st.dataframe(clustered.head(50), use_container_width=True)
    features = details["feature_columns"]
    st.plotly_chart(
        px.scatter(
            clustered,
            x=features[0],
            y=features[1],
            color=clustered["cluster"].astype(str),
            title=f"Clusters using {algorithm.upper()}",
        ),
        use_container_width=True,
    )


def render_relationship_section(dataframe: pd.DataFrame, numeric_columns: list[str]) -> None:
    st.subheader("Visualization Builder")
    columns = list(dataframe.columns)
    chart_type = st.selectbox("Chart type", ["bar", "line", "scatter", "histogram", "box"], key="chart_type")
    x_col = st.selectbox("X axis", columns, key="chart_x")
    y_col = None
    if chart_type != "histogram":
        y_options = columns if chart_type in {"bar", "line", "scatter"} else numeric_columns
        if not y_options:
            st.info("This chart needs numeric columns for Y.")
            return
        y_col = st.selectbox("Y axis", y_options, key="chart_y")

    frame = chart_ready_frame(dataframe, x_col, y_col)
    if frame.empty:
        st.info("The selected fields do not have enough complete values.")
        return

    if chart_type == "bar":
        fig = px.bar(frame, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
    elif chart_type == "line":
        fig = px.line(frame, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
    elif chart_type == "scatter":
        fig = px.scatter(frame, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
    elif chart_type == "histogram":
        fig = px.histogram(frame, x=x_col, title=f"Histogram of {x_col}")
    else:
        fig = px.box(frame, x=x_col, y=y_col, title=f"Boxplot of {y_col} by {x_col}")
    st.plotly_chart(fig, use_container_width=True)


def render_export_section(dataset_name: str, dataframe: pd.DataFrame, eda_results: dict[str, Any]) -> None:
    st.subheader("Export Report")
    base_name = dataset_name.replace("[Model] ", "")
    if base_name in st.session_state.datasets:
        schema = st.session_state.datasets[base_name].schema
    else:
        schema = {
            column: {
                "detected_type": str(dataframe[column].dtype),
                "confirmed_type": str(dataframe[column].dtype),
                "null_pct": round(float(dataframe[column].isna().mean() * 100), 2),
                "example": "" if dataframe[column].dropna().empty else str(dataframe[column].dropna().iloc[0]),
            }
            for column in dataframe.columns
        }
    report_html = generate_html_report(dataset_name, dataframe, schema, eda_results, st.session_state.relationships)
    st.download_button(
        "Download HTML report",
        data=report_html,
        file_name=f"{base_name.replace('.', '_')}_report.html",
        mime="text/html",
    )
    st.code(report_html[:1500], language="html")


def render_logs() -> None:
    with st.expander("Logs and warnings"):
        if not st.session_state.logs:
            st.write("No logs yet.")
            return
        for entry in st.session_state.logs[-20:]:
            st.write(f"- {entry}")


def main() -> None:
    init_state()
    selected_module = render_sidebar()
    st.title("Sistema Inteligente de Analisis Automatizado y Exploratorio de Datos")
    tabs = st.tabs(["Data Sources", "Schema", "Model", "Dashboard"])
    with tabs[0]:
        render_data_sources()
    with tabs[1]:
        render_schema()
    with tabs[2]:
        render_model()
    with tabs[3]:
        render_dashboard(selected_module)
    render_logs()


if __name__ == "__main__":
    main()
