# Civil Aviation Accident Analysis

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/theamanali/civil-aviation-accident-analysis/blob/main/analysis.ipynb)
![Python](https://img.shields.io/badge/Python-3-blue)
![Status](https://img.shields.io/badge/status-complete-brightgreen)

Exploratory data analysis of **23,917 civil aviation accidents and incidents from 1919 to 2023**, from the [Aviation Safety Network](https://aviation-safety.net/) global database, combined with World Bank flight and passenger counts to measure accident and death rates. The project looks at where, when, and what kind of accidents happen, and handles the messy parts of real-world data along the way: inconsistent dates, placeholder values, and fields that can't be taken at face value.

## Key Findings

- **Flying has become far safer.** Adjusted for flight volume, the civil accident rate fell about 71%, from 17.5 accidents per million departures in the 1970s to 5.1 in 2013–2022, while worldwide departures grew about 3.5x.
- **The risk of dying on board fell about 97%**, from roughly 1 death per 240,000 passengers in the 1970s to 1 per 7.5 million in 2013–2022, as passenger numbers grew more than 7x.
- **Accident rates vary widely by country.** Adjusted for flight volume (2000–2019), Russia, Indonesia, Canada, and Mexico had 2–4x the rate of the US and UK, while China and Japan were among the lowest. Smaller aviation markets averaged 9.3 accidents per million departures, more than twice the 20 busiest countries (4.2).
- **Modern jets are the most survivable.** About 21% of Boeing 727 and 737 accidents killed anyone, versus 62% for the DC-3. Military operators have the highest share of fatal accidents (9 of the top 10 operators, 66–82% fatal).

More findings (seasonality, World War II, fatalities, data quality) are in the [notebook](analysis.ipynb), each with a short takeaway.

## Visualizations

![Accident rate per million departures](images/accident_rate.png)

![On-board deaths per million passengers](images/deaths_per_passenger.png)

![Accident rates by country](images/country_accident_rates.png)

![Accidents per year](images/accidents_by_year.png)

![Deaths per year](images/deaths_by_year.png)

![Severity by aircraft family](images/severity_by_aircraft.png)

| Accidents by month | Accidents by season (hemisphere-adjusted) |
|---|---|
| ![Accidents per month](images/accidents_by_month.png) | ![Accidents by season](images/accidents_by_season.png) |

| Top 15 countries | Accident categories |
|---|---|
| ![Top 15 countries by number of accidents](images/top_countries.png) | ![Distribution of accident categories](images/accident_categories.png) |

## Approach

1. **Data loading:** pulled the dataset programmatically with `kagglehub` so the notebook runs end to end without manual downloads.
2. **Data quality audit:** built a missingness report that counts true nulls *and* placeholder values per column. Text placeholders (`"unknown"`, `"N/A"`, `"?"`, blanks) are matched case-insensitively, and numeric ones (`0`, `-1`) are skipped for columns where zero is a real value, like fatalities.
3. **Cleaning:** parsed free-form dates with `pd.to_datetime(format="mixed", errors="coerce")`, converted country placeholders (`"?"`, `"Unknown country"`) to nulls, and kept invalid rows out of time-based analysis instead of imputing them. Parsed the text `fatalities` column (`"5"` or `"5+ 1"`) into on-board, ground, and total counts with a regex, keeping missing values missing instead of treating them as 0. Grouped 3,193 aircraft type variants into 806 families (e.g. `"Douglas C-47A (DC-3)"` and `"Douglas DC-3A-197D"` → DC-3).
4. **Feature engineering:**
   - Extracted month from accident dates and normalized monthly counts by days per month.
   - Mapped each country to a hemisphere (Northern, Southern, or equatorial) so that "winter" means December in Canada but July in Australia.
   - Derived meteorological seasons from month + hemisphere, excluding countries that straddle the equator and open-ocean locations (2,450 rows) instead of guessing. The data has no coordinates, and places near the equator mostly have wet and dry seasons rather than winter and summer, so a country lookup is as precise as the season comparison needs.
5. **Normalization by flight volume:** joined yearly accident counts with the World Bank's worldwide departures series (1970–2022). To keep the two sources comparable, only ASN accidents were counted, with military operators (matched by name, e.g. air forces, navies, the USAAF) and private flights excluded. Divided on-board deaths by the World Bank's passengers-carried series to get deaths per million passengers, counting bombings, shootdowns, and hijackings alongside accidents, since they kill passengers too. Repeated the accident rate for the 20 busiest countries using country-level departures, with a name mapping between ASN and World Bank country names and a note that ASN records accident location while the World Bank records airline registration.
6. **Aggregation and visualization:** grouped by year, month, season, country, ASN category, operator, and aircraft family with pandas, and plotted with Matplotlib and Seaborn.

## Tech Stack

Python · pandas · NumPy · Matplotlib · Seaborn · kagglehub · Google Colab

## Run It

Click **Open in Colab** above, or run it locally:

```bash
pip install -r requirements.txt
jupyter notebook analysis.ipynb
```

Both datasets download automatically when the notebook runs.

## Next Steps

- Accident causes and phase of flight, which this dataset doesn't record; a richer source such as the NTSB database would be needed

## Data Source

- [Civil Aviation Accidents](https://www.kaggle.com/datasets/warcoder/civil-aviation-accidents) on Kaggle, sourced from the Aviation Safety Network
- World Bank (CC BY 4.0): [Air transport, registered carrier departures worldwide](https://data.worldbank.org/indicator/IS.AIR.DPRT) and [Air transport, passengers carried](https://data.worldbank.org/indicator/IS.AIR.PSGR)

## License

Code is released under the [MIT License](LICENSE). The World Bank data in `data/world_bank/` is © World Bank, licensed under CC BY 4.0. The accident dataset isn't included in this repository.
