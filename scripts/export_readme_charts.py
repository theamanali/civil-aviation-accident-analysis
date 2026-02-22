"""Render the README charts from analysis.ipynb in light and dark themes.

Runs the notebook once per theme and saves the charts below to images/. GitHub shows the
"-dark" versions to visitors using dark mode (see the <picture> tags in README.md).
Run it after changing one of these charts:

    python scripts/export_readme_charts.py
"""

import base64
import os
import pathlib

import nbformat
from nbclient import NotebookClient

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Notebook cell id -> image file name
README_CHARTS = {
    "rate-departures": "accident_rate",
    "passenger-rate": "deaths_per_passenger",
    "country-rate": "country_accident_rates",
    "severity-family": "severity_by_aircraft",
}


def main():
    for theme in ("light", "dark"):
        os.environ["CHART_THEME"] = theme  # the notebook's setup cell reads this
        notebook = nbformat.read(ROOT / "analysis.ipynb", as_version=4)
        NotebookClient(notebook, timeout=600, resources={"metadata": {"path": str(ROOT)}}).execute()

        suffix = "" if theme == "light" else "-dark"
        for cell in notebook.cells:
            name = README_CHARTS.get(cell.metadata.get("id"))
            if name is None:
                continue
            images = [o["data"]["image/png"] for o in cell.get("outputs", []) if "image/png" in o.get("data", {})]
            assert len(images) == 1, f"expected one chart in cell {cell.metadata['id']}, found {len(images)}"
            (ROOT / "images" / f"{name}{suffix}.png").write_bytes(base64.b64decode(images[0]))
            print(f"Wrote images/{name}{suffix}.png")


if __name__ == "__main__":
    main()
