# Scoring model — design

Status: proposed, 2026-08-24. Supersedes the term list critiqued in the Codex review of the same
date. Companion documents: `CONTEXT.md` (glossary), `docs/adr/0001` (pod identity), `docs/adr/0002`
(terrain profile vs conditions).

---

## 1. What the score is

**The score is an ordinal device for ranking today's pods against each other. It is not a quantity.**

A 73 in January and a 73 in April do not describe the same skiing. Nothing calibrates them against
each other, and nothing will until there are seasons of observed outcomes to fit against. Saying
otherwise would be invented precision.

Two consequences, and they are binding:

- **The number is never shown to the skier.** The ranking is shown, and the reasons are shown. A
  0–100 figure on screen would claim a precision the model does not have.
- **Comparison is only ever within one request.** Scores are never stored, trended, or compared
  across days.

The prediction target, stated plainly so later work can be checked against it: *given the skier's
intent, which pod will produce the best skiing during the chosen window, relative to the other pods
available today.*

## 2. Factors, not terms

The first draft had nine additive terms over four correlated inputs. Wind drove three of them,
snowfall four, temperature three. Adding correlated quantities does not make them independent — the
score saturates and the arbitrary weights end up deciding the answer.

Instead: each **input is consumed by exactly one factor**.

| Factor | Answers | Inputs — each appears here and nowhere else |
|---|---|---|
| `surface` | What is under my skis? | new snow, snow density, per-run grooming state, melt/refreeze history, base depth, wind redistribution |
| `visibility` | Can I see? | cloud cover, tree cover |
| `comfort` | Is it pleasant to stand in? | station wind and gusts, air temperature, landform TPI |
| `fit` | Is this the terrain I asked for? | eligible-run difficulty mix, vertical, sustained pitch |

Corrections against the first draft, both caught in review: tree cover was listed under two factors
and wind under two. Tree cover now sits only in `visibility`; `comfort` uses TPI for terrain shape.
Wind sits only in `comfort`, and the redistribution indicator inside `surface` consumes *snow*
transport state, computed upstream, not the wind field again.

`access` is not a factor. It is a gate — §5.

**Intent does not enter a factor.** In the first draft intent shaped `fit` *and* set the weights,
which double-applied it on top of difficulty already gating runs. Intent sets weights only. `fit`
measures terrain against the skier's declared ability and nothing else.

### Factor range

Every factor returns a value in `[0.05, 1]`, with written meanings for both endpoints.

The floor is not cosmetic. A value of exactly zero annihilates the combination below and ties every
affected pod at zero regardless of everything else. **Anything that genuinely means "do not go here"
is a gate, not a factor value.** A factor is a quality signal among places you could ski; it never
expresses impossibility.

### Combination

Score is the **weighted geometric mean** of the factor values.

Geometric rather than arithmetic because skiing does not average: perfect snow plus a whiteout is a
bad day, not a half-marks day, and the geometric mean says so without a special case.

Its cost, and this is a real limitation rather than a detail: the geometric mean treats factors as
ratio-scale, so it assumes `visibility` 0.2 → 0.4 means a genuine doubling. Nothing establishes
that, and a monotonic remapping that preserves each factor's ordinal meaning can still reverse the
combined ranking. The mitigation is §3 — the answer only commits where the winner is robust — plus
the ablation and metamorphic tests in §10. **If a factor's transform cannot be given a defensible
ratio meaning, it belongs in `fit` as a filter or in §5 as a gate, not in the mean.**

## 3. Uncertainty, missing inputs, ties, and abstention

The first draft answered missing data with a shared factor set: drop any factor unavailable for any
pod, score everyone on the remainder. Both reviewers rejected it independently, and they were right.
It replaces one bias with a worse one — a single pod with a dead sensor deletes a discriminating
factor for *every* pod, so the badly-observed pod degrades the whole field and can win the degraded
comparison. Combined with the abstention rule it was even sharper: one pod with three dead sensors
would force the whole mountain to abstain.

**Every pod carries a score interval, and the answer commits only where one pod dominates.**

1. For each pod, each **available** factor contributes its point value.
2. Each **unavailable** factor contributes its full allowed range, `[0.05, 1]`. Nothing is dropped
   and no weight is renormalised.
