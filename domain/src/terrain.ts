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

/**
 * Topographic position index, in metres: the pod's mean height above its own surroundings.
 *
 * Positive is convex — a ridge or shoulder, where wind strips snow away. Negative is concave — a
 * bowl or gully where wind-drifted snow collects. It describes snow DEPOSITION, not shelter, and
 * the two come apart: Cirque reads -13.7 m and is above treeline. A continuous measurement
 * replaces the hand-guessed `low`/`medium`/`high` label the retired catalog carried.
 */
export type LandformTpiMetres = number;

/**
 * Landform bands, for display only. Never score off these — score off the metres.
 *
 * Deliberately named for shape, not shelter. TPI measures where snow collects, which is not the
 * same question as whether a place is pleasant to stand in: Cirque is strongly concave and also
 * above treeline, so it collects wind-drifted snow while being exposed to everything. Calling a
 * negative TPI "sheltered" would licence exactly that confusion.
 */
export const landformBand = (tpi: number): 'concave' | 'neutral' | 'convex' =>
  tpi <= -3 ? 'concave' : tpi >= 3 ? 'convex' : 'neutral';

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
  readonly landform: Field<LandformTpiMetres>;
  /** Free text for the things the numbers do not carry. Shown to nobody; read by whoever edits this. */
  readonly notes?: string | undefined;
}

export interface Pod {
  readonly identity: PodIdentity;
  readonly terrain: TerrainProfile;
}
