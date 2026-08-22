---
status: accepted
date: 2026-08-22
---

# Terrain profile is separate from pod conditions, and difficulty is fetched

A Pod is modelled as three records on three clocks: identity (never changes), terrain profile
(per season), and conditions (per fetch). The old single `Pod` record fused all three, which is
how "recently groomed" could be a constant in a JSON file while the real grooming report was
being fetched successfully two functions away.

Difficulty moves out of the profile entirely. It is derived from the fetched run list on every
request, not stored.

## Why difficulty had to move

`difficulty_max` gates the hard constraint that keeps a skier off terrain above their level, and
it is wrong for nine of the eleven pods. Reproduce with `npm run verify` in `domain/`; the
authored column is the value the gate actually ran on, resolved through the broken pod map, so
Cirque reads Hanging Valley's row and Pipes/Parks reads the row labelled "Cirque".

| Pod | Gate ran on | Feed's actual max | Effect |
|---|---|---|---|
| Elk Camp | green | black | admits a green skier to advanced terrain |
| Alpine Springs | blue | black | admits a blue skier to advanced terrain |
| Campground | black | double-black | admits a black skier to expert terrain |
| Big Burn | black | extreme | admits a black skier to extreme terrain |
| High Alpine | black | extreme | admits a black skier to extreme terrain |
| Cirque | double-black | extreme | admits a double-black skier to extreme terrain |
| Hanging Valley | double-black | extreme | admits a double-black skier to extreme terrain |
| Sam's Knob | double-black | black | hides a pod the skier could ski |
| Pipes/Parks | black | none — every run is a park | park runs are not a point on this scale |
| Coney Express | blue | blue | agrees |
| Two Creeks | blue | blue | agrees |

Seven of the nine err in the direction that admits a skier to terrain harder than they asked
for. A safety gate has no business running on a guess when the authoritative answer arrives on
every fetch.

The same reasoning does not extend to aspect, elevation, tree cover, or exposure — no feed
carries those, so they stay in the profile and carry provenance instead.

## The gate itself is blunt, and now fixable

Excluding a pod because its single hardest run exceeds the cap throws away the other twenty. Big
Burn has one extreme run among twenty-one, and gating on the maximum hides twelve intermediates
from an intermediate skier. That was unavoidable when the only thing stored per pod was one
scalar. It is avoidable now that the run list is in hand, and the recommender should filter and
score at run granularity within a pod rather than gating the pod on its worst case. Deliberately
left for the scoring-model redesign; recorded here so the blunt version is not mistaken for
intent.

## Consequences

Every value in a terrain profile is a `Sourced<T>`: `fetched`, `surveyed`, or `estimated` with a
documented basis. Absence is a typed state, so a field we have not sourced yet cannot be silently
defaulted into a score — the scorer must either handle it or exclude the pod with a stated
reason. This is the mechanism behind the charter's bar that every number shown traces to a
fetched value or a documented model term.

The cost is that the eleven profiles start mostly unpopulated. Difficulty mix, run counts, park
and gated flags, and per-lift vertical are fetched today; aspect, elevation range, tree cover,
and exposure are not, and the recommender is honestly weaker until they are surveyed off the
trail map and a DEM. Carrying the old attribute sets across the broken pod map would have filled
those fields faster and would have laundered guesses into values that look sourced — the same
table above is what those guesses were worth on the one attribute we can check.
