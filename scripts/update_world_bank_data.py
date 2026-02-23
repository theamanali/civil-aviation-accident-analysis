"""Refresh the World Bank snapshots in data/world_bank/ that analysis.ipynb reads.

The notebook uses saved copies rather than the live API so its results don't change when the
World Bank revises past figures. Run this to pull the latest data, then re-run the notebook:

    python scripts/update_world_bank_data.py
"""

import csv
import json
import pathlib
import urllib.request

API_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=20000{dates}"
COUNTRIES_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "world_bank"

# (file name, country code, indicator, description, optional year range)
SNAPSHOTS = [
    ("world_IS.AIR.DPRT", "WLD", "IS.AIR.DPRT", "Registered carrier departures, worldwide", None),
    ("world_IS.AIR.PSGR", "WLD", "IS.AIR.PSGR", "Passengers carried, worldwide", None),
    ("countries_IS.AIR.DPRT_2000-2019", "all", "IS.AIR.DPRT", "Registered carrier departures, by country", (2000, 2019)),
]


def fetch(country, indicator, years=None):
    dates = f"&date={years[0]}:{years[1]}" if years else ""
    with urllib.request.urlopen(API_URL.format(country=country, indicator=indicator, dates=dates), timeout=60) as response:
        meta, rows = json.load(response)
    return meta, [row for row in rows if row["value"] is not None]


def fetch_aggregate_codes():
    """Codes for World Bank groupings like "World" or "High income", which aren't countries."""
    with urllib.request.urlopen(COUNTRIES_URL, timeout=60) as response:
        _, countries = json.load(response)
    # Income groups appear in indicator data with only a 2-letter code (e.g. "XD" for High income), so keep both
    return {code for c in countries if c["region"]["value"] == "Aggregates" for code in (c["id"], c["iso2Code"])}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    aggregate_codes = fetch_aggregate_codes()
    table = []
    for name, country, indicator, description, years in SNAPSHOTS:
        meta, rows = fetch(country, indicator, years)
        with open(OUT_DIR / f"{name}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            if country == "WLD":
                writer.writerow(["year", "value"])
                writer.writerows((r["date"], r["value"]) for r in sorted(rows, key=lambda r: r["date"]))
            else:
                writer.writerow(["country", "year", "value", "is_aggregate"])
                writer.writerows(
                    (r["country"]["value"], r["date"], r["value"], r["countryiso3code"] in aggregate_codes or r["country"]["id"] in aggregate_codes)
                    for r in sorted(rows, key=lambda r: (r["country"]["value"], r["date"]))
                )
        coverage = f"{years[0]}-{years[1]}" if years else f"{min(r['date'] for r in rows)}-{max(r['date'] for r in rows)}"
        table.append(f"| `{name}.csv` | {description} ([{indicator}](https://data.worldbank.org/indicator/{indicator})) | {coverage} | {meta['lastupdated']} |")
        print(f"Wrote {name}.csv ({len(rows)} rows, World Bank last updated {meta['lastupdated']})")

    (OUT_DIR / "README.md").write_text(
        "# World Bank snapshots\n\n"
        "Saved copies of the World Bank data used by `analysis.ipynb`, so the results don't change when the World Bank "
        "revises past figures. Years with no value are left out. In the by-country file, `is_aggregate` marks "
        "World Bank groupings such as \"World\" or \"High income\" that aren't countries.\n\n"
        "| File | Series | Years | World Bank last updated |\n|---|---|---|---|\n"
        + "\n".join(table)
        + "\n\nTo refresh, run `python scripts/update_world_bank_data.py` and re-run the notebook.\n\n"
        "Source: World Bank, World Development Indicators, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).\n"
    )


if __name__ == "__main__":
    main()
