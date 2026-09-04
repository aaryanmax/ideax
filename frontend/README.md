# ideax-frontend (Member P)

Tactical dashboard UI for semantic retrieval + multi-temporal change
detection, built with Vite + React + Tailwind.

## Run it

```bash
cd frontend        # or wherever you place this folder in the repo
npm install
npm run dev
```

Opens on http://localhost:5173. The dev server proxies `/api/*` to
`http://127.0.0.1:8000` (see `vite.config.js`), so once Y's FastAPI backend
is running locally, the frontend can already reach it.

## Contract

Every request/response shape in `src/lib/api.js` mirrors
`backend/app/schemas.py` field-for-field:

- `searchTiles()` → `POST /search`, body = `SearchRequest`, returns `SearchResponse`
- `detectChange()` → `POST /change`, body = `ChangeDetectionRequest`
- `clusterAround()` → `POST /cluster`, body = `ClusterRequest`

If a field gets renamed on the backend, rename it here too — don't invent
a translation layer.

## Going from mock data to live data

`src/data/mockSearchResponse.js` has the exact shape `/search` returns.
`App.jsx` currently loads it directly. To go live:

```js
// App.jsx
import { useEffect, useState } from "react";
import { searchTiles } from "./lib/api.js";

const [response, setResponse] = useState(null);

useEffect(() => {
  searchTiles({ query, sensor_filter: sensorFilter }).then(setResponse);
}, [query, sensorFilter]);
```

Nothing downstream (`CandidateGallery`, `DetailPanel`, `SplitSlider`) needs
to change — they already consume the `SearchResponse` shape.

## Structure

```
src/
  lib/api.js               fetch wrappers matching the Pydantic schemas
  lib/format.js            swatch color + verdict/status style helpers
  data/mockSearchResponse.js
  components/
    Header.jsx
    SearchPanel.jsx        SearchRequest inputs (query, top_k, filters)
    CandidateGallery.jsx   renders SearchResult[]
    SplitSlider.jsx        before/after comparison for a tile pair
    DetailPanel.jsx        selected tile + approve/reject
    CommitLog.jsx
  App.jsx
  main.jsx
```

## Note on `image_path`

Tiles are rendered as deterministic color swatches (`lib/format.js`) until
there's an endpoint that serves a raster crop for a given `image_path`.
Swap the swatch `<div>` in `SplitSlider.jsx` for an `<img>` once that
endpoint exists.
