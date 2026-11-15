// Every imagery and data source on screen, with its required credit line and licence.

export interface CreditEntry {
  source: string;
  used: string;
  credit: string;
  licence: string;
  link: string;
}

export const CREDITS: CreditEntry[] = [
  {
    source: 'NASA Global Imagery Browse Services (GIBS)',
    used: 'Earth base imagery (Blue Marble Next Generation), night lights (VIIRS Black Marble 2016) and the place-name overlay (reference labels, 15 m).',
    credit:
      "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS).",
    licence: 'NASA Earth science data, openly available without a key or fee; the credit line above is requested by GIBS.',
    link: 'https://nasa-gibs.github.io/gibs-api-docs/',
  },
  {
    source: 'Sentinel-2 cloudless 2016 by EOX',
    used: 'Sharper Earth imagery that fades in when you zoom below about 1,300 km.',
    credit:
      'Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016).',
    licence: 'Creative Commons Attribution 4.0 International (CC BY 4.0). Only the 2016 edition is used; later editions carry a different licence.',
    link: 'https://s2maps.eu',
  },
  {
    source: 'NASA Moon Trek (Solar System Treks, NASA/JPL)',
    used: 'Moon imagery: LRO Wide Angle Camera global mosaic (303 pixels per degree, version 2).',
    credit: 'NASA Moon Trek; LRO LROC Wide Angle Camera mosaic, NASA/GSFC/Arizona State University.',
    licence: 'NASA mission data. The Moon Trek service publishes no separate licence text; NASA/GSFC/ASU are credited as the image source.',
    link: 'https://trek.nasa.gov/moon/',
  },
  {
    source: 'Gazetteer of Planetary Nomenclature (IAU WGPSN, USGS)',
    used: 'Moon feature names and positions (1,691 maria, craters of 10 km and larger, mountains, valleys and other named features).',
    credit:
      'Gazetteer of Planetary Nomenclature, International Astronomical Union (IAU) Working Group for Planetary System Nomenclature (WGPSN), USGS Astrogeology Science Center.',
    licence: 'Published by the USGS (a US Government work). Longitudes converted from 0-360 east to -180..180 east.',
    link: 'https://planetarynames.wr.usgs.gov/',
  },
  {
    source: 'CesiumJS 1.147',
    used: '3D globe rendering, Sun and Moon positions, sky atmosphere.',
    credit: 'CesiumJS, Cesium GS, Inc. and contributors.',
    licence: 'Apache License 2.0.',
    link: 'https://cesium.com/platform/cesiumjs/',
  },
  {
    source: 'Star background (bundled with CesiumJS)',
    used: 'Sky box in both views, built from the Tycho-2 star catalogue.',
    credit: 'NASA Goddard Space Flight Center Scientific Visualization Studio, Tycho Catalog Skymap (Version 2.0), as bundled with CesiumJS.',
    licence: 'NASA imagery; terms as listed in the CesiumJS licence file.',
    link: 'https://svs.gsfc.nasa.gov/3572',
  },
  {
    source: 'Barlow and Barlow Semi Condensed typefaces',
    used: 'All interface text, bundled with the site (no font service).',
    credit: 'Barlow by Jeremy Tribby.',
    licence: 'SIL Open Font License 1.1.',
    link: 'https://fontsource.org/fonts/barlow',
  },
  {
    source: 'GIBS web examples',
    used: 'The geographic tiling scheme for GIBS tiles is adapted from NASA’s example code.',
    credit: 'nasa-gibs/gibs-web-examples, Copyright 2013-2020 United States Government as represented by the Administrator of NASA.',
    licence: 'Apache License 2.0.',
    link: 'https://github.com/nasa-gibs/gibs-web-examples',
  },
];

export function renderCredits(container: HTMLElement, extra: CreditEntry[] = []): void {
  container.replaceChildren();
  const list = document.createElement('dl');
  list.className = 'credits-list';
  for (const c of [...CREDITS, ...extra]) {
    const dt = document.createElement('dt');
    const a = document.createElement('a');
    a.href = c.link;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = c.source;
    dt.append(a);
    const used = document.createElement('dd');
    used.textContent = c.used;
    const credit = document.createElement('dd');
    credit.className = 'credit-line';
    credit.textContent = c.credit;
    const licence = document.createElement('dd');
    licence.className = 'credit-licence';
    licence.textContent = c.licence;
    list.append(dt, used, credit, licence);
  }
  container.append(list);
}
