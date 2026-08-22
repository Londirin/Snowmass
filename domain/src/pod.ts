/**
 * Pod identity.
 *
 * A pod's identity is the name Aspen's grooming feed uses for it. There is one namespace and it
 * arrives on every fetch — see docs/adr/0001. The slug is derived from the official name by a
 * fixed rule but declared explicitly, so that an upstream rename surfaces as an unrecognized
 * pod rather than quietly becoming a twelfth one.
 */

/** The eleven ski pods of Snowmass. Closed on purpose. */
export type PodId =
  | 'alpine-springs'
  | 'big-burn'
  | 'campground'
  | 'cirque'
  | 'coney-express'
  | 'elk-camp'
  | 'hanging-valley'
  | 'high-alpine'
  | 'pipes-parks'
  | 'sams-knob'
  | 'two-creeks';

export const POD_IDS = [
  'alpine-springs',
  'big-burn',
  'campground',
  'cirque',
  'coney-express',
  'elk-camp',
  'hanging-valley',
  'high-alpine',
  'pipes-parks',
  'sams-knob',
  'two-creeks',
] as const satisfies readonly PodId[];

/**
 * Verbatim as the grooming feed spells it, apostrophe and slash included. This is the join key
 * against raw payloads; nothing else should string-match on pod names.
 */
export const OFFICIAL_POD_NAME: Record<PodId, string> = {
  'alpine-springs': 'Alpine Springs',
  'big-burn': 'Big Burn',
  campground: 'Campground',
  cirque: 'Cirque',
  'coney-express': 'Coney Express',
  'elk-camp': 'Elk Camp',
  'hanging-valley': 'Hanging Valley',
  'high-alpine': 'High Alpine',
  'pipes-parks': 'Pipes/Parks',
  'sams-knob': "Sam's Knob",
  'two-creeks': 'Two Creeks',
};

/**
 * Groups in the grooming feed that are not ski pods. They arrive in the same array as the pods
 * and must be dropped before scoring, not scored and then filtered.
 */
export const NON_SKI_GROOMING_GROUPS = [
  'Uphill Routes',
  'Hike/XC Bike Trails',
  'Lost Forest',
] as const;

export type NonSkiGroomingGroup = (typeof NON_SKI_GROOMING_GROUPS)[number];

const BY_OFFICIAL_NAME = new Map<string, PodId>(
  POD_IDS.map((id) => [OFFICIAL_POD_NAME[id], id]),
);
const NON_SKI = new Set<string>(NON_SKI_GROOMING_GROUPS);

/**
 * What a grooming-feed group turned out to be.
 *
 * `unrecognized` is the important arm: Aspen renaming or adding a pod is a thing a human needs
 * to see, so it becomes a diagnostic carried to the response, never a pod scored on defaults.
 */
export type GroomingGroup =
  | { readonly kind: 'pod'; readonly podId: PodId }
  | { readonly kind: 'non-ski'; readonly name: NonSkiGroomingGroup }
  | { readonly kind: 'unrecognized'; readonly name: string };

export const classifyGroomingGroup = (feedName: string): GroomingGroup => {
  const name = feedName.trim();
  const podId = BY_OFFICIAL_NAME.get(name);
  if (podId) return { kind: 'pod', podId };
  if (NON_SKI.has(name)) return { kind: 'non-ski', name: name as NonSkiGroomingGroup };
  return { kind: 'unrecognized', name };
};

/** What kind of skiing a pod is. Parks do not take the aspect-and-wind physics meaningfully. */
export type PodCharacter = 'alpine' | 'terrain-park';

export interface PodIdentity {
  readonly id: PodId;
  /** Exactly as Aspen spells it. */
  readonly officialName: string;
  readonly character: PodCharacter;
}
