/**
 * API layer — every shape here mirrors backend/app/schemas.py field-for-field.
 * This file IS the frontend half of the contract in TEAM_GUIDE.md.
 * Do not rename a field here without renaming it on Y's side too.
 *
 * In dev, vite.config.js proxies /api/* -> http://127.0.0.1:8000, so these
 * calls work whether the backend runs on your machine or a teammate's.
 */

const BASE = "/api";

async function postJSON(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${path} -> ${res.status}: ${text}`);
  }
  return res.json();
}

/**
 * @typedef {Object} TileMetadata
 * @property {string} tile_id
 * @property {number} latitude
 * @property {number} longitude
 * @property {object|null} bbox_geojson
 * @property {string} acquisition_date  ISO 8601 date
 * @property {string} sensor
 * @property {number|null} cloud_cover_pct
 * @property {string} image_path
 * @property {number} embedding_index
 */

/**
 * @typedef {Object} SearchResult
 * @property {string} tile_id
 * @property {number} score  cosine similarity [0,1]
 * @property {TileMetadata} metadata
 */

/**
 * @typedef {Object} SearchResponse
 * @property {string} query
 * @property {number} top_k
 * @property {number} n_results
 * @property {SearchResult[]} results
 * @property {number} execution_time_ms
 */

/**
 * POST /search — body matches SearchRequest.
 * @param {{query: string, top_k?: number, date_range_start?: string|null,
 *          date_range_end?: string|null, sensor_filter?: string|null}} params
 * @returns {Promise<SearchResponse>}
 */
export function searchTiles({
  query,
  top_k = 10,
  date_range_start = null,
  date_range_end = null,
  sensor_filter = null,
}) {
  return postJSON("/search", { query, top_k, date_range_start, date_range_end, sensor_filter });
}

/**
 * POST /change — body matches ChangeDetectionRequest.
 * @param {{tile_id_t1: string, tile_id_t2: string, confidence_threshold?: number}} params
 */
export function detectChange({ tile_id_t1, tile_id_t2, confidence_threshold = 0.5 }) {
  return postJSON("/change", { tile_id_t1, tile_id_t2, confidence_threshold });
}

/**
 * POST /cluster — body matches ClusterRequest.
 * @param {{tile_id: string, radius_km?: number, top_k?: number}} params
 */
export function clusterAround({ tile_id, radius_km = 50, top_k = 10 }) {
  return postJSON("/cluster", { tile_id, radius_km, top_k });
}
