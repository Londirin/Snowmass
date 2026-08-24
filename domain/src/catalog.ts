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
import { OFFICIAL_POD_NAME, POD_IDS } from './pod.js';

import { derived, estimated, fetched, isoDate, timestamp, unsourced } from './provenance.js';
import type { AspectProfile, ElevationRange, Pod, TerrainProfile } from './terrain.js';
import terrainDerived from '../fixtures/terrain-derived.json' with { type: 'json' };

const GROOMING_FEED_URL =
  'https://www.aspensnowmass.com/AspenSnowmass/GroomingReport/Feed?mountain=Snowmass';
const LIFT_FEED_URL =
  'https://www.aspensnowmass.com/AspenSnowmass/LiftStatus/Feed?mountain=Snowmass&areas=&isSummer=False';

/** The observation this catalog's fetched fields come from. Fixtures in `domain/fixtures/`. */
const OBSERVED = timestamp('2026-08-22T23:40:00Z');

/**
 * Terrain measured rather than guessed.
 *
 * `domain/derive/terrain.py` joins OpenStreetMap run geometry to pods by Aspen's own run names,
 * samples elevation from AWS terrarium tiles, and computes aspect from the fall line, tree cover
 * from timber flanking each run, and exposure as a topographic position index. Importing its
 * output rather than transcribing it means the catalog cannot drift from the derivation.
 *
 * Pipes/Parks is absent: OpenStreetMap does not carry Aspen's park feature names as pistes, so
 * nothing matched. It stays unsourced rather than being filled with a neighbour's numbers.
 */
const DERIVED_ON = isoDate('2026-08-22');
const DERIVED_INPUTS = [
  'OpenStreetMap piste:type=downhill geometry (ODbL)',
  'OpenStreetMap natural=wood + landuse=forest (ODbL)',
  'AWS Terrain Tiles, terrarium encoding, zoom 14',
  'Aspen grooming feed, recorded 2026-08-22, for pod membership',
];
const METHOD = 'domain/derive/terrain.py';

const NAME_TO_ID = new Map<string, PodId>(
  POD_IDS.map((id) => [OFFICIAL_POD_NAME[id], id]),
);

type DerivedPod = {
  aspect: { dominant: string; present: string[] };
  elevation: { bottom_ft: number; top_ft: number };
  tree_cover: { flanking: number | null };
  exposure: { mean_tpi_m: number | null };
  coverage: { runs_matched: number };
};

const DERIVED = new Map<PodId, DerivedPod>();
for (const [officialName, rec] of Object.entries(
  terrainDerived.pods as Record<string, DerivedPod>,
)) {
  const id = NAME_TO_ID.get(officialName);
  if (id) DERIVED.set(id, rec);
}

const UNMEASURED =
  'domain/derive/terrain.py found no OpenStreetMap geometry matching this pod\u2019s runs.';

const terrainFor = (podId: PodId, notes?: string): TerrainProfile => {
  const d = DERIVED.get(podId);
  if (!d) {
    return {
      podId,
      aspect: unsourced(UNMEASURED),
      elevation: unsourced(UNMEASURED),
      treeCover: unsourced(UNMEASURED),
      landform: unsourced(UNMEASURED),
      ...(notes === undefined ? {} : { notes }),
    };
  }
  const aspect: AspectProfile = {
    dominant: d.aspect.dominant as AspectProfile['dominant'],
    present: d.aspect.present as unknown as AspectProfile['present'],
  };
  const elevation: ElevationRange = {
    bottomFt: d.elevation.bottom_ft,
    topFt: d.elevation.top_ft,
  };
  return {
    podId,
    aspect: derived(aspect, DERIVED_INPUTS, METHOD, DERIVED_ON),
    elevation: derived(elevation, DERIVED_INPUTS, METHOD, DERIVED_ON),
    treeCover:
      d.tree_cover.flanking === null
        ? unsourced(UNMEASURED)
        : derived(d.tree_cover.flanking, DERIVED_INPUTS, METHOD, DERIVED_ON),
    landform:
      d.exposure.mean_tpi_m === null
        ? unsourced(UNMEASURED)
        : derived(d.exposure.mean_tpi_m, DERIVED_INPUTS, METHOD, DERIVED_ON),
    ...(notes === undefined ? {} : { notes }),
  };
};

/** How many of the pod's runs the derivation actually matched — a confidence input, not a score. */
export const derivedRunCoverage = (podId: PodId): number =>
  DERIVED.get(podId)?.coverage.runs_matched ?? 0;

const alpine = (id: PodId): Pod['identity'] => ({
  id,
  officialName: OFFICIAL_POD_NAME[id],
  character: 'alpine',
});

export const POD_CATALOG: Record<PodId, Pod> = {
  'alpine-springs': {
    identity: alpine('alpine-springs'),
    terrain: terrainFor('alpine-springs'),
  },
  'big-burn': {
    identity: alpine('big-burn'),
    terrain: terrainFor(
      'big-burn',
      'Spans roughly 2,000 ft of vertical, so a single elevation band would misdescribe it.',
    ),
  },
  campground: { identity: alpine('campground'), terrain: terrainFor('campground') },
  cirque: {
    identity: alpine('cirque'),
    terrain: terrainFor(
      'cirque',
      'Strongly concave and above treeline: the derivation gives it the lowest TPI and the lowest tree cover on the mountain, against the 0.9 tree cover the retired catalog carried. Figures live in terrain-derived.json so they cannot go stale here.',
    ),
  },
  'coney-express': {
    identity: alpine('coney-express'),
    terrain: terrainFor('coney-express'),
  },
  'elk-camp': { identity: alpine('elk-camp'), terrain: terrainFor('elk-camp') },
  'hanging-valley': {
    identity: alpine('hanging-valley'),
    terrain: terrainFor(
      'hanging-valley',
      'No lift of its own in the lift feed. Access is a survey question, not a feed question.',
    ),
  },
  'high-alpine': { identity: alpine('high-alpine'), terrain: terrainFor('high-alpine') },
  'pipes-parks': {
    identity: {
      id: 'pipes-parks',
      officialName: OFFICIAL_POD_NAME['pipes-parks'],
      // Fetched: all six runs carry difficulty `terrain-park`, and the group is `isGatedTerrain`.
      character: 'terrain-park',
    },
    terrain: terrainFor(
      'pipes-parks',
      'Features are rebuilt through the season, so grooming matters here far more than aspect.',
    ),
  },
  'sams-knob': { identity: alpine('sams-knob'), terrain: terrainFor('sams-knob') },
  'two-creeks': { identity: alpine('two-creeks'), terrain: terrainFor('two-creeks') },
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
