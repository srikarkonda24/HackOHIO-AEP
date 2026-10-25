import type { CustomerPoint } from "./types";

type PointFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: { premise_id: string; circuit_id: string };
};

export function isPlottableCustomer(c: CustomerPoint): boolean {
  return (
    Number.isFinite(c.longitude) &&
    Number.isFinite(c.latitude) &&
    c.longitude !== 0 &&
    c.latitude !== 0
  );
}

export function customersToFeatureCollection(customers: CustomerPoint[]): {
  type: "FeatureCollection";
  features: PointFeature[];
} {
  const features = customers.filter(isPlottableCustomer).map((c) => ({
    type: "Feature" as const,
    geometry: {
      type: "Point" as const,
      coordinates: [c.longitude, c.latitude] as [number, number],
    },
    properties: {
      premise_id: c.premise_id,
      circuit_id: c.circuit_id,
    },
  }));

  return { type: "FeatureCollection", features };
}

export function boundsFromFeatures(
  features: PointFeature[],
): [[number, number], [number, number]] | null {
  if (features.length === 0) return null;

  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;

  for (const f of features) {
    if (f.geometry?.type !== "Point") continue;
    const [lng, lat] = f.geometry.coordinates as [number, number];
    minLng = Math.min(minLng, lng);
    minLat = Math.min(minLat, lat);
    maxLng = Math.max(maxLng, lng);
    maxLat = Math.max(maxLat, lat);
  }

  if (!Number.isFinite(minLng)) return null;
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}
