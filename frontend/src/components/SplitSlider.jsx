import React, { useState } from 'react';

export default function SplitSlider({ candidate, before, after }) {
  const [sliderPos, setSliderPos] = useState(50);

  const activeCandidate = candidate || after || before;
  if (!activeCandidate) return null;

  const tileId = activeCandidate.tile_id || activeCandidate.patch_id;

  const t1Url = activeCandidate.t1_thumbnail 
    ? (activeCandidate.t1_thumbnail.startsWith("http") 
        ? activeCandidate.t1_thumbnail 
        : `http://localhost:8000${activeCandidate.t1_thumbnail}`)
    : `http://localhost:8000/static/tiles/thumbnails/${tileId}_t1.png`;

  const t2Url = activeCandidate.t2_thumbnail 
    ? (activeCandidate.t2_thumbnail.startsWith("http") 
        ? activeCandidate.t2_thumbnail 
        : `http://localhost:8000${activeCandidate.t2_thumbnail}`)
    : (activeCandidate.thumbnail_url 
        ? (activeCandidate.thumbnail_url.startsWith("http") 
            ? activeCandidate.thumbnail_url 
            : `http://localhost:8000${activeCandidate.thumbnail_url}`)
        : `http://localhost:8000/static/tiles/thumbnails/${tileId}_t2.png`);

  return (
    <div className="relative w-full h-64 bg-zinc-950 rounded border border-zinc-800 overflow-hidden select-none">
      {/* T2 (After / Aug 2026) Background */}
      <img
        src={t2Url}
        alt="Post-Monsoon (Aug 2026)"
        className="absolute inset-0 w-full h-full object-cover"
      />
      <span className="absolute bottom-2 right-2 z-10 px-2 py-0.5 text-[10px] font-mono bg-black/70 text-emerald-400 rounded">
        T2: 2026-08-31
      </span>

      {/* T1 (Before / Feb 2026) Clipped Layer */}
      <img
        src={t1Url}
        alt="Dry Season Baseline (Feb 2026)"
        className="absolute inset-0 w-full h-full object-cover"
        style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)`, willChange: 'clip-path' }}
      />
      <span className="absolute bottom-2 left-2 z-10 px-2 py-0.5 text-[10px] font-mono bg-black/70 text-amber-400 rounded">
        T1: 2026-02-17
      </span>

      {/* Interactive Divider Line */}
      <div
        className="absolute top-0 bottom-0 w-1 bg-emerald-400 cursor-ew-resize z-20 -translate-x-1/2"
        style={{ left: `${sliderPos}%` }}
      >
        <div className="absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 bg-black/50 backdrop-blur-md shadow-lg border-2 border-emerald-400 rounded-full flex items-center justify-center text-xs text-emerald-400">
          ↔
        </div>
      </div>

      {/* Range Input Overlay */}
      <input
        type="range"
        min="0"
        max="100"
        value={sliderPos}
        onChange={(e) => setSliderPos(Number(e.target.value))}
        className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-30"
      />
    </div>
  );
}
