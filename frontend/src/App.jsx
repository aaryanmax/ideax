import { useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import CandidateGallery from "./components/CandidateGallery.jsx";
import CommitLog from "./components/CommitLog.jsx";
import DetailPanel from "./components/DetailPanel.jsx";
import { MOCK_SEARCH_RESPONSE, MOCK_COMMITS } from "./data/mockSearchResponse.js";
// import { searchTiles } from "./lib/api.js";  // uncomment once /search is live

export default function App() {
  const [query, setQuery] = useState(MOCK_SEARCH_RESPONSE.query);
  const [response] = useState(MOCK_SEARCH_RESPONSE); // replace with useState(null) + useEffect(searchTiles) when live
  const [minConfidence, setMinConfidence] = useState(0);
  const [sensorFilter, setSensorFilter] = useState(null);
  const [selectedTileId, setSelectedTileId] = useState(MOCK_SEARCH_RESPONSE.results[0].tile_id);
  const [commits, setCommits] = useState(MOCK_COMMITS);
  const [fontScale, setFontScale] = useState(100); // % — scales all rem/em-based text via root font-size

  const sensors = useMemo(() => [...new Set(response.results.map((r) => r.metadata.sensor))], [response]);

  const results = useMemo(
    () =>
      response.results.filter(
        (r) => r.score >= minConfidence && (!sensorFilter || r.metadata.sensor === sensorFilter)
      ),
    [response, minConfidence, sensorFilter]
  );

  const selected = results.find((r) => r.tile_id === selectedTileId) ?? results[0] ?? null;

  // Stand-in "before" tile: nearest earlier pass over the same coordinates.
  // Once /change is live, tile_id_t1 comes back from the backend directly.
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

  // zoom (not fontSize) so it also scales the fixed-px text sizes used
  // throughout the dashboard (text-[10px] etc.), not just rem-based ones
  return (
    <div className="min-h-screen w-full bg-base text-ink" style={{ zoom: `${fontScale}%` }}>
      <Header
        nResults={response.n_results}
        executionMs={response.execution_time_ms}
        fontScale={fontScale}
        onFontScaleChange={setFontScale}
      />

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
        />
      </div>
    </div>
  );
}