3. Propagating those through the weighted geometric mean gives every pod a `[low, high]` interval.
   A pod with complete data has a narrow interval; a pod with a dead sensor has a wide one.
4. **Commit** to a pod when its `low` exceeds every other pod's `high`. It won under every
   assumption its missing data could have taken.
5. **Tie** when intervals overlap and the pods differ on no contrast axis (§8).
6. **Contrast** when intervals overlap and they do differ on a contrast axis.
7. **Abstain** when no pod's interval separates from the field and the spread is dominated by
   missing inputs rather than by real differences.

This is one mechanism doing four jobs, and each property falls out rather than being asserted:

- Missing data cannot flatter a pod. It widens the interval, and a wide interval cannot dominate.
- One pod's dead sensor does not touch any other pod's interval.
- Ties and the contrast card get the interval §8 needed and the first draft never defined.
- Abstention becomes a computed outcome, not a hand-set trigger.

**Mandatory inputs still gate.** A pod missing access, difficulty, or eligible runs is excluded with
`kind: 'insufficient-data'` and the named input — it is not given a wide interval, because those are
not quality signals.

**Factor identity is a signature, not a name.** Two pods' `surface` values are only comparable when
they were computed by the same factor version from the same required-input set. A `surface` from
grooming alone is a different quantity from one that also saw snowfall and density. Each factor
therefore declares a version and a required-input signature; a mismatch makes the factor unavailable
for that pod, which widens its interval rather than silently comparing unlike things.

**Freshness gates before any of this.** Grooming and lift state have hard staleness limits. Past
them they are unavailable, not stale-but-usable.

## 4. Eligible runs are the unit of computation

The previous draft filtered runs and then scored pod-level aggregates. Those aggregates describe the
whole pod — for Big Burn, mostly upper-mountain expert terrain — so an intermediate would have been
shown a score describing a mountain they were not going to ski.

**Every terrain input is computed over the pod's eligible runs, not the pod.** That requires
per-run terrain, so `domain/derive/terrain.py` gains per-run output alongside its per-pod rollup:
elevation range, aspect, tree cover, TPI, length, vertical, and mean pitch. The per-pod figures
become a derived rollup rather than the primary record.

### Run roles

A run that clears the difficulty gate is not necessarily skiing. But geometry alone cannot decide
every role, and the first draft claimed it could. An OSM polyline plus DEM elevations supports a
**binary** classification and no more:

| Role | Decided from | Rule |
|---|---|---|
| `descent` | own geometry | sustained pitch ≥ 8° over ≥ 100 m contiguous, and total vertical ≥ 150 m |
| `not-descent` | own geometry | everything else |

`connector` and `egress` are **not** derivable here: knowing a run links two descents, or terminates
at a base area, requires the route graph deferred below. They are recorded as `not-descent` and the
distinction is left for v2 rather than guessed.

**Sustained pitch, not mean pitch.** A long green, a steep pitch with a flat runout, and a traverse
cutting across a steep face can share a mean. The rule keys on the steepest contiguous stretch.

Thresholds above are starting values with a stated basis — 8° is roughly the point below which a
snowboarder stops moving, 150 m is about a third of the smallest lift-served vertical on the
mountain. They are named constants, calibrated against a season, not magic numbers.

**A pod qualifies only if it has at least two eligible `descent` runs.** Two, not one, because the
answer contract in §8 promises 2–4 named runs as evidence; a one-descent pod could qualify and then
fail to satisfy its own output. The flat-cat-track pod fails qualification with a stated reason.

**Unmatched runs are a coverage gap, not an absence.** A feed run with no OSM geometry cannot be
classified, so it counts toward neither qualification nor exclusion, and the pod's per-run coverage
ratio is reported. Where coverage falls below a declared threshold the terrain factors are
unavailable for that pod — which widens its interval under §3 rather than silently scoring it on a
biased subset. This matters most for the gladed runs §12 already flags as disproportionately
unmatched.

### Explicitly deferred

