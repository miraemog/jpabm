"""Official reference data used for calibration and validation.

Every number here was read from a public source during development (see SOURCES).
Nothing in this file is tuned: it is the yardstick the model is judged against.
"""

YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070]

# IPSS "Population Projections for Japan (2023 revision)", fertility-medium / mortality-medium.
# Age shares in percent: (0-14, 15-64, 65+)   [IPSS Population Statistics 2023 rev., Table 2-8]
IPSS_AGE_SHARE = {
    2020: (11.9, 59.5, 28.6), 2025: (11.1, 59.3, 29.6), 2030: (10.3, 58.9, 30.8),
    2035: (10.0, 57.6, 32.3), 2040: (10.1, 55.1, 34.8), 2045: (10.1, 53.6, 36.3),
    2050: (9.9, 52.9, 37.1), 2055: (9.6, 52.8, 37.6), 2060: (9.3, 52.8, 37.9),
    2065: (9.1, 52.5, 38.4), 2070: (9.2, 52.1, 38.7),
}
# Total dependency index = (0-14 + 65+) / (15-64) * 100        [Table 2-8]
IPSS_DEPENDENCY = {2020: 68.0, 2025: 68.6, 2030: 69.8, 2035: 73.5, 2040: 81.6, 2045: 86.5,
                   2050: 89.0, 2055: 89.4, 2060: 89.3, 2065: 90.4, 2070: 91.8}
# Total population, thousands                                    [Table 2-9]
IPSS_POP_K = {2020: 126146, 2025: 123262, 2030: 120116, 2035: 116639, 2040: 112837,
              2045: 108801, 2050: 104686, 2055: 100508, 2060: 96148, 2065: 91587, 2070: 86996}
# Share aged 75+ in percent                                      [Table 2-9]
IPSS_75PLUS = {2020: 14.7, 2025: 17.5, 2030: 18.8, 2035: 19.2, 2040: 19.7, 2045: 20.9,
               2050: 23.2, 2055: 24.7, 2060: 25.3, 2065: 25.3, 2070: 25.1}

# Period age-specific fertility, births per woman-year, 2020      [IPSS Table 4-7 / MHLW vital stats]
ASFR_2020 = {15: 0.0025, 20: 0.0230, 25: 0.0747, 30: 0.0973, 35: 0.0553, 40: 0.0118, 45: 0.0004}
# (5-year bands; TFR = 5 * sum = 1.325, consistent with the reported 1.33)

# IPSS assumptions (medium variant unless noted)
IPSS_TFR_2020 = 1.33
IPSS_TFR_LONGRUN = {"low": 1.13, "medium": 1.36, "high": 1.64}      # reached by 2070
IPSS_E0_2020 = {"M": 81.58, "F": 87.72}
IPSS_E0_2070 = {"M": 85.89, "F": 91.94}
IPSS_FOREIGN_NET_INFLOW = 163_791   # persons/year, reached in 2040 (medium)
POP_2020 = 126_146_000

# Marriage (MHLW 2024 / MIC 2020 census, via public summaries)
MEAN_AGE_FIRST_MARRIAGE = {"M": 31.1, "F": 29.7}
LIFETIME_UNMARRIED_2020 = {"M": 0.266, "F": 0.165}
BIRTHS_OUTSIDE_MARRIAGE = 0.02      # "only a few out of every 100 babies" (approximation)

# Pension: 2024 Actuarial Valuation (財政検証) income replacement rate
PENSION_REPL_2024 = 61.2
PENSION_REPL_2060 = {"growth": 57.6, "past30": 50.4}

SOURCES = {
    "IPSS Population Projections 2023 rev.": "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2023RE/T02-08.files/sheet001.htm",
    "IPSS total population by age group": "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2023RE/T02-09.files/sheet001.htm",
    "IPSS age-specific fertility": "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2023RE/T04-07.files/sheet001.htm",
    "MHLW summary of 2023 projections (TFR/e0/migration assumptions)": "https://www.mhlw.go.jp/wp/hakusyo/kousei/25-2/dl/01.pdf",
    "NRI note on 2024 pension actuarial valuation": "https://www.nri.com/jp/knowledge/blog/lst/2024/fis/kiuchi/0703_2",
}

# Population by 5-year age group and sex, 1 July 2020 (persons).
# Secondary source: Wikipedia "Demographics of Japan", citing IPSS / Statistics Bureau.
# (85+ is split 85-89/90-94/95-99/100+ in the ratio 3717/1822/519/76 thousand.)
POP_PYRAMID_2020 = {
    0: (2406000, 2288000), 5: (2580000, 2462000), 10: (2736000, 2605000), 15: (2932000, 2792000),
    20: (3298000, 3089000), 25: (3240000, 3036000), 30: (3391000, 3244000), 35: (3767000, 3665000),
    40: (4289000, 4183000), 45: (4954000, 4847000), 50: (4353000, 4305000), 55: (3905000, 3913000),
    60: (3674000, 3770000), 65: (4047000, 4305000), 70: (4288000, 4798000), 75: (3193000, 3953000),
    80: (2239000, 3159000), "85+": (1856000, 3776000),
}
POP_85PLUS_SPLIT = {85: 3717, 90: 1822, 95: 519, 100: 76}   # thousands, 5-year bands
SOURCES["2020 population pyramid (secondary)"] = "https://en.wikipedia.org/wiki/Demographics_of_Japan"
