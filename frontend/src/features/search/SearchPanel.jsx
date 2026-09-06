import { Search, Satellite } from "lucide-react";
import { useRef, useEffect } from "react";

const SAMPLE_PROMPTS = [
  { label: "Urban Settlements", query: "dense urban settlement or buildings" },
  { label: "Crop Fields", query: "seasonal crop fields or agricultural land" },
  { label: "Water / Riverbed", query: "water body or riverbed" },
];

export default function SearchPanel({
  query,
  onQueryChange,
  onApplyPrompt,
  minConfidence,
  onMinConfidenceChange,
  sensors,
  sensorFilter,
  onSensorFilterChange,
  datasetFilter,
  onDatasetFilterChange,
  availableDatasets = [],
}) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [query]);

  const handlePromptSelect = (promptText) => {
    if (onApplyPrompt) {
      onApplyPrompt(promptText);
    } else {
      onQueryChange(promptText);
    }
  };

  return (
    <aside className="border-b border-border p-4 space-y-6 lg:border-b-0 lg:border-r">
      <div>
        <label className="font-cond text-xs font-semibold tracking-wide text-muted">Dataset / Region</label>
        <div className="mt-2">
          <select
            value={datasetFilter}
            onChange={(e) => onDatasetFilterChange(e.target.value)}
            className="w-full rounded-sm border border-border bg-panel px-2.5 py-2 font-mono text-xs text-ink outline-none transition-colors hover:border-borderHover focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50"
          >
            {availableDatasets.map((ds) => (
              <option key={ds.value} value={ds.value}>
                {ds.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="tour-search rounded p-1 -m-1 transition-colors">
        <div className="flex items-center justify-between">
          <label className="font-cond text-xs font-semibold tracking-wide text-muted">Tactical Query Prompt</label>
          <span className="font-mono text-[9px] text-emerald-400/80 uppercase tracking-wider">Semantic Retr</span>
        </div>
        <div className="mt-2 flex items-center gap-2 rounded-sm border border-border bg-panel px-2.5 py-2 focus-within:border-emerald-500/60 focus-within:ring-1 focus-within:ring-emerald-500/40">
          <Search size={14} className="shrink-0 text-muted" />
          <textarea
            ref={textareaRef}
            rows={1}
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handlePromptSelect(query);
              }
            }}
            placeholder="describe the change, e.g. dense urban settlement"
            className="w-full bg-transparent text-sm text-ink placeholder:text-faint outline-none resize-none overflow-hidden leading-relaxed font-mono"
          />
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SAMPLE_PROMPTS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => handlePromptSelect(p.query)}
              className="rounded border border-border/70 bg-panelAlt px-1.5 py-0.5 font-mono text-[9px] text-muted hover:border-emerald-500/60 hover:text-emerald-300 hover:bg-emerald-950/30 transition-all cursor-pointer"
            >
              + {p.label}
            </button>
          ))}
        </div>
        <p className="mt-1.5 font-mono text-[10px] text-faint">natural language prompt or paste a tile_id</p>
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
