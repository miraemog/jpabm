import numpy as np
from jpabm import Params, run, run_many, data as D
from jpabm.validate import validate, summarize
from jpabm.model import q_table, _e0


def test_life_expectancy_matches_ipss():
    for s, n in ((0, "M"), (1, "F")):
        assert abs(_e0(q_table(0)[s]) - D.IPSS_E0_2020[n]) < 0.05
        assert abs(_e0(q_table(50)[s]) - D.IPSS_E0_2070[n]) < 0.05


def test_baseline_starts_at_2020_census():
    r = run(Params(n_agents=40000), seed=1)
    assert abs(r["pop"][0] / 1e6 - 126.146) < 0.01
    assert abs(r["share_65p"][0] - 28.6) < 0.8


def test_baseline_tracks_ipss():
    rows, _ = validate(n_runs=4, n_agents=60000)
    s = summarize(rows)
    assert s["pop_max_abs_pct"] < 3.0
    assert s["dep_max_abs_pts"] < 4.5
    assert s["old_max_abs_pts"] < 1.5


def test_levers_move_in_the_right_direction():
    base = run_many(Params(n_agents=40000), 4, 7)
    hi = run_many(Params(n_agents=40000, tfr_delta=0.4), 4, 7)
    imm = run_many(Params(n_agents=40000, net_immigration=400000), 4, 7)
    assert hi["pop"][:, -1].mean() > base["pop"][:, -1].mean()
    assert imm["pop"][:, -1].mean() > base["pop"][:, -1].mean()
    assert imm["dependency"][:, -1].mean() < base["dependency"][:, -1].mean()


def test_retirement_age_lowers_debt_ratio():
    base = run_many(Params(n_agents=40000), 3, 3)
    late = run_many(Params(n_agents=40000, retirement_age=70), 3, 3)
    assert late["f_debtgdp"][:, -1].mean() < base["f_debtgdp"][:, -1].mean()


def test_fiscal_anchors_2024_2026():
    r = run(Params(n_agents=40000), seed=2)
    assert abs(r["f_gdp"][4] - 642.4) < 0.1 and abs(r["f_debt"][4] - 1079.7) < 0.1
    assert abs(r["f_benpct"][4] - 21.53) < 0.1 and abs(r["replacement"][4] - 61.2) < 0.1
    assert abs(r["f_intr"][6] - 13.0) < 1.0          # FY2026 budget interest 13.1 trillion yen


def test_economic_levers_move_in_the_right_direction():
    k = dict(n_agents=30000)
    base = run_many(Params(**k), 3, 11)["f_debtgdp"][:, -1].mean()
    assert run_many(Params(**k, tax_consumption=15), 3, 11)["f_debtgdp"][:, -1].mean() < base
    assert run_many(Params(**k, long_yield=4.0), 3, 11)["f_debtgdp"][:, -1].mean() > base
    assert run_many(Params(**k, productivity=1.5), 3, 11)["f_debtgdp"][:, -1].mean() < base


def test_python_matches_javascript_reference():
    """Means of the browser model (JavaScript port) for the baseline; Python must agree within sampling noise."""
    import json, os
    ref = json.load(open(os.path.join(os.path.dirname(__file__), "js_reference.json")))
    R = run_many(Params(n_agents=60000), 6, 41)
    for key, i, tol in (("f_debtgdp", 50, 15), ("f_debtgdp", 30, 8), ("f_real", 50, 2.5), ("f_benpct", 50, 0.8), ("dependency", 50, 1.5), ("pop", 50, 1.5e6)):
        assert abs(np.nanmean(R[key][:, i]) - ref[f"{key}_{i}"]) < tol, (key, i)


def test_policy_inactive_before_policy_start():
    a = run(Params(n_agents=30000, tfr_delta=0.5), seed=5)
    b = run(Params(n_agents=30000, tfr_delta=0.0), seed=5)
    assert np.allclose(a["pop"][:5], b["pop"][:5])
