import { useEffect, useState, useRef } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Maximize2, Minimize2, MapPin, AlertTriangle, X, Crosshair, CheckCircle2 } from "lucide-react";
import { verdictFor, VERDICT_STYLE } from "../../lib/format.js";
import { triggerHaptic } from "../../lib/haptics.js";

/**
 * Validate whether coordinates fall within indexed tactical surveillance coverage
 */
export function getSectorForCoordinates(lat, lng) {
  // Delhi NCR Tactical Sector (lat: ~28.17-28.72, lon: ~76.25-76.87)
  if (lat >= 27.8 && lat <= 29.2 && lng >= 75.8 && lng <= 77.5) {
    return {
      available: true,
      sectorId: "delhi",
      name: "Delhi NCR Tactical Sector",
      center: [28.536, 76.457]
    };
  }
  // Mumbai Littoral Sector (lat: ~18.90-19.25, lon: ~72.78-73.05)
  if (lat >= 18.6 && lat <= 19.6 && lng >= 72.5 && lng <= 73.4) {
    return {
      available: true,
      sectorId: "mumbai",
      name: "Mumbai Littoral Sector",
      center: [19.041, 72.827]
    };
  }
  return {
    available: false,
    reason: `Coordinates [${lat.toFixed(3)}°N, ${lng.toFixed(3)}°E] fall outside active surveillance coverage. Indexed data is currently available for Delhi NCR (28.5°N, 76.5°E) and Mumbai Littoral (19.0°N, 72.8°E).`
  };
}

function MapInterface({ 
  activeLocation, 
  activeCandidateId, 
  onDatasetFilterChange, 
  onFetchReject,
  onFetchSuccess,
  isExpanded 
}) {
  const map = useMap();
  const [isUserPanned, setIsUserPanned] = useState(false);
  const [rejection, setRejection] = useState(null);
  const [successInfo, setSuccessInfo] = useState(null);

  const lastFlownIdRef = useRef(null);
  const lastFlownCoordsRef = useRef(null);

  // Resize check when map container mounts or expands/collapses
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 250);
    return () => clearTimeout(timer);
  }, [map, isExpanded]);

  // Smooth flyTo candidate when selected or when new candidate dataset is loaded
  useEffect(() => {
    if (!activeLocation) return;
    const coordsKey = `${activeLocation[0].toFixed(4)},${activeLocation[1].toFixed(4)}`;
    
    const candidateChanged = activeCandidateId && lastFlownIdRef.current !== activeCandidateId;
    const coordsChanged = coordsKey !== lastFlownCoordsRef.current;
    
    if (candidateChanged || (!isUserPanned && coordsChanged)) {
      lastFlownIdRef.current = activeCandidateId;
      lastFlownCoordsRef.current = coordsKey;
      setIsUserPanned(false);
      setRejection(null);
      map.flyTo(activeLocation, Math.max(map.getZoom(), 13), { 
        animate: true,
        duration: 1.0 
      });
    }
  }, [activeCandidateId, activeLocation, isUserPanned, map]);

  // Track user manual panning
  useMapEvents({
    dragstart: () => {
      setIsUserPanned(true);
      setSuccessInfo(null);
    }
  });

  const handleFetchHere = () => {
    const center = map.getCenter();
    const sectorCheck = getSectorForCoordinates(center.lat, center.lng);

    if (!sectorCheck.available) {
      // REJECT REQUEST AND STAY EXACTLY THERE
      setIsUserPanned(true);
      setSuccessInfo(null);
      setRejection({
        lat: center.lat,
        lng: center.lng,
        message: sectorCheck.reason
      });
      triggerHaptic('reject');
      if (onFetchReject) {
        onFetchReject(sectorCheck.reason);
      }
      return;
    }

    // ACCEPT REQUEST
    setRejection(null);
    setSuccessInfo(`Acquiring ${sectorCheck.name}...`);
    setIsUserPanned(false);
    triggerHaptic('scan');
    
    if (onFetchSuccess) {
      onFetchSuccess(sectorCheck);
    }
    if (onDatasetFilterChange) {
      onDatasetFilterChange(sectorCheck.sectorId);
    }
  };

  const handleRecenter = () => {
    if (activeLocation) {
      setIsUserPanned(false);
      setRejection(null);
      map.flyTo(activeLocation, Math.max(map.getZoom(), 13), { animate: true, duration: 0.8 });
    }
  };

  return (
    <>
      {/* Rejection Alert: Map stays here and displays why */}
      {rejection && (
        <div className="absolute top-2 left-2 right-2 sm:left-1/2 sm:-translate-x-1/2 sm:w-[340px] z-[400] flex flex-col gap-1 p-2 bg-zinc-950/95 border border-rose-500/70 text-rose-200 rounded shadow-2xl backdrop-blur-md animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-rose-400 uppercase font-mono">
              <AlertTriangle size={13} className="text-rose-400 shrink-0" />
              <span>Coverage Missing (Rejected)</span>
            </div>
            <button 
              onClick={() => setRejection(null)} 
              className="text-zinc-400 hover:text-white p-0.5"
              title="Dismiss"
            >
              <X size={12} />
            </button>
          </div>
          <p className="text-[10px] font-mono leading-tight text-zinc-300 text-left">
            {rejection.message}
          </p>
        </div>
      )}

      {/* Manual Pan Actions: Fetch Here & Re-center */}
      {isUserPanned && !rejection && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[400] flex items-center gap-1.5">
          <button 
            onClick={handleFetchHere}
            className="flex items-center gap-1.5 bg-zinc-900/95 hover:bg-zinc-800 text-zinc-100 px-3 py-1.5 rounded-full shadow-xl border border-emerald-500/60 hover:border-emerald-400 text-xs font-mono font-medium tracking-wider transition-all hover:scale-105 active:scale-95"
            title="Scan currently visible map area"
          >
            <MapPin size={13} className="text-emerald-400 shrink-0" />
            <span>FETCH HERE</span>
          </button>
          {activeLocation && (
            <button
              onClick={handleRecenter}
              className="flex items-center gap-1 bg-zinc-900/95 hover:bg-zinc-800 text-zinc-300 hover:text-white px-2 py-1.5 rounded-full shadow-xl border border-zinc-700 text-xs font-mono tracking-wider transition-all hover:scale-105 active:scale-95"
              title="Re-center on active target"
            >
              <Crosshair size={13} className="text-amber-400 shrink-0" />
            </button>
          )}
        </div>
      )}

      {/* Success Status Indicator */}
      {successInfo && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[400] flex items-center gap-1.5 px-3 py-1 bg-emerald-950/95 border border-emerald-500/60 text-emerald-300 rounded-full text-xs font-mono shadow-xl backdrop-blur-md">
          <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
          <span>{successInfo}</span>
        </div>
      )}
    </>
  );
}

