from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler


def summarize_dataset(dataframe: pd.DataFrame) -> dict[str, Any]:
    numeric_df = dataframe.select_dtypes(include=["number"])
    categorical_df = dataframe.select_dtypes(exclude=["number"])

    numeric_summary = (
        numeric_df.describe().transpose().reset_index().rename(columns={"index": "column"})
        if not numeric_df.empty
        else pd.DataFrame()
    )
    missing_summary = (
        dataframe.isna()
        .mean()
        .mul(100)
        .round(2)
        .reset_index()
        .rename(columns={"index": "column", 0: "missing_pct"})
        .sort_values("missing_pct", ascending=False)
    )

    categorical_summary = []
    for column in categorical_df.columns[:10]:
        top = dataframe[column].astype("string").fillna("<NA>").value_counts().head(5)
        categorical_summary.append({"column": column, "top_values": top.to_dict()})

    return {
        "numeric_summary": numeric_summary,
        "missing_summary": missing_summary,
        "categorical_summary": categorical_summary,
        "insights": generate_insights(dataframe, missing_summary),
    }


def generate_insights(dataframe: pd.DataFrame, missing_summary: pd.DataFrame) -> list[str]:
    if dataframe.empty:
        return ["The selected dataset is empty."]

    insights = [f"Dataset contains {dataframe.shape[0]} rows and {dataframe.shape[1]} columns."]
    high_missing = missing_summary[missing_summary["missing_pct"] > 20].head(3)
    for _, row in high_missing.iterrows():
        insights.append(f"Column {row['column']} has {row['missing_pct']}% missing values.")

    numeric_df = dataframe.select_dtypes(include=["number"])
    if not numeric_df.empty:
        variance = numeric_df.var(numeric_only=True).sort_values(ascending=False).head(2)
        for column, value in variance.items():
            insights.append(f"{column} shows high variability (variance {value:.2f}).")

    if len(insights) == 1:
        insights.append("No major data quality issues were detected in the basic scan.")
    return insights


def correlation_analysis(dataframe: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    numeric_df = dataframe.select_dtypes(include=["number"])
    if numeric_df.shape[1] < 2:
        return pd.DataFrame()
    return numeric_df.corr(method=method).round(3)


def outlier_analysis(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    numeric_df = dataframe.select_dtypes(include=["number"])
    rows = []
    masks: dict[str, pd.Series] = {}

    for column in numeric_df.columns:
        series = numeric_df[column].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (numeric_df[column] < lower) | (numeric_df[column] > upper)
        count = int(mask.sum())
        rows.append(
            {
                "column": column,
                "lower_bound": round(lower, 4),
                "upper_bound": round(upper, 4),
                "outlier_count": count,
                "outlier_pct": round((count / max(len(numeric_df), 1)) * 100, 2),
            }
        )
        masks[column] = mask

    if not rows:
        return pd.DataFrame(), masks
    return pd.DataFrame(rows).sort_values("outlier_pct", ascending=False), masks


def clustering_analysis(
    dataframe: pd.DataFrame, algorithm: str = "kmeans", n_clusters: int = 3, eps: float = 0.5, min_samples: int = 5
) -> tuple[pd.DataFrame, dict[str, Any]]:
    numeric_df = dataframe.select_dtypes(include=["number"]).dropna()
    if numeric_df.shape[0] < 3 or numeric_df.shape[1] < 2:
        return pd.DataFrame(), {"error": "At least 3 complete rows and 2 numeric columns are required."}

    scaled = StandardScaler().fit_transform(numeric_df)
    if algorithm == "dbscan":
        labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled)
    else:
        labels = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(scaled)

    clustered = numeric_df.copy()
    clustered["cluster"] = labels
    return clustered, {
        "cluster_counts": clustered["cluster"].value_counts().sort_index().to_dict(),
        "feature_columns": list(numeric_df.columns),
    }


def chart_ready_frame(dataframe: pd.DataFrame, x_col: str, y_col: str | None = None) -> pd.DataFrame:
    selected = [x_col]
    if y_col and y_col != x_col:
        selected.append(y_col)
    return dataframe[selected].dropna().copy()


def distribution_for_column(dataframe: pd.DataFrame, column: str, limit: int = 20) -> pd.DataFrame:
    series = dataframe[column]
    if pd.api.types.is_numeric_dtype(series):
        bins = min(limit, max(int(np.sqrt(len(series.dropna()))), 5))
        bucketed = pd.cut(series, bins=bins).astype("string").value_counts().sort_index()
        result = bucketed.reset_index()
        # Avoid duplicate column names by ensuring unique names
        result.columns = ["bucket", "count"]
        return result

    counts = series.astype("string").fillna("<NA>").value_counts().head(limit)
    result = counts.reset_index()
    # Avoid duplicate column names by ensuring unique names
    result.columns = ["value", "count"]
    return result
