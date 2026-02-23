# World Bank snapshots

Saved copies of the World Bank data used by `analysis.ipynb`, so the results don't change when the World Bank revises past figures. Years with no value are left out. In the by-country file, `is_aggregate` marks World Bank groupings such as "World" or "High income" that aren't countries.

| File | Series | Years | World Bank last updated |
|---|---|---|---|
| `world_IS.AIR.DPRT.csv` | Registered carrier departures, worldwide ([IS.AIR.DPRT](https://data.worldbank.org/indicator/IS.AIR.DPRT)) | 1970-2023 | 2026-10-08 |
| `world_IS.AIR.PSGR.csv` | Passengers carried, worldwide ([IS.AIR.PSGR](https://data.worldbank.org/indicator/IS.AIR.PSGR)) | 1970-2023 | 2026-10-08 |
| `countries_IS.AIR.DPRT_2000-2019.csv` | Registered carrier departures, by country ([IS.AIR.DPRT](https://data.worldbank.org/indicator/IS.AIR.DPRT)) | 2000-2019 | 2026-10-08 |

To refresh, run `python scripts/update_world_bank_data.py` and re-run the notebook.

Source: World Bank, World Development Indicators, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
