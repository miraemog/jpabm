"""Policy experiments on equal footing (population) and one-at-a-time (economy). Writes experiments.json.
The web simulator's comparison table is generated from this file."""
import json, numpy as np
from jpabm import Params, run_many, data as D

N, R, S = 100_000, 20, 2000
F = D.IPSS_FOREIGN_NET_INFLOW
SC = {
 "base":     Params(n_agents=N),
 "imm10":    Params(n_agents=N, net_immigration=F + 100_000),
 "births10": Params(n_agents=N, tfr_delta=0.18),
 "marr10":   Params(n_agents=N, marriage_mult=1.10),
 "ret68":    Params(n_agents=N, retirement_age=68),
 "trend":    Params(n_agents=N, tfr_delta=-0.13),
 "demo3":    Params(n_agents=N, tfr_delta=0.18, net_immigration=F + 100_000, retirement_age=68),
 "tax15":    Params(n_agents=N, tax_consumption=15),
 "prem1":    Params(n_agents=N, contribution_gdp_pct=1.0),
 "yld4":     Params(n_agents=N, long_yield=4.0),
 "infl3":    Params(n_agents=N, inflation=3.0),
 "infl3y35": Params(n_agents=N, inflation=3.0, long_yield=3.5),
 "prod15":   Params(n_agents=N, productivity=1.5),
 "prod0":    Params(n_agents=N, productivity=0.0),
}
if __name__ == "__main__":
    out = {}
    res = {k: run_many(p, R, S) for k, p in SC.items()}
    b = np.nanmean(res["base"]["births"], 0)
    for k, r in res.items():
        m = lambda key: np.nanmean(r[key], 0)
        out[k] = dict(pop70=float(m("pop")[50] / 1e6), dep70=float(m("dependency")[50]), real70=float(m("f_real")[50]),
                      debt70=float(m("f_debtgdp")[50]), it50=float(m("f_inttax")[30]), repl60=float(m("replacement")[40]),
                      pb50=float(m("f_pb")[30]), ben50=float(m("f_benpct")[30]),
                      extra_births_2031_40=float(np.nanmean((m("births") - b)[11:21])))
    json.dump(out, open("experiments.json", "w"), indent=1, ensure_ascii=False)
    for k, v in out.items(): print(k.ljust(9), {a: round(x, 1) for a, x in v.items()})
