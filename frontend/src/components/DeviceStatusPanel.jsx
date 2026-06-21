import React, { useEffect, useRef } from 'react';

function DeviceCard({ dev, index }) {
  const isOnline = dev.status === 'online';
  const color = isOnline ? '#4ade80' : (dev.status === 'timeout' ? '#fbbf24' : '#f87171');
  const statusText = isOnline ? 'ONLINE' : (dev.status === 'timeout' ? 'TIMEOUT' : 'OFFLINE');

  return (
    <div
      key={`${dev.code}-${index}`}
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: '6px',
        padding: '8px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ fontSize: '12px', color: '#e2e8f0', fontWeight: 'bold' }}>{dev.name}</div>
        <div style={{ fontSize: '9px', color: '#64748b' }}>{dev.code}</div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }} />
          <span style={{ fontSize: '10px', color, fontWeight: 'bold', paddingTop: '1px' }}>
            {statusText}
          </span>
        </div>
        <div style={{ fontSize: '9px', color: '#475569' }}>
          {dev.last_data ? dev.last_data.replace('T', ' ').slice(5, 16) : '未知'}
        </div>
      </div>
    </div>
  );
}

export default function DeviceStatusPanel({ devices }) {
  const viewportRef = useRef(null);
  const trackRef = useRef(null);
  const singleGroupRef = useRef(null);
  const pausedRef = useRef(false);
  const d = devices?.data || [];
  const shouldLoop = d.length >= 6;

  useEffect(() => {
    const viewport = viewportRef.current;
    const track = trackRef.current;
    const singleGroup = singleGroupRef.current;
    if (!viewport || !track || !singleGroup) return;

    let frame = 0;
    let offset = 0;
    let loopHeight = 0;

    const resetTrack = () => {
      offset = 0;
      track.style.transform = 'translate3d(0, 0, 0)';
    };

    const measure = () => {
      loopHeight = shouldLoop ? singleGroup.getBoundingClientRect().height : 0;
      if (!shouldLoop || loopHeight <= viewport.clientHeight) {
        resetTrack();
      }
    };

    const tick = () => {
      if (shouldLoop && loopHeight > viewport.clientHeight && !pausedRef.current) {
        offset += 0.45;
        if (offset >= loopHeight) {
          offset = 0;
        }
        track.style.transform = `translate3d(0, ${-offset}px, 0)`;
      }
      frame = requestAnimationFrame(tick);
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(viewport);
    observer.observe(singleGroup);
    frame = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [shouldLoop, d]);

  if (d.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666', fontSize: '13px' }}>
        等待设备连接...
      </div>
    );
  }

  return (
    <div
      ref={viewportRef}
      onMouseEnter={() => { pausedRef.current = true; }}
      onMouseLeave={() => { pausedRef.current = false; }}
      style={{
        height: '100%',
        overflow: 'hidden',
        paddingRight: '4px',
        position: 'relative',
      }}
    >
      <div
        ref={trackRef}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          willChange: 'transform',
        }}
      >
        <div
          ref={singleGroupRef}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {d.map((dev, index) => <DeviceCard key={`${dev.code}-primary-${index}`} dev={dev} index={index} />)}
        </div>

        {shouldLoop ? (
          <div
            aria-hidden="true"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            {d.map((dev, index) => <DeviceCard key={`${dev.code}-clone-${index}`} dev={dev} index={index} />)}
          </div>
        ) : null}
      </div>
    </div>
  );
}
