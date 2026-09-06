import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

/**
 * Slippy tile to latitude/longitude (WGS84)
 */
function num2deg(x, y, z) {
  const n = Math.pow(2, z);
  const lonDeg = (x / n) * 360 - 180;
  const latRad = Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n)));
  const latDeg = (latRad * 180) / Math.PI;
  return { lat: latDeg, lon: lonDeg };
}

/**
 * Draw procedural dark tactical vector grid tile directly on an HTML5 canvas
 */
function drawTacticalCanvas(ctx, coords, size, showGrid) {
  const width = size.x;
  const height = size.y;

  // Clean Dark Base Fill
  ctx.fillStyle = "#080c14";
  ctx.fillRect(0, 0, width, height);

  if (!showGrid) return;

  // Very subtle outer border to distinguish tiles faintly
  ctx.strokeStyle = "rgba(20, 35, 55, 0.4)";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

  // Subtle tactical crosshair at tile center
  const midX = width / 2;
  const midY = height / 2;
  ctx.strokeStyle = "rgba(30, 50, 75, 0.35)";
  ctx.beginPath();
  ctx.moveTo(midX - 8, midY);
  ctx.lineTo(midX + 8, midY);
  ctx.moveTo(midX, midY - 8);
  ctx.lineTo(midX, midY + 8);
  ctx.stroke();

  // Subtle tactical corner reticles
  const rLen = 5;
  ctx.strokeStyle = "rgba(52, 211, 153, 0.25)";
  ctx.beginPath();
  // Top-left
  ctx.moveTo(2, 2 + rLen); ctx.lineTo(2, 2); ctx.lineTo(2 + rLen, 2);
  // Top-right
  ctx.moveTo(width - 2 - rLen, 2); ctx.lineTo(width - 2, 2); ctx.lineTo(width - 2, 2 + rLen);
  // Bottom-left
  ctx.moveTo(2, height - 2 - rLen); ctx.lineTo(2, height - 2); ctx.lineTo(2 + rLen, height - 2);
  // Bottom-right
  ctx.moveTo(width - 2 - rLen, height - 2); ctx.lineTo(width - 2, height - 2); ctx.lineTo(width - 2, height - 2 - rLen);
  ctx.stroke();

  // Overlay coordinate markings
  try {
    const { lat, lon } = num2deg(coords.x, coords.y, coords.z);
    ctx.font = '9px "IBM Plex Mono", monospace';
    ctx.fillStyle = "rgba(80, 110, 140, 0.45)";
    const latStr = `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? "N" : "S"}`;
    const lonStr = `${Math.abs(lon).toFixed(2)}°${lon >= 0 ? "E" : "W"}`;
    ctx.fillText(`${latStr} ${lonStr}`, 8, height - 8);
  } catch (e) {
    // ignore
  }
}

/**
 * TacticalCanvasGridLayer: A custom Leaflet GridLayer for air-gapped tactical operations.
 * - Procedural dark vector tactical canvas rendered directly on the client
 * - Zero network dependencies; 0 broken tile / 404 errors
 */
export default function TacticalCanvasGridLayer({ showGrid = true }) {
  const map = useMap();

  useEffect(() => {
    const TacticalGridLayer = L.GridLayer.extend({
      createTile: function (coords, done) {
        const tile = document.createElement("canvas");
        const tileSize = this.getTileSize();
        tile.width = tileSize.x;
        tile.height = tileSize.y;
        const ctx = tile.getContext("2d");

        drawTacticalCanvas(ctx, coords, tileSize, showGrid);
        done(null, tile);
        return tile;
      },
    });

    const tacticalLayer = new TacticalGridLayer({
      tileSize: 256,
      updateWhenIdle: false,
      zIndex: 1,
    });

    tacticalLayer.addTo(map);

    return () => {
      map.removeLayer(tacticalLayer);
    };
  }, [map, showGrid]);

  return null;
}
