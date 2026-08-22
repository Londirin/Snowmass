---
status: accepted
date: 2026-08-22
---

# Pod identity is the official Aspen pod name

A Pod's identity is a slug derived from the name Aspen's own grooming feed uses for it, drawn
from a closed set of eleven. The private slug namespace in `pods_snowmass_v1.json`
(`fanny_hill`, `sheer_bliss`, `sneaky_glades`, …), the `OFFICIAL_POD_TO_ID` map that translated
between the two, and the `snowmass_run_crosswalk.csv` lookup that assigned runs to pods are all
retired. The feed already tags every run with its pod on every fetch; nothing needs to translate.

## Why

The crosswalk CSV is not an independent source. Reconciled against a live fetch on 2026-08-22,
all 130 of its rows appear in the feed with identical pod, run name, and difficulty — zero
disagreements — and the feed's only 7 extra rows are its three non-ski groups. The CSV is a
derived snapshot, so the lookup it powered added a lossy hop and no information.

That hop is where pod identity broke. The chain ran feed pod name → discard → run name → CSV →
pod name → hand-maintained slug map → hand-authored attributes. Two joins on hand-maintained
tables, each a chance to be wrong, and both were: `OFFICIAL_POD_TO_ID` sent Cirque and Hanging
Valley to the same slug and sent Pipes/Parks to a slug labelled "Cirque". Deleting the hops
deletes the bug class, not just today's instances.

The `RUN_ALIASES` table is retired with them. It patched four run names that the live feed does
not use — `Adam's Avenue` bare, where the feed has `(Lower)` and `(Upper)`. Those names come
from the hand-written test fixture, so the aliases existed to reconcile the code with a fixture
that misdescribed the source rather than with the source.

## Considered options

**Open string ids.** Resilient to Aspen renaming or adding a pod, but gives up any guarantee
that a pod arriving from the feed has a terrain profile to score against — the failure would be
a silently under-described pod, which is the failure mode this project already shipped once.

**Closed union of eleven, chosen.** Unrecognized pod names are a typed diagnostic: reported,
and excluded from scoring with a stated reason, never scored on defaults. The set has been
stable across the two observations we have (the crosswalk's capture and 2026-08-22) and a
rename should be something a human sees, not something the app absorbs.

## Consequences

Run-to-pod assignment now costs nothing and cannot drift, but the app inherits Aspen's naming:
if they rename a pod mid-season, every run in it lands in the unrecognized bucket and that pod
drops out of recommendations until the union is updated. That is the intended trade — a visible
gap over a confident wrong answer — and it needs to fail loudly enough to notice from the lift.
