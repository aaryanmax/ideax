import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useSearchStore } from '../store/useSearchStore.js';
import { Download, Check, Trash2, X, AlertTriangle, ShieldCheck } from 'lucide-react';

const REGIONS = [
  {
    id: 'delhi',
    name: 'Delhi NCR Tactical Sector',
    description: 'T43RFM Ground Swath + High-Res Sentinel-2 Tiles',
    sizeMB: 28.5,
  },
  {
    id: 'mumbai',
    name: 'Mumbai Littoral',
    description: 'Coastal Surveillance EEZ Boundaries + Sentinel-2 Tiles',
    sizeMB: 14.2,
  },
  {
    id: 'global',
    name: 'Global Vectors',
    description: 'Worldwide Country & Admin Boundaries (No Tiles)',
    sizeMB: 13.5,
  },
];

export default function OfflineRegionManager({ onClose }) {
  const { downloadedRegions, finishDownloadRegion, removeDownloadedRegion } = useSearchStore();
  const [downloading, setDownloading] = useState(null);
  const [progress, setProgress] = useState(0);
  const backdropRef = useRef(null);
  const closeButtonRef = useRef(null);

  // ── Body scroll lock ───────────────────────────────────────────────────────
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  // ── ESC to close ───────────────────────────────────────────────────────────
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // ── Auto-focus close button on mount ──────────────────────────────────────
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  // ── Click-outside backdrop to close ───────────────────────────────────────
  const handleBackdropClick = useCallback((e) => {
    if (e.target === backdropRef.current) onClose();
  }, [onClose]);

  // ── Download simulation ────────────────────────────────────────────────────
  const handleDownload = (regionId) => {
    setDownloading(regionId);
    setProgress(0);
    let current = 0;
    const interval = setInterval(() => {
      current += Math.random() * 15;
      if (current >= 100) {
        clearInterval(interval);
        finishDownloadRegion(regionId);
        setDownloading(null);
      } else {
        setProgress(current);
      }
    }, 200);
  };

  const handleRemove = (regionId) => {
    if (window.confirm('Remove this offline region data?')) {
      removeDownloadedRegion(regionId);
    }
  };

  // ── Modal markup ───────────────────────────────────────────────────────────
  const modal = (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="Offline Data Manager"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        background: 'rgba(0,0,0,0.82)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        userSelect: 'none',
        /* Animation */
        animation: 'orm-fade-in 180ms ease both',
      }}
    >
      <style>{`
        @keyframes orm-fade-in {
          from { opacity: 0; transform: scale(0.96) translateY(8px); }
          to   { opacity: 1; transform: scale(1)    translateY(0);   }
        }
      `}</style>

      {/* Dialog card */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '672px',          /* ~max-w-2xl */
          maxHeight: 'calc(100vh - 2rem)',
          display: 'flex',
          flexDirection: 'column',
          background: '#09090b',      /* zinc-950 */
          border: '1px solid #27272a',/* zinc-800 */
          borderRadius: '6px',
          boxShadow: '0 25px 60px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
      >
        {/* ── Header ── */}
        <div style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid #27272a',
          background: 'rgba(24,24,27,0.6)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={20} style={{ color: '#34d399', flexShrink: 0 }} />
            <div>
              <h2 style={{
                margin: 0,
                fontFamily: 'ui-monospace, SFMono-Regular, monospace',
                fontWeight: 700,
                fontSize: '13px',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: '#f4f4f5',
              }}>
                Offline Data Manager
              </h2>
              <p style={{ margin: 0, fontSize: '10px', color: '#71717a', marginTop: '2px' }}>
                Manage local vector &amp; tile caches for air-gapped deployments
              </p>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close"
            style={{
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              border: '1px solid transparent',
              borderRadius: '4px',
              background: 'transparent',
              color: '#71717a',
              cursor: 'pointer',
              transition: 'background 150ms, color 150ms',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#27272a'; e.currentTarget.style.color = '#e4e4e7'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#71717a'; }}
          >
            <X size={15} />
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          /* Custom scrollbar */
          scrollbarWidth: 'thin',
          scrollbarColor: '#3f3f46 transparent',
        }}>
          {/* Warning banner */}
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
            padding: '8px 12px',
            background: 'rgba(120,53,15,0.25)',
            border: '1px solid rgba(146,64,14,0.45)',
            borderRadius: '4px',
            color: 'rgba(251,191,36,0.85)',
            fontSize: '10px',
            lineHeight: '1.5',
          }}>
            <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: '1px' }} />
            <p style={{ margin: 0 }}>
              Ensure you have sufficient local storage before caching high-resolution Sentinel-2 tiles.
            </p>
          </div>

          {/* Region rows */}
          {REGIONS.map(region => {
            const isDownloaded = downloadedRegions.includes(region.id);
            const isDownloading = downloading === region.id;

            return (
              <div
                key={region.id}
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  padding: '14px 16px',
                  border: '1px solid #27272a',
                  borderRadius: '5px',
                  background: 'rgba(24,24,27,0.35)',
                  transition: 'background 150ms',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(24,24,27,0.6)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(24,24,27,0.35)'; }}
              >
                {/* Info */}
                <div style={{ minWidth: 0, flex: '1 1 200px' }}>
                  <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 700, color: '#e4e4e7' }}>
                    {region.name}
                  </h3>
                  <p style={{ margin: '4px 0 0', fontSize: '10px', color: '#71717a' }}>
                    {region.description}
                  </p>
                  <div style={{ marginTop: '6px', fontSize: '10px', fontWeight: 700, color: '#a1a1aa' }}>
                    EST. SIZE: {region.sizeMB.toFixed(1)} MB
                  </div>
                </div>

                {/* Action */}
                <div style={{ flexShrink: 0 }}>
                  {isDownloading ? (
                    <div style={{ width: '136px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginBottom: '4px' }}>
                        <span style={{ color: '#34d399', fontWeight: 700 }}>DOWNLOADING…</span>
                        <span style={{ color: '#a1a1aa' }}>{Math.min(progress, 100).toFixed(0)}%</span>
                      </div>
                      <div style={{ height: '5px', width: '100%', background: '#27272a', borderRadius: '99px', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.min(progress, 100)}%`,
                          background: '#10b981',
                          transition: 'width 200ms ease-out',
                          borderRadius: '99px',
                        }} />
                      </div>
                    </div>
                  ) : isDownloaded ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        fontSize: '10px',
                        fontWeight: 700,
                        color: '#34d399',
                        background: 'rgba(6,78,59,0.4)',
                        border: '1px solid rgba(52,211,153,0.3)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                      }}>
                        <Check size={11} />
                        READY
                      </span>
                      <button
                        onClick={() => handleRemove(region.id)}
                        title="Remove offline data"
                        aria-label={`Remove ${region.name} offline data`}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '28px',
                          height: '28px',
                          border: '1px solid transparent',
                          borderRadius: '4px',
                          background: 'transparent',
                          color: 'rgba(244,63,94,0.6)',
                          cursor: 'pointer',
                          transition: 'background 150ms, color 150ms',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(136,19,55,0.4)'; e.currentTarget.style.color = '#f43f5e'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(244,63,94,0.6)'; }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleDownload(region.id)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '5px 14px',
                        background: '#27272a',
                        border: '1px solid #52525b',
                        borderRadius: '4px',
                        color: '#e4e4e7',
                        fontSize: '11px',
                        fontWeight: 700,
                        fontFamily: 'inherit',
                        cursor: 'pointer',
                        letterSpacing: '0.04em',
                        transition: 'background 150ms, border-color 150ms',
                        whiteSpace: 'nowrap',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = '#3f3f46'; e.currentTarget.style.borderColor = '#71717a'; }}
                      onMouseLeave={e => { e.currentTarget.style.background = '#27272a'; e.currentTarget.style.borderColor = '#52525b'; }}
                    >
                      <Download size={13} />
                      DOWNLOAD
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  // ── Render into body portal to escape header stacking context ─────────────
  return createPortal(modal, document.body);
}
