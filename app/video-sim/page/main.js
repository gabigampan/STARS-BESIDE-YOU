import * as THREE from 'three';
import * as M from './model.js';

const D2R = Math.PI / 180;
const qs = new URLSearchParams(location.search);
const SC = await (await fetch('/scenario.json')).json();
const TR = await (await fetch('/work/terrain.json')).json();
const bin = async (p, T) => new T(await (await fetch(p)).arrayBuffer());
const nearZ = await bin('/work/near_z.f32', Float32Array);
const farZ = await bin('/work/far_z.f32', Float32Array);
const nearHz = await bin('/work/near_hz.i16', Int16Array);
const farHz = await bin('/work/far_hz.i16', Int16Array);
const isSolar = SC.name === 'solar';
const W = SC.width, H = SC.height;
const S0 = SC.constants.solar_constant_W_m2.value;
const SUN_I = SC.render?.sun_intensity ?? 7.0;
const SIM_END = SC.sun.sim_end_s, CARD0 = SC.duration_s - SC.card_s;

// ------------------------------------------------------------------ renderer
const canvas = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: qs.get('aa') !== '0', preserveDrawingBuffer: true, logarithmicDepthBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.setClearColor(0x000000, 1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(SC.camera.fov_deg, W / H, 0.3, 700000);

// world frame: x = east, y = up, z = south (north = -z)
const dirFromAzEl = (az, el) => new THREE.Vector3(Math.sin(az * D2R) * Math.cos(el * D2R), Math.sin(el * D2R), -Math.cos(az * D2R) * Math.cos(el * D2R));

// ------------------------------------------------------------------ terrain
function gridSample(z, n, step, half, e, nn) {
  const c = (e + half) / step, r = (nn + half) / step;
  const c0 = Math.max(0, Math.min(n - 2, Math.floor(c))), r0 = Math.max(0, Math.min(n - 2, Math.floor(r)));
  const fc = Math.min(1, Math.max(0, c - c0)), fr = Math.min(1, Math.max(0, r - r0));
  const i = r0 * n + c0;
  return z[i] * (1 - fr) * (1 - fc) + z[i + n] * fr * (1 - fc) + z[i + 1] * (1 - fr) * fc + z[i + n + 1] * fr * fc;
}
const NEAR = TR.near, FAR = TR.far;
function groundAt(e, n) {
  if (Math.abs(e) < NEAR.half - NEAR.step && Math.abs(n) < NEAR.half - NEAR.step) return gridSample(nearZ, NEAR.n, NEAR.step, NEAR.half, e, n);
  return gridSample(farZ, FAR.n, FAR.step, FAR.half, e, n);
}

const sunU = { sunElev: { value: 0 } };
const camU = { microFade: { value: 1 } };

function terrainGeometry(z, n, step, half, holeHalf) {
  const pos = new Float32Array(n * n * 3), uv = new Float32Array(n * n * 2);
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    const i = r * n + c, e = -half + c * step, nn = -half + r * step;
    let y = z[i];
    if (holeHalf && Math.abs(e) < holeHalf && Math.abs(nn) < holeHalf) y -= 60; // hidden under the near patch
    pos[3 * i] = e; pos[3 * i + 1] = y; pos[3 * i + 2] = -nn;
    uv[2 * i] = (c + 0.5) / n; uv[2 * i + 1] = (r + 0.5) / n;
  }
  const idx = new Uint32Array((n - 1) * (n - 1) * 6); let k = 0;
  for (let r = 0; r < n - 1; r++) for (let c = 0; c < n - 1; c++) {
    const a = r * n + c, b = a + 1, d = a + n, e2 = d + 1;
    idx[k++] = a; idx[k++] = b; idx[k++] = d; idx[k++] = b; idx[k++] = e2; idx[k++] = d;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('hzuv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  g.computeVertexNormals();
  return g;
}

function hzTexture(n) {
  const data = new Uint16Array(n * n);
  const tex = new THREE.DataTexture(data, n, n, THREE.RedFormat, THREE.HalfFloatType);
  tex.minFilter = THREE.LinearFilter; tex.magFilter = THREE.LinearFilter; tex.needsUpdate = true;
  return tex;
}
function updateHz(tex, slices, nPts, nAz, az) {
  const x = az / (360 / nAz), i0 = Math.floor(x) % nAz, i1 = (i0 + 1) % nAz, f = x - Math.floor(x);
  const o0 = i0 * nPts, o1 = i1 * nPts, d = tex.image.data;
  for (let i = 0; i < nPts; i++) d[i] = THREE.DataUtils.toHalfFloat((slices[o0 + i] * (1 - f) + slices[o1 + i] * f) * 0.01);
  tex.needsUpdate = true;
}

// The terrain-shadow / disc-visibility factor multiplies only the Sun (directional light 0, the only
// shadow-casting light, which three.js sorts first); the earthshine light is not affected.
const LFB = THREE.ShaderChunk.lights_fragment_begin.replace('getDirectionalLightInfo( directionalLight, directLight );',
  'getDirectionalLightInfo( directionalLight, directLight );\n\t\tif ( UNROLLED_LOOP_INDEX == 0 ) directLight.color *= sunLitF;');
if (LFB === THREE.ShaderChunk.lights_fragment_begin) throw new Error('light chunk patch failed');
const NOISE_GLSL = `
float h21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.0-2.0*f);
  return mix(mix(h21(i),h21(i+vec2(1,0)),u.x), mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),u.x), u.y); }
float fbm(vec2 p){ float a=0.5, s=0.0; for(int k=0;k<4;k++){ s+=a*vnoise(p); p*=2.03; a*=0.5; } return s; }
vec2 h22(vec2 p){ return vec2(h21(p), h21(p + vec2(19.19, 7.73))); }
// procedural small-crater micro-relief (shading only, no geometry): one crater per cell of size S
float craterH(vec2 p, float S){
  vec2 c = floor(p / S), f = p / S - c; vec2 rr = h22(c);
  if (rr.y < 0.62) return 0.0;
  float r = mix(0.08, 0.30, rr.x * rr.x * rr.x);
  vec2 ctr = 0.5 + (h22(c + 31.7) - 0.5) * (1.0 - 2.9 * r);
  float d = length(f - ctr) / r;
  float h = d < 1.0 ? -pow(1.0 - d * d, 1.3) * 0.75 + 0.12 * smoothstep(0.6, 1.0, d) : 0.12 * (1.0 - smoothstep(1.0, 1.6, d));
  return h * r * S * 0.30;
}
float microH(vec2 p, float fadeSmall){
  return craterH(p, 23.0) + craterH(p + 7.3, 9.0) * fadeSmall + craterH(p + 3.1, 3.7) * fadeSmall + (fbm(p * 0.09) + fbm(p * 0.37) * 0.25) * 0.6;
}
`;

function terrainMaterial(tex, micro) {
  const m = new THREE.MeshLambertMaterial({ color: new THREE.Color(0.60, 0.592, 0.578) });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.hzTex = { value: tex }; sh.uniforms.sunElev = sunU.sunElev; sh.uniforms.microFade = camU.microFade;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec2 hzuv; varying vec2 vHz; varying vec3 vW;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvHz = hzuv; vW = (modelMatrix * vec4(position, 1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform sampler2D hzTex; uniform float sunElev; uniform float microFade; varying vec2 vHz; varying vec3 vW;\n' + NOISE_GLSL)
      .replace('#include <color_fragment>', `#include <color_fragment>
        float dist = length(vW - cameraPosition);
        float alb = fbm(vW.xz * 0.013) - 0.5;
        diffuseColor.rgb *= 1.0 + 0.10 * alb;`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        ${micro ? `
        float fade = microFade * clamp(1.0 - dist / 320.0, 0.0, 1.0);
        if (fade > 0.0) {
          vec2 p = vW.xz; float e = 0.06;
          float fs = clamp(1.0 - dist / 140.0, 0.0, 1.0);
          float n0 = microH(p, fs), nx = microH(p + vec2(e, 0.0), fs), nz = microH(p + vec2(0.0, e), fs);
          vec3 gw = vec3(-(nx - n0) / e, 0.0, -(nz - n0) / e) * fade;
          normal = normalize(normal + (viewMatrix * vec4(gw, 0.0)).xyz);
        }` : ''}`)
      .replace('#include <lights_fragment_begin>', `float hz = texture2D(hzTex, vHz).r;
        float sunLitF = clamp((sunElev - hz) / 0.533 + 0.5, 0.0, 1.0);
        ` + LFB);
  };
  return m;
}

const nearTex = hzTexture(NEAR.n), farTex = hzTexture(FAR.n);
const nearMesh = new THREE.Mesh(terrainGeometry(nearZ, NEAR.n, NEAR.step, NEAR.half, 0), terrainMaterial(nearTex, true));
nearMesh.receiveShadow = true;
const farMesh = new THREE.Mesh(terrainGeometry(farZ, FAR.n, FAR.step, FAR.half, NEAR.half - FAR.step * 1.5), terrainMaterial(farTex, false));
scene.add(nearMesh, farMesh);

// ------------------------------------------------------------------ sky
const SKY_R = 400000;
{
  const rnd = M.rng(20261115), n = 2600, p = new Float32Array(n * 3), col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const u = rnd() * 2 - 1, th = rnd() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    p[3 * i] = SKY_R * s * Math.cos(th); p[3 * i + 1] = SKY_R * u; p[3 * i + 2] = SKY_R * s * Math.sin(th);
    const b = 0.10 + 0.45 * Math.pow(rnd(), 3.0);
    col[3 * i] = b; col[3 * i + 1] = b; col[3 * i + 2] = b * 1.04;
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const stars = new THREE.Points(g, new THREE.PointsMaterial({ size: 2.0, sizeAttenuation: false, vertexColors: true, toneMapped: false, depthWrite: false }));
  stars.renderOrder = -2; scene.add(stars); window.__stars = stars;
}
const sunDisc = new THREE.Mesh(new THREE.CircleGeometry(SKY_R * 0.9 * Math.tan(M.SUN_DIAM_DEG / 2 * D2R), 48), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }));
scene.add(sunDisc);
let earth = null;
if (TR.earth && TR.earth.draw) {
  const r = SKY_R * 0.8 * Math.tan(0.95 * D2R);
  // lit by the Sun's direction whatever the local time (the Sun always shines on the Earth's day side)
  earth = new THREE.Mesh(new THREE.SphereGeometry(r, 64, 32), new THREE.ShaderMaterial({
    uniforms: { sunDirW: { value: new THREE.Vector3(0, 1, 0) } },
    vertexShader: 'varying vec3 vN; void main(){ vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform vec3 sunDirW; varying vec3 vN; void main(){ float l = max(dot(normalize(vN), sunDirW), 0.0); gl_FragColor = vec4(vec3(0.62, 0.68, 0.76) * (0.03 + 0.97 * l), 1.0); }' }));
  scene.add(earth);
}

// ------------------------------------------------------------------ lights
const sun = new THREE.DirectionalLight(0xffffff, SUN_I);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
const sc = sun.shadow.camera; sc.left = -170; sc.right = 170; sc.top = 170; sc.bottom = -170; sc.near = 10; sc.far = 3000;
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.05;
scene.add(sun, sun.target);
scene.add(new THREE.AmbientLight(0xffffff, 0.035));
// earthshine: light from the Earth's direction, scaled by the Earth's lit fraction; shown only at night with a raised exposure (labelled)
const earthLight = new THREE.DirectionalLight(0xdfe6f0, 0); scene.add(earthLight, earthLight.target);
const EARTH_BOOST = SC.render?.earthshine_display_fraction ?? 0.10; // stated assumption: faint fill standing in for light reflected by surrounding regolith

// ------------------------------------------------------------------ objects
const objLit = { value: 1 };
function objMat(opts) {
  const m = new THREE.MeshStandardMaterial(opts);
  m.onBeforeCompile = (sh) => {
    sh.uniforms.objLit = objLit;
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float objLit;')
      .replace('#include <lights_fragment_begin>', 'float sunLitF = objLit;\n' + LFB);
  };
  return m;
}
const shadowAll = (o) => o.traverse((c) => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } });
const g0 = groundAt(0, 0);
const root = new THREE.Group(); root.position.set(0, g0, 0); scene.add(root);

let solar = null, base = null;
if (isSolar) {
  const A = SC.array;
  const grey = objMat({ color: 0x6c6f74, roughness: 0.6, metalness: 0.3 });
  const alu = objMat({ color: 0xb9bcc0, roughness: 0.45, metalness: 0.6 });
  const cells = objMat({ color: 0x1b2230, roughness: 0.32, metalness: 0.15 });
  const back = objMat({ color: 0xc9c7c1, roughness: 0.8, metalness: 0.0 });
  const foot = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.55, 1.8), grey); foot.position.y = 0.2; root.add(foot);
  for (const [x, z] of [[1.1, 1.1], [-1.1, 1.1], [1.1, -1.1], [-1.1, -1.1]]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.08, 0.9, 8), alu); leg.position.set(x, 0.1, z); leg.rotation.set(z * 0.25, 0, -x * 0.25); root.add(leg);
  }
  const mastLower = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 2.0, 16), alu); mastLower.position.y = 1.4; root.add(mastLower);
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 1, 16), alu); root.add(mast);
  const head = new THREE.Group(); root.add(head);
  const hub = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.35), grey); head.add(hub);
  const FLAT = A.final_tilt_deg === 0;   // flat (horizontal) array: the head is turned so the wings unfold upwards and end lying flat
  if (!FLAT) { const tip = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.2, 6), alu); tip.position.y = 0.85; head.add(tip); }
  const panelGeo = new THREE.BoxGeometry(A.panel_w_m, A.panel_h_m, 0.045);
  // vertical array: -z face (index 5) is the cell side, facing the Sun; flat array: +z face (index 4), which ends facing up
  const panelMats = FLAT ? [alu, alu, alu, alu, cells, back] : [alu, alu, alu, alu, back, cells];
  if (FLAT) head.rotation.set(-Math.PI / 2, 0, 0);
  const wings = [];
  for (const side of [1, -1]) {
    const wroot = new THREE.Group(); wroot.scale.x = side; head.add(wroot);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.08, 0.08), alu); arm.position.x = 0.4; wroot.add(arm);
    let parent = wroot, x0 = 0.6; const hinges = [];
    for (let k = 0; k < A.panels_per_wing; k++) {
      const h = new THREE.Group(); h.position.x = x0; parent.add(h);
      const p = new THREE.Mesh(panelGeo, panelMats); p.position.x = A.panel_w_m / 2; h.add(p);
      // thin frame lines between cells for an engineering look
      for (let j = 1; j < 4; j++) { const bar = new THREE.Mesh(new THREE.BoxGeometry(0.02, A.panel_h_m, 0.05), alu); bar.position.x = j * A.panel_w_m / 4; h.add(bar); }
      hinges.push(h); parent = h; x0 = A.panel_w_m + 0.04;
    }
    wings.push(hinges);
  }
  shadowAll(root);
  solar = { mast, head, wings, FLAT };
} else {
  const HB = SC.habitat;
  const white = objMat({ color: 0xd2cec6, roughness: 0.7, metalness: 0.05 });
  const metal = objMat({ color: 0x8d9096, roughness: 0.5, metalness: 0.5 });
  const fabric = objMat({ color: 0xe0dbd0, roughness: 0.95, metalness: 0.0 });
  const reg = objMat({ color: new THREE.Color(0.47, 0.465, 0.455), roughness: 1.0, metalness: 0.0 });
  const module = new THREE.Group(); root.add(module);
  const cyl = new THREE.Mesh(new THREE.CylinderGeometry(HB.module_d_m / 2, HB.module_d_m / 2, HB.module_l_m, 48), white); cyl.rotation.z = Math.PI / 2; module.add(cyl);
  for (const s of [-1, 1]) {
    const cap = new THREE.Mesh(new THREE.SphereGeometry(HB.module_d_m / 2, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), white);
    cap.scale.y = 0.25; cap.rotation.z = -s * Math.PI / 2; cap.position.x = s * HB.module_l_m / 2; module.add(cap);
  }
  for (let j = -2; j <= 2; j++) { const rib = new THREE.Mesh(new THREE.TorusGeometry(HB.module_d_m / 2 + 0.02, 0.05, 6, 48), metal); rib.rotation.y = Math.PI / 2; rib.position.x = j * HB.module_l_m / 5; module.add(rib); }
  for (const [x, z] of [[-2.8, 1.4], [2.8, 1.4], [-2.8, -1.4], [2.8, -1.4]]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 1.6, 8), metal); leg.position.set(x, -HB.module_d_m / 2 - 0.4, z); module.add(leg);
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.06, 16), metal); pad.position.set(x, -HB.module_d_m / 2 - 1.2, z); module.add(pad);
  }
  const hatch = new THREE.Mesh(new THREE.BoxGeometry(0.2, 1.6, 1.0), metal); hatch.position.set(-HB.module_l_m / 2 - 0.5, -0.2, 0); module.add(hatch);
  const infl = new THREE.Group(); module.add(infl);
  const inflM = new THREE.Mesh(new THREE.CapsuleGeometry(HB.inflatable_d_m / 2, HB.inflatable_l_m - HB.inflatable_d_m * 0.5, 12, 48), fabric);
  inflM.rotation.z = Math.PI / 2; infl.add(inflM);
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(1.3, 1.3, 0.7, 32), metal); collar.rotation.z = Math.PI / 2; collar.position.x = HB.module_l_m / 2 + 0.6; module.add(collar);
  // regolith berm following the real ground
  const segA = 160, segP = 7, prof = [[0, 0], [0.12, 0.55], [0.3, 0.92], [0.5, 1.0], [0.7, 0.92], [0.88, 0.55], [1, 0]];
  const bp = new Float32Array(segA * segP * 3), groundY = new Float32Array(segA * segP), ph = new Float32Array(segA * segP), angF = new Float32Array(segA * segP);
  const cx = HB.module_l_m * 0.25;
  for (let a = 0; a < segA; a++) for (let j = 0; j < segP; j++) {
    const ang = (a / (segA - 1)) * (Math.PI * 2 - 0.55) + 0.275 + Math.PI, rr = HB.berm_r_m + prof[j][0] * HB.berm_w_m;
    const x = cx + rr * Math.cos(ang), z = rr * Math.sin(ang), i = a * segP + j;
    bp[3 * i] = x; bp[3 * i + 2] = z; groundY[i] = groundAt(x, -z) - g0 - 0.15; ph[i] = prof[j][1] * HB.berm_h_m; angF[i] = a / (segA - 1);
    bp[3 * i + 1] = groundY[i];
  }
  const bidx = []; for (let a = 0; a < segA - 1; a++) for (let j = 0; j < segP - 1; j++) { const i = a * segP + j; bidx.push(i, i + 1, i + segP, i + 1, i + segP + 1, i + segP); }
  const bg = new THREE.BufferGeometry(); bg.setAttribute('position', new THREE.BufferAttribute(bp, 3)); bg.setIndex(bidx); bg.computeVertexNormals();
  const berm = new THREE.Mesh(bg, reg); root.add(berm);
  shadowAll(root);
  // highest ground under the module footprint, so the legs stand on the real surface
  let gmax = -1e9; for (let x = -4; x <= 9; x += 1) for (let z = -3; z <= 3; z += 1) gmax = Math.max(gmax, groundAt(x, -z) - g0);
  base = { module, infl, berm, bg, groundY, ph, angF, gmax };
}

// ------------------------------------------------------------------ camera path
function camAt(t) {
  const K = SC.camera.keys;
  if (t <= K[0].t) return K[0]; if (t >= K[K.length - 1].t) return K[K.length - 1];
  let i = 0; while (K[i + 1].t < t) i++;
  const u = (t - K[i].t) / (K[i + 1].t - K[i].t);
  const get = (j, key) => key === 'dist' ? Math.log(K[Math.max(0, Math.min(K.length - 1, j))][key]) : K[Math.max(0, Math.min(K.length - 1, j))][key];
  const out = {};
  for (const key of ['dist', 'elev_deg', 'az_deg', 'target_z']) {
    const p0 = get(i - 1, key), p1 = get(i, key), p2 = get(i + 1, key), p3 = get(i + 2, key);
    const m1 = i === 0 ? 0 : (p2 - p0) / 2 * ((K[i + 1].t - K[i].t) / (K[i + 1].t - K[i - 1].t)) * 2;
    const m2 = i + 2 >= K.length ? 0 : (p3 - p1) / 2 * ((K[i + 1].t - K[i].t) / (K[i + 2].t - K[i].t)) * 2;
    const u2 = u * u, u3 = u2 * u;
    out[key] = (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2;
  }
  out.dist = Math.exp(out.dist);
  return out;
}

// ------------------------------------------------------------------ precomputed time series (solar power, energy)
const objProfile = TR.obj_hz;
function sunAt(t) {
  const Hh = M.hourAngleAt(SC, t);
  const s = M.sunENU(SC.site.lat_deg, SC.sun.declination_deg, Hh);
  const hz = M.horizonAt(objProfile, TR.obj_hz_step_deg, s.az);
  return { Hh, ...s, hz, vis: M.discVisible(s.elev, hz) };
}
const series = [];
if (isSolar) {
  const A = SC.array, dt = 1 / SC.fps / 4;
  let E = 0, prevP = 0;
  for (let k = 0; k * dt <= SIM_END + 1e-9; k++) {
    const t = k * dt, s = sunAt(t);
    const deployed = t >= A.deploy_end_s;
    const P = M.panelPower(S0, A.final_tilt_deg, s.elev, s.vis).P;   // per m2 of a Sun-facing vertical panel at hub height
    if (k > 0 && deployed && t - dt >= A.deploy_end_s - 1e-9) E += 0.5 * (P + prevP) * (M.simDays(SC, t) - M.simDays(SC, t - dt)) * 24 / 1000; // kWh/m2, from the end of deployment
    prevP = P;
    series.push({ t, P, E, days: M.simDays(SC, t) });
  }
}
const seriesAt = (t) => series[Math.max(0, Math.min(series.length - 1, Math.round(t * SC.fps * 4)))];
const Tcurve = isSolar ? null : M.buildTemperatureCurve(SC, (Hh) => {
  const s = M.sunENU(SC.site.lat_deg, SC.sun.declination_deg, Hh);
  return M.discVisible(s.elev, M.horizonAt(objProfile, TR.obj_hz_step_deg, s.az));
});

// ------------------------------------------------------------------ overlay
const panel = document.getElementById('panel');
const foot = document.getElementById('foot');
const card = document.getElementById('card');
const f1 = (x, d = 1) => (Math.abs(x) < 0.5 * Math.pow(10, -d) ? 0 : x).toFixed(d);
const thou = (x) => Math.round(x).toLocaleString('en-US');
const COMP = M.compression(SC);
const compStr = '×' + thou(Number(COMP.toPrecision(3)));
const prodShort = (p) => p.split(' (')[0].replace('LOLA ', '');

foot.innerHTML = `3D simulation driven by table data. Not real footage. &nbsp;·&nbsp; Terrain: real ${SC.render?.relief_credit ?? 'LOLA'} relief, ${prodShort(NEAR.product)} at ${f1(NEAR.step, 1)} m/px (±${f1(NEAR.half / 1000, 0)} km), ` +
  `far field ${prodShort(FAR.product)} meshed at ${f1(FAR.step, 0)} m/px; fine surface texture is procedural. ` +
  (isSolar ? 'Array size and timing: illustrative.' : 'Habitat shapes, sizes and timing: illustrative.');

const graph = document.createElement('canvas'); graph.width = 548; graph.height = 128;
function row(l, v) { return `<div class="row"><span class="l">${l}</span><span class="v">${v}</span></div>`; }

// Flat array: x axis = one whole lunar cycle (synodic period) from sunrise; the night half is shaded.
const CYC = SC.constants.synodic_period_days.value;
const H_RISE = -Math.acos(-Math.tan(SC.site.lat_deg * D2R) * Math.tan(SC.sun.declination_deg * D2R)) / D2R;
const dayFromRise = (Hh) => (Hh - H_RISE) / 360 * CYC;
function drawCycleGraph(t) {
  const g = graph.getContext('2d'), w = graph.width, h = graph.height, pl = 8, pr = 8, pt = 8, pb = 22;
  const X = (d) => pl + (w - pl - pr) * d / CYC, Y = (P) => pt + (h - pt - pb) * (1 - P / 1400);
  g.clearRect(0, 0, w, h);
  g.fillStyle = 'rgba(255,255,255,0.04)'; g.fillRect(0, 0, w, h);
  const dSet = dayFromRise(-H_RISE);
  g.fillStyle = 'rgba(120,130,160,0.22)'; g.fillRect(X(dSet), pt, X(CYC) - X(dSet), h - pt - pb);
  g.strokeStyle = 'rgba(255,255,255,0.14)'; g.lineWidth = 1;
  for (const v of [0, 700, 1400]) { const y = Y(v); g.beginPath(); g.moveTo(pl, y + 0.5); g.lineTo(w - pr, y + 0.5); g.stroke(); }
  // model curve over the whole daytime (dashed), then the part already shown (solid)
  g.setLineDash([5, 5]); g.strokeStyle = 'rgba(242,163,58,0.45)'; g.lineWidth = 1.5; g.beginPath();
  for (let k = 0; k <= 200; k++) { const Hh = H_RISE + (-2 * H_RISE) * k / 200; const e = M.sunENU(SC.site.lat_deg, SC.sun.declination_deg, Hh).elev; const P = S0 * Math.max(0, Math.sin(e * D2R)); const x = X(dayFromRise(Hh)), y = Y(P); if (k === 0) g.moveTo(x, y); else g.lineTo(x, y); }
  g.stroke(); g.setLineDash([]);
  g.strokeStyle = '#f2a33a'; g.lineWidth = 2.5; g.beginPath();
  const kmax = Math.round(Math.min(t, SIM_END) * SC.fps * 4);
  for (let k = 0; k <= kmax; k += 2) { const s = series[k]; const x = X(dayFromRise(M.hourAngleAt(SC, s.t))), y = Y(s.P); if (k === 0) g.moveTo(x, y); else g.lineTo(x, y); }
  g.stroke();
  g.fillStyle = 'rgba(255,255,255,0.62)'; g.font = '17px sans-serif';
  g.fillText(`day ${f1(dSet)} d`, X(0) + 2, h - 5); g.fillText(`night ${f1(CYC - dSet)} d (no sunlight)`, X(dSet) + 6, h - 5);
}
function drawGraph(t) {
  if (solar && solar.FLAT) return drawCycleGraph(t);
  const g = graph.getContext('2d'), w = graph.width, h = graph.height, pl = 8, pr = 8, pt = 8, pb = 8;
  g.clearRect(0, 0, w, h);
  g.fillStyle = 'rgba(255,255,255,0.04)'; g.fillRect(0, 0, w, h);
  g.strokeStyle = 'rgba(255,255,255,0.14)'; g.lineWidth = 1;
  for (const v of [0, 700, 1400]) { const y = pt + (h - pt - pb) * (1 - v / 1400); g.beginPath(); g.moveTo(pl, y + 0.5); g.lineTo(w - pr, y + 0.5); g.stroke(); }
  const Dtot = M.simDays(SC, SIM_END);
  g.strokeStyle = '#f2a33a'; g.lineWidth = 2.5; g.beginPath();
  const kmax = Math.round(Math.min(t, SIM_END) * SC.fps * 4);
  for (let k = 0; k <= kmax; k += 2) {
    const s = series[k]; const x = pl + (w - pl - pr) * s.days / Dtot, y = pt + (h - pt - pb) * (1 - s.P / 1400);
    if (k === 0) g.moveTo(x, y); else g.lineTo(x, y);
  }
  g.stroke();
}

const inset = document.getElementById('inset');
let insetImg = null;
if (!isSolar) {
  inset.style.display = 'block';
  insetImg = new Image(); insetImg.src = '/work/hillshade_near.png'; await insetImg.decode();
  const tm = SC.table_values.moon;
  document.getElementById('insetScale').innerHTML = `<div style="display:flex;justify-content:space-between"><span>${tm.tmin_k.value} K</span><span>${tm.tmax_k.value} K</span></div>` +
    `<canvas id="bar" width="304" height="14" style="width:304px;height:14px;margin:4px 0 0"></canvas><div style="font-size:22px">${f1(NEAR.half * 2 / 1000, 0)} km patch, uniform</div>`;
}
const cold = [62, 92, 140], warm = [176, 160, 136];
const tint = (u) => cold.map((c, i) => Math.round(c + (warm[i] - c) * u));
function drawInset(T) {
  const tm = SC.table_values.moon, u = (T - tm.tmin_k.value) / (tm.tmax_k.value - tm.tmin_k.value);
  const c = document.getElementById('insetCanvas').getContext('2d');
  c.globalCompositeOperation = 'source-over'; c.drawImage(insetImg, 0, 0, 304, 304);
  c.globalCompositeOperation = 'multiply'; const [r, g, b] = tint(u); c.fillStyle = `rgb(${r},${g},${b})`; c.fillRect(0, 0, 304, 304);
  c.globalCompositeOperation = 'source-over';
  const bar = document.getElementById('bar').getContext('2d');
  for (let x = 0; x < 304; x++) { const [r2, g2, b2] = tint(x / 303); bar.fillStyle = `rgb(${r2},${g2},${b2})`; bar.fillRect(x, 0, 1, 14); }
  bar.fillStyle = '#fff'; bar.fillRect(Math.round(u * 300), 0, 4, 14);
}

// Pair card (Lunar base): every number comes from the scenario's pair_values block, which
// prepare.py checks against the shipped bundle (explain.json) before anything is rendered.
function buildPairCard() {
  const C = SC.card, PV = SC.pair_values;
  const lv = (x) => ({ MEASURED: 'measured', DERIVED: 'derived', MODELLED: 'modelled' }[x] || x);
  const fx = (x, d) => Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const val = (x, r) => `${fx(x, r.dec)}${r.unit === '°' ? '°' : ' ' + r.unit}`;
  const rowsH = C.rows.map((r) => {
    const v = r.info ? PV.not_part_of_similarity[r.var] : PV.variables[r.var];
    const side = (b) => {
      const x = v[b], s = r[b];
      const c = r.celsius ? ` <span class="c">(${fx(x - 273.15, 2)} °C)</span>` : '';
      const p = r.pct ? `<div class="pct">percentile ${fx(v[b + '_pct'], 2)}</div>` : '';
      return `<td class="num">${val(x, r)}${c}<div class="lv">${lv(s.level)}${s.note ? ', ' + s.note : ''}</div>${p}</td>`;
    };
    const d = `<td class="num">${val(v.diff ?? v.difference, r)}${r.pct ? `<div class="pct">${fx(v.diff_pct, 2)} percentile points</div>` : ''}</td>`;
    return `<tr><td class="var">${r.label}${r.sub ? `<div class="lv">${r.sub}</div>` : ''}</td>${side('earth')}${side('moon')}${d}</tr>`;
  }).join('');
  document.getElementById('card').classList.add('pair');
  const es = SC.earth_site, ms = SC.site;
  const ll =(lat, lon) => `${Math.abs(lat)}° ${lat < 0 ? 'S' : 'N'} ${Math.abs(lon)}° ${lon < 0 ? 'W' : 'E'}`;
  document.getElementById('cardInner').innerHTML = `<h1>${C.title}</h1><div class="sub">${C.subtitle}</div>` +
    `<table class="pair"><tr><th>Variable</th><th>Earth: ${es.name}<div class="lv">cell ${es.cell_id}, ${ll(es.lat_deg, es.lon_deg)}; ${es.nearest_place_km} km from ${es.nearest_place}</div></th>` +
    `<th>Moon: ${ms.card_name}<div class="lv">cell ${ms.cell_id}, ${ms.label}; ${ms.place_ref.distance_km} km from ${ms.place_ref.feature}</div></th><th>Real difference</th></tr>${rowsH}</table>` +
    `<div class="sentence">${PV.pair_sentence}</div><div class="legend">${C.legend}</div>`;
}

// Pair card (Solar panels): every number comes from scenario.pair_values, checked by prepare.py
// against explain.json (solar rank 1), similarity.json and missions.json before anything is rendered.
function buildSolarPairCard() {
  const C = SC.card, PV = SC.pair_values;
  const lv = (x) => ({ MEASURED: 'measured', DERIVED: 'derived', MODELLED: 'modelled' }[x] || x);
  const L = PV.levels;
  const unitS = (u) => (u === '°' ? '°' : ' ' + u);
  const rowsH = C.rows.map((r) => {
    if (r.kind === 'atmosphere') {
      const a = PV.atmosphere;
      return `<tr class="hl"><td class="var">${r.label}${r.sub ? `<div class="lv">${r.sub}</div>` : ''}</td>` +
        `<td class="num">${a.ground_kwh_m2_day} ${r.unit}<div class="lv">${lv(L[r.var].earth)}, ${r.earth_note}</div></td>` +
        `<td class="num">${PV.variables[r.moon_from].moon} ${r.unit}<div class="lv">${lv(L[r.moon_from].moon)}, ${r.moon_note}</div></td>` +
        `<td class="num">${a.loss_pct_display} % lost<div class="lv">${a.ground_display} of ${a.toa_display} ${r.unit} reach the ground</div></td></tr>`;
    }
    const v = r.info ? PV.not_part_of_similarity[r.var] : PV.variables[r.var];
    const side = (b) => `<td class="num">${v[b]}${unitS(r.unit)}<div class="lv">${lv(L[r.var][b])}${r[b + '_note'] ? ', ' + r[b + '_note'] : ''}</div></td>`;
    return `<tr><td class="var">${r.label}${r.sub ? `<div class="lv">${r.sub}</div>` : ''}</td>${side('earth')}${side('moon')}<td class="num">${v.difference}${unitS(r.unit)}${r.tol ? `<div class="lv">tolerance ${v.tolerance}${unitS(r.unit)}</div>` : ''}</td></tr>`;
  }).join('');
  document.getElementById('card').classList.add('pair');
  const es = SC.earth_site, ms = SC.site;
  const ll = (lat, lon) => `${Math.abs(lat)}° ${lat < 0 ? 'S' : 'N'} ${Math.abs(lon)}° ${lon < 0 ? 'W' : 'E'}`;
  document.getElementById('cardInner').innerHTML = `<h1>${C.title}</h1><div class="sub">${C.subtitle}</div>` +
    `<table class="pair"><tr><th>Variable</th><th>Earth: ${es.name}<div class="lv">cell ${es.cell_id}, ${ll(es.lat_deg, es.lon_deg)}; ${es.nearest_place_km} km from ${es.nearest_place}</div></th>` +
    `<th>Moon: ${ms.card_name}<div class="lv">cell ${ms.cell_id}, ${ms.label}; ${ms.place_ref.distance_km} km from ${ms.place_ref.feature}</div></th><th>Real difference</th></tr>${rowsH}</table>` +
    `<div class="sentence">${PV.pair_sentence}</div><div class="legend">${C.legend}</div>`;
}

function buildCard() {
  if (SC.pair_values && SC.pair_values.mission === 'solar') return buildSolarPairCard();
  if (SC.pair_values) return buildPairCard();
  const C = SC.card, tv = SC.table_values;
  const lv = (x) => ({ MEASURED: 'measured', DERIVED: 'derived', MODELLED: 'modelled' }[x] || x);
  const cell = (body, v) => {
    if (!v) return '<td class="num">—</td>';
    const e = tv[body][v.var]; let val = typeof e.value === 'number' ? (v.fmt ? Number(e.value).toFixed(v.fmt) : e.value) : (v.text || e.value);
    return `<td class="num">${val}${v.unit ? (v.unit === '°' ? '' : ' ') + v.unit : ''}<span class="lv">${lv(e.level)}${v.note ? ', ' + v.note : ''}</span></td>`;
  };
  let rows = C.rows.map((r) => `<tr><td class="var">${r.label}</td>${cell('earth', r.earth)}${cell('moon', r.moon)}</tr>`).join('');
  document.getElementById('cardInner').innerHTML = `<h1>${C.title}</h1><div class="sub">${C.subtitle}</div>` +
    `<table><tr><th>Variable</th><th>Earth: ${SC.earth_site.name}<br><span class="lv" style="margin:0">cell ${SC.earth_site.cell_id}, ${Math.abs(SC.earth_site.lat_deg)}° ${SC.earth_site.lat_deg < 0 ? 'S' : 'N'} ${Math.abs(SC.earth_site.lon_deg)}° ${SC.earth_site.lon_deg < 0 ? 'W' : 'E'}</span></th>` +
    `<th>Moon: ${SC.site.place}<br><span class="lv" style="margin:0">cell ${SC.site.cell_id}, ${SC.site.label}</span></th></tr>${rows}</table>` +
    `<div class="sentence">${C.sentence}</div><div class="legend">${C.legend}</div>`;
}
buildCard();

// ------------------------------------------------------------------ lunar base: status label and display exposure
// Each habitat step has an 'active' label (shown from t0 while it moves) and a 'done' label shown
// only from t1, the first moment the part is at rest (phase() reaches exactly 1 at t1), for hold_s.
function baseStatus(t, s) {
  const HB = SC.habitat, st = HB.steps;
  const hold = HB.done_hold_s ?? 0.8;
  for (let k = st.length - 1; k >= 0; k--) {
    const x = st[k], nextT0 = k + 1 < st.length ? st[k + 1].t0 : Infinity;
    if (t >= x.t0 && t < x.t1) return x.active;
    if (t >= x.t1 && t < Math.min(x.t1 + hold, nextT0)) return x.done;
  }
  const S = SC.sun_status;
  if (s.elev <= -M.SUN_DIAM_DEG / 2) return S.night;
  if (s.vis <= 0) return t < st[0].t0 ? S.before_sunrise : S.blocked;
  if (s.vis < 1) return t < st[0].t0 ? S.rising : S.partly;
  return t < st[0].t0 ? S.day_before : S.day_after;
}
// Solar (flat array, scenario.sun_status with elevation bands): while the array moves the label is
// sun_status.deploying; from deploy_end_s (the first frame at rest: phase() reaches exactly 1 there)
// sun_status.deployed for done_hold_s; otherwise the label follows the Sun at the array (real terrain
// horizon first, then the Sun's elevation band; morning / afternoon from the sign of the hour angle).
function solarStatus(t, s) {
  const A = SC.array, S = SC.sun_status;
  if (!S) return null;
  if (t >= A.deploy_start_s && t < A.deploy_end_s) return S.deploying;
  if (t >= A.deploy_end_s && t < A.deploy_end_s + (A.done_hold_s ?? 1.5)) return S.deployed;
  const stowed = t < A.deploy_start_s;
  if (s.elev <= -M.SUN_DIAM_DEG / 2) return S.night;
  if (s.vis <= 0) return S.blocked;
  if (s.vis < 1) return S.partly;
  const am = s.Hh < 0;
  if (s.elev < S.low_deg) return stowed ? S.low_morning_stowed : am ? S.low_morning : S.low_evening;
  if (stowed) return S.morning_stowed;
  if (s.elev >= S.high_deg) return S.high;
  return am ? S.morning : S.afternoon;
}
// Display exposure (a camera setting, not a change of the light): 1 while the habitat site sees the
// whole solar disc, render.shadow_exposure (EX) while it sees none of it, and in between the value that
// keeps the site's light level constant on screen: 1 / (1/EX + (1 - 1/EX) * visible disc fraction).
// A function of t only (no adaptation lag). Stated on screen whenever it is above 1.25.
// Solar (render.low_sun_exposure = {ref_deg, max}): display exposure min(max, max(1, sin(ref) / sin(h))),
// h = the Sun's elevation, so the ground lit by a low Sun stays readable; a function of t only; stated on
// screen whenever it is above 1.25. The light itself is not changed (power uses the real geometry).
function lowSunExposure(t) {
  const L = SC.render?.low_sun_exposure; if (!L) return 1;
  const h = Math.max(0.3, sunAt(Math.min(t, SIM_END)).elev);
  return Math.min(L.max, Math.max(1, Math.sin(L.ref_deg * D2R) / Math.sin(h * D2R)));
}
function exposureAt(t) {
  if (isSolar) return lowSunExposure(t);
  const EX = SC.render?.shadow_exposure ?? 1;
  if (EX === 1) return 1;
  const v = sunAt(Math.min(t, SIM_END)).vis;
  return 1 / (1 / EX + (1 - 1 / EX) * v);
}
window.statusAt = function (t) {
  const s = sunAt(Math.min(t, SIM_END));
  return { t, status: isSolar ? solarStatus(t, s) : baseStatus(t, s), sunElev: s.elev, sunAz: s.az, horizon: s.hz, visible: s.vis, exposure: exposureAt(t) };
};

// ------------------------------------------------------------------ frame
const tmpV = new THREE.Vector3();
window.renderAt = function (t) {
  const tc = Math.min(t, SIM_END);
  const s = sunAt(tc);
  sunU.sunElev.value = s.elev;
  const sd = new THREE.Vector3(s.E, s.U, -s.N).normalize();
  updateHz(nearTex, nearHz, NEAR.n * NEAR.n, TR.n_az, s.az);
  updateHz(farTex, farHz, FAR.n * FAR.n, TR.n_az, s.az);
  objLit.value = s.vis;

  // camera
  const ck = camAt(Math.min(t, SC.camera.keys[SC.camera.keys.length - 1].t));
  const tgt = new THREE.Vector3(0, g0 + ck.target_z, 0);
  const cp = tgt.clone().add(dirFromAzEl(ck.az_deg, ck.elev_deg).multiplyScalar(ck.dist));
  cp.y = Math.max(cp.y, groundAt(cp.x, -cp.z) + 1.8);
  camera.position.copy(cp); camera.lookAt(tgt); camera.updateMatrixWorld();
  camU.microFade.value = Math.min(1, Math.max(0, (1200 - ck.dist) / 600));

  // sky objects follow the camera (they are at infinity)
  sunDisc.position.copy(cp).addScaledVector(sd, SKY_R * 0.9); sunDisc.lookAt(cp);
  sunDisc.visible = s.elev > -1;
  window.__stars.position.copy(cp);
  let night = 0, earthLit = 0;
  if (earth) {
    const ed = dirFromAzEl(TR.earth.az_deg, TR.earth.elev_deg);
    earth.position.copy(cp).addScaledVector(ed, SKY_R * 0.8);
    earth.material.uniforms.sunDirW.value.copy(sd);
    earthLit = (1 - sd.dot(ed)) / 2;              // illuminated fraction of the Earth disc seen from the Moon
    night = 1 - M.smooth(s.vis);
    earthLight.position.copy(tgt).addScaledVector(ed, 1500); earthLight.target.position.copy(tgt);
    earthLight.intensity = SUN_I * EARTH_BOOST * earthLit * night;
  }

  sun.position.copy(tgt).addScaledVector(sd, 1500); sun.target.position.copy(tgt);
  sun.intensity = s.elev > -M.SUN_DIAM_DEG ? SUN_I : 0;

  const out = { t: +t.toFixed(4), H: s.Hh, sunElev: s.elev, sunAz: s.az, horizon: s.hz, visible: s.vis, days: M.simDays(SC, tc), compression: COMP };
  let status = '', rows = '';
  if (isSolar) {
    const A = SC.array;
    const uM = M.phase(t, A.deploy_start_s, A.deploy_start_s + (A.deploy_end_s - A.deploy_start_s) * 0.4);
    const uW = M.phase(t, A.deploy_start_s + (A.deploy_end_s - A.deploy_start_s) * 0.4, A.deploy_end_s);
    const L = 2.0 + (A.mast_height_m - 2.0) * uM;
    solar.mast.scale.y = L; solar.mast.position.y = 0.4 + L / 2;
    solar.head.position.y = 0.4 + L - (A.mast_height_m - A.hub_height_m) * uM;
    if (!solar.FLAT) solar.head.rotation.y = -s.az * D2R;
    const fold = (1 - uW) * 86 * D2R;
    for (const hinges of solar.wings) hinges.forEach((h, k) => { h.rotation.y = k === 0 ? -fold * 0.98 : (k % 2 ? 2 * fold : -2 * fold); });
    const se = seriesAt(tc);
    const deployed = t >= A.deploy_end_s;
    const pp = M.panelPower(S0, A.final_tilt_deg, s.elev, s.vis);
    out.P = se.P; out.E = se.E; out.tilt = A.final_tilt_deg; out.inc = pp.inc; out.deployed = deployed;
    if (SC.sun_status) status = solarStatus(t, s);
    else if (t < A.deploy_start_s) status = s.vis > 0 ? 'Dawn: array stowed' : 'Dawn: Sun behind the terrain';
    else if (!deployed) status = 'Deploying array';
    else if (s.elev <= -M.SUN_DIAM_DEG / 2) status = 'Sun below the horizon';
    else if (s.vis <= 0) status = 'Sun blocked by terrain';
    else if (s.vis < 1) status = 'Sun partly behind terrain';
    else status = 'Tracking the Sun';
    if (solar.FLAT) {
      const PL = SC.panel_text;
      const ex = exposureAt(t); renderer.toneMappingExposure = ex; out.exposure = ex;
      rows = row('Sun elevation', f1(s.elev) + '°') + row('Sun azimuth', f1(s.az) + '°') + row('Terrain horizon', f1(s.hz) + '°') +
        row('Panel', 'flat (horizontal)') + row('Power (model)', thou(se.P) + ' W/m²') + row(deployed ? 'Energy (model)' : 'Energy (after deploy)', se.E.toFixed(2) + ' kWh/m²') +
        row('Elapsed', f1(M.simDays(SC, tc)) + ' Earth days') + row('Time', compStr) + row('Earth', PL.earth_row);
      panel.innerHTML = `<div class="title">Solar panels · ${SC.site.cell_id}</div><div class="site">${SC.site.label}, ${SC.site.place}</div>` +
        `<div class="site zone">${SC.site.zone.name}</div><div class="status">${status}</div>${rows}` +
        `<div id="graphwrap"><div class="cap">${PL.graph_caption}</div></div><div class="tag" style="margin-top:6px">${PL.model_tag}` +
        (ex > 1.25 ? `<br><span style="color:#f2a33a">Exposure ×${f1(ex)} for the low Sun (not to scale).</span>` : '') + `</div>`;
      document.getElementById('graphwrap').appendChild(graph); drawGraph(t);
      out.status = status;
    } else {
    rows = row('Sun elevation', f1(s.elev) + '°') + row('Sun azimuth', f1(s.az) + '°') + row('Terrain horizon', f1(s.hz) + '°') +
      row('Panel tilt', f1(A.final_tilt_deg) + '°') + row('Incidence', f1(pp.inc) + '°') +
      row('Power', thou(se.P) + ' W/m²') + row(deployed ? 'Energy' : 'Energy (after deploy)', se.E.toFixed(2) + ' kWh/m²') +
      row('Elapsed', f1(M.simDays(SC, tc)) + ' Earth days') + row('Time', compStr) +
      row('Earth', TR.earth.draw ? 'above horizon' : 'below horizon');
    panel.innerHTML = `<div class="title">Solar array · ${SC.site.cell_id}</div><div class="site">${SC.site.label}, ${SC.site.place}</div><div class="status">${status}</div>${rows}` +
      `<div id="graphwrap"><div class="cap">Power per m² vs time, 0–1,400 W/m²</div></div><div class="tag" style="margin-top:6px">Computed: Sun, power, energy (S0 ${S0} W/m²)</div>`;
    document.getElementById('graphwrap').appendChild(graph); drawGraph(t);
    }
  } else {
    const HB = SC.habitat, st = HB.steps;
    const u1 = M.phase(t, st[0].t0, st[0].t1), u2 = M.phase(t, st[1].t0, st[1].t1), u3 = Math.min(1, Math.max(0, (t - st[2].t0) / (st[2].t1 - st[2].t0)));
    const restY = base.gmax + HB.module_d_m / 2 + 1.23;
    base.module.position.set(0, restY + (1 - u1) * 22, 0);
    base.module.visible = t >= st[0].t0 - 0.01;
    const rs = 0.28 + 0.72 * u2;
    base.infl.scale.set(0.35 + 0.65 * u2, rs, rs);
    base.infl.position.x = HB.module_l_m / 2 + 1.0 + (HB.inflatable_l_m / 2) * (0.35 + 0.65 * u2);
    base.infl.visible = t >= st[1].t0 - 0.01;
    const pa = base.bg.attributes.position;
    for (let i = 0; i < base.groundY.length; i++) { const k = M.smooth((u3 * 1.25 - base.angF[i]) * 4); pa.array[3 * i + 1] = base.groundY[i] + base.ph[i] * k; }
    pa.needsUpdate = true; base.bg.computeVertexNormals();
    base.berm.visible = t >= st[2].t0;
    const T = Tcurve(s.Hh);
    out.T = T; out.night = night; out.earthLit = earthLit;
    const tm = SC.table_values.moon;
    status = baseStatus(t, s);
    out.status = status;
    const ex = exposureAt(t);
    renderer.toneMappingExposure = ex;
    out.exposure = ex; out.landed = t >= st[0].t1;
    const lit = s.vis >= 1 ? 'sunlit' : s.vis > 0 ? 'partly sunlit' : (s.elev > -M.SUN_DIAM_DEG / 2 ? 'in terrain shadow' : 'night');
    rows = row('Surface temp.', `${f1(T)} K  ${f1(T - 273.15)} °C`) + row('Measured min', tm.tmin_k.value + ' K') + row('Measured max', tm.tmax_k.value + ' K') +
      row('Diurnal amplitude', tm.lst_diurnal_amp_k.value + ' K') + row('Sun elevation', f1(s.elev) + '°') + row('Sun azimuth', f1(s.az) + '°') +
      row('Terrain horizon', f1(s.hz) + '°') + row('Habitat site', lit) + row('Elapsed', f1(M.simDays(SC, tc)) + ' Earth days') + row('Time', compStr) +
      row('Earth', TR.earth.draw ? `az ${f1(TR.earth.az_deg, 0)}° el ${f1(TR.earth.elev_deg)}°` : 'behind terrain (mean pos.)');
    const exTag = ex > 1.25 ? `<br><span style="color:#f2a33a">Exposure raised ×${f1(ex)} to show the ground in shadow (not to scale).</span>` : '';
    panel.innerHTML = `<div class="title">Lunar base · ${SC.site.cell_id}</div><div class="site">${SC.site.label}, ${SC.site.place}</div>` +
      (SC.site.zone ? `<div class="site zone">${SC.site.zone.name}</div>` : '') + `<div class="status">${status}</div>${rows}` +
      `<div class="tag" style="margin-top:8px">Surface temp.: model curve between the measured Diviner min and max. Sun: computed.${night > 0.5 ? '<br><span style=\"color:#f2a33a\">Night view: exposure raised to show earthshine (not to scale).</span>' : ''}${exTag}</div>`;
    drawInset(T);
  }
  out.status = status;
  const cu = Math.min(1, Math.max(0, (t - CARD0) / 0.8));
  card.style.opacity = String(cu);
  for (const el of [panel, foot, inset]) el.style.opacity = String(1 - cu);
  renderer.render(scene, camera);
  return out;
};
// Check view: the near terrain patch seen straight down (orthographic, north up), lit from the
// north-west at 25 deg like the shaded-relief PNG written by prepare.py, objects and overlays hidden.
window.renderTopdown = function () {
  const s = { az: Number(qs.get('tdaz') ?? 315), elev: 25 };
  const sd = dirFromAzEl(s.az, s.elev);
  sunU.sunElev.value = s.elev; updateHz(nearTex, nearHz, NEAR.n * NEAR.n, TR.n_az, s.az);
  camU.microFade.value = 0; objLit.value = 0; root.visible = false; if (earth) earth.visible = false; sunDisc.visible = false;
  for (const el of [panel, foot, inset, card]) el.style.display = 'none';
  const h = NEAR.half, cam = new THREE.OrthographicCamera(-h * 16 / 9, h * 16 / 9, h, -h, 1, 50000);
  cam.position.set(0, 20000, 0); cam.up.set(0, 0, -1); cam.lookAt(0, 0, 0); cam.updateMatrixWorld();
  sun.position.copy(sd).multiplyScalar(5000); sun.target.position.set(0, 0, 0); sun.intensity = SUN_I;
  renderer.render(scene, cam);
};
window.__ready = true;
