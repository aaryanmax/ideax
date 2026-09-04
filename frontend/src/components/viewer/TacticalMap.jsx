import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Maximize2, Minimize2 } from "lucide-react";
import { verdictFor, VERDICT_STYLE } from "../../lib/format.js";

function MapUpdater({ activeLocation }) {
  const map = useMap();
  useEffect(() => {
    // Force a resize check just in case the container size wasn't ready on first mount
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 250);
    
    if (activeLocation) {
      map.flyTo(activeLocation, 13, { animate: true });
    }
    return () => clearTimeout(timer);
  }, [activeLocation, map]);
  return null;
}

export default function TacticalMap({ 
  candidates, 
  total, 
  activeCandidateId, 
  onSelect, 
  threshold,
  className = "",
  style = {},
  hideHeader = false,
  isExpanded = false,
  onToggleExpand
}) {
  const activeCandidate = candidates.find(c => c.tile_id === activeCandidateId);
  const activeLocation = activeCandidate 
    ? [activeCandidate.metadata.latitude, activeCandidate.metadata.longitude]
    : (candidates.length > 0 ? [candidates[0].metadata.latitude, candidates[0].metadata.longitude] : [28.5, 76.4]);

  return (
    <div className={`flex flex-col relative ${className}`} style={style}>
      {!hideHeader && (
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-cond text-sm font-semibold tracking-wide text-ink">Tactical Map View</h2>
          <span className="font-mono text-[10px] text-faint">
            {candidates.length} of {total}
          </span>
        </div>
      )}
      <div className="flex-1 rounded-sm border border-border overflow-hidden relative z-0" style={{ height: "100%", minHeight: "100px" }}>
        <MapContainer center={activeLocation} zoom={13} zoomControl={isExpanded} attributionControl={false} style={{ height: "100%", width: "100%", zIndex: 0 }}>
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=cb1_2wrn_1_e49a6d427e83ef6163d8f9e4"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          />
          {candidates.map(candidate => {
            const isActive = candidate.tile_id === activeCandidateId;
            const cv = VERDICT_STYLE[verdictFor(candidate.score, threshold)];
            
            const size = isActive ? 18 : 12;
            const glowClass = isActive ? "animate-pulse" : "";
            
            const html = `
              <div class="${glowClass}" style="
                background-color: ${isActive ? '#10b981' : cv.dot};
                width: ${size}px;
                height: ${size}px;
                border-radius: 50%;
                border: 2px solid ${isActive ? 'white' : 'rgba(255,255,255,0.3)'};
                box-shadow: 0 0 ${isActive ? '15px 5px rgba(16,185,129,0.6)' : '4px rgba(0,0,0,0.5)'};
                transition: all 0.2s ease-in-out;
              "></div>
            `;
            
            const icon = L.divIcon({
              html,
              className: '', 
              iconSize: [size, size],
              iconAnchor: [size / 2, size / 2]
            });

            return (
              <Marker
                key={candidate.tile_id}
                position={[candidate.metadata.latitude, candidate.metadata.longitude]}
                icon={icon}
                eventHandlers={{
                  click: () => onSelect(candidate.tile_id)
                }}
              />
            );
          })}
          <MapUpdater activeLocation={activeLocation} />
        </MapContainer>
        
        {onToggleExpand && (
          <button 
            onClick={onToggleExpand} 
            className="absolute top-2 right-2 z-[400] bg-zinc-900/90 hover:bg-zinc-800 p-1.5 rounded text-faint hover:text-ink ring-1 ring-zinc-700/50 transition-colors shadow-lg"
            title={isExpanded ? "Collapse Map" : "Expand Map"}
          >
             {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        )}
      </div>
    </div>
  );
}
