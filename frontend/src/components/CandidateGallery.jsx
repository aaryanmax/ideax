import { swatchColor, verdictFor, VERDICT_STYLE } from "../lib/format.js";

export default function CandidateGallery({ results, total, selectedTileId, onSelect, threshold }) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-cond text-sm font-semibold tracking-wide text-ink">Ranked candidates</h2>
        <span className="font-mono text-[10px] text-faint">
          {results.length} of {total}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {results.map((r) => {
          const cv = VERDICT_STYLE[verdictFor(r.score, threshold)];
          const active = r.tile_id === selectedTileId;
          return (
            <button
              key={r.tile_id}
              onClick={() => onSelect(r.tile_id)}
              className={`rounded-sm border p-3 text-left transition-colors ${
                active ? "border-amber/60 bg-panelAlt" : "border-border bg-panel hover:border-borderHover"
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
                <span className="truncate font-mono text-[11px] text-[#B8BFC9]" title={r.tile_id}>
                  {r.tile_id}
                </span>
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
                  {r.metadata.latitude.toFixed(3)}, {r.metadata.longitude.toFixed(3)}
                </span>
                <span>{r.score.toFixed(2)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
