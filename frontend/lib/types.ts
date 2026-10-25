export interface DeviceSearchRow {
  device_key: string;
  device_type: string;
  location_id: string;
  dependent_premises: number;
}

export interface DeviceSearchResponse {
  devices: DeviceSearchRow[];
}

export interface DeviceRecord {
  device_key: string;
  device_type: string;
  location_id: string;
  source_type: string;
  source_id: string;
}

export interface CustomerPoint {
  premise_id: string;
  longitude: number;
  latitude: number;
  circuit_id: string;
}

export interface DeviceImpactResponse {
  device: DeviceRecord;
  potentially_dependent_premises: number;
  returned_customer_points: number;
  customers: CustomerPoint[];
  note: string;
}

export interface PremiseRecord {
  premise_id: string;
  longitude: number;
  latitude: number;
  circuit_id: string;
}

export interface PremiseUpstreamResponse {
  premise: PremiseRecord;
  upstream: DeviceRecord[];
}

export interface HealthResponse {
  status: string;
  premises: number;
  gis_db?: boolean;
}

export interface GisLayerMeta {
  layer_id: string;
  title: string;
  geometry: "point" | "line";
  source_file: string;
  source_crs: string;
  record_count: number;
  default_on: boolean;
  min_zoom: number;
  bbox_required: boolean;
  fields: string[];
}

export interface GisJoinLayerStats {
  features: number;
  features_with_location_n: number;
  distinct_location_n: number;
  distinct_location_n_matched_to_devices: number;
  features_with_matched_location_n: number;
}

export interface GisJoinReport {
  method: string;
  totals: {
    devices_in_network_db: number;
    distinct_device_location_id: number;
    gis_features_with_location_n: number;
    gis_features_matched_exact_location_id: number;
    distinct_matched_location_ids: number;
  };
  layers: Record<string, GisJoinLayerStats>;
}

export interface GisCatalogResponse {
  layers: GisLayerMeta[];
  join: GisJoinReport | null;
  note: string;
}

export interface GisFeatureProperties {
  [key: string]: string | number | boolean | null | undefined;
  _layer: string;
  _feature_id: string;
  _location_n?: string | null;
  _topology_match?: boolean;
}

export interface GisFeature {
  type: "Feature";
  id?: string;
  geometry: { type: string; coordinates: unknown };
  properties: GisFeatureProperties;
}

export interface GisFeatureCollection {
  type: "FeatureCollection";
  features: GisFeature[];
  layer: string;
  returned: number;
  truncated: boolean;
  reason?: string;
  filter_note?: string;
}

export interface StudyAreaConfig {
  selected_circuit_id: string;
  title: string;
  selection_rationale: string;
  filter: {
    infrastructure: string;
    damage: string;
  };
  bounds_wgs84: {
    min_lng: number;
    min_lat: number;
    max_lng: number;
    max_lat: number;
  };
  counts: Record<string, number>;
  candidates_compared: Array<Record<string, unknown>>;
}

export interface DemoSectionDevice {
  location_n: string;
  device_key: string;
  layer: string;
  device_type: string;
  dependent_premises: number;
}

export interface DemoSectionConfig {
  circuit_id: string;
  primary_gis_circuit_id?: string;
  title: string;
  selection_rationale: string;
  data_integrity?: Record<string, unknown>;
  bounds_wgs84: {
    min_lng: number;
    min_lat: number;
    max_lng: number;
    max_lat: number;
  };
  map: {
    min_zoom: number;
    max_zoom: number;
    max_bounds_padding: number;
  };
  filter: Record<string, string>;
  protective_devices: DemoSectionDevice[];
  dependency_analysis: {
    individual_counts: Record<string, number>;
    pairwise_overlap: Array<{
      a_location_n: string;
      b_location_n: string;
      shared_premises: number;
    }>;
    union_premises: number;
    union_premises_outside_map_bounds: number;
  };
  primary_segments_in_bounds: number;
  concerns: string[];
}

export interface TopologyDeviceMatch {
  device_key: string;
  device_type: string;
  location_id: string;
  source_type: string;
  source_id: string;
  dependent_premises: number;
}

export interface GisLocationMatch {
  location_id: string;
  match_method: string;
  gis_assets: Array<{
    layer_id: string;
    feature_id: string;
    location_n: string;
    properties: Record<string, unknown>;
  }>;
  devices: TopologyDeviceMatch[];
  note: string;
}

export interface SelectedGisAsset {
  layerId: string;
  featureId: string;
  locationId: string | null;
  properties: GisFeatureProperties;
  geometry?: { type: string; coordinates: unknown };
}

export interface DeviceUnavailableScenario {
  scenario_type: "device_unavailable";
  device_key: string;
  device: DeviceRecord;
  modeled_potential_exposure_count: number;
  premise_count: number;
  returned_customer_points: number;
  premise_ids: string[];
  customers: CustomerPoint[];
  note: string;
  disclaimer: string;
}

export interface ActiveExposureScenario {
  deviceKey: string;
  gisLayerId?: string;
  gisFeatureId?: string;
  locationId?: string | null;
  data: DeviceUnavailableScenario;
}
