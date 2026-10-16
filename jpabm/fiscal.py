"""Economy and public finance block (annual, from fiscal 2024).

Real GDP = labour input x productivity. Prices, tax rates and yields are scenario inputs.
Anchors are published FY2024-26 figures (Ministry of Finance, IPSS, MHLW); see README for the list.
Scope: national general account and ordinary government bonds (not local government, reserve fund or special accounts).
Growth does not depend on tax, interest rates or inflation (a stated limitation).
"""
from __future__ import annotations
import numpy as np

N0 = 642.4            # nominal GDP FY2024, trillion yen (= social benefits 138.3 / 21.53%)
TAXC0 = 25.0          # consumption tax revenue FY2024
KO = 0.0873           # income + corporate + other taxes, share of nominal GDP (FY2025 outturn 58.2)
PEN0, MED0, WEL0 = 57.8528, 44.8055, 35.6436           # benefits FY2024 (IPSS)
CB = (16.4, 13.3, 29.1, 57.3, 92.3)                    # medical cost per head by age band, 10k yen (FY2021)
SOC26, OTH26 = 39.0559, 46.1                           # FY2026 budget: national social security, other primary spending
D24, D25 = 1079.7, 1104.3                              # ordinary government bonds outstanding
R24, R25 = 0.83, 0.98                                  # average interest rate (%)
KAPPA, SPEED, X25 = 0.87, 0.23, 14.4
REPL0, FLOOR = 0.612, 0.50
I0 = 4                                                 # index of 2024 when the run starts in 2020

KEYS = ["gdp", "real", "tax", "taxc", "ben", "benpct", "repl", "pb", "debt", "debtgdp", "intr", "inttax", "rav", "gn", "infl", "yld", "soc"]


def _ramp(y, start, ramp):
    return 0.0 if y < start else min(1.0, max(0.0, (y - start + 1) / max(1, ramp)))


def fiscal(out: dict, p) -> dict:
    """`out` needs: labor_index, workers, retirees, b0..b4 (persons by age band). Returns dict of f_* arrays."""
    T = len(out["labor_index"])
    f = {k: np.zeros(T) for k in KEYS}
    lab, nw, nr = out["labor_index"], out["workers"], out["retirees"]
    b = [out[f"b{j}"] for j in range(5)]
    ramp = lambda y: _ramp(y, p.policy_start, p.policy_ramp)
    cohort = lambda i: sum(CB[j] * b[j][i] for j in range(5))
    infl_base = lambda y: 3.3 if y == 2025 else (2.4 if y == 2026 else 2.0)
    P = A = 1.0; Y = N0; Rprev = REPL0; ben_pc = 0.0
    med_k = pop_a = pop014_a = pop65_a = B26 = 0.0; P5 = 1.0
    rows = []
    for i in range(I0, T):
        y = p.start_year + i; r = ramp(y)
        pi = (infl_base(y) if y <= 2026 else 2.0 + r * (p.inflation - 2.0)) / 100
        ylr = 2.5 + r * (p.long_yield - 2.5)
        yl = 1.0 if y <= 2024 else (1.6 if y == 2025 else 2.6 + (ylr - 2.6) * min(1.0, (y - 2026) / 4))
        pg = 0.0 if y <= 2024 else (0.9 + r * (p.productivity - 0.9)) / 100
        if i > I0:
            Y *= (lab[i] / lab[i - 1]) * (1 + pg); P *= 1 + pi; A *= 1 + pg
        N = Y * P; W = A * P
        pop = sum(b[j][i] for j in range(5)); pop65 = b[3][i] + b[4][i]
        if i == I0:
            med_k = MED0 / cohort(i); pop_a = pop; pop014_a = b[0][i]; pop65_a = pop65; ben_pc = PEN0 / nr[i]
        slide = 0.0
        if i > I0:
            gw = (1 + pg) * (1 + pi) - 1; gk = nw[i] / nw[i - 1] - 1
            slide = max(0.0, -gk + 0.003) if Rprev > FLOOR else 0.0
            ben_pc *= 1 + max(0.0, gw - slide)
        Rr = REPL0 * (ben_pc / (PEN0 / nr[I0])) / W; Rprev = Rr
        pen = nr[i] * ben_pc; med = med_k * W * cohort(i)
        wel = WEL0 * W * (0.55 * pop65 / pop65_a + 0.25 * b[0][i] / pop014_a + 0.20 * pop / pop_a)
        B = pen + med + wel
        tc = TAXC0 * ((10 + r * (p.tax_consumption - 10)) / 10) * N / N0
        to = KO * N * (1 + r * p.tax_other_pct / 100); tax = tc + to
        rows.append(dict(i=i, y=y, N=N, P=P, B=B, tax=tax, yl=yl))
        f["gdp"][i] = N; f["real"][i] = 100 * Y / N0; f["tax"][i] = tax; f["taxc"][i] = tc; f["ben"][i] = B
        f["benpct"][i] = 100 * B / N; f["repl"][i] = 100 * Rr; f["infl"][i] = 100 * pi; f["yld"][i] = yl
        if i == 6: B26 = B
        if i == 5: P5 = P
    P6 = rows[2]["P"]
    D = D24; rav = R24
    for row in rows:
        i, y = row["i"], row["y"]; r = ramp(y)
        other = OTH26 * row["P"] / P6
        s = max(0.0, SOC26 * row["B"] / B26 - r * p.contribution_gdp_pct / 100 * row["N"])
        pb = row["tax"] - s - other
        if i == I0:
            D = D24; rav = R24; f["intr"][i] = 7.9
        elif i == I0 + 1:
            D = D25; rav = R25; f["intr"][i] = 9.4
        else:
            rav = rav + SPEED * (row["yl"] - rav)
            it = KAPPA * D * rav / 100; f["intr"][i] = it
            D = D + it - pb + X25 * row["P"] / P5
        f["soc"][i] = s; f["pb"][i] = 100 * pb / row["N"]; f["debt"][i] = D; f["debtgdp"][i] = 100 * D / row["N"]
        f["inttax"][i] = 100 * f["intr"][i] / row["tax"]; f["rav"][i] = rav
        f["gn"][i] = 100 * (row["N"] / rows[i - 1 - I0]["N"] - 1) if i > I0 else 0.0
    for k in KEYS:
        f[k][:I0] = f[k][I0]
    return {f"f_{k}": v for k, v in f.items()}
