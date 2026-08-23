/** Parsing of Aspen's station-summary table.
 *
 * The table is intentionally parsed from its two header rows.  Aspen has changed both the
 * number and order of sensors in these groups before; column offsets are not an API.
 */

export interface StationField {
  readonly name: string;
  readonly unit: string | null;
}

export interface StationGroup {
  readonly name: string;
  readonly fields: readonly StationField[];
}

export interface StationReading {
  readonly date: string;
  readonly time: string;
  readonly stations: Readonly<Record<string, Readonly<Record<string, number | null>>>>;
}

const tagText = (html: string): string =>
  html
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&deg;/gi, '°')
    .replace(/&amp;/gi, '&')
    .trim();

const cells = (row: string, tag: 'th' | 'td'): string[] => {
  const found: string[] = [];
  const pattern = new RegExp(`<${tag}\\b[^>]*>[\\s\\S]*?<\\/${tag}>`, 'gi');
  for (const match of row.matchAll(pattern)) found.push(match[0]);
  return found;
};

const attr = (html: string, name: string): number => {
  const match = html.match(new RegExp(`\\b${name}\\s*=\\s*["'](\\d+)["']`, 'i'));
  return Number(match?.[1] ?? 1);
};

const fieldName = (cell: string): string => tagText(cell.replace(/<span\b[^>]*class\s*=\s*["'][^"']*units[^"']*["'][^>]*>[\s\S]*?<\/span>/gi, ''));

const rows = (html: string, className: string, tag: 'tr' | 'tbody' = 'tr'): string[] => {
  const pattern = new RegExp(`<${tag}\\b[^>]*class\\s*=\\s*["'][^"']*\\b${className}\\b[^"']*["'][^>]*>[\\s\\S]*?<\\/${tag}>`, 'gi');
  return [...html.matchAll(pattern)].map((match) => match[0]);
};

const tableRows = (html: string): string[] => {
  const body = html.match(/<tbody\b[^>]*>([\s\S]*?)<\/tbody>/i)?.[1] ?? '';
  return [...body.matchAll(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi)].map((row) => row[0]);
};

/** Parse all hourly rows, preserving missing cells as null rather than inventing values. */
export const parseStationSummary = (html: string): readonly StationReading[] => {
  const groupRow = rows(html, 'groups')[0];
  const columnRow = rows(html, 'cols')[0];
  if (!groupRow || !columnRow) return [];

  const groups: { name: string; start: number; end: number }[] = [];
  let column = 0;
  for (const cell of cells(groupRow, 'th')) {
    const span = attr(cell, 'colspan');
    const name = tagText(cell);
    groups.push({ name, start: column, end: column + span });
    column += span;
  }

  const fields = cells(columnRow, 'th').map((cell) => ({
    name: fieldName(cell),
    unit: tagText(cell.match(/<span\b[^>]*class\s*=\s*["'][^"']*units[^"']*["'][^>]*>([\s\S]*?)<\/span>/i)?.[1] ?? '') || null,
  }));

  return tableRows(html).map((row) => {
    const rowCells = cells(row, 'td');
    const values = rowCells.map((cell) => {
      const value = tagText(cell);
      if (value === '' || value === '-') return null;
      const number = Number(value.replace(/,/g, ''));
      return Number.isFinite(number) ? number : null;
    });
    const stations: Record<string, Record<string, number | null>> = {};
    for (const group of groups) {
      if (!group.name) continue;
      const station: Record<string, number | null> = {};
      for (let index = group.start; index < group.end; index += 1) {
        const field = fields[index];
        if (field) station[field.name] = values[index] ?? null;
      }
      stations[group.name] = station;
    }
    const date = tagText(rowCells[0] ?? '');
    const time = tagText(rowCells[1] ?? '');
    return { date, time, stations };
  });
};

/** More explicit alias for callers that parse an HTML document rather than a feed object. */
export const parseStationSummaryHtml = parseStationSummary;
