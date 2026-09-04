import { Minus, Plus, Radar } from "lucide-react";

const MIN_SCALE = 85;
const MAX_SCALE = 130;
const STEP = 5;

export default function Header({ nResults, executionMs, fontScale, onFontScaleChange }) {
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

      <div className="flex items-center gap-4">
        <div
          className="flex items-center gap-1 rounded-sm border border-border px-1 py-1"
          role="group"
          aria-label="Text size"
        >
          <button
            type="button"
            onClick={() => onFontScaleChange(Math.max(MIN_SCALE, fontScale - STEP))}
            disabled={fontScale <= MIN_SCALE}
            aria-label="Decrease text size"
            className="rounded-sm p-1 text-muted hover:bg-panelAlt hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <Minus size={12} />
          </button>
          <span className="w-9 text-center font-mono text-[10px] text-muted">{fontScale}%</span>
          <button
            type="button"
            onClick={() => onFontScaleChange(Math.min(MAX_SCALE, fontScale + STEP))}
            disabled={fontScale >= MAX_SCALE}
            aria-label="Increase text size"
            className="rounded-sm p-1 text-muted hover:bg-panelAlt hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <Plus size={12} />
          </button>
        </div>

        <div className="flex items-center gap-4 font-mono text-[10px] text-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-verified" />
            AIR-GAPPED
          </span>
          <span>{nResults} results</span>
          <span>{executionMs.toFixed(1)}ms</span>
        </div>
      </div>
    </header>
  );
}
