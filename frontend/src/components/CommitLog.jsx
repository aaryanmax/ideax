import { ChevronRight, GitCommitHorizontal } from "lucide-react";
import { STATUS_STYLE } from "../lib/format.js";

export default function CommitLog({ commits }) {
  return (
    <div className="mt-6">
      <h2 className="mb-3 font-cond text-sm font-semibold tracking-wide text-ink">Geospatial commits</h2>
      <div className="divide-y divide-border rounded-sm border border-border">
        {commits.map((c) => (
          <div key={c.id} className="flex items-center justify-between px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <GitCommitHorizontal size={13} className="shrink-0 text-faint" />
              <span className="font-mono text-[11px] text-[#B8BFC9]">{c.id}</span>
              <ChevronRight size={12} className="shrink-0 text-borderHover" />
              <span className="truncate font-mono text-[11px] text-muted">{c.tile_id}</span>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="font-mono text-[10px] text-faint">{c.ts}</span>
              <span className="font-mono text-[10px] text-faint">analyst {c.analyst}</span>
              <span className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] capitalize ${STATUS_STYLE[c.status]}`}>
                {c.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
