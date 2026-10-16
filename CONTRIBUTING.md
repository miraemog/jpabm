# Contributing

jpabm is a small, readable model. The goal is that anyone can add a layer and see, in one table, how it changes the
validation against IPSS 2023 and the scenario results.

## Ground rules

1. **The Python package is the reference.** The web simulator (`docs/`) is a JavaScript port. If you change an equation,
   change it in `jpabm/` first. If the baseline moves, update `tests/js_reference.json` (or port the change to
   `docs/jpabm_web_model.js`) so `test_python_matches_javascript_reference` passes.
2. **Every number needs a source.** Put reference data in `jpabm/data.py` with a link in `SOURCES`. Mark anything that is
   an assumption, not a statistic, as such in a comment and in the README's "Known approximations".
3. **Report what you fitted.** The README states which parameters were fitted and to what. A new layer should do the same,
   and say which published figures it was *not* fitted to, so they can be used as a check.
4. `pytest` must pass and `python -m jpabm.validate` should not get worse without an explanation in the pull request.

## Where to add things

**Prefectures instead of 4 regions.** Regions are an `int8` column (`region`) with four constants in `jpabm/data.py` / `model.py`:
`REGIONS`, `REGION_SHARE0`, `REGION_FERT`, `REGION_WAGE`, and the migration edge list `MIGRATION`. To go to 47 prefectures:
1. replace those arrays with length-47 ones (2020 census shares, prefecture TFR, wage index from the Basic Survey on Wage Structure);
2. replace `MIGRATION` with a 47x47 annual probability matrix from the Report on Internal Migration;
3. change `rng.choice(4, ...)` in `_initial_population` and the hard-coded `4` in the region draws in `run()`;
4. keep the national totals identical at the start so the IPSS validation does not move (the code already rescales `REGION_FERT`).

**Education layer.** Add an `educ` column next to `age`, `sex`, `region`, `married`:
1. sample it in `_initial_population` from the 2020 census (age x sex x schooling);
2. assign it at age 18-22 inside the yearly step (university entry rate by region is the natural lever);
3. let it modify something that already exists: wage (`REGION_WAGE` becomes `WAGE[region, educ]`, which changes `labor_index`),
   marriage hazard, or fertility multiplier;
4. add a lever to `Params` and a row to `scripts/experiments.py`.

**Other open items** (see README, "Known approximations"): divorce and widowhood, households, a funded pension reserve and
national subsidy, local government finances, IPSS high/low variant checks, an `NDIM`-style regression test for each new layer.

## Style

Plain NumPy, vectorised over agents. No new dependencies in the core package (plotting stays in the `plot` extra).
