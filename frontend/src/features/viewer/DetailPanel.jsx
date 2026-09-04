import { useState, useEffect } from "react";
import { Check, ShieldAlert, ShieldCheck, X, Loader2 } from "lucide-react";
import SplitSlider from "./SplitSlider.jsx";
import { verdictFor, VERDICT_STYLE } from "../../lib/format.js";
import { commitTarget } from "../../lib/api.js";
import { triggerHaptic } from "../../lib/haptics.js";
import TacticalMap from "./TacticalMap.jsx";

export default function DetailPanel({
  selected,
  before,
  threshold,
  onApprove,
  onReject,
  activeAnalysis,
  onCommitSuccess,
  candidates,
  totalCandidates,
  onSelectCandidate,
  onDiscoverPattern,
  isDiscovering,
  onDatasetFilterChange,
  onFetchReject,
  onFetchSuccess
}) {
  const [isCommitting, setIsCommitting] = useState(false);
  const [isMapExpanded, setIsMapExpanded] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      
      if (e.key === 'Enter' && selected && !isCommitting) {
        e.preventDefault();
        triggerHaptic('approve');
        handleDecision('APPROVED');
      } else if (e.key === 'Backspace' && selected && !isCommitting) {
        e.preventDefault();
        triggerHaptic('reject');
        handleDecision('REJECTED');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selected, isCommitting, activeAnalysis]);

  if (!selected) {
    return (
      <aside className="border-t border-border p-4 lg:border-l lg:border-t-0 min-h-full">
        <div className="flex flex-col items-center justify-center h-full text-zinc-600 space-y-4">
          <div className="tour-viewer w-16 h-16 border border-zinc-700 rounded-full flex items-center justify-center animate-pulse">
            <span className="text-2xl">⌖</span>
          </div>
          <p className="tour-spotrep text-xs font-mono uppercase tracking-widest text-center">Awaiting Sector Selection</p>
        </div>
      </aside>
    );
  }

  const verdict = verdictFor(selected.score, threshold);
  const vs = VERDICT_STYLE[verdict];

  const handleDecision = async (status) => {
    if (!selected || isCommitting) return;
    setIsCommitting(true);
    try {
      const payload = {
        patch_id: selected.tile_id,
        new_status: status,
        analyst_id: "OFFICER_DELHI_01",
        confidence: selected.score,
        latitude: selected.metadata?.latitude ?? 28.5,
        longitude: selected.metadata?.longitude ?? 76.5,
        rationale: activeAnalysis?.classification
          ? `Tactical classification: ${activeAnalysis.classification.classification} (${(activeAnalysis.classification.confidence * 100).toFixed(0)}%)`
          : `Analyst manual decision: ${status}`,
      };

      await commitTarget(payload);

      if (status === "APPROVED" && onApprove) onApprove();
      if (status === "REJECTED" && onReject) onReject();
      if (onCommitSuccess) await onCommitSuccess();
    } catch (err) {
      console.error("Failed to commit target:", err);
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <aside className="border-t border-border p-4 lg:border-l lg:border-t-0">
      <div className="space-y-4">
        <div>
          <div className="flex items-center justify-between gap-2">
            <h3 className="truncate font-cond text-sm font-semibold tracking-wide text-ink" title={selected.tile_id}>
              {selected.tile_id}
            </h3>
            <span className={`flex shrink-0 items-center gap-1 rounded-sm px-1.5 py-0.5 font-mono text-[10px] ring-1 ${vs.ring} ${vs.text}`}>
              {verdict === "false_alarm" ? <ShieldAlert size={10} /> : <ShieldCheck size={10} />}
              {vs.label}
            </span>
          </div>
          <p className="mt-0.5 font-mono text-[10px] text-muted">
            {selected.metadata.latitude.toFixed(3)}, {selected.metadata.longitude.toFixed(3)}
          </p>
          {activeAnalysis ? (
            activeAnalysis.classification && (
              <div className="mt-2 inline-flex items-center gap-1.5 rounded bg-emerald-900/30 px-2 py-1 text-[10px] font-semibold text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
                <span className="uppercase">{activeAnalysis.classification.classification}</span>
                <span className="opacity-75">{(activeAnalysis.classification.confidence * 100).toFixed(0)}%</span>
              </div>
            )
          ) : (
            <div className="mt-2 h-6 w-24 rounded bg-zinc-800/50 animate-pulse" />
          )}
        </div>

        <SplitSlider candidate={selected} before={before?.metadata} after={selected.metadata} />

        {/* Tactical Mini-map Context */}
        <div className="relative w-full h-36 bg-zinc-950 border border-zinc-900 rounded overflow-hidden mt-2">
          <TacticalMap
            candidates={candidates || []}
            total={totalCandidates || 0}
            activeCandidateId={selected.tile_id}
            onSelect={onSelectCandidate}
            threshold={threshold}
            className="h-full w-full"
            style={{ height: "100%" }}
            hideHeader={true}
            isExpanded={false}
            onToggleExpand={() => setIsMapExpanded(true)}
            onDatasetFilterChange={onDatasetFilterChange}
            onFetchReject={onFetchReject}
            onFetchSuccess={onFetchSuccess}
          />
          <div className="absolute top-1 left-1 px-1 text-[9px] font-mono text-zinc-400 uppercase tracking-widest z-[400] pointer-events-none drop-shadow-md bg-black/40 rounded">
            Sector {selected.tile_id.split('_')[1] || '01'}
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-y-2 font-mono text-[10px]">
          <dt className="text-faint">Projection</dt>
          <dd className="text-right text-[#B8BFC9]">WGS84</dd>
          <dt className="text-faint">Sensor</dt>
          <dd className="text-right text-[#B8BFC9]">{selected.metadata.sensor}</dd>
          <dt className="text-faint">Cloud cover</dt>
          <dd className="text-right text-[#B8BFC9]">
            {selected.metadata.cloud_cover_pct != null ? `${selected.metadata.cloud_cover_pct}%` : "n/a"}
          </dd>
          <dt className="text-faint">Pass date</dt>
          <dd className="text-right text-[#B8BFC9]">{selected.metadata.acquisition_date}</dd>
          <dt className="text-faint">score</dt>
          <dd className="text-right text-amber">{selected.score.toFixed(2)}</dd>
        </dl>

        <button
          onClick={() => onDiscoverPattern(selected.tile_id)}
          disabled={isDiscovering}
          className="w-full mt-3 py-2 px-3 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-500/60 hover:border-emerald-400 text-emerald-300 hover:text-emerald-100 rounded text-xs font-mono tracking-wider flex items-center justify-center space-x-2 transition-all shadow-[0_0_10px_rgba(16,185,129,0.15)] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span>{isDiscovering ? '⟳ SCANNING AOR...' : '⌕ DISCOVER ANALOGOUS SITES'}</span>
        </button>

        {activeAnalysis ? (
          activeAnalysis.spotrep ? (
            <div className="tour-spotrep mt-4 p-3 bg-zinc-950 border border-emerald-900/60 rounded shadow-inner">
              <div className="text-[10px] text-emerald-500 font-bold uppercase mb-1.5 tracking-wider">
                Generated SPOTREP (DGIS-Standard)
              </div>
              <pre className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap font-medium text-emerald-400">
                {activeAnalysis.spotrep}
              </pre>
            </div>
          ) : (
            <div className="tour-spotrep mt-4 p-3 bg-zinc-950/50 border border-zinc-800/60 rounded shadow-inner flex items-center justify-center text-zinc-600 font-mono text-xs">
              NO SPOTREP GENERATED
            </div>
          )
        ) : (
          <div className="tour-spotrep mt-4 p-3 bg-zinc-950/50 border border-zinc-800/60 rounded shadow-inner animate-pulse">
            <div className="h-2.5 w-1/2 bg-zinc-800/50 rounded mb-3"></div>
            <div className="space-y-2">
              <div className="h-2 w-full bg-zinc-800/40 rounded"></div>
              <div className="h-2 w-5/6 bg-zinc-800/40 rounded"></div>
              <div className="h-2 w-4/5 bg-zinc-800/40 rounded"></div>
              <div className="h-2 w-2/3 bg-zinc-800/40 rounded"></div>
            </div>
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <button
            disabled={isCommitting}
            onClick={() => { triggerHaptic('approve'); handleDecision("APPROVED"); }}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-verified/40 bg-verified/10 py-1.5 font-cond text-xs font-semibold tracking-wide text-verifiedText hover:bg-verified/15 disabled:opacity-50"
          >
            {isCommitting ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
            Approve
          </button>
          <button
            disabled={isCommitting}
            onClick={() => { triggerHaptic('reject'); handleDecision("REJECTED"); }}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-danger/40 bg-danger/10 py-1.5 font-cond text-xs font-semibold tracking-wide text-dangerText hover:bg-danger/15 disabled:opacity-50"
          >
            {isCommitting ? <Loader2 size={13} className="animate-spin" /> : <X size={13} />}
            Reject
          </button>
        </div>
      </div>

      {/* Fullscreen Map Modal */}
      {isMapExpanded && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 md:p-8">
           <div className="w-full max-w-6xl h-[80vh] bg-base rounded-md border border-border shadow-2xl flex flex-col overflow-hidden relative animate-in fade-in zoom-in-95 duration-200">
             <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-panel z-10">
               <h2 className="font-cond font-semibold tracking-wide text-ink">Expanded Tactical Map</h2>
               <button onClick={() => setIsMapExpanded(false)} className="text-faint hover:text-ink"><X size={16} /></button>
             </div>
             <div className="flex-1 w-full h-full p-0 relative">
                <TacticalMap
                  candidates={candidates || []}
                  total={totalCandidates || 0}
                  activeCandidateId={selected.tile_id}
                  onSelect={onSelectCandidate}
                  threshold={threshold}
                  className="h-full w-full absolute inset-0"
                  style={{ height: "100%" }}
                  hideHeader={true}
                  isExpanded={true}
                  onToggleExpand={() => setIsMapExpanded(false)}
                  onDatasetFilterChange={onDatasetFilterChange}
                  onFetchReject={onFetchReject}
                  onFetchSuccess={onFetchSuccess}
                />
             </div>
           </div>
        </div>
      )}
    </aside>
  );
}

