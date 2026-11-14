#!/usr/bin/env node
// Builds public/static/iau_moon_features.json from the USGS/IAU Gazetteer of Planetary
// Nomenclature Moon centre-point shapefile (MOON_nomenclature_center_pts.dbf).
// Source: https://planetarynames.wr.usgs.gov/GIS_Downloads
//   https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.zip
// Usage: node scripts/build_iau_features.mjs [path/to/MOON_nomenclature_center_pts.dbf]
// The gazetteer stores centre longitude as 0..360 east; it is converted here to -180..180 east.
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readDbf } from './dbf.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const DEFAULT_DBF =
  '/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/iau/moon_shp/MOON_nomenclature_center_pts.dbf';
const src = process.argv[2] ?? DEFAULT_DBF;
const out = resolve(here, '../public/static/iau_moon_features.json');

// Feature classes kept whatever their size (they are the large named regions).
const ALWAYS = new Set(['Mare', 'Oceanus', 'Lacus', 'Sinus', 'Palus', 'Planitia', 'Mons', 'Vallis', 'Rupes', 'Statio']);
// Smaller classes kept above a size threshold (km).
const MIN_DIAMETER = { Crater: 10, Rima: 60, Dorsum: 60, Catena: 40, Promontorium: 0 };

const { rows } = readDbf(src);
const round = (v, d) => Math.round(v * 10 ** d) / 10 ** d;
const features = [];
for (const r of rows) {
  if (r.approval !== 'Adopted by IAU') continue;
  const cls = String(r.type).split(',')[0].trim();
  const d = typeof r.diameter === 'number' ? r.diameter : 0;
  const keep = ALWAYS.has(cls) || (cls in MIN_DIAMETER && d >= MIN_DIAMETER[cls]);
  if (!keep) continue;
  let lon = Number(r.center_lon);
  if (lon > 180) lon -= 360;
  const lat = Number(r.center_lat);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
  features.push([r.clean_name || r.name, cls, round(lat, 3), round(lon, 3), round(d, 1)]);
}
features.sort((a, b) => b[4] - a[4]);

const doc = {
  source: 'USGS Gazetteer of Planetary Nomenclature, Moon centre points (IAU WGPSN)',
  url: 'https://planetarynames.wr.usgs.gov/GIS_Downloads',
  credit: 'Gazetteer of Planetary Nomenclature, International Astronomical Union (IAU) Working Group for Planetary System Nomenclature (WGPSN), USGS Astrogeology Science Center',
  coordinates: 'planetocentric latitude, longitude east in -180..180 degrees, sphere R = 1737.4 km',
  fields: ['name', 'type', 'lat', 'lon', 'diameter_km'],
  features,
};
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify(doc));
console.log(`wrote ${features.length} features to ${out}`);
