import { create } from 'zustand';
import { MOCK_COMMITS, MOCK_SEARCH_RESPONSE } from '../data/mockSearchResponse.js';
import { searchTiles, analyzeChange, getAuditLog, findSimilarSites } from '../lib/api.js';

const getInitialMockResults = () => {
  return MOCK_SEARCH_RESPONSE.results.map((r, idx) => ({
    ...r,
    thumbnail_url: r.thumbnail_url || null,
    t1_thumbnail: null,
    t2_thumbnail: null,
    col_off: 4000 + (idx % 5) * 512,
    row_off: 4000 + Math.floor(idx / 5) * 512,
    verified: r.score > 0.20,
  }));
};

const initialMockResults = getInitialMockResults();

export const useSearchStore = create((set, get) => ({
  query: "seasonal crop fields or agricultural land",
  debouncedQuery: "seasonal crop fields or agricultural land",
  response: {
    results: initialMockResults,
    n_results: initialMockResults.length,
    execution_time_ms: 18.5
  },
  minConfidence: 0,
  sensorFilter: null,
  datasetFilter: "none",
  selectedTileId: initialMockResults[0]?.tile_id ?? null,
  commits: MOCK_COMMITS,
  activeAnalysis: {
    classification: {
      classification: "Dense Urban / Built-up Sector",
      confidence: 0.89,
      risk_level: "HIGH",
    },
    change_detected: true,
    phenological_shift: 0.34,
    metrics: {
      ndvi_delta: -0.28,
      ndwi_delta: 0.05,
      nbr_delta: -0.19,
    },
    coordinates: [32.612, 74.881],
  },
  runTour: false,
  discoverySummary: null,
  isDiscovering: false,
  isSearching: false,
  tacticalAlert: null,
  resolution: "10m", // "10m", "20m", "60m"
  mapMode: "airgapped", // "airgapped" (local vector + cached tiles) | "online" (WAN CartoDB fallback)
  vectorLayers: {
    boundaries: true,
    districts: true,
    expressways: true,
    waterways: true,
    grid: true,
  },
  showTooltips: true,
  downloadedRegions: (() => {
    try {
      const saved = localStorage.getItem('vayu_offline_regions');
      return saved ? JSON.parse(saved) : ['delhi'];
    } catch {
      return ['delhi'];
    }
  })(),
  uiScale: (() => {
    try {
      const saved = localStorage.getItem('vayu_ui_scale');
      const val = saved ? parseInt(saved, 10) : 100;
      if (typeof document !== 'undefined') {
        document.documentElement.style.zoom = `${val}%`;
      }
      return val;
    } catch {
      return 100;
    }
  })(),

  availableDatasets: [
    { value: "none", label: "Auto (Map View)" },
    { value: "all", label: "All India" },
    { value: "delhi", label: "Delhi, NCR" },
    { value: "mumbai", label: "Mumbai, MH" },
  ],

  setQuery: (query) => set({ query }),
  setDebouncedQuery: (debouncedQuery) => set({ debouncedQuery }),
  setMinConfidence: (minConfidence) => set({ minConfidence }),
  setSensorFilter: (sensorFilter) => set({ sensorFilter }),
  setDatasetFilter: (datasetFilter) => set({ datasetFilter }),
  setSelectedTileId: (selectedTileId) => set({ selectedTileId }),
  setRunTour: (runTour) => set({ runTour }),
  setDiscoverySummary: (discoverySummary) => set({ discoverySummary }),
  setTacticalAlert: (tacticalAlert) => set({ tacticalAlert }),
  setResolution: (resolution) => set({ resolution }),
  setCommits: (commits) => set({ commits }),
  setMapMode: (mapMode) => set({ mapMode }),
  setShowTooltips: (showTooltips) => set({ showTooltips }),
  toggleVectorLayer: (layerKey) =>
    set((state) => ({
      vectorLayers: {
        ...state.vectorLayers,
        [layerKey]: !state.vectorLayers[layerKey],
      },
    })),

  startDownloadRegion: (regionId) => {
    // We could add a downloading state map here, but for simplicity, we handle UI in the component
  },
  finishDownloadRegion: (regionId) => {
    set((state) => {
      const newRegions = [...new Set([...state.downloadedRegions, regionId])];
      try {
        localStorage.setItem('vayu_offline_regions', JSON.stringify(newRegions));
      } catch (e) {}
      return { downloadedRegions: newRegions };
    });
  },
  removeDownloadedRegion: (regionId) => {
    set((state) => {
      const newRegions = state.downloadedRegions.filter(id => id !== regionId);
      try {
        localStorage.setItem('vayu_offline_regions', JSON.stringify(newRegions));
      } catch (e) {}
      return { downloadedRegions: newRegions };
    });
  },

  setUiScale: (val) => {
    const clamped = Math.min(150, Math.max(70, val));
    try {
      localStorage.setItem('vayu_ui_scale', String(clamped));
    } catch {
      // ignore
    }
    if (typeof document !== 'undefined') {
      document.documentElement.style.zoom = `${clamped}%`;
      window.dispatchEvent(new Event('resize'));
    }
    set({ uiScale: clamped });
  },

  increaseUiScale: () => {
    const scales = [75, 85, 90, 100, 110, 125, 140];
    const current = get().uiScale;
    const next = scales.find(s => s > current) || 140;
    get().setUiScale(next);
  },

  decreaseUiScale: () => {
    const scales = [75, 85, 90, 100, 110, 125, 140];
    const current = get().uiScale;
    const prev = [...scales].reverse().find(s => s < current) || 75;
    get().setUiScale(prev);
  },

  resetUiScale: () => {
    get().setUiScale(100);
  },

  applyPrompt: (promptText) => {
    set({ query: promptText, debouncedQuery: promptText });
    get().doSearch();
  },

  fetchDatasets: async () => {
    try {
      const { getDatasets } = await import('../lib/api.js');
      const data = await getDatasets();
      if (data?.datasets?.length > 0) {
        set({ availableDatasets: data.datasets });
      }
    } catch (err) {
      console.warn("Could not load dynamic datasets:", err);
    }
  },

  fetchAuditLog: async () => {
    try {
      const data = await getAuditLog(null, 50);
      if (data?.records?.length > 0) set({ commits: data.records });
    } catch (err) {
      console.warn("Could not load audit log, maintaining local ledger:", err);
    }
  },

  doSearch: async () => {
    const { debouncedQuery, datasetFilter } = get();
    set({ isSearching: true });
    try {
      const start = performance.now();
      const geojson = await searchTiles(debouncedQuery, 6, datasetFilter);
      const execTime = performance.now() - start;

      if (geojson?.features) {
        const transformed = geojson.features.map((feature, idx) => {
          const patchId = feature.properties.patch_id || `patch_${idx}`;
          // Prefer t2_thumbnail (the "after" scene) for gallery preview; fall back to thumbnail_url then constructed path
          const rawT2 = feature.properties.t2_thumbnail;
          const rawThumb = feature.properties.thumbnail_url;
          const bestRaw = rawT2 || rawThumb;
          const thumbUrl = bestRaw
            ? (bestRaw.startsWith("http") ? bestRaw : `http://localhost:8000${bestRaw}`)
            : `http://localhost:8000/static/tiles/thumbnails/${patchId}_t2.png`;

          const t1Date = feature.properties.t1_date || "T1";
          const t2Date = feature.properties.t2_date || feature.properties.acquisition_date || "T2";

          return {
            tile_id: patchId,
            score: feature.properties.similarity_score,
            thumbnail_url: thumbUrl,
            t1_thumbnail: feature.properties.t1_thumbnail,
            t2_thumbnail: feature.properties.t2_thumbnail,
            t1_date: t1Date,
            t2_date: t2Date,
            col_off: feature.properties.col_off,
            row_off: feature.properties.row_off,
            metadata: {
              latitude: feature.properties.center ? feature.properties.center[0] : 28.536,
              longitude: feature.properties.center ? feature.properties.center[1] : 76.457,
              acquisition_date: t2Date,
              t1_date: t1Date,
              t2_date: t2Date,
              sensor: feature.properties.sensor || "Sentinel-2 L2A",
              cloud_cover_pct: feature.properties.cloud_cover_pct || 0,
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
      console.warn("Live search API unavailable, applying cached intelligence fallback:", err);
      const mockResults = getInitialMockResults();
      set({
        response: {
          results: mockResults,
          n_results: mockResults.length,
          execution_time_ms: 18.5,
        },
        selectedTileId: mockResults[0]?.tile_id ?? null
      });
    } finally {
      set({ isSearching: false });
    }
  },

  doAnalyze: async (selected) => {
    if (!selected) return set({ activeAnalysis: null });
    try {
      let colOff = selected.col_off;
      let rowOff = selected.row_off;

      if (colOff == null || rowOff == null) {
        const matchNum = selected.tile_id.match(/patch_([a-zA-Z0-9]+)$/);
        if (matchNum) {
          const idx = parseInt(matchNum[1], 10);
          if (!isNaN(idx)) {
            colOff = 4000 + (idx % 5) * 512;
            rowOff = 4000 + Math.floor(idx / 5) * 512;
          } else {
            colOff = 4500;
            rowOff = 4500;
          }
        } else {
          colOff = 4500;
          rowOff = 4500;
        }
      }

      const analysis = await analyzeChange(colOff, rowOff, true, get().resolution, selected.tile_id);
      set({ activeAnalysis: analysis });
    } catch (err) {
      console.warn("Live analyze API unavailable, applying cached tactical classification:", err);
      set({
        activeAnalysis: {
          classification: {
            classification: "Dense Urban / Built-up Sector",
            confidence: 0.89,
            risk_level: "HIGH",
          },
          change_detected: true,
          phenological_shift: 0.34,
          metrics: {
            ndvi_delta: -0.28,
            ndwi_delta: 0.05,
            nbr_delta: -0.19,
          },
          coordinates: [selected.metadata?.latitude ?? 28.536, selected.metadata?.longitude ?? 76.457],
        }
      });
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
