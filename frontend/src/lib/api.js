const API_BASE = "http://localhost:8000/api/v1";

/**
 * Execute semantic search over satellite patches via FAISS vector index
 */
export async function searchTiles(query, topK = 6, dataset = "all") {
  try {
    const res = await fetch(`${API_BASE}/search/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query.trim(), top_k: topK, dataset }),
    });
    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("API error during searchTiles:", err);
    throw err;
  }
}

/**
 * Run bitemporal change detection & tactical classification on a selected patch
 */
export async function analyzeChange(colOff = 4500, rowOff = 4500, force = true) {
  try {
    const res = await fetch(`${API_BASE}/analyze/change`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        col_off: colOff,
        row_off: rowOff,
        width: 512,
        height: 512,
        force: force,
      }),
    });
    if (!res.ok) throw new Error(`Change analysis failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("API error during analyzeChange:", err);
    throw err;
  }
}

/**
 * Retrieve audit trail records from SQLite
 */
export async function getAuditLog(status = null, limit = 50) {
  try {
    let url = `${API_BASE}/audit/log?limit=${limit}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Fetch audit log failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("API error during getAuditLog:", err);
    throw err;
  }
}

/**
 * Commit target verification decision to audit trail
 */
export async function commitTarget(payload) {
  try {
    const res = await fetch(`${API_BASE}/audit/commit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Commit target failed: ${res.statusText} (${errText})`);
    }
    return await res.json();
  } catch (err) {
    console.error("API error during commitTarget:", err);
    throw err;
  }
}

/**
 * Image-to-Image Discovery: Find semantically aligned sites matching a baseline patch
 */
export async function findSimilarSites(patchId, topK = 6, cluster = true) {
  try {
    const res = await fetch(`${API_BASE}/search/similar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patch_id: patchId,
        top_k: topK,
        cluster_results: cluster,
        eps_km: 15.0,
        min_samples: 2,
      }),
    });
    if (!res.ok) throw new Error(`Discovery failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("API error during findSimilarSites:", err);
    throw err;
  }
}
