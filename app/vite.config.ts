import { defineConfig, loadEnv } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

const cesiumBuild = 'node_modules/cesium/Build/Cesium';
// Where Cesium's workers, textures and star map are served from (relative to the page).
// index.html sets window.CESIUM_BASE_URL to the same folder.
const CESIUM_BASE = 'cesium';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const useIon = env.VITE_USE_ION === '1';
  return {
    base: './',
    define: {
      // The ion token reaches the bundle only when ion mode is switched on explicitly.
      // A normal (key-free) build never contains it.
      ...(useIon ? {} : { 'import.meta.env.VITE_CESIUM_ION_TOKEN': JSON.stringify('') }),
    },
    plugins: [
      viteStaticCopy({
        targets: [
          { src: `${cesiumBuild}/Workers`, dest: CESIUM_BASE, rename: { stripBase: 4 } },
          { src: `${cesiumBuild}/ThirdParty`, dest: CESIUM_BASE, rename: { stripBase: 4 } },
          { src: `${cesiumBuild}/Assets`, dest: CESIUM_BASE, rename: { stripBase: 4 } },
          { src: `${cesiumBuild}/Widgets`, dest: CESIUM_BASE, rename: { stripBase: 4 } },
        ],
      }),
    ],
    build: {
      target: 'es2022',
      sourcemap: false,
      // CesiumJS is one large ES module graph (about 4 MB minified); splitting it gains nothing.
      chunkSizeWarningLimit: 6000,
    },
    server: { port: 5173 },
  };
});
