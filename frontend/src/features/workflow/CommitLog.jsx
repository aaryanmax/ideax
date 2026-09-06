import { ChevronRight, GitCommitHorizontal, Search, Download } from "lucide-react";
import { STATUS_STYLE } from "../../lib/format.js";
import { useState } from "react";
import { exportProvenance } from "../../lib/api.js";

export default function CommitLog({ commits }) {
  const [search, setSearch] = useState("");

  const filteredCommits = commits.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const patchId = (c.patch_id || c.tile_id || `patch_${c.id}`).toLowerCase();
    const analyst = (c.analyst_id || c.analyst || "analyst").toString().toLowerCase();
    const commitLabel = c.hash_value ? c.hash_value.slice(0, 7) : (String(c.id).startsWith("c-") ? String(c.id) : `c-${c.id}`);
    const statusKey = (c.status || "pending").toLowerCase();
    
    return patchId.includes(q) || analyst.includes(q) || commitLabel.includes(q) || statusKey.includes(q);
  });

  return (
    <div className="tour-audit mt-6">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="font-cond text-sm font-semibold tracking-wide text-ink">Geospatial commits</h2>
          <button
            onClick={() => exportProvenance().catch(err => alert("Failed to export provenance: " + err.message))}
            className="flex items-center gap-1 rounded bg-zinc-900 px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-emerald-400 ring-1 ring-emerald-500/30 hover:bg-emerald-950/30 transition-colors"
            title="Download full processing provenance as GeoJSON"
          >
            <Download size={10} />
            Export
          </button>
        </div>
        <div className="relative">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-faint" />
          <input
            type="text"
            placeholder="Search commits..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-48 rounded-sm border border-border bg-ground px-2 py-1 pl-6 text-xs text-ink placeholder:text-muted focus:border-borderHover focus:outline-none"
          />
        </div>
      </div>
      <div className="max-h-[300px] overflow-y-auto">
        <div className="divide-y divide-border rounded-sm border border-border">
          {filteredCommits.map((c) => {
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
          {filteredCommits.length === 0 && (
            <div className="px-3 py-4 text-center text-xs text-muted">
              No commits found matching "{search}"
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
