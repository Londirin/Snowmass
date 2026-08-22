/**
 * The eleven pods.
 *
 * Populated only where a value is actually sourced. Aspect, elevation, tree cover, and exposure
 * are `unsourced` because as of 2026-08-22 no feed carries them and they have not been surveyed
 * — the four attribute sets in the retired `pods_snowmass_v1.json` were hand-authored guesses
 * reachable only through a slug map that was demonstrably wrong, so porting them across would
 * have dressed guesses up as values. See docs/adr/0002 and `RETIRED_ENTRIES` below.
 */
import type { AccessEdge } from './access.js';
import { liftId } from './access.js';
import type { PodId } from './pod.js';
import { OFFICIAL_POD_NAME } from './pod.js';
import type { Pod } from './terrain.js';
import { estimated, fetched, timestamp, unsourced } from './provenance.js';

const GROOMING_FEED_URL =
  'https://www.aspensnowmass.com/AspenSnowmass/GroomingReport/Feed?mountain=Snowmass';
const LIFT_FEED_URL =
  'https://www.aspensnowmass.com/AspenSnowmass/LiftStatus/Feed?mountain=Snowmass&areas=&isSummer=False';

/** The observation this catalog's fetched fields come from. Fixtures in `domain/fixtures/`. */
const OBSERVED = timestamp('2026-08-22T23:40:00Z');

const TRAIL_MAP_SURVEY =
  'Aspen Snowmass winter trail map + a 10m DEM. Not yet done — this is the next data task.';

const alpine = (id: PodId): Pod['identity'] => ({
  id,
  officialName: OFFICIAL_POD_NAME[id],
  character: 'alpine',
});

const unsurveyedTerrain = (podId: PodId, notes?: string): Pod['terrain'] => ({
  podId,
  aspect: unsourced(TRAIL_MAP_SURVEY),
  elevation: unsourced(TRAIL_MAP_SURVEY),
  treeCover: unsourced(TRAIL_MAP_SURVEY),
  exposure: unsourced(TRAIL_MAP_SURVEY),
  notes,
});

export const POD_CATALOG: Record<PodId, Pod> = {
  'alpine-springs': {
    identity: alpine('alpine-springs'),
    terrain: unsurveyedTerrain('alpine-springs'),
  },
  'big-burn': {
    identity: alpine('big-burn'),
    terrain: unsurveyedTerrain(
      'big-burn',
      'Spans roughly 2,000 ft of vertical, so a single elevation band would misdescribe it.',
    ),
  },
  campground: { identity: alpine('campground'), terrain: unsurveyedTerrain('campground') },
  cirque: {
    identity: alpine('cirque'),
    terrain: unsurveyedTerrain(
      'cirque',
      'Above treeline: 15 of 16 runs are expert or extreme per the feed. Any tree-cover estimate should start near zero, not at the 0.9 the retired catalog carried.',
    ),
  },
  'coney-express': {
    identity: alpine('coney-express'),
    terrain: unsurveyedTerrain('coney-express'),
  },
  'elk-camp': { identity: alpine('elk-camp'), terrain: unsurveyedTerrain('elk-camp') },
  'hanging-valley': {
    identity: alpine('hanging-valley'),
    terrain: unsurveyedTerrain(
      'hanging-valley',
      'No lift of its own in the lift feed. Access is a survey question, not a feed question.',
    ),
  },
  'high-alpine': { identity: alpine('high-alpine'), terrain: unsurveyedTerrain('high-alpine') },
  'pipes-parks': {
    identity: {
      id: 'pipes-parks',
      officialName: OFFICIAL_POD_NAME['pipes-parks'],
      // Fetched: all six runs carry difficulty `terrain-park`, and the group is `isGatedTerrain`.
      character: 'terrain-park',
    },
    terrain: unsurveyedTerrain(
      'pipes-parks',
      'Features are rebuilt through the season, so grooming matters here far more than aspect.',
    ),
  },
  'sams-knob': { identity: alpine('sams-knob'), terrain: unsurveyedTerrain('sams-knob') },
  'two-creeks': { identity: alpine('two-creeks'), terrain: unsurveyedTerrain('two-creeks') },
};

/**
 * Lift → pod access.
 *
 * The eight `fetched` edges are ones where the lift feed files the lift under a service area
 * whose name is a pod name — Aspen asserting the link itself. The rest are gaps: three pods have
 * no lift filed under their own name, and how you reach them is terrain knowledge that has to be
 * surveyed. `KNOWN_ACCESS_GAPS` names them rather than letting them read as `no-access`.
 */
const fetchedEdge = (lift: string, pod: PodId): AccessEdge => ({
  lift: liftId(lift),
  pod,
  kind: 'primary',
  source: fetched(null, LIFT_FEED_URL, 'liftStatuses[].area', OBSERVED).source,
});

