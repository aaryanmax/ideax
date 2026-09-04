import { ChevronRight, GitCommitHorizontal } from "lucide-react";
import { STATUS_STYLE } from "../lib/format.js";

export default function CommitLog({ commits }) {
  return (
    <div className="tour-audit mt-6">
      <h2 className="mb-3 font-cond text-sm font-semibold tracking-wide text-ink">Geospatial commits</h2>
      <div className="divide-y divide-border rounded-sm border border-border">
        {commits.map((c) => {
          const statusKey = (c.status || "pending").toLowerCase();
          const patchId = c.patch_id || c.tile_id || `patch_${c.id}`;
          const analyst = c.analyst_id || c.analyst || "analyst";
          const rawTs = c.reviewed_at || c.timestamp || c.ts || "recent";
          const formattedTs = typeof rawTs === "string" && rawTs.includes("T")
            ? rawTs.split("T")[1]?.slice(0, 8) || rawTs.slice(0, 10)
            : String(rawTs).slice(0, 19);
          const commitLabel = c.hash_value ? c.hash_value.slice(0, 7) : (String(c.id).startsWith("c-") ? c.id : `c-${c.id}`);

          return (
            <div key={c.id ?? Math.random()} className="flex items-center justify-between px-3 py-2">
              <div className="flex min-w-0 items-center gap-2">
                <GitCommitHorizontal size={13} className="shrink-0 text-faint" />
                <span className="font-mono text-[11px] text-[#B8BFC9]" title={c.hash_value || commitLabel}>{commitLabel}</span>
                <ChevronRight size={12} className="shrink-0 text-borderHover" />
                <span className="truncate font-mono text-[11px] text-muted">{patchId}</span>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="font-mono text-[10px] text-faint">{formattedTs}</span>
                <span className="font-mono text-[10px] text-faint">analyst {analyst}</span>
                <span className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] capitalize ${STATUS_STYLE[statusKey] || STATUS_STYLE.pending}`}>
                  {statusKey}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
