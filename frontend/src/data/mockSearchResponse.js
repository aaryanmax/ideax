// Shape is identical to what /search actually returns (SearchResponse).
// Swap useSearch's mock branch for a live searchTiles() call once the
// backend is up — nothing downstream needs to change.
export const MOCK_SEARCH_RESPONSE = {
  query: "new structure near ridge access road",
  top_k: 10,
  n_results: 6,
  execution_time_ms: 38.4,
  results: [
    {
      tile_id: "T44RMR_20240819_S2L2A",
      score: 0.94,
      metadata: {
        tile_id: "T44RMR_20240819_S2L2A",
        latitude: 32.612,
        longitude: 74.881,
        bbox_geojson: null,
        acquisition_date: "2024-08-19",
        sensor: "Sentinel-2 L2A",
        cloud_cover_pct: 3.1,
        image_path: "data/testbed/tiles/T44RMR_20240819.tif",
        embedding_index: 417,
      },
    },
    {
      tile_id: "T44RMR_20240717_S2L2A",
      score: 0.41,
      metadata: {
        tile_id: "T44RMR_20240717_S2L2A",
        latitude: 32.612,
        longitude: 74.881,
        bbox_geojson: null,
        acquisition_date: "2024-07-17",
        sensor: "Sentinel-2 L2A",
        cloud_cover_pct: 18.6,
        image_path: "data/testbed/tiles/T44RMR_20240717.tif",
        embedding_index: 392,
      },
    },
    {
      tile_id: "T44RMS_20240818_S2L2A",
      score: 0.87,
      metadata: {
        tile_id: "T44RMS_20240818_S2L2A",
        latitude: 32.554,
        longitude: 74.812,
        bbox_geojson: null,
        acquisition_date: "2024-08-18",
        sensor: "Sentinel-2 L2A",
        cloud_cover_pct: 1.4,
        image_path: "data/testbed/tiles/T44RMS_20240818.tif",
        embedding_index: 405,
      },
    },
    {
      tile_id: "T44RMR_20240815_S1SAR",
      score: 0.62,
      metadata: {
        tile_id: "T44RMR_20240815_S1SAR",
        latitude: 32.699,
        longitude: 74.755,
        bbox_geojson: null,
        acquisition_date: "2024-08-15",
        sensor: "Sentinel-1 SAR",
        cloud_cover_pct: null,
        image_path: "data/testbed/tiles/T44RMR_20240815.tif",
        embedding_index: 388,
      },
    },
    {
      tile_id: "T44RMQ_20240811_S2L2A",
      score: 0.28,
      metadata: {
        tile_id: "T44RMQ_20240811_S2L2A",
        latitude: 32.601,
        longitude: 74.870,
        bbox_geojson: null,
        acquisition_date: "2024-08-11",
        sensor: "Sentinel-2 L2A",
        cloud_cover_pct: 42.0,
        image_path: "data/testbed/tiles/T44RMQ_20240811.tif",
        embedding_index: 361,
      },
    },
    {
      tile_id: "T44RNR_20240809_S2L2A",
      score: 0.91,
      metadata: {
        tile_id: "T44RNR_20240809_S2L2A",
        latitude: 32.842,
        longitude: 74.669,
        bbox_geojson: null,
        acquisition_date: "2024-08-09",
        sensor: "Sentinel-2 L2A",
        cloud_cover_pct: 6.7,
        image_path: "data/testbed/tiles/T44RNR_20240809.tif",
        embedding_index: 356,
      },
    },
  ],
};

export const MOCK_COMMITS = [
  { id: "c-2291", tile_id: "T44RMR_20240819_S2L2A", analyst: "A", status: "approved", ts: "2024-08-19 06:41" },
  { id: "c-2288", tile_id: "T44RNR_20240809_S2L2A", analyst: "KM", status: "approved", ts: "2024-08-17 21:03" },
  { id: "c-2284", tile_id: "T44RMR_20240717_S2L2A", analyst: "A", status: "rejected", ts: "2024-08-17 09:12" },
  { id: "c-2279", tile_id: "T44RMR_20240815_S1SAR", analyst: "Y", status: "pending", ts: "2024-08-16 14:55" },
];
