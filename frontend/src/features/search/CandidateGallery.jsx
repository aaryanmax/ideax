import { swatchColor, verdictFor, VERDICT_STYLE } from "../../lib/format.js";

export default function CandidateGallery({ results, total, activeCandidateId, onSelect, threshold }) {
  return (
    <div>
      <div className="tour-gallery mb-3 flex items-center justify-between rounded p-1 -m-1">
        <h2 className="font-cond text-sm font-semibold tracking-wide text-ink">Ranked candidates</h2>
        <span className="font-mono text-[10px] text-faint">
          {results.length} of {total}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {results.map((r) => {
          const cv = VERDICT_STYLE[verdictFor(r.score, threshold)];
          const isActive = r.tile_id === activeCandidateId;

          const handleMouseEnter = () => {
            const t1Url = r.t1_thumbnail ? (r.t1_thumbnail.startsWith("http") ? r.t1_thumbnail : `http://localhost:8000${r.t1_thumbnail}`) : `http://localhost:8000/static/tiles/thumbnails/${r.tile_id}_t1.png`;
            const t2Url = r.t2_thumbnail ? (r.t2_thumbnail.startsWith("http") ? r.t2_thumbnail : `http://localhost:8000${r.t2_thumbnail}`) : (r.thumbnail_url ? (r.thumbnail_url.startsWith("http") ? r.thumbnail_url : `http://localhost:8000${r.thumbnail_url}`) : `http://localhost:8000/static/tiles/thumbnails/${r.tile_id}_t2.png`);
            new Image().src = t1Url;
            new Image().src = t2Url;
          };

          return (
            <button
              key={r.tile_id}
              onClick={() => onSelect(r.tile_id)}
              onMouseEnter={handleMouseEnter}
              className={`rounded-sm bg-panel p-3 text-left transition-all duration-200 cursor-pointer border ${
                isActive ? 'ring-2 ring-emerald-500 border-transparent shadow-[0_0_15px_rgba(16,185,129,0.2)]' : 'border-zinc-800 hover:border-zinc-600'
              }`}
            >
              <div className="relative h-24 w-full overflow-hidden rounded-sm border border-border bg-zinc-900">
                {r.thumbnail_url ? (
                  <img
                    src={r.thumbnail_url}
                    alt={r.tile_id}
                    className="h-full w-full object-cover"
                    loading="lazy"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                ) : null}
                <div
                  className={`h-full w-full ${r.thumbnail_url ? "hidden" : "block"}`}
                  style={{
                    backgroundImage: `linear-gradient(120deg, ${swatchColor(r.tile_id, 0)} 0%, ${swatchColor(
                      r.tile_id,
                      0
                    )} 48%, ${swatchColor(r.tile_id, 1)} 52%, ${swatchColor(r.tile_id, 1)} 100%)`,
                  }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="truncate font-mono text-[11px] text-[#B8BFC9]" title={r.tile_id}>
                    {r.tile_id}
                  </span>
                  {r.cluster_id !== undefined && (
                    <span className={`flex shrink-0 items-center px-1.5 py-0.5 rounded-sm font-mono text-[9px] font-bold tracking-wider ${
                      r.cluster_id === 0 ? 'bg-emerald-950/80 text-emerald-400 ring-1 ring-emerald-500/50' :
                      r.cluster_id === 1 ? 'bg-cyan-950/80 text-cyan-400 ring-1 ring-cyan-500/50' :
                      r.cluster_id === -1 ? 'bg-amber-950/40 text-amber-500/80 ring-1 ring-amber-500/40 border-dashed' :
                      'bg-indigo-950/80 text-indigo-400 ring-1 ring-indigo-500/50'
                    }`}>
                      {r.cluster_callsign}
                    </span>
                  )}
                </div>
                <span
                  className={`flex shrink-0 items-center gap-1 rounded-sm px-1.5 py-0.5 font-mono text-[10px] ring-1 ${cv.ring} ${cv.text}`}
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: cv.dot }} />
                  {cv.label}
                </span>
              </div>
              <p className="mt-1 truncate text-xs text-muted">
                {r.metadata.sensor} · {r.metadata.acquisition_date}
              </p>
              <div className="mt-1.5 flex items-center justify-between font-mono text-[10px] text-faint">
                <span>
                  {r.metadata?.latitude?.toFixed(3) ?? "0.000"}, {r.metadata?.longitude?.toFixed(3) ?? "0.000"}
                </span>
                <span>{r.score?.toFixed(2) ?? "0.00"}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
