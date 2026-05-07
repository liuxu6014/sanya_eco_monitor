import React from 'react';

export default function RainGaugePanel({ rainData }) {
  const DEVICE_MAP = {
    '16132920': '杧果林站 (4G)',
    '16132921': '橡胶林站 (4G)',
    '16132922': '次生林站 (4G)',
  };

  // Ensure we always have these 3 stations visualized
  const displayCodes = ['16132920', '16132921', '16132922'];
  const formatUpdatedAt = (value) => {
    if (!value) return '暂无数据';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '暂无数据';
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', height: '100%', padding: '4px 0' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }} className="no-scrollbar">
        {displayCodes.map(code => {
          const d = rainData?.[code];
          const name = DEVICE_MAP[code] || `${code} 雨量站`;
          
          return (
            <div key={code} style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '6px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ fontSize: '13px', color: '#e2e8f0', fontWeight: 'bold' }}>{name}</div>
                <div style={{ fontSize: '10px', color: '#64748b' }}>
                   ID: {code} | {formatUpdatedAt(d?.updated_at)}
                </div>
              </div>
              
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '18px', color: d ? '#38bdf8' : '#475569', fontWeight: 'bold' }}>
                  {d ? (typeof d.rainfall === 'number' ? d.rainfall.toFixed(1) : '0.0') : '—'}
                  <span style={{ fontSize: '10px', color: '#888', marginLeft: '2px', fontWeight: 'normal' }}>mm</span>
                </div>
                <div style={{ fontSize: '10px', color: d?.status === 'online' ? '#4ade80' : '#475569' }}>
                  ● {d?.status === 'online' ? '实时降雨' : '离线/停报'}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
