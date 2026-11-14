import { Cartesian3, JulianDate, Math as CesiumMath, Matrix3, Simon1994PlanetaryPositions, Transforms } from 'cesium';

// Orientation of the Moon from the IAU WGCCRE report (Archinal et al. 2018, Celest. Mech. Dyn.
// Astron. 130:22, table for the Moon): pole right ascension alpha0, declination delta0 and prime
// meridian angle W, in degrees, with d = days and T = Julian centuries since J2000 (TDB).
// Rotation ICRF -> body-fixed = Rz(W) * Rx(90 - delta0) * Rz(90 + alpha0).
// (CesiumJS 1.147's computeIcrfToMoonFixedMatrix put the sub-Earth point near 57-177 deg longitude
// in our checks instead of near 0, so the standard model is implemented here.)

const D = CesiumMath.RADIANS_PER_DEGREE;
const J2000 = 2451545.0;
const TT_MINUS_UTC_S = 69.184; // 32.184 s + 37 leap seconds (valid since 2017)

function moonOrientation(time: JulianDate): { alpha0: number; delta0: number; w: number } {
  const jd = time.dayNumber + (time.secondsOfDay + TT_MINUS_UTC_S) / 86400;
  const d = jd - J2000;
  const T = d / 36525;
  const E = [
    0,
    125.045 - 0.0529921 * d,
    250.089 - 0.1059842 * d,
    260.008 + 13.0120009 * d,
    176.625 + 13.3407154 * d,
    357.529 + 0.9856003 * d,
    311.589 + 26.4057084 * d,
    134.963 + 13.064993 * d,
    276.617 + 0.3287146 * d,
    34.226 + 1.7484877 * d,
    15.134 - 0.1589763 * d,
    119.743 + 0.0036096 * d,
    239.961 + 0.1643573 * d,
    25.053 + 12.9590088 * d,
  ].map((v) => v * D);
  const s = (i: number) => Math.sin(E[i] as number);
  const c = (i: number) => Math.cos(E[i] as number);
  const alpha0 =
    269.9949 + 0.0031 * T - 3.8787 * s(1) - 0.1204 * s(2) + 0.07 * s(3) - 0.0172 * s(4) + 0.0072 * s(6) -
    0.0052 * s(10) + 0.0043 * s(13);
  const delta0 =
    66.5392 + 0.013 * T + 1.5419 * c(1) + 0.0239 * c(2) - 0.0278 * c(3) + 0.0068 * c(4) - 0.0029 * c(6) +
    0.0009 * c(7) + 0.0008 * c(10) - 0.0009 * c(13);
  const w =
    38.3213 + 13.17635815 * d - 1.4e-12 * d * d + 3.561 * s(1) + 0.1208 * s(2) - 0.0642 * s(3) + 0.0158 * s(4) +
    0.0252 * s(5) - 0.0066 * s(6) - 0.0047 * s(7) - 0.0046 * s(8) + 0.0028 * s(9) + 0.0052 * s(10) +
    0.004 * s(11) + 0.0019 * s(12) - 0.0044 * s(13);
  return { alpha0: alpha0 * D, delta0: delta0 * D, w: w * D };
}

const rz1 = new Matrix3();
const rx = new Matrix3();
const rz2 = new Matrix3();

/** Rotation from ICRF axes to the Moon's body-fixed axes (IAU model). */
export function icrfToMoonFixed(time: JulianDate, result = new Matrix3()): Matrix3 {
  const { alpha0, delta0, w } = moonOrientation(time);
  // Matrix3.fromRotationZ(a) rotates vectors by +a; frame rotations need the transpose (-a).
  Matrix3.fromRotationZ(-(CesiumMath.PI_OVER_TWO + alpha0), rz1);
  Matrix3.fromRotationX(-(CesiumMath.PI_OVER_TWO - delta0), rx);
  Matrix3.fromRotationZ(-w, rz2);
  Matrix3.multiply(rx, rz1, result);
  return Matrix3.multiply(rz2, result, result);
}

const sunInertial = new Cartesian3();
const moonInertial = new Cartesian3();
const m3 = new Matrix3();

/**
 * Unit vector from the Moon's centre toward the Sun in the Moon's body-fixed frame (the frame of
 * Cesium's Ellipsoid.MOON globe: latitude/longitude as in the IAU gazetteer). Sun and Moon positions
 * come from Simon et al. (1994), as Cesium uses for its own Sun and Moon.
 */
export function sunDirectionMoonFixed(time: JulianDate, result = new Cartesian3()): Cartesian3 {
  Simon1994PlanetaryPositions.computeSunPositionInEarthInertialFrame(time, sunInertial);
  Simon1994PlanetaryPositions.computeMoonPositionInEarthInertialFrame(time, moonInertial);
  const toSun = Cartesian3.subtract(sunInertial, moonInertial, result);
  Matrix3.multiplyByVector(icrfToMoonFixed(time, m3), toSun, toSun);
  return Cartesian3.normalize(toSun, toSun);
}

/** Unit vector from the Moon's centre toward the Earth, body-fixed (used for checks). */
export function earthDirectionMoonFixed(time: JulianDate, result = new Cartesian3()): Cartesian3 {
  Simon1994PlanetaryPositions.computeMoonPositionInEarthInertialFrame(time, moonInertial);
  const toEarth = Cartesian3.negate(moonInertial, result);
  Matrix3.multiplyByVector(icrfToMoonFixed(time, m3), toEarth, toEarth);
  return Cartesian3.normalize(toEarth, toEarth);
}

/** Sub-solar point on Earth (degrees), via Cesium's TEME pseudo-fixed frame (arc-minute accuracy). */
export function subsolarPointEarth(time: JulianDate): { lat: number; lon: number } {
  const sun = Simon1994PlanetaryPositions.computeSunPositionInEarthInertialFrame(time, new Cartesian3());
  const m = Transforms.computeTemeToPseudoFixedMatrix(time, new Matrix3());
  const v = Cartesian3.normalize(Matrix3.multiplyByVector(m, sun, sun), sun);
  return { lat: CesiumMath.toDegrees(Math.asin(v.z)), lon: CesiumMath.toDegrees(Math.atan2(v.y, v.x)) };
}
