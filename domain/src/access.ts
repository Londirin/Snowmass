/**
 * Which lifts get you into which pods.
 *
 * This cannot be read off the lift feed. That feed groups lifts into eight service areas which
 * are not the eleven pods and are not a subset of them: the Cirque Surface Lift is filed under
 * Big Burn, and Cirque, Hanging Valley, and Pipes/Parks have no lift filed under their own name
 * at all. Joining lifts to pods on that field would report three real pods as unserved whenever
 * the mountain is open — a confident wrong answer of exactly the kind this project already shipped.
 *
 * So the relation is hand-authored terrain knowledge. It is authored over two stable, fetched
 * vocabularies — nineteen named lifts, eleven named pods — rather than over invented slugs, and
 * every row carries provenance like any other unfetched value.
 */
import type { PodId } from './pod.js';
import type { Provenance } from './provenance.js';

/** The lift's name exactly as the lift feed spells it. */
export type LiftId = string & { readonly __brand: 'LiftId' };

export const liftId = (feedLiftName: string): LiftId => feedLiftName.trim() as LiftId;

/**
 * `primary` — the lift lands you in that pod's terrain.
 * `connecting` — you reach the pod from that lift's top by traverse or hike.
 *
 * The distinction matters for the answer given to a skier: a pod reachable only by a traverse
 * from a running lift is open to them but costs twenty minutes, and a pod whose only connecting
 * lift is on wind hold is not reachable at all.
 */
export type AccessKind = 'primary' | 'connecting';

export interface AccessEdge {
  readonly lift: LiftId;
  readonly pod: PodId;
  readonly kind: AccessKind;
  readonly source: Provenance;
}

/** How a pod stands today, once lift statuses are applied to the access edges. */
export type PodAccess =
  | { readonly kind: 'lift-served'; readonly via: readonly LiftId[] }
  | { readonly kind: 'traverse-only'; readonly from: readonly LiftId[] }
  | { readonly kind: 'no-access'; readonly reason: string }
  /** Lift feed unreachable — we do not know, and saying so beats guessing either way. */
  | { readonly kind: 'unknown'; readonly reason: string };
