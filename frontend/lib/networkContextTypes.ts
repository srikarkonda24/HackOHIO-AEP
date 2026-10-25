export interface NetworkContextPremise {
  premise_id: string;
  longitude: number;
  latitude: number;
  circuit_id: string;
  source: string;
}

export interface NetworkContextDevice {
  device_key: string;
  device_type: string;
  location_id: string;
  source_type?: string;
  source_id?: string;
}

export interface NetworkContextUpstream {
  device: NetworkContextDevice;
  relationship_kind: string;
  evidence_type: string;
  source: string;
  is_ordered_path_position: boolean;
  direct_equipment_link_to_recorded_service_location: boolean;
  location_id_gis_join: {
    location_id: string | null;
    gis_features_found: boolean;
    match_method: string | null;
  };
  gis_assets: Array<{
    layer_id: string;
    feature_id: string;
    location_n: string;
    attributes: Record<string, unknown>;
  }>;
  gis_switching_attribute_disclaimer?: string | null;
}

export interface CustomerNetworkContext {
  premise_id: string;
  premise: NetworkContextPremise;
  customer_clip: Record<string, unknown> | null;
  customer_clip_source: string | null;
  service_transformer: {
    recorded_service_location_n: string;
    evidence_type: string;
    source: string;
    relationship_kind: string;
    matched_network_devices: NetworkContextDevice[];
    note: string;
  } | null;
  upstream_devices: NetworkContextUpstream[];
  upstream_device_count: number;
  upstream_is_ordered_path: boolean;
  circuit_identifier_observations: Array<{
    location_n: string;
    conflict_type: string;
    circuit_ids: Record<string, string[]>;
    note: string;
  }>;
  missing_or_partial: string[];
  limitations: string[];
  disclaimer: string;
  evidence_model_version: string;
  gis_attribute_references?: unknown[];
  gis_location_attributes?: Record<string, unknown>;
}