export const ACCESS_EDGES: readonly AccessEdge[] = [
  fetchedEdge('Alpine Springs', 'alpine-springs'),
  fetchedEdge('Big Burn', 'big-burn'),
  fetchedEdge('Sheer Bliss', 'big-burn'),
  fetchedEdge('Campground', 'campground'),
  fetchedEdge('Village Express', 'coney-express'),
  fetchedEdge('Sky Cab Gondola', 'coney-express'),
  fetchedEdge('Scooper Surface Lift', 'coney-express'),
  fetchedEdge('Treehouse Carpet', 'coney-express'),
  fetchedEdge('Elk Camp Gondola', 'elk-camp'),
  fetchedEdge('Elk Camp Chairlift', 'elk-camp'),
  fetchedEdge('Meadows Chairlift', 'elk-camp'),
  fetchedEdge('Meadows Carpet', 'elk-camp'),
  fetchedEdge('Assay Hill', 'elk-camp'),
  fetchedEdge('Assay Hill Carpet', 'elk-camp'),
  fetchedEdge('Bear Bottom Carpet', 'elk-camp'),
  fetchedEdge('High Alpine', 'high-alpine'),
  fetchedEdge("Sam's Knob", 'sams-knob'),
  fetchedEdge('Two Creeks', 'two-creeks'),
  {
    lift: liftId('Cirque Surface Lift'),
    pod: 'cirque',
    kind: 'primary',
    source: estimated(
      null,
      "The lift feed files this lift under the Big Burn service area, but names it for the Cirque pod and gives it 806 ft of vertical. Name and vertical both point at Cirque; confirm against the trail map before this drives an answer.",
    ).source,
  },
];

/**
 * Pods with no sourced lift access. They must resolve to `unknown`, never `no-access` — reporting
 * a real pod as unreachable is the same class of confident wrong answer this rebuild exists to fix.
 */
export const KNOWN_ACCESS_GAPS: Partial<Record<PodId, string>> = {
  'hanging-valley':
    'No lift filed under this name. Reached from the top of another lift by traverse or hike — which one, and whether it is gated, needs the trail map.',
  'pipes-parks':
    'No lift filed under this name. Parks sit on the lower mountain and are presumably served from the Coney Express side; unconfirmed.',
};

/**
 * The retired `pods_snowmass_v1.json`, recorded so the reconciliation is auditable rather than
 * a silent deletion. Twelve entries for ten reachable pods, keyed by a slug namespace of run and
 * lift names that was never the pod namespace.
 */
export const RETIRED_ENTRIES: readonly {
  readonly slug: string;
  readonly displayName: string;
  readonly resolvesTo: PodId | null;
  readonly note: string;
}[] = [
  { slug: 'elkrange_beginner', displayName: 'Elk Camp', resolvesTo: 'elk-camp', note: 'Authored difficulty_max=green; the feed shows an advanced run in this pod.' },
  { slug: 'fanny_hill', displayName: 'Coney Express', resolvesTo: 'coney-express', note: 'Slug is a run name. Authored difficulty agreed with the feed.' },
  { slug: 'village_express_cruisers', displayName: 'Two Creeks', resolvesTo: 'two-creeks', note: 'Slug is a base-area lift that does not serve Two Creeks.' },
  { slug: 'big_burn', displayName: 'Big Burn', resolvesTo: 'big-burn', note: 'Authored difficulty_max=black; the feed shows one extreme run.' },
  { slug: 'sams_knob', displayName: "Sam's Knob", resolvesTo: 'sams-knob', note: 'Authored difficulty_max=double_black; the feed tops out at advanced.' },
  { slug: 'campground_glades', displayName: 'Campground', resolvesTo: 'campground', note: 'Authored difficulty_max=black; the feed shows an expert run.' },
  { slug: 'sheer_bliss', displayName: 'High Alpine', resolvesTo: 'high-alpine', note: 'Slug is a lift the feed files under Big Burn.' },
  { slug: 'alpine_springs', displayName: 'Alpine Springs', resolvesTo: 'alpine-springs', note: 'Authored difficulty_max=blue; the feed shows an advanced run.' },
  { slug: 'hanging_valley_wall', displayName: 'Hanging Valley', resolvesTo: 'hanging-valley', note: 'Also the target of the "Cirque" key in the retired OFFICIAL_POD_TO_ID map.' },
  { slug: 'adams_avenue', displayName: 'Elk Camp', resolvesTo: null, note: 'Duplicate display name, unreachable from the crosswalk, still scored — two identically named pods could share one top-three.' },
  { slug: 'sneaky_glades', displayName: 'Cirque', resolvesTo: null, note: 'Target of the "Pipes/Parks" key. Described as 0.9 tree cover and difficulty_max=black; the real Cirque is an above-treeline bowl that is 15/16 expert or extreme.' },
  { slug: 'lower_crosswinds', displayName: 'Coney Express', resolvesTo: null, note: 'Duplicate display name, unreachable from the crosswalk, still scored.' },
];

/** Pipes/Parks had no entry at all in the retired catalog, so it could never be recommended. */
export const PODS_MISSING_FROM_RETIRED_CATALOG: readonly PodId[] = ['pipes-parks'];
