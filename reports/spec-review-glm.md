# Spec review — `docs/superpowers/specs/2026-08-24-scoring-model-design.md`

Read-only critical review. Tags: **[P1]** critical (the spec as written will produce wrong rankings or is unimplementable), **[P2]** advisory (undefined, ambiguous, or contradicts repo data but fixable). Citations are `spec §N:line` and `file:line`.

---

## 1. What breaks in the weighted geometric mean (§2)

**[P1] A single zero factor zeroes the whole score and forces a universal tie, defeating §1.**
§2:50–55 celebrates that "one factor near zero pulls the whole score down." But a legitimately-zero factor (a whiteout → `visibility = 0`; a wind event → `comfort = 0`) makes the weighted geometric mean exactly 0 for *every* pod that shares that condition. §8:186–188 then requires ties to be reported as ties. So on any day where one live-condition factor is genuinely zero across the field — the exact days the model is supposed to help on — the output is "every pod is equivalent," which contradicts §1:11 ("the score is an ordinal device for ranking today's pods"). The geometric mean is being asked to do two incompatible things: be a hard veto (§2's rationale) and be a ranker (§1).

**[P1] Dropping a factor under §3 re-normalises the weights and can flip the ranking between pods whose own inputs never changed.**
§2:50 weights come from intent and are fixed for the request. §3:72 drops a factor from the *shared* set when *any* pod lacks it. The weighted geometric mean is `∏ f_i^w_i` normalised by `Σ w_i`; dropping factor `k` changes the denominator to `Σ_{i≠k} w_i`, rescaling every surviving factor's effective weight. Two pods A and B with identical surviving factor values can swap rank purely because a third pod C lost a sensor and `visibility` was dropped. The spec never acknowledges this re-normalisation effect; §3 frames dropping as "fair" when it is in fact rank-changing for pods that lost nothing.

**[P2] The weight lower bound is asserted but never stated.** §2:57–58 says weights are "bounded so that no factor can be zeroed out entirely." The bound itself is absent. Without a number the rule is unimplementable and untestable (see Q4).

---

## 2. Is the shared-factor-set rule (§3) sound?

**[P1] No — it introduces a contamination bias the spec does not acknowledge.** §3:71–72 drops a factor for *all* pods when *any* pod lacks it. Consider one pod with a dead wind station: `comfort` is unavailable for that pod, so `comfort` is dropped for every pod. Every other pod that had perfectly good wind data is now scored without the factor that would have distinguished a sheltered pod from an exposed one. The dead-sensor pod is scored on a smaller, terrain-heavier set; the pods that were honestly rankable lose their discriminating axis. The bias direction is systematic: a pod with a dead sensor drags the ranking quality of the entire field down, and can rank higher than it should because the factor that would have penalised it (e.g. exposure) is gone. This is a new bias of exactly the class the spec claims to remove in §3:62–67.

The sounder rule — drop the factor *only for the pod missing it*, score that pod on the remaining factors with a confidence penalty, or exclude it — is not considered. §3:73–74 only excludes pods missing *mandatory* inputs (access, difficulty, eligible runs); `visibility`/`comfort`/`surface` are not mandatory, so a pod missing them contaminates the rest rather than being excluded.

**[P1] One pod with dead snow + wind + cloud sensors forces whole-mountain abstention.** §3:75–77 abstains when the shared set contains no live-condition factor. Combined with §3:72 (drop for all if missing for any), a single pod missing `surface`, `visibility`, and `comfort` inputs drops all three live factors → the shared set is terrain-only → abstain. The entire recommendation collapses because of one pod's dead sensors. The spec's own abstain rule, interacting with its shared-set rule, makes the system's availability depend on the worst-served pod.

---

## 3. Per-run terrain (§4) — what is missing in `domain/derive/terrain.py` and `terrain-derived.json`

**[P1] No per-run output exists today.** `terrain.py` accumulates only per-pod rollups. `pod_rec["runs"]` (terrain.py:284–285) is a list of *names* used solely for the `coverage.runs_matched` count (terrain.py:360). `terrain-derived.json` has no per-run records at all — each pod entry has `aspect`, `elevation`, `tree_cover`, `exposure`, `coverage`, none keyed by run. To support §4:89–91 the script must emit, per run: elevation range, aspect, tree cover, TPI, length, vertical, mean pitch. None of these is computed or stored per run; the segment loop (terrain.py:290–323) aggregates into `pod_rec` directly. This is a real build, not a wiring change.

**[P1] Two of the four run roles cannot be honestly classified from the geometry available.** §4:96 claims "each run is classified from its own geometry." The geometry in hand is an OSM polyline + DEM elevation per vertex.
- `descent` (mean pitch above flat threshold, vertical above minimum) — derivable.
- `traverse` (low pitch, meaningful length) — derivable.
- `connector` ("short, links two descents") — **not derivable**: requires a run-graph (which run connects to which) that the script never builds. OSM `piste:type=downhill` ways carry no explicit join.
- `egress` ("terminates at a base area, low pitch") — **not derivable**: requires a base-area polygon/point set the script does not load.

So §4's role table is half-implementable from current data; the other half needs a topology/base-area source the spec does not name.

**[P1] Per-run terrain is absent for exactly the runs §12 admits are biased.** `terrain-derived.json:37–60` lists 22 unmatched OSM runs, including `Glade One/Two/Three`, `Hanging Valley Glades`, `Headwall`, `Powerline Glades`. §12:248–251 says the unmatched list is "disproportionately glades and walls." §4 makes eligible runs the unit of computation, but the gladed runs — the ones whose tree cover matters most for `visibility` and `comfort` — have *no* per-run terrain and no per-run tree cover. The spec's own unit of computation is undefined for the runs where the bias it acknowledges lives.

**[P2] `comfort`'s TPI input is per-pod today, but §4 demands per-run.** §2:40 lists TPI as a `comfort` input; §4:88 says "every terrain input is computed over the pod's eligible runs." `terrain-derived.json` carries TPI only as a pod-level `mean_tpi_m`. Either `comfort` must move to per-run TPI (requires the per-run build above) or §4's "every terrain input" claim overstates what the factor uses.

---

## 4. Undefined thresholds, unstated units, rules with no test

**[P1] Run-role thresholds (§4:100–105).** "flat threshold," "vertical above the minimum," "meaningful length," "short" are all unnumeric. §4:105 says they are "declared as named constants with a stated basis" — but the spec declares none. Unimplementable as written.

**[P1] Contrast-card interval and margin (§8:181–184).** "Its score interval overlaps the winner's, or sits within a declared margin." The score from §2 is a point estimate; no uncertainty model is defined anywhere. `assessment.ts:49–55` has `score: number` and `confidence: {level, gaps}` — no interval, no variance. "Declared margin" is not declared. The tie rule (§8:186–188) keys off "overlaps within uncertainty," but uncertainty is undefined. This block is unimplementable.

**[P1] Melt-risk computation (§7:162–165).** "overnight refreeze, hours above freezing, accumulated radiation, time since the last 0 °C crossing." No formula, no units, no thresholds. "Weighted zero" shadow mode is fine without a formula, but §7:159 says it is "computed, logged" — computed how? The rule has no test.

**[P2] Redistribution indicator (§6:143–145).** "active only when there is recent snow and sustained transport-strength wind." "recent," "sustained," "transport-strength" all undefined.

**[P2] Weight lower bound (§2:57–58).** Stated to exist, not stated. (Also flagged in Q1.)

**[P2] Intent→weight mapping (§2:50, §12:244).** Acknowledged open in §12, but §2 presents the combination as the mechanism with no placeholder, so the spec is non-functional without it.

**[P2] "Hike-required terrain" (§5:128).** Gate 4 excludes hike-required terrain unless the morning brief says otherwise. No data field in `conditions.ts` or `access.ts` marks a run or pod as hike-required; `AccessKind` is only `primary`/`connecting` (access.ts:30). The gate has no source.

**[P2] Divergence trigger "confidence dropped" (§9:201).** `Confidence.level` is `{high,medium,low}` (assessment.ts:43–47). "Dropped" is testable as an enum step, but the spec does not say whether high→medium counts, only medium→low, etc. §9:202–203 correctly calls out "conditions moved materially" as having no test — but it is listed alongside the testable triggers without being struck, so it reads as a trigger.

**[P2] Metamorphic test "strictly better on every input must never rank lower" (§10:217).** Not well-defined once §3's shared-factor-set rule can drop the very factor on which a pod is strictly better. The test as written can conflict with the §3 rule.

---

## 5. Claims the code or data contradicts

**[P1] `avoid_crowds` is claimed removed from `SkierConstraints`; the type still carries it.** §11:234 says "It is also removed from `SkierConstraints`." `assessment.ts:18` still has `readonly avoidCrowds: number;`. The spec's claim is false against the contract it must fit.

**[P1] Cirque TPI figure is inconsistent between spec, data, and catalog.** §6:142 says "−13.7 m." `terrain-derived.json:192` says `mean_tpi_m: -13.7` ✓. But `catalog.ts:133` (the in-repo note for Cirque) says "TPI -12.7 m." The catalog note the spec's own companion ADRs build on is stale by 1 m. The spec quotes the data figure but the codebase carries a different one.

**[P1] §8's "score interval" has no basis in the type contracts.** `PodAssessment` (`assessment.ts:49–55`) carries a single `score: number` plus a categorical `Confidence`. There is no interval, variance, or uncertainty field. §8:181–184's contrast-card rule depends on intervals that the data model does not represent. Either the type contract must change (out of scope for a "design" spec that claims to fit existing contracts) or §8 is unimplementable.

**[P2] §4:89 is ambiguous between "already exists" and "to be built."** "domain/derive/terrain.py gains per-run output alongside its per-pod rollup" — read literally ("gains") it implies the change is done; the file and fixture show it is not (see Q3). The spec does not distinguish prescriptive from descriptive here, which is the kind of ambiguity that becomes a silent gap.

**[P2] §3.3 vs §5.2 on `unknown` access.** §3:73–74 says a pod missing a mandatory input (access) is excluded. §5:124–126 says `KNOWN_ACCESS_GAPS` pods resolve to `unknown`, *never* `no-access*, and gate 2 only excludes "no running lift by ACCESS_EDGES." A pod with `unknown` access (lift feed unreachable) is neither excluded by §5.2 nor clearly "missing" access under §3.3 — `access.ts:44` makes `unknown` a first-class arm. The spec does not say whether `unknown` access satisfies the mandatory-access input or triggers `insufficient-data`. `catalog.ts:214–219` lists two such pods. This is a real ambiguity that decides whether Hanging Valley and Pipes/Parks are scored or excluded.

**[P2] `surface` mixes per-run terrain with mountain-wide base depth.** §2:38 lists `base depth` as a `surface` input; §4:88 says "every terrain input is computed over the pod's eligible runs." `conditions.ts:81–93` makes `baseDepthIn` a single mountain-wide SNOTEL field and `thinCoverRisk` a per-pod derived field ("needs a per-pod term"). Neither is per-run. The spec's §4 rule is stated as universal over terrain inputs but `surface` quietly violates it; the spec should either carve out conditions vs terrain or acknowledge base depth is applied at pod/mountain scale.

**[P2] §6:142 "aspect is near-constant here at 92.9% NW/N/NE."** The figure is not derivable from `terrain-derived.json` as published (which gives per-pod `share_by_aspect`, not a mountain-wide aggregate). Not contradicted, but unreproducible from the cited data — the spec should point at the computation.

---

## Summary

| Tag | Count |
|---|---|
| [P1] | 13 |
| [P2] | 10 |

Distinct [P1] findings: zero-factor tie collapse; weight re-normalisation on factor drop; contamination bias from shared-factor-set; whole-mountain abstention from one dead pod; no per-run terrain exists today; connector/egress roles unclassifiable from current geometry; gladed runs have no per-run terrain; run-role thresholds undefined; contrast-card interval/margin undefined; melt-risk formula undefined; `avoid_crowds` claimed removed but still in `SkierConstraints`; Cirque TPI inconsistent between catalog and data; §8 score interval has no type-contract basis.

Distinct [P2] findings: weight lower bound; redistribution indicator thresholds; intent→weight mapping; hike-required source; confidence-dropped trigger definition; metamorphic-test conflict with §3; §4:89 descriptive/prescriptive ambiguity; §3.3 vs §5.2 `unknown` access; `surface` base-depth scale; 92.9% aspect figure unreproducible.
