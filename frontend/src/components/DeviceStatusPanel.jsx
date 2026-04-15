import React, { useEffect, useRef } from 'react';

export default function DeviceStatusPanel({ devices }) {
  const scrollRef = useRef(null);
  const d = devices?.data || [];

  const isPaused = useRef(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || d.length <= 6) return;

    let animationId;
    const scroll = () => {
      if (!isPaused.current) {
        if (el.scrollTop >= el.scrollHeight / 2) {
          el.scrollTop = 0;
        } else {
          el.scrollTop += 0.5;
        }
      }
      animationId = requestAnimationFrame(scroll);
    };

    animationId = requestAnimationFrame(scroll);
    return () => cancelAnimationFrame(animationId);
  }, [d]);

  if (d.length === 0) {
    return (
       <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666', fontSize: '13px' }}>
        等待设备连接...
      </div>
    )
  }

  // Double the list for seamless looping
  const displayList = d.length > 6 ? [...d, ...d] : d;

  return (
    <div 
      ref={scrollRef}
      onMouseEnter={() => { isPaused.current = true; }}
      onMouseLeave={() => { isPaused.current = false; }}
      style={{ 
        height: '100%', 
        overflowY: 'hidden', 
        paddingRight: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}
    >
      {displayList.map((dev, i) => {
        const isOnline = dev.status === 'online';
        const color = isOnline ? '#4ade80' : (dev.status === 'timeout' ? '#fbbf24' : '#f87171');
        const statusText = isOnline ? 'ONLINE' : (dev.status === 'timeout' ? 'TIMEOUT' : 'OFFLINE');
        
        return (
          <div key={`${dev.code}-${i}`} style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.05)',
            borderRadius: '6px',
            padding: '8px 12px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexShrink: 0, // Prevent shrinking in the flex container
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
               <div style={{ fontSize: '12px', color: '#e2e8f0', fontWeight: 'bold' }}>{dev.name}</div>
               <div style={{ fontSize: '9px', color: '#64748b' }}>{dev.code}</div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }} />
                  <span style={{ fontSize: '10px', color: color, fontWeight: 'bold', paddingTop: '1px' }}>
                    {statusText}
                  </span>
                </div>
                <div style={{ fontSize: '9px', color: '#475569' }}>
                   {dev.last_data ? dev.last_data.replace('T', ' ').slice(5, 16) : '未知'}
                </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
