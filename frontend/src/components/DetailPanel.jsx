import { Check, ShieldAlert, ShieldCheck, X } from "lucide-react";
import SplitSlider from "./SplitSlider.jsx";
import { verdictFor, VERDICT_STYLE } from "../lib/format.js";

export default function DetailPanel({ selected, before, threshold, onApprove, onReject }) {
  if (!selected) {
    return (
      <aside className="border-t border-border p-4 lg:border-l lg:border-t-0">
        <p className="font-mono text-xs text-faint">Select a candidate to inspect.</p>
      </aside>
    );
  }

  const verdict = verdictFor(selected.score, threshold);
  const vs = VERDICT_STYLE[verdict];

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
        </div>

        <SplitSlider before={before.metadata} after={selected.metadata} />

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

        <div className="flex gap-2 pt-1">
          <button
            onClick={onApprove}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-verified/40 bg-verified/10 py-1.5 font-cond text-xs font-semibold tracking-wide text-verifiedText hover:bg-verified/15"
          >
            <Check size={13} />
            Approve
          </button>
          <button
            onClick={onReject}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-danger/40 bg-danger/10 py-1.5 font-cond text-xs font-semibold tracking-wide text-dangerText hover:bg-danger/15"
          >
            <X size={13} />
            Reject
          </button>
        </div>
      </div>
    </aside>
  );
}
