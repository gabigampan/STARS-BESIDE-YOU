var TARGET_RES_M = 500;
var centerLon = -0.265196;
var centerLat = 39.139605;
var roi = ee.Geometry.Point([centerLon, centerLat]).buffer(30000).bounds();

var srtm = ee.Image('USGS/SRTMGL1_003').select('elevation').toFloat();
var aster = ee.Image('NASA/ASTER_GED/AG100_003');
var asterDem = aster.select('elevation').toFloat();
var elevation_m = srtm.unmask(asterDem).rename('elevation_m');

var slope_deg = ee.Terrain.slope(elevation_m).toFloat().rename('slope_deg');
var roughness_m = elevation_m.reduceNeighborhood({
  reducer: ee.Reducer.stdDev(),
  kernel: ee.Kernel.square(1, 'pixels')
}).toFloat().rename('roughness_m');

var meanElev = elevation_m.reduceRegion({
  reducer: ee.Reducer.mean(),
  geometry: roi,
  scale: TARGET_RES_M,
  maxPixels: 1e9
}).getNumber('elevation_m');
var elevation_rel_m = elevation_m.subtract(meanElev).toFloat().rename('elevation_rel_m');

var modisLst = ee.ImageCollection('MODIS/061/MOD11A1')
  .filterBounds(roi)
  .filterDate('2025-01-01', '2026-11-14')
  .map(function(img) {
    var qc = img.select('QC_Day');
    var goodQuality = qc.bitwiseAnd(3).lte(1);
    var tempK = img.select('LST_Day_1km').multiply(0.02);
    var validRange = tempK.gte(180.0).and(tempK.lte(360.0));
    return tempK.updateMask(goodQuality.and(validRange));
  })
  .median();

var asterTempK = aster.select('temperature_mean').multiply(0.01);
var temp_k = modisLst.unmask(asterTempK).toFloat().rename('temp_k');

var asterNdvi = aster.select('ndvi').multiply(0.01);
var rock_or_bare_frac = ee.Image(1.0).subtract(asterNdvi).clamp(0.0, 1.0)
  .toFloat().rename('rock_or_bare_frac');

var sar_sigma0_db = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(roi)
  .filterDate('2025-01-01', '2026-11-14')
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .select('VV')
  .median()
  .clamp(-35.0, 15.0)
  .toFloat()
  .rename('sar_sigma0_db');

var earthHarmonized = ee.Image.cat([
  elevation_m,
  elevation_rel_m,
  slope_deg,
  roughness_m,
  temp_k,
  rock_or_bare_frac,
  sar_sigma0_db
]).reproject({crs: 'EPSG:3857', scale: TARGET_RES_M}).clip(roi);

Map.centerObject(roi, 10);
Map.addLayer(earthHarmonized.select('elevation_m'), {min: 0, max: 2500}, 'Elevation (m)');
Map.addLayer(earthHarmonized.select('temp_k'), {min: 270, max: 315}, 'Temperature (K)');

Export.image.toDrive({
  image: earthHarmonized,
  description: 'earth_harmonized_clean_500m',
  fileNamePrefix: 'earth_harmonized_clean',
  region: roi,
  scale: TARGET_RES_M,
  crs: 'EPSG:3857',
  maxPixels: 1e9,
  fileFormat: 'GeoTIFF'
});
