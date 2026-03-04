from __future__ import annotations

from html import escape

import pandas as pd


def generate_html_report(
    dataset_name: str,
    dataframe: pd.DataFrame,
    schema: dict[str, dict[str, object]],
    eda_results: dict[str, object],
    relationships: list[dict[str, str]],
) -> str:
    preview_table = dataframe.head(20).to_html(index=False, classes="preview-table")
    numeric_summary = (
        eda_results["numeric_summary"].head(20).to_html(index=False, classes="preview-table")
        if not eda_results["numeric_summary"].empty
        else "<p>No numeric summary available.</p>"
    )
    missing_summary = eda_results["missing_summary"].head(20).to_html(index=False, classes="preview-table")

    schema_rows = []
    for column, meta in schema.items():
        schema_rows.append(
            "<tr>"
            f"<td>{escape(column)}</td>"
            f"<td>{escape(str(meta['detected_type']))}</td>"
            f"<td>{escape(str(meta['confirmed_type']))}</td>"
            f"<td>{escape(str(meta['null_pct']))}%</td>"
            f"<td>{escape(str(meta['example']))}</td>"
            "</tr>"
        )

    relationship_items = "".join(
        (
            "<li>"
            f"{escape(rel['left_table'])}.{escape(rel['left_column'])} "
            f"{escape(rel['relationship_type'])} "
            f"{escape(rel['right_table'])}.{escape(rel['right_column'])}"
            "</li>"
        )
        for rel in relationships
    )
    insight_items = "".join(f"<li>{escape(item)}</li>" for item in eda_results["insights"])

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Data Analysis AI Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1, h2 {{ color: #0f172a; }}
    .preview-table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
    .preview-table th, .preview-table td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    .preview-table th {{ background: #e5e7eb; }}
    .section {{ margin-bottom: 32px; }}
  </style>
</head>
<body>
  <h1>Data Analysis AI Report</h1>
  <div class="section">
    <h2>Dataset</h2>
    <p><strong>Name:</strong> {escape(dataset_name)}</p>
    <p><strong>Rows:</strong> {dataframe.shape[0]} | <strong>Columns:</strong> {dataframe.shape[1]}</p>
  </div>
  <div class="section">
    <h2>Key Insights</h2>
    <ul>{insight_items}</ul>
  </div>
  <div class="section">
    <h2>Relationships</h2>
    <ul>{relationship_items or "<li>No relationships defined.</li>"}</ul>
  </div>
  <div class="section">
    <h2>Data Dictionary</h2>
    <table class="preview-table">
      <thead>
        <tr><th>Column</th><th>Detected</th><th>Confirmed</th><th>Null %</th><th>Example</th></tr>
      </thead>
      <tbody>
        {''.join(schema_rows)}
      </tbody>
    </table>
  </div>
  <div class="section">
    <h2>Preview</h2>
    {preview_table}
  </div>
  <div class="section">
    <h2>Numeric Summary</h2>
    {numeric_summary}
  </div>
  <div class="section">
    <h2>Missing Values</h2>
    {missing_summary}
  </div>
</body>
</html>
"""