Full route reachability — which lift serves which run, where runs connect, whether the return to a
lift crosses terrain above the skier's cap — is **not in v1**. v1 requires an eligible descent within
a pod that has a running lift by `ACCESS_EDGES`. That is weaker than true reachability and the gap is
recorded here so it is not mistaken for coverage. Two pods already have no sourced lift access at all
(`KNOWN_ACCESS_GAPS`).

## 5. Gates

Gates are operational truth. They run before scoring and no score overrides them.

1. **Closure.** A closed pod, or one with no open eligible descent, is out.
2. **Access.** No running lift by `ACCESS_EDGES` is out. `KNOWN_ACCESS_GAPS` pods resolve to
   `unknown`, never `no-access` — reporting a real pod as unreachable is the confident-wrong failure
   this project already shipped once.
3. **Difficulty.** Filters runs, never pods. A pod survives on its qualifying runs.
4. **Intent.** Hike-required terrain is out unless the morning brief said otherwise.

## 6. Safety

Non-negotiable, and it constrains the model rather than sitting alongside it.

- The app **never** presents wind loading as desirable. Loaded snow is avalanche terrain.
- The app **never** contradicts or reinterprets a closure or a gate. Aspen's operational state is
  authoritative and final.
- No output implies terrain is safe. The model ranks skiing quality among terrain that is *already
  open*, and says so.

`windLoading` as previously drafted is dropped. It multiplied TPI by wind direction by aspect, and
each factor was weak: aspect is near-constant here at 92.9% NW/N/NE, and TPI measures snow
deposition, not shelter — Cirque is a concave bowl **and** above treeline, so its −13.7 m reads as
"sheltered" while being exactly the place you would be sandblasted. What survives is a capped
redistribution *indicator* inside `surface`, active only when there is recent snow and sustained
transport-strength wind, and never framed as an invitation.

## 7. Melt risk

`meltRisk` replaces the retired aspect-slush penalty, which keyed on S/SE/SW aspects that make up
0.6% of this mountain and so could essentially never fire correctly.

It cannot be calibrated before winter. The station is dead from roughly May to October — every cell
reads `-` — and there is no archive, so no amount of work now establishes that a coefficient predicts
anything.

Therefore:

- It ships **computed, logged, and weighted zero**. Shadow mode.
- Every raw station response is archived from the first day of the season, so a later calibration has
  data to fit.
- It is promoted to a live weight only after a season of observed outcomes.
- It uses **history, not an instantaneous reading**: overnight refreeze, hours above freezing,
  accumulated radiation, time since the last 0 °C crossing.
- Freezing level is applied against the **eligible runs' elevation distribution**, not the pod's
  min/max. Pods spanning 2,000–3,000 ft make a single band meaningless.

A season-gate precedes all of it: off-season the mountain is closed, so the recommendation is gated
before melt scoring is ever reached.

## 8. The answer

**One pod, committed to, with 2–4 named runs as evidence** — named because a pod is not something you
point your skis at, and because named runs make the recommendation checkable against the grooming
report.

**A contrast card, on a crisp rule.** The first draft's phrasing — "different elevation band or
shelter class, within a threshold, qualitatively different" — had no implementable meaning, and the
intervals it leaned on did not exist. They exist now (§3). The rule:

- The candidate passed the same gates and carries the same factor signatures (§3).
- Its interval **overlaps** the winner's.
- It differs from the winner on at least one **contrast axis**, computed over eligible runs, from a
  closed set: `elevation`, `landform`, `surface`. The axis is `landform`, not "shelter" — TPI
  describes where snow collects, and §6 is explicit that this is not the same as being sheltered.
- A difference counts only past a declared per-axis margin.
- Selection and tie-breaking are deterministic: highest `low` bound, then highest `high`, then pod
  id.

**Ties are reported as ties.** Overlapping intervals with no contrast-axis difference means the
model cannot separate them today. Committing to one and demoting the other would manufacture a
distinction the data does not support.

**Abstention is shown, not hidden.** When §3 abstains, the app says which sources it could not reach
and shows what it does know. It never falls through to a ranking on terrain constants — that would
answer identically every day of the year, which is the original defect in a new costume.

## 9. What the engine owes the two modes

The morning-brief and on-mountain surfaces are specified in the frontend spec, not here. The engine
owes them three things:

