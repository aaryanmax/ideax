import { Search, Satellite } from "lucide-react";

export default function SearchPanel({
  query,
  onQueryChange,
  minConfidence,
  onMinConfidenceChange,
  sensors,
  sensorFilter,
  onSensorFilterChange,
}) {
  return (
    <aside className="border-b border-border p-4 space-y-6 lg:border-b-0 lg:border-r">
      <div>
        <label className="font-cond text-xs font-semibold tracking-wide text-muted">Query</label>
        <div className="mt-2 flex items-center gap-2 rounded-sm border border-border bg-panel px-2.5 py-2">
          <Search size={14} className="shrink-0 text-muted" />
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="describe the change, e.g. new structure near tree line"
            className="w-full bg-transparent text-sm text-ink placeholder:text-faint outline-none"
          />
        </div>
        <p className="mt-1.5 font-mono text-[10px] text-faint">natural language or paste a tile_id</p>
      </div>

      <div>
        <div className="flex items-center justify-between">
          <label className="font-cond text-xs font-semibold tracking-wide text-muted">Min. score</label>
          <span className="font-mono text-[11px] text-amber">{minConfidence.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={0.95}
          step={0.01}
          value={minConfidence}
          onChange={(e) => onMinConfidenceChange(parseFloat(e.target.value))}
          className="mt-3 w-full accent-amber"
        />
        <p className="mt-1.5 font-mono text-[10px] text-faint">maps to confidence_threshold on /change</p>
      </div>

      <div>
        <label className="font-cond text-xs font-semibold tracking-wide text-muted">sensor_filter</label>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {sensors.map((s) => (
            <button
              key={s}
              onClick={() => onSensorFilterChange(sensorFilter === s ? null : s)}
              className={`flex items-center gap-1 rounded-sm border px-2 py-1 font-mono text-[10px] transition-colors ${
                sensorFilter === s
                  ? "border-amber/50 bg-amber/10 text-amberText"
                  : "border-border text-[#B8BFC9] hover:border-borderHover"
              }`}
            >
              <Satellite size={10} className="text-sensorAccent" />
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <p className="font-cond text-xs font-semibold tracking-wide text-muted">SFAS gate</p>
        <p className="mt-1.5 font-mono text-[10px] leading-relaxed text-faint">
          Score below threshold is treated as suppressed here client-side —
          the gate ultimately decides this server-side on /change.
        </p>
      </div>
    </aside>
  );
}
