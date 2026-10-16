/* jpabm-js: JavaScript port of the Python model (jpabm/model.py). Same equations, same calibration. */
const JPABM = (function () {
  const MAXAGE = 120, YEAR0 = 2020;
  const POP_2020 = 126146000, FOREIGN_2040 = 163791;
  const ASFR_BANDS = { 15: 0.0025, 20: 0.0230, 25: 0.0747, 30: 0.0973, 35: 0.0553, 40: 0.0118, 45: 0.0004 };
  const TFR_TABLE = 5 * Object.values(ASFR_BANDS).reduce((a, b) => a + b, 0);
  const ASFR = new Float64Array(MAXAGE + 1);
  for (const lo of Object.keys(ASFR_BANDS)) { const l = +lo, h = l === 45 ? 50 : l + 5; for (let a = l; a < h; a++) ASFR[a] = ASFR_BANDS[lo]; }
  const PYRAMID = [[0, 2406000, 2288000], [5, 2580000, 2462000], [10, 2736000, 2605000], [15, 2932000, 2792000], [20, 3298000, 3089000],
    [25, 3240000, 3036000], [30, 3391000, 3244000], [35, 3767000, 3665000], [40, 4289000, 4183000], [45, 4954000, 4847000],
    [50, 4353000, 4305000], [55, 3905000, 3913000], [60, 3674000, 3770000], [65, 4047000, 4305000], [70, 4288000, 4798000],
    [75, 3193000, 3953000], [80, 2239000, 3159000]];
  const P85 = [[85, 3717], [90, 1822], [95, 519], [100, 76]], P85M = 1856000, P85F = 3776000;
  const REGION_SHARE0 = [0.29, 0.20, 0.30, 0.21];
  const FRAW = [0.85, 0.95, 1.0, 1.15];
  const FDEN = FRAW.reduce((s, v, i) => s + v * REGION_SHARE0[i], 0);
  const REGION_FERT = FRAW.map(v => v / FDEN);
  const REGION_WAGE = [1.25, 1.10, 0.95, 0.80];
  const MIGRATION = [[[1, 0.003], [2, 0.006]], [[0, 0.020], [2, 0.006]], [[1, 0.030], [0, 0.035], [3, 0.004]], [[2, 0.055], [1, 0.010], [0, 0.015]]];
  const MORT = { A: 3e-4, c: 0.13, B: [1.689936239133019e-06, 7.449900742893467e-07], shift: [4.421515844583247, 4.337088057810469] };
  const FIRST_MARR_MEAN = [31.1, 29.7], UNMARRIED = [0.266, 0.165], NONMAR = 0.02;
  const IPSS = {
    years: [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070],
    pop: [126.146, 123.262, 120.116, 116.639, 112.837, 108.801, 104.686, 100.508, 96.148, 91.587, 86.996],
    dep: [68.0, 68.6, 69.8, 73.5, 81.6, 86.5, 89.0, 89.4, 89.3, 90.4, 91.8],
    old: [28.6, 29.6, 30.8, 32.3, 34.8, 36.3, 37.1, 37.6, 37.9, 38.4, 38.7],
  };

  function rng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function erf(x) { const s = x < 0 ? -1 : 1; x = Math.abs(x); const t = 1 / (1 + 0.3275911 * x);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return s * y; }
  const phi = x => 0.5 * (1 + erf(x / Math.SQRT2));
  function poisson(lam, r) { if (lam > 200) { const u1 = r() || 1e-12, u2 = r(); return Math.max(0, Math.round(lam + Math.sqrt(lam) * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2))); }
    const L = Math.exp(-lam); let k = 0, p = 1; do { k++; p *= r(); } while (p > L); return k - 1; }

  const qCache = new Map();
  function qTable(step, longev) {
    const key = Math.min(step, 50) + '|' + longev; if (qCache.has(key)) return qCache.get(key);
    const f = Math.min(step, 50) / 50, q = new Float64Array(2 * (MAXAGE + 1));
    for (let s = 0; s < 2; s++) for (let a = 0; a <= MAXAGE; a++) {
      q[s * 121 + a] = a === MAXAGE ? 1 : 1 - Math.exp(-(MORT.A + MORT.B[s] * Math.exp(MORT.c * (a - MORT.shift[s] * f * longev)))); }
    qCache.set(key, q); return q;
  }
  const mCache = new Map();
  function marriageTables(mult, sd) {
    const key = mult.toFixed(3) + '|' + sd; if (mCache.has(key)) return mCache.get(key);
    const H = new Float64Array(2 * 121), ever = new Float64Array(2 * 121);
    for (let s = 0; s < 2; s++) { const mu = FIRST_MARR_MEAN[s], e = Math.min(0.98, (1 - UNMARRIED[s]) * mult); let cum = 0;
      for (let a = 0; a <= MAXAGE; a++) { const f = a < 16 ? 0 : e * (phi((a + 1 - mu) / sd) - phi((a - mu) / sd));
        ever[s * 121 + a] = cum; const surv = 1 - cum; H[s * 121 + a] = surv > 1e-9 ? Math.min(1, Math.max(0, f / surv)) : 0; cum += f; } }
    const out = { H, ever }; mCache.set(key, out); return out;
  }
  function tfrPath(year, longrun) { const xs = [2020, 2023, 2028, 2070], ys = [1.33, 1.26, 1.29, longrun];
    if (year <= xs[0]) return ys[0]; if (year >= xs[3]) return ys[3];
    for (let i = 0; i < 3; i++) if (year <= xs[i + 1]) return ys[i] + (ys[i + 1] - ys[i]) * (year - xs[i]) / (xs[i + 1] - xs[i]); return ys[3]; }
  function immPath(year) { return year >= 2040 ? FOREIGN_2040 : 60000 + (FOREIGN_2040 - 60000) * (year - 2020) / 20; }

  const DEFAULTS = { n: 40000, years: 50, policyStart: 2025, policyRamp: 10, tfrDelta: 0, netImm: FOREIGN_2040, marriageMult: 1, retAge: 65,
    migMult: 1, tfrLongrun: 1.36, longevMult: 1, marrSd: 4.8,
    taxC: 10, taxOth: 0, prem: 0, infl: 2.0, yld: 2.5, prod: 0.9 };

  function run(user, seed) {
    const p = Object.assign({}, DEFAULTS, user), r = rng(seed), n0 = p.n, weight = POP_2020 / n0;
    const cap = Math.floor(n0 * 2.2) + 2000;
    let age = new Int16Array(cap), sex = new Uint8Array(cap), reg = new Uint8Array(cap), mar = new Uint8Array(cap), cnt = n0;
    const base = marriageTables(1, p.marrSd), M0end = new Float64Array(2 * 121);
    for (let s = 0; s < 2; s++) for (let a = 0; a <= MAXAGE; a++) M0end[s * 121 + a] = a === MAXAGE ? 1 : base.ever[s * 121 + a + 1];
    // initial population from the 2020 pyramid
    const cells = [], cum = []; let tot = 0;
    for (const [lo, m, f] of PYRAMID) { cells.push([lo, 0]); tot += m; cum.push(tot); cells.push([lo, 1]); tot += f; cum.push(tot); }
    const sp = P85.reduce((s, x) => s + x[1], 0);
    for (const [lo, th] of P85) { cells.push([lo, 0]); tot += P85M * th / sp; cum.push(tot); cells.push([lo, 1]); tot += P85F * th / sp; cum.push(tot); }
    for (let i = 0; i < n0; i++) { const u = r() * tot; let lo = 0, hi = cum.length - 1; while (lo < hi) { const mid = (lo + hi) >> 1; if (cum[mid] > u) hi = mid; else lo = mid + 1; }
      const c = cells[lo]; age[i] = Math.min(MAXAGE, c[0] + Math.floor(r() * 5)); sex[i] = c[1];
      const u2 = r(); let g = 0, acc = REGION_SHARE0[0]; while (u2 > acc && g < 3) { g++; acc += REGION_SHARE0[g]; } reg[i] = g;
      mar[i] = r() < base.ever[sex[i] * 121 + age[i]] ? 1 : 0; }
    const T = p.years, out = { pop: new Float64Array(T + 1), s014: new Float64Array(T + 1), s1564: new Float64Array(T + 1), s65: new Float64Array(T + 1),
      dep: new Float64Array(T + 1), lr: new Float64Array(T + 1), lr65: new Float64Array(T + 1), labor: new Float64Array(T + 1), tokyo: new Float64Array(T + 1), tfr: new Float64Array(T + 1),
      pyr: new Float32Array((T + 1) * 42), weight: weight,
      nw: new Float64Array(T + 1), nr: new Float64Array(T + 1), b0: new Float64Array(T + 1), b1: new Float64Array(T + 1), b2: new Float64Array(T + 1), b3: new Float64Array(T + 1), b4: new Float64Array(T + 1) };
    let laborRef = 0;
    function record(i, ret, tfrT) {
      let c014 = 0, c1564 = 0, c65 = 0, w = 0, rr = 0, w65 = 0, labor = 0, tk = 0, g1 = 0, g2 = 0, g3 = 0, g4 = 0;
      for (let k = 0; k < cnt; k++) { const a = age[k]; if (a < 15) c014++; else if (a < 65) c1564++; else c65++;
        if (a >= 20) { if (a < ret) { w++; labor += REGION_WAGE[reg[k]]; } else rr++; if (a < 65) w65++; }
        if (reg[k] === 0) tk++;
        if (a >= 15) { if (a < 45) g1++; else if (a < 65) g2++; else if (a < 75) g3++; else g4++; }
        out.pyr[i * 42 + sex[k] * 21 + (a >= 100 ? 20 : (a / 5) | 0)]++; }
      if (i === 0) { for (let k = 0; k < cnt; k++) if (age[k] >= 20 && age[k] < 65) laborRef += REGION_WAGE[reg[k]]; }
      out.pop[i] = cnt * weight; out.s014[i] = 100 * c014 / cnt; out.s1564[i] = 100 * c1564 / cnt; out.s65[i] = 100 * c65 / cnt;
      out.dep[i] = 100 * (c014 + c65) / Math.max(1, c1564); out.lr[i] = w / Math.max(1, rr); out.lr65[i] = w65 / Math.max(1, c65);
      out.labor[i] = 100 * labor / laborRef; out.tokyo[i] = 100 * tk / cnt; out.tfr[i] = tfrT;
      out.nw[i] = w * weight; out.nr[i] = rr * weight; out.b0[i] = c014 * weight; out.b1[i] = g1 * weight; out.b2[i] = g2 * weight; out.b3[i] = g3 * weight; out.b4[i] = g4 * weight;
    }
    record(0, 65, tfrPath(2020, p.tfrLongrun));
    const bornReg = new Uint8Array(cap);
    for (let step = 0; step < T; step++) {
      const year = YEAR0 + step;
      const ramp = year < p.policyStart ? 0 : Math.min(1, Math.max(0, (year - p.policyStart + 1) / Math.max(1, p.policyRamp)));
      const ret = Math.round(65 + (p.retAge - 65) * ramp), mm = 1 + (p.marriageMult - 1) * ramp, mig = 1 + (p.migMult - 1) * ramp;
      const imm = immPath(year) + (p.netImm - FOREIGN_2040) * ramp, tfrT = tfrPath(year, p.tfrLongrun) + p.tfrDelta * ramp;
      const H = marriageTables(Math.round(mm * 1000) / 1000, p.marrSd).H, Q = qTable(step, p.longevMult), fscale = tfrT / TFR_TABLE;
      let j = 0, nb = 0;
      for (let i = 0; i < cnt; i++) {
        const a = age[i], s = sex[i];
        if (r() < Q[s * 121 + a]) continue;
        let m = mar[i], g = reg[i];
        if (!m && r() < H[s * 121 + a]) m = 1;
        if (!m && a >= 18 && a <= 30) { const u = r(), edges = MIGRATION[g]; let c = 0;
          for (let e = 0; e < edges.length; e++) { const d = edges[e][0], pr = edges[e][1] * ((g === 2 || g === 3) && d !== 3 ? mig : 1); if (u >= c && u < c + pr) { g = d; break; } c += pr; } }
        if (s === 1 && a >= 15 && a <= 49) {
          const base_ = ASFR[a] * fscale * REGION_FERT[g]; let pb;
          if (a < 20) pb = base_; else { const me = Math.min(0.98, Math.max(0.02, M0end[121 + a])); pb = m ? base_ * (1 - NONMAR) / me : base_ * NONMAR / (1 - me); }
          if (pb > 0.6) pb = 0.6;
          if (r() < pb) bornReg[nb++] = g;
        }
        age[j] = Math.min(MAXAGE, a + 1); sex[j] = s; reg[j] = g; mar[j] = m; j++;
      }
      for (let b = 0; b < nb; b++) { age[j] = 0; sex[j] = r() < 0.488 ? 1 : 0; reg[j] = bornReg[b]; mar[j] = 0; j++; }
      const nimm = poisson(imm / weight, r);
      for (let b = 0; b < nimm && j < cap; b++) { const a = 20 + Math.floor(r() * 20), s = r() < 0.5 ? 1 : 0, u = r();
        age[j] = a; sex[j] = s; reg[j] = u < 0.55 ? 0 : (u < 0.80 ? 1 : 2); mar[j] = r() < base.ever[s * 121 + a] ? 1 : 0; j++; }
      cnt = j; record(step + 1, ret, tfrT);
    }
    fiscal(out, p);
    return out;
  }

  /* ---------------- economy and public finance (annual, from FY2024) ----------------
     Real GDP = labour input x productivity. Prices, tax rates and yields are scenario inputs.
     Anchors are published FY2024/25/26 figures; see the assumptions list on the page. */
  const FIS = {
    N0: 642.4,            // nominal GDP FY2024, trillion yen (= social benefits 138.3 / 21.53%)
    TAXC0: 25.0,          // consumption tax revenue FY2024 (26.03 in FY2025 is +4.0%)
    KO: 0.0873,           // income + corporate + other taxes as a share of nominal GDP (FY2025 outturn 58.2)
    PEN0: 57.8528, MED0: 44.8055, WEL0: 35.6436,   // benefits FY2024 (IPSS)
    CB: [16.4, 13.3, 29.1, 57.3, 92.3],            // medical cost per head by age band, 10k yen (FY2021)
    SOC26: 39.0559, OTH26: 46.1, PB26: 1.3,
    D24: 1079.7, D25: 1104.3, R24: 0.83, R25: 0.98, KAPPA: 0.87, SPEED: 0.23, X25: 14.4, REPL0: 0.612, FLOOR: 0.50
  };
  function fiscal(out, p) {
    const T = out.pop.length, i0 = 4, Z = () => new Float64Array(T);
    const f = { wage: Z(), price: Z(), gdp: Z(), real: Z(), tax: Z(), taxc: Z(), ben: Z(), benpct: Z(), repl: Z(), pb: Z(), debt: Z(), debtgdp: Z(), intr: Z(), inttax: Z(), rav: Z(), gn: Z(), infl: Z(), yld: Z(), soc: Z() };
    const ramp = y => y < p.policyStart ? 0 : Math.min(1, Math.max(0, (y - p.policyStart + 1) / Math.max(1, p.policyRamp)));
    let P = 1, A = 1, Y = FIS.N0, b = 0, Rprev = FIS.REPL0, D = FIS.D24, rav = FIS.R24, medK = 0, W0 = 1, popA = 0, pop014A = 0, pop65A = 0, B26 = 0, P5 = 1;
    const cohort = i => FIS.CB[0] * out.b0[i] + FIS.CB[1] * out.b1[i] + FIS.CB[2] * out.b2[i] + FIS.CB[3] * out.b3[i] + FIS.CB[4] * out.b4[i];
    const inflBase = y => y === 2025 ? 3.3 : y === 2026 ? 2.4 : 2.0;
    function yearly(i, tc, to) {}
    const rows = [];
    for (let i = i0; i < T; i++) {
      const y = 2020 + i, r = ramp(y);
      const pi = (y <= 2026 ? inflBase(y) : 2.0 + r * (p.infl - 2.0)) / 100;
      const ylr = 2.5 + r * (p.yld - 2.5), yl = y <= 2024 ? 1.0 : y === 2025 ? 1.6 : (2.6 + (ylr - 2.6) * Math.min(1, (y - 2026) / 4));
      const pg = y <= 2024 ? 0 : (0.9 + r * (p.prod - 0.9)) / 100;
      if (i > i0) { Y *= (out.labor[i] / out.labor[i - 1]) * (1 + pg); P *= 1 + (y === 2024 ? 0 : pi); A *= 1 + pg; }
      const N = Y * P, W = A * P;
      const pop = out.b0[i] + out.b1[i] + out.b2[i] + out.b3[i] + out.b4[i], pop65 = out.b3[i] + out.b4[i];
      if (i === i0) { medK = FIS.MED0 / cohort(i); popA = pop; pop014A = out.b0[i]; pop65A = pop65; b = FIS.PEN0 / out.nr[i]; }
      let slide = 0;
      if (i > i0) { const gw = (1 + pg) * (1 + pi) - 1, gk = out.nw[i] / out.nw[i - 1] - 1;
        slide = Rprev > FIS.FLOOR ? Math.max(0, -gk + 0.003) : 0; b *= 1 + Math.max(0, gw - slide); }
      const Rr = FIS.REPL0 * (b / (FIS.PEN0 / out.nr[i0])) / (W / 1); Rprev = Rr;
      const pen = out.nr[i] * b, med = medK * W * cohort(i);
      const wel = FIS.WEL0 * W * (0.55 * pop65 / pop65A + 0.25 * out.b0[i] / pop014A + 0.20 * pop / popA);
      const B = pen + med + wel;
      const tc = FIS.TAXC0 * ((10 + r * (p.taxC - 10)) / 10) * N / FIS.N0, to = FIS.KO * N * (1 + r * p.taxOth / 100), tax = tc + to;
      rows.push({ i, y, N, P, W, B, tc, to, tax, yl, pi, Rr, pop });
      f.wage[i] = 100 * A; f.price[i] = 100 * P; f.gdp[i] = N; f.real[i] = 100 * Y / FIS.N0; f.tax[i] = tax; f.taxc[i] = tc; f.ben[i] = B; f.benpct[i] = 100 * B / N; f.repl[i] = 100 * Rr; f.infl[i] = 100 * pi; f.yld[i] = yl;
      if (i === 6) B26 = B;
      if (i === 5) P5 = P;
    }
    // central budget
    const P6 = rows[2].P;
    const soc = (row, r) => Math.max(0, FIS.SOC26 * row.B / B26 - r * p.prem / 100 * row.N);
    for (const row of rows) {
      const i = row.i, y = row.y, r = ramp(y), other = FIS.OTH26 * row.P / P6;
      const s = soc(row, r), pb = row.tax - s - other;
      if (i === 4) { D = FIS.D24; rav = FIS.R24; f.intr[i] = 7.9; }
      else if (i === 5) { D = FIS.D25; rav = FIS.R25; f.intr[i] = 9.4; }
      else { rav = rav + FIS.SPEED * (row.yl - rav); const it = FIS.KAPPA * D * rav / 100; f.intr[i] = it; D = D + it - pb + FIS.X25 * row.P / P5; }
      f.soc[i] = s; f.pb[i] = 100 * pb / row.N; f.debt[i] = D; f.debtgdp[i] = 100 * D / row.N; f.inttax[i] = 100 * f.intr[i] / row.tax; f.rav[i] = rav;
      f.gn[i] = i > i0 ? 100 * (row.N / rows[i - 1 - i0].N - 1) : 0;
    }
    for (const k of Object.keys(f)) for (let i = 0; i < i0; i++) f[k][i] = f[k][i0];
    out.f = f; out.repl = f.repl;
    for (const k of Object.keys(f)) out['f_' + k] = f[k];
  }
  const KEYS = ['pop', 's014', 's1564', 's65', 'dep', 'repl', 'labor', 'tokyo', 'tfr', 'f_gdp', 'f_real', 'f_tax', 'f_taxc', 'f_ben', 'f_benpct', 'f_pb', 'f_debt', 'f_debtgdp', 'f_intr', 'f_inttax', 'f_rav', 'f_gn', 'f_infl', 'f_yld', 'f_soc', 'f_wage', 'f_price'];
  function stats(runs) {
    const T = runs[0].pop.length, res = {};
    for (const key of KEYS) { const mean = new Float64Array(T), lo = new Float64Array(T), hi = new Float64Array(T);
      for (let t = 0; t < T; t++) { const v = runs.map(x => x[key][t]).sort((a, b) => a - b); mean[t] = v.reduce((s, x) => s + x, 0) / v.length;
        lo[t] = v[Math.floor(0.1 * (v.length - 1))]; hi[t] = v[Math.ceil(0.9 * (v.length - 1))]; }
      res[key] = { mean, lo, hi }; }
    const P = new Float64Array(runs[0].pyr.length);
    for (const r of runs) for (let k = 0; k < P.length; k++) P[k] += r.pyr[k] * r.weight / runs.length;
    res.pyr = P;
    return res;
  }
  return { run, stats, IPSS, DEFAULTS, tfrPath, FOREIGN_2040, FIS };
})();
if (typeof module !== 'undefined') module.exports = JPABM;
