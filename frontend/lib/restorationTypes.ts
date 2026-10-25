export interface RestorationNetworkResponse {
  network: {
    network_version: string;
    title: string;
    disclaimer: string;
    modeled_customer_group_id?: string;
    components: Array<{ id: string; label: string; repair_type: string }>;
    switches?: Array<{ id: string; label: string; initial_state: string; illustrative_only?: boolean }>;
    customer_groups: Array<{
      id: string;
      label: string;
      priority_tier: number;
      simulated_customer_count: number;
    }>;
  };
  labor_references: {
    synthetic_labor_warning?: boolean;
    data_provenance?: string;
    replace_with_aep_workbook?: string;
  };
}

export type DamageSeverity = "minor" | "moderate" | "major";
export type AccessConditions = "normal" | "difficult" | "restricted";

export interface StormContext {
  damage_severity: DamageSeverity;
  access_conditions: AccessConditions;
  extra_mobilization_hours: number;
  crew_mobilization_hours: number;
  repair_quantity_by_component: Record<string, number>;
  access_ready_hours_by_component: Record<string, number>;
  eta_explanations: string[];
  disclaimer: string;
}

export interface RestorationSimRequest {
  damaged_component_ids: string[];
  total_workers: number;
  workers_per_crew: number;
  baseline_repair_order?: string[];
  enable_step_restoration?: boolean;
  damage_severity?: DamageSeverity;
  access_conditions?: AccessConditions;
  extra_mobilization_hours?: number;
}

export interface ScheduleBlock {
  strategy?: Array<{ type: string; component_id?: string; action_id?: string }>;
  timeline: Array<Record<string, unknown>>;
  group_restoration_times: Record<string, number | null>;
  all_groups_restored_at: number | null;
  weighted_customer_restoration_time: number;
  crew_count: number;
}

export interface RestorationSimResponse {
  damaged_component_ids: string[];
  storm_context?: StormContext;
  labor_preview?: Array<{
    component_id: string;
    repair_type: string;
    quantity: number;
    central_repair_hours: number;
    access_ready_hours: number;
  }>;
  modeled_customer_group_id?: string;
  modeled_home_restore_hours?: number | null;
  all_groups_restore_hours?: number | null;
  initial_snapshot: {
    simulated_outage_group_ids: string[];
    powered_group_ids: string[];
    switch_states?: Record<string, string>;
  };
  repair_only_optimized: ScheduleBlock | null;
  step_restoration_optimized: ScheduleBlock | null;
  baseline_repair_order?: ScheduleBlock;
  comparison: {
    hospital_restore_delta_hours: number | null;
    repair_only_hospital_restore?: number | null;
    step_restoration_hospital_restore?: number | null;
    note?: string;
  };
  labor_config_metadata: {
    synthetic_labor_warning?: boolean;
    data_provenance?: string;
  };
  limitations: string[];
  baseline?: ScheduleBlock;
  optimized?: ScheduleBlock;
}
