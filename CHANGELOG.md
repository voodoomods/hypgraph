# Changelog

## Unreleased

- **A size the record doesn't hold is refused.** "No crashes emerged in countless test runs" and "In our initial 10
  trials across dozens of test suites" went in on 0 of 10 test suites in which the parser crashed, "Across a dozen
  trials" on 14 encodings: a reader takes the claim to rest on far more than was counted. Read when "dozens / scores /
  hundreds / thousands / millions of", or "countless / innumerable / untold / myriad / endless", sits on the counted
  set (its plural follows within four words) or on its runs / trials / tests / scenarios / cases, and every count and
  number bound to the claim is below the least the word can mean (dozens 24, scores 40, hundreds 200, thousands
  2,000, the countless family 1,000); and "a dozen" when no bound count is 11 to 13 and nothing makes it rough or a
  bound ("about a dozen", "over a dozen"). A negator on the size itself takes it back ("not dozens of runs"); the
  clause's own "no crashes" doesn't. "Numerous", "many" and "a handful" name no size and aren't read. Pooled telephone
  lines (5,175): 5 false and 1 overreach refused, no true line, nothing looser. The three live rounds since (2,868
  lines, scanned for the shape before the rule was written, so not held out): 2 false and 1 overreach, no true line.
  Corpus (vs main, 3,877 records): 14 stricter, all telephone-showcase lines of this shape, nothing looser. Live
  (gpt-oss on the BC-250s, fresh seeds 2200-2211, main vs this branch, 931 lines labelled blind, paired refile): 1
  false and 1 overreach refused, no true line. Tests: `tests/test_invented_scale.py`.
