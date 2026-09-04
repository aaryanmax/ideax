import { create } from 'zustand';
import { MOCK_COMMITS } from '../data/mockSearchResponse.js';
import { searchTiles, analyzeChange, getAuditLog, findSimilarSites } from '../lib/api.js';

export const useSearchStore = create((set, get) => ({
  query: "seasonal crop fields or agricultural land",
  debouncedQuery: "seasonal crop fields or agricultural land",
  response: { results: [], n_results: 0, execution_time_ms: 0 },
  minConfidence: 0,
  sensorFilter: null,
  datasetFilter: "none",
  selectedTileId: null,
  commits: MOCK_COMMITS,
  activeAnalysis: null,
  runTour: false,
  discoverySummary: null,
  isDiscovering: false,
  tacticalAlert: null,

  setQuery: (query) => set({ query }),
  setDebouncedQuery: (debouncedQuery) => set({ debouncedQuery }),
  setMinConfidence: (minConfidence) => set({ minConfidence }),
  setSensorFilter: (sensorFilter) => set({ sensorFilter }),
  setDatasetFilter: (datasetFilter) => set({ datasetFilter }),
  setSelectedTileId: (selectedTileId) => set({ selectedTileId }),
  setRunTour: (runTour) => set({ runTour }),
  setDiscoverySummary: (discoverySummary) => set({ discoverySummary }),
  setTacticalAlert: (tacticalAlert) => set({ tacticalAlert }),
  setCommits: (commits) => set({ commits }),

  fetchAuditLog: async () => {
    try {
      const data = await getAuditLog(null, 50);
      if (data?.records?.length > 0) set({ commits: data.records });
    } catch (err) {
      console.warn("Could not load audit log:", err);
    }
  },

  doSearch: async () => {
    const { debouncedQuery, datasetFilter } = get();
    try {
      const start = performance.now();
      const geojson = await searchTiles(debouncedQuery, 6, datasetFilter);
      const execTime = performance.now() - start;

      if (geojson?.features) {
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

        set({
          response: { results: transformed, n_results: transformed.length, execution_time_ms: execTime },
          selectedTileId: transformed.length > 0 
            ? (transformed.some(t => t.tile_id === get().selectedTileId) ? get().selectedTileId : transformed[0].tile_id)
            : null
        });
      }
    } catch (err) {
      console.error("Search error:", err);
    }
  },

  doAnalyze: async (selected) => {
    if (!selected) return set({ activeAnalysis: null });
    set({ activeAnalysis: null });
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
      set({ activeAnalysis: analysis });
    } catch (err) {
      console.error("Analyze error:", err);
    }
  },

  discoverPattern: async (patchId) => {
    set({ isDiscovering: true, discoverySummary: null });
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

      set(prev => ({
        response: { ...prev.response, results: transformed, n_results: transformed.length },
        discoverySummary: data.tactical_summary,
        selectedTileId: transformed.length > 0 ? transformed[0].tile_id : prev.selectedTileId
      }));
    } catch (err) {
      console.error("Discovery error:", err);
    } finally {
      set({ isDiscovering: false });
    }
  },

  recordDecision: (selected, status) => {
    if (!selected) return;
    set(prev => ({
      commits: [
        {
          id: `c-${Math.floor(Math.random() * 9000 + 1000)}`,
          tile_id: selected.tile_id,
          analyst: "OFFICER_DELHI_01",
          status,
          ts: new Date().toISOString().slice(0, 16).replace("T", " "),
        },
        ...prev.commits,
      ]
    }));
  }
}));
