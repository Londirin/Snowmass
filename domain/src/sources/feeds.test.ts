import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { maxDifficultyOf } from '../conditions.js';
import { buildMountainConditions } from './lifts.js';
import type { GroomingFeedPayload } from './grooming.js';
import type { LiftFeedPayload } from './lifts.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const fixture = <T>(name: string): T =>
  JSON.parse(readFileSync(join(HERE, '..', '..', 'fixtures', name), 'utf8')) as T;

const grooming = (): GroomingFeedPayload => fixture('grooming-feed.2026-08-22.json');
const lifts = (): LiftFeedPayload => fixture('lift-status.2026-08-22.json');

test('recorded Aspen fixtures parse into the expected mountain counts', () => {
  const conditions = buildMountainConditions(grooming(), lifts());
  const runCount = [...conditions.pods.values()].reduce((count, pod) => count + pod.runs.length, 0);

  assert.equal(conditions.pods.size, 11);
  assert.equal(runCount, 130);
  assert.equal(conditions.lifts.length, 19);
});

test('each pod maxDifficulty is derived from its own runs', () => {
  const conditions = buildMountainConditions(grooming(), lifts());
  const alpine = conditions.pods.get('alpine-springs');
  const coney = conditions.pods.get('coney-express');

  assert.ok(alpine);
  assert.ok(coney);
  assert.equal(alpine.maxDifficulty.value, maxDifficultyOf(alpine.runs));
  assert.equal(alpine.maxDifficulty.value, 'black');
  assert.equal(coney.maxDifficulty.value, maxDifficultyOf(coney.runs));
  assert.equal(coney.maxDifficulty.value, 'blue');
});

test('invented grooming groups are carried as diagnostics', () => {
  const payload = grooming();
  const conditions = buildMountainConditions({
    ...payload,
    areas: [...payload.areas, { name: 'Invented Pod', isGatedTerrain: false, trails: [] }],
  }, lifts());

  assert.ok(conditions.diagnostics.some((diagnostic) => diagnostic.includes('Invented Pod')));
});

test('hanging-valley has unknown rather than no-access', () => {
  const conditions = buildMountainConditions(grooming(), lifts());
  assert.equal(conditions.pods.get('hanging-valley')?.access.kind, 'unknown');
});

test('unmapped lift statuses preserve raw text and add a diagnostic', () => {
  const payload = lifts();
  const first = payload.liftStatuses[0];
  assert.ok(first);
  const conditions = buildMountainConditions(grooming(), {
    ...payload,
    liftStatuses: [{ ...first, status: 'Wind Hold' }, ...payload.liftStatuses.slice(1)],
  });
  const lift = conditions.lifts[0];

  assert.ok(lift);
  assert.equal(lift.statusRaw, 'Wind Hold');
  assert.ok(conditions.diagnostics.some((diagnostic) => diagnostic.includes('Wind Hold')));
});
