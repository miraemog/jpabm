"""Compare the model with the IPSS 2023 medium projection. Run:  python -m jpabm.validate"""
from __future__ import annotations
import numpy as np
from . import data as D
from .model import Params, run_many


def validate(n_runs: int = 20, n_agents: int = 100_000, seed0: int = 1000):
    R = run_many(Params(n_agents=n_agents), n_runs, seed0)
    rows = []
    mean = lambda k: np.nanmean(R[k], 0)
    sd = lambda k: np.nanstd(R[k], 0)
    for y in D.YEARS:
        i = y - 2020
        rows.append(dict(
            year=y,
            pop_model=mean("pop")[i] / 1e6, pop_ipss=D.IPSS_POP_K[y] / 1e3,
            dep_model=mean("dependency")[i], dep_ipss=D.IPSS_DEPENDENCY[y],
            old_model=mean("share_65p")[i], old_ipss=D.IPSS_AGE_SHARE[y][2],
            work_model=mean("share_15_64")[i], work_ipss=D.IPSS_AGE_SHARE[y][1],
            kid_model=mean("share_0_14")[i], kid_ipss=D.IPSS_AGE_SHARE[y][0],
            old75_model=mean("share_75p")[i], old75_ipss=D.IPSS_75PLUS[y],
            pop_sd=sd("pop")[i] / 1e6,
        ))
    return rows, R


def summarize(rows):
    err = lambda a, b: np.array([r[a] - r[b] for r in rows])
    pop_pct = np.array([100 * (r["pop_model"] / r["pop_ipss"] - 1) for r in rows])
    out = {
        "pop_max_abs_pct": float(np.abs(pop_pct).max()),
        "pop_2070_pct": float(pop_pct[-1]),
        "dep_max_abs_pts": float(np.abs(err("dep_model", "dep_ipss")).max()),
        "dep_2070_pts": float(err("dep_model", "dep_ipss")[-1]),
        "old_max_abs_pts": float(np.abs(err("old_model", "old_ipss")).max()),
        "work_max_abs_pts": float(np.abs(err("work_model", "work_ipss")).max()),
        "kid_max_abs_pts": float(np.abs(err("kid_model", "kid_ipss")).max()),
        "old75_max_abs_pts": float(np.abs(err("old75_model", "old75_ipss")).max()),
    }
    return out


def pension_check(R):
    i = 2060 - 2020
    return dict(model_2024=float(np.nanmean(R["replacement"], 0)[4]),
                model_2060=float(np.nanmean(R["replacement"], 0)[i]),
                official_2024=D.PENSION_REPL_2024, official_2060=D.PENSION_REPL_2060)


def main():
    rows, R = validate()
    print(f"{'year':>5} | {'pop M (model/IPSS)':>20} | {'dep idx':>14} | {'65+ %':>13} | {'15-64 %':>13} | {'0-14 %':>12} | {'75+ %':>12}")
    for r in rows:
        print(f"{r['year']:>5} | {r['pop_model']:8.1f} /{r['pop_ipss']:7.1f}  | {r['dep_model']:6.1f} /{r['dep_ipss']:5.1f} | "
              f"{r['old_model']:5.1f} /{r['old_ipss']:5.1f} | {r['work_model']:5.1f} /{r['work_ipss']:5.1f} | "
              f"{r['kid_model']:4.1f} /{r['kid_ipss']:4.1f} | {r['old75_model']:4.1f} /{r['old75_ipss']:4.1f}")
    s = summarize(rows)
    print("\nSummary:", {k: round(v, 2) for k, v in s.items()})
    print("Pension pressure check:", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in pension_check(R).items()})


if __name__ == "__main__":
    main()
