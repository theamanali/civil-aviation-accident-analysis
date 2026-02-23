"""Export Tableau-ready CSVs from analysis.ipynb.

Runs the notebook's code once, then writes the cleaned accident records and the tables behind each
finding to tableau/. Statistics that Tableau can't easily compute (confidence intervals, trend fits,
bootstrap and test results) are precomputed as columns, so they can be drawn as error bars or bands.

    python scripts/export_tableau_data.py

Files written:
    accidents.csv           one row per ASN record, cleaned, with the notebook's derived fields
    yearly_rates.csv        1970-2022 accident rate per million departures and deaths per million passengers, with trend lines
    country_rates.csv       2000-2019 accident rate per million departures for every country, with 95% Poisson CIs
    market_groups.csv       pooled 2000-2019 rates for the busiest 20 countries vs mid-sized and smallest markets
    aircraft_severity.csv   share of fatal accidents by aircraft family (50+ accidents), with 95% Wilson CIs
    operator_severity.csv   share of fatal accidents by operator (50+ accidents), with 95% Wilson CIs
    monthly.csv             accidents per calendar day by month
    summary_stats.csv       the headline numbers from the README, for captions and reference lines
"""

import contextlib
import io
import os
import pathlib
import warnings

import matplotlib

matplotlib.use("Agg")  # the notebook's charts are drawn but not shown

import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "tableau"

OCCURRENCE_TYPES = {"A": "Accident", "C": "Criminal occurrence", "H": "Hijacking", "I": "Incident", "O": "Other", "U": "Unknown"}
DAMAGE_LEVELS = {"1": "Hull loss", "2": "Repairable damage"}
HEMISPHERES = {"N": "Northern", "S": "Southern", "Mixed/Equatorial": "Equatorial or ocean"}


def run_notebook() -> dict:
    """Run every code cell of the notebook in one namespace and return the resulting variables."""
    namespace = {"display": lambda *args, **kwargs: None}
    notebook = nbformat.read(ROOT / "analysis.ipynb", as_version=4)
    os.chdir(ROOT)  # the notebook reads data/world_bank/ relative to the repo root
    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*non-interactive.*")
        for cell in notebook.cells:
            if cell.cell_type == "code":
                exec(cell.source, namespace)
                plt.close("all")
    return namespace


def accidents_table(ns: dict) -> pd.DataFrame:
    data = ns["aviation_data"]
    month = data["date"].dt.month.astype("Int64")
    hemisphere = data["country"].map(ns["assign_hemisphere"])

    # Seasons only where the hemisphere is known, matching section 6
    season = pd.Series(pd.NA, index=data.index, dtype="string")
    has_season = month.notna() & hemisphere.isin(["N", "S"])
    season[has_season] = [ns["season_from_month_and_hemi"](m, h) for m, h in zip(month[has_season], hemisphere[has_season])]

    # Same definitions as section 10: civil accidents exclude hijackings, criminal occurrences, military and private flights
    is_military = ns["is_military"]
    is_private = ns["is_private"]
    is_accident = data["cat"].str.startswith("A").fillna(False).astype(bool)

    total = data["fatalities_total"]
    return pd.DataFrame({
        "date": data["date"].dt.strftime("%Y-%m-%d"),
        "year": pd.to_numeric(data["year"], errors="coerce").astype("Int64"),
        "month": month,
        "country": data["country"],
        "country_world_bank": data["country"].replace(ns["COUNTRY_TO_WORLD_BANK"]),
        "hemisphere": hemisphere.map(HEMISPHERES),
        "season": season,
        "location": data["location"],
        "category": data["cat"],
        "occurrence_type": data["cat"].str[0].map(OCCURRENCE_TYPES),
        "damage": data["cat"].str[1:].map(DAMAGE_LEVELS),
        "aircraft_type": data["type"],
        "aircraft_family": data["aircraft_family"],
        "registration": data["registration"],
        "operator": data["operator_clean"],
        "is_military": is_military,
        "is_private": is_private,
        "is_civil_accident": is_accident & ~is_military & ~is_private,
        "fatalities_onboard": data["fatalities_onboard"],
        "fatalities_ground": data["fatalities_ground"],
        "fatalities_total": total,
        "is_fatal": (total > 0).astype("boolean"),
    })


