import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Database, Search, Activity, CheckCircle, AlertTriangle, Layers, BrainCircuit, Play, Cpu } from "lucide-react";
import { triggerHaptic } from "../../lib/haptics.js";

export default function DatasetStudioModal({ onClose }) {
  const [sources, setSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [datasetName, setDatasetName] = useState("mumbai");
  const [t1Path, setT1Path] = useState("");
  const [t2Path, setT2Path] = useState("");

  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);

  const [aiRecs, setAiRecs] = useState(null);

  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestLog, setIngestLog] = useState([]);
  
  const [isImporting, setIsImporting] = useState(false);
  const [importSourcePath, setImportSourcePath] = useState("");
  const [importTargetFolder, setImportTargetFolder] = useState("");

  const fetchSources = () => {
    fetch("http://localhost:8000/api/v1/dataset-studio/sources")
      .then(r => r.json())
      .then(d => setSources(d.sources || []))
      .catch(e => console.error(e));
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleSourceSelect = (src) => {
    triggerHaptic("click");
    setSelectedSource(src);
    setValidationResult(null);
    setAiRecs(null);

    // Fetch AI recommendations for this path
    fetch(`http://localhost:8000/api/v1/dataset-studio/ai-recommendations?path=${encodeURIComponent(src.path)}`)
      .then(r => r.json())
      .then(d => setAiRecs(d))
      .catch(e => console.error(e));
  };

  const typeColor = (type) => {
    if (type === 'patch_package') return 'text-sensorAccent';
    if (type === 'safe') return 'text-verifiedText';
    return 'text-amberText';
  };

  const typeDot = (type) => {
    if (type === 'patch_package') return 'bg-sensorAccent';
    if (type === 'safe') return 'bg-verified';
    return 'bg-amber';
  };

  const typeBadgeClass = (type) => {
    if (type === 'patch_package') return 'bg-sensorAccent/10 border-sensorAccent/30 text-sensorAccent';
    if (type === 'safe') return 'bg-verified/10 border-verified/30 text-verifiedText';
    return 'bg-amber/10 border-amber/30 text-amberText';
  };

  const validateBounds = async () => {
    if (!selectedSource || !lat || !lon) return;
    triggerHaptic("scan");
    setIsValidating(true);
    setValidationResult(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/dataset-studio/validate-bounds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: parseFloat(lat),
          lon: parseFloat(lon),
          dataset_path: selectedSource.path
        })
      });
      const data = await res.json();
      setValidationResult(data);
    } catch (err) {
      setValidationResult({ valid: false, message: "API Error: " + err.message });
    } finally {
      setIsValidating(false);
    }
  };

  const handleIngest = async () => {
    if (!selectedSource) return;
    triggerHaptic("scan");
    setIsIngesting(true);
    setIngestLog(prev => [...prev, "Starting ingestion sequence..."]);

    try {
      let reqBody = {
        mode: selectedSource.type === 'patch_package' ? 'patch' : (selectedSource.type === 'safe' ? 'safe' : 'raw'),
        dataset: datasetName,
        lat: parseFloat(lat) || 0,
        lon: parseFloat(lon) || 0,
      };

      if (reqBody.mode === 'patch') {
        reqBody.input_path = selectedSource.path;
      } else {
        reqBody.t1 = t1Path || selectedSource.path;
        reqBody.t2 = t2Path || selectedSource.path;
      }

      const res = await fetch("http://localhost:8000/api/v1/dataset-studio/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reqBody)
      });

      const data = await res.json();
      setIngestLog(prev => [...prev, data.message || "Ingestion finished.", data.details || ""]);
      if (data.status === "success") {
        setIngestLog(prev => [...prev, "✅ Tactical Index Updated. Reload dashboard to view."]);
      }
    } catch (err) {
      setIngestLog(prev => [...prev, "❌ Error: " + err.message]);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleImport = async () => {
    if (!importSourcePath || !importTargetFolder) return;
    setIsImporting(true);
    triggerHaptic("click");
    try {
      const res = await fetch("http://localhost:8000/api/v1/dataset-studio/import-source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_path: importSourcePath,
          target_folder: importTargetFolder
        })
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setImportSourcePath("");
        setImportTargetFolder("");
        fetchSources(); // Reload the list
      } else {
        alert("Import Failed: " + (data.detail || data.message));
      }
    } catch (err) {
      alert("Error connecting to server for import: " + err.message);
    } finally {
      setIsImporting(false);
    }
  };

  // Lock body scroll when modal is open and handle ESC
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", handleKey);
    };
  }, [onClose]);

  return createPortal(
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 sm:p-6 select-none"
      style={{ isolation: 'isolate' }}
    >
      <div className="bg-base w-full max-w-5xl h-[90vh] rounded-2xl border border-border shadow-[0_25px_80px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-panel shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-verified/10 rounded-xl border border-verified/20">
              <Database className="text-verified" size={18} />
            </div>
            <div>
              <h2 className="font-cond font-bold tracking-widest text-ink text-lg uppercase">Dataset Ingestion Studio</h2>
              <p className="font-mono text-[10px] text-muted mt-0.5 tracking-wider uppercase">Import · Validate · Process Raw Tactical Data</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-ink hover:bg-panelAlt p-2 rounded-lg transition-all border border-transparent hover:border-border"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Left Panel: Sources */}
          <div className="w-[280px] shrink-0 border-r border-border bg-panel flex flex-col">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0 bg-panelAlt/40">
              <span className="font-mono text-[9px] text-faint uppercase tracking-[0.15em] font-bold">Raw Data Sources</span>
              <span className="bg-border text-muted text-[9px] px-2 py-0.5 rounded-full font-mono font-bold">{sources.length}</span>
            </div>

            <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5">
              {sources.map((src, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSourceSelect(src)}
                  className={`w-full text-left p-3 rounded-xl border transition-all duration-150 flex items-start gap-3 min-w-0 group ${selectedSource?.path === src.path
                      ? "bg-verified/10 border-verified/30 shadow-[0_0_20px_rgba(143,174,122,0.08)]"
                      : "bg-panelAlt/50 border-border/50 hover:border-borderHover hover:bg-panelAlt"
                    }`}
                >
                  <div className={`mt-0.5 shrink-0 p-1.5 rounded-lg transition-colors ${selectedSource?.path === src.path
                      ? 'bg-verified/20 text-verified'
                      : 'bg-base/80 text-faint group-hover:text-muted'
                    }`}>
                    <Layers size={13} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={`text-[11px] font-bold truncate tracking-wide font-mono ${selectedSource?.path === src.path ? 'text-ink' : 'text-muted group-hover:text-ink'
                      }`} title={src.name}>
                      {src.name}
                    </div>
                    <div className="flex items-center gap-1.5 mt-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${typeDot(src.type)}`} />
                      <span className={`text-[9px] font-mono uppercase tracking-wider font-bold ${typeColor(src.type)}`}>
                        {src.type}
                      </span>
                    </div>
                  </div>
                  {selectedSource?.path === src.path && (
                    <div className="w-0.5 self-stretch rounded-full bg-verified/60 ml-auto shrink-0" />
                  )}
                </button>
              ))}
              {sources.length === 0 && (
                <div className="text-xs text-muted text-center py-12 flex flex-col items-center gap-3">
                  <Database size={28} className="opacity-15" />
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-faint">No sources found</p>
                    <p className="text-[10px] text-faint/60 mt-1">Place files in data/raw/</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Import Navigator */}
            <div className="px-4 py-3 border-t border-border bg-panelAlt/20 shrink-0">
              <span className="font-mono text-[9px] text-faint uppercase tracking-[0.15em] font-bold block mb-3">Navigator: Import Local</span>
              <div className="space-y-2">
                <input 
                  type="text" 
                  value={importSourcePath}
                  onChange={(e) => setImportSourcePath(e.target.value)}
                  placeholder="Win Path (e.g. C:\Data\SAT)" 
                  className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-[10px] text-ink font-mono focus:border-sensorAccent/50 outline-none placeholder:text-faint/40"
                />
                <input 
                  type="text" 
                  value={importTargetFolder}
                  onChange={(e) => setImportTargetFolder(e.target.value)}
                  placeholder="Target Folder (e.g. Mumbai)" 
                  className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-[10px] text-ink font-mono focus:border-sensorAccent/50 outline-none placeholder:text-faint/40"
                />
                <button 
                  onClick={handleImport}
                  disabled={isImporting || !importSourcePath || !importTargetFolder}
                  className="w-full flex items-center justify-center gap-1.5 bg-sensorAccent/10 hover:bg-sensorAccent/20 border border-sensorAccent/30 text-sensorAccent py-1.5 rounded-lg text-[9px] font-mono font-bold uppercase tracking-wider transition-all disabled:opacity-50"
                >
                  {isImporting ? <Activity size={10} className="animate-spin" /> : <Database size={10} />}
                  {isImporting ? 'Copying...' : 'Transfer to data/raw'}
                </button>
              </div>
            </div>
          </div>

          {/* Right Panel: Details & Action */}
          <div className="flex-1 flex flex-col overflow-y-auto bg-base">
            {!selectedSource ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted gap-5 p-8">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full bg-panel flex items-center justify-center border border-border shadow-inner">
                    <Search size={32} className="opacity-30 text-faint" />
                  </div>
                  <div className="absolute inset-0 rounded-full border border-border/30 scale-125 animate-ping opacity-20" />
                </div>
                <div className="text-center">
                  <p className="font-mono text-sm tracking-widest uppercase text-muted/80">Select a Dataset</p>
                  <p className="text-[10px] text-faint mt-1 font-mono">Choose a raw source from the left panel to begin</p>
                </div>
              </div>
            ) : (
              <div className="max-w-2xl w-full mx-auto p-6 space-y-5 pb-8">

                {/* Selected source info badge */}
                <div className="flex items-center gap-3 px-4 py-3 bg-panel rounded-xl border border-border">
                  <div className="p-2 bg-verified/10 rounded-lg">
                    <Layers size={14} className="text-verified" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-[9px] text-faint uppercase tracking-wider">Selected Source</p>
                    <p className="text-sm font-bold text-ink font-mono truncate mt-0.5">{selectedSource.name}</p>
                  </div>
                  <span className={`text-[9px] font-mono font-bold uppercase px-2.5 py-1 rounded-md border ${typeBadgeClass(selectedSource.type)}`}>
                    {selectedSource.type}
                  </span>
                </div>

                {/* AI Recommendations */}
                {aiRecs && (
                  <div className="bg-sensorAccent/5 border border-sensorAccent/20 rounded-xl p-4">
                    <div className="flex items-center gap-2.5 text-sensorAccent mb-3">
                      <div className="p-1.5 bg-sensorAccent/10 rounded-lg">
                        <BrainCircuit size={14} />
                      </div>
                      <h4 className="font-mono text-[10px] uppercase tracking-[0.12em] font-bold">AI Recommendations</h4>
                    </div>
                    <ul className="text-xs font-sans text-ink/80 space-y-1.5 pl-1">
                      {aiRecs.recommendations.map((r, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-sensorAccent/50 mt-0.5 shrink-0">›</span>
                          <span className="leading-relaxed">{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Pre-flight Config */}
                <div className="bg-panel rounded-xl border border-border overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-border bg-panelAlt/40 flex items-center gap-2">
                    <Cpu size={13} className="text-faint" />
                    <h3 className="font-mono text-[10px] text-faint uppercase tracking-[0.12em] font-bold">Pre-Flight Configuration</h3>
                  </div>
                  <div className="p-5 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="block text-[9px] font-mono text-faint uppercase tracking-[0.12em] font-bold">Target Latitude</label>
                        <input
                          type="number" step="0.001" value={lat} onChange={e => setLat(e.target.value)}
                          className="w-full bg-base border border-border rounded-lg px-3 py-2.5 text-sm text-ink font-mono focus:border-verified/50 focus:ring-1 focus:ring-verified/20 outline-none transition-all placeholder:text-faint/40"
                          placeholder="e.g. 19.506"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="block text-[9px] font-mono text-faint uppercase tracking-[0.12em] font-bold">Target Longitude</label>
                        <input
                          type="number" step="0.001" value={lon} onChange={e => setLon(e.target.value)}
                          className="w-full bg-base border border-border rounded-lg px-3 py-2.5 text-sm text-ink font-mono focus:border-verified/50 focus:ring-1 focus:ring-verified/20 outline-none transition-all placeholder:text-faint/40"
                          placeholder="e.g. 83.133"
                        />
                      </div>
                      <div className="col-span-2 space-y-1.5">
                        <label className="block text-[9px] font-mono text-faint uppercase tracking-[0.12em] font-bold">Target Catalog Partition</label>
                        <select
                          value={datasetName} onChange={e => setDatasetName(e.target.value)}
                          className="w-full bg-base border border-border rounded-lg px-3 py-2.5 text-sm text-ink font-mono focus:border-verified/50 focus:ring-1 focus:ring-verified/20 outline-none transition-all cursor-pointer"
                        >
                          <option value="mumbai">Mumbai / Global Index</option>
                          <option value="delhi">Delhi Index</option>
                        </select>
                      </div>
                    </div>

                    {selectedSource.type !== 'patch_package' && (
                      <div className="pt-4 mt-1 border-t border-border/60 border-dashed grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label className="block text-[9px] font-mono text-faint uppercase tracking-[0.12em] font-bold">T1 Source Path</label>
                          <input type="text" value={t1Path} onChange={e => setT1Path(e.target.value)} className="w-full bg-base border border-border rounded-lg px-3 py-2.5 text-sm text-ink font-mono focus:border-verified/50 focus:ring-1 focus:ring-verified/20 outline-none transition-all placeholder:text-faint/30" placeholder={selectedSource.path} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="block text-[9px] font-mono text-faint uppercase tracking-[0.12em] font-bold">T2 Source Path</label>
                          <input type="text" value={t2Path} onChange={e => setT2Path(e.target.value)} className="w-full bg-base border border-border rounded-lg px-3 py-2.5 text-sm text-ink font-mono focus:border-verified/50 focus:ring-1 focus:ring-verified/20 outline-none transition-all placeholder:text-faint/30" placeholder={selectedSource.path} />
                        </div>
                        <div className="col-span-2 bg-amber/8 border border-amber/15 rounded-lg p-3">
                          <p className="text-[10px] text-amberText font-mono flex items-center gap-2">
                            <AlertTriangle size={12} className="text-amber shrink-0" />
                            Both T1 and T2 must be specified for safe/raw processing.
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="pt-1 flex items-center gap-3">
                      <button
                        onClick={validateBounds}
                        disabled={isValidating || !lat || !lon}
                        className="flex items-center justify-center gap-2 bg-panelAlt hover:bg-borderHover border border-border hover:border-borderHover text-ink px-4 py-2 rounded-lg text-[11px] font-mono font-bold uppercase tracking-widest transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
                      >
                        {isValidating ? (
                          <Activity size={13} className="animate-spin text-sensorAccent" />
                        ) : (
                          <Search size={13} className="text-muted" />
                        )}
                        {isValidating ? 'Validating...' : 'Validate Bounds'}
                      </button>

                      {validationResult && (
                        <div className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-[11px] border font-mono font-bold flex-1 ${validationResult.valid
                            ? 'bg-verified/10 border-verified/25 text-verifiedText'
                            : 'bg-danger/10 border-danger/25 text-dangerText'
                          }`}>
                          {validationResult.valid
                            ? <CheckCircle size={13} className="shrink-0" />
                            : <AlertTriangle size={13} className="shrink-0" />
                          }
                          <span className="truncate">{validationResult.message}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Pipeline Execution */}
                <div className="bg-panel rounded-xl border border-border overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-border bg-panelAlt/40 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Play size={13} className="text-faint" />
                      <h3 className="font-mono text-[10px] text-faint uppercase tracking-[0.12em] font-bold">Pipeline Execution</h3>
                    </div>
                    {ingestLog.length > 0 && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-verified animate-pulse" />
                        <span className="text-[9px] font-mono text-faint uppercase tracking-wider">Live</span>
                      </div>
                    )}
                  </div>
                  <div className="p-5 space-y-4">
                    <button
                      onClick={handleIngest}
                      disabled={isIngesting || (selectedSource.type !== 'patch_package' && (!validationResult || !validationResult.valid))}
                      className="w-full flex items-center justify-center gap-2.5 bg-verified hover:brightness-110 text-base px-4 py-3.5 rounded-xl text-[11px] font-mono font-black tracking-[0.15em] uppercase transition-all shadow-[0_0_30px_rgba(143,174,122,0.12)] hover:shadow-[0_0_35px_rgba(143,174,122,0.25)] disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed active:scale-[0.99]"
                    >
                      {isIngesting ? (
                        <Activity size={16} className="animate-spin" />
                      ) : (
                        <Play size={16} className="fill-current" />
                      )}
                      {isIngesting ? 'Executing Pipeline...' : 'Run Ingestion & Register'}
                    </button>

                    {ingestLog.length > 0 && (
                      <div className="bg-base border border-border rounded-xl p-4 h-40 overflow-y-auto font-mono text-[10px] text-muted">
                        {ingestLog.map((log, i) => (
                          <div key={i} className={`mb-1.5 flex items-start gap-2 ${log.includes("❌ Error")
                              ? "text-dangerText font-bold"
                              : log.includes("✅")
                                ? "text-verifiedText font-bold"
                                : ""
                            }`}>
                            <span className="opacity-30 shrink-0 mt-0.5">›</span>
                            <span className="break-all leading-relaxed">{log}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
