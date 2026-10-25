import type { CustomerNetworkContext } from "./networkContextTypes";

export function friendlyDeviceCategory(deviceType: string): string {
  const t = deviceType.toLowerCase();
  if (t.includes("recloser")) return "protective device (recloser)";
  if (t.includes("fuse")) return "protective device (fuse)";
  if (t.includes("circuit breaker")) return "circuit protection";
  if (t.includes("distribution")) return "distribution transformer";
  if (t.includes("step")) return "step transformer";
  if (t.includes("transformer") || t.includes("xfrm")) return "transformer";
  return "network equipment";
}

export function summarizeServiceLocation(ctx: CustomerNetworkContext): string[] {
  const lines: string[] = [];
  const clip = ctx.customer_clip;
  if (clip?.city && clip?.state) {
    lines.push(`Service area: ${clip.city}, ${clip.state}.`);
  }
  if (clip?.kind_of_se) {
    lines.push(`Service type recorded as ${String(clip.kind_of_se).toLowerCase()}.`);
  }
  if (ctx.premise.circuit_id) {
    lines.push(
      `Your anonymized service record is associated with utility circuit identifier ${ctx.premise.circuit_id} in our index.`,
    );
  }
  if (ctx.service_transformer) {
    lines.push(
      "Our customer records include a reference to a service transformer location that matches equipment in the utility network index.",
    );
  } else if (ctx.missing_or_partial.includes("customer_clip_shapefile_unavailable")) {
    lines.push(
      "Detailed customer shapefile attributes are not available in this environment; only indexed network data is shown.",
    );
  } else {
    lines.push(
      "We could not load a recorded service transformer location for this premise from customer GIS.",
    );
  }
  return lines;
}

export function summarizeNetworkKnowledge(ctx: CustomerNetworkContext): string[] {
  const lines: string[] = [];
  const categories = new Map<string, number>();
  for (const u of ctx.upstream_devices) {
    const label = friendlyDeviceCategory(u.device.device_type);
    categories.set(label, (categories.get(label) ?? 0) + 1);
  }
  const parts = [...categories.entries()].map(([k, n]) => `${n} ${k}${n > 1 ? "s" : ""}`);
  if (parts.length) {
    lines.push(
      `Our records associate your service location with ${parts.join(", ")} in the upstream dependency index.`,
    );
  }
  lines.push(
    "These associations come from the utility’s upstream equipment list for your premise. They are not a step-by-step map of wires on the ground.",
  );
  if (ctx.upstream_is_ordered_path === false) {
    lines.push(
      "The order of devices in our index does not represent a confirmed path from your meter to each piece of equipment.",
    );
  }
  lines.push(ctx.disclaimer);
  return lines;
}

export function hasIncompleteData(ctx: CustomerNetworkContext): boolean {
  return (
    ctx.missing_or_partial.length > 0 ||
    !ctx.service_transformer ||
    ctx.upstream_device_count === 0
  );
}

export function incompleteDataMessage(ctx: CustomerNetworkContext): string | null {
  if (ctx.upstream_device_count === 0) {
    return "No upstream equipment memberships were found for this premise in the network index.";
  }
  if (ctx.missing_or_partial.includes("customer_clip_record_not_found_for_premise")) {
    return "This premise exists in the network index but has no matching customer shapefile row.";
  }
  return ctx.missing_or_partial.length ? "Some optional data sources were unavailable." : null;
}
