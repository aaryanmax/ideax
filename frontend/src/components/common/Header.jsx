import { Radar, HelpCircle } from "lucide-react";

export default function Header({ nResults, executionMs, onStartTour }) {
  return (
    <header className="flex items-center justify-between border-b border-border px-5 py-3">
      <div className="flex items-center gap-3">
        <Radar size={18} className="text-amber" />
        <div>
          <h1 className="font-cond text-[15px] font-semibold tracking-wide text-ink">
            VAYU-CHRONICLE
          </h1>
          <p className="font-mono text-[10px] text-muted">
            semantic retrieval · multi-temporal change intelligence
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4 font-mono text-[10px] text-muted">
        <button onClick={onStartTour} className="flex items-center gap-1.5 hover:text-ink transition-colors">
          <HelpCircle size={14} />
          <span>TUTORIAL</span>
        </button>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-verified" />
          AIR-GAPPED
        </span>
        <span>{nResults} results</span>
        <span>{executionMs.toFixed(1)}ms</span>
      </div>
    </header>
  );
}
