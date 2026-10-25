export type NotificationChannel = "sms" | "email" | "in_app";

export type AlertType =
  | "storm_preparation"
  | "modeled_outage"
  | "eta_update"
  | "power_restored";

export interface AlertPreferences {
  notifications_enabled: boolean;
  channel: NotificationChannel;
  medium_risk_preparation: boolean;
}

export interface AlertEvent {
  event_id: string;
  session_id: string;
  premise_id: string;
  modeled_customer_reference: string;
  alert_type: AlertType;
  trigger_reason: string;
  relative_risk?: string | null;
  eta_category?: string | null;
  eta_category_previous?: string | null;
  channel: NotificationChannel;
  channel_label: string;
  timestamp_utc: string;
  simulated_time_hours?: number | null;
  title: string;
  body: string;
  status: "previewed" | "suppressed" | "eligible";
  suppression_reason?: string | null;
  delivery_note: string;
  read: boolean;
}

export interface AlertSessionResponse {
  session_id: string;
  premise_id: string;
  modeled_customer_group_id: string;
  preferences: AlertPreferences;
  events: AlertEvent[];
  unread_count: number;
  disclaimer: string;
}

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  storm_preparation: "Storm preparation",
  modeled_outage: "Simulated outage",
  eta_update: "ETA update",
  power_restored: "Power restored",
};
