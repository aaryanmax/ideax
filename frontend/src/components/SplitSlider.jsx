import { useCallback, useRef, useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { swatchColor } from "../lib/format.js";

const GRID_BG =
  "repeating-linear-gradient(0deg, rgba(255,255,255,0.04) 0px, rgba(255,255,255,0.04) 1px, transparent 1px, transparent 24px), repeating-linear-gradient(90deg, rgba(255,255,255,0.04) 0px, rgba(255,255,255,0.04) 1px, transparent 1px, transparent 24px)";

// Takes two TileMetadata objects — the shape a tile_id_t1 / tile_id_t2
// pair resolves to once /change is wired up.
export default function SplitSlider({ before, after }) {
  const [pos, setPos] = useState(50);
  const trackRef = useRef(null);
  const dragging = useRef(false);

  const setFromClientX = useCallback((clientX) => {
    const track = trackRef.current;
    if (!track) return;
    const rect = track.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPos(Math.min(100, Math.max(0, pct)));
  }, []);

  const onPointerDown = (e) => {
    dragging.current = true;
    setFromClientX(e.clientX);
  };
  const onPointerMove = (e) => {
    if (!dragging.current) return;
    setFromClientX(e.clientX);
  };
  const endDrag = () => {
    dragging.current = false;
  };

  return (
    <div className="space-y-2">
      <div
        ref={trackRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
        className="relative h-56 w-full cursor-ew-resize select-none overflow-hidden rounded-sm border border-border"
        style={{ touchAction: "none" }}
      >
        {/* AFTER — base layer. Production: <img src={`/tiles/${after.image_path}`} /> */}
        <div className="absolute inset-0" style={{ backgroundColor: swatchColor(after.tile_id, 1), backgroundImage: GRID_BG }} />
        <span className="absolute bottom-2 right-2 rounded-sm bg-black/50 px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-ink/80">
          AFTER · {after.acquisition_date}
        </span>

        {/* BEFORE — clipped */}
        <div className="absolute inset-0 overflow-hidden" style={{ width: `${pos}%` }}>
          <div
            className="absolute inset-y-0 left-0"
            style={{
              width: trackRef.current ? trackRef.current.getBoundingClientRect().width : "100%",
              backgroundColor: swatchColor(before.tile_id, 0),
              backgroundImage: GRID_BG,
            }}
          />
          <span className="absolute bottom-2 left-2 rounded-sm bg-black/50 px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-ink/80">
            BEFORE · {before.acquisition_date}
          </span>
        </div>

        <div className="absolute inset-y-0 w-px bg-amber" style={{ left: `${pos}%` }}>
          <div className="absolute left-1/2 top-1/2 flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-amber bg-base">
            <SlidersHorizontal size={12} className="rotate-90 text-amber" />
          </div>
        </div>
      </div>
      <p className="font-mono text-[10px] text-muted">
        {before.tile_id} → {after.tile_id} · bitemporal delta rendered client-side, no tile leaves the device.
      </p>
    </div>
  );
}
