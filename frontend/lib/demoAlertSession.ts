const SESSION_KEY = "gridaware_demo_alert_session_id";

export function getDemoAlertSessionId(): string {
  if (typeof window === "undefined") return "ssr-placeholder";
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID().replace(/-/g, "").slice(0, 22)
        : `demo-${Date.now()}`;
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function resetDemoAlertSessionId(): string {
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 22)
      : `demo-${Date.now()}`;
  localStorage.setItem(SESSION_KEY, id);
  return id;
}
