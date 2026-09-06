import React, { useMemo } from 'react';
import { Joyride } from 'react-joyride';
import { Radar, X, ArrowRight, ArrowLeft, Terminal } from 'lucide-react';
import { useSearchStore } from '../../store/useSearchStore.js';

function TacticalTourTooltip({
  backProps,
  closeProps,
  index,
  isLastStep,
  primaryProps,
  skipProps,
  step,
  tooltipProps,
  size,
}) {
  const store = useSearchStore();

  const handlePromptClick = (promptText) => {
    store.applyPrompt(promptText);
  };

  return (
    <div
      {...tooltipProps}
      className="w-[320px] max-w-[calc(100vw-32px)] rounded border border-emerald-500/60 bg-[#171B21] p-4 shadow-[0_12px_45px_rgba(0,0,0,0.85),0_0_20px_rgba(16,185,129,0.15)] text-ink select-none font-sans box-border overflow-hidden"
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-border/80 pb-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <Radar size={15} className="text-emerald-400 animate-spin-slow shrink-0" />
          <span className="font-mono text-[10px] font-bold tracking-widest text-emerald-400 uppercase truncate">
            STEP {String(index + 1).padStart(2, '0')} // {String(size).padStart(2, '0')}
          </span>
        </div>
        <button
          {...closeProps}
          type="button"
          aria-label="Close Tour"
          className="rounded p-0.5 text-muted hover:text-ink hover:bg-panelAlt transition-colors cursor-pointer shrink-0 ml-2"
        >
          <X size={14} />
        </button>
      </div>

      {/* Title & Body */}
      <div className="mt-3">
        {step.title && (
          <h3 className="font-cond text-sm font-semibold tracking-wide text-ink uppercase">
            {step.title}
          </h3>
        )}
        <div className="mt-1.5 font-mono text-xs text-[#B8BFC9] leading-relaxed break-words">
          {step.content}
        </div>

        {/* Interactive Prompt Chips (Step 0) */}
        {index === 0 && (
          <div className="mt-3.5 pt-2.5 border-t border-border/70">
            <div className="flex items-center gap-1.5 mb-2">
              <Terminal size={12} className="text-emerald-400 shrink-0" />
              <span className="font-mono text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">
                Click prompt to test live:
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {[
                { label: "Dense urban settlement", query: "dense urban settlement or buildings" },
                { label: "Seasonal crop fields", query: "seasonal crop fields or agricultural land" },
                { label: "Water body or riverbed", query: "water body or riverbed" }
              ].map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => handlePromptClick(p.query)}
                  className="flex items-center justify-between rounded border border-emerald-500/30 bg-emerald-950/20 px-2.5 py-1.5 font-mono text-[11px] text-emerald-300 hover:border-emerald-400 hover:bg-emerald-900/40 transition-all text-left cursor-pointer group"
                >
                  <span className="truncate">"{p.label}"</span>
                  <span className="text-[10px] text-emerald-500 group-hover:text-emerald-300 ml-1 shrink-0">EXEC ↵</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Navigation Bar */}
      <div className="mt-4 pt-3 border-t border-border/80 flex items-center justify-between gap-2">
        {/* Step Progress Dots */}
        <div className="flex items-center gap-1 shrink-0">
          {Array.from({ length: size }).map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === index
                  ? 'w-4 bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]'
                  : 'w-1.5 bg-zinc-700'
              }`}
            />
          ))}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          {!isLastStep && (
            <button
              {...skipProps}
              type="button"
              className="px-1.5 py-1 font-mono text-[10px] text-muted hover:text-ink transition-colors cursor-pointer"
            >
              Skip
            </button>
          )}

          {index > 0 && (
            <button
              {...backProps}
              type="button"
              className="flex items-center gap-1 rounded border border-border bg-panelAlt px-2 py-1 font-mono text-[10px] text-muted hover:text-ink hover:border-borderHover transition-colors cursor-pointer"
            >
              <ArrowLeft size={10} />
              <span>Back</span>
            </button>
          )}

          <button
            {...primaryProps}
            type="button"
            className="flex items-center gap-1 rounded border border-emerald-500/80 bg-emerald-950/60 px-2.5 py-1 font-mono text-[10px] font-semibold text-emerald-300 hover:bg-emerald-900 hover:border-emerald-400 hover:text-emerald-200 transition-all shadow-[0_0_12px_rgba(16,185,129,0.2)] cursor-pointer"
          >
            <span>{isLastStep ? 'Finish' : 'Next'}</span>
            {!isLastStep && <ArrowRight size={10} />}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function FieldManualTour({ run, setRun }) {
  const [stepIndex, setStepIndex] = React.useState(0);

  const steps = useMemo(() => [
    {
      target: '.tour-search',
      placement: 'right-start',
      title: "Semantic Query Retrieval",
      content: "Type natural language prompts or select a tactical preset below to retrieve relevant satellite candidates using vector embeddings.",
      skipBeacon: true,
      hideOverlay: true,
    },
    {
      target: '.tour-gallery',
      placement: 'bottom-start',
      title: "Ranked Bitemporal Candidates",
      content: "Satellite patches ranked by multi-modal semantic score. Use Up/Down keyboard arrow keys or click any card to inspect.",
      skipBeacon: true,
      hideOverlay: true,
    },
    {
      target: '.tour-viewer',
      placement: 'left-start',
      title: "Bitemporal Split Comparator",
      content: "Interactive split-screen comparator. Drag the divider handle (↔) horizontally to analyze phenological drift between T1 (Baseline) and T2 (Surveillance).",
      skipBeacon: true,
      hideOverlay: true,
    },
    {
      target: '.tour-spotrep',
      placement: 'left-start',
      title: "Automated AI SPOTREP",
      content: "Zero-shot tactical Situation Report (SPOTREP) providing automated classification, confidence scoring, and vegetative change metrics.",
      skipBeacon: true,
      hideOverlay: true,
    },
    {
      target: '.tour-audit',
      placement: 'top',
      title: "Cryptographic Audit Ledger",
      content: "Immutable verification ledger. Press [Enter] hotkey to record Approved verification, or [Backspace] to Reject sector changes.",
      skipBeacon: true,
      hideOverlay: true,
    }
  ], []);

  React.useEffect(() => {
    if (run) {
      setStepIndex(0);
    }
  }, [run]);

  const handleJoyrideEvent = (data) => {
    const { action, status, type, index } = data;
    const finishedStatuses = ['finished', 'skipped'];

    if (finishedStatuses.includes(status) || action === 'close' || action === 'skip' || type === 'tour:end') {
      setRun(false);
      setStepIndex(0);
    } else if (type === 'step:after') {
      setStepIndex(index + (action === 'prev' ? -1 : 1));
    } else if (type === 'error:target_not_found') {
      // Gracefully advance if a specific target element is temporarily unmounted
      setStepIndex(index + 1);
    }
  };

  return (
    <Joyride
      steps={steps}
      run={run}
      stepIndex={stepIndex}
      continuous
      scrollToFirstStep
      onEvent={handleJoyrideEvent}
      tooltipComponent={TacticalTourTooltip}
      options={{
        skipBeacon: true,
        hideOverlay: true,
        scrollOffset: 70,
        zIndex: 10000,
      }}
      floatingOptions={{
        strategy: 'fixed',
        shiftOptions: {
          padding: 16,
          mainAxis: true,
          crossAxis: true,
        },
        flipOptions: {
          padding: 16,
          fallbackPlacements: ['bottom', 'top', 'left'],
        },
        autoUpdate: {
          elementResize: true,
          ancestorScroll: true,
        },
      }}
    />
  );
}
