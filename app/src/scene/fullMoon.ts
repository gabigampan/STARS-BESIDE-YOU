// The "Full Moon" lighting instant, computed from the same Sun and Moon positions Cesium uses
// (Simon et al. 1994, Simon1994PlanetaryPositions), so the date is derived, not typed in.
//
// 1. Opposition: the first local maximum of the Sun-Earth-Moon elongation (angle between the
//    geocentric Sun and Moon directions) after FULL_MOON_SEARCH_FROM, found on an hourly scan and
//    refined by golden-section search to about a second.
// 2. Daylight over Europe and Africa: the instant nearest to opposition at which the sub-solar
//    point on Earth is on FULL_MOON_SUBSOLAR_LON_DEG (15 E, the meridian through central Europe
//    and central Africa), rounded to the minute. The Moon's phase changes by about 0.5 degree per
//    hour, so the near side stays fully lit a few hours either side of opposition.

import { Cartesian3, JulianDate, Math as CesiumMath, Simon1994PlanetaryPositions } from 'cesium';
import { subsolarPointEarth } from './sun';

/** Start of the search: the day this build was made. The result is the next full Moon after it. */
export const FULL_MOON_SEARCH_FROM = '2026-11-14T00:00:00Z';
/** Meridian the Sun should be over at the chosen instant (degrees east). */
export const FULL_MOON_SUBSOLAR_LON_DEG = 15;

const sun = new Cartesian3();
const moon = new Cartesian3();

/** Geocentric angle between the Sun and the Moon, degrees (180 = exact opposition). */
export function elongationDeg(time: JulianDate): number {
  Simon1994PlanetaryPositions.computeSunPositionInEarthInertialFrame(time, sun);
  Simon1994PlanetaryPositions.computeMoonPositionInEarthInertialFrame(time, moon);
  return CesiumMath.toDegrees(Cartesian3.angleBetween(sun, moon));
}

const at = (t0: JulianDate, hours: number) => JulianDate.addSeconds(t0, hours * 3600, new JulianDate());

/** Instant of the first opposition (full Moon) after `from`. */
export function findOpposition(from: JulianDate): JulianDate {
  // Hourly scan for the first local maximum (a lunation is ~709 hours).
  let prev = elongationDeg(at(from, 0));
  let cur = elongationDeg(at(from, 1));
  let h = 1;
  for (; h < 24 * 31; h++) {
    const next = elongationDeg(at(from, h + 1));
    if (cur >= prev && cur > next) break;
    prev = cur;
    cur = next;
  }
  // Golden-section refinement on [h-1, h+1] hours.
  let a = h - 1;
  let b = h + 1;
  const g = (Math.sqrt(5) - 1) / 2;
  let c = b - g * (b - a);
  let d = a + g * (b - a);
  let fc = elongationDeg(at(from, c));
  let fd = elongationDeg(at(from, d));
  while (b - a > 1 / 3600) {
    if (fc > fd) {
      b = d;
      d = c;
      fd = fc;
      c = b - g * (b - a);
      fc = elongationDeg(at(from, c));
    } else {
      a = c;
      c = d;
      fc = fd;
      d = a + g * (b - a);
      fd = elongationDeg(at(from, d));
    }
  }
  return at(from, (a + b) / 2);
}

const wrap180 = (deg: number) => ((((deg + 180) % 360) + 360) % 360) - 180;

export interface FullMoonInstant {
  /** The lighting instant (opposition shifted so the Sun is over FULL_MOON_SUBSOLAR_LON_DEG), to the minute. */
  time: JulianDate;
  /** Exact opposition found by the search. */
  opposition: JulianDate;
  /** Sun-Earth-Moon elongation at `time`, degrees. */
  elongationDeg: number;
  /** Sub-solar point on Earth at `time`, degrees. */
  subsolar: { lat: number; lon: number };
}

/** The Full Moon lighting instant after `fromIso` (defaults to FULL_MOON_SEARCH_FROM). */
export function computeFullMoonInstant(fromIso = FULL_MOON_SEARCH_FROM, subsolarLonDeg = FULL_MOON_SUBSOLAR_LON_DEG): FullMoonInstant {
  const opposition = findOpposition(JulianDate.fromIso8601(fromIso));
  // The sub-solar longitude moves west by ~15 degrees per hour; a few Newton steps find the
  // instant nearest opposition at which it equals the target meridian.
  let t = JulianDate.clone(opposition);
  for (let i = 0; i < 4; i++) {
    const diff = wrap180(subsolarPointEarth(t).lon - subsolarLonDeg);
    t = JulianDate.addSeconds(t, (diff / 15.041) * 3600, new JulianDate());
  }
  // Round to the minute so the documented date is exact.
  const ms = Math.round(JulianDate.toDate(t).getTime() / 60000) * 60000;
  const time = JulianDate.fromDate(new Date(ms));
  return { time, opposition, elongationDeg: elongationDeg(time), subsolar: subsolarPointEarth(time) };
}
