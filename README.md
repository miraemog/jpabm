# jpabm — an agent-based model of Japan's population, economy and public finances

Each agent is one person (age, sex, region, marital status). The model runs 2020→2070 in annual steps and is
**calibrated to, and checked against, the IPSS 2023 national projections** (National Institute of Population and
Social Security Research). It is meant for *comparing policy scenarios on equal footing*, not for forecasting.

日本語: 個人単位の人口モデル（2020→2070）。社人研(IPSS)2023年推計に合わせて調整し、公式値との差を公開しています。
出生率・移民・退職年齢・結婚率に加え、消費税率・長期金利・物価・生産性を動かして、人口、実質GDP、社会保障、国の債務の変化を比べられます。
ブラウザ版: 同梱の `docs/mini_japan_simulator.html`（JavaScript移植版）。正本はこのPython版で、`tests/test_model.py` が両者の一致を確認します。

## Install and run

```bash
pip install git+https://github.com/miraemog/jpabm.git      # numpy only
# or, from a clone:
pip install -e ".[dev]"
python -m jpabm.validate    # prints the comparison table below
pytest                      # 9 tests, ~6 s
```

Reproduce everything in a browser, with no installation: open `docs/Colab_reproduce.ipynb` in Google Colab
(File > Open notebook > GitHub). It installs the package from this repository and re-runs the validation table and the scenarios.

```python
from jpabm import Params, run_many, band
base = run_many(Params(n_agents=100_000), n_runs=20)
imm  = run_many(Params(n_agents=100_000, net_immigration=263_791), n_runs=20)   # +100k/yr
print(base["dependency"][:, -1].mean(), imm["dependency"][:, -1].mean())
```

Levers (all phased in linearly from 2025 over `policy_ramp` years): `tfr_delta`, `net_immigration` (persons/yr),
`retirement_age`, `marriage_mult`, `migration_mult`; baselines: `tfr_longrun` (1.13 / 1.36 / 1.64 = IPSS low / medium / high),
`longevity_mult`.

## Validation against IPSS 2023 (fertility-medium, mortality-medium)

100,000 agents, mean of 20 replicates. Max gaps over 2020–2070:
population 1.8%, dependency index 3.7 points, 65+ share 0.9 pt,
15–64 share 1.0 pt, 0–14 share 0.3 pt. The model ages slightly faster than IPSS
(2070: population +1.8%, dependency +3.6 points).

| Year | Population (M) model / IPSS | Dependency index model / IPSS | 65+ share % model / IPSS | 15-64 share % model / IPSS | 0-14 share % model / IPSS |
|---|---|---|---|---|---|
| 2020 | 126.1 / 126.1 | 68.0 / 68.0 | 28.4 / 28.6 | 59.5 / 59.5 | 12.0 / 11.9 |
| 2025 | 123.4 / 123.3 | 69.1 / 68.6 | 29.6 / 29.6 | 59.2 / 59.3 | 11.3 / 11.1 |
| 2030 | 120.2 / 120.1 | 70.7 / 69.8 | 30.8 / 30.8 | 58.6 / 58.9 | 10.6 / 10.3 |
| 2035 | 116.6 / 116.6 | 74.2 / 73.5 | 32.4 / 32.3 | 57.4 / 57.6 | 10.2 / 10.0 |
| 2040 | 112.8 / 112.8 | 82.2 / 81.6 | 35.1 / 34.8 | 54.9 / 55.1 | 10.0 / 10.1 |
| 2045 | 108.9 / 108.8 | 87.2 / 86.5 | 36.7 / 36.3 | 53.4 / 53.6 | 9.9 / 10.1 |
| 2050 | 105.0 / 104.7 | 90.0 / 89.0 | 37.6 / 37.1 | 52.6 / 52.9 | 9.8 / 9.9 |
| 2055 | 101.0 / 100.5 | 91.1 / 89.4 | 38.1 / 37.6 | 52.3 / 52.8 | 9.6 / 9.6 |
| 2060 | 96.9 / 96.1 | 91.7 / 89.3 | 38.4 / 37.9 | 52.2 / 52.8 | 9.4 / 9.3 |
| 2065 | 92.8 / 91.6 | 94.1 / 90.4 | 39.2 / 38.4 | 51.5 / 52.5 | 9.3 / 9.1 |
| 2070 | 88.6 / 87.0 | 95.4 / 91.8 | 39.6 / 38.7 | 51.2 / 52.1 | 9.2 / 9.2 |

**What was fitted and what was not.** Life expectancy (IPSS 2020 and 2070, by sex) is matched exactly by construction.
One more parameter, the Gompertz slope of mortality, was fitted to the 65+ and 75+ population shares
(`scripts/calibrate_mortality.py`). Population, 0–14 and 15–64 shares and the dependency index were **not** used for fitting.

## Economy and public finances (v0.2)

`jpabm/fiscal.py` adds an annual block from fiscal 2024: real GDP (labour input × productivity), social security benefits
(pensions by number of recipients, medical spending by age structure, welfare), the pension replacement rate with the
macro-economic slide (stopped at 50%), consumption and other taxes, the national primary balance, ordinary government bonds
and interest payments. Levers: `tax_consumption`, `tax_other_pct`, `contribution_gdp_pct`, `long_yield`, `inflation`,
`productivity`. Anchors are FY2024–26 figures from the Ministry of Finance, IPSS, MHLW and the Cabinet Office; they are listed in
`jpabm/fiscal.py` and on the web page, which also marks which values are fitted assumptions.

