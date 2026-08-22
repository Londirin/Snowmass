# Snowmass run recommender

Recommends where to ski at Snowmass right now, given today's grooming, lift status, snow, and
weather, plus the skier's constraints and preferences.

The mountain has its own vocabulary and this project uses it. Where our earlier code invented a
private name for something Aspen already names, the invented name is listed under _Avoid_.

## Terrain

**Pod**:
One of the eleven named ski-terrain zones of Snowmass. The unit the recommender recommends.
Aspen names them and every run belongs to exactly one.
_Avoid_: Area, zone, sector, region.

**Area**:
Banned as a domain term. Aspen's two feeds both use the word for different partitions of the
mountain — the grooming feed splits it fourteen ways, the lift feed eight — so unqualified "area"
is always ambiguous. Say Pod, Grooming Area, or Lift Service Area.

**Grooming Area**:
A group in the grooming feed's raw payload. Fourteen of them: the eleven Pods plus three
non-ski groups (Uphill Routes, Hike/XC Bike Trails, Lost Forest).

**Lift Service Area**:
A group in the lift feed's raw payload. Eight of them, coarser than the Pods and not a subset —
the Cirque Surface Lift is filed under Big Burn, and three Pods have no lift filed under their
own name at all. Never join a Lift to a Pod on this field.

**Run**:
A named trail within one Pod. Carries a difficulty and today's open and groomed status.
_Avoid_: Trail (Aspen's raw payload word — used only when quoting the feed), piste.

**Lift**:
A named uphill conveyance. Serves one or more Pods through the Access relation.

**Access**:
The relation from a Lift to the Pods you can ski from it. `primary` means the Lift lands you in
that Pod's terrain; `connecting` means you reach the Pod from that Lift's top by traverse or
hike. Hand-authored terrain knowledge, not a feed field.

**Aspect**:
The compass direction a slope faces. Governs sun exposure, so it drives both slush and
wind-loading. One of the two axes of the mountain's real physics.

**Elevation Band**:
Where a Pod's terrain sits vertically. The other axis. A Pod spans a range, not a point — Big
Burn covers nearly two thousand feet — so a single band label per Pod is a lossy description.

**Exposure**:
How much of a Pod is open to wind and flat light, as opposed to sheltered by trees or terrain.

## Facets of a Pod

The three change on completely different clocks and the earlier model's central mistake was
storing them in one record.

**Pod Identity**:
The Pod's name and stable key. Aspen owns it. Changes approximately never.

**Terrain Profile**:
A Pod's physical character — aspect, elevation range, tree cover, exposure, lift access.
Changes when the mountain is re-cut, so effectively per season.

**Pod Conditions**:
What is true of a Pod today — which runs are open, which were groomed, which lifts are turning,
how deep the snow is. Changes hourly and is always fetched, never stored as a constant.
_Avoid_: Status (too vague — say which of open, groomed, or lift status you mean).

**Pod Assessment**:
The scored result for one Pod over one time window, given a skier's constraints. The join of
Terrain Profile, Pod Conditions, and the weather forecast. Never persisted.
_Avoid_: Recommendation (reserve that for the ranked top-three actually shown).

## Evidence

**Provenance**:
Where a value came from: `fetched` from a named source at a named time, `surveyed` off an
official map or dataset, or `estimated` from a documented model term. Every number the app shows
carries one. A value with no provenance is not displayed.

**Sourced Value**:
A value bound to its Provenance. The absence of one is a first-class state the scorer must
handle, not a default that scores silently.

**Source Health**:
Whether a data source answered this time: live, serving a cache of stated age, or unreachable
with a stated reason. Surfaced to the skier rather than hidden behind a spinner.

**Fallback**:
Serving the last good payload when a source is unreachable. Always labelled with its age. The
project's original failure was scoring against a stale constant while presenting it as current.
