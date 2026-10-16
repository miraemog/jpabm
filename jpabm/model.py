"""Mini-Japan agent-based model (vectorised, calibrated to IPSS 2023 projections).

Each agent is one individual (age, sex, region, marital status). One agent stands for
POP_2020 / n_agents real people. Annual steps, 2020 -> 2070.

Per-year order: death -> marriage -> regional migration -> births -> immigration -> age+1.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from math import erf, sqrt

import numpy as np

from . import data as D
from .fiscal import fiscal

REGIONS = ["tokyo_metro", "osaka_nagoya", "regional_city", "rural_periphery"]
REGION_SHARE0 = np.array([0.29, 0.20, 0.30, 0.21])        # assumption (see README)
_REGION_FERT_RAW = np.array([0.85, 0.95, 1.00, 1.15])      # Tokyo TFR 0.96 vs national 1.15 (2024)
REGION_FERT = _REGION_FERT_RAW / float(REGION_SHARE0 @ _REGION_FERT_RAW)   # national TFR preserved at t0
REGION_WAGE = np.array([1.25, 1.10, 0.95, 0.80])
# annual out-migration probability of unmarried 18-30 year olds: origin -> {dest: p}   (assumption)
MIGRATION = {
    0: {1: 0.003, 2: 0.006},
    1: {0: 0.020, 2: 0.006},
    2: {1: 0.030, 0: 0.035, 3: 0.004},
    3: {2: 0.055, 1: 0.010, 0: 0.015},
}
MAX_AGE = 120
MORT_C = 0.130      # Gompertz slope; fitted to the IPSS 65+ and 75+ shares 2025-2070 (scripts/calibrate_mortality.py)
TFR_ASFR_TABLE = 5 * sum(D.ASFR_2020.values())             # 1.325

# ----------------------------------------------------------------------------- parameters


@dataclass(frozen=True)
class Params:
    n_agents: int = 50000
    years: int = 50
    start_year: int = 2020
    # --- policy levers, phased in linearly from `policy_start` over `policy_ramp` years
    policy_start: int = 2025
    policy_ramp: int = 10
    tfr_delta: float = 0.0              # added to the IPSS-medium TFR path
    net_immigration: float = float(D.IPSS_FOREIGN_NET_INFLOW)   # persons / year
    marriage_mult: float = 1.0          # multiplies lifetime-ever-married share (capped at 0.98)
    retirement_age: int = 65            # contribution stops / pension starts
    migration_mult: float = 1.0         # multiplies rural->city and regional->metro flows
    # --- baseline (IPSS variants)
    tfr_longrun: float = 1.36           # 1.13 low / 1.36 medium / 1.64 high
    longevity_mult: float = 1.0         # 1.0 = IPSS mortality-medium e0 gains
    first_marriage_sd: float = 4.8      # assumption
    # --- economy and public finance (phased in with the same ramp)
    tax_consumption: float = 10.0       # consumption tax rate, %
    tax_other_pct: float = 0.0          # change in income/corporate/other tax revenue vs baseline, %
    contribution_gdp_pct: float = 0.0   # extra contribution revenue as % of GDP (replaces general-account transfer)
    long_yield: float = 2.5             # long-run 10y yield, % (2026: 2.6, converges over 4 years)
    inflation: float = 2.0              # long-run inflation, % (2025: 3.3, 2026: 2.4)
    productivity: float = 0.9           # annual productivity growth, %


# ----------------------------------------------------------------------------- mortality


def _surv_table(A, B, c, shift):
    ages = np.arange(MAX_AGE + 1)
    q = 1.0 - np.exp(-(A + B * np.exp(c * (ages - shift))))
    q[-1] = 1.0
    return q


def _e0(q):
    S = np.cumprod(np.r_[1.0, 1.0 - q[:-1]])
    return float(np.sum(S * (1.0 - 0.5 * q)))


def _bisect(f, lo, hi, target, n=80, increasing=True):
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        v = f(mid)
        if (v < target) == increasing:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@lru_cache(maxsize=1)
def mortality_params(A: float = 3e-4, c: float = None):
    """Gompertz-Makeham hazard h = A + B*exp(c*(age - shift)), per sex.

    B is solved so that period e0(2020) matches IPSS; `shift` so that e0(2070) matches IPSS.
    """
    c = MORT_C if c is None else c
    out = {}
    for s, name in enumerate(("M", "F")):
        B = _bisect(lambda lb: _e0(_surv_table(A, 10 ** lb, c, 0.0)), -9.0, -2.0,
                    D.IPSS_E0_2020[name], increasing=False)
        B = 10 ** B
        shift = _bisect(lambda sh: _e0(_surv_table(A, B, c, sh)), 0.0, 40.0,
                        D.IPSS_E0_2070[name], increasing=True)
        out[s] = (A, B, c, shift)
    return out


def q_table(year_offset: float, longevity_mult: float = 1.0):
    """Annual death probability, shape (2, MAX_AGE+1), for `year_offset` years after 2020."""
    mp = mortality_params()
    f = min(year_offset, 50.0) / 50.0
    return np.vstack([_surv_table(A, B, c, shift * f * longevity_mult) for (A, B, c, shift) in (mp[0], mp[1])])


# ----------------------------------------------------------------------------- marriage


def _phi(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


@lru_cache(maxsize=64)
def marriage_tables(mult: float = 1.0, sd: float = 4.8):
    """First-marriage hazard H[sex, age] and ever-married share at START of each age.

    The age-at-first-marriage density is Normal(mean_age, sd) scaled to the lifetime
    ever-married share, so the lifetime unmarried rate (26.6% M / 16.5% F in 2020)
    and the mean marriage age (31.1 / 29.7) are matched by construction.
    """
    H = np.zeros((2, MAX_AGE + 1))
    ever_start = np.zeros((2, MAX_AGE + 1))
    for s, name in enumerate(("M", "F")):
        mu = D.MEAN_AGE_FIRST_MARRIAGE[name]
        ever = min(0.98, (1.0 - D.LIFETIME_UNMARRIED_2020[name]) * mult)
        ages = np.arange(MAX_AGE + 1)
        f = ever * np.array([_phi((a + 1 - mu) / sd) - _phi((a - mu) / sd) for a in ages])
        f[ages < 16] = 0.0
        cum = np.cumsum(f)
        ever_start[s, 1:] = cum[:-1]
        surv = 1.0 - ever_start[s]
        H[s] = np.where(surv > 1e-9, np.clip(f / np.maximum(surv, 1e-9), 0, 1), 0.0)
    return H, ever_start


# ----------------------------------------------------------------------------- fertility


def _asfr_single():
    a = np.zeros(MAX_AGE + 1)
    for lo, rate in D.ASFR_2020.items():
        hi = 50 if lo == 45 else lo + 5
        a[lo:hi] = rate
    return a


ASFR = _asfr_single()


def tfr_path(year: int, longrun: float) -> float:
    """IPSS-medium-like period TFR: 1.33 (2020) -> 1.26 (2023) -> ~1.29 (2028) -> longrun (2070).
    The 2023/2028 anchors are an approximate reading of IPSS's statement that TFR stays
    below 1.3 until 2028 (see README, 'known approximations')."""
    anchors = [(2020, 1.33), (2023, 1.26), (2028, 1.29), (2070, longrun)]
    xs, ys = zip(*anchors)
    return float(np.interp(year, xs, ys))


def imm_path(year: int) -> float:
    """Baseline net immigration (persons/yr): ramps from a COVID-depressed level in 2020 to the
    IPSS-stated 163,791 in 2040 and stays flat. The 2020 value (60k) is an ASSUMPTION; IPSS states
    only the 2040 level (see README, 'known approximations')."""
    return float(np.interp(year, [2020, 2040], [60_000.0, float(D.IPSS_FOREIGN_NET_INFLOW)]))


# ----------------------------------------------------------------------------- simulation


class Result(dict):
    """dict of numpy arrays indexed by year (length years+1), plus `.params`."""
    params: Params


def _ramp(year, p: Params):
    if year < p.policy_start:
        return 0.0
    return float(np.clip((year - p.policy_start + 1) / max(1, p.policy_ramp), 0.0, 1.0))


def _initial_population(p: Params, rng, Q0, ever_start):
    """Sample agents from the 2020 population pyramid (5-year age x sex), uniform within each band."""
    cells, probs = [], []
    split_tot = float(sum(D.POP_85PLUS_SPLIT.values()))
    for lo, (m, f) in D.POP_PYRAMID_2020.items():
        if lo == "85+":
            for lo2, th in D.POP_85PLUS_SPLIT.items():
                share = th / split_tot
                cells += [(lo2, 0), (lo2, 1)]; probs += [m * share, f * share]
        else:
            cells += [(lo, 0), (lo, 1)]; probs += [m, f]
    probs = np.array(probs, dtype=float); probs /= probs.sum()
    idx = rng.choice(len(cells), size=p.n_agents, p=probs)
    lo = np.array([cells[i][0] for i in range(len(cells))])[idx]
    sex = np.array([cells[i][1] for i in range(len(cells))], dtype=np.int8)[idx]
    age = np.minimum(lo + rng.integers(0, 5, size=p.n_agents), MAX_AGE).astype(np.int16)
    region = rng.choice(4, size=p.n_agents, p=REGION_SHARE0).astype(np.int8)
    married = rng.random(p.n_agents) < ever_start[sex, age]
    return age, sex, region, married


def run(params: Params = Params(), seed: int = 0) -> Result:
    p = params
    rng = np.random.default_rng(seed)
    weight = D.POP_2020 / p.n_agents
    H0, ever0 = marriage_tables(1.0, p.first_marriage_sd)
    Q0 = q_table(0.0, p.longevity_mult)
    age, sex, region, married = _initial_population(p, rng, Q0, ever0)
    M0_end = np.vstack([np.r_[ever0[s, 1:], 1.0] for s in range(2)])   # ever-married share at END of age a
    nm = D.BIRTHS_OUTSIDE_MARRIAGE

    T = p.years
    cols = ["pop", "share_0_14", "share_15_64", "share_65p", "dependency", "share_75p", "workers",
            "retirees", "lr", "lr65", "labor_index", "tokyo_share", "rural_share", "births", "deaths",
            "immigrants", "tfr_realized", "tfr_target", "marriages", "b0", "b1", "b2", "b3", "b4"]
    out = {c: np.full(T + 1, np.nan) for c in cols}
    out["year"] = np.arange(p.start_year, p.start_year + T + 1)
    labor_ref = None

    def record(i, year, ret, births=np.nan, deaths=np.nan, imm=np.nan, tfr_real=np.nan, tfr_t=np.nan, marr=np.nan):
        nonlocal labor_ref
        n = age.size
        a = age
        c014 = (a < 15).sum(); c1564 = ((a >= 15) & (a < 65)).sum(); c65 = (a >= 65).sum()
        w = ((a >= 20) & (a < ret)).sum(); r = (a >= ret).sum()
        w65 = ((a >= 20) & (a < 65)).sum(); r65 = (a >= 65).sum()
        labor = REGION_WAGE[region[(a >= 20) & (a < ret)]].sum()
        if labor_ref is None:
            labor_ref = REGION_WAGE[region[(a >= 20) & (a < 65)]].sum()
        out["pop"][i] = n * weight
        out["share_0_14"][i] = 100 * c014 / n; out["share_15_64"][i] = 100 * c1564 / n
        out["share_65p"][i] = 100 * c65 / n
        out["dependency"][i] = 100 * (c014 + c65) / max(1, c1564)
        out["share_75p"][i] = 100 * (a >= 75).sum() / n
        out["workers"][i] = w * weight; out["retirees"][i] = r * weight
        out["lr"][i] = w / max(1, r); out["lr65"][i] = w65 / max(1, r65)
        out["labor_index"][i] = 100 * labor / labor_ref
        out["tokyo_share"][i] = 100 * (region == 0).mean(); out["rural_share"][i] = 100 * (region == 3).mean()
        out["births"][i] = births * weight if births == births else np.nan
        out["deaths"][i] = deaths * weight if deaths == deaths else np.nan
        out["immigrants"][i] = imm * weight if imm == imm else np.nan
        out["tfr_realized"][i] = tfr_real; out["tfr_target"][i] = tfr_t; out["marriages"][i] = marr
        for j, (lo_, hi_) in enumerate(((0, 15), (15, 45), (45, 65), (65, 75), (75, 200))):
            out[f"b{j}"][i] = ((a >= lo_) & (a < hi_)).sum() * weight

    record(0, p.start_year, 65)
    for step in range(T):
        year = p.start_year + step
        r = _ramp(year, p)
        ret = int(round(65 + (p.retirement_age - 65) * r))
        mmult = 1.0 + (p.marriage_mult - 1.0) * r
        mig_mult = 1.0 + (p.migration_mult - 1.0) * r
        imm_rate = imm_path(year) + (p.net_immigration - D.IPSS_FOREIGN_NET_INFLOW) * r
        tfr_t = tfr_path(year, p.tfr_longrun) + p.tfr_delta * r
        H, _ = marriage_tables(round(mmult, 3), p.first_marriage_sd)
        Q = q_table(step, p.longevity_mult)

        # 1. death
        alive = rng.random(age.size) >= Q[sex, age]
        n_dead = int((~alive).sum())
        age, sex, region, married = age[alive], sex[alive], region[alive], married[alive]
        # 2. first marriage
        marry = (~married) & (rng.random(age.size) < H[sex, age])
        married = married | marry
        # 3. regional migration of unmarried 18-30 year olds
        elig = np.where((~married) & (age >= 18) & (age <= 30))[0]
        if elig.size:
            u = rng.random(elig.size)
            reg_e = region[elig]
            new_reg = reg_e.copy()
            for o, edges in MIGRATION.items():
                m = reg_e == o
                cum = 0.0
                for d, pr in edges.items():
                    pr_eff = pr * (mig_mult if (o in (2, 3) and d != 3) else 1.0)   # scale flows OUT of regional/rural areas
                    sel = m & (u >= cum) & (u < cum + pr_eff)
                    new_reg[sel] = d
                    cum += pr_eff
            region[elig] = new_reg
        # 4. births
        wi = np.where((sex == 1) & (age >= 15) & (age <= 49))[0]
        fscale = tfr_t / TFR_ASFR_TABLE
        a_w = age[wi]
        base = ASFR[a_w] * fscale * REGION_FERT[region[wi]]
        m_end = np.clip(M0_end[1, a_w], 0.02, 0.98)
        p_birth = np.where(a_w < 20, base,
                           np.where(married[wi], base * (1 - nm) / m_end, base * nm / (1 - m_end)))
        p_birth = np.clip(p_birth, 0.0, 0.6)
        gave = rng.random(wi.size) < p_birth
        mothers = wi[gave]
        n_birth = int(mothers.size)
        # realised period TFR (sum of age-specific rates)
        births_by_age = np.bincount(a_w[gave], minlength=MAX_AGE + 1)
        women_by_age = np.bincount(a_w, minlength=MAX_AGE + 1)
        tfr_real = float(np.sum(births_by_age[15:50] / np.maximum(1, women_by_age[15:50])))
        new_age = np.zeros(n_birth, dtype=np.int16)
        new_sex = (rng.random(n_birth) < 0.488).astype(np.int8)
        new_reg = region[mothers]
        new_mar = np.zeros(n_birth, dtype=bool)
        # 5. immigration
        n_imm = int(rng.poisson(imm_rate / weight))
        imm_age = rng.integers(20, 40, size=n_imm).astype(np.int16)
        imm_sex = (rng.random(n_imm) < 0.5).astype(np.int8)
        imm_reg = rng.choice(4, size=n_imm, p=[0.55, 0.25, 0.20, 0.0]).astype(np.int8)
        imm_mar = rng.random(n_imm) < _ever_start_base(imm_sex, imm_age, p.first_marriage_sd)
        # 6. age + 1 for everyone who was alive at the start of the year, THEN add newborns at age 0
        #    (adding them first made every newborn 1 year old at year end and emptied the age-0 cohort)
        age = np.minimum(age + 1, MAX_AGE).astype(np.int16)
        age = np.concatenate([age, new_age, imm_age]); sex = np.concatenate([sex, new_sex, imm_sex])
        region = np.concatenate([region, new_reg, imm_reg]); married = np.concatenate([married, new_mar, imm_mar])
        record(step + 1, year + 1, ret, n_birth, n_dead, n_imm, tfr_real, tfr_t, int(marry.sum()) * weight)

    # pension pressure index: pay-as-you-go with a fixed contribution rate => replacement ∝ workers/retirees.
    k = D.PENSION_REPL_2024 / out["lr65"][2024 - p.start_year]
    out["pressure_index"] = k * out["lr"]          # v0.1 index, kept for reference
    out.update(fiscal(out, p))
    out["replacement"] = out["f_repl"]             # replacement rate with the macro-economic slide (floor 50%)
    res = Result(out)
    res.params = p
    return res


def _ever_start_base(sex, age, sd):
    _, ever = marriage_tables(1.0, sd)
    return ever[sex, np.clip(age, 0, MAX_AGE)]


def run_many(params: Params = Params(), n_runs: int = 20, seed0: int = 0) -> dict:
    """Stack replicate runs -> dict of arrays shaped (n_runs, years+1)."""
    runs = [run(params, seed0 + i) for i in range(n_runs)]
    stacked = {k: np.vstack([r[k] for r in runs]) for k in runs[0] if k != "year"}
    stacked["year"] = runs[0]["year"]
    return stacked


def band(stacked: dict, key: str, lo: float = 10, hi: float = 90):
    x = stacked[key]
    return np.nanmean(x, 0), np.nanpercentile(x, lo, 0), np.nanpercentile(x, hi, 0)


def with_(p: Params, **kw) -> Params:
    return replace(p, **kw)
