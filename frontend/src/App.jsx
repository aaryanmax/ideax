import { useMemo, useEffect } from "react";
import Header from "./components/common/Header.jsx";
import SearchPanel from "./features/search/SearchPanel.jsx";
import CandidateGallery from "./features/search/CandidateGallery.jsx";
import CommitLog from "./features/workflow/CommitLog.jsx";
import DetailPanel from "./features/viewer/DetailPanel.jsx";
import { X } from "lucide-react";
import { triggerHaptic } from "./lib/haptics.js";
import FieldManualTour from "./features/workflow/FieldManualTour.jsx";
import { useSearchStore } from "./store/useSearchStore.js";

export default function App() {
  const store = useSearchStore();

  const handleFetchReject = (reason) => {
    store.setTacticalAlert({ type: 'error', message: reason });
  };

  const handleFetchSuccess = (sector) => {
    store.setTacticalAlert({
      type: 'success',
      message: `Surveillance Sector Locked: ${sector.name}. Retrieving assets...`
    });
  };

  useEffect(() => {
    store.fetchAuditLog();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => store.setDebouncedQuery(store.query), 300);
    return () => clearTimeout(timer);
  }, [store.query]);

  useEffect(() => {
    store.doSearch();
  }, [store.debouncedQuery, store.datasetFilter]);

  const sensors = useMemo(() => [...new Set(store.response.results.map((r) => r.metadata.sensor))], [store.response]);

  const results = useMemo(
    () =>
      store.response.results.filter(
        (r) => r.score >= store.minConfidence && (!store.sensorFilter || r.metadata.sensor === store.sensorFilter)
      ),
    [store.response, store.minConfidence, store.sensorFilter]
  );

  const selected = results.find((r) => r.tile_id === store.selectedTileId) ?? results[0] ?? null;

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        triggerHaptic('scan');
        const idx = results.findIndex(r => r.tile_id === selected?.tile_id);
        if (idx >= 0 && idx < results.length - 1) store.setSelectedTileId(results[idx + 1].tile_id);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        triggerHaptic('scan');
        const idx = results.findIndex(r => r.tile_id === selected?.tile_id);
        if (idx > 0) store.setSelectedTileId(results[idx - 1].tile_id);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [results, selected]);

  useEffect(() => {
    store.doAnalyze(selected);
  }, [selected]);

  const before = useMemo(() => {
    if (!selected) return null;
    return (
      store.response.results.find(
        (r) =>
          r.tile_id !== selected.tile_id &&
          r.metadata.latitude === selected.metadata.latitude &&
          r.metadata.longitude === selected.metadata.longitude
      ) ?? selected
    );
  }, [store.response, selected]);

  const handleDiscover = (patchId) => {
    triggerHaptic('scan');
    store.discoverPattern(patchId);
  }

  return (
    <div className="min-h-screen w-full bg-base text-ink">
      <FieldManualTour run={store.runTour} setRun={store.setRunTour} />
      <Header nResults={store.response.n_results} executionMs={store.response.execution_time_ms} onStartTour={() => store.setRunTour(true)} />

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_320px]">
        <SearchPanel
          query={store.query}
          onQueryChange={store.setQuery}
          minConfidence={store.minConfidence}
          onMinConfidenceChange={store.setMinConfidence}
          sensors={sensors}
          sensorFilter={store.sensorFilter}
          onSensorFilterChange={store.setSensorFilter}
          datasetFilter={store.datasetFilter}
          onDatasetFilterChange={store.setDatasetFilter}
        />

        <main className="p-4 flex flex-col min-w-0">
          {store.tacticalAlert && (
            <div className={`mb-4 flex items-center justify-between rounded border px-4 py-3 shadow-[0_0_15px_rgba(0,0,0,0.2)] ${
              store.tacticalAlert.type === 'error'
                ? 'border-rose-500/60 bg-rose-950/50 text-rose-300'
                : 'border-emerald-500/60 bg-emerald-950/50 text-emerald-300'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                  store.tacticalAlert.type === 'error' ? 'bg-rose-900/80 text-rose-300' : 'bg-emerald-900/80 text-emerald-300'
                }`}>
                  {store.tacticalAlert.type === 'error' ? '!' : '✓'}
                </div>
                <p className="font-mono text-xs font-medium tracking-wide">
                  {store.tacticalAlert.message}
                </p>
              </div>
              <button 
                onClick={() => store.setTacticalAlert(null)}
                className="text-zinc-400 hover:text-zinc-100"
              >
                <X size={16} />
              </button>
            </div>
          )}

          {store.discoverySummary && (
            <div className="mb-4 flex items-center justify-between rounded border border-emerald-500/50 bg-emerald-950/40 px-4 py-3 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
              <div className="flex items-center gap-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-900/80 text-emerald-400">
                  <span className="text-sm font-bold">✓</span>
                </div>
                <p className="font-mono text-xs font-medium tracking-wide text-emerald-300">
                  {store.discoverySummary}
                </p>
              </div>
              <button 
                onClick={() => store.setDiscoverySummary(null)}
                className="text-emerald-500/70 hover:text-emerald-400"
              >
                <X size={16} />
              </button>
            </div>
          )}
          <div className="flex-1">
            <CandidateGallery
              results={results}
              total={store.response.results.length}
              activeCandidateId={selected?.tile_id}
              onSelect={store.setSelectedTileId}
              threshold={store.minConfidence || 0.5}
            />
          </div>
          
          <CommitLog commits={store.commits} />
        </main>

        <DetailPanel
          selected={selected}
          before={before}
          threshold={store.minConfidence || 0.5}
          onApprove={() => store.recordDecision(selected, "approved")}
          onReject={() => store.recordDecision(selected, "rejected")}
          activeAnalysis={store.activeAnalysis}
          onCommitSuccess={store.fetchAuditLog}
          candidates={results}
          totalCandidates={store.response.results.length}
          onSelectCandidate={store.setSelectedTileId}
          onDiscoverPattern={handleDiscover}
          isDiscovering={store.isDiscovering}
          onDatasetFilterChange={store.setDatasetFilter}
          onFetchReject={handleFetchReject}
          onFetchSuccess={handleFetchSuccess}
        />
      </div>
    </div>
  );
}
