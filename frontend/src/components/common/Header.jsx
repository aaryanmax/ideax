import { useState, useEffect, useRef } from "react";
import { 
  HelpCircle, 
  Monitor, 
  Radar, 
  RotateCcw, 
  X, 
  ShieldCheck, 
  Globe, 
  Menu, 
  Layers, 
  MousePointerClick, 
  DownloadCloud,
  Database,
  Maximize2,
  Minimize2
} from "lucide-react";
import { useSearchStore } from "../../store/useSearchStore.js";
import { triggerHaptic } from "../../lib/haptics.js";
import OfflineRegionManager from "../OfflineRegionManager.jsx";
import DatasetStudioModal from "../../features/workflow/DatasetStudioModal.jsx";

export default function Header({ nResults, executionMs, onStartTour }) {
  const { 
    uiScale, 
    increaseUiScale, 
    decreaseUiScale, 
    resetUiScale, 
    setUiScale,
    mapMode, 
    setMapMode, 
    vectorLayers, 
    toggleVectorLayer,
    showTooltips,
    setShowTooltips
  } = useSearchStore();

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isOfflineManagerOpen, setIsOfflineManagerOpen] = useState(false);
  const [isDatasetStudioOpen, setIsDatasetStudioOpen] = useState(false);
  const menuRef = useRef(null);
  const buttonRef = useRef(null);

  // Close menu on click outside or Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isMenuOpen) {
        setIsMenuOpen(false);
      }
    };
    const handleClickOutside = (e) => {
      if (
        menuRef.current && 
        !menuRef.current.contains(e.target) && 
        buttonRef.current && 
        !buttonRef.current.contains(e.target)
      ) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  const handleToggleMode = (mode) => {
    triggerHaptic("scan");
    setMapMode(mode);
  };

  const presetScales = [80, 90, 100, 110, 125];

  return (
    <header className="relative flex items-center justify-between border-b border-border bg-base/95 px-5 py-2.5 select-none z-[1000] backdrop-blur-md">
      {/* Left Branding */}
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded border border-amber-500/30 bg-amber-950/20 text-amber shadow-[0_0_10px_rgba(245,158,11,0.15)]">
          <Radar size={18} className="animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-cond text-[15px] font-semibold tracking-wide text-ink">
              VAYU-CHRONICLE
            </h1>
            <span className="rounded bg-emerald-950/60 border border-emerald-500/40 px-1.5 py-0.2 font-mono text-[9px] font-semibold text-emerald-400">
              v1.0 MIL-SPEC
            </span>
          </div>
          <p className="font-mono text-[10px] text-muted leading-tight">
            semantic retrieval · multi-temporal change intelligence
          </p>
        </div>
      </div>

      {/* Right Quick Telemetry & Hamburger Control */}
      <div className="flex items-center gap-3 font-mono text-[10px] text-muted">
        {/* Quick Air-Gapped Mode Status */}
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className={`hidden sm:flex items-center gap-1.5 px-2 py-1 rounded border transition-all cursor-pointer ${
            mapMode === "airgapped"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300 hover:border-emerald-400"
              : "bg-blue-950/40 border-blue-500/40 text-blue-300 hover:border-blue-400"
          }`}
          title="Click to toggle tactical operational controls"
        >
          <span 
            className={`h-1.5 w-1.5 rounded-full ${
              mapMode === "airgapped" ? "bg-emerald-400 animate-pulse" : "bg-blue-400"
            }`} 
          />
          <span className="font-bold tracking-wider">
            {mapMode === "airgapped" ? "AIR-GAPPED HARDENED" : "WAN ONLINE"}
          </span>
        </button>

        {/* Quick Size Display */}
        <div className="hidden md:flex items-center gap-1 rounded border border-border/80 bg-panel px-2 py-0.5 text-ink">
          <span className="text-[9px] text-muted font-bold">SIZE:</span>
          <span className="text-[10px] text-emerald-400 font-bold min-w-[28px] text-center">
            {uiScale}%
          </span>
        </div>

        {/* Telemetry Stats */}
        <div className="hidden lg:flex items-center gap-2 text-zinc-500">
          <span>{nResults} targets</span>
          <span>·</span>
          <span>{(executionMs ?? 0).toFixed(1)}ms</span>
        </div>

        {/* Tutorial Quick Button */}
        <button 
          onClick={onStartTour} 
          className="flex items-center gap-1.5 hover:text-ink transition-colors cursor-pointer px-1.5 py-1 rounded hover:bg-panel"
          title="Launch Field Manual Guided Tour"
        >
          <HelpCircle size={14} className="text-zinc-400 hover:text-amber" />
          <span className="hidden sm:inline font-mono text-[10px]">TUTORIAL</span>
        </button>

        {/* Hamburger Menu Toggle Button */}
        <button
          ref={buttonRef}
          onClick={() => {
            triggerHaptic("click");
            setIsMenuOpen(!isMenuOpen);
          }}
          className={`flex h-7 w-7 items-center justify-center rounded border transition-all cursor-pointer ${
            isMenuOpen
              ? "bg-emerald-950 border-emerald-500 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]"
              : "bg-panel border-border text-zinc-300 hover:text-white hover:border-zinc-500"
          }`}
          title="Tactical System Controls & Settings Menu"
          aria-expanded={isMenuOpen}
        >
          {isMenuOpen ? <X size={15} /> : <Menu size={15} />}
        </button>
      </div>

      {/* Hamburger Dropdown Drawer / Control Panel */}
      {isMenuOpen && (
        <div
          ref={menuRef}
          className="absolute top-[100%] right-4 mt-2 w-[340px] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-4.5rem)] overflow-y-auto overscroll-contain rounded-xl border border-zinc-700/60 bg-zinc-950/98 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.9)] backdrop-blur-xl font-mono text-xs z-50 animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-emerald-950/60 rounded-lg border border-emerald-500/30">
                <ShieldCheck size={13} className="text-emerald-400" />
              </div>
              <span className="font-cond font-bold tracking-[0.12em] text-sm text-zinc-100 uppercase">
                Tactical System Console
              </span>
            </div>
            <button
              onClick={() => setIsMenuOpen(false)}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/80 transition-colors border border-transparent hover:border-zinc-700"
            >
              <X size={12} />
            </button>
          </div>

          <div className="flex flex-col gap-4">
            {/* 1. Network & Map Mode Toggle */}
            <div>
              <div className="flex items-center justify-between text-[10px] font-bold text-zinc-400 uppercase tracking-[0.12em] mb-2.5">
                <span className="flex items-center gap-2">
                  <Globe size={12} className="text-amber-400" />
                  Map Network Protocol
                </span>
                <span className={`text-[9px] px-2 py-0.5 rounded-full border font-bold ${
                  mapMode === "airgapped" 
                    ? "text-emerald-300 bg-emerald-950/60 border-emerald-500/30" 
                    : "text-blue-300 bg-blue-950/60 border-blue-500/30"
                }`}>
                  {mapMode === "airgapped" ? "OFFLINE SECURE" : "ONLINE WAN"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-1.5 p-1 bg-zinc-900/80 rounded-lg border border-zinc-800/80">
                <button
                  type="button"
                  onClick={() => handleToggleMode("airgapped")}
                  className={`flex flex-col items-center py-2.5 px-1 rounded-md text-center transition-all cursor-pointer ${
                    mapMode === "airgapped"
                      ? "bg-emerald-950/90 text-emerald-200 border border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.15)] font-bold"
                      : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60 border border-transparent"
                  }`}
                >
                  <span className="text-[10px] tracking-widest">AIR-GAPPED</span>
                  <span className="text-[8px] opacity-70 mt-0.5">Vector + Local Cache</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleToggleMode("online")}
                  className={`flex flex-col items-center py-2.5 px-1 rounded-md text-center transition-all cursor-pointer ${
                    mapMode === "online"
                      ? "bg-blue-950/90 text-blue-200 border border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.15)] font-bold"
                      : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60 border border-transparent"
                  }`}
                >
                  <span className="text-[10px] tracking-widest">ONLINE WAN</span>
                  <span className="text-[8px] opacity-70 mt-0.5">Remote CartoDB</span>
                </button>
              </div>

              <p className="text-[9px] text-zinc-500 mt-2 leading-relaxed">
                {mapMode === "airgapped"
                  ? "✓ Zero external network calls. Bundled Delhi NCR GeoJSON & procedural dark vector canvas active."
                  : "⚠ Queries remote basemap servers. Will display empty gray tiles if internet disconnects."}
              </p>
            </div>

            {/* 2. Global Display & Site Zoom */}
            <div className="border-t border-zinc-800/60 pt-3.5">
              <div className="flex items-center justify-between text-[10px] font-bold text-zinc-400 uppercase tracking-[0.12em] mb-2.5">
                <span className="flex items-center gap-2">
                  <Monitor size={12} className="text-cyan-400" />
                  Display Scaling
                </span>
                <span className="text-[9px] text-emerald-400 font-bold px-2 py-0.5 bg-emerald-950/40 rounded-full border border-emerald-500/20">{uiScale}%</span>
              </div>

              <div className="flex items-center gap-1.5 mb-2">
                <button
                  onClick={() => { triggerHaptic("click"); decreaseUiScale(); }}
                  className="flex-1 py-1.5 px-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 hover:border-zinc-600 text-zinc-200 rounded-lg text-center font-bold text-[10px] cursor-pointer active:scale-95 transition-all"
                  title="Decrease UI scale"
                >
                  - ZOOM OUT
                </button>
                <button
                  onClick={() => { triggerHaptic("click"); resetUiScale(); }}
                  className="py-1.5 px-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 hover:border-zinc-600 text-emerald-400 hover:text-emerald-300 rounded-lg text-center text-[10px] font-bold cursor-pointer transition-all"
                  title="Reset to standard 100%"
                >
                  <RotateCcw size={12} />
                </button>
                <button
                  onClick={() => { triggerHaptic("click"); increaseUiScale(); }}
                  className="flex-1 py-1.5 px-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 hover:border-zinc-600 text-zinc-200 rounded-lg text-center font-bold text-[10px] cursor-pointer active:scale-95 transition-all"
                  title="Increase UI scale"
                >
                  + ZOOM IN
                </button>
              </div>

              {/* Quick Presets */}
              <div className="flex items-center gap-1">
                {presetScales.map((scale) => (
                  <button
                    key={scale}
                    onClick={() => { triggerHaptic("click"); setUiScale(scale); }}
                    className={`flex-1 py-1 rounded-md text-[9px] border transition-all cursor-pointer ${
                      uiScale === scale
                        ? "bg-emerald-950 border-emerald-500/60 text-emerald-300 font-bold shadow-[0_0_8px_rgba(16,185,129,0.15)]"
                        : "bg-zinc-900 border-zinc-800 text-zinc-500 hover:text-zinc-300 hover:border-zinc-700"
                    }`}
                  >
                    {scale}%
                  </button>
                ))}
              </div>
            </div>

            {/* 3. Vector Map Layer Toggles */}
            <div className="border-t border-zinc-800/60 pt-3.5">
              <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-400 uppercase tracking-[0.12em] mb-2.5">
                <Layers size={12} className="text-emerald-400" />
                <span>Tactical Vector Layers</span>
              </div>

              <div className="space-y-0.5 text-[10px]">
                <label className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-900/60 cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors group">
                  <span className="flex items-center gap-2.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.5)]" />
                    Delhi NCT Admin Boundary
                  </span>
                  <input
                    type="checkbox"
                    checked={vectorLayers.boundaries}
                    onChange={() => toggleVectorLayer("boundaries")}
                    className="accent-emerald-500 rounded cursor-pointer w-3.5 h-3.5"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-900/60 cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors group">
                  <span className="flex items-center gap-2.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_4px_rgba(34,211,238,0.5)]" />
                    NCR Strategic Districts
                  </span>
                  <input
                    type="checkbox"
                    checked={vectorLayers.districts}
                    onChange={() => toggleVectorLayer("districts")}
                    className="accent-emerald-500 rounded cursor-pointer w-3.5 h-3.5"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-900/60 cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors group">
                  <span className="flex items-center gap-2.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_4px_rgba(251,191,36,0.5)]" />
                    Expressways (KMP / KGP / NH-48)
                  </span>
                  <input
                    type="checkbox"
                    checked={vectorLayers.expressways}
                    onChange={() => toggleVectorLayer("expressways")}
                    className="accent-emerald-500 rounded cursor-pointer w-3.5 h-3.5"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-900/60 cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors group">
                  <span className="flex items-center gap-2.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-400 shadow-[0_0_4px_rgba(56,189,248,0.5)]" />
                    Yamuna Basin & Drainage
                  </span>
                  <input
                    type="checkbox"
                    checked={vectorLayers.waterways}
                    onChange={() => toggleVectorLayer("waterways")}
                    className="accent-emerald-500 rounded cursor-pointer w-3.5 h-3.5"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-900/60 cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors group">
                  <span className="flex items-center gap-2.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
                    Procedural MGRS Canvas Grid
                  </span>
                  <input
                    type="checkbox"
                    checked={vectorLayers.grid}
                    onChange={() => toggleVectorLayer("grid")}
                    className="accent-emerald-500 rounded cursor-pointer w-3.5 h-3.5"
                  />
                </label>
              </div>
            </div>

            {/* 3.5. Map Interaction Features */}
            <div className="border-t border-zinc-800/60 pt-3.5">
              <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-400 uppercase tracking-[0.12em] mb-2.5">
                <MousePointerClick size={12} className="text-amber-400" />
                <span>Interaction Features</span>
              </div>
              <div className="space-y-0.5 text-[10px]">
                <label className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-900/60 cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors">
                  <span className="flex items-center gap-2.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
                    Hover Tooltips (Expanded Map)
                  </span>
                  <input
                    type="checkbox"
                    checked={showTooltips}
                    onChange={() => setShowTooltips(!showTooltips)}
                    className="accent-emerald-500 rounded cursor-pointer w-3.5 h-3.5"
                  />
                </label>
              </div>
            </div>

            {/* 3.6 Action Buttons */}
            <div className="border-t border-zinc-800/60 pt-3.5 pb-1 space-y-2">
               <button
                 onClick={() => {
                   setIsMenuOpen(false);
                   setIsOfflineManagerOpen(true);
                 }}
                 className="flex items-center gap-2.5 w-full px-3.5 py-2.5 bg-zinc-900 hover:bg-zinc-800/80 border border-zinc-700/60 hover:border-zinc-600 text-zinc-200 hover:text-white text-[10px] font-bold tracking-[0.1em] uppercase rounded-xl transition-all shadow-sm hover:shadow-md active:scale-[0.98] group"
                >
                  <div className="p-1.5 bg-zinc-800 rounded-lg border border-zinc-700/60 group-hover:border-zinc-500 transition-colors">
                    <DownloadCloud size={12} className="text-cyan-400" />
                  </div>
                  <span>Offline Region Manager</span>
                </button>
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    setIsDatasetStudioOpen(true);
                  }}
                  className="flex items-center gap-2.5 w-full px-3.5 py-2.5 bg-emerald-950/30 hover:bg-emerald-950/60 border border-emerald-700/30 hover:border-emerald-500/50 text-emerald-300 hover:text-emerald-200 text-[10px] font-bold tracking-[0.1em] uppercase rounded-xl transition-all shadow-sm hover:shadow-[0_0_15px_rgba(16,185,129,0.1)] active:scale-[0.98] group"
                >
                  <div className="p-1.5 bg-emerald-950/60 rounded-lg border border-emerald-700/40 group-hover:border-emerald-500/60 transition-colors">
                    <Database size={12} className="text-emerald-400" />
                  </div>
                  <span>Dataset Ingestion Studio</span>
                </button>
              </div>
            
            {/* 4. Telemetry Diagnostics Footer */}
            <div className="border-t border-zinc-800/60 pt-3 flex items-center justify-between text-[9px] text-zinc-600">
              <span className="font-mono tracking-wider">CRS: WGS84 (EPSG:4326)</span>
              <div className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-emerald-600 font-bold tracking-wider">AIR-GAP COMPLIANT</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {isOfflineManagerOpen && (
        <OfflineRegionManager onClose={() => setIsOfflineManagerOpen(false)} />
      )}
      
      {isDatasetStudioOpen && (
        <DatasetStudioModal onClose={() => setIsDatasetStudioOpen(false)} />
      )}
    </header>
  );
}
