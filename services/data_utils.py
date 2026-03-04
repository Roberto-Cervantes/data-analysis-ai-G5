from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd

TYPE_OPTIONS = ["numeric", "categorical", "datetime", "boolean", "text"]


@dataclass
class DatasetRecord:
    name: str
    dataframe: pd.DataFrame
    source_type: str
    size_bytes: int
    loaded_at: str
    schema: dict[str, dict[str, Any]]
    warnings: list[str]

    @property
    def rows(self) -> int:
        return int(self.dataframe.shape[0])

    @property
    def columns(self) -> int:
        return int(self.dataframe.shape[1])


def load_uploaded_file(uploaded_file: Any) -> DatasetRecord:
    suffix = uploaded_file.name.lower().split(".")[-1]
    payload = uploaded_file.getvalue()

    if suffix == "csv":
        dataframe = pd.read_csv(BytesIO(payload))
        source_type = "csv"
    elif suffix in {"xlsx", "xls"}:
        dataframe = pd.read_excel(BytesIO(payload))
        source_type = "excel"
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")

    schema = infer_schema(dataframe)
    return DatasetRecord(
        name=uploaded_file.name,
        dataframe=dataframe,
        source_type=source_type,
        size_bytes=len(payload),
        loaded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        schema=schema,
        warnings=[],
    )


def infer_schema(dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
    schema: dict[str, dict[str, Any]] = {}
    for column in dataframe.columns:
        series = dataframe[column]
        detected = detect_series_type(series)
        example = next((value for value in series.dropna().head(1).tolist()), None)
        schema[column] = {
            "detected_type": detected,
            "confirmed_type": detected,
            "null_pct": round(float(series.isna().mean() * 100), 2),
            "example": "" if example is None else str(example),
            "warnings": [],
        }
    return schema


def detect_series_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    non_null = series.dropna()
    if non_null.empty:
        return "text"

    lowered = non_null.astype(str).str.strip().str.lower()
    if lowered.isin({"true", "false", "yes", "no", "0", "1", "y", "n"}).mean() >= 0.9:
        return "boolean"

    if pd.to_numeric(non_null, errors="coerce").notna().mean() >= 0.9:
        return "numeric"

    if pd.to_datetime(non_null, errors="coerce").notna().mean() >= 0.9:
        return "datetime"

    unique_ratio = non_null.nunique(dropna=True) / max(len(non_null), 1)
    if non_null.nunique(dropna=True) <= 30 or unique_ratio <= 0.2:
        return "categorical"

    return "text"


def apply_schema_to_dataset(
    record: DatasetRecord, confirmed_types: dict[str, str]
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]], list[str]]:
    dataframe = record.dataframe.copy()
    updated_schema: dict[str, dict[str, Any]] = {}
    all_warnings: list[str] = []

    for column in dataframe.columns:
        target_type = confirmed_types.get(column, record.schema[column]["confirmed_type"])
        converted, warnings = convert_series(dataframe[column], target_type)
        dataframe[column] = converted
        updated_schema[column] = {
            **record.schema[column],
            "confirmed_type": target_type,
            "warnings": warnings,
            "null_pct": round(float(dataframe[column].isna().mean() * 100), 2),
            "example": "" if dataframe[column].dropna().empty else str(dataframe[column].dropna().iloc[0]),
        }
        all_warnings.extend(f"{record.name}::{column} - {warning}" for warning in warnings)

    return dataframe, updated_schema, all_warnings


def convert_series(series: pd.Series, target_type: str) -> tuple[pd.Series, list[str]]:
    warnings: list[str] = []

    if target_type == "numeric":
        converted = pd.to_numeric(series, errors="coerce")
        invalid = int(series.notna().sum() - converted.notna().sum())
        if invalid:
            warnings.append(f"{invalid} values could not be converted to numeric")
        return converted, warnings

    if target_type == "datetime":
        converted = pd.to_datetime(series, errors="coerce")
        invalid = int(series.notna().sum() - converted.notna().sum())
        if invalid:
            warnings.append(f"{invalid} values could not be converted to datetime")
        return converted, warnings

    if target_type == "boolean":
        mapped = (
            series.astype(str)
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                    "yes": True,
                    "no": False,
                    "1": True,
                    "0": False,
                    "y": True,
                    "n": False,
                    "nan": pd.NA,
                    "none": pd.NA,
                }
            )
        )
        invalid = int(series.notna().sum() - mapped.notna().sum())
        if invalid:
            warnings.append(f"{invalid} values could not be converted to boolean")
        return mapped.astype("boolean"), warnings

    if target_type == "categorical":
        return series.astype("string").astype("category"), warnings

    return series.astype("string"), warnings


def validate_relationship(
    datasets: dict[str, DatasetRecord],
    left_table: str,
    left_column: str,
    right_table: str,
    right_column: str,
    relationship_type: str,
) -> list[str]:
    warnings: list[str] = []
    left_series = datasets[left_table].dataframe[left_column]
    right_series = datasets[right_table].dataframe[right_column]
    left_type = datasets[left_table].schema[left_column]["confirmed_type"]
    right_type = datasets[right_table].schema[right_column]["confirmed_type"]

    if left_type != right_type:
        warnings.append(f"Type mismatch: {left_type} vs {right_type}")
    if left_series.isna().any():
        warnings.append(f"{left_table}.{left_column} contains null keys")
    if right_series.isna().any():
        warnings.append(f"{right_table}.{right_column} contains null keys")

    left_dup = bool(left_series.duplicated().any())
    right_dup = bool(right_series.duplicated().any())
    if relationship_type == "1-1" and (left_dup or right_dup):
        warnings.append("1-1 relationship violated by duplicate keys")
    if relationship_type == "1-N" and left_dup:
        warnings.append("1-N relationship expects unique keys on the left table")
    if relationship_type == "N-1" and right_dup:
        warnings.append("N-1 relationship expects unique keys on the right table")

    return warnings


def build_joined_view(
    datasets: dict[str, DatasetRecord], relationships: list[dict[str, str]]
) -> tuple[str, pd.DataFrame] | None:
    if not relationships:
        return None

    first = relationships[0]
    left_table = first["left_table"]
    joined = datasets[left_table].dataframe.copy()
    view_name = left_table
    used_tables = {left_table}

    for relation in relationships:
        right_table = relation["right_table"]
        if right_table in used_tables:
            continue
        joined = joined.merge(
            datasets[right_table].dataframe.copy(),
            left_on=relation["left_column"],
            right_on=relation["right_column"],
            how="left",
            suffixes=("", f"_{right_table}"),
        )
        used_tables.add(right_table)
        view_name = f"{view_name}_join_{right_table}"

    return view_name, joined
