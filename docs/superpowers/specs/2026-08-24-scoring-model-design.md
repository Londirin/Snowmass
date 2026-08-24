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

The critiqued design had nine additive terms over four correlated inputs. Wind drove three of them,
snowfall four, temperature three. Adding correlated quantities does not make them independent — the
score saturates and the weights, which are arbitrary anyway, end up deciding the answer.

Instead: each **input is consumed by exactly one factor**, and factors combine.

| Factor | Answers | Inputs (each appears once, here only) |
|---|---|---|
| `surface` | What will be under my skis? | new snow + density, grooming state per run, melt/refreeze history, base depth |
| `visibility` | Will I be able to see? | cloud cover, tree cover over eligible runs |
| `comfort` | Will it be pleasant to stand in? | station wind and gusts, tree cover, TPI |
| `fit` | Is this the terrain I asked for? | eligible-run difficulty mix, vertical, pitch, intent |

`access` is not a factor. It is a gate — see §5.

Each factor returns a value in `[0, 1]` with a written meaning for the endpoints, plus the list of
inputs it actually used.

### Combination

Score is the **weighted geometric mean** of the factor values, with weights from the skier's intent.

Geometric rather than arithmetic because skiing does not average. A day with perfect snow and a
whiteout is not a good day and a half-marks answer would be wrong; it is a bad day, and the
geometric mean says so without needing a special case. One factor near zero pulls the whole score
down, which is the behaviour we want and which an additive model has to be bullied into.

Weights come from intent and are bounded so that no factor can be zeroed out entirely — the skier
may not care about visibility, but the model still may not pretend a whiteout is fine.

## 3. Missing inputs

This is the defect the Codex review found in the previous draft, and it is the same class of bug as
the hardcoded grooming constant this whole rebuild exists to remove.

**Omitting a term when its source is missing is arithmetically identical to setting it to zero.** In
an additive model a missing penalty *rewards* the pod whose data failed to load. Labelling it in
`confidence.gaps` describes a wrong ranking; it does not prevent one.

The rule:

1. Compute the **shared factor set** — factors whose inputs are available for *every* candidate pod.
2. Score all pods on exactly that set. A factor unavailable for any pod is dropped for all of them.
3. A pod missing a **mandatory** input (access, difficulty, eligible runs) is excluded with
   `kind: 'insufficient-data'` and the named missing input. It is never scored on what remains.
4. **Abstain** when the shared set contains no live-condition factor. Ranking pods on terrain
   constants alone reproduces the original defect in a new costume: it would rank the same way every
   day of the year. The app says what it could not reach and shows what it does know.

Every factor therefore carries its input list, and the response carries the shared set that was
actually used.

## 4. Eligible runs are the unit of computation

The previous draft filtered runs and then scored pod-level aggregates. Those aggregates describe the
whole pod — for Big Burn, mostly upper-mountain expert terrain — so an intermediate would have been
shown a score describing a mountain they were not going to ski.

**Every terrain input is computed over the pod's eligible runs, not the pod.** That requires
per-run terrain, so `domain/derive/terrain.py` gains per-run output alongside its per-pod rollup:
elevation range, aspect, tree cover, TPI, length, vertical, and mean pitch. The per-pod figures
become a derived rollup rather than the primary record.

### Run roles

A run that clears the difficulty gate is not necessarily skiing. Each run is classified from its own
geometry:

| Role | Rule | Counts as skiing |
|---|---|---|
| `descent` | mean pitch above the flat threshold and vertical above the minimum | yes |
| `traverse` | low pitch, meaningful length | no |
| `connector` | short, links two descents | no |
| `egress` | terminates at a base area, low pitch | no |

Thresholds are declared as named constants with a stated basis, not scattered magic numbers.

**A pod qualifies only if it has at least one eligible `descent`.** The flat-cat-track pod fails
qualification and is excluded with a stated reason. This is the concrete case the previous draft got
wrong.

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

**A contrast card, on a crisp rule.** The previous draft's phrasing — "different elevation band or
shelter class, within a threshold, qualitatively different" — was hand-waving with no implementable
meaning. The rule:

- The candidate passed the same gates and was scored on the same shared factor set.
- Its score interval **overlaps** the winner's, or sits within a declared margin.
- It differs from the winner on at least one **contrast axis**, computed over eligible runs, from a
  closed set: `elevation`, `shelter`, `surface`.
- Selection and tie-breaking are deterministic.

**Ties are reported as ties.** If two candidates overlap within uncertainty and differ on no contrast
axis, the honest output is that they are equivalent today. Committing to one and demoting the other
to a card would be manufacturing a distinction the model cannot support.

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
- a pod strictly better on every input must never rank lower
- adding a closed run must not change the ranking
- removing an input must not improve any pod's rank relative to another (the missing-data property
  from §3, asserted directly)
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

- Which SNOTEL station represents Snowmass. The verified recipe covers Ivanhoe (`547:CO:SNTL`); the
  charter names Independence Pass (`542:CO:SNTL`) and flags `531` as a different drainage. Neither is
  confirmed as representative and base depth should not be trusted until one is.
- Factor weights. Deliberately unset here. They are fitted or hand-tuned against a season, not
  guessed in August.
- Whether `fit` belongs in the geometric mean or acts as a gate. It behaves more like a filter than a
  quality signal, and forcing it into the same combination may be wrong.
- Tree cover is biased low for pods whose gladed runs are unmatched in OpenStreetMap. The unmatched
  list is disproportionately glades and walls — `Glade One/Two/Three`, `Powerline Glades`,
  `Hanging Valley Glades`, `Headwall`. Coverage per pod is recorded; the bias direction is known but
  not yet corrected.
