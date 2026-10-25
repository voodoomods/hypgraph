## Refusals replayed — 263: changed 29, language passes 30, passes 25, same 40, unknown 139

| refused as | same | changed | passes | language passes | unknown |
|---|---|---|---|---|---|
| `UNBOUND_NUMBER` | 15 | 9 | 0 | 27 | 96 |
| `SIGNIFICANCE_WITHOUT_TEST` | 18 | 14 | 17 | 22 | 0 |
| `ABSOLUTE_WITHOUT_COUNT` | 13 | 21 | 8 | 8 | 0 |
| `MEASUREMENT_UNKNOWN_FIELD` | 3 | 2 | 0 | 3 | 26 |
| `SIGNIFICANCE_NOT_SHOWN` | 0 | 0 | 0 | 1 | 28 |
| `MEASUREMENT_MALFORMED` | 1 | 1 | 0 | 2 | 9 |
| `EVIDENCE_MISSING` | 1 | 1 | 0 | 1 | 7 |
| `COMPARATIVE_WITHOUT_COMPARISON` | 10 | 0 | 0 | 0 | 0 |
| `MEASUREMENT_MISMATCH` | 0 | 0 | 0 | 0 | 4 |
| `EXCLUSION_WITHOUT_POWER` | 0 | 0 | 0 | 0 | 4 |
| `SCOPE_MISSING` | 0 | 0 | 0 | 0 | 1 |

### Would be treated differently now

