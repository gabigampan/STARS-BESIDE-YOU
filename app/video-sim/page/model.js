// Pure formulas shared by the scene and the data panel. Every number shown on screen is either a
// scenario value (copied from the project's tables or an official constant) or the output of one of
// these functions. No randomness, no wall clock: everything is a function of the video time t (s).

export const D2R = Math.PI / 180;

// Sun direction in the site's local frame (east, north, up), Sun centre, no refraction.
// Same formula as the tables (provenance_moon.csv, irradiance / sun_low_frac):
//   sin h = sin(lat) sin(d) + cos(lat) cos(d) cos(H)
export function sunENU(latDeg, declDeg, hourAngleDeg) {
  const p = latDeg * D2R, d = declDeg * D2R, H = hourAngleDeg * D2R;
  const E = -Math.cos(d) * Math.sin(H);
  const N = Math.cos(p) * Math.sin(d) - Math.sin(p) * Math.cos(d) * Math.cos(H);
  const U = Math.sin(p) * Math.sin(d) + Math.cos(p) * Math.cos(d) * Math.cos(H);
  const elev = Math.asin(Math.max(-1, Math.min(1, U))) / D2R;
  let az = Math.atan2(E, N) / D2R; if (az < 0) az += 360;
  return { E, N, U, elev, az };
}

export function hourAngleAt(sc, t) {
  const s = sc.sun, f = Math.min(1, Math.max(0, t / s.sim_end_s));
  return s.hour_angle_start_deg + (s.hour_angle_end_deg - s.hour_angle_start_deg) * f;
}

// Simulated time elapsed (Earth days) at video time t, and the time compression factor.
export function simDays(sc, t) {
  const s = sc.sun, f = Math.min(1, Math.max(0, t / s.sim_end_s));
  return (s.hour_angle_end_deg - s.hour_angle_start_deg) / 360 * sc.constants.synodic_period_days.value * f;
}
export function compression(sc) {
  const s = sc.sun;
  return (s.hour_angle_end_deg - s.hour_angle_start_deg) / 360 * sc.constants.synodic_period_days.value * 86400 / s.sim_end_s;
}

// Terrain horizon (deg) at azimuth az from a profile sampled every stepDeg.
export function horizonAt(profile, stepDeg, az) {
  const n = profile.length, x = ((az % 360) + 360) % 360 / stepDeg;
  const i0 = Math.floor(x) % n, i1 = (i0 + 1) % n, f = x - Math.floor(x);
  return profile[i0] * (1 - f) + profile[i1] * f;
}

// Fraction of the solar disc (angular diameter 0.533 deg) above the horizon, linear approximation.
export const SUN_DIAM_DEG = 0.533;
export function discVisible(sunElev, horizon) {
  return Math.min(1, Math.max(0, (sunElev - horizon) / SUN_DIAM_DEG + 0.5));
}

// Solar mission: power per m2 of panel, vertical panel (tilt 90 deg) turned to the Sun's azimuth.
//   incidence i = angle between the panel normal and the Sun = Sun elevation (perfect azimuth tracking)
//   P = S0 * cos(i) * visible disc fraction (0 when the real terrain blocks the Sun)
export function panelPower(S0, tiltDeg, sunElev, visible) {
  // normal of a panel tilted by tiltDeg from horizontal, facing the Sun azimuth: elevation 90 - tilt
  const nElev = 90 - tiltDeg;
  const inc = Math.abs(sunElev - nElev);
  const cosI = Math.max(0, Math.cos(inc * D2R));
  return { P: sunElev > -SUN_DIAM_DEG ? S0 * cosI * visible : 0, inc };
}

// Lunar base: temperature shape model between the measured Tmin and Tmax (stated in the scenario).
export function buildTemperatureCurve(sc, n = 4000) {
  const tau = sc.temperature_model.tau_days;
  const lat = sc.site.lat_deg, decl = sc.sun.declination_deg;
  const P = sc.constants.synodic_period_days.value;
  // two full cycles from H = -180, keep the second (periodic steady state)
  const g = new Float64Array(2 * n);
  let gSet = 0, tSet = 0, up = false;
  for (let k = 0; k < 2 * n; k++) {
    const H = -180 + 360 * (k / n);
    const tDays = P * k / n;
    const h = sunENU(lat, decl, H).elev;
    if (h > 0) { g[k] = Math.pow(Math.sin(h * D2R), 0.25); up = true; }
    else { if (up) { gSet = g[k - 1]; tSet = tDays; up = false; } g[k] = gSet * Math.exp(-(tDays - tSet) / tau); }
  }
  const second = g.slice(n);
  let lo = Infinity, hi = -Infinity; for (const v of second) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  const tmin = sc.table_values.moon.tmin_k.value, tmax = sc.table_values.moon.tmax_k.value;
  return function T(H) {
    const x = (((H + 180) % 360) + 360) % 360 / 360 * n;
    const i0 = Math.floor(x) % n, i1 = (i0 + 1) % n, f = x - Math.floor(x);
    const v = second[i0] * (1 - f) + second[i1] * f;
    return tmin + (tmax - tmin) * (v - lo) / (hi - lo);
  };
}

export function smooth(x) { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); }
export function phase(t, t0, t1) { return smooth((t - t0) / (t1 - t0)); }

// Deterministic hash noise for star positions.
export function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let x = s; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
}
