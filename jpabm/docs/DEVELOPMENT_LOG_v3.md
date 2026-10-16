# Development log — v3 (IPSS-validated model, browser tool, package)

Date: 2026-10-16. Everything below was observed while building; numbers are from actual runs.

## Correction to earlier results
The v2 claim "immigration has about twice the leverage of fertility" compared levers of different sizes
(0→10 immigrants/1000 vs TFR 0.9→1.5) and is withdrawn. v3 sizes both to ~+92k people per year (2031–40 average):
immigration cuts the 2070 dependency index by 5.6 points, births by 1.3 (about 4×), with the assumptions listed in the README.

## What changed in the model
Rebuilt as a vectorised, individual-level model (one agent = one person) starting from the 2020 census-based pyramid.
Dropped from v2: household-pooled consumption/savings and the firm-level labour market (the new model reports labour input,
not wages or consumption). Kept: four regions with a migration hierarchy, marriage-linked fertility.

## Difficulties and fixes (in the order they appeared)
1. **First IPSS comparison failed.** Age shares sampled uniformly inside 0-14/15-64/65+ bands gave 2070 population 95.6M vs IPSS 87.0M (+10%)
   and a 2040 dependency index of 73.6 vs 81.6. The baby-boom and baby-boom-junior cohorts were missing.
   Fix: sample from a 5-year × sex pyramid (secondary source, noted in README).
2. **Demographic noise at 20,000 agents.** One agent was ~6,300 people, so births were ~130 agents/year and the realised TFR swung 1.08–1.43 year to year.
   Fix: 100,000 agents for validation, 30,000 × 14 replicates in the browser.
3. **Mortality shape.** Life expectancy matched exactly, but the 75+ share ran too high (2070: 27.3% vs 25.1%). Only the Gompertz slope was free;
   it was fitted on the 65+/75+ shares (0.092 → 0.13). Population, 0–14, 15–64 and dependency were not used in fitting.
4. **Immigration overshoot.** A flat 164k/yr made 2070 population +3.5% too high. IPSS states only the 2040 level, so a ramp from an
   assumed 60k (2020) was used; this is an assumption, listed in the README.
5. **Bug found by validation: newborns were aged before being added**, so every child was 1 at year end and the age-0 cohort was empty.
   Symptom: 0–14 share 8.4% vs IPSS 9.2%. Fixed; 0–14 now within 0.35 points. The fix exposed a masked error: the dependency gap rose to ~4 points,
   so the slope was refitted (item 3). A residual remains (2070: dependency +3.6, population +1.8%) and is reported rather than tuned away.
6. **Pension pressure is not a forecast.** With a fixed contribution rate and no subsidy/reserve/slide floor the 2060 value is 41.5% vs the
   official 50.4–57.6%. Left untuned and documented.
7. **JavaScript port check.** Baseline 2070 (16 runs, 40k agents): population 88.8M (Python 88.6), dependency 95.4 (95.4), Tokyo share 40.1 (40.3),
   pension pressure 2060 41.6 (41.2); immigration +100k: 93.4M / 90.5 (93.8 / 90.0); births +0.18 TFR: 92.3M / 94.3 (92.7 / 94.3).

## Not done
- IPSS high/low fertility variants were not compared (their totals were not retrieved).
- Regional shares, migration probabilities and fertility/wage multipliers are assumptions; no prefecture data.
- No divorce/widowhood, no funded pension reserve, no capital or productivity.

## Run counts
Validation: 20 runs × 100k agents. Policy table: 7 scenarios × 16 runs × 100k agents (112 runs). Calibration grids: 21 + 7 + 7 settings × 3 runs.
Earlier notebooks (v1 151 runs, v2 509 runs) used the older model and are not comparable to these results.