def yearly_rates_table(ns: dict) -> pd.DataFrame:
    years = pd.RangeIndex(1970, 2023, name="year")
    rate_fit, death_fit = ns["rate_fit"], ns["death_fit"]
    death_rate = ns["death_rate"].reindex(years)
    table = pd.DataFrame({
        "departures": ns["departures"].reindex(years),
        "passengers": ns["passengers"].reindex(years),
        "civil_accidents": ns["civil_per_year"].reindex(years, fill_value=0),
        "accidents_per_million_departures": ns["rate"].reindex(years).round(3),
        "accident_rate_trend": np.exp(rate_fit.intercept + rate_fit.slope * years).round(3),
        "civil_onboard_deaths": ns["onboard_deaths_per_year"](ns["civil_records"]).reindex(years),
        "deaths_per_million_passengers": death_rate.round(4),
        "death_rate_trend": np.exp(death_fit.intercept + death_fit.slope * years).round(4),
        "passengers_per_death": (1_000_000 / death_rate).replace(np.inf, np.nan).round(-3),
        "excluded_from_trend": years.isin([2020, 2021]),  # COVID-19
    }, index=years)
    return table.reset_index()


def poisson_rate_interval(accidents: pd.Series, departures: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Exact 95% Poisson confidence interval for accidents per million departures (same as section 12)."""
    low = pd.Series(stats.chi2.ppf(0.025, 2 * accidents) / 2, index=accidents.index).fillna(0)  # 0 accidents -> lower bound 0
    high = pd.Series(stats.chi2.ppf(0.975, 2 * accidents + 2) / 2, index=accidents.index)
    return low / departures * 1_000_000, high / departures * 1_000_000


def market_group(ns: dict, countries: pd.Index) -> pd.Series:
    groups = pd.Series("Under 1M departures", index=countries)
    groups[groups.index.isin(ns["mid_size"].index)] = "Other 1M+ departures"
    groups[groups.index.isin(ns["top_20"].index)] = "Busiest 20"
    return groups


def country_rates_table(ns: dict) -> pd.DataFrame:
    table = ns["by_country"].copy()
    table = table[table["departures"] > 0]
    world_rate = ns["world_rate"]
    table["accidents_per_million_departures"] = table["accidents"] / table["departures"] * 1_000_000
    table["ci_low"], table["ci_high"] = poisson_rate_interval(table["accidents"], table["departures"])
    table["vs_world_rate"] = np.select(
        [table["ci_low"] > world_rate, table["ci_high"] < world_rate], ["Significantly above", "Significantly below"], "Not significant"
    )
    table["world_rate"] = world_rate
    table["departures_rank"] = table["departures"].rank(ascending=False, method="first").astype(int)
    table["market_group"] = market_group(ns, table.index)
    table["in_busiest_chart"] = table.index.isin(ns["busiest"].index)  # the 18 countries charted in section 12
    table = table.astype({"departures": "int64", "accidents": "int64"}).round(
        {"accidents_per_million_departures": 3, "ci_low": 3, "ci_high": 3, "world_rate": 3}
    )
    return table.sort_values("departures_rank").rename_axis("country").reset_index()


def market_groups_table(ns: dict) -> pd.DataFrame:
    rows = []
    for label, group in [("Busiest 20", ns["top_20"]), ("Other 1M+ departures", ns["mid_size"]), ("Under 1M departures", ns["smallest"])]:
        rows.append({
            "market_group": label,
            "countries": len(group),
            "accidents": int(group["accidents"].sum()),
            "departures": int(group["departures"].sum()),
            "accidents_per_million_departures": round(ns["pooled_rate"](group), 3),
        })
    return pd.DataFrame(rows)


def severity_with_intervals(ns: dict, table: pd.DataFrame, fatal: pd.Series, name: str) -> pd.DataFrame:
    table = table.copy()
    table["fatal_accidents"] = fatal[table.index].astype(int)
    table["pct_fatal"] = (table["fatal_accidents"] / table["accidents"] * 100).round(2)
    low, high = ns["wilson_interval"](table["fatal_accidents"], table["accidents"])
    table["ci_low"], table["ci_high"] = low.round(2), high.round(2)
    table = table.rename(columns={"accidents": "accidents_with_known_deaths"})
    return table.sort_values("accidents_with_known_deaths", ascending=False).rename_axis(name).reset_index()


def aircraft_severity_table(ns: dict) -> pd.DataFrame:
    table = severity_with_intervals(ns, ns["family_severity"], ns["fatal_accidents"], "aircraft_family")
    table["in_top_15_chart"] = table["aircraft_family"].isin(ns["most_common"].index)
    return table


def operator_severity_table(ns: dict) -> pd.DataFrame:
    table = ns["operator_severity"].drop(columns=["ci_low", "ci_high", "military"])
    table = severity_with_intervals(ns, table, ns["fatal_by_operator"], "operator")
    table["is_military"] = ns["is_military_operator"](table["operator"])
    return table


def monthly_table(ns: dict) -> pd.DataFrame:
    counts, days = ns["accidents_per_month"], ns["days_in_month"]
    per_day = counts / days
    average = counts.sum() / days.sum()
    return pd.DataFrame({
        "month": counts.index,
        "month_name": ns["MONTH_LABELS"],
        "accidents": counts.values,
        "days": days.values,
        "accidents_per_day": per_day.round(2).values,
        "vs_average_pct": ((per_day / average - 1) * 100).round(1).values,
    })


def summary_table(ns: dict) -> pd.DataFrame:
    rate, death_rate = ns["rate"], ns["death_rate"]
    rate_ci, death_ci, ratio_ci = ns["rate_ci"], ns["death_ci"], ns["ratio_ci"]

    operators = ns["operator_severity"]
    fatal = ns["fatal_by_operator"][operators.index]
    military = operators["military"]
    records_military = ns["is_military_operator"](ns["aviation_data"]["operator_clean"])
    missing_deaths = ns["aviation_data"]["fatalities_total"].isna()

    rows = [
        ("Accidents per million departures, 1970s", rate.loc[1970:1979].mean(), None, None),
        ("Accidents per million departures, 2013-2022", rate.loc[2013:2022].mean(), None, None),
        ("Accident rate change, 1970s to 2013-2022 (%)", (rate.loc[2013:2022].mean() / rate.loc[1970:1979].mean() - 1) * 100, None, None),
        ("Accident rate trend (% per year)", ns["rate_change"] * 100, rate_ci[0] * 100, rate_ci[1] * 100),
        ("Deaths per million passengers, 1970s", death_rate.loc[1970:1979].mean(), None, None),
        ("Deaths per million passengers, 2013-2022", death_rate.loc[2013:2022].mean(), None, None),
        ("Passengers per on-board death, 1970s", 1e6 / death_rate.loc[1970:1979].mean(), None, None),
        ("Passengers per on-board death, 2013-2022", 1e6 / death_rate.loc[2013:2022].mean(), None, None),
        ("Death rate trend (% per year)", ns["death_change"] * 100, death_ci[0] * 100, death_ci[1] * 100),
        ("Worldwide accidents per million departures, 2000-2019", ns["world_rate"], None, None),
        ("Smaller markets vs busiest 20, rate ratio", ns["rate_ratio"], ratio_ci[0], ratio_ci[1]),
        ("Mid-sized vs busiest 20, Mann-Whitney p", ns["size_test"].pvalue, None, None),
        ("Military operators, % of accidents fatal", fatal[military].sum() / operators.loc[military, "accidents"].sum() * 100, None, None),
        ("Civil operators, % of accidents fatal", fatal[~military].sum() / operators.loc[~military, "accidents"].sum() * 100, None, None),
        ("Military vs civil operators, Mann-Whitney p", ns["military_test"].pvalue, None, None),
        ("Military records with no fatality count (%)", missing_deaths[records_military].mean() * 100, None, None),
        ("Civil records with no fatality count (%)", missing_deaths[~records_military].mean() * 100, None, None),
        ("Month differences, chi-square p", ns["p_month"], None, None),
        ("Season differences, chi-square p", ns["p_season"], None, None),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "ci_low", "ci_high"]).astype(
        {"value": float, "ci_low": float, "ci_high": float}
    )


def main():
    print("Running analysis.ipynb...")
    ns = run_notebook()
    OUT_DIR.mkdir(exist_ok=True)
    tables = {
        "accidents": accidents_table(ns),
        "yearly_rates": yearly_rates_table(ns),
        "country_rates": country_rates_table(ns),
        "market_groups": market_groups_table(ns),
        "aircraft_severity": aircraft_severity_table(ns),
        "operator_severity": operator_severity_table(ns),
        "monthly": monthly_table(ns),
        "summary_stats": summary_table(ns),
    }
    for name, table in tables.items():
        table.to_csv(OUT_DIR / f"{name}.csv", index=False)
        print(f"Wrote tableau/{name}.csv ({len(table):,} rows)")


if __name__ == "__main__":
    main()
