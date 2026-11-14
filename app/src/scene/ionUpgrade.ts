// Optional Cesium ion upgrade. Active only when VITE_USE_ION=1 and VITE_CESIUM_ION_TOKEN is set at
// build time; otherwise this module does nothing and the app stays key-free (the deployed mode).
// The rest of the code never needs to know which mode is running.

import {
  Cesium3DTileset,
  CesiumTerrainProvider,
  ImageryLayer,
  Ion,
  IonImageryProvider,
} from 'cesium';
import type { Globes } from './globes';

/** Cesium ion asset ids (Cesium docs, checked 2026-11-14). */
const ION_ASSETS = { worldTerrain: 1, bingAerial: 2, moon: 2684829 } as const;

export function ionEnabled(): boolean {
  return import.meta.env.VITE_USE_ION === '1' && Boolean(import.meta.env.VITE_CESIUM_ION_TOKEN);
}

export interface IonResult {
  used: string[];
  failed: string[];
}

export async function applyIonUpgrade(globes: Globes): Promise<IonResult> {
  const result: IonResult = { used: [], failed: [] };
  if (!ionEnabled()) return result;
  Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN as string;

  const es = globes.earth.scene;
  try {
    es.terrainProvider = await CesiumTerrainProvider.fromIonAssetId(ION_ASSETS.worldTerrain, {
      requestWaterMask: true,
      requestVertexNormals: true,
    });
    es.globe.showWaterEffect = true;
    result.used.push('Cesium World Terrain');
  } catch {
    result.failed.push('Cesium World Terrain');
  }
  try {
    const bing = await IonImageryProvider.fromAssetId(ION_ASSETS.bingAerial);
    // Insert just above Blue Marble so night lights and labels stay on top.
    es.imageryLayers.add(new ImageryLayer(bing), 1);
    result.used.push('Bing Maps aerial (Cesium ion)');
  } catch {
    result.failed.push('Bing Maps aerial (Cesium ion)');
  }

  try {
    const tileset = await Cesium3DTileset.fromIonAssetId(ION_ASSETS.moon);
    globes.moon.scene.primitives.add(tileset);
    result.used.push('Cesium Moon terrain');
  } catch {
    // The account may not have Cesium Moon in its asset library; the WAC globe stays.
    result.failed.push('Cesium Moon terrain');
  }
  es.requestRender();
  globes.moon.scene.requestRender();
  return result;
}
