import { useMemo, useState, useEffect } from "react";
import Header from "./components/Header.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import CandidateGallery from "./components/CandidateGallery.jsx";
import CommitLog from "./components/CommitLog.jsx";
import DetailPanel from "./components/DetailPanel.jsx";
import { searchTiles, analyzeChange } from "./lib/api.js";
import { MOCK_COMMITS } from "./data/mockSearchResponse.js";

export default function App() {
  const [query, setQuery] = useState("new structure near ridge access road");
  const [response, setResponse] = useState({ results: [], n_results: 0, execution_time_ms: 0 });
  const [minConfidence, setMinConfidence] = useState(0);
  const [sensorFilter, setSensorFilter] = useState(null);
  const [selectedTileId, setSelectedTileId] = useState(null);
  const [commits, setCommits] = useState(MOCK_COMMITS);
  const [activeAnalysis, setActiveAnalysis] = useState(null);

  useEffect(() => {
    let active = true;
    async function doSearch() {
      if (!query) return;
      try {
        const start = performance.now();
        const geojson = await searchTiles(query, 6);
        const execTime = performance.now() - start;
        if (!active) return;

        if (geojson && geojson.features) {
          const transformed = geojson.features.map((feature, idx) => ({
            tile_id: feature.properties.patch_id || `patch_${idx}`,
            score: feature.properties.similarity_score,
            metadata: {
              latitude: feature.properties.center ? feature.properties.center[0] : 0,
              longitude: feature.properties.center ? feature.properties.center[1] : 0,
              acquisition_date: "2026-08-31",
              sensor: "Sentinel-2 L2A",
              cloud_cover_pct: 0,
            },
            coordinates: feature.geometry.coordinates,
            verified: feature.properties.similarity_score > 0.20
          }));
          
          setResponse({
            results: transformed,
            n_results: transformed.length,
            execution_time_ms: execTime
          });
          
          if (transformed.length > 0) {
            setSelectedTileId(transformed[0].tile_id);
          } else {
            setSelectedTileId(null);
          }
        }
      } catch (err) {
        console.error("Search error:", err);
      }
    }
    doSearch();
    return () => { active = false; };
  }, [query]);

  const sensors = useMemo(() => [...new Set(response.results.map((r) => r.metadata.sensor))], [response]);

  const results = useMemo(
    () =>
      response.results.filter(
        (r) => r.score >= minConfidence && (!sensorFilter || r.metadata.sensor === sensorFilter)
      ),
    [response, minConfidence, sensorFilter]
  );

  const selected = results.find((r) => r.tile_id === selectedTileId) ?? results[0] ?? null;

  useEffect(() => {
    let active = true;
    async function doAnalyze() {
      if (!selected) {
        setActiveAnalysis(null);
        return;
      }
      setActiveAnalysis(null);
      try {
        let colOff = 4500, rowOff = 4500;
        const match = selected.tile_id.match(/patch_(\d+)_(\d+)/);
        if (match) {
          colOff = parseInt(match[1], 10);
          rowOff = parseInt(match[2], 10);
        }
        
        const analysis = await analyzeChange(colOff, rowOff, true);
        if (active) setActiveAnalysis(analysis);
      } catch (err) {
        console.error("Analyze error:", err);
      }
    }
    doAnalyze();
    return () => { active = false; };
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
        analyst: "P",
        status,
        ts: new Date().toISOString().slice(0, 16).replace("T", " "),
      },
      ...prev,
    ]);
  }

  return (
    <div className="min-h-screen w-full bg-base text-ink">
      <Header nResults={response.n_results} executionMs={response.execution_time_ms} />

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_320px]">
        <SearchPanel
          query={query}
          onQueryChange={setQuery}
          minConfidence={minConfidence}
          onMinConfidenceChange={setMinConfidence}
          sensors={sensors}
          sensorFilter={sensorFilter}
          onSensorFilterChange={setSensorFilter}
        />

        <main className="p-4">
          <CandidateGallery
            results={results}
            total={response.results.length}
            selectedTileId={selected?.tile_id}
            onSelect={setSelectedTileId}
            threshold={minConfidence || 0.5}
          />
          <CommitLog commits={commits} />
        </main>

        <DetailPanel
          selected={selected}
          before={before}
          threshold={minConfidence || 0.5}
          onApprove={() => recordDecision("approved")}
          onReject={() => recordDecision("rejected")}
          activeAnalysis={activeAnalysis}
        />
      </div>
    </div>
  );
}