export default function TacticalMap({ 
  candidates = [], 
  total = 0, 
  activeCandidateId, 
  onSelect, 
  threshold,
  className = "",
  style = {},
  hideHeader = false,
  isExpanded = false,
  onToggleExpand,
  onDatasetFilterChange,
  onFetchReject,
  onFetchSuccess
}) {
  const activeCandidate = candidates.find(c => c.tile_id === activeCandidateId);
  const activeLocation = activeCandidate 
    ? [activeCandidate.metadata.latitude, activeCandidate.metadata.longitude]
    : (candidates.length > 0 ? [candidates[0].metadata.latitude, candidates[0].metadata.longitude] : null);

  const initialCenter = activeLocation || [28.536, 76.457];

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
        <MapContainer 
          center={initialCenter} 
          zoom={13} 
          zoomControl={isExpanded} 
          attributionControl={false} 
          style={{ height: "100%", width: "100%", zIndex: 0 }}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=cb1_2wrn_1_e49a6d427e83ef6163d8f9e4"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          />
          {candidates.map(candidate => {
            const isActive = candidate.tile_id === activeCandidateId;
            const cv = VERDICT_STYLE[verdictFor(candidate.score, threshold)];
            
            const size = isActive ? 18 : 12;
            const glowClass = isActive ? "animate-pulse" : "";
            
            let dotColor = cv.dot;
            let borderColor = 'rgba(255,255,255,0.3)';
            let glow = '4px rgba(0,0,0,0.5)';
            if (candidate.cluster_id !== undefined) {
              if (candidate.cluster_id === 0) dotColor = '#34d399';
              else if (candidate.cluster_id === 1) dotColor = '#22d3ee';
              else if (candidate.cluster_id === -1) { dotColor = 'rgba(245, 158, 11, 0.3)'; borderColor = '#f59e0b'; }
              else dotColor = '#818cf8';
            }
            if (isActive) {
               dotColor = '#10b981';
               borderColor = 'white';
               glow = '15px 5px rgba(16,185,129,0.6)';
            }
            
            const html = `
              <div class="${glowClass}" style="
                background-color: ${dotColor};
                width: ${size}px;
                height: ${size}px;
                border-radius: 50%;
                border: 2px solid ${borderColor};
                box-shadow: 0 0 ${glow};
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
          <MapInterface 
            activeLocation={activeLocation} 
            activeCandidateId={activeCandidateId}
            onDatasetFilterChange={onDatasetFilterChange}
            onFetchReject={onFetchReject}
            onFetchSuccess={onFetchSuccess}
            isExpanded={isExpanded}
          />
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
