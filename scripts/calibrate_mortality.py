"""Fit the Gompertz slope c (and nothing else) so that the 65+ and 75+ population shares match IPSS 2025-2070.
e0 targets are matched exactly for every c by construction (B and shift are solved per sex).
Held out (NOT fitted): total population, 0-14 and 15-64 shares, dependency ratio."""
import sys, numpy as np
import jpabm.model as M
from jpabm import Params, run_many, data as D

def loss(c, n=60000, reps=3):
    M.MORT_C = c; M.mortality_params.cache_clear()
    R = run_many(Params(n_agents=n), reps, seed0=100)
    m75 = np.nanmean(R["share_75p"], 0); m65 = np.nanmean(R["share_65p"], 0)
    ys = (2025,2030,2035,2040,2045,2050,2055,2060,2065,2070)
    return sum((m75[y-2020]-D.IPSS_75PLUS[y])**2 + (m65[y-2020]-D.IPSS_AGE_SHARE[y][2])**2 for y in ys)

if __name__ == "__main__":
    cs = [0.100,0.110,0.120,0.130,0.140,0.150,0.160]
    res = [(loss(c), c) for c in cs]
    for l, c in res: print("c=%.3f  SSE=%.2f" % (c, l))
    print("best c:", min(res)[1])
