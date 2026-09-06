import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

const STATUS_META = {
  ok:         { icon: CheckCircle2,  color: "text-emerald-400", bg: "bg-emerald-900/20", ring: "ring-emerald-500/30", label: "OK" },
  warn:       { icon: AlertTriangle, color: "text-amber-400",   bg: "bg-amber-900/20",   ring: "ring-amber-500/30",   label: "WARN" },
  suppressed: { icon: XCircle,       color: "text-rose-400",    bg: "bg-rose-900/20",    ring: "ring-rose-500/30",    label: "SUPPRESSED" },
  error:      { icon: XCircle,       color: "text-rose-500",    bg: "bg-rose-950/30",    ring: "ring-rose-600/30",    label: "ERROR" },
};

function StepRow({ entry, index }) {
  const [open, setOpen] = useState(false);
  const meta = STATUS_META[entry.status] || STATUS_META.ok;
  const Icon = meta.icon;

  const hasValue = entry.value !== null && entry.value !== undefined;

  return (
    <div
      className={`rounded border ${meta.ring} ring-1 ${meta.bg} transition-all duration-200`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-left group"
        disabled={!hasValue}
      >
        {/* Step badge */}
        <span className="shrink-0 w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center font-mono text-[9px] text-zinc-400">
          {entry.step}
        </span>

        {/* Status icon */}
        <Icon size={13} className={`shrink-0 ${meta.color}`} />

        {/* Name */}
        <span className="flex-1 font-mono text-[11px] text-zinc-200 font-medium truncate">
          {entry.name}
        </span>

        {/* Status chip */}
        <span className={`shrink-0 font-mono text-[9px] px-1.5 py-0.5 rounded ${meta.color} bg-zinc-900/60 ring-1 ${meta.ring}`}>
          {meta.label}
        </span>

        {/* Expand chevron */}
        {hasValue && (
          open
            ? <ChevronDown size={12} className="shrink-0 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
            : <ChevronRight size={12} className="shrink-0 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
        )}
      </button>

      {/* Detail row — always visible */}
      {entry.detail && (
        <p className="px-3 pb-2 font-mono text-[10px] text-zinc-400 leading-relaxed">
          {entry.detail}
        </p>
      )}

      {/* Expanded value payload */}
      {open && hasValue && (
        <div className="mx-3 mb-2 rounded bg-zinc-950/60 border border-zinc-800 p-2 overflow-x-auto">
          <pre className="font-mono text-[10px] text-zinc-300 leading-relaxed whitespace-pre-wrap break-words">
            {JSON.stringify(entry.value, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function PipelineInspector({ processingLog, rawAnalysis }) {
  const [panelOpen, setPanelOpen] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  if (!processingLog || processingLog.length === 0) return null;

  const suppressedCount = processingLog.filter((e) => e.status === "suppressed").length;
  const warnCount = processingLog.filter((e) => e.status === "warn").length;

  return (
    <div className="mt-4 border border-zinc-800 rounded bg-zinc-900/40">
      {/* Header toggle */}
      <button
        onClick={() => setPanelOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-zinc-800/40 transition-colors rounded-t"
      >
        <div className="flex items-center gap-2">
          <Info size={12} className="text-indigo-400" />
          <span className="font-mono text-[11px] font-semibold text-indigo-300 tracking-wider uppercase">
            Pipeline Inspector
          </span>
          <span className="font-mono text-[10px] text-zinc-500">
            {processingLog.length} steps
          </span>
          {suppressedCount > 0 && (
            <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-rose-900/30 text-rose-400 ring-1 ring-rose-500/30">
              {suppressedCount} suppressed
            </span>
          )}
          {warnCount > 0 && (
            <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-amber-900/30 text-amber-400 ring-1 ring-amber-500/30">
              {warnCount} warn
            </span>
          )}
        </div>
        {panelOpen
          ? <ChevronDown size={13} className="text-zinc-500" />
          : <ChevronRight size={13} className="text-zinc-500" />
        }
      </button>

      {panelOpen && (
        <div className="px-3 pb-3 space-y-1.5">
          {/* Vertical step list */}
          {processingLog.map((entry, i) => (
            <StepRow key={entry.step} entry={entry} index={i} />
          ))}

          {/* Raw JSON toggle */}
          {rawAnalysis && (
            <div className="pt-1">
              <button
                onClick={() => setShowRaw((v) => !v)}
                className="font-mono text-[10px] text-zinc-500 hover:text-zinc-300 underline underline-offset-2 transition-colors"
              >
                {showRaw ? "Hide" : "Show"} raw API response
              </button>
              {showRaw && (
                <div className="mt-2 rounded bg-zinc-950 border border-zinc-800 p-2 overflow-x-auto max-h-64">
                  <pre className="font-mono text-[10px] text-zinc-300 whitespace-pre-wrap break-words">
                    {JSON.stringify(rawAnalysis, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