- **Intent is an input, and it is mutable.** Effort appetite, willingness to hike, whether the skier
  is guiding anyone, travel radius. Mutable because fatigue and party composition change during a
  day; an intent fixed at breakfast would leave the app answering a question the skier stopped
  asking.
- **A day plan**, not just a now-answer: the same ranking evaluated across the day's windows.
- **Divergence**, computed rather than eyeballed, on defined triggers: the recommended pod changed
  identity, its access state changed, its confidence dropped or the shared factor set shrank, or a
  gate that previously passed now fails. "Conditions moved materially" is not a trigger — it has no
  test.

## 10. Testing

**Parity, quarantined.** The 5,400 oracle vectors test the legacy term functions only, fed legacy pod
attributes. They prove the TypeScript reproduces the Python arithmetic, including its defects. They
are not evidence about the new model, and they exercise only five weather regimes over six-hour
sequences where nothing but cloud cover moves.

**Metamorphic tests** carry the new model, because there is no ground truth to assert against. These
are checkable without labels and they catch real bugs:

- raising wind must never raise a pod's score
- widening any interval must never turn a tie into a commit
- a pod strictly better on every input must never rank lower
- adding a closed run must not change the ranking
- **missing data cannot manufacture a winner.** Removing an input must never let a pod commit that
  would not have committed with the input present, across the input's whole allowed range. Stated
  as "removing an input must not improve any pod's rank" the property was simply false, and review
  caught it: if A leads on surface and B on visibility, removing surface *must* improve B. The
  dominance formulation in §3 is what is actually testable.
- overlapping snow windows (1/12/24h) must not compound — one storm counted once

**Full-pipeline golden fixtures** for: winter conditions, missing and stale sources, a lift going on
hold mid-session, mixed-difficulty pods, cat-track-only eligibility, sensor boundary values, and
near-tied scores.

**Ablations** on each factor, recorded as intentional model-version changes. Precedent: removing the
`avoid_crowds` stub moves the winner in 3.3% of vectors, top-three order in 14.3%, and top-three
membership in 10.9% — measured, not assumed, and reproduced independently.

## 11. Removed, and why

- **`avoid_crowds`** — was `avoid_crowds × 1.5 × (1 − percent_groomed)`. There is no crowd data. It
  is deleted rather than approximated, and it comes back when there is a real source. It is also
  removed from `SkierConstraints`; if the UI still offers the intent, the honest response is that
  crowd conditions are unavailable, not silent acceptance.
- **`_aspect_slush_penalty`** — see §7.
- **`windLoading`** as a bonus — see §6.

## 12. Open questions

- **Factor transforms and weights are unset.** Until both exist this is an architecture, not an
  executable model. They are calibrated against a season, not guessed in August. This is the single
  largest gap and it is deliberate.
- **Which SNOTEL station represents Snowmass.** The verified recipe covers Ivanhoe (`547:CO:SNTL`);
  the charter names Independence Pass (`542:CO:SNTL`) and flags `531` as a different drainage.
  Neither is confirmed representative, so base depth stays out of `surface` until one is.
- **No interpolation from station to run.** Wind, snowfall, and radiation are point measurements at
  six stations; base depth is a point measurement elsewhere entirely. Treating a station reading as
  true across a pod is an assumption the spec currently makes silently. It needs a stated
  interpolation rule and a representativeness check per pod.
- **Melt risk has no formula yet**, only a named input list. Shadow mode does not need one to ship,
  but "computed and logged" is not a testable rule until it does.
- **No outcome labels exist.** Shadow-mode archiving gives inputs to fit against; it gives nothing
  to fit *to*. Promoting any weight needs a record of how the skiing actually was, which means a
  deliberate logging habit from the first day of the season.
- **Route reachability is deferred** (§4) and is the largest single piece of missing capability.
- **Tree cover is biased low** for pods whose gladed runs are unmatched in OpenStreetMap — the
  unmatched list is disproportionately glades and walls. Per-pod coverage is reported and §4 makes
  low coverage widen the interval rather than pass silently, but the underlying bias is uncorrected.
- **The Cirque access edge is `estimated`**, and its own provenance says to confirm it against the
  trail map before it drives an answer. §5 calls gates operational truth, so this edge does not yet
  meet the standard the spec sets for it.