Checks: FY2024 anchors (GDP, debt, benefits/GDP, replacement 61.2%) and FY2026 interest (≈¥13 trillion) are tested.
The replacement rate reaches about 49.6% in 2060 against 50.4–57.6% in the 2024 official valuation.

**Scope and limits.** National general account and ordinary government bonds only (no local government, pension reserve or special accounts).
Growth depends only on workers and productivity inputs: tax rates, interest rates and inflation do **not** feed back into growth, so tax-rise
scenarios overstate the fall in debt. Tax revenue is proportional to the rate (consumption) or to nominal GDP (other taxes).

## Levers

Population levers are sized to add about the same number of people per year (about 90k on average in 2031–40, phased in 2025–35).
Economic levers are changed one at a time with population at baseline. 20 replicates × 100,000 agents (`scripts/experiments.py`).

| Scenario | Pop 2070 (M) | Dependency 2070 | Real GDP 2070 (FY2024=100) | Debt 2070 (% GDP) | Interest ÷ tax 2050 |
|---|---|---|---|---|---|
| Baseline (IPSS medium) | 88.5 | 95.5 | 100.2 | 296% | 37.8% |
| Immigration +100k/yr | 93.9 | 89.9 | 109.8 | 251% | 35.5% |
| Births +100k/yr (TFR +0.18) | 92.8 | 94.3 | 105.0 | 279% | 37.7% |
| Marriage share +10% | 91.0 | 95.0 | 102.7 | 288% | 37.8% |
| Pension age 68 | 88.5 | 95.5 | 108.8 | 223% | 30.9% |
| Recent TFR persists (1.17 in 2035) | 85.7 | 96.7 | 96.8 | 310% | 37.8% |
| Immigration + births + age 68 | 98.1 | 89.1 | 123.8 | 175% | 29.0% |
| Consumption tax 10% to 15% | 88.5 | 95.5 | 100.2 | 213% | 26.8% |
| Contribution revenue +1% of GDP | 88.5 | 95.5 | 100.2 | 253% | 34.2% |
| Long-term yield 4% | 88.5 | 95.5 | 100.2 | 437% | 72.6% |
| Inflation 3% (yield 2.5%) | 88.5 | 95.5 | 100.2 | 218% | 31.5% |
| Inflation 3%, yield 3.5% | 88.5 | 95.5 | 100.2 | 279% | 49.8% |
| Productivity 1.5%/yr | 88.5 | 95.5 | 128.1 | 204% | 31.9% |
| Productivity 0%/yr | 88.5 | 95.5 | 69.1 | 493% | 48.4% |

Headcount for headcount, immigration lowers the 2070 dependency index about 4.5× as much as births (−5.6 vs −1.2),
because arrivals are assumed to be 20–39 and working immediately, while newborns take ~20 years. That depends on the
immigration assumptions below and ignores integration costs. The interest rate matters most for debt: a long-term yield of 4% instead of 2.5%
takes the 2070 debt ratio from about 300% to about 440%.

One model, two front ends: the Python package is the reference; the web page is a JavaScript port. `tests/js_reference.json` holds the browser
model's baseline means and `test_python_matches_javascript_reference` fails if they drift apart.

## Known approximations (please help improve these)

- 2020 age structure: 5-year × sex pyramid from a secondary source (Wikipedia citing IPSS/Statistics Bureau), uniform within bands.
- Age-specific fertility: 2020 shape held fixed; births outside marriage fixed at 2%; the 2023–2028 TFR path (1.26→1.29) is an approximate reading of IPSS ("below 1.3 until 2028").
- Immigration: 164k/yr (IPSS value for 2040) reached by linear ramp from an assumed 60k in 2020; arrivals aged 20–39, same marriage/fertility as natives.
- Marriage: first-marriage age ~ Normal(mean, 4.8); means and lifetime unmarried rates from 2020/2024 statistics; no divorce or widowhood.
- Regions (4): population shares, fertility multipliers, wage multipliers and migration probabilities are assumptions, not fitted to prefecture data.
- Economy: growth is labour input × exogenous productivity (no capital accumulation, no feedback from tax, rates or inflation); fiscal scope is the national general account.

## Extending

See [CONTRIBUTING.md](CONTRIBUTING.md) for step-by-step notes on adding prefectures or an education layer.

`jpabm/data.py` holds every reference number with its source. Natural next steps: prefecture-level regions with real
migration flows (Statistics Bureau), an education layer, households and divorce, a funded pension reserve and subsidy,
and checks against the IPSS fertility/mortality variants (high/low).

## Sources

- IPSS Population Projections 2023 rev.: https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2023RE/T02-08.files/sheet001.htm
- IPSS total population by age group: https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2023RE/T02-09.files/sheet001.htm
- IPSS age-specific fertility: https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2023RE/T04-07.files/sheet001.htm
- MHLW summary of 2023 projections (TFR/e0/migration assumptions): https://www.mhlw.go.jp/wp/hakusyo/kousei/25-2/dl/01.pdf
- NRI note on 2024 pension actuarial valuation: https://www.nri.com/jp/knowledge/blog/lst/2024/fis/kiuchi/0703_2
- 2020 population pyramid (secondary): https://en.wikipedia.org/wiki/Demographics_of_Japan

## Citation

See `CITATION.cff`. MIT licence.