- **changed** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → COMPARATIVE_WITHOUT_COMPARISON): “A leads B overall by only the small surplus in discordant cells, and the exact two-sided McNemar p-value is 0.416, far above 0.05. A is therefore NOT significan”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is not significantly more accurate than B at the 5% level: discordant cells are A>B 41 vs B>A 33 of 74 discordant pairs, exact two-sided McNemar p = 0.4160 > ”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is not significantly more accurate than B at the 5% level: discordant cells are A>B 41 vs B>A 33 of 74 discordant pairs, exact two-sided McNemar p = 0.4160 > ”
- **language passes** (MEASUREMENT_MALFORMED, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is not significantly more accurate than B at the 5% level: discordant cells are A>B 41 vs B>A 33 of 74 discordant pairs, exact two-sided McNemar p = 0.4160 > ”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is NOT significantly more accurate than B at the 5% level: discordant pairs are 41 (A correct/B wrong) vs 33 (B correct/A wrong); exact two-sided McNemar (bin”
- **language passes** (ABSOLUTE_WITHOUT_COUNT, UNBOUND_NUMBER → accepted): “Model A accuracy over all 856 items is 660/856 = 0.7710280373831776, and Model B accuracy is 652/856 = 0.7616822429906542. Both figures independently reproduced”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “A is not significantly more accurate than B at the 5% level: the exact two-sided McNemar p-value is 0.41599, above the 0.05 threshold, so the null hypothesis of”
- **changed** (ABSOLUTE_WITHOUT_COUNT, SIGNIFICANCE_WITHOUT_TEST → ABSOLUTE_WITHOUT_COUNT, COMPARATIVE_WITHOUT_COMPARISON): “A is not significantly more accurate than B: the exact two-sided McNemar p-value (0.41599) exceeds the 0.05 level, so the null of equal accuracy is not rejected”
- **changed** (ABSOLUTE_WITHOUT_COUNT, SIGNIFICANCE_WITHOUT_TEST → ABSOLUTE_WITHOUT_COUNT): “A is NOT significantly more accurate than B at the 5% level. The exact two-sided McNemar p-value is 0.41599, far above the 0.05 threshold, and the 95% confidenc”
- **language passes** (MEASUREMENT_UNKNOWN_FIELD, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “By an exact two-sided McNemar test on the 856 paired items, A is not significantly more accurate than B at the 5% level: 41 items correct only for A and 33 only”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “Model A is not significantly more accurate than B at the 5% level (exact two-sided McNemar p = 0.4160 on the discordant pairs; alpha = 0.05), so the answer to Q”
- **language passes** (MEASUREMENT_MALFORMED, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “Model A is not significantly more accurate than B at the 5% level: exact two-sided McNemar on the 74 discordant pairs (41 A-only correct, 33 B-only correct) giv”
- **changed** (SIGNIFICANCE_WITHOUT_TEST → COMPARATIVE_WITHOUT_COMPARISON): “Verification of CL7/CL9/CL10: on items.csv (818 fully paired items, no missing values, no duplicate item_id) A's per-subset accuracy advantage over B reproduces”
- **changed** (MEASUREMENT_MALFORMED, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → COMPARATIVE_WITHOUT_COMPARISON): “Verification of CL7/CL9/CL10: on items.csv (818 fully paired items, no missing values, no duplicate item_id, subset labels exactly {math, code, reading}) model ”
- **changed** (ABSOLUTE_WITHOUT_COUNT, MEASUREMENT_UNKNOWN_FIELD, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → SIGNIFICANCE_WITHOUT_TEST): “Over all 818 items, model A accuracy is 0.7885 (645/818) and model B accuracy is 0.7323 (599/818). The exact two-sided McNemar test on the 75 items where A is c”
- **language passes** (ABSOLUTE_WITHOUT_COUNT, UNBOUND_NUMBER → accepted): “Over all 818 items model A's accuracy is 645/818 = 0.78851 and model B's is 599/818 = 0.73227, a gap of 0.05623 in favour of A.”
- **passes** (ABSOLUTE_WITHOUT_COUNT → accepted): “Model B's accuracy over all 818 items is 599/818 = 0.732274 (0.7323).”
- **passes** (ABSOLUTE_WITHOUT_COUNT → accepted): “Model B's accuracy over all 818 items is 599/818 = 0.732274 (0.7323).”
- **passes** (ABSOLUTE_WITHOUT_COUNT → accepted): “Model A's accuracy over all 818 items is 645/818 = 0.788509 (0.7885).”
- **changed** (ABSOLUTE_WITHOUT_COUNT, EVIDENCE_MISSING, MEASUREMENT_UNKNOWN_FIELD, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → ABSOLUTE_WITHOUT_COUNT, COMPARATIVE_WITHOUT_COMPARISON, SIGNIFICANCE_WITHOUT_TEST): “The site B exceedance in CL8 is statistically supported, not merely numerical: with corrected site_b_fixed.csv (n=68), site B mean nitrate is 5.87900 mg/L (sd 0”
- **language passes** (ABSOLUTE_WITHOUT_COUNT, UNBOUND_NUMBER → accepted): “Independent critic recomputation confirms CL6: mean nitrate at site B = 5.879 mg/L from site_b_fixed.csv (n=68; 0 missing, 0 non-numeric, no duplicate/absent sa”
- **changed** (ABSOLUTE_WITHOUT_COUNT → ABSOLUTE_WITHOUT_COUNT, COMPARATIVE_WITHOUT_COMPARISON): “Site B mean minus site A mean is -0.828 mg/L, 95% CI [-1.077, -0.579], Welch p<1e-8; the interval lies below zero in 1 of 1 tests. Site A values (6.707 mg/L) ex”
- **changed** (ABSOLUTE_WITHOUT_COUNT → ABSOLUTE_WITHOUT_COUNT, COMPARATIVE_WITHOUT_COMPARISON): “Site B mean minus site A mean is -0.828 mg/L, 95% CI [-1.077, -0.579], Welch p<1e-8. The interval lies entirely below zero, so the values at site A (6.707 mg/L)”
- **changed** (ABSOLUTE_WITHOUT_COUNT, SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → ABSOLUTE_WITHOUT_COUNT, COMPARATIVE_WITHOUT_COMPARISON, SIGNIFICANCE_WITHOUT_TEST): “Both sites exceed the 5 mg/L average limit. Site A mean nitrate is 6.707 mg/L (95% CI [6.556, 6.858], n=75, one-sided p=4.3e-35), i.e. +1.707 mg/L above the lim”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “On the paired items the discordant counts are 46 items where A is right and B wrong and 37 items where B is right and A wrong; the exact two-sided McNemar test ”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “On the 1220 paired items the discordant counts are 46 items where A is right and B wrong and 37 items where B is right and A wrong; the exact two-sided McNemar ”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “On the paired items the discordant counts are 46 items where A is right and B wrong and 37 items where B is right and A wrong; the exact two-sided McNemar test ”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “A is not significantly more accurate than B: exact two-sided McNemar gives p=0.3800, above the 0.05 threshold, so the answer to Q3 is no.”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is not significantly more accurate than B at the 5% level: exact two-sided McNemar on the 83 discordant items (46 A-only-correct, 37 B-only-correct) gives p=0”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is not significantly more accurate than B at the 5% level: exact two-sided McNemar on the 83 discordant items (b10=46 A-only-correct, b01=37 B-only-correct) g”
- **language passes** (EVIDENCE_MISSING, SIGNIFICANCE_WITHOUT_TEST → accepted): “A is not significantly more accurate than B at the 5% level by an exact two-sided McNemar test on the paired items and a p-value of 0.37999939641191804.”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “A is not significantly more accurate than B at the 5% level: of the 83 discordant pairs, 46 favour A and 37 favour B.”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “The exact two-sided McNemar test on the paired items yields p = 0.37999939641191804 (46 A-only-right vs 37 B-only-right discordant pairs), which is above the 0.”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “By an exact two-sided McNemar test on the paired items, 46 of the 83 discordant pairs favour A and 37 favour B (p = 0.3800, above 0.05): A is not significantly ”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “By an exact two-sided McNemar test on the paired items (discordant pairs 46 vs 37, p = 0.3800, above 0.05), A is not significantly more accurate than B at the 5”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “By an exact two-sided McNemar test on the paired items, A is not significantly more accurate than B at the 5% level: discordant pairs 46 vs 37, p = 0.3800.”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “A is not significantly more accurate than B at the 5% level: the discordant pairs are 46 (A right, B wrong) vs 37 (B right, A wrong), and an exact two-sided McN”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “A is not significantly more accurate than B: the discordant pairs are 46 (A only) vs 37 (B only), and an exact two-sided McNemar test gives p = 0.3800.”
- **language passes** (SIGNIFICANCE_WITHOUT_TEST, UNBOUND_NUMBER → accepted): “No subset shows a significant A advantage on its own (exact McNemar p: code 0.0895, math 1.0, reading 0.8388), and a 20000-draw item bootstrap gives P(code diff”
- **passes** (SIGNIFICANCE_WITHOUT_TEST → accepted): “Overall A accuracy is 0.792623 and B accuracy 0.785246; the paired discordant counts are 46 A-only vs 37 B-only, giving an exact two-sided McNemar p of 0.3800, ”
