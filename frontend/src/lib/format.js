// Deterministic placeholder swatch for a tile until image_path resolves to
// a real raster crop server-side. Same tile_id always renders the same color.
export function swatchColor(tileId, offset) {
  let h = offset;
  for (let i = 0; i < tileId.length; i++) h = (h * 31 + tileId.charCodeAt(i)) % 360;
  return `hsl(${h}, 22%, ${offset === 0 ? 24 : 30}%)`;
}

// score is a cosine similarity [0,1] straight off SearchResult. This split
// is a UI-side read against the panel's own threshold — the backend does
// not send a verdict field; A's SFAS gate decides the real cutoff server-side.
export function verdictFor(score, threshold) {
  if (score < threshold) return "false_alarm";
  if (score < threshold + 0.15) return "pending";
  return "verified";
}

export const VERDICT_STYLE = {
  verified: { label: "Verified", dot: "#8FAE7A", text: "text-verifiedText", ring: "ring-verified/30" },
  false_alarm: { label: "Below threshold", dot: "#C1523A", text: "text-dangerText", ring: "ring-danger/30" },
  pending: { label: "Pending", dot: "#D4A24C", text: "text-amberText", ring: "ring-amber/30" },
};

export const STATUS_STYLE = {
  approved: "text-verifiedText bg-verified/10 ring-1 ring-verified/25",
  rejected: "text-dangerText bg-danger/10 ring-1 ring-danger/25",
  pending: "text-amberText bg-amber/10 ring-1 ring-amber/25",
};