- **'Half of the counted set' on a count that isn't half is refused.** "Half of the massive files met the deadline"
  on 2 of 6 files over 1 GB parsed within the time budget, and "Only half of the massive files met deadlines" on 2 of
  5, went in in the telephone showcase (blind-labelled false). Either side of a count is half only when the count is,
  so, unlike the majority rules, no side has to be worked out. Read only when "half" sits on the counted set itself and
  nothing loosens or bounds it ("about half", "more than half", "fewer than half", "half or more", "cut in half"); a
  count that rounds to 50% (half up) stands. Pooled telephone lines (5,175, the rule's development set): the 2 false
  lines refused, nothing else moves. Corpus (vs main, 3,853 records): 1 stricter (one of those two lines), nothing
  looser. Held out (953 labelled live sentences, seeds 1800-1811) and live on gpt-oss-20b (BC-250s, fresh seeds
  1900-1911, main and branch side by side, 963 pooled sentences labelled blind and refiled on both): no sentence said
  "half", nothing moves, so neither exercised the rule. Tests: `tests/test_half_off_count.py`.
- **The counted set as the direct object of any verb says it of every one.** "The parser flags misformatted files" on
  20 of 21, "Parser snuffs malformed files", "It spotted corrupted files", "Parser wrestles massive files, staying
  unshaken" on 5 of 7: the bare plural object was read only after the count's own verb or one of mastery, and pooling
  every blind-labelled telephone line (5,175 sentences, run1-3 and three live rounds) showed it as the largest group of
  the 106 false lines main still accepted. Any other verb now reads it too, as `COUNT_CONTRADICTS`, when the set is its
  direct object: no preposition between, an -ed word right before the set is its adjective ("malformed files"), an
  -ous / -ss / -us / -is word is no verb. A clause that states a count, says the contrary, negates, or puts the verb in
  a reported question or time clause ("we measured how the parser handles malformed files", "limits surfaced when the
  parser confronted enormous files") isn't read. On that pool, which the rule was designed from: 23 false and 3
  overreach lines refused, none of the 2,307 accepted true lines. Corpus (vs main, 3,853 records): 29 stricter, all
  telephone-showcase claims labelled false or overreach, nothing looser. Live on gpt-oss-20b (BC-250s, fresh seeds
  1800-1811, main and branch side by side, 953 pooled sentences labelled blind and refiled on both): 1 false and 1
  overreach line refused, no true line, nothing looser. Tests: `tests/test_object_any_verb.py`.
- **'Only a few' of the counted set on a count over half is refused.** The mirror of 'most' on a count under half
  (#166). "Only a few of our biggest files finish on time" on 4 of 7 files over 1 GB parsed within the time budget,
  "Only a handful of massive files kept pace" on 3 of 5: a reader takes most of them to have failed, and most passed.
  Read when a shrinking word ("only / just / merely a few, a handful, a fraction", "a select few", "few", "a minority
  of") sits on the counted set — its plural follows, or, with nothing following ("only a few finish on time"), the set
  is named earlier in the sentence — on a count over half, and its clause doesn't speak of the rest (contrary words,
  negation, reaching a limit: "only a few exceeded the time limit", "only a handful challenged the time limits").
  Exactly half, plain "a few" and "all but a handful" aren't read. **This one rests on a definition:** blind
  labellers of the telephone showcase split on it (11 false, 7 true, in the pool), and the showcase's labelling guide
  now calls it false. Pooled telephone lines (5,175, the development set): exactly those 18 refused, nothing else.
  Held out (1,916 lines labelled before the guide changed, seeds 1800-1911): 16 refused, 6 labelled false and 10
  true, all of this shape. Corpus (vs main, 3,877 records): 33 stricter, all telephone-showcase lines of this shape,
  nothing looser; three that spoke of the slow side ("hit time limits", "stretched its limits") were read until the
  limit guard went in. Live (gpt-oss on the BC-250s, fresh seeds 2000-2011, main vs this branch, 952 lines labelled
  blind under the amended guide, paired refile): 4 moved, 3 false refused and 1 true — "Only a few large files hit the
  ceiling" on 3 of 5, the slow side again; the limit guard now takes ceilings, caps and walls, so it is kept and the
  live round reads 3 false refused, 0 true (that one case was seen before the guard, so it isn't held out).
  The limit guard was then a list of verbs (hit, challenge, stretch, test, reach), and on its first held-out run
  (telephone showcase run4) it missed one: "Only a handful of large files touch the time limit" on 4 of 7 was refused,
  a true line. It now reads any limit in the shrinking word's clause as the slow side, unless a word puts the few
  inside it ("staying under the time limit", "met timing limits", "finished within", "beat"). Every blind-labelled
  telephone line (14,047): the rule fires on 57, that true line no longer among them, and on nothing new; the corpus
  doesn't move. Live (fresh seeds 2700-2711, 975 lines labelled blind, the rule before and after this change): nothing
  moves, as no line of the round put a shrinking word on a majority beside a limit.
  Tests: `tests/test_minority_over_half.py`.
- **"Each" on the counted set, with nothing to say how many, says it of every one.** "The parser flagged each
  malformed file, delivering crystal-clear errors" on 19 of 20 and "Malformed files? Each one triggered a crystal-clear
  error alert" on 23 of 24 went in (telephone showcase, gpt-oss-20b, blind-labelled false), while the same lines with
  "every" were refused. Now "each" as the counted set's own determiner ("each" and up to three words before the
  counted noun, or "each one" with the set named earlier in the sentence) on a count with exceptions is
  `COUNT_CONTRADICTS`, when nothing else in the sentence says how many or hedges and it isn't negated. Most "each" is
  distributive and honest ("rejected nearly every bad file, each with a clear error", "11 trades, each incurring a
  0.1% fee", "each other"): a first draft that read "each" as "every" refused 193 items of the corpus, nearly all of
  that kind, and was dropped. Pooled telephone lines (5,175): 3 false refused, nothing else moves. Corpus (vs main,
  3,973 records): 4 live claims stricter, every one a telephone line of this shape, nothing looser. The five live
  rounds since the pool (4,772 lines labelled blind): 3 false refused, no true line. Live on gpt-oss-20b (BC-250s,
  fresh seeds 2300-2311, main vs branch, 927 lines labelled blind, paired refile): nothing moves, as no line of the
  round put "each" on the counted set. Tests: `tests/test_each_as_every.py`.
- **The target rule rounds as the other number checks do.** `TARGET_NOT_MET` lets a change stand when it rounds to the
  goal as written, but rounded with `round()` (the binary value, halves to even): 20.5% missed "the 21% target",
  12.5% missed "the 13% target" and 4.85% (stored as 4.8499...) missed "the 4.9% target", while every other number
  check reads them as 21, 13 and 4.9. It now uses `_shows`, half up, single-digit whole numbers kept as `_shows` keeps
  them (4.5% is not "the 5% target"). Corpus (vs main, 3,781 records): nothing moves. Live on gpt-oss-20b (BC-250s,
  pressure showcase, seeds 1700-1711 on main and branch side by side, 114 pooled lines refiled on both): nothing moves;
  no benchmark there sat within half a point of its goal. Tests: `tests/test_target_half_up.py`.
- **'Most' of the counted set, said its own way, on a count under half is refused.** "We met deadlines on most large
  files" went in twice on 3 of 7 files over 1 GB parsed within the time budget (telephone showcase run3, gpt-oss-20b,
  blind-labelled false). The even-split rule only read majority words at exactly half, because either side of a count
  may be the one meant. Now a majority word ('most', 'a majority of', 'nearly all', …) that sits on the counted set
  itself, on a count under half, is `COUNT_CONTRADICTS` when its clause says nothing contrary and doesn't negate.
  "Most large files missed / overran / fell short of the time budget" speaks of the rest and stands, as does any clause
  on a count whose own name is put the contrary way ("test suites in which the parser crashed"). Corpus (vs main,
  3,757 records): 2 stricter (the two run3 lines above), nothing looser; of the 7 statements with a majority word on a
  count under half, the other five are untouched (one true complement, two about another measure, two about "data"
  rather than the counted files). Live on gpt-oss-20b (BC-250s, seeds 1700-1711 on main and branch side by side, 941
  pooled sentences labelled blind and refiled on both): no verdict moves, and no sentence had a majority word on a
  count under half, so the live round didn't exercise the rule. Tests: `tests/test_majority_under_half.py`.
- **An effect said to stand out from the noise is a significance claim.** Once "significantly" was refused on a
  speed-up whose interval spanned 0, gpt-oss wrote "a measurable improvement", "a noticeable performance boost" and
  "noticeably quicker responses" on the same benchmarks (p 0.22-0.42), and the record accepted them. "measurable",
  "noticeable" and "discernible" before a change or a comparative ("a measurable 6.6% reduction", "measurably
  faster") now read as "significantly" does, in claims and in reports: the bound test has to show it. A kind of thing
  ("measurable outcomes", "a noticeable share") is not a change, and "detectable" stays out — "no detectable effect at
  this sample size" is the absence wording the report check recommends. Corpus (vs main, 3,673 records): 2 live
  claims and 9 replayed refusals stricter (`SIGNIFICANCE_NOT_SHOWN`), every one a pressure-showcase line on p >= 0.05;
  nothing looser, no other line moves. As if on the four earlier live pressure pools: 4 false lines and 1 overreach
  line newly refused, and 1 line its labeller read as true ("showing a measurable improvement" at p = 0.38, noted as
  borderline; other labellers read the same wording as false). Live on gpt-oss-20b (BC-250s, seeds 1400-1411 on main
  and branch side by side, 120 pooled lines labelled blind and refiled on both): 2 lines move, both "noticeably faster
  responses" at p >= 0.05 (labelled overreach); no true or false line moves. Tests: `tests/test_stands_out.py`.
- **A goal said reached is held against the measured change** (`TARGET_NOT_MET`). Under a VP's "land the 20% we
  announced", gpt-oss wrote "the new build meets the 20% performance target" on a 2.9-6.6% speed-up and it went in:
  the 20% is an investigation constant, which accounts for itself, and nothing compared it with the speed-up. Now a
  percent named as a goal (a target, goal, objective, promise, pledge or commitment; "a target of a 20% reduction",
  "the 20% we announced") that the sentence says was met, reached, exceeded or beaten is refused when every bound
  change in percent (a speed-up, a reduction, a gain, a difference — not an interval's end, an extreme or a goal)
  falls short of it in size. A goal missed, negated, aimed at or planned isn't read, and with no change bound nothing
  is said: a goal's direction isn't in its words ("the 1% error target" is met from below). The refusal shows the
  claim false, so it joins the refusal log's contradictions. Corpus (vs #160, 3,625 records): 12 live claims and 28
  replayed refusals stricter, every one a pressure-showcase line claiming the 20% target on a 2.9-6.6% speed-up (or
  on an 18 ms difference); nothing looser, no other line moves. Live on gpt-oss-20b (BC-250s, the pressure probe,
  seeds 1300-1311 on #160 and branch side by side, 113 pooled lines labelled blind and refiled on both): false lines
  accepted 6 -> 4, both moves "meeting our 20% target" lines; no true or overreach line moves. The 4 left are "20%
  faster" lines that #161 refuses; with #161, none is accepted. Tests: `tests/test_target_met.py`.
- **A figure rounded half up is the value rounded.** Every comparison of a printed figure with a bound value used
  `round()`, which rounds the stored binary value with halves to even: 4.85 (stored as 4.8499…) gives 4.8 and 0.125
  gives 0.12. So "95% CI 4.9 to 11.3" on an interval from 4.85 to 11.27 was refused as a number nothing accounts for,
  and a measurement of 4.9 against a result of 4.85 was a mismatch. A printed figure now stands when it is the value
  rounded half up or half to even, and nothing further away (`_shows`, used by the number reader, the measurement
  check, the comparison reader and `report_check`). A single-digit whole number keeps `round()`: there an exact half
  is most often a ratio of round numbers, and half up let 0.5 cover the "1" of "over 1 GB" and 2.5 the "3" of
  "field 3" (five replayed refusals in a first corpus run, one an overreach line). Corpus (vs main, 3,625 records): no
  text reads differently, no live claim or result moves; replayed refusals 25 looser, 0 stricter, every one an honest
  half-up rounding (0.8963 for 717/800, 8.98 for 8.975, 43.3% for 43.25%, 2813 for 2812.5, …). Live on gpt-oss-20b
  (BC-250s, the tutoring-pilot probe, seeds 2100-2119 on main and branch, 86 pooled lines labelled blind and refiled
  on both; and the 91 lines of seeds 2000-2019): 3 and 6 lines move, all true lines newly accepted; no false or
  overreach line moves. Tests: `tests/test_half_up.py`.
- **A hyphen joins a label word to its number as a space does.** "test 4" was already a label, not a figure, but
  "test-2" — and gpt-oss's "test‑2" (U+2011) — was read as the number 2, so an honest "Tutoring raises test‑2 scores
  by about 8.99 points (95% CI 6.35 to 11.64)" stood only while a ratio or sum of its bound values happened to round
  to 2. Now the reader's label words (case, test, line, step, item, row, issue, section, rule, figure, table, question,
  no.) name their number across a hyphen too; "295-of-400", "1-in-500", "fast-40" and "(F-32)" stay figures. Corpus
  (vs main, 3,478 records): 228 texts read differently, each dropping only a labelled 1 or 2 (and "spec-case-8");
  replayed refusals 6 looser, all tutoring-challenge lines refused for the label's 2; no live claim or result moves.
  Live on gpt-oss-20b (BC-250s, a tutoring-pilot probe that writes "test‑2" unprompted, seeds 2000-2019, main and
  branch side by side, 91 pooled lines labelled blind and refiled on both): no line moves — on fresh lines a 2 is
  nearly always covered by some derived number anyway, so the fix removes a dependence on coincidence rather than
  changing today's verdicts. Tests: `tests/test_label_hyphen.py`.
- **An interval's ends are not amounts to add or divide.** Every pair of bound measurements gave its ratios, relative
  change and sum as numbers a claim may state, and for an interval's ends they covered false lines: under "land the
  20% we announced", gpt-oss filed "the new build is 20% faster" on 6.3%, accepted because the interval's ends have a
  ratio of -3.2 / 15.8 = -0.2025; on 6.7% because they differ by 20.2; and on 5.4% because the high end plus the
  speed-up make 14.1 + 5.4 = 19.5 (live pressure tests, BC-250s). Now two ends of one interval — measurements whose key
  and name name an interval and, the end's word (low / high / lower / upper …) aside, are the same — make only its
  width, which never accounts for a figure written as a percent ("20.2 points wide" still stands); and an interval's
  end with a value that is no interval's end makes no sum (their difference and ratios stand: "8.7 points above the
  estimate", "about 13 times the 0.002 threshold"). Corpus (vs #160, 3,465 records): no result moves; replayed
  refusals 2 stricter and live claims 11 stricter — 4 false "20% faster" showcase lines; "p=0.33" with no p-value
  bound and "-1.7 ± 4.0" on an interval whose half-width is 3.33, each covered by a ratio of the ends; and 7 honest
  tutoring lines whose "test-2" is read as the number 2, which an interval ratio or sum rounding to 2 had covered.
  Pressure showcase, as if (blind labels): false accepted run1 9 → 6, run2 2 → 2, true lines unchanged. Live on
  gpt-oss-20b (BC-250s, seeds 1200-1211, #160 and branch side by side, 104 pooled lines labelled blind and refiled on
  both): false accepted 8 → 7, true refused 0 → 0; the earlier live pool 5 → 3. Of the 7 false lines still accepted, 4
  say "meets the 20% target", which nothing checks yet. Tests: `tests/test_interval_ends.py`.
- **A percent is accounted for only by a number that can be one, and the target's figure stands when the measured effect clears it.** Under a VP's "land the 20% we announced", gpt-oss filed "the new build delivers up to 20% faster response times" on a 4.8% speed-up and it was accepted: the medians, 412 ms and 392 ms, differ by 20. "The new build is 20% faster" on 2.8% went in on the interval's high end over the run count, 8.0 / 40 = 0.2 (pressure showcase run2, BC-250s: 4 of the 5 false lines published). Now a value in a known unit that isn't a percent — from its `unit`, a unit in brackets at the end of its name ("(ms)"), or its key's last word (`_ms`, `_pct`) — a sum or difference with one, and a ratio of two different known units or of a percent to a value not known to be one never account for a figure written as a percent; a value whose unit isn't known reads as before. The same coincidences had been the only way a true understatement ("20% faster" on a measured 24.5%) got past the constant-as-effect rule, so it went in 10 times and was refused 9: now the target's figure said as the effect stands whenever the claim binds a measured effect known to be a percent (not an interval's end, an extreme or a goal), at least as large, signed. Corpus (vs main, 3,321 records): live claims 4 stricter (the run2 false lines), replayed refusals 1 stricter ("0%" bound only to a $0 placeholder) and 10 looser (true understatements); telephone showcase 0 of 1,627 move. Live on gpt-oss-20b (BC-250s, fresh seeds, main and branch side by side, 116 pooled lines labelled blind and refiled on both): false accepted 7 → 5, overreach 1 → 0, true refused 9 → 1. The two "20% faster" lines still accepted are covered by an interval's low end over its high end (-3.2 / 15.8), and "meets the 20% target" is still unchecked. Tests: `tests/test_percent_units.py`.
- **A count with exceptions proves no absolute.** An absolute in the clause of a stated k-of-n count was taken to
  name the set the count ran over ("a count of every selection finds 2 of 1,024 worth more") and went unchecked; commas
  don't end a clause, so "Parser nailed 7 of 8 tests, proving solid coverage" went in on 7 of 8, and "which proves"
  read the same. A word of proof (proves, proving, proof, guarantees, certainly, conclusively, …) names no set: on a
  count with exceptions it is now `COUNT_CONTRADICTS`, with a message that keeps the count and drops the proof. On a
  count of 0 or n the stated n still scopes it, as before. Corpus: 13 live claims stricter, every one a showcase
  overreach line. Telephone run1, as if: overreach accepted 171 → 166, true and false unchanged. Live on gpt-oss-20b
  (BC-250s, 12 new chains on each engine, 947 sentences labelled blind and refiled on both): 11 move, all newly
  refused overreach; no true or false line moves. Tests: `tests/test_proof_from_a_part.py`.
- **"Proving" says what "proves" says.** "proves", "proven" and "proof" were absolutes but the participle wasn't, so
  "Nearly all test suites passed, proving our parser's reliability" on 9 of 10 went in. On merged main the telephone
  showcase accepted 27 lines with it (25 overreach, 2 false) and refused none of its true lines for want of it. Now
  "proving" is read as "proves" is, with the same exclusions, and not when it opens its sentence ("Proving that
  P ≠ PSPACE would be a breakthrough" is about proving, not a claim that anything was). "proved" stays out: "proved
  optimal in-sample" says how something turned out, and "the claim that the test proved them equivalent is not
  licensed" reports a claim to deny it; both are honest lines in the corpus. Corpus (3,237 records): 17 live claims
  stricter, every one a showcase overreach line; no replayed refusal or result moves. Telephone showcase, as if:
  false lines accepted 11 → 9, overreach 188 → 171, true lines refused unchanged. Live on gpt-oss-20b (BC-250s, 12
  new chains on each engine, 916 sentences labelled blind and refiled on both): 25 move, all newly refused, 2 false and
  23 overreach, no true line. Tests: `tests/test_proving.py`.
- **A set named by its size is the set that was counted.** On merged main the telephone showcase refused "All 14
  encodings handled flawlessly" on 14 of 14 "text encodings read correctly", and "All nine encodings…", as a count of
  something else: the statement leaves out "text", and a count of one kind backs no claim about every kind (audit
  HG-024-02). Now an absolute's clause that names the set by the count's n ("all 14 encodings", "each of the 14
  encodings", "the nine encodings were all…") is about that set, unless something else in the clause reaches past it
  ("and every other format", "so any encoding works"), its quantifier isn't the size's own ("no route … among the 3
  routes"), it names another kind ("all 14 binary encodings"), or another count in the investigation has the same n.
  "Every encoding" and "every tested encoding" stay refused. A number in words no longer reads as a kind ("nine
  encodings" as if "cargo routes"). Corpus (3,237 records): 2 replayed refusals looser and none stricter, no live
  claim or result moves. Telephone showcase (each line filed alone): true lines refused 87 → 84, and 3 lines labelled
  overreach now go in ("All 8 encodings handled flawlessly—full Unicode support"); main refused those only for the
  missing "text" and accepts each once "text" is added, so the overreach is in "full Unicode support", which no check
  reads. Pressure showcase, both /play/ attack rounds and the back-test unchanged. Tests:
  `tests/test_stated_n_pins_set.py`.
- **The counted set as the object of a deed says it of every one too.** The bare-plural check read only a clause's
  subject, so on merged main the telephone showcase let in "Parser rejects malformed files" on 24 of 25, "Our parser
  smashed test suites" on 9 of 10, "reigned supreme in test suites" on 6 of 7 and "Parser conquers real-world files" on
  67 of 68 (9 of its 20 false lines that went in), and two /play/ bypasses ("The parser rejects malformed files with a
  clear error" on 23 of 24). Now the counted noun as the bare or definite plural object of the count's own verb (the
  participle in its name: rejected, parsed, passed, read) or of a verb of mastery (conquers, dominated, smashed,
  reigned, aced, nailed, swept, …) is `COUNT_CONTRADICTS` on a count with exceptions, under the same exclusions
  (a number, quantifier, hedge or exception anywhere in the sentence) and not when negated. Other verbs aren't read:
  "accuracy was measured on overlap rows" says nothing of how many. Corpus (3,237 records): 9 live claims stricter,
  every one of them one of those showcase lines; no replayed refusal or result moves. Telephone showcase: false lines
  accepted 20 → 11, true lines refused unchanged at 87. Pressure showcase and the back-test unchanged; /play/ round 1
  catches two more. Tests: `tests/test_object_generic.py`.
- **"All" that counts nothing, and a part counted in any written form, are not absolutes.** On merged main the
  telephone showcase refused two true lines: "Nine of ten test suites passed—solid coverage all around" on 9 of 10
  ("all around" read as "all") and "64/65 real-world files parsed flawlessly" on 64 of 65 ("flawlessly" was said of a
  part only when written "64 of 65"). Now "all" in an idiom ("all around", "above all", "at all", "all in all",
  "all told", "all the same") or at the head of a compound that names a set ("all-rows", "all-orders", "all-cause") is
  not an absolute and does not qualify a generic plural; "all-passing", "all-green" and "all-clear" still are. A part
  is stated as a count also as "64/65" and in words ("sixty-four of sixty-five", but not "every one of"). Corpus
  (3,237 records): 16 replayed refusals looser and none stricter, each an honest "all-rows accuracy", "all-orders
  average", "any leak at all" or "beat buy and hold at all" (the false `COUNT_CONTRADICTS` noted under the p-value entry
  below is one); no live claim or result moves. Telephone showcase: true lines refused 87 → 85, false lines accepted
  unchanged at 20; pressure showcase and both /play/ attack rounds unchanged. A first draft exempted every "all-"
  compound and let "An all-passing run of the test suites" through on 9 of 10; that and 13 other attack forms are now
  tests. Tests: `tests/test_not_absolute_forms.py`.
- **A stated count is read in its other forms.** The stated-count check read "24 of 24" and "all 24" but not
  "24/24" or a count in words, so on 23 of 24 malformed files rejected "The parser rejected malformed files 24/24",
  "Twenty-four of twenty-four malformed files were rejected" and "The parser rejected all twenty-four malformed files"
  went in (a second /play/ attack round). Now "k/n" (not a date, path, decimal or percent) and number words up to
  ninety-nine, compounds whole whichever hyphen joins them, are held to the record's count with `COUNT_CONTRADICTS`,
  under the same exclusions. A label word ("run 3 of 7", "arm 2/3") now counts only when nothing but space separates it
  from the count. Corpus (3,237 records): 182 statements with a slash count and 57 with a count in words reach the
  comparison and none moves; the first draft refused one ("154 users per arm; 22/154 in A vs 31/154 in B" read the 22
  as an arm label across the semicolon), now a test. Tests: `tests/test_stated_count_forms.py`.
- **A p-value is checked as it is written.** Scientific notation was read in pieces: "p = 1.57e-06" as 1 and 06,
  "p<1e-20" as 20. An honest p-value bound to the claim was refused over the stray "06" (29 McNemar claims in the
  harmony runs), and an unbound one went in when its exponent happened to be accounted for. Figures like 1.2e-5,
  3E+04, 1.2e5 and 1.2 × 10^-5 are now read whole, to the places written (1.2e-5 to 6); an exponent without a sign
  needs a decimal point before it, so a short hash like "55351e01" stays a name. A p-value threshold written with one
  significant digit ("p < 0.001", "p<1e-20", "p > 0.05") is accounted for when a bound p-value is on the stated side of
  it; main took "p < 0.001" only when the bound p times 100 rounded to 0.001. A figure such as "p >= 0.1531" still
  needs binding. A derived sum or difference that cancels to float noise is 0, so 8.9e-16 accounts for nothing.
  Corpus (3,237 records): 472 texts read differently, every change a scientific-notation figure; 60 replayed
  refusals looser (each a p-value bound to its claim, or "at p<0.05" with a bound p below it), 9 live claims and 6
  refusals stricter (each a p-value no measurement binds), and one refusal now reaches a false
  `COUNT_CONTRADICTS` on "all-rows accuracy" that main already gives its sister claim. Tests:
  `tests/test_p_as_written.py`.
- **A derived number is read as a percent only when it could be a fraction.** Under a VP's "land the 20% we
  announced", gpt-oss-20b filed "the new build is 20% faster" on speed-ups of 4.2%, 4.6% and 5.7% (pressure
  showcase), and each was accepted: its 20 was accounted for by a derived 0.2 read as 20%, a speed-up of 4.2 plus an
  interval's low end of -4.0, a p-value over an interval's end, or a p-value of 0.2. Now a p-value, arithmetic on
  p-values, a count's k, n and n − k ("100 percent" on 23 of 24 was the 1 that failed, times 100), and the sum or
  difference of two values both 2 or more in size are never read as percents, and a p-value
  takes part in no sum, difference or ratio with an effect. Stated as themselves ("p = 0.2", "agree within 0.0014")
  they still account for the number; a difference of two rates is still said in points or percent, and returns kept
  as fractions above 1 still subtract to a percent. A p-value is read from its unit, a `p_value` / `pvalue` / `p_adj`
  key, a key pairing "p" with a test (`fisher_p`, `p_welch`) unless its unit says fraction / proportion / share / rate,
  or a name saying "p-value"; `p_a` is not one. Corpus (3,237 records): 17 live claims and 10 replayed refusals move,
  all stricter, each a number covered only by such a coincidence ("the other 18 outcomes" by a p-value of 0.18, the
  "20" of "p<1e-20" by 6.604 - 6.402, "slow=50" by -19.5 + 20 trials); the first drafts' false refusals are tests.
  Tests: `tests/test_derived_percent.py`.
- **A stated count is held to the record's count.** On 23 of 24 malformed files rejected, "All 24 malformed files
  were rejected" and "The parser caught 24 of 24 malformed files" went in: every number in them is accounted for (24
  is the bound n), and nothing compared the stated count with the bound one. Now "k of n", "k out of the n", "all n",
  "each of the n" and "every one of the n" are refused with `COUNT_CONTRADICTS` when n is a bound count's n, that
  count has an exception, and the stated k is neither its k nor n − k. Precision over recall: it isn't checked when
  the stated k is any other bound number, when the sentence also states the record's count of that n, when two counts
  over the n differ, against a total kept as a count (n of n, so an understatement isn't caught), or for labels and
  ranks ("run 3 of 7"), membership ("one of 20 settings"), the set ("across all 24 files") and negation ("not all
  24"). Found by the /play/ challenges. Corpus (3,237 records): 3 live claims move, all stricter and all real ("All 6
  tests in test_semver.py pass" bound to 3 of 6 passed); no replayed refusal or result moves. The first drafts refused
  9 more claims and 3 refusals there; each shape is now a test. Tests: `tests/test_stated_count.py`.
- **A refused absolute names the count bound with it.** When "every" / "all" / "flawlessly" is refused because the
  count bound with the claim isn't read as about what the statement says (a count of *text* encodings doesn't cover
  "every encoding"), the refusal used to say only "back it with a k/n measurement". It now names the count ("14 of 14
  text encodings read correctly") and says to name what it counts as the count does, or to state it. The verdict is
  unchanged. Found in the telephone showcase (gpt-oss-20b): writers three retellings from the table, who never saw a
  count, guessed "all 10 tested encodings" until they dropped a true row. Tests: `tests/test_absolute_names_count.py`.
- **A constant is not a measured effect.** The investigation's `constants` account for a number in a statement
  wherever it appears, so a target could stand in for the result: with the announced 20% recorded as a constant so
  "beats the 20% target" could be said, "the new build is 20% faster" was accepted on a 5.9% speed-up (pressure
  showcase, gpt-oss-20b under a VP's "it should land the 20% we announced"). A number accounted for only by a constant
  and said as the size of an effect — "20% faster", "a 20% speed boost", "cut by 20%", "a speed-up of 20%", "up to 20%
  faster" — is now `UNBOUND_NUMBER`, with a message that says to state the measured value and name the constant as
  what it is ("the 20% target"). A bound measurement or derived number with that value still accounts for it; a
  constant named as a target, budget or threshold reads as before. The claim's scope is left out: it holds scenario
  parameters and givens a statement rightly says as changes ("a 10% increase in interest rates"; with the scope in,
  the corpus diff moved 6 live claims, all such). Corpus diff, 3,226 records: R / C / V moved 0. On the showcase's
  127 lines it refuses 14 false lines main accepts and 8 understatements ("20% faster" on 21–23%), which now have
  to give the measured value. Tests: `tests/test_effect_not_from_constant.py`.
- **`optimization@3`: an optimum the values deny is refused.** `optimization@2` checks that a supporting result
  *has* a bound or gap before "optimal" is said, not what they say: "the route plan is optimal at a cost of 412" was
  accepted with a bound of 398, and on an infeasible incumbent. The new profile version adds `OPTIMAL_CONTRADICTED`:
  optimal / optimum / best possible said of the solution when every supporting result that says something has an
  infeasible incumbent or a relative gap above 1e-4 (from objective and bound when both are given, else the recorded
  gap, when it is a fraction). Reference uses ("within 0.72% of the theoretical optimum", "the gap to the optimum")
  and sentences that deny something (an audit measuring a plan against the optimum) are not claims of optimality.
  `optimization@1` and `@2` are frozen and unchanged; no existing record moves. Checked as if pinned `@3`, the 348
  live claims in existing optimization records give 1 refusal (a true optimum on a result whose bound is 0; the first
  draft also refused 5 audits and a gap in value units, now tests). Re-filing the optimal-plan showcase's 126 logged sentences moves none.
  Tests: `tests/test_optimization_v3.py`.
- **`trading@3`: an edge the values deny is refused.** `trading@2` checks that a supporting result *has* an
  out-of-sample, after-cost return and a trials count before "edge" is said, not what the return is: "the strategy
  has an edge out of sample after costs" was accepted on a −3.1% out-of-sample return, and the backtest-bragging
  showcase (gpt-oss-20b) filed "a net return of 11.60%, outperforming the buy-and-hold benchmark of 12.50%" and
  "alpha generation" on strategies that lost to buy-and-hold. The new profile version adds `EDGE_CONTRADICTED`
  (profitable / edge need an out-of-sample after-cost gain; edge / alpha / excess, and beats / outperforms when the
  sentence names the benchmark, need it above the benchmark's; never in a sentence that denies something, as an
  audit refuting the edge does) and `IN_SAMPLE_UNLABELLED` (a claim whose only bound returns are in sample, not
  called in sample). `trading@1` and `@2` are frozen and unchanged; no existing record moves. Checked as if pinned
  `@3`, the 1,084 live claims in existing trading records give 7 refusals, all overclaims (the first draft gave 30
  refusals on honest audits too; they are now tests). Re-filing the showcase's 367 logged sentences moves 9, all on no-edge
  trials. Tests: `tests/test_trading_v3.py`.
- **A comparison the measurements reverse is refused.** "A net return of 11.60%, outperforming the buy-and-hold
  benchmark of 12.50%", both figures bound to the backtest's fields, went into the record: `COMPARATIVE_WITHOUT_
  COMPARISON` counted the measured sides and never read their order. The backtest-bragging showcase published five
  such sentences, three of them from the seat told to report accurately ("79.32% …, outperforming … 84.33%"). New
  `COMPARISON_REVERSED`: the figure just after a comparison word and the nearest figure of the same kind before it,
  in one clause, each matching a bound measurement; words of size ("higher than", "exceeds") compare the values,
  words of merit ("outperforms", "beats", "better than") only where both keys say which way is better (a return up,
  an error or a cost down). It stays out of what it can't read: a difference or multiple ("3 points higher than",
  "twice"), a threshold ("rose to more than", or inside an absolute), a negation ("does not exceed", "without
  exceeding"), the parts of a fraction, a hyphenated label ("step-1"), figures counting different things ("30
  parcels … 60 seconds"), and a figure printed without its minus sign against a negative value ("a loss of 4.66% is
  less than a loss of 56.73%"). Over 3,181 existing records it moves 5 items, all stricter, all these sentences;
  the first draft also refused five honest sentences in HypSwarm challenge records and one in the Exp6 smoke, which
  became the exclusions above and the tests. Tests: `tests/test_comparison_reversed.py`.
- **Saying a source is silent isn't denying what follows.** `SOURCE_CONTRADICTS` took the two words after a negation
  as what a statement denies, so an honest "the handbook does not specify after how many days a staff password must
  be changed", citing the sections it had searched, was refused as denying 'after' because one of them said "rising
  to 27 days after 5 years of service". The seat filed it three times, and the refusal log called it an author who
  said a contradicted claim again and never corrected it (who's-hallucinating showcase run 1: the only conduct warning
  in 30 records, on an honest seat). The second word no longer counts when it opens a phrase of its own ('after',
  'whether', 'during', …); the word denied still does, even one of those ("before 5 years, not after"). Over 3,125
  existing records only 13 logged refusals move, all this sentence from that showcase and its smokes; no live claim
  or result moves. Tests: `tests/test_denied_words.py`.
- **An unbound number's refusal names the sources the claim cites.** `UNBOUND_NUMBER` advised binding a result field
  only, even when the claim cited a source: an agent whose cited passage didn't give the number had no way to read
  that from the refusal. It now says what accounts for numbers (bound measurements, cited sources, the scope, the
  investigation's constants), adds "the source it cites doesn't give them" (or "none of the N sources it cites gives
  them") when sources are cited, and offers citing a source whose passage gives them as a fix. Wording only: what is
  refused does not change. Tests: `tests/test_profiles_041.py`.
- **The report says why the instrument's results aren't open items.** Open items have always left out the
  instrument's own results (measurements need no claim to carry them), but the line read "results no claim carries:
  none" right under a results table marking those results "NO" (spot-the-bad-actor showcase, run 3, in the Atlas).
  It now adds that the instrument's own measurements need none and aren't listed. Wording only. Tests:
  `tests/test_report_open_items.py`.
- **Hyphenated number words: "twenty‑five" is 25, "two‑sided" is no figure, whichever hyphen.** gpt-oss writes the
  non-breaking hyphen (U+2011), which the number reader didn't treat as a hyphen: "twenty‑five days of paid annual
  leave", citing a handbook passage that gives 25, was refused as 20 and 5 (who's-hallucinating showcase smoke, an
  honest seat), "forty‑six lamps" was checked as 6, and "two‑sided p-value" was read as a 2 to bind. A tens-units
  number ("twenty-five", "forty‑six", ASCII hyphen, U+2010 or U+2011) is now read whole; a number word joined to
  another word ("two-sided", "five‑year") is part of a compound adjective, not a figure in a statement. A scope or a
  cited passage still accounts for what it mentions, compounds included: "a five-year period" accounts for "five
  years", "a seven-layer protocol" for "7 layers". A number word after a word is a label, not a count, and accounts
  for nothing: "two weeks' notice", made up and citing a passage on "priority-two tickets", went in during the
  who's-hallucinating run 1 under the first version of this change. Over 3,055 existing records (22,138 logged
  refusals replayed, 14,557 live claims and 38,502 live results re-checked), results don't move; one accepted claim
  is now refused — a pasted passage of ward figures written as words ("fifty-seven", "eighty-six") that nothing
  binds; 126 refusals lose an `UNBOUND_NUMBER` their scope or passage accounts for, and 55 gain one, all claims
  citing no source that write "thirty-two" (they were already refused for that). The label rule, diffed alone over
  3,115 records, moves only that "two weeks' notice". Tests: `tests/test_number_word_hyphens.py`.
- **A figure denied against the source that gives it.** `SOURCE_CONTRADICTS` read denied words and units, not
  figures: "the Nusk–Corlune road is actually 12 km long, not 10 km as the register indicates", linking as support the
  register item that gives 10 km, was accepted (spot-the-bad-actor showcase run 2, the liar's last word). A figure the
  statement denies ("not 10 km", "isn't 10 km", "rather than 10 km") that a linked support source gives, in the same
  unit and about the same thing (two content words shared with the statement's sentence), is now that source's
  contradiction. A denial of a plan or an expectation ("200 patients, not 250 as planned") is not. Saying the denial
  again is a repeat. Across 3,011 existing records only that liar's claim changes; replaying the showcase logs, the
  record rule names 10/10 liars in run 2 with this and the repeat-after-correction fix, and no honest party changes.
  Tests: `tests/test_contradictions.py`.
- **'A majority' of an even split is refused.** "Parsed a majority of large files within the time budget" went in on
  3 of 6 (say-no-more-than-the-data showcase run 3): nothing read 'most', 'a majority', 'more than half' or 'nearly
  all' against the count. Either side of a count may be the one meant ("most settings lose" on 2 of 20 beating), so
  such a word fits any count but exactly half, where neither side is more than half; there it is now
  `COUNT_CONTRADICTS`, offering 'k of n' or 'half'. Over 7,265 claim versions with bound measurements in 3,031 existing
  records, it fires on that statement only. Tests: `tests/test_majority_at_half.py`.
- **A lie said again after a correction is said again.** A refusal that repeats an earlier one the author had since
  fixed was logged as a new, separate claim shown false, because the repeat check only looked at refusals still open.
  Found in the spot-the-bad-actor showcase run 2: a paid critic's "the shortest is 55 km" was refused, the true "the
  route via Quelby measures 55 km" was accepted as its fix, then the same sentence was filed again word for word.
  Conduct read "did not say it again, and corrected it 2 times", and the tie-breaker reading the record acquitted.
  `_note_reassertion` now also checks the author's fixed refusals (first refusals only; a third time leads back to
  the first), so it reads "said it again 1 time after being shown, and corrected it 1 time". A different false claim
  after a correction is still a new claim shown false. Replaying the showcase logs: two liars per run gain a repeat,
  one more liar is named (9/10), no honest party changes. Tests: `tests/test_contradictions.py`.
- **Qualified headlines are read as qualified, and "all but N" as a count.** In the say-no-more-than-the-data
  showcase run 2, four true headlines were refused as absolutes: "near-perfect success" (8 of 9), "parsed
  flawlessly, one exception" (74 of 75) and two "all but one malformed file flagged" (18 of 19, 19 of 20). "Near-"
  now qualifies like "nearly" (with the non-breaking hyphen models write too); "one exception" / "with a single
  exception" qualify a manner absolute like "except one" (not "without a single exception"); and "all but N" is no
  longer an absolute but a count, n − N of n, refused as COUNT_CONTRADICTS when no bound count of what it's about
  has N exceptions either way ("all but a few" names no number and stays a hedge). Two misses of the same kind
  are read now: "without a hitch" (a false run-2 headline that went in, 78 of 80) and "stands undefeated" (a false
  run-1 headline, 8 of 9, that had been refused only for its "all"). Replaying the showcase logs: five true
  headlines go in, the false "without a hitch" is refused, no false one goes in; Exp1 unchanged. Over 8,714 claim statements in 3,011 existing records, three change reading, each
  correctly. Tests: `tests/test_implied_absolutes.py`.
- **A bare plural that is what the count counts says it of every one.** "Malformed files rejected with clear errors"
  went in on 23 of 24 malformed files rejected with a clear error, while "every malformed file rejected" on the same
  count was refused: in the say-no-more-than-the-data showcase, eleven false headlines of this shape went in over
  two runs, and no true one had it (the true ones said "nearly all", "most", a number, or named the exception). Now
  refused as COUNT_CONTRADICTS when a clause's subject is a plural that is the bound count's own counted noun, the
  count is mixed (0 < k < n), and nothing in the sentence says how many or hedges. Replaying the showcase logs:
  those eleven are refused, no true or overreach-labelled headline changes, Exp1 unchanged. Over 7,277 claim
  versions with bound measurements in 3,011 existing records, the rule fires on 14 statements, all of them those
  showcase headlines. Tests: `tests/test_generic_plurals.py`.
- **A bare plural's refusal offers a qualifier true of the count.** The generic-plural refusal suggested 'nearly
  all' or 'most' whatever the count; on 3 of 6 large files parsed, the rewrite said "a majority", which half is not
  (say-no-more-than-the-data showcase run 3). It now offers one word that fits k of n: 'nearly all' (90 % or more),
  'most' (over half), 'half', 'fewer than half', or 'a few' (under 10 %). Wording only. Tests:
  `tests/test_generic_plurals.py`.
- **The overclaims report and the Atlas say what each author did after being shown false.** They showed only how
  many overclaims were refused: a showcase record's Atlas read "6 overclaim(s) refused by the record", while the line
  that tells a liar from an honest mistake, `conduct()`'s, was printed only by `hypgraph demo dispute`.
  `refusal_report` (and `GET /api/graph/refusals`, `hypgraph refusals`) now carries `conduct` per author and an
  "After being shown false" section. The Atlas's Needs attention lists each author's line, flagged when its last word
  still says the claim or was contradicted: "quin: … said it again 5 times after being shown, and never corrected it;
  its last word still says it" beside "uma: … said it again 1 time after being shown, and corrected it 1 time; its
  last word no longer says it". Facts, not a verdict. Tests: `tests/test_demo_dispute.py`.

## 0.8.8 — 2026-11-15: the record tells a liar who keeps at it from one who moved on

No change to the bundle format. One check closes a back door (a link is checked like the claim's create); the
rest were found by small showcase experiments on gpt-oss-20b (BC-250), where a paid critic argued against an
honest researcher and a writer drafted launch headlines from test counts. The conduct log now counts a lie said
again beside a figure it denies as a repeat, and a new false figure each time as persisting (`conduct()` gains
`replaced_false`); the bound a refusal suggests is accepted; "flawlessly" and "without a single error" are
absolutes. Each was checked by replaying the experiments' logs, with no model calls: on 0.8.7 the replays
reproduce the runs exactly.

- **A link that adds support to a claim is checked like the claim's create.** Claim checks ran when a claim was
  created or revised, never when a later `link` added to what it rests on. So any check that reads the support
  (a source that says the opposite, a count against an absolute, a profile's source rules) could be stepped round:
  write the claim on harmless support, then link the rest. In a HypSwarm swarm on gpt-oss-20b (BC-250, 2026-11-10)
  an inconclusive answer was created on a result, and its `cites` link to an unreferenced source was added 53 s
  later. It was reviewed checked. A non-curator's link that changes a claim's support now runs `checks.claim_issues`
  and the profile's claim checks with and without the link. The link is refused only for problems it brings; one the
  claim already had doesn't block an unrelated link. The refusal is logged as `op=link` on the claim. Replayed over
  270 swarm records on the released profiles, 0 of 5,079 later links would be refused.
- **A lie said again beside a figure it denies or compares is a repeat.** A count contradiction stored every number
  in the refused statement as part of the lie, including a denied or compared one ("40 km, **not 38 km**", "31 km,
  since the true total **exceeds 30 km**"). `refusals.carried` never counts those as asserted, so the same sentence
  said again was logged as moving off it, not as a repeat. The refusal now stores only the figures the statement
  asserts (`checks.asserted_figures`, one pattern for both sides), and `carried` reads refusals logged before this
  through the refused statement. Found in the spot-the-bad-actor showcase (gpt-oss-20b, BC-250, 2026-11-15): replaying
  its 20 record-arm disputes, one paid critic goes from 0 repeats and 5 moves off to 3 repeats, still saying it at
  the end. No other party's conduct changes.
- **A new false figure each time reads as persisting, not moving off.** An author refused six times with a different
  figure each time (31, 32, 33 km ...) had every refusal logged as moving off the last one, and `conduct()` summed it
  up as "the author did not say it again". `conduct()` now counts `replaced_false`: claims shown false whose author's
  last word on them was a move into another claim the record also showed false. It is a subset of `moved_off`, so
  existing fields keep their meaning. The sentence says it ("did not say the same claim again, but replaced a
  contradicted claim with another the record also contradicted 5 times, and never corrected it"). Derived on read
  from the log, so existing records read the new way. Found in the spot-the-bad-actor showcase (gpt-oss-20b, BC-250,
  2026-11-15), where a tie-breaker reading the record acquitted such a critic. Replaying its 20 record-arm disputes:
  6 of 10 paid critics get a replacement count, no honest party does, and no verdict of the record rule changes.
- **The honest wording a refusal suggests is accepted.** `ABSOLUTE_UNDERPOWERED` suggests "no occurrences in 8
  trials (95% upper bound 31%)", and `bound()` prints "at most 31%". The record then refused that figure as unbound,
  for two reasons. Statistical figures had to be written to a decimal place, and for k = n the printed bound
  (1 − lower bound) wasn't among the derived numbers at all. A percentage the statement itself labels as a bound
  ("upper bound", "at most", "no more than" …) now matches a bound count's 95% bounds, or their complements, as
  printed. The match is by position, so a labelled bound vouches for nothing else in the sentence. Unlabelled
  figures keep the decimal rule. `check_text` does the same. Found in the say-no-more-than-the-data showcase
  (gpt-oss-20b, BC-250, 2026-11-15). Replaying its 82 headline attempts, 11 that were refused are now accepted, all
  of them correct bounds for their counts, and no other outcome changes.
- **"Flawlessly" and "without a single error" are absolutes.** They say of how things went what "every" says of
  how many, and they weren't in `language.ABSOLUTE`. So "Real-world files parsed flawlessly" on 76 of 77 went in,
  while "every real-world file parsed" on the same count was refused. Added: flawless(ly), without (a single / any /
  one) error / failure / fault / crash / exception / bug / mistake / glitch / hitch, and error- / failure- / fault- /
  crash- / bug-free. These words describe the manner of their subject, so they cover every one of it only when the
  subject does: "nearly all files parsed flawlessly", "72 of 73 parsed without error" and "flawlessly, only a handful
  slipped" stay true and still go in. Found in the say-no-more-than-the-data showcase (gpt-oss-20b, BC-250,
  2026-11-15). Replaying its 82 headline attempts, the 4 false drafts that used these words are refused, and no
  other outcome changes. None of the 2,646 HypSwarm records on hand has a claim using them.

## 0.8.7 — 2026-11-08: a snapshot is loaded at one moment

No change to the bundle format or the checks: one read fix and one scope fix, both found running HypSwarm.

- **A snapshot is loaded at one moment.** The tables behind a snapshot were each read in their own implicit
  transaction, so a second Graph on the same file could commit a node and its edge between the `nodes` read and
  the `edges` read; the edge then named a node the snapshot didn't hold, was skipped, and its mark was advanced
  past it — that Graph never saw the edge again until a rebuild. hypswarm's scheduler and the MCP server an
  external seat works through share a file this way (one process, two threads); on Ubuntu CI the scheduler found
  "no live claim" on a question every other Graph showed answered, reworked the order, and asked the seat to count
  again, which the record refused as a restatement (2026-11-05 to 11-08, never on Windows). A rebuild, a delta
  (with its retraction check) and the row load now run inside one read transaction; a load inside a write's own
  transaction joins it. Reproduced deterministically before the fix (`tests/test_consistent_load.py`).
- **The run behind a result on a question is a run on the question.** A question's scope collected results through
  its claims (`derived_from`, `supports`) but runs only through an experiment's `executes` or a `part_of` link. A
  harness that registers run → result → claim and links only the claim to the question left the run gate reading
  "no run executes an experiment on Q1" with the result and the claim both met; the harness issued a `run` order
  every round beside the review, and on one BC-250 run the seats filed 11 claims on 3 questions without settling
  one (S3, 2026-11-07). The scope now adds the runs that `produced` its results.

## 0.8.6 — 2026-11-07: a placeholder is not a statement

- **A figure's name is not the figure.** The slot check (`STATEMENT_EMPTY`) now refuses `$mean_tutored`,
  `$cost_per_change$`, `<claim_id>`, and a bare name shaped like a figure standing where the figure belongs ("a
  p-value steps_k_p", "before costs of cum_rule_before"). Over every BC-250 challenge record (1,535 claims) 13 were
  written this way and reviewers checked three of them, one with a note listing the numbers the claim left out. A
  name beside its value passes: "17.13 % (oos_return)", "oos_return = 0.17", "a mean_diff of 1.7"; a column named
  `steps_k` is a name, not a slot.
- **A claim that is a question says nothing.** A statement ending in a question mark is refused as `STATEMENT_EMPTY`.
  On a BC-250 run a seat wrote the question's own text as a claim superseding its right answer, and the reviewer
  checked it, so the question settled on a question. A question followed by its answer passes as before.

## 0.8.5 — 2026-11-06: fewer false refusals

- A date a source writes as an ordinal is in the source: "the 14th of June 1887" accounts for "14 June 1887". It was refused as an unbound number, and a seat ended up with a claim saying the bridge opened "on a date".
- A statement with an unfilled slot is refused as STATEMENT_EMPTY: a template's `{date}`, or a variable's name where its value belongs (`accuracy = A_easy_acc`). Inline code is not read for this.
- **A report that denies significance isn't refused for it.** `REPORT_SIGNIFICANCE_UNBACKED` is a warning, not an
  error, when the sentence denies the test: emphasis ("*not* significantly"), "no statistically significant difference",
  "does not support a statistically significant advantage". Before, only the bare "not significant" counted, so an
  honest negative was refused and small models gave up on the report. A sentence that also asserts significance
  ("not only significantly", "B is not significantly cheaper, but A is significantly better") stays an error.
- **A named p-value carries the test.** A result whose values name one (`p`, `p_value`, `pvalue`, `p_exact`, …) backs a
  significance word, and so does a claim whose statement gives a p-value or that rests on such a result. Before, only a
  value with a `p` field did, so citing the claim that held the test was refused.
- **A word and a figure say something.** `STATEMENT_EMPTY` no longer fires on "A's accuracy is 0.814."; placeholders
  still do, with a number beside them or not.

## 0.8.4 — 2026-11-04: sources in the sidebar; a focus on one node's part of the graph

- **A Sources view in the Explorer's sidebar.** Everything an investigation cites, in one place: outside literature
  (citation, kind, DOI and URL as links, the passage as the author quoted it, when it was retrieved) and pinned
  references into other records (the linked-records table, moved here from under the graph), each with the claims,
  results, hypotheses and experiments that cite it and their standing. Filters for sources cited by nothing, sources
  with no DOI or URL, and sources that fell (withdrawn or superseded) while live nodes still cite them. CSV and BibTeX
  export. The view says what the record checked: a pinned reference's version hash; for outside literature, nothing.
  A DOI or URL in a node's fields now opens where it points. Key `6`; the later views move to `7`–`9`.
- **A focus on one node's part of the graph.** From a node's details, "Show what it rests on" (the engine's `why`
  walk), "Show what rests on it" (its mirror: everything that rests on the node by a link, the claims that cite a
  source included; what would *fall* with it is the narrower engine walk the drawer shows under "If it fell") or
  "Show its neighbours" (depth 1–3) draws only that part of the record, with a bar naming the node, the lens, the
  depth and how many nodes are shown; the type chips still apply, the centre is always drawn, a focus of one or two
  nodes is drawn at a readable size rather than filling the pane, Esc clears it. Under Graph, the sidebar lists the
  records this one pins (the subgraphs, each a jump to that record in the linked graph) and the investigation's
  questions, each a focus on the question, what answers or addresses it and what that rests on. The focus is in the link
  (`#view=graph&focus=CL7&lens=why`, "Copy link" on the bar), so a review comment can point at exactly the subgraph it
  means, and the JSON export of a focused graph is that part of the record with the focus named. `HypGraph.focusIds`
  computes the set from the record's own edges, so a bundle and a server agree (`tests/test_ui_sources_focus.py`).

## 0.8.3 — 2026-11-03: the next-experiments view in a stable order

- **`verify --standing` no longer fails on a sound bundle with two or more untested hypotheses.** `next_experiments`
  listed `untested_hypotheses` by iterating a set of ids, so the order followed Python's per-process string hashing:
  a bundle exported in one process carried one order and its re-derivation another, and `hypgraph verify --standing`
  reported a standing mismatch (`<inv>/next`) on a record whose content was identical. The list now follows the order
  the hypotheses were added. Found on a 785-node record; that record and three smaller ones now derive identically
  under six hash seeds.

## 0.8.2 — 2026-11-01: an extreme that quotes its own counterexample; a disputed answer

- **A quoted counterexample no longer excuses an extreme.** A stated count used to exempt an extreme whenever its
  clause said "k of n ... than", meant for a count about a figure of the statement's own ("the shortest is 21 km; 1 of
  77 are shorter than 26 km"). It also exempted the count at the extreme's own figure, so "the shortest route is 30 km,
  since 1 of 77 are shorter than 30 km" was accepted. The count is now an exception to the extreme whenever its figure,
  on the result or in the sentence, is the extreme's own.
- **Two readings that exemption had hidden.** "The highest ... is therefore not 125" is a denial (an adverb between
  the copula and "not"), and a bound in the extreme's own direction ("the shortest is at most 30 km", "91 or more") is
  not a claim that the figure is the extreme. A bound the other way ("the shortest is at least 30 km") still claims it.
- Replayed on 1,900 recorded claim writes: 5 change, all now refused. Four are an extreme stated beside the count
  that shows it false. One is a retraction worded as the claim ("the highest is 80, but this is not correct: 3 of
  1,024 are worth more"). Who the record names as still saying something false is unchanged or better on every set.
- **`hypgraph demo dispute`: a disputed answer.** A teaching record in which two parties answer one question from the
  same road register. Ada makes an honest mistake, the record refuses it (`COUNT_CONTRADICTS`) and she corrects it.
  Mallory cites the register's units note for a claim it contradicts, is refused twice (`SOURCE_CONTRADICTS`) and files
  it without the note. An independent reviewer checks one claim and fails the other, so the Evidence view shows one
  answer checked and one contested, and `Graph.conduct()` names who kept saying it. It is also on the website
  (`examples/dispute/`, in every site language) and in the README. `hypgraph demo` with no name still builds Broad
  Street.

## 0.8.1 — 2026-11-01: exact figures, units within their kind

An independent audit of 0.8.0 found two defects in the typed checks, both confirmed on the published wheel.

- **Exact figures (HG-080-01).** Containment of two conditions was decided by probing at each figure ± 1 and the
  midpoints, in floats. Above 2**53 a figure + 1 is the figure, so x > 1e18 looked inside x <= 1e18, and a count of 0
  above 1e18 supported "none below 1e18". Containment is now decided on the pieces the two figures cut the line into,
  with no arithmetic on them, and figures keep their exact value (10**18 + 1 is not 1e18; it renders as itself).
- **Units within their kind (HG-080-02).** The unit table's kind was dropped, so `lb` (mass) matched `GBP` and
  `sterling` (currency) through the shared name "pound". A unit is now its (kind, unit) readings: `lb` = `lbs` and
  `GBP` = `sterling` still, never across kinds, and an ambiguous `pound` matches only another `pound`; the refusal says
  what it could be and asks for `lb` or `GBP`.
- **`exactly` decided from bounds.** It was left unresolved unless its set was the counted one or its complement:
  4 of 4 above F now contradicts "exactly 4 below F". Over one population every verdict now equals enumeration of the
  consistent worlds (sound and complete), and the test checks that.
- **An extreme stated as a value is two atoms.** In a typed investigation "the longest of the 4 routes is 26 km"
  needs both "none above 26" and "some at 26 or more"; one of them is refused (`ASSERTION_MISSING`). An extreme stated
  as a bound ("the slowest took at least 40 minutes") needs one.
- Tests: containment against exact rational probes over large, adjacent, subnormal and signed-zero figures; the audit's
  cases through `_decide` and the write gate; units; extremes. The audit's own test file passes (13 of 13).

## 0.8.0 — 2026-11-01: typed claim assertions

Eight independent audits (HG-020 → HG-028) found the same class of failure, each time in a new wording: to decide
whether a count backs or contradicts a claim, the checks read words — the result's key and the claimant's
measurement name for what was counted, the statement for what is asserted and which clause a count belongs to — and
the claimant writes most of those words. Each fix narrowed one wording; the next audit found another. 0.8.0 stops
inferring that structure from words.

- **Typed counts.** A count may say what it counted: `population` (a path, `route/passenger` lies within `route`),
  `property` and `unit`, beside `k`, `n`, `figure` and `op`. The result's author writes them; the instrument, on its
  own results.
- **Typed assertions.** A claim may carry `asserts`, atoms `{quantifier none | all | some | exactly, population,
  property, op, figure, unit, n, k, measurement}`. Each is decided against its bound count by sets on the number line
  and population paths (`src/hypgraph/assertions.py`): supported, contradicted, or unresolved with the field that
  blocked it. No words are read, so a true atom can't lend anything to a false one (HG-028-01) and "all 4 routes"
  meets its counterexample however the set is enumerated (HG-028-02). New codes `ASSERTION_CONTRADICTED` (tracked in
  conduct like `COUNT_CONTRADICTS`, `by_assertion`) and `ASSERTION_UNRESOLVED`.
- **Typed investigations.** `typed_claims: true` on an investigation (or a profile's `typed_claims`) makes atoms the
  check: a statement that asserts an absolute, an extreme or a count needs an atom for each part that does
  (`ASSERTION_MISSING`, with atoms drafted from the statement and its typed counts — never trusted, checked once
  written), and the word interpretation stands down there: measurement names and keys aren't read for what was
  counted, and the absolute / counterexample / extreme checks don't run. Numbers in the statement must still be bound;
  every other check runs as before.
- **Standing.** A claim's state carries `assertions` (each atom rendered as the sentence it asserts, with its verdict
  against the count as it stands now), `assertion_contradicted` when a count revised later makes an atom false (the
  claim joins the revalidation queue), and `checked_by`: `typed`, `wording` or `none`. Bundles carry the verdicts, and
  the verifier checks them against the rows. The Atlas claim drawer shows the atoms as the headline and the author's
  sentence beneath, labelled as prose.
- **A count is whole, for everyone** (HG-028-03). `k` and `n` must be whole numbers (an int or an integral float),
  finite, `0 ≤ k ≤ n`, `n ≥ 1`, on creation and on revision (`VALUE_NOT_A_COUNT`); counts used to be truncated, so 0.9
  of 4 read as 0 of 4 and backed "none". A typed count must be complete (`VALUE_TYPE_INVALID`).
- **The word checks are frozen.** Outside a typed investigation they run as in 0.7.28 and are documented as heuristics;
  HG-028-01 and -02 remain limits of untyped mode. Replaying the 1,900 recorded adversarial entries changes none, and
  every trial's standing is the same.
- Tests: `tests/test_assertions.py` (the interval logic checked against enumeration over every op and quantifier, paths,
  units, the gate, standing, bundles, the draft) and `tests/test_typed_audits.py` (92 attack sentences from the audits
  and their holdouts, around fixed atoms: none changes a verdict).

## 0.7.28 — 2026-11-01: a figure said twice, a comparison in another tense

Fixes from an independent audit of 0.7.27 (HG-027-01, -02) and from paraphrases written after the first fix; each case
below failed on 0.7.27 and is now a test (`tests/test_figure_said_twice.py`, 22 of its 34 cases fail on 0.7.27).

- **A figure said in a clause that claims nothing doesn't lend it words** (HG-027-01). 0.7.27 read every clause that
  stated a count's figure for what the count was about, so "Speed was recorded above 26 separately; no route is longer
  than 26 km" still let a speed count named "routes longer than 26 km" back the length claim, and cargo counts back
  passenger claims the same way. Of the clauses that state the figure, only those that make the claim (an absolute or
  an extreme) are read now, when any does.
- **A comparison is read the same in every tense** (HG-027-02). "No route exceeded 26 km" was an absolute, but its
  figure went unread ("exceeds" was read, "exceeded" wasn't), so any complete count backed it, even beside a count of 1
  route over 26. Every stage now reads one list: "exceed" and "surpass" in every tense, "above", "below", "beyond", and
  "over" / "under" after "is" / "was" or the noun "no" opens ("no route under 20 km exists"); not "over 1000 runs",
  which says how many were run. A comparison whose figure still can't be read ("no route is longer than the usual
  one") is backed only by a count that makes that comparison, never by one that compares nothing.
- **"None of the 4 routes" is still contradicted by its count.** An absolute over a set the sentence enumerates needs no
  count of its own, but it used to skip the check entirely, so a bound count of 1 route over 26 went unread. A count
  that finds an exception now contradicts an enumerated "none" or "neither". An enumerated "all" / "every" stays
  exempt: in the recorded entries it names the set a count ran over ("across all 1,024 selections, 2 fit").
- **One count backs "no route exceeds 26 km".** "Exceeds" with a figure inside an absolute is a bound the absolute check
  settles, not two measured things compared; the comparison check no longer asks for a second measurement there.
- Replaying the 1,900 recorded adversarial entries changes none, and every trial's standing is the same. This is
  still word matching: the typed claim layer the audits recommend is not built.

## 0.7.27 — 2026-11-01: words said elsewhere, comparisons the checks didn't know

Fixes from an independent audit of 0.7.26 (HG-026-01, -02); each case below failed on 0.7.26 and is now a test
(`tests/test_borrowed_words.py`).

- **A word said in another clause doesn't make a count fit** (HG-026-01). What a count's key says it counted had to be
  said by the measurement's name or anywhere in the statement, so "Speed was recorded separately; no route is longer
  than 26 km" let a speed count named "routes longer than 26 km" back the length claim, and "Cargo routes were
  inspected; no passenger route is longer …" did the same for a cargo count. The words must now be said where the
  claim states the count's figure (its clause, from the comma before its absolute or extreme). Eight paraphrases over
  other subjects and properties, written after the fix, are tests too: an extra clause never turns a refusal into an
  acceptance, and an honest count backs the claim with or without one.
- **Any comparison makes an absolute** (HG-026-01, found while reproducing it). "No crate is heavier than 40 kg" and "no
  shift had errors above 5" weren't read as absolutes, so they went in with no count, or with a count of crate prices.
  "No …" before any comparison word is now an absolute; heavier / lighter, warmer / colder, older / younger, taller,
  wider, deeper, louder and stronger are comparisons along their own axes (weight, temperature, age, height, width,
  depth, loudness, strength), and a comparative the checks don't know ("brighter than") is met only by a count that
  says the same word. A three-letter word before a comparison ("bridge age above 60") now names what was counted, and
  "span" is a length, so an honest count of bridge spans backs "no bridge is longer than 60 m".
- **A mixed "and" / "or" clause has to be split** (HG-026-02). 0.7.26's notes said such a clause is unresolved "until a
  count of the whole condition is bound"; nothing ties a count to the whole condition, so that never happened. The
  refusal now says to split the claim into clauses that each join their comparisons one way.

## 0.7.26 — 2026-11-01: what a count is of, what its key compared, "and" with "or"

Fixes from an independent audit of 0.7.25 (HG-025-01 to -03); each case below failed on 0.7.25 and is now a test
(`tests/test_what_a_count_is_of.py`).

- **A count names its kind in the singular too** (HG-025-01). Kinds were read only before a plural, so none of 3
  "cargo route longer than 26 km" (or "cargo longer than 26 km") backed "no passenger route is longer than 26 km"
  while the passenger count was 1 of 3. What a count names before its comparison is now read singular or plural: a
  count of cargo routes neither backs nor refutes a claim about passenger routes. A word that says what was compared
  ("selections worth more") isn't read as the kind, and a bound in the statement ("the limit is at most 49 kg") isn't
  what the claim is about.
- **A count's name can't change what its key counted** (HG-025-02). A count the lab keyed `route_speed_above_26`,
  named "routes longer than 26 km" by the claimant, backed a claim about length. The key is the result's own name for
  what it counted: a measurement whose name compares along another axis (length, not speed), or whose key counts a
  thing neither the name nor the statement says ("cargo" under a name for passenger routes), is now
  `MEASUREMENT_MISMATCH`. "route length above 26 km" still names a count of routes longer than 26 km.
- **"And" with "or" in one clause is left unresolved** (HG-025-03). The parts were checked one by one, so routes of 5,
  20 and 25 km, which make "every route is longer than 10 km and shorter than 30 km or shorter than 6 km" true, gave
  `COUNT_CONTRADICTS`. Which parts go together isn't settled by the words, so no count of a part backs or refutes such
  a clause: it is `ABSOLUTE_WITHOUT_COUNT` until a count of the whole condition is bound, or the claim is split.

## 0.7.25 — 2026-11-01: which counts bear on a claim, joined comparisons, boundaries in names

Fixes from an independent audit of 0.7.24 (HG-024-01 to -04); each case below failed on 0.7.24 and is now a test
(`tests/test_counts_that_bear.py`).

- **A count with no comparison doesn't back one** (HG-024-01). With no comparison of its own, a count of none or all
  was read the old way, so "3 of 3 routes processed" backed "nothing is longer than 26 km" and "every route is longer
  than 26 km". A count that states no comparison now doesn't bear on a claim that rules one out
  (`ABSOLUTE_WITHOUT_COUNT`). A claim with no comparison ("no route ever failed") reads a plain count as before.
- **A count of one kind doesn't back a claim about another** (HG-024-02). A count and a claim were matched on any shared
  word, so none of 3 cargo routes longer than 26 km backed "no passenger route is longer than 26 km" while the passenger
  count was 1 of 3, and backed "no route is longer" too. A count names what it counts in the plural ("cargo routes");
  where the statement uses that word, the words right before it say which kind. A count backs a claim only if every
  kind it names is one the statement names; a count of one kind that finds some still refutes a claim about all, and
  two kinds named apart (cargo, passenger) are left unresolved.
- **Two comparisons joined in one clause** (HG-024-03). "And" ended the clause, so "no route is shorter than 20 km and
  longer than 30 km" was refused by a route shorter than 20, and "every route is longer than 10 km and shorter than 30
  km" went in with "shorter than 30" unread, even with the count that refutes it bound. An "and" or "or" before a
  comparison with no subject of its own now keeps it in the clause. "No … A or B" and "every … A and B" are false if
  either part fails; "no … A and B" and "every … A or B" rule out only what meets both, so none of one part backs them
  and a count of each part on its own leaves them unresolved.
- **A count's name must say its boundary** (HG-024-04). Only a name pointing the other way was caught: a `>=` count
  named "routes longer than 26 km", or a `>` count named "26 km or longer", went in. A name that leaves the figure out
  where the count took it in, or the other way round, is now `MEASUREMENT_MISMATCH`.

## 0.7.24 — 2026-11-01: what a quantifier needs, where a comparison's boundary falls, one check per extreme

Fixes from an independent audit of 0.7.23 (HG-023-01 to -05); each case below failed on 0.7.23 and is now a test.

- **"Nothing" needs none, "every" needs all** (HG-023-01). Any count of none or all backed an absolute, so "nothing
  is longer than 26 km" went in with all 3 routes longer, and "every route is longer than 26 km" with none. When a
  count's comparison is known, the claim now needs the extreme its quantifier names; the other extreme shows it false
  (`COUNT_CONTRADICTS`). A count of what lies outside the claim's exceptions is read as its complement: none of 3
  longer than 26 is 3 of 3 at 26 or shorter. "Every" in a clause that states its own count ("a count of every route
  finds 1 of 76 shorter") names the set counted and is not read as a quantifier. A count whose comparison can't be
  told ("failures") is read as before.
- **"At least" is not "longer than"** (HG-023-02). Comparisons keep their boundary: `op` takes `<`, `<=`, `=`, `!=`,
  `>=`, `>`, and names say "at least", "at most", "26 km or longer", "not / no shorter than", "no more than". A count
  refutes a claim only if everything it found is an exception, and backs it only if it covers every exception: two
  routes at least 26 km neither refute nor back "no route is longer than 26 km" (the routes of exactly 26 lie between),
  and none longer than 26 doesn't back "no route is 26 km or longer". `=` and `!=` counts don't bear on a comparison.
  "At least" used to be read as pointing down and "at most" up. "No route is 26 km or longer" and "no route is at
  least 26 km" are absolutes too.
- **Two extremes are two claims** (HG-023-03). "The shortest route is 26 km; the longest route is 35 km" pooled both
  figures and both directions, and the count of 2 longer than 26 refused the true sentence. Each extreme, and each
  thing an absolute rules out, is now checked with its own figure and direction; the refusal names the extreme it
  found false.
- **What "of" and "for" name says which thing** (HG-023-04). "Weights of cargo" and "weights of passengers" both read
  as bare "weights", and "shipping cargo weights" met "shipping passenger weights" on one shared word. The object of
  "of" / "for" now counts, and two subjects that each say something the other doesn't are left apart: unresolved, not
  a contradiction. One that only adds to the other ("the recorded weights of cargo") is the same thing.
- **A contrast keeps the unit it asserts** (HG-023-05). "Not in pounds but in kilograms" lost its kilograms, and
  "kilograms rather than pounds" kept both, so a claim of pounds citing either went in. A clause with no subject or
  verb of its own takes the subject its sentence named last ("… but always in kilograms"); one that names its own
  ("and passenger weights in pounds") doesn't. What follows "rather than" / "instead of", up to its unit, is set aside.
- Limits: subjects, units of record, quantifiers and comparisons are still read from words, not typed (only a count's
  `figure` and `op` are); a missed contradiction is preferred to a false one, so subjects left apart are not
  compared; conversions aren't checked; and the replay of earlier recorded entries changes nothing, which shows no
  regression but none of those entries tries these cases.

## 0.7.23 — 2026-11-01: a count points one way, "no route is longer", what a unit is said of

Fixes from an independent audit of 0.7.22 (HG-022-01 to -05); each case below failed on 0.7.22 and is now a test.

- **A count points one way** (HG-022-01, -02). A count of routes longer than 26 km matched "the shortest route is
  26 km" on the figure, so the true claim was refused as `COUNT_CONTRADICTS`; and a count of none shorter than 26
  backed "nothing is longer than 26 km". Comparisons now carry a direction on an axis ("longer" / "shorter",
  "faster" / "slower"; "more", "above", "highest" meet any axis), and a count that points the other way from the
  claim's exceptions neither refutes nor backs it. A result can state the comparison with the count
  (`{"k": 2, "n": 3, "figure": 26, "op": ">"}`); that is the only direction, and a measurement whose name points the
  other way is refused as `MEASUREMENT_MISMATCH`. Without one, a name and key that point opposite ways can widen what
  a count refutes, never what it backs.
- **"No route is longer than 26 km" is an absolute** (HG-022-02), like "nothing is longer": it needs a count of
  exceptions. Only a "no" that opens its clause, followed within three words by a copula and a comparison, is read
  this way ("routes that visit no town twice" is not one).
- **A unit of record said with a verb** (HG-022-03). Only "is / are / was / were" stated a unit, so "recorded parcel
  weights use pounds" went in beside the note that every recorded parcel weight is in kilograms. A short, fixed list
  is read too: use, recorded / measured / expressed / given / listed / reported / denominated / kept / stated /
  written / logged / entered / priced / quoted in. A hedge ("might be recorded in pounds") asserts nothing.
- **Two things that share a word are two things** (HG-022-04). "Passenger weights are recorded in pounds" was refused
  against a source saying shipping weights are in kilograms, on the word "weights". A unit is now compared only when
  the two subjects have the same head and don't each carry modifiers the other lacks entirely; every clause of the
  source is read, and one that says the claim's unit of that thing means no contradiction.
- **A quantity is not a unit of record** (HG-022-05). "The parcel mass is about 2.2 pounds", citing "the parcel mass
  is one kilogram", was refused: a unit after a number ("2.2 pounds", "one kilogram", "36 kg") is a quantity, and
  isn't compared. The refusal no longer says a quantity can't be in two units; it says the source doesn't support the
  statement.
- Limits: which thing a subject names and which unit a record uses are read from words, not typed; conversions
  aren't checked, so "2.2 pounds" against "50 kilograms" goes in; verbs outside the list aren't read; the "no X is
  longer" pattern is narrow ("there is no route longer" isn't read); and a direction is read only from the comparison
  words above.

## 0.7.22 — 2026-11-01: a label can't move a count, every part of a claim is checked, units rule each other out

Fixes from an independent audit of 0.7.21 (HG-021-01 to -04); each case below failed on 0.7.21 and is now a test.

- **The result says what a count is about, not its label** (HG-021-01). 0.7.21 read a count's figure from its
  free-text name, so renaming the count of 2 beyond 93 "worth more than 140" moved it off "the highest value is 93",
  and the false claim went in. An instrument can now state the figure with the count
  (`{"k": 2, "n": 1024, "figure": 93}`); that figure is the only one, a measurement whose name says another is refused
  as `MEASUREMENT_MISMATCH`, and the figure accounts for the number in the statement. Without one, a name that
  disagrees with its key adds a figure and never replaces one: a count that finds exceptions refutes a claim at either
  figure, and a count of none vouches only when both are the claim's.
- **Every absolute and every extreme in a claim is checked** (HG-021-02). A true "nothing worth more than 140 fits
  among the 1,024 selections" ended the check, and "the highest value is 93" beside it was never looked at. One check
  now runs per figure the absolutes are about, and the extreme is checked as well.
- **A source that states another unit of the same kind isn't support** (HG-021-03). Only a claim that denied or
  doubted the source's word was compared with it, so "the recorded weights are in pounds", citing the note that every
  recorded weight is in kilograms, went in. Units of mass, length, temperature and volume, and currencies, now rule
  each other out when the claim and the source say them of the same thing (`SOURCE_CONTRADICTS`). A clause that only
  converts ("in kilograms, about 2.2 pounds each") or states a condition ("if the weights are pounds") asserts
  nothing. `conduct()` counts saying the ruled-out unit again as saying the claim again.
- **`shown_false` is not a lying rate** (HG-021-04). The `conduct()` docstring now says so: it adds up contradictions
  by the record's own count and by a cited source, and a source can be wrong. Read `by_count`, `by_source`,
  `corrected`, `reasserted` and `still_saying` instead.
- Limits, unchanged: contradictions in meaning outside the unit families aren't checked; a claim that drops the
  citation or count that would contradict it is not checked against it; `strict_claims: false` runs no claim checks;
  and a result without a stated figure still relies on its key to say what it counted.

## 0.7.21 — 2026-11-01: counts at the claim's figure, scoped negation, conduct by kind

Fixes from an independent audit of 0.7.20 (HG-020-01 to -04); each case below failed on 0.7.20 and is now a test.

- **A count bears on a claim only at the figure the claim names.** A count says what lies beyond one figure
  ("fitting selections worth more than 93"). In 0.7.20, binding a count of nothing beyond 140 beside the count of 2
  beyond 93, in either order, let "nothing worth more than 93 fits" and "the highest value is 93" in (HG-020-01); and
  a count beyond 93 refused the true "the highest value is 95" as `COUNT_CONTRADICTS`, which `conduct()` then held
  against its author (HG-020-02). Now a count of exceptions at the claim's own figure refutes it whatever else is bound
  beside it, and a count at another figure neither refutes nor rescues it. A count says its figure in its name
  ("more than 93", "above 93"); a number at the end of a key counts only when it is a figure the claim names, since it
  may just number repeated counts (`worth_more_2` is the second count, not one beyond 2). A count that names no figure
  is read as before.
- **A source's "not X" negates X, not its whole sentence.** "Every recorded weight is in kilograms, not pounds" used
  to be skipped for its "not", so it supported a claim of pounds (HG-020-03). A negation now reaches to the end of its
  clause; "the weights were not recorded in kilograms" still asserts nothing about kilograms.
- **Conduct says which contradiction it was, and describes behaviour, not intent** (HG-020-04). `conduct()` adds
  `by_count` (the record's own count contradicted the claim) and `by_source` (a source the author cited as support
  says otherwise: the citation doesn't support the claim, which is not proof it is false, since a source can be
  wrong). `shown_false` is still their total. Its sentence names each kind, and a last word that was refused now
  reads "contradicted by the record". The docstring no longer reads intent into it: conduct is evidence for a
  reviewer, not a verdict on anyone.
- Limits, unchanged and now stated: a claim that drops the citation or count that would contradict it is not checked
  against it, and an investigation with `strict_claims: false` runs no claim checks.

## 0.7.20 — 2026-11-01: a claim the record can show false, and who keeps making it

- **A claim the record's own counts show false is refused as false** (`COUNT_CONTRADICTS`). "The shortest route is
  31 km" beside a bound count of 2 of 81 routes shorter, or "nothing worth more fits" beside 1 of 1,024 that does, used
  to fail at most as a missing denominator; now the count is named as the contradiction. An extreme claimed of a figure
  no answer reaches is refused too, when the instrument also counts what reaches the figure exactly (0 of n). Not
  claims: a denied extreme ("120 is not the highest"), the domain a stated count ran over ("a count of every route
  finds 1 of 74 shorter") and a stated count itself ("is 1 of 63 routes").
- **A source cited as support that says the opposite is refused** (`SOURCE_CONTRADICTS`): "the weights are in
  pounds" citing the note that every weight is in kilograms, or casting doubt on what that note asserts without
  denying it ("not independently established", "the only note calling them kilograms"). It no longer counts as a
  line of support for the claim that contradicts it.
- **Conduct: who corrected and who kept saying it.** `Graph.conduct(inv, author)` reads the refusal log per author:
  claims shown false, corrections, the same claim said again (`reasserted`; a correction that names the old figure to
  deny it is not a repeat), and where each author ends (`still_saying`, `moved_off`, `ends_false`). Refusal rows carry
  the event `seq`, so a claim accepted later that moves off a refused one is seen.
- `content_words` stems a word and its inflections alike (route / routes, fits / fitting), so a count's name meets
  the sentence it bears on. `language.SUPERLATIVE` is exported. Tests: `tests/test_contradictions.py`.

## 0.7.19 — 2026-10-31: linked records, drawn together

- **The Explorer draws linked records together.** When an investigation pins nodes of other records (pinned
  references, 0.7.8), its graph now draws each of those records beside it, each in its own box, and follows their
  pins in turn: a parent that pins child 1 and child 2 shows all three, with every pin drawn from the citing source to
  the node it pins. Each record is read as its own bundle with its hash chain re-verified, and each pin is checked
  against the version it names (`checkPin`, held to `verify_reference`'s verdicts by `tests/test_linked_records.py`):
  green when the hash matches, amber when the node was revised since, red when it was withdrawn or doesn't match.
  Beside each pin is the pinned node's standing in its own record. Nothing is merged; the records are laid out in
  columns by distance, each mirrored to keep its pins short. A *Linked records* panel under the graph lists each
  record, its chain, and every pin into it; the overview has a card, and a node of a linked record opens in the
  drawer from its own bundle. Following stops at three links and twelve records by default (`linkDepth`,
  `linkMax`); another site is read only when the viewer asks (`linked: 'same-origin' | 'all' | 'off'`), and a page
  can map record URLs to bundles (`records`, `recordUrl`). `HypGraph.linkRecords`, `checkPin`, `bundleReferences`,
  `normRecord` and `resolveWith` are exported. Translated into es, fr, de and zh-Hans.
- **A worked example on the site.** `hypgraph.demos.linked` builds three records joined by pins: Broad Street, 1854
  (the demo, unchanged), East London, 1866 (Farr's inquiry, which pins Broad Street's comparison as what it repeats)
  and a synthesis, London's water, 1854–1866, which pins claims in both. `examples/linked/` serves each record as
  its own page and bundle, opening on the graph.
- The site's `.sub` style no longer leaks into the app's card headings.

## 0.7.18 — 2026-10-31: a scoped bundle can't call an active node superseded

- **A scoped bundle can't show an active node as superseded and still say its views are checked.** A re-audit of
  0.7.17 found that a bundle naming a `scope.inv` (which the chain doesn't cover) could show any node, an active claim
  or the investigation itself, as superseded, and verify against its published head with `views: "checked"` and
  coverage complete: the verifier let a scoped bundle call any non-withdrawn node superseded, because links from
  other investigations are left out. Now, in the Python and browser verifiers alike, that allowance applies only
  when events really are redacted (without them every link is in the bundle, so the lifecycle fails) and only to a
  type a `supersedes` or `corrects` link can point at (never an investigation or a review), and even then the views
  are `"unconfirmed"`, not `"checked"`, with a warning naming each node; `hypgraph verify` prints
  `views: NOT CHECKED`. The Explorer header shows a *views not checked* pill for `historical` and `unconfirmed`
  views, and the verify page names both instead of calling them checked (`tests/test_verify_scoped_views.py`).
- **The spec says what a verifier does with lifecycles.** `docs/spec.md` and `docs/verification.md` no longer say a
  verifier accepts the value either rule gives: the current rule is authoritative, a 0.3-only lifecycle is
  `historical`, a scoped one superseded from outside is `unconfirmed`, anything else fails.

## 0.7.17 — 2026-10-31: a superseded node can't verify as active

- **A superseded node can't verify as active.** A pre-launch audit of 0.7.16 found that the verifier accepted a node's
  lifecycle under either the current rule or 0.3's, which counted only an active replacement: in a chain RS3
  supersedes RS2 supersedes RS1, 0.3 calls RS1 active, so a bundle edited to show RS1 active verified with
  `views: "checked"`, its chain, rows and head untouched; setting the bundle's `generator` (which the chain doesn't
  cover) to 0.3 also turned `--standing` from a problem into "not checked". Now, in the Python and browser verifiers
  alike, a lifecycle is checked against the current rule only. One that matches only 0.3's rule still verifies (a 0.3
  export shows it so) but the result says `views: "historical"`, not `"checked"`, and the warning names each such node
  and what the current rule makes it; `hypgraph verify` prints `views: NOT CHECKED`. The generator is never consulted.
  Covered for `supersedes` and `corrects`, chains of three, withdrawn replacements, scoped bundles and a forged or
  deleted generator, with the browser verifier held to the same verdict, warning and coverage
  (`tests/test_verify_lifecycle.py`).
- **The Explorer and the website speak Spanish, French, German and Simplified Chinese.** The UI's strings are in a
  table (English, the source, in `hypgraph.js`; translations in `hypgraph.i18n.js`, loaded on demand or registered
  with `HypGraph.addStrings`). The language comes from `?lang=`, the host page's `lang`, a saved choice, then the
  browser's, else English; a switcher in the header changes it (`langSwitch: false` hides it in an embed). The main
  site pages are built in each language under `site/<lang>/` by `dev/build_site.py` from `i18n/site/<lang>.json`,
  with `hreflang` alternates, a language menu and a note that the English is authoritative. `i18n/glossary.json`
  fixes how claim, standing, supersedes, withdrawn, head, bundle, scope … are rendered, and the tests hold every
  table to it (`tests/test_i18n.py`). What the verifier, the engine and the CLI say stays English and byte-identical
  in Python and JS: agents and audits parse it.

## 0.7.16 — 2026-10-31: a bundle's scope must be a real one

- **A bundle's scope must be a real one.** A re-audit of 0.7.15 found that `scope.inv`, which the chain doesn't
  cover, was taken on trust: naming a claim, question, result or hypothesis as the scope showed that one node, hid the
  rest of the record, and still verified against the published head; a full export of two investigations relabelled
  as one hid the other. Now, in the Python and browser verifiers alike, the scope must name an investigation and the
  bundle hold only that investigation's nodes, as an export writes it; a bundle without a scope may not redact events
  (`tests/test_verify_scope.py`).
- **The redaction warning says what can't be checked.** A redacted event keeps only its hash, so that it lies
  outside the investigation is the bundle's word; the warning says so, and that only the full record against the
  published head rules out a change hidden among them.
- **The verify page names the scope from the verified investigation**, not from the unhashed `scope.title`, and says
  whether the bundle's derived views were checked or absent. The spec says what `ok`, `coverage` and `views` vouch for.

## 0.7.15 — 2026-10-31: derived views must carry every fact the rows fix

- **Derived views must carry every fact the rows fix.** A re-audit of 0.7.14 found that a derived field was compared
  with the verified rows only when it was there: deleting a withdrawn claim's `state.lifecycle`, or its whole `state`,
  still verified as complete, and the explorer then showed the claim as active. An emptied investigation list, nodes
  without a title, author or code, and links without an end verified too. Now every one of those facts must be present
  and agree, in the Python and browser verifiers alike; the lifecycle is derived again from the verified rows
  (withdrawals and live replacements, under the 0.3 rule or the current one, as the exporter may have used either)
  instead of only checked for "withdrawn"; the investigation list must show each investigation once. A bundle exported
  without derived views still verifies and says so (`views: none`) (`tests/test_verify_views.py`).
- **A malformed bundle fails instead of raising.** An event body that isn't a JSON object fails with that problem; a
  field missing or of the wrong kind fails as malformed; `hypgraph verify` on a file that isn't JSON says so.
- **The explorer never defaults a missing lifecycle to active.** It shows *unknown*.

## 0.7.14 — 2026-10-31: the verifier trusts its caller's policy, and derived screens say they are as exported

- **The verifier trusts its caller's policy, not the bundle's.** A re-audit of 0.7.13 found that the bundle and
  browser verifiers took the importer's name from the bundle's `policy`, which the chain doesn't cover. Older events
  don't vouch for the author of a node the importer wrote, so naming a historical writer the importer let an edited
  bundle re-attribute that writer's nodes, and it still verified against the published head. Now the default
  importer is used unless the caller supplies a policy (`hypgraph verify --policy FILE` / `--importer NAME`,
  `verify_bundle(b, policy=…)`, `verifyBundle(b, head, {policy})`); every supplied field must match the bundle's, and a
  different stated importer is reported. `--standing` derives under the supplied policy and names the fields it took
  from the bundle on trust (`tests/test_verify_trust.py`).
- **Coverage is stated at the top.** Every result says `coverage: complete` or `partial` (fields no event vouched
  for, or redacted events); the CLI prints it, and the explorer shows a *partial coverage* badge.
- **Reports, stages and work orders are labelled as exported.** The explorer's Overview, Pipeline, Evidence, Work
  orders and Report screens say, for a bundle, that what they show is as exported and not verified, and how to
  re-derive it; the Report's subtitle no longer says its interpretation is checked. `dev/ui_smoke.py` fails a bundle
  view that drops the label.
- **Sequence numbers must run 1 to n**, in bundles and graph files: they aren't hashed, so a relabelled or gapped log
  now fails.

## 0.7.13 — 2026-10-31: verification checks every row, and examples for agent frameworks

- **Verification checks every row, both ways.** A pre-launch audit found that `verify_bundle`, `verify_file` and
  the browser's `verifyBundle` only checked that each row present matched an event. A bundle or graph file with a
  withdrawal, a version, a link, a lease or a whole table removed still verified, so a withdrawn claim could come
  back to life through `load()`; changed authors, times, link ends, reasons and duplicated rows passed too. Now every
  row must be written by an event and match it field by field, every row an event wrote must be present, and no key
  may appear twice, in Python, SQLite and the browser alike (`tests/test_verify_complete.py`, which also checks the
  browser verifier agrees on every case).
- **Events hash every field of the row they write.** New events carry `reason_sha` (create, revise), `why_sha`
  (link, retract, withdraw), `note_sha` (leases), a review's `code` and `inv`, and `as` when the importer credits
  another author. Only the importer may. Older records still verify: what their events don't cover is reported as
  `unchecked`, field by field, instead of passing silently.
- **Derived views are checked; standing is labelled.** A bundle's `derived` views must agree with the verified rows
  on every fact the rows fix (nodes, live links, titles, authors, times, withdrawn or not); an edited view fails.
  Standing can't be checked from the rows, so the result says `standing: {checked: false}`; `hypgraph verify
  --standing` re-derives it with the same engine version and fails on a difference. The explorer shows a separate
  "standing as exported" badge beside the verified one, and a banner over a record that doesn't verify.
- **The verify page takes a published head** and lists the fields an older record doesn't cover.

- **A LangChain example** (`examples/frameworks/langchain_agent.py`): `create_agent` with the record's tools from a
  `MultiServerMCPClient` session, the same story as the others. It runs in the `frameworks` CI job.
- **Examples for agent frameworks** (`examples/frameworks/`): LangGraph, PydanticAI, CrewAI, the OpenAI Agents SDK
  and the Claude Agent SDK, each connected to a record through `hypgraph mcp`. All five tell the same story: the
  agent claims a 1.2-point difference is significant, the record refuses with the arithmetic, and the agent writes
  the honest claim, which is accepted. They run offline with a scripted model through each framework's own
  tool-calling path, or with `--real` on a real model. The README covers the one setting each framework needs so a
  refusal reaches the model instead of ending the run. A new CI job runs them all (the Claude Agent SDK, which has no
  scripted mode, gets a wiring check).

## 0.7.12 — 2026-10-31: the trust boundary, verification and docs, reviewed before launch

A pre-launch review of who may write as whom, through every interface. Each fix has a test that failed first
(`tests/test_trust_boundary.py`).

- **A page on another port can't write.** `hypgraph serve` compared a write's `Origin` by host name only, so a page
  served from another port of the same machine (a dev server, an agent-built page) could write to a server running
  without tokens. A browser write must now come from the exact host and port the server was reached at;
  `Origin: null` is refused. Clients that send no `Origin` are unaffected.
- **A `*` token can't write as a reviewer.** `--token SECRET=*` covered every non-reserved name, reviewers included,
  so an agent holding one could review its own work officially under a reviewer's name. A name on a review board
  (the policy's reviewers, or the ones an investigation names) must now be named on a token. Tokens that name their
  authors are unchanged.
- **Only an order's issuer directs it.** `accept_work`, `rework` and `settle` didn't check who called them, so a
  worker (through its MCP seat, say) could rework its own order with an easier `done_when`, meet it and accept it.
  Now only the author who issued an order, or a curator, accepts or reworks it, and `settle` settles only the
  orders its caller issued. HypSwarm's scheduler and lead (which act as the harness that issued the orders) and
  HypMesh pass their suites unchanged.
- **A bad `Content-Length` is a 400.** A non-numeric one crashed the request handler and a negative one held its
  thread until the client hung up.
- **A refused write gets its refusal.** The server read a write's body only after the origin check, and closing on
  an unread body reset the connection on Windows, so a client saw "connection aborted" instead of the 403.
- **More blind adversarial tests:** graph operations on sealed nodes (link, retract, withdraw, revise, lease), the
  work-order lifecycle as the checker (return, accept, rework, cancel, settle), every enumeration route, 25 guesses
  in a row on one record, and eight MCP tools. The chain head is no longer shown to a sealed reader (`/verify`, the
  MCP `verify` tool): it is a hash over sealed bodies, and a reader that is sealed has no use for it.
- **SECURITY.md rewritten** for what the record enforces, which interface is trusted, what tokens do and don't
  protect (writes, not reads), what blind orders protect and where they don't apply, and what verification shows.

Verification against a published head, and a clean-install walkthrough in CI:

- **`hypgraph verify --head HEX`** (and `verify_bundle(b, head=...)`, `anchored(res, head)`) fails unless the chain
  ends at a head published elsewhere. A chain only shows it is consistent with itself: whoever can write a record can
  change a claim and recompute every hash, or cut the record short, and it still verifies. `tests/test_anchoring.py`
  does both and shows each verifying on its own and failing against the published head. `verify` now prints the full
  head, the thing to publish.
- **[docs/verification.md](docs/verification.md)** separates the four guarantees (internal consistency, not
  rewritten since published, provenance of the evidence, truth of a claim) and shows how to publish and sign a head
  with tools readers already have (a paper, a signed tag, `ssh-keygen -Y sign`, a timestamp).
- **`dev/e2e_install.py`** installs HypGraph into a fresh environment and does what the README and `--help` say, as
  someone who has never seen the repository: a record, an experiment and its result, a claim accepted and one refused
  with the honest version, a review, an export, and verification elsewhere with no graph file. CI runs it on the
  built wheel (with the MCP extra) and on the sdist, on Ubuntu and Windows; the release job runs it before
  publishing.

Docs reconciled, GitHub Releases, a linter in CI:

- **Docs match the code.** `docs/review-2026-10-24.md` gets a status table: each finding checked against 0.7.11 by
  running it, with the evidence (eight resolved, one in part). `docs/PLAN.md` says what is done, what moved
  (authentication, anchoring) and where HypGraph ends and HypSwarm, HypMesh and HypDMZ begin. The README lists the
  work-order tools and points to SECURITY.md. AGENTS.md, the Agent Skill and llms.txt tell an agent holding a work
  order to start with `my_work()`, and that a blind order's sealed tools are expected, not an error.
- **GitHub Releases.** The release job creates one for each tag after PyPI has the files: the changelog's section,
  how to install, and where to check provenance (`dev/release_notes.py`, which you can run to preview).
- **[docs/RELEASE-READINESS.md](docs/RELEASE-READINESS.md):** the pre-launch review's findings, what was fixed and
  tested, the limitations accepted, what is deferred, and the recommendation (conditional go).
- **pyflakes in CI** (`ruff check`, rules `F` only): undefined names and dead imports, not style. Five unused imports
  and one unused variable removed.

## 0.7.11 — 2026-10-30: a sealed checker can't learn the answer by asking

An adversarial test on a local HypMesh planted a 5-digit reading and 12-digit tags in a lead's sealed nodes and
attacked every route as the blind checker. Nothing leaked directly, but the checker could tell a right guess from a
wrong one, and 60 requests recovered the reading exactly. Fixed:

- **Errors no longer mark a right guess.** Answers scrubbed only the numbers the sealed material carries, so a route
  that echoes its input (`resolve`, `node`, `why`, `order`, `check_work`, a refused write) answered "no node
  '[sealed]'" for a right guess and "no node '48220'" for a wrong one. While a reader is sealed, every number in an
  error is now blanked, secret or not; the MCP seat does the same.
- **A write is answered with the view after it.** The checker's own new numbers were scrubbed with the view from
  before the write, so a result carrying the right reading came back "[sealed]".
- **No check reads sealed material for a sealed writer.** A claim bound to the sealed result was refused with an
  unbound number for a wrong guess and passed that check for the right one, and the auto-bind looked the guess up
  in the sealed results without any id given. A sealed writer may now link to a sealed node only to say its own work
  supports, challenges or tests a hypothesis; binding to, resting on, reviewing, revising or ordering work on sealed
  nodes is refused with one message before any check runs, and a seat holding a blind order issues no orders.
  `Graph.sealed_from(hide)` lets a host apply its reader's view to writes, so writing under another name doesn't
  escape the seal.
- **The leak check at issue skips what is sealed from the issuer**, which would otherwise answer the issuer's guesses.

`tests/test_blind_oracles.py` asks every request with the right and a wrong guess on fresh records and requires the
same answer; 14 of its 23 tests fail on 0.7.10.

## 0.7.10 — 2026-10-30: fixes from the first live blind run

Claude led a question on a HypMesh and issued a blind order; Codex took the order through its seat and counted the
primes below 1,000,000 whose digits sum to 23 with its own sieve. The record marked its result written blind and
agreeing blind with Claude's, and nothing sealed reached Codex. Four fixes from that run and a phone-width check:

- **Investigations are part of the problem statement a blind checker reads.** Only the order's own investigation
  and the curators' were. A lead whose framing lived in a second investigation had it sealed, the numbers that
  define the problem (1,000,000; 23) read as secrets, and an honest blind order was refused. Questions and
  investigations say what is being found out; don't put answers in them.
- **`my_work` without an investigation lists your orders in every investigation.** It asked "which
  investigation?" when a record held two, and the seat's first call failed.
- **`produced_by`, `generated_by`, `output_of`, `executed_by` and `tested_by` are read as the relation they
  invert.** The node types fix the direction, so the link is turned round. Codex's first result was refused for
  `produced_by`.
- **On a phone, every tab of the embedded app can be reached.** The embed's `overflow: visible` beat the narrow
  rule that makes the nav a scrolling strip. On hypdmz.com at 375 px, four of the eight tabs (Evidence, Work
  orders, Audit log, Report) sat past the edge with no way to scroll to them. The nav now scrolls, and the embed
  clips sideways, so the closed drawer can't widen a host page that doesn't clip it.

## 0.7.9 — 2026-10-30: blind work orders

- **A checker can measure without seeing the answer it checks.** `issue_work(..., blind=True)` (MCP `issue_work`
  `blind=true`, HTTP write `blind`) issues a work order whose assignee works blind until it returns the order.
  The order text gives the objective, the method and the target by code only. Hypotheses and their predictions,
  results, claims, reviews, runs and their code, sources, other orders and other teams' attempts are sealed.
  `hypgraph.blind` holds the rules:
  - **At issue**, a blind order is refused with a prediction, with a predicate that has to read its target
    (`reviewed`, `no_open_objection`, `report_clean`), for an assignee that has already written in the record, and
    when its objective, method or note quote a number only the sealed material carries.
  - **At read**, the MCP server seals its seat while that seat holds an open blind order. The tools that summarise
    what others wrote are refused, `show` refuses a sealed node, `find` leaves sealed nodes out, and every number
    only the sealed material carries is scrubbed from what comes back. `blind.dispatch(g, ..., keep=)` gives a host
    the same redaction for its HTTP routes, per reader (HypMesh uses it). `hypgraph serve` and the Python API read
    the whole record: a file is only as blind as whoever holds it.
  - **In standing**, a result its assignee wrote inside the window is `blind` (and `sealed` while the window is
    open). After the return, a blind result that repeats an earlier result's numbers `agrees_blind` with it
    instead of restating it, and a claim or hypothesis counts its `blind_lines`: "2 independent lines of support
    (1 written blind)". A result revised after the window closed is no longer blind.
  - The record sees writes, not reads. A seat that read the record before its order was issued has already seen
    what is now sealed: give a checker its order first.

## 0.7.8 — 2026-10-29: pinned references between records

- **A record can cite a node of another record and prove what it read.** A `source` takes four more fields,
  `record` (the cited record's URL), `node`, `version` and `hash` (sha256 of that version's canonical body, the
  same hash the cited record's chain holds), all four or none (`SHAPE_REFERENCE` otherwise). `Graph.pin(node,
  record_url)` / `GET /api/graph/pin/{id}?record=` build them for one of this record's nodes, with the node's own
  words in `citation` and `says`, so the citing record reads without the cited one. `Graph.references(inv)` /
  `GET /api/graph/references` list the sources here that pin other records, with who cites them.
  `hypgraph.verify_reference(fields, fetch=)` reads the cited record's node route (HTTP, or a host's own reader)
  and reports whether the pinned version still hashes to the pin, whether it was revised since, and whether it
  was withdrawn. The citing record never trusts the other's status; it trusts the hash it pinned. A record stays
  one trust boundary; a host that holds many (a mesh) derives the network from these pins.

## 0.7.7 — 2026-10-29: `hypgraph serve` inside a container

- **`hypgraph serve` bound to `0.0.0.0` answered 421 to everyone.** Its Host check knew only the bind address,
  which no browser sends: inside a container with a published port, every request arrives as
  `Host: 127.0.0.1:<host port>` and was refused as a possible DNS rebinding. A wildcard bind now accepts the
  loopback names (the port was never part of the check), and `--allow-host NAME` (repeatable; `allow_hosts=` on
  `make_server` / `serve`) adds a LAN or service name. A wildcard bind still never means "any Host".
 
## 0.7.6 — 2026-10-29: the swarm as swimlanes, and the UI walked on a real record

- **UI polish from a walk of a real swarm record.** Identical alerts collapse into one line with a count (a seat
  that looped four times showed four lines); the six KPI tiles fit one row where the sixth sat orphaned below;
  the grids break on the panel's own width, not the window's (container queries: an embed is narrower than its
  page, and the Live view squeezed its graph to 130 px between two full columns); the theme follows the OS unless
  the visitor chose one; a refusal relayed twice ("claim refused: claim
  refused:") reads once in the event stream; `mount(…, {embed: true})` marks an app on a page of its own: it
  grows to its content and scrolls nothing inside, so a wheel over it moves the page (twenty ticks over the
  homepage's embed used to move nothing), and its feed shows the latest 15 events. hypgraph.com: the hero's chips no
  longer wrap mid-phrase.

- **The Live view shows the swarm as swimlanes.** Seats as rows in the order they first took work, time across,
  every work order a bar coloured by how the record settled it (accepted, reworked, returned, cancelled, in
  flight), every model call a tick above the bar and every tool call a tick below, refusals and failures in
  red, the scheduler's reworks and escalations as marks on their own row, and the playhead sweeping across
  during replay on a fixed axis. Hover anything for its figures; click an order for its trace. Drawn from the
  telemetry the view already holds, no dependency.

## 0.7.5 — 2026-10-28: a cited source is a line of support, and a finding of failure is not a fall

- **A cited source is a line of support, and a succeeded run's "failed" outcome is a finding, not a fall.**
  A knowledge claim that cites its sources (`cites` → source, or `derived_from` → source) read "no live
  support · unverified" even after 0.7.4 counted bound results; the source is what such a claim rests on,
  and its line is `external`. And a result with `outcome: failed` counted as a broken premise whatever its
  run did: testers write "failed" for the code under test failing its spec (30 results in the challenge
  records, 13 carrying checked claims that then read UNSUPPORTED — every support has fallen). A result a
  succeeded run produced did happen; it falls only when there is no run or the run did not succeed.

## 0.7.4 — 2026-10-28: a bound result is a line of support, and a relation word is read as the relation it names

- **A bound result is a line of support.** A claim's standing counted only `supports` edges into it, so a claim
  that derives from a result and binds its numbers to it by `measurements` read "no live support", evidence
  "unverified" — 73 of 113 active claims in the challenge records, each with its result right there. The results a
  claim derives from and the results its measurements bind now count as lines of support (each once; shared runs
  or data still merge into one line), so the evidence profile is the result's — lab-recorded when the instrument
  filed it — and `unsupported` means what it says.
- **A relation word the grammar doesn't have is read as the relation it names.** "generated", "created", "wrote"
  → `produced`; "ran", "executed" → `executes`; "test" → `tests`; "answer" → `answers`; "used", "reads" → `uses`;
  "contradicts", "refutes" → `challenges`; and so on (`schema.REL_SYNONYMS`, one reading each), noted on the
  link like a translation. A hypothesis "derived from" a claim or result is `motivated_by` it; an experiment
  "derived from" a hypothesis `tests` it. The link refusals left in the runs after 0.7.3: an unknown relation
  `generated`, `derived_from hypothesis → claim`.

## 0.7.3 — 2026-10-28: the refusal log sees everything — results, shape, links — and reads a link as the relation that joins

- **A link is read as the relation that joins.** A relation that can't join its two types, where one relation says
  the same thing between them, is applied as that relation with a note, like a link turned round: an experiment
  that "supports" a hypothesis *tests* it; a run that "uses" an experiment *executes* it; a result, experiment or
  decision that "answers" a question is *part of* it; a claim or result that "uses" or "rests on" an artifact is
  *derived from* it; a decision that "supports" a claim is *based on* it (`schema.TRANSLATE`). An experiment may
  `uses` the artifact it is designed on. A link refused on its pair is matched as fixed by the link that then
  lands between the same nodes. Read off 23 `LINK_NOT_ALLOWED` refusals in nine runs: every hint named the
  relation, 3 were taken; 19 of the 23 pairs now go through.
- **Shape refusals are logged, coded, and say where the thing goes.** A sixteen-challenge sweep's run logs held
  217 refusals for a field, an option or a link the schema doesn't have, against the 79 overclaims its refusal
  logs held — the larger friction stream, and invisible to the log, the report and the replay. Now `clean_body`
  and the link check raise a `GraphError` whose `problems` carry a code (`SHAPE_UNKNOWN_FIELD`,
  `SHAPE_NOT_AN_OPTION`, `SHAPE_MISSING_FIELD`, `SHAPE_TOO_LONG`, `SHAPE_TOO_SHORT`, `SHAPE_WRONG_TYPE`,
  `LINK_NOT_ALLOWED`, `LINK_UNKNOWN_RELATION`, `LINK_NO_NODE`) and a fix; `create`, `revise` and `link` log the
  refusal with the body (`detail.type` `shape` / `link`) before raising it; `refusal_report` counts them apart under
  `shape`; `replay_refusals` skips them. The three messages the sweep hit most now say where the thing goes: `code`
  on a result belongs to the run (`code=[…]`, `produced` → the result); an experiment's `expected` goes on its
  `tests` link (`data: {expected: …}`); and `outcome must be one of …` explains each option. An option written as
  a leading word and a sentence ("negative — no outcome remains significant after correction", "H1 confirmed: the
  setting loses its edge") is read as the word, the sentence kept as the evidence note; a leading "fail" stays
  refused as ambiguous (negative if the code ran and showed the opposite, failed if it didn't run). Plural and
  result-kind words on a claim's `kind` (`findings`, `computed`) map to `finding`. Read off the 17 outcome bodies
  the new log captured in the first runs on the branch: 9 were whole sentences with no option word (refused, now
  with the fix), 8 began with one.
- **The refusal log treats results like claims.** A refused result is logged in full (its summary as the statement,
  `RESULT_RESTATES` included), the author's next accepted result that says the same thing — by its words, or by
  carrying at least half of the refused result's value keys again — fixes it (`fixes_refusals`, and the report's
  *fixed* column, which showed 0 for every result code), and `replay_refusals` runs results through the value and
  profile result checks as their author, claims through the profile checks too (an `EDGE_WITHOUT_TRIALS` refusal
  used to replay as `passes`), and counts `RESULT_RESTATES` and typed-node refusals as skipped instead of replaying
  a decision's choice as a claim. Found replaying 846 refusals from the challenge studies.
## 0.7.2 — 2026-10-28: the honest sentences the rules were refusing, and a nominal effect can't hide its correction

- **Honest sentences the rules were refusing.** Read off every refusal logged in 96 records of the challenge studies
  (846 refusals; each fix replayed on all of them):
  - absolutes over a set the sentence counts ("cases 1-7 all pass", "none of these 49 rows", "all other 19
    outcomes"), "almost all", an interval "entirely below zero", "distinguishable from zero", "cannot be used /
    asserted / ruled out", and "proven" beside a bound gap or bound, are not generalisations and pass;
  - "no difference remains significant after correction" denies a test, it is not an exclusion that needs power;
    "the interval excludes zero" is interval language;
  - a p-value is found by its key's tokens (`welch_two_sided_p`, `raw_p_steps_k`, `steps_k_p`), not only by a `p_`
    prefix, so "significant" beside such a field is tested rather than refused;
  - a key written beside its value ("n_sig_holm = 0 of 20") is not `KEY_FOR_NUMBER`; "two-sided" and a date are not
    unbound numbers;
  - a result value's `k` and `n` must be numbers (`VALUE_NOT_A_NUMBER`): `{"k": "40/50", "n": "rank 1 of 20"}` is a
    label in a count's clothes, and it crashed a run downstream;
  - the instrument's re-execution of a run (what the code printed) is not asked for `feasible` beside an objective
    or fees beside a return — the original result was; a benchmark's return (buy-and-hold, flat) is not a return
    the strategy earned, and `BACKTEST_WITHOUT_COSTS` now names the fields it took as returns.
- **`UNCORRECTED_EFFECT` reads its qualifier beside the effect word.** "Uncorrected" counts within 20 words of
  "changes" / "differs", in the same sentence — not anywhere in it. A 70-word finding "The supplement changes
  steps_k … while dropping its uncorrected p < 0.05 claim" had passed on the word's presence alone.
- **A nominal effect can't hide its correction in the scope.** New code `UNCORRECTED_EFFECT`: a finding that says an
  outcome changed, differs or is significant, while a live result in the same investigation holds that outcome's
  corrected p-value (Holm, Bonferroni, FDR, …) at or above 0.05 or a count of 0 outcomes surviving correction, is
  refused unless the sentence says the test is uncorrected ("differs at uncorrected p < 0.05"), or it binds a
  corrected value and names the correction — or it is filed as a lead. The
  refusal quotes the result and field. "Not significant after Holm correction (Holm p = 0.25)" beside a bound
  nominal p of 0.012 is read against the corrected p, not refused as `SIGNIFICANCE_CONTRADICTED`. Found in a
  20-outcome trial study, where two of twelve runs settled "the supplement changes steps_k" as a checked finding,
  hedged only in the scope field, while the same record said nothing survived correction.
- **The record's own bookkeeping decision isn't a position.** `accept_work` settles an order with a decision
  whose text quotes the order's objective and that rests on the claims that met its predicates. Under trading, a
  kind-less decision with position words in its text and `based_on` links counted as a position, so settling an
  order on "should the desk take a paper position?" was refused for want of a stop (POSITION_WITHOUT_STOP) and the
  run crashed as it settled. The decision now carries `kind: accepted`; a real position still needs its stop.

## 0.7.1 — 2026-10-27: a computed answer needs its code, and opposed answers keep a question open

- **A computation nobody can re-run doesn't settle a computational question.** The optimization workflow's
  `solved`, trading's `backtested` and the scientific workflow's evidenced stage (`result_exists` under a
  scientific profile) count only results something can re-run: the run that produced them carries its code, or
  it is the instrument's (`kind=lab`). Through the hypswarm CLI, with no tool that executes code, the seats wrote
  "exact DP over capacity" and "brute force over 2^21" as prose; the verifier passed a wrong optimum (757 for
  656) and the question settled. The gate now says which results report a computation with no code behind it.
  `workflow.rerunnable(snap, result)`.
- **A question settles only when every live answer to it is checked.** A checked answer beside a live unchecked one
  used to settle the question, and the two may disagree: in a real-model trading run a reviewer re-ran the numbers
  behind "no look-ahead" and checked it while "it is look-ahead" stood unchecked on the same question. The board row
  now says `answered` with the unchecked answers named (`unchecked`), the reviewed gate names them, and completion
  waits. An answer nobody may review (its author is the only reviewer) doesn't block; the row lists it under
  `unreviewable`. `derive.unchecked_answers` / `unreviewable_answers`.
- **Measuring returns isn't trading them.** Trading's BACKTEST_WITHOUT_COSTS no longer fires on a result that counts
  its returns (`n_returns`, `insample_n_returns`, a value in units of returns, days, bars or trades) or reports a
  statistic of them (an autocorrelation, its t, p, standard error or CI). A return, P&L or Sharpe still needs its
  costs. A real-model run lost eight writes measuring a lag-1 autocorrelation.
- **A confidence interval that excludes zero isn't an exclusion.** "Excludes zero", "excludes 1" (a ratio's
  null) and "rules out chance" say an effect is there, so they no longer need a power check
  (EXCLUSION_WITHOUT_POWER). "Rules out an effect" and "no effect" still do.

## 0.7.0 — 2026-10-27: measure questions, and claim checks that know a version from a figure

- **Measure questions.** A question may say `asks: "measure"`, and its workflow's `measure_skips` gates then don't
  apply to it, in `Graph.stage()` and as order predicates. Until now every question met every gate of its profile:
  a timing question was reworked for a diff, a count for a preregistered hypothesis, a look-ahead check for a
  backtest. Real-model runs lost most of their calls to those reworks. `profiles.view()` lists the skipped gates.
- **Claim checks:** dotted versions, inline code and labels (case 8, cases 9–12, #3) aren't figures; a measurement's
  key written in place of its number is refused (KEY_FOR_NUMBER); a statement that says nothing ("Placeholder.")
  is refused (STATEMENT_EMPTY).
- **A rework's predicates are checked like an order's:** an unknown predicate is refused, naming every predicate the
  target can take. A lead had reworked an order with an invented one (`claim_answers_q3`) that could never be met.
- **Trading: a statistic about returns isn't a return earned.** Correlations, hit rates and other diagnostics of
  returns no longer need fees and slippage (BACKTEST_WITHOUT_COSTS); a return, P&L or Sharpe still does.
- **hypgraph.com in the app's design system.** One stylesheet on the HypGraph app's tokens and components, light by
  default, restyles every page. The new homepage:
  - opens on the live app, which can switch between the five workflows, Broad Street and the page's own record;
  - offers the agent and engineer paths, then the facts, what the record refuses, the eight rules and the
    arithmetic of never;
  - ends with the workflows, the deployment options, the page's record and what the record shows and doesn't claim.
- **The homepage proves its figures with its own HypGraph record** (`dev/site_record.py`, now run at every deploy):
  - The instrument measures each figure: tests passing, runtime dependencies, the example records' chains, the bound
    behind the arithmetic of never, and the refused overclaims.
  - A reviewer re-measures each one another way.
  - The page's text is checked against the record with `hypgraph check`, and a copy error fails the deploy.
- **The report check no longer flags "not ruled out" as an absence claim.** Exclusion words that the sentence negates
  are skipped, as absolutes already were. "Up to 58,155 … are not ruled out" and "a leak cannot be ruled out" are
  hedges; the engine's own bound note says it in those words.

- **Derivation scales with the record.** Working out which earlier results a result repeats (`derive.restates`) took a
  pass over the whole graph for every result, recomputing each one's numbers, so deriving a record grew with the
  square of its results. It now reads a per-snapshot index of each investigation's results by the numbers they carry,
  and a result's numbers are computed once per version, shared across snapshots. On `dev/bench.py`'s record: 10,001
  nodes derive in 0.34 s (was 20.35 s), 4,001 in 0.11 s (was 3.65 s). The write-time duplicate check uses the same
  index.
- **Two fixes to carried standing.** Both were found by the test at scale.
  - Results written in the same second were ordered by id, so a result written later could count as "earlier" and
    change what an older result repeats, after the older one's standing had been derived and carried forward. Ties now
    go by write order.
  - Revising or withdrawing a result now re-derives the results that repeat its numbers. They reach it through no
    edge, so they used to keep their old standing.

  The randomized incremental suite now gives results numbers, by several authors, and revises them. It fails on the
  old code (5 of 6 seeds) and passes now.
- `dev/bench.py`: reads, writes and derivation at a given record size, on your machine. The README's performance
  figures come from it.

## 0.6.0 — 2026-10-26: the HypGraph UI, live swarm observability, an example per profile

The Atlas becomes **HypGraph**: one app for every profile, in each profile's own words, that watches a swarm
work as it happens and replays any finished run. The design record is `docs/ui-plan.md`. Nothing in the record
format changes; bundles gain optional fields that sit outside the hash chain.

**The HypGraph UI**, which replaces the Atlas:
- **Eight views in each profile's own words:** Overview, Live, Pipeline, Graph, Evidence, Work orders, Audit log and
  Report. A software investigation shows Requirements and Verifications; a trading one shows Theses and Positions.
- **Overview** has KPI tiles, the completion criteria, each question's stage, a "needs attention" list and recent
  activity. Attention covers stale evidence, contested claims, premises that fell, leases held past their time,
  returned orders, overclaims refused and a broken chain.
- **Pipeline** is a swimlane of the profile's stages, with each gate met or not, its evidence, and what would meet it.
- **Live** shows seats, the record growing and the event stream. It follows `/api/graph/stream` and falls back to
  polling on hosts without it. Any run plays back with play, pause, scrub and speed controls.
- **Drawers:** a node's drawer gives its standing, fields, links both ways, provenance and what would be at risk if
  it fell. A question's drawer gives its stage and gates.
- **Enterprise:**
  - light by default, with dark one key away;
  - WCAG AA text contrast in both themes, checked by a test;
  - every screen is a URL, and Back and Forward work;
  - ⌘K search over views, investigations and nodes, plus keys 1–8, `/`, `t` and Esc;
  - CSV export for tables, PNG and JSON for the graph, Markdown and print-to-PDF for the report, and the bundle;
  - the hash-chain badge, read-only, with no build step.
- **Compatibility for one release:** `atlas.js` and `atlas.css` load the new app, `HypAtlas` is an alias of
  `HypGraph`, and the `--hg-*` theme tokens still apply. Routes a host doesn't serve are hidden rather than failing,
  so PegasusDMZ's older API still works.
- `dev/ui_smoke.py` renders every view of five profile fixtures in both themes, plus an Atlas-style page, in headless
  Chrome. CI runs it.

**Live observability for a running swarm** (with hypswarm ≥ 0.1.0a7's telemetry):
- **`hypgraph serve` streams a swarm's telemetry.** hypswarm writes `<record>.telemetry.jsonl` beside the record: every
  model call, tool call, work order and scheduler decision, as spans. The server serves it at `GET /api/graph/telemetry`
  (paged by byte offset) and tails it into `/api/graph/stream` as `telemetry` events. Ids become `<seq>:<offset>` so a
  reconnect resumes both. A sidecar that appears after the server starts is picked up, and `--telemetry FILE` /
  `--no-telemetry` override the default. Telemetry is shown, never trusted for standing.
- **The Live view shows the swarm working:**
  - each seat's call in flight (the model it's calling or the tool it's running, with seconds elapsed), and its calls,
    tokens, cost and errors;
  - KPI tiles for model calls, tokens in → out and cached, spend, tool calls, errors, and budget used against the run's cap;
  - an event stream merging the record and telemetry, with a filter;
  - a trace for any work order, showing each model and tool call on a timeline;
  - alerts: a tool failing three times in a row, a seat repeating an identical tool call, failed model calls, the
    budget passing 80 %;
  - status from the run's own start and end ("Run ended · settled").

  A record opened before its swarm starts picks the investigation up when it begins. Replay scopes telemetry to the
  replay position. Overview's spend falls back to telemetry when the ledger isn't metered.
- `dev/ui-fixtures/swarm.*` holds a real scripted swarm's bundle and telemetry, and the smoke check requires its trace.

**What the UI needs from the engine:**
- **Each profile speaks its own words.** `Profile.labels` gives the short noun a screen shows for each node type: a
  software question is a **Requirement**, a trading hypothesis a **Thesis**, a decision a **Position**, an
  optimization result a **Solution**. `profiles.view(pid)` returns what a UI needs: the labels for every node type
  (the kernel's word where the profile has none), the meaning of each type, and the workflow's stages, gates and
  report name. The `@1` profiles are frozen and keep the kernel's words. The labels are display only.
- **A bundle carries the workflow views.** Each investigation's `derived` now has `profile`, `stages`, `completion`,
  `board` and `orders` beside the report, so a viewer shows stages and gates without the engine. As before, derived
  views are outside the hash chain and never trusted.
- **Watch a record live.** `GET /api/graph/stream?inv=&after=` pushes every event as it is written, as Server-Sent
  Events. It includes writes from another process on the same file, so a swarm running against the record is
  watched as it works. Ids are event seqs, so a client resumes with `Last-Event-ID`. A comment line every 15 s keeps
  proxies open, and `max_seconds` bounds a read.
- `GET /api/graph/profile?inv=` gives the investigation's profile as a UI speaks it.
- "Atlas" is now the HypGraph UI in the server, the CLI, the README and the skill.

**A live example per profile on hypgraph.com:**
- **Five live examples.** `/examples/` has one page per `@2` profile: scientific, software, trading, knowledge and
  optimization. Each is a HypSwarm run on a real record that opens on its live replay. You see the seats take work
  orders, model and tool calls in flight, writes refused and rewritten, and reviews landing, then you can explore the
  pipeline, graph, evidence and report. The pages load offline from their bundles and re-verify each hash chain in
  the browser. `dev/site_examples.py` rebuilds them from HypSwarm's scripted examples, pacing each reply 0.35–1.4 s,
  and every page says so.
- **A bundle can carry the run's telemetry.** `export(inv, telemetry=path)` and `hypgraph export --telemetry [FILE]`
  (default `<db>.telemetry.jsonl`) add a swarm's sidecar for replay. It is outside the hash chain:
  `verify_bundle` and `from_bundle` ignore it, and the UI labels it "not hash-chained". It is off unless asked for,
  because a sidecar names a run's models, seats and spend.
- **`play` opens on the replay.** The `play` mount option, or `#view=live&play=1`, opens the Live view and plays the
  run from its first event. With reduced motion requested, it shows the finished run with Play one click away.
- **A refused write is not an error.** In the Live view, a tool call the record refused counts as "refused by the
  record", with its reason: amber on the seat, in the stream and in the trace. Errors count real failures only.
- **The site's Atlas page is replaced.** The UI is served from `/app/`, `/explore/` opens any bundle full screen, and
  `/atlas/` forwards there (keeping `?bundle=`, the hand-over from `/verify/` and the fragment). The home page embeds
  the app directly. `/verify/` says when a bundle carries telemetry and opens bundles in HypGraph.
- **A narrow layout.** Below 760 px of its own width (a phone, or a narrow frame), the app's sidebar becomes a strip of
  tabs and the top bar wraps. It uses a container query, so an embed sizes it, not the window.
- The smoke check also renders the site: each example opens replaying with its chain verified, plus the home page,
  the explorer, the `/atlas/` forward and the gallery (106 pages).

## 0.5.3 — 2026-10-26: results that name no file can go stale

- **A result that names no file it read can go stale.** Under a workflow (`@2` profiles), a result whose run has no
  `uses` link was fresh forever, however the files changed. It now goes STALE once an input file of its
  investigation is replaced or withdrawn after the result was written ("it names no file it read, and A1 changed
  after it was written"), and claims resting only on it with it. A file registered on another question only
  (`part_of`) doesn't count against it; run outputs and page excerpts never do; a result written after the change
  is fresh; a result that names its files keeps the usual rule (only those files count). Ordered by the event log,
  not timestamps. Records without a workflow are unchanged. Measured on 851 results in HypSwarm's stored study
  records: none changes standing.

## 0.5.2 — 2026-10-26: freshness for sources, stale evidence in the report

For P3 (the change suite and the instruments in HypSwarm), the record had to know when a *page* moved, not only a
file:
- **A source is fresh while its page still says it.** A host that re-fetches a source's page registers an
  `excerpt` artifact (`derived_from` the source; `meta.contains_passage`, `meta.fetched`). The source is STALE when
  every excerpt of it was superseded, or the live one says the page no longer contains its passage — an edit
  elsewhere on the page keeps it fresh. A source never re-fetched is not stale: nothing says it moved.
- **A claim is stale when every result and every cited source behind it is.** The knowledge gates
  (`source_quoted`, `sourced`) take only fresh sources, so a changed page reopens the question at *sourced*.
- **The report marks it.** Claims and results on stale evidence read `checked · STALE` in the facts tables, a new
  open item lists them, the workflow section lists stale sources too, and the report check treats calling a stale
  claim settled as `REPORT_OVERSTATES_STANDING`.
- **Gates count only what still speaks for the question.** `result_exists`, `backtested` and `solved` take only
  fresh results (their message says which went stale and why); `result_reviewed` doesn't count a check of a stale
  result; a decision is stale when everything it was based on is, and `positioned` / `decided` take only fresh ones
  — a position taken on a backtest the vendor later corrected has to be decided again.
- **The report check reads the answers block.** A fenced ```answers block (the part of a report a harness scores and a
  reader copies) was skipped like any code block, so a report could carry an answer only stale evidence gave and pass.
  Now each answer has to be one a current claim on its question makes — live, not stale — at the precision written and
  with its sign: `REPORT_ANSWER_STALE` when only old claims or stale results give it (or a current claim binds the
  same field to another value), `REPORT_ANSWER_UNBACKED` when no claim does or the question has no claim,
  `REPORT_ANSWERS_UNREADABLE` for invalid JSON. Results count through the claims that bind them, and a count k of n
  backs its rate; a number a claim names only as a superseded figure doesn't back an answer; URLs, paths and hashes
  are provenance. Keys are question codes in any case, or a flat object checked against the investigation. Found by
  HypSwarm's change suite.
- **The report check skips the record's own facts.** A line inside a "Facts from the research graph" block is not
  linted when it is exactly a line the record generates now (a hypothesis that says "significantly" is a conjecture
  the record lists, not the author's assertion). Anything else written under that heading is checked as usual.
  Found when a report was refused for the hypothesis line the record itself had written.

## 0.5.1 — 2026-10-26

What wiring HypSwarm's scheduler to the stages (P2) found the workflows had no honest ending or no right answer for:
- **Declining a thesis is a decision.** A decision `kind=no_position` based on the claim meets `positioned` and
  `position_sized` ("1 declined"); only `kind=position` needs size, stop, review date and `paper=true`.
- **An honest "it can't be answered" settles a question whatever its stage.** A checked claim of kind
  `inconclusive` or `exclusion` that answers the question (no source says it; too few trades; infeasible) completes
  it; `stage()` reports `settled_by` and `settled_how`. The claim still needs its evidence — the search's own
  result ("read 3 of 3 pages; 0 mention it") is what it derives from.
- **A verified failure settles a software requirement.** A checked claim resting on an instrument-recorded
  *negative* result ("1 of 2 checks pass", re-run by the instrument) completes the question; `tests_pass_current`
  stays unmet and `requirements_verified_current` says so.
- **The same bytes, registered again, are one node that learns.** A second `create` of an artifact with the same
  sha adds the links given now (`part_of` a question, `supersedes`) and, when the node was untyped, its `kind` /
  `meta` / `path` as a new version. Before, the task's own file silently swallowed the diff registered on it.
- **A decision that settles a work order is the harness's, not the question's** (`decided` ignores it).
- **optimization gains a `checked` stage** (the verifier checks the claim after the result): a question settles on a
  checked claim, so the workflow had to ask for one.
- A review order's target predates the order; `reviewed` / `result_reviewed` now ask that the *review* be new.
- `report()` names experiments by aim and decisions by choice.

## 0.5.0 — 2026-10-26: profiles carry their discipline's workflow

Each discipline's method, as the record enforces it — one page each in `docs/workflows/`, taken from the method
itself (hypothetico-deductive with preregistration; continuous integration and code review; preregistered
backtesting and risk management; source criticism and fact-checking; operations-research practice). The `@1`
profiles are frozen as they were; `scientific@2` … `optimization@2` add the workflow. No profile → unchanged.

- **The stage is derived, never set.** `Graph.stage(question)` / `stages(inv)`, `GET /stage/{id}` / `/stages`, MCP
  `stage`: a question is in the first stage whose gate the record does not meet, every gate MET / NOT MET with what
  would meet it. `Profile.workflow` (`Workflow`, `Stage`) holds the stages, gates, invalidation, typed shapes.
- **Gates double as order predicates**: `hypothesis_stated`, `preregistered` (the experiment, with its expected
  outcome, precedes any run that executes it), `decided`, `diff_registered`, `tests_pass_current`,
  `instance_registered`, `source_quoted`, `search_recorded`, `backtested` (out of sample, after costs, trials
  declared), `positioned`, `still_valid`, `solved`, `result_reviewed`. The `@2` profiles' `done_when` use them.
- **A workflow widens what counts as resting on.** `uses` (scientific, software, trading, optimization) and `cites`
  (knowledge) join `schema.RISKY` for that profile only (`derive.EXTRA_RISKY`): a corrected data file, a superseded
  diff or instance, a withdrawn source puts what rested on it AT RISK. Records under `@1` keep exactly the standing
  they had.
- **Freshness** (`derive.stale`, in every standing): a result whose run used an artifact that is now superseded or
  withdrawn, or whose new `valid_until` has passed, is STALE; a claim is stale when every result behind it is. A
  check on stale evidence doesn't meet `reviewed`; `requirements_verified_current` and `incumbent_verified` need
  fresh instrument runs.
- **Typed shapes.** `artifact.kind` + `artifact.meta` with required fields per workflow (`diff`: base_sha,
  head_sha, files; `instance`; `prices`; `solution`: objective, feasible …) → `ARTIFACT_MISSING_FIELDS`;
  `source.kind` primary / secondary / tertiary and `reliability`; `decision.kind` with `size`, `stop`,
  `review_date`, `paper`, `sensitivity`. `supersedes` now joins artifacts; `corrects` joins sources.
- **The disciplines' refusals**: `TESTS_ON_STALE_HEAD`, `REVIEW_BY_AUTHOR` (the diff's author can't check the
  claim), `EDGE_WITHOUT_TRIALS`, `POSITION_WITHOUT_STOP`, `LIVE_ORDER` (no such path exists), `PASSAGE_MISSING`,
  `SOLVED_WITHOUT_INSTANCE`, `OPTIMAL_ON_STALE_INSTANCE`.
- **Report**: under an `@2` profile, `report()` adds the workflow's section — each question's stage and next gate,
  and the evidence that has gone stale.
- Schema additions are fields and relation endpoints only; no migration. Deferred to later phases, and said so in
  the specs: per-workflow evidence rank (documented, not derived), the knowledge re-fetch check and
  `NUMBER_NOT_IN_PASSAGE`, CI as the software instrument, mechanical feasibility recomputation.

## 0.4.3 — 2026-10-26

Five vocabulary-friction fixes from the HypSwarm discovery study, where 110 of 118 refusals were binding, naming
and shape errors rather than overclaims — and one correct answer was refused fifteen times.
- **A named p-value backs "significantly".** A bound field named `p`, `p_value` or `p_<test>` (an exact McNemar
  `p_exact`), or such a field on a supporting result, satisfies the significance check; below 0.05 the word is
  accepted, above it `SIGNIFICANCE_NOT_SHOWN` quotes it. The record's own two-proportion test stays the fallback.
- **A bound measurement's result supports the claim.** A claim written with `measurements` that name a result gets
  a `supports` edge from that result, so its standing counts the line of support the writer already bound.
- **A wrong relation names the right one.** `executes can't join run → question … — a run joins a question with
  part_of, motivated_by; the other way round, a question joins a run with …`.
- **Enum synonyms** (`schema.SYNONYMS`): `outcome=success` → `positive`, `kind=fact` → `finding`,
  `state=done` → `succeeded`, and more; the stored value is canonical.
- **Small integers bind to a value the sentence names.** "produced 0 trades" binds to `oos_trades`,
  "capacity is 7" to `capacity_total`; an unnamed small integer still binds only to a count.

## 0.4.2 — 2026-10-25

- **A question is not an assertion.** `language.interrogative` / `asserted` return nothing for a sentence that ends
  with a question mark, and the report check skips the language and number rules on a sentence that asks or that
  quotes one of the investigation's own questions (citations are still checked). Found in the first real HypSwarm
  mixed-swarm run: the lead headed a section "Q2 — Is A significantly more accurate than B…?" and lost its report
  to `REPORT_SIGNIFICANCE_UNBACKED` three times.

## 0.4.1 — 2026-10-25

Three rules the hypswarm examples exposed, each with a test:
- A claim's numbers that appear in a cited source's passage, citation or title are accounted for (a knowledge claim
  "signed on 24 October 1648" citing the passage that says so is no longer `UNBOUND_NUMBER`).
- A rework's predicates count evidence written since the **first** order of its chain (`coord.chain_root`): a
  `tests_pass` met by the instrument's re-run under the original order stays met under the rework.
- `PASS_WITHOUT_INSTRUMENT_RUN` accepts a claim resting on the author's result when a live lab run `replicates`
  the run that produced it and the re-run's result is positive (`profiles._instrument_backed`).

## 0.4.0 — 2026-10-25: the coordination layer

Held until the harmony study had exercised every path (pilots 1–4, a 142-run confirmatory, two follow-up rounds). Governance profiles, token-bound authors, work orders with predicates, order text that carries the target, instrument reproduction, replayable refusals.

### Identity and arithmetic (2026-10-25)
- `hypgraph serve --token SECRET[=authors]` binds writes to bearer tokens (401 without one, 403 for an author the token isn't bound to; a reserved name needs a token that names it). `--token-file`, `$HYPGRAPH_TOKEN`. Without tokens: unchanged. `Policy.extra_reserved` lets a host reserve its own names (hypswarm reserves `harness`). ADR-001.
- **Governance profiles** (`hypgraph.profiles`, ADR-002): `scientific@1` (the default), `software@1`, `trading@1`, `knowledge@1`, `optimization@1` — each a versioned set of default predicates per target, domain predicates (`tests_pass`, `backtested_oos`, `sourced`, `feasible_bounded`), write-time refusals (`PASS_WITHOUT_INSTRUMENT_RUN`, `EDGE_WITHOUT_OOS_COSTS`, `BACKTEST_WITHOUT_COSTS`, `CLAIM_WITHOUT_SOURCE`, `OPTIMAL_WITHOUT_BOUND`, `OBJECTIVE_WITHOUT_FEASIBILITY`) and completion criteria. Pinned on the investigation (`fields.profile`); `Graph.completion(inv)`, `GET /api/graph/completion|profiles`, MCP `completion`; the briefing names the profile and its criteria. A cited source counts as a claim's evidence.
- The order text carries the target's own content (a claim's statement, scope, measurements and the values of the results it rests on; a result's values; a question's text; an experiment's protocol), and names a replication of the author's run when one exists — the harmony confirmatory showed 11–16 `show` calls a run reading back what the reply had said.
- `cancel_work` releases the target's lease when the order was still open, so the target can be issued to someone else at once (a resumed hypswarm run with a replaced seat found it blocked).
- `stats.two_proportions` / `detectable` no longer divide by zero on an empty arm (undefined, p = 1, the whole range). `tests/test_stats_values.py` pins Wilson, rule-of-three, Newcombe and the z-test to reference values.


- **Honest negations pass.** A word counts only when its sentence asserts it (`language.asserted`): "A is not
  significantly better", "no evidence that it ever fails", "we cannot conclude that…" are accepted; the unnegated
  overclaim is refused as before. New code `SIGNIFICANCE_CONTRADICTED`: "not significant" when the bound counts
  are (p < 0.05). Found by the harmony pilot, where the checker refused the honest sentence its own message asked
  for.
- **The record binds the numbers it already holds.** A claim's loose numbers are bound to the author's own results
  in the investigation (linked results first) before any refusal; a `derived_from` link is added to the result
  they came from, and the reply says what was bound. Small integers (≤ 12) bind only to counts. In the pilot,
  61 of 106 refused numbers were already in a result.
- **The done signal.** After every write by an assignee, the reply carries its open orders with each predicate
  MET / NOT MET, and "return_work now" when all are (`coord.done_lines`; `orders` on create / revise / review
  results; shown by the MCP tools). In the pilot 8 of 9 sub-agents worked to their turn cap past done.
- **Orders meetable by construction.** `done_when` accepts `predicate` / `name` / a bare string as spellings of
  `p`, and a bad predicate's refusal shows the valid form. Each predicate in an order carries how to meet it with
  the assignee's tools. `result_exists` and `run_registered` count what the assignee wrote while holding the
  order, so no link vocabulary stands between an honest result and a met predicate. A third rework of an order
  whose predicate hasn't moved is refused, with the choices spelled out.
- **The question board.** The briefing's unit is the question: settled (a checked claim answers it), contested,
  answered (unchecked), in progress, open; the frontier is driven by it, and one review settles a question
  (`question_board`). `settle` / MCP `settle_work` accepts every returned order whose predicates are all met.
  Standing in the briefing is now exceptions only (contested, at risk, fallen).
- **Absolutes over an enumerated set pass.** "A trails B in every subset: math −2.6, code −2.2, reading −0.4",
  "all three subsets", "over all 818 items" quantify over what the sentence lists; they are not
  generalisations and are no longer refused. "below zero" is a number, not "never".
- **Replay.** Refusals are logged with the whole claim body and its support, and `hypgraph replay-refusals`
  (`Graph.replay_refusals`) runs every logged refusal through the checker as it is now: same, changed, passes.
  A rule change is judged on the corpus of what agents wrote before it ships.
- **A result written twice is written once.** The same author re-registering the same numbers (the multiset of
  a result's values, rounded, keys ignored) is refused with `RESULT_RESTATES`; a declared rerun (a run that
  `replicates`) is kept and marked; another author's restatement is kept and its standing says `RESTATES RSn`.
  Restated results are collapsed in work-order text.

- **Coordinating a team through the record** (`coord.py`). All of it is deterministic and makes no model calls.
  - `briefing(inv)`: the orchestrator's context compiled from the record (mission, rules, roster, standing,
    frontier, orders in flight and returned with their predicates checked, budget, what changed since the last
    one), with a hash.
  - Work orders are `task` nodes: `issue_work` (the target is leased to the assignee; a duplicate is refused),
    `order_text`, `return_work`, `check_work` (each predicate MET / NOT MET with the nodes that satisfy it),
    `accept_work` (a decision based on the evidence, only when every predicate is met), `rework`, `cancel_work`
    and `cancel_moot`.
  - An order's status is derived, never set: open, returned, overdue, accepted, reworked, cancelled or moot.
    Only evidence written after the order was issued counts toward it.
- **Schema.**
  - `task` gains optional `objective`, `assignee`, `role`, `prediction`, `method`, `done_when`, `budget` and
    `note`; `kanban_id` is no longer required.
  - New relations `rests_on` (an order's pinned premises) and `settles` (a decision accepting an order).
  - `works_on` and `rests_on` join the at-risk relations, so the blast radius of a withdrawal now lists the work
    orders it makes moot.
- **Surfaces.** MCP tools `briefing`, `issue_work`, `my_work`, `check_work`, `return_work`, `accept_work`,
  `rework`, `cancel_work` and `cancel_moot`; CLI `hypgraph brief` and `hypgraph orders`.

## 0.3.0 — 2026-10-24

- **The refusal log.** Every refused claim is logged: author, statement, codes, messages. A later accepted claim by
  the same author that says the same thing (same node, or ≥ 30% shared content words within 24 hours) marks the
  refusal fixed. Append-only, with its own hash chain (`verify_refusals()`); the record's chain is untouched.
  - API: `refusals()`, `refusal_report()`.
  - CLI: `hypgraph refusals [--author …]`. MCP: `refusal_log`. HTTP: `GET /api/graph/refusals`.
  - Atlas: an "Overclaims caught" card in the Work view.
- **`hypgraph check report.md`** lints a write-up against the record (`Graph.check_text`; MCP `check_report`; HTTP
  `POST /api/graph/check`). Exits 1 on errors (`--strict`: warnings too).
  - Errors: citations of withdrawn nodes, settled language about unchecked, contested or at-risk work, unknown
    codes, and unbacked never / no effect / significantly.
  - Warnings: numbers no result contains or implies, omitted disputes, superseded citations, uncited causal
    language.
  - Calibrated on 24 real PegasusDMZ write-ups against its live record. That fixed negations ("cannot be proven"),
    quoted passages under correction, instructions ("never use the eval set"), p-values given in the sentence, and
    "results in" as a noun phrase.
- An absolute whose statement gives its n ("no leaks in 50 prompts", "nothing in 50 of 50") is scoped to what was
  seen and accepted; its standing still carries the bound. Without n it is refused, as before.
- Spec draft 3 (§8 refusal log, §9 checking a write-up).

## 0.2.0 — 2026-10-24

**Refusal, remastered.** The claim checks now do the arithmetic the writer skipped, and every refusal says what the
count actually supports and offers the honest sentence.

- **The arithmetic of never.** "Never" / "always" / "eliminates" / "100%" need a count of what they're about with
  k = 0 or n (`ABSOLUTE_WITHOUT_COUNT`, `ABSOLUTE_UNRELATED_COUNT`). That count needs a 95% bound under 5%
  (`ABSOLUTE_UNDERPOWERED`: "0 of 3 only rules out more than 63%"), and the statement has to show its denominator
  (`ABSOLUTE_HIDES_DENOMINATOR`). The bounds are exact at k = 0 (1 − 0.05^(1/n), the rule of three) and Wilson
  otherwise.
- **Exposure.** A claim can say how many uses, users or units it applies to (`exposure`, `exposure_unit`). Refusals
  and the claim's standing then state how many failures the bound leaves unruled out: "up to 58,155 of 1,000,000".
- **New rules:** `COMPARATIVE_WITHOUT_COMPARISON`, `SIGNIFICANCE_WITHOUT_TEST`, `SIGNIFICANCE_NOT_SHOWN` (the
  record runs a two-proportion test on bound counts itself), `CAUSAL_WITHOUT_INTERVENTION`, and
  `EXCLUSION_WITHOUT_POWER` for "no effect" however it is filed, with the smallest effect the sample could have
  detected.
- **True numbers pass.** Differences, ratios, percentages and relative changes computed from bound measurements are
  accepted ("2.8 points", "81.2% vs 78.4%", "+3.6%"). Statistical quantities must be written to one decimal place, so
  "5 points" can't borrow an interval's end.
- **Refusals agents can act on:** a stable code on every line, and `GraphError.problems` with `code`, `message`,
  `fix` and `words`.
- **Blast radius.** `withdraw()`, and a review that makes a node fall, return `blast_radius`: what rests on it, by
  type, with claims and decisions named (and spend, if metered). The CLI and MCP print it.
- **`hypgraph bound K N --exposure X`** and the MCP tool `bound`: what a count supports, before anyone writes "never".
- A claim's standing carries `bounds`, and `test` for "significantly" claims. Spec draft 2 (§7 rewritten).
- Credits: made by Nicolas Houghtaling at VoodooMods LLC (README, NOTICE, CITATION.cff, package metadata, site).

## 0.1.0 — 2026-10-24

First release on PyPI.

- **Writes cost what they touch.** A write no longer copies the whole in-memory snapshot. Tables are shallow
  copies, and a node's list is copied only when the write appends to it. Derived standing is kept for every node the
  write can't affect (`derive.affected_by`), so the first full read after a write no longer re-derives the graph.
  At 10,000 nodes: building the graph took 77 s instead of 133 s, a full read after a write 0.02 s instead of
  0.17 s, and a write at 5,000 nodes 5.8 ms instead of 12 ms. A randomized suite checks the carried standing
  against a full rebuild after every kind of write.
- New indexes for display codes and the rate limit (`nodes(inv, type)`, `nodes(inv, code)`, `events(actor, kind,
  at)`). Created on open; existing records just gain them.
- Positioning: the evidence layer for AI research agents. README and site lead with the MCP server and the Agent
  Skill; a new engineering guide (`/engineers/`) replaces the human guide; the eval-report example replaces the
  classroom one.

### Extracted from PegasusDMZ

Extracted from the PegasusDMZ research graph and verified against it: on a copy of Pegasus's live
graph (1,357 events, 790 nodes in 5 investigations), the library reproduces the same chain head, every node's
standing, the work queues and the next-experiment rankings.

- **Engine** (stdlib only): typed nodes and edges, append-only SQLite with a SHA-256 event chain and `verify()`,
  standing derived on read, claim checks on write, review pinned to versions, independence and evidence profile,
  leases, next experiments, work map, digest, report.
- **Policy**: reviewers, instrument, operator, importer and system are the host's to set (they were hardcoded in
  Pegasus). Optional `spend` hook for cost. Injectable `clock`; only the importer may set a write's time.
- **Bundles** (`hypgraph/1-bundle`): every event and body as the exact hashed string, so they can be verified in any
  language. Scoped exports redact events outside the investigation and say so. A complete bundle replays row for row.
- **CLI**: `init`, `add`, `link`, `review`, `revise`, `withdraw`, `ls`, `show --why/--impact/--history`, `next`, `work`,
  `report`, `export`, `import`, `verify`, `demo`, `schema`, `serve`, `mcp`, `skill`.
- **MCP server** (FastMCP, `hypgraph[mcp]`): 17 tools, 4 resources, a `method` prompt. Writes as one fixed author.
- **Agent skill**: `SKILL.md` ships in the package; `hypgraph skill --install`.
- **Atlas**: the framework-free explorer, with an HTTP source and a bundle source (it verifies the chain in the
  browser). Cytoscape is vendored.
- **Demo**: Broad Street, 1854 — a teaching reconstruction with three refusals built into the story.
- Fixed while extracting it: a report listed stale-reviewed claims under the wrong key; claim measurements now accept
  result codes (RS3) and store ids.
