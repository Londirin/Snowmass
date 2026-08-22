/**
 * A pod's physical character — the half of the model that does not change day to day.
 *
 * Difficulty is deliberately absent: it is fetched per request from the run list, because the
 * hand-authored values contradicted the feed for five of ten pods and one of those errors was
 * safety-relevant. See docs/adr/0002.
 */
import type { Field } from './provenance.js';
import type { PodId, PodIdentity } from './pod.js';

export type Aspect = 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW';

/** Aspects that bake in spring sun and drive the slush penalty. */
export const SUN_ASPECTS = new Set<Aspect>(['S', 'SE', 'SW']);

/**
 * Which way a pod's skiable terrain faces.
 *
 * A set rather than a scalar because real pods wrap a ridge, and `dominant` because they are not
 * evenly split — Big Burn is mostly north with west shoulders, and a mean of N and W is NW,
 * which is a direction it barely holds.
 */
export interface AspectProfile {
  readonly dominant: Aspect;
  /** Includes `dominant`. Non-empty by construction. */
  readonly present: readonly [Aspect, ...Aspect[]];
}

/**
 * A pod's vertical extent, in feet.
 *
 * A range, not a band label. Big Burn covers close to two thousand feet, so "upper" describes
 * its top and misdescribes its bottom — and elevation is one of the two axes that decide whether
 * a storm left powder or rain crust.
 */
export interface ElevationRange {
  readonly bottomFt: number;
  readonly topFt: number;
}

/** How much of the pod is open to wind and flat light. */
export type Exposure = 'sheltered' | 'mixed' | 'exposed';

/**
 * Per-season terrain description. Every field is a `Field<T>`, so an unpopulated one is a state
 * the scorer must decide about rather than a hole that `??` fills with a guess.
 */
export interface TerrainProfile {
  readonly podId: PodId;
  readonly aspect: Field<AspectProfile>;
  readonly elevation: Field<ElevationRange>;
  /** 0–1. The share of the pod's terrain with skiable trees, which is what saves a flat-light day. */
  readonly treeCover: Field<number>;
  readonly exposure: Field<Exposure>;
  /** Free text for the things the numbers do not carry. Shown to nobody; read by whoever edits this. */
  readonly notes?: string | undefined;
}

export interface Pod {
  readonly identity: PodIdentity;
  readonly terrain: TerrainProfile;
}
