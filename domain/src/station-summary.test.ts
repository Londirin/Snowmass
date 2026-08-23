import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseStationSummary } from './station-summary.js';

const fixture = (name: string): string =>
  readFileSync(join(process.cwd(), 'fixtures', name), 'utf8');

test('the real off-season fixture preserves missing values as null', () => {
  const readings = parseStationSummary(fixture('station-summary.2026-08-22.html'));
  assert.equal(readings.length, 25);
  assert.equal(
    readings.flatMap((reading) => Object.values(reading.stations).flatMap(Object.values)).filter(
      (value) => value !== null,
    ).length,
    0,
  );
});

test('the synthetic winter fixture round-trips its values', () => {
  const reading = parseStationSummary(fixture('station-summary.synthetic-winter.html'))[0];
  assert.deepEqual(reading?.stations.Timbline, {
    'Tot Snow': 1.5,
    'New Snow': 2.5,
    Temp: 3.5,
    'Rel Hum': 4.5,
    Baro: 5.5,
    T20: 6.5,
    'T Surface': 7.5,
    'Net Total': 8.5,
    Albedo: 9.5,
  });
});

test('group labels, not fixed positions, determine station assignment', () => {
  const html = fixture('station-summary.synthetic-winter.html').replace('>Timbline</th>', '>Changed Group</th>');
  const reading = parseStationSummary(html)[0];
  assert.equal(reading?.stations['Changed Group']?.['Tot Snow'], 1.5);
  assert.equal(reading?.stations['Mid Alt']?.['Tot Snow'], 10.5);
});
