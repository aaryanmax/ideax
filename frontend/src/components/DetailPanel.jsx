import { useState } from "react";
import { Check, ShieldAlert, ShieldCheck, X, Loader2 } from "lucide-react";
import SplitSlider from "./SplitSlider.jsx";
import { verdictFor, VERDICT_STYLE } from "../lib/format.js";
import { commitTarget } from "../lib/api.js";

export default function DetailPanel({
  selected,
  before,
  threshold,
  onApprove,
  onReject,
  activeAnalysis,
  onCommitSuccess,
}) {
  const [isCommitting, setIsCommitting] = useState(false);

  if (!selected) {
    return (
      <aside className="border-t border-border p-4 lg:border-l lg:border-t-0">
        <p className="font-mono text-xs text-faint">Select a candidate to inspect.</p>
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
          {activeAnalysis?.classification && (
            <div className="mt-2 inline-flex items-center gap-1.5 rounded bg-emerald-900/30 px-2 py-1 text-[10px] font-semibold text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
              <span className="uppercase">{activeAnalysis.classification.classification}</span>
              <span className="opacity-75">{(activeAnalysis.classification.confidence * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>

        <SplitSlider candidate={selected} before={before?.metadata} after={selected.metadata} />

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

        {activeAnalysis?.spotrep && (
          <div className="mt-4 p-3 bg-zinc-950 border border-emerald-900/60 rounded shadow-inner">
            <div className="text-[10px] text-emerald-500 font-bold uppercase mb-1.5 tracking-wider">
              Generated SPOTREP (DGIS-Standard)
            </div>
            <pre className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap font-medium text-emerald-400">
              {activeAnalysis.spotrep}
            </pre>
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <button
            disabled={isCommitting}
            onClick={() => handleDecision("APPROVED")}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-verified/40 bg-verified/10 py-1.5 font-cond text-xs font-semibold tracking-wide text-verifiedText hover:bg-verified/15 disabled:opacity-50"
          >
            {isCommitting ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
            Approve
          </button>
          <button
            disabled={isCommitting}
            onClick={() => handleDecision("REJECTED")}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-danger/40 bg-danger/10 py-1.5 font-cond text-xs font-semibold tracking-wide text-dangerText hover:bg-danger/15 disabled:opacity-50"
          >
            {isCommitting ? <Loader2 size={13} className="animate-spin" /> : <X size={13} />}
            Reject
          </button>
        </div>
      </div>
    </aside>
  );
}

