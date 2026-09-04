const API_BASE = "http://localhost:8000/api/v1";

/**
 * Execute semantic search over satellite patches via FAISS vector index
 */
export async function searchTiles(query, topK = 6) {
  try {
    const res = await fetch(`${API_BASE}/search/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query.trim(), top_k: topK }),
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
