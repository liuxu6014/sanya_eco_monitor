import React, { useEffect, useMemo, useRef, useState } from 'react';

function formatMetricValue(value) {
  if (value == null) return '--';
  const numeric = Number(value);
  return Number.isNaN(numeric) ? '--' : numeric.toFixed(2);
}

function formatLatestUpdatedAt(value) {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export default function RunoffPanel({ runoffStations, deviceMeta = [] }) {
  const devices = useMemo(
    () => (Array.isArray(deviceMeta) ? deviceMeta : []).filter((item) => item?.code),
    [deviceMeta],
  );
  const deviceCodes = devices.map((item) => item.code);
  const [activeCode, setActiveCode] = useState(deviceCodes[0] || '');
  const [isAutoPlay, setIsAutoPlay] = useState(true);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!deviceCodes.length) {
      setActiveCode('');
      return;
    }
    if (!deviceCodes.includes(activeCode)) {
      setActiveCode(deviceCodes[0]);
    }
  }, [activeCode, deviceCodes]);

  useEffect(() => {
    if (!isAutoPlay || deviceCodes.length <= 1) return undefined;

    timerRef.current = setInterval(() => {
      setActiveCode((current) => {
        const index = deviceCodes.indexOf(current);
        const nextIndex = index >= 0 ? (index + 1) % deviceCodes.length : 0;
        return deviceCodes[nextIndex];
      });
    }, 5000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [deviceCodes, isAutoPlay]);

  const handleManualSelect = (code) => {
    setActiveCode(code);
    setIsAutoPlay(false);

    if (timerRef.current) clearInterval(timerRef.current);
    setTimeout(() => setIsAutoPlay(true), 30000);
  };

  const activeDevice = devices.find((item) => item.code === activeCode) || null;
  const data = activeCode ? runoffStations?.[activeCode] || null : null;
  const showRainfallMetric = data?.rainfall != null;

  const metrics = [
    { label: '当前流速', key: 'flow_speed', unit: 'm/s', color: '#4ade80' },
    { label: '瞬时流量', key: 'flow_rate', unit: 'm³/s', color: '#38bdf8' },
    { label: '累计流量', key: 'total_flow', unit: 'm³', color: '#38bdf8' },
    { label: '水位', key: 'water_level', unit: 'm', color: '#facc15' },
    { label: '含沙量', key: 'sand_content', unit: 'kg/L', color: '#fb923c' },
    { label: '液位压力', key: 'liquid_pressure', unit: 'kPa', color: '#c084fc' },
    { label: '当前径流', key: 'runoff', unit: 'm³/min', color: '#4ade80' },
    ...(showRainfallMetric ? [{ label: '今日累计雨量', key: 'rainfall', unit: 'mm', color: '#60a5fa' }] : []),
  ];

  return (
    <div
      style={{ display: 'flex', flexDirection: 'column', gap: '6px', height: '100%', padding: '4px 0' }}
      onMouseEnter={() => setIsAutoPlay(false)}
      onMouseLeave={() => setIsAutoPlay(true)}
    >
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {devices.map((device) => (
          <div
            key={device.code}
            onClick={() => handleManualSelect(device.code)}
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              borderRadius: '4px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              background: activeCode === device.code ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.05)',
              border: activeCode === device.code ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
              color: activeCode === device.code ? '#38bdf8' : '#888',
              transition: 'all 0.2s',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {device.panel_name || device.name || device.code}
            {activeCode === device.code && isAutoPlay && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  height: '2px',
                  background: '#38bdf8',
                  animation: 'runoffProgress 5s linear forwards',
                }}
              />
            )}
          </div>
        ))}
      </div>

      <style>{`
        @keyframes runoffProgress {
          from { width: 0% }
          to { width: 100% }
        }
      `}</style>

      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gridTemplateRows: 'repeat(2, 1fr)',
          gap: '5px',
          minHeight: 0,
        }}
      >
        {metrics.map((metric) => {
          const value = data ? data[metric.key] : null;
          const hasData = value != null;
          const displayUnit = metric.key === 'runoff' ? (data?.runoff_unit || metric.unit) : metric.unit;
          return (
            <div
              key={metric.label}
              style={{
                background: 'rgba(255,255,255,0.05)',
                padding: '6px 4px',
                borderRadius: '6px',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                borderLeft: `2px solid ${hasData ? metric.color : 'rgba(255,255,255,0.1)'}`,
              }}
            >
              <div style={{ fontSize: '9px', color: '#888', marginBottom: '3px' }}>{metric.label}</div>
              <div style={{ fontSize: '13px', color: hasData ? metric.color : '#444', fontWeight: 'bold', lineHeight: 1.2 }}>
                {formatMetricValue(value)}
                {hasData && (
                  <span style={{ fontSize: '8px', color: '#666', marginLeft: '2px', fontWeight: 'normal' }}>
                    {displayUnit}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ fontSize: '9px', color: '#444', display: 'flex', justifyContent: 'space-between', flexShrink: 0 }}>
        <span>{activeDevice?.panel_name || activeDevice?.name || activeCode || '暂无设备'} | {activeCode || '--'}</span>
        <span style={{ color: data?.updated_at ? '#4ade80' : '#475569' }}>
          最新更新时间 {formatLatestUpdatedAt(data?.updated_at)}
        </span>
      </div>
    </div>
  );
}
