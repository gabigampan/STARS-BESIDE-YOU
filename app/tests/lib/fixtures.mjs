// Where the tests find the bundle variants and write their screenshots. Every folder can be set by
// an environment variable; the defaults are inside app/.fixtures/ (ignored by git), never an
// absolute scratch path of one machine.
//   NO_TWIN_BUNDLE (or OTHER_BUNDLE): the no-twin fixture, built with the engine:
//     cd "tierra luna" && python -m engine build --similarity-rule repo_global_mean --out ../app/.fixtures/bundle_global_mean
//   ZONE_FIXTURE, REV5_BUNDLE: optional older variants (tests skip them when absent)
//   SHOTS_DIR: screenshots of the browser tests

import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const APP = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const FIXTURES = join(APP, '.fixtures');
export const NO_TWIN_BUNDLE = process.env.NO_TWIN_BUNDLE ?? process.env.OTHER_BUNDLE ?? join(FIXTURES, 'bundle_global_mean');
export const ZONE_FIXTURE = process.env.ZONE_FIXTURE ?? join(FIXTURES, 'fixture_zones');
export const REV5_BUNDLE = process.env.REV5_BUNDLE ?? join(FIXTURES, 'rev5');
export const SHOTS_DIR = process.env.SHOTS_DIR ?? join(FIXTURES, 'shots');
