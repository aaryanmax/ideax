import { useMemo, useState, useEffect } from "react";
import Header from "./components/Header.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import CandidateGallery from "./components/CandidateGallery.jsx";
import CommitLog from "./components/CommitLog.jsx";
import DetailPanel from "./components/DetailPanel.jsx";
import { X } from "lucide-react";
import { searchTiles, analyzeChange, getAuditLog, findSimilarSites } from "./lib/api.js";
import { triggerHaptic } from "./lib/haptics.js";
import FieldManualTour from "./components/workflow/FieldManualTour.jsx";
import { MOCK_COMMITS } from "./data/mockSearchResponse.js";

export default function App() {
  const [query, setQuery] = useState("seasonal crop fields or agricultural land");
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [response, setResponse] = useState({ results: [], n_results: 0, execution_time_ms: 0 });
  const [minConfidence, setMinConfidence] = useState(0);
  const [sensorFilter, setSensorFilter] = useState(null);
  const [datasetFilter, setDatasetFilter] = useState("none");
  const [selectedTileId, setSelectedTileId] = useState(null);
  const [commits, setCommits] = useState(MOCK_COMMITS);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [runTour, setRunTour] = useState(false);
  const [discoverySummary, setDiscoverySummary] = useState(null);
  const [isDiscovering, setIsDiscovering] = useState(false);

  // Fetch initial audit log records on mount
  const fetchAuditLog = async () => {
    try {
      const data = await getAuditLog(null, 50);
      if (data && data.records && data.records.length > 0) {
        setCommits(data.records);
      }
    } catch (err) {
      console.warn("Could not load audit log from backend:", err);
    }
  };

  useEffect(() => {
    fetchAuditLog();
  }, []);

  // Debounce query input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Semantic search triggered on debounced query change, datasetFilter & mount
  useEffect(() => {
    let active = true;
    async function doSearch() {
      const searchQuery = debouncedQuery || "seasonal crop fields or agricultural land";
      try {
        const start = performance.now();
        const geojson = await searchTiles(searchQuery, 6, datasetFilter);
        const execTime = performance.now() - start;
        if (!active) return;

        if (geojson && geojson.features) {
          const transformed = geojson.features.map((feature, idx) => {
            const patchId = feature.properties.patch_id || `patch_${idx}`;
            const rawThumb = feature.properties.thumbnail_url;
            const thumbUrl = rawThumb
              ? (rawThumb.startsWith("http") ? rawThumb : `http://localhost:8000${rawThumb}`)
              : `http://localhost:8000/static/tiles/thumbnails/${patchId}.png`;

            return {
              tile_id: patchId,
              score: feature.properties.similarity_score,
              thumbnail_url: thumbUrl,
              t1_thumbnail: feature.properties.t1_thumbnail,
              t2_thumbnail: feature.properties.t2_thumbnail,
              col_off: feature.properties.col_off,
              row_off: feature.properties.row_off,
              metadata: {
                latitude: feature.properties.center ? feature.properties.center[0] : 28.536,
                longitude: feature.properties.center ? feature.properties.center[1] : 76.457,
                acquisition_date: "2026-08-31",
                sensor: "Sentinel-2 L2A",
                cloud_cover_pct: 0,
              },
              coordinates: feature.geometry?.coordinates,
              verified: feature.properties.similarity_score > 0.20,
            };
          });

          setResponse({
            results: transformed,
            n_results: transformed.length,
            execution_time_ms: execTime,
          });

          if (transformed.length > 0) {
            setSelectedTileId((prev) =>
              transformed.some((t) => t.tile_id === prev) ? prev : transformed[0].tile_id
            );
          } else {
            setSelectedTileId(null);
          }
        }
      } catch (err) {
        console.error("Search error:", err);
      }
    }
    doSearch();
    return () => {
      active = false;
    };
  }, [debouncedQuery, datasetFilter]);

  const sensors = useMemo(() => [...new Set(response.results.map((r) => r.metadata.sensor))], [response]);

  const results = useMemo(
    () =>
      response.results.filter(
        (r) => r.score >= minConfidence && (!sensorFilter || r.metadata.sensor === sensorFilter)
      ),
    [response, minConfidence, sensorFilter]
  );

  const selected = results.find((r) => r.tile_id === selectedTileId) ?? results[0] ?? null;

  // Keyboard navigation for up/down candidate selection
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        triggerHaptic('scan');
        const idx = results.findIndex(r => r.tile_id === selected?.tile_id);
        if (idx >= 0 && idx < results.length - 1) setSelectedTileId(results[idx + 1].tile_id);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        triggerHaptic('scan');
        const idx = results.findIndex(r => r.tile_id === selected?.tile_id);
        if (idx > 0) setSelectedTileId(results[idx - 1].tile_id);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [results, selected]);

  // Run change detection & tactical SPOTREP classification when selected tile changes
  useEffect(() => {
    let active = true;
    async function doAnalyze() {
      if (!selected) {
        setActiveAnalysis(null);
        return;
      }
      setActiveAnalysis(null);
      try {
        let colOff = selected.col_off;
        let rowOff = selected.row_off;

        if (colOff == null || rowOff == null) {
          const matchNum = selected.tile_id.match(/patch_(\d+)$/);
          if (matchNum) {
            const idx = parseInt(matchNum[1], 10);
            colOff = 4000 + (idx % 5) * 512;
            rowOff = 4000 + Math.floor(idx / 5) * 512;
          } else {
            colOff = 4500;
            rowOff = 4500;
          }
        }

        const analysis = await analyzeChange(colOff, rowOff, true);
        if (active) setActiveAnalysis(analysis);
      } catch (err) {
        console.error("Analyze error:", err);
      }
    }
    doAnalyze();
    return () => {
      active = false;
    };
  }, [selected]);

  // Stand-in "before" tile: nearest earlier pass over the same coordinates.
  const before = useMemo(() => {
    if (!selected) return null;
    return (
      response.results.find(
        (r) =>
          r.tile_id !== selected.tile_id &&
          r.metadata.latitude === selected.metadata.latitude &&
          r.metadata.longitude === selected.metadata.longitude
      ) ?? selected
    );
  }, [response, selected]);

  function recordDecision(status) {
    if (!selected) return;
    setCommits((prev) => [
      {
        id: `c-${Math.floor(Math.random() * 9000 + 1000)}`,
        tile_id: selected.tile_id,
        analyst: "OFFICER_DELHI_01",
        status,
        ts: new Date().toISOString().slice(0, 16).replace("T", " "),
      },
      ...prev,
    ]);
  }

  const handleDiscoverPattern = async (patchId) => {
    setIsDiscovering(true);
    setDiscoverySummary(null);
    try {
      const data = await findSimilarSites(patchId);
      
      const transformed = data.features.map((feature, idx) => {
        const pId = feature.properties.patch_id || `patch_${idx}`;
        const rawThumb = feature.properties.thumbnail_url;
        const thumbUrl = rawThumb
          ? (rawThumb.startsWith("http") ? rawThumb : `http://localhost:8000${rawThumb}`)
          : `http://localhost:8000/static/tiles/thumbnails/${pId}.png`;

        return {
          tile_id: pId,
          score: feature.properties.similarity_score,
          thumbnail_url: thumbUrl,
          t1_thumbnail: feature.properties.t1_thumbnail,
          t2_thumbnail: feature.properties.t2_thumbnail,
          col_off: feature.properties.col_off,
          row_off: feature.properties.row_off,
          cluster_id: feature.properties.cluster_id,
          cluster_callsign: feature.properties.cluster_callsign,
          metadata: {
            latitude: feature.properties.center ? feature.properties.center[0] : 28.536,
            longitude: feature.properties.center ? feature.properties.center[1] : 76.457,
            acquisition_date: "2026-08-31",
            sensor: "Sentinel-2 L2A",
            cloud_cover_pct: 0,
          },
          coordinates: feature.geometry?.coordinates,
          verified: feature.properties.similarity_score > 0.20,
        };
      });

      setResponse(prev => ({
        ...prev,
        results: transformed,
        n_results: transformed.length,
      }));
      setDiscoverySummary(data.tactical_summary);
      triggerHaptic('scan');
      if (transformed.length > 0) setSelectedTileId(transformed[0].tile_id);
    } catch (err) {
      console.error("Discovery error:", err);
    } finally {
      setIsDiscovering(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-base text-ink">
      <FieldManualTour run={runTour} setRun={setRunTour} />
      <Header nResults={response.n_results} executionMs={response.execution_time_ms} onStartTour={() => setRunTour(true)} />

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_320px]">
        <SearchPanel
          query={query}
          onQueryChange={setQuery}
          minConfidence={minConfidence}
          onMinConfidenceChange={setMinConfidence}
          sensors={sensors}
          sensorFilter={sensorFilter}
          onSensorFilterChange={setSensorFilter}
          datasetFilter={datasetFilter}
          onDatasetFilterChange={setDatasetFilter}
        />

        <main className="p-4 flex flex-col min-w-0">
          {discoverySummary && (
            <div className="mb-4 flex items-center justify-between rounded border border-emerald-500/50 bg-emerald-950/40 px-4 py-3 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
              <div className="flex items-center gap-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-900/80 text-emerald-400">
                  <span className="text-sm font-bold">✓</span>
                </div>
                <p className="font-mono text-xs font-medium tracking-wide text-emerald-300">
                  {discoverySummary}
                </p>
              </div>
              <button 
                onClick={() => setDiscoverySummary(null)}
                className="text-emerald-500/70 hover:text-emerald-400"
              >
                <X size={16} />
              </button>
            </div>
          )}
          <div className="flex-1">
            <CandidateGallery
              results={results}
              total={response.results.length}
              activeCandidateId={selected?.tile_id}
              onSelect={setSelectedTileId}
              threshold={minConfidence || 0.5}
            />
          </div>
          
          <CommitLog commits={commits} />
        </main>

        <DetailPanel
          selected={selected}
          before={before}
          threshold={minConfidence || 0.5}
          onApprove={() => recordDecision("approved")}
          onReject={() => recordDecision("rejected")}
          activeAnalysis={activeAnalysis}
          onCommitSuccess={fetchAuditLog}
          candidates={results}
          totalCandidates={response.results.length}
          onSelectCandidate={setSelectedTileId}
          onDiscoverPattern={handleDiscoverPattern}
          isDiscovering={isDiscovering}
          onDatasetFilterChange={setDatasetFilter}
        />
      </div>
    </div>
  );
}
