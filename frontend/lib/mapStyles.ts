/** Basemap styles (no API key). First entry is preferred; fallbacks used on load failure. */
export const MAP_STYLE_URLS = [
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  "https://demotiles.maplibre.org/style.json",
] as const;

/** Font stack from CARTO Dark Matter style (for cluster count labels). */
export const CARTO_FONT_STACK = [
  "Montserrat Medium",
  "Open Sans Regular",
  "Noto Sans Regular",
  "Noto Sans CJK JP Regular",
] as const;
