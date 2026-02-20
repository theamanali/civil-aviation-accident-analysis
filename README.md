# Civil Aviation Accident Analysis

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/theamanali/civil-aviation-accident-analysis/blob/main/analysis.ipynb)
![Python](https://img.shields.io/badge/Python-3-blue)
![Status](https://img.shields.io/badge/status-in%20progress-yellow)

Exploratory data analysis of **23,917 civil aviation accidents and incidents** from the [Aviation Safety Network](https://aviation-safety.net/) global database. The project looks at where, when, and what kind of accidents happen, and handles the messy parts of real-world data along the way: inconsistent dates, placeholder values, and fields that can't be taken at face value.

## Key Findings

- **The US accounts for 18% of all recorded accidents** (4,371). The US, Russia, UK, Canada, and India together make up about 34% of the dataset, across 231 countries.
- **Accident counts per country are heavily skewed.** The mean is ~100 per country but the median is 23, so a few countries account for most of the records.
- **About 73% of records are hull-loss accidents** (ASN category A1), and another 10% are accidents with repairable damage (A2). Criminal occurrences, hijackings, and other events make up most of the remainder.
- **Season makes almost no difference.** After adjusting seasons for each country's hemisphere, the four seasons are within 3% of each other (5,257–5,418 accidents).
- **February has the fewest accidents**, but it is also the shortest month. Per day, it is in line with the rest of the year.
- **Fatality counts are missing or zero for 17% of records**, which is why this project doesn't draw conclusions from fatality totals yet.

## Visualizations

| Accidents by month | Accidents by season (hemisphere-adjusted) |
|---|---|
| ![Accidents per month](images/accidents_by_month.png) | ![Accidents by season](images/accidents_by_season.png) |

![Distribution of accident categories](images/accident_categories.png)

## Approach

1. **Data loading:** pulled the dataset programmatically with `kagglehub` so the notebook runs end to end without manual downloads.
2. **Data quality audit:** built a missingness report that counts true nulls *and* placeholder values (`"unknown"`, `"N/A"`, `0`, `-1`, blanks) per column, since placeholders hide in plain sight in this dataset.
3. **Cleaning:** parsed free-form dates with `pd.to_datetime(errors="coerce")`, normalized country strings, and kept invalid rows out of time-based analysis instead of imputing them.
4. **Feature engineering:**
   - Extracted month from accident dates.
   - Mapped each country to a hemisphere (Northern, Southern, or equatorial) so that "winter" means December in Canada but July in Australia.
   - Derived meteorological seasons from month + hemisphere, excluding countries that straddle the equator (2,005 rows) instead of guessing.
5. **Aggregation and visualization:** grouped by month, season, country, and ASN category with pandas, and plotted with Matplotlib and Seaborn.

## Tech Stack

Python · pandas · NumPy · Matplotlib · Seaborn · kagglehub · Google Colab

## Run It

Click **Open in Colab** above, or run it locally:

```bash
pip install pandas numpy matplotlib seaborn kagglehub
jupyter notebook analysis.ipynb
```

The dataset downloads automatically on first run.

## Next Steps

- Normalize accident counts by flight volume, so countries with more air traffic aren't overrepresented
- Trend analysis by year and decade
- Clean the fatality column and analyze severity by operator and aircraft type
- Replace the country-to-hemisphere lookup with location coordinates for more accurate seasons

## Data Source

[Civil Aviation Accidents](https://www.kaggle.com/datasets/warcoder/civil-aviation-accidents) on Kaggle, sourced from the Aviation Safety Network.
