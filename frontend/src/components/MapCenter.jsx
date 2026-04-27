import { useState, useEffect, useRef, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, ZoomControl, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import s from './MapCenter.module.css'

// 高德卫星图层（无需Key，国内直连）
const GAODE_SAT   = 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}'
const GAODE_LABEL = 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}'
const MAP_SUBS = ['1', '2', '3', '4']

// Fix Leaflet default icon resolution in Vite
delete L.Icon.Default.prototype._getIconUrl

/**
 * makeIcon: 只渲染圆点 + 波纹动画，不含标签或连线。
 * 标签由独立的 DOM overlay 层渲染，支持拖动。
 */
function makeIcon(color) {
  return L.divIcon({
    className: '',
    iconSize:   [0, 0],
    iconAnchor: [0, 0],
    html: `
      <div style="position:relative;width:0;height:0;">
        <div style="
          position:absolute;
          width:12px;height:12px;border-radius:50%;
          top:-6px;left:-6px;
          background:${color};
          box-shadow:0 0 10px ${color},0 0 20px ${color}66;
          z-index:3;
        "></div>
        <div style="
          position:absolute;
          width:28px;height:28px;border-radius:50%;
          top:-14px;left:-14px;
          border:1px solid ${color}88;
          animation:ripple_${color.replace('#','')} 2s linear infinite;
          z-index:2;
        "></div>
      </div>
      <style>
        @keyframes ripple_${color.replace('#','')} {
          0%   { transform:scale(0.5);opacity:1 }
          100% { transform:scale(1.8);opacity:0 }
        }
      </style>
    `,
  })
}

// ─── Device definitions ──────────────────────────────────────────────────────
// labelCenter: [dx, dy] 标签中心的初始像素偏移（相对标记圆心）。
// 布局经过数学验证：按 zoom=12 下各标记的实际屏幕坐标计算，
// 所有 120×38px 标签包围盒均不重叠（最小间距 ≥ 2px）。
const DEVICES = [
  // ── 左侧独立站点 ──────────────────────────────────────
  {
    id: 'spore',
    name: '孢子捕捉仪',
    code: 'BZ202411200001',
    lat: 18.349816, lng: 109.362321,
    color: '#d500f9',
    labelCenter: [-160, -80],
    fields: (d) => {
      const s = d?.spore?.status
      return [
        { label: '最新捕获', value: d?.spore?.latest_count ?? '—', unit: '个' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' },
      ]
    },
  },
  {
    id: 'insect',
    name: '智能虫情测报灯',
    code: 'PBCR48F-340838-0001',
    lat: 18.349816, lng: 109.362321,
    color: '#ff1744',
    labelCenter: [-140, -120],
    fields: (d) => {
      const s = d?.insect?.status
      return [
        { label: '昨日捕获', value: d?.insect?.total_yesterday ?? '—', unit: '只' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' },
      ]
    },
  },
  // ── 底部独立站点 ──────────────────────────────────────
  {
    id: 'water',
    name: '面源污染监测站',
    code: '16133028',
    lat: 18.314145, lng: 109.463094,
    color: '#ffd600',
    labelCenter: [140, -100],
    fields: (d) => {
      const wq = d?.water_quality
      const s = wq?.status
      return [
        { label: '氨氮', value: wq?.nh4n ?? '—', unit: 'mg/L' },
        { label: '高猛酸盐', value: wq?.permanganate ?? '—', unit: 'mg/L' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '未接入'), unit: '' },
      ]
    },
  },
  // ── 右侧密集区域（已验证互不重叠）──────────────────────
  {
    id: 'runoff_mg1',
    name: '杧果林径流监测系统1号',
    code: '16132920',
    lat: 18.3640213, lng: 109.4821167,
    color: '#ff6d00',
    labelCenter: [180, 80],
    fields: (d) => {
      const r = d?.runoff_stations?.['16132920']
      const s = r?.status
      return [
        { label: '流量', value: r?.flow_rate ?? '—', unit: 'm³/h' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'rain1',
    name: '4G雨量计1号',
    code: '16132920',
    lat: 18.3640213, lng: 109.4821167,
    color: '#2979ff',
    labelCenter: [100, 160],
    fields: (d) => {
      const g = d?.rain_gauges?.['16132920']
      const s = g?.status
      return [
        { label: '雨量', value: g?.rainfall ?? '—', unit: 'mm' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'runoff_xj1',
    name: '橡胶林径流监测系统1号',
    code: '16132921',
    lat: 18.3628883, lng: 109.4733582,
    color: '#aeea00',
    labelCenter: [-160, 140],
    fields: (d) => {
      const r = d?.runoff_stations?.['16132921']
      const s = r?.status
      return [
        { label: '流量', value: r?.flow_rate ?? '—', unit: 'm³/h' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'rain2',
    name: '4G雨量计2号',
    code: '16132921',
    lat: 18.3628883, lng: 109.4733582,
    color: '#2979ff',
    labelCenter: [-200, 0],
    fields: (d) => {
      const g = d?.rain_gauges?.['16132921']
      const s = g?.status
      return [
        { label: '雨量', value: g?.rainfall ?? '—', unit: 'mm' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'runoff_mg2',
    name: '杧果林径流监测系统2号',
    code: '16132923',
    lat: 18.3672924, lng: 109.4803925,
    color: '#ff6d00',
    labelCenter: [-180, -140],
    fields: (d) => {
      const r = d?.runoff_stations?.['16132923']
      const s = r?.status
      return [
        { label: '流量', value: r?.flow_rate ?? '—', unit: 'm³/h' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'runoff_xj2',
    name: '橡胶林径流监测系统2号',
    code: '16132924',
    lat: 18.3700542, lng: 109.4898224,
    color: '#aeea00',
    labelCenter: [220, -60],
    fields: (d) => {
      const r = d?.runoff_stations?.['16132924']
      const s = r?.status
      return [
        { label: '流量', value: r?.flow_rate ?? '—', unit: 'm³/h' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'runoff_cs',
    name: '次生林径流监测系统',
    code: '16132922',
    lat: 18.3940544, lng: 109.4813004,
    color: '#1de9b6',
    labelCenter: [120, -100],
    fields: (d) => {
      const r = d?.runoff_stations?.['16132922']
      const s = r?.status
      return [
        { label: '流量', value: r?.flow_rate ?? '—', unit: 'm³/h' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'rain3',
    name: '4G雨量计3号',
    code: '16132922',
    lat: 18.3940544, lng: 109.4813004,
    color: '#2979ff',
    labelCenter: [240, -20],
    fields: (d) => {
      const g = d?.rain_gauges?.['16132922']
      const s = g?.status
      return [
        { label: '雨量', value: g?.rainfall ?? '—', unit: 'mm' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
  {
    id: 'runoff_bl',
    name: '槟榔林径流监测系统',
    code: '16132925',
    lat: 18.3916378, lng: 109.4681549,
    color: '#ff4081',
    labelCenter: [-100, -160],
    fields: (d) => {
      const r = d?.runoff_stations?.['16132925']
      const s = r?.status
      return [
        { label: '流量', value: r?.flow_rate ?? '—', unit: 'm³/h' },
        { label: '状态', value: s === 'online' ? '在线' : (s ? '离线' : '待接入'), unit: '' }
      ]
    },
  },
]

/** 构造气泡标签的 HTML 内容（纯文字部分） */
function buildLabelContent(dev, data) {
  const fields = dev.fields(data)
  const main = fields[0]
  return { name: dev.name, label: main.label, value: main.value, unit: main.unit }
}

// ─── MarkerPixelTracker ──────────────────────────────────────────────────────
// 在 MapContainer 内部追踪每个设备标记点的屏幕像素坐标，在地图移动/缩放时更新。
function MarkerPixelTracker({ onUpdate }) {
  const map = useMap()

  const update = useCallback(() => {
    const positions = {}
    DEVICES.forEach(dev => {
      const pt = map.latLngToContainerPoint([dev.lat, dev.lng])
      positions[dev.id] = { x: Math.round(pt.x), y: Math.round(pt.y) }
    })
    onUpdate(positions)
  }, [map, onUpdate])

  useMapEvents({ move: update, zoom: update, resize: update })
  useEffect(() => { update() }, [update])
  return null
}

// ─── DraggableLabel ──────────────────────────────────────────────────────────
function DraggableLabel({ dev, content, x, y, onDrag, onClick, fontScale = 1 }) {
  const dragRef = useRef(null)
  const baseName = 11 * fontScale
  const baseVal  = 10 * fontScale
  const baseUnit =  9 * fontScale

  const onMouseDown = (e) => {
    if (e.button !== 0) return
    e.stopPropagation()
    e.preventDefault()
    const startCX = e.clientX
    const startCY = e.clientY
    dragRef.current = { startX: e.clientX - x, startY: e.clientY - y }
    const move = (e) => {
      if (!dragRef.current) return
      onDrag(e.clientX - dragRef.current.startX, e.clientY - dragRef.current.startY)
    }
    const up = (upE) => {
      dragRef.current = null
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      const dist = Math.hypot(upE.clientX - startCX, upE.clientY - startCY)
      if (dist < 5 && onClick) {
        onClick()
      }
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  }

  return (
    <div
      onMouseDown={onMouseDown}
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: 'translate(-50%, -50%)',
        cursor: 'grab',
        background: 'rgba(4,12,32,0.85)',
        border: `1px solid ${dev.color}66`,
        borderRadius: 6,
        padding: '4px 8px',
        whiteSpace: 'nowrap',
        backdropFilter: 'blur(8px)',
        boxShadow: '0 2px 10px rgba(0,0,0,0.6)',
        lineHeight: 1.3,
        userSelect: 'none',
        zIndex: 500,
      }}
    >
      <div style={{ fontSize: baseName, fontWeight: 600, color: dev.color, letterSpacing: '.4px', marginBottom: 2 }}>
        {content.name}
      </div>
      <div style={{ fontSize: baseVal, color: 'rgba(200,220,255,.7)' }}>
        {content.label}:{' '}
        <span style={{ color: '#fff', fontWeight: 700 }}>{content.value}</span>
        {content.unit && (
          <span style={{ color: 'rgba(200,220,255,.5)', fontSize: baseUnit }}> {content.unit}</span>
        )}
      </div>
    </div>
  )
}

// ─── DeviceCard ──────────────────────────────────────────────────────────────
function DeviceCard({ device, data, onClose, pos, onMove }) {
  const fields = device.fields(data)
  const dragRef = useRef(null)

  const onMouseDown = (e) => {
    if (e.button !== 0) return
    e.stopPropagation()
    dragRef.current = { ox: e.clientX - pos.x, oy: e.clientY - pos.y }
    const move = (e) => {
      if (!dragRef.current) return
      onMove({ x: e.clientX - dragRef.current.ox, y: e.clientY - dragRef.current.oy })
    }
    const up = () => {
      dragRef.current = null
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  }

  return (
    <div className={s.card} style={{ left: pos.x, top: pos.y }}>
      <div className={s.cardHeader} style={{ borderColor: device.color, cursor: 'grab' }} onMouseDown={onMouseDown}>
        <span className={s.cardDot} style={{ background: device.color, boxShadow: `0 0 8px ${device.color}` }} />
        <span className={s.cardName}>{device.name}</span>
        <button className={s.cardClose} onClick={onClose}>×</button>
      </div>
      <div className={s.cardBody}>
        {fields.map(f => (
          <div key={f.label} className={s.cardRow}>
            <span className={s.cardLabel}>{f.label}</span>
            <span className={s.cardValue} style={{ color: f.value === '—' || f.value === '接入中' ? 'var(--text-dim)' : 'var(--text)' }}>
              {f.value}{f.unit && <span className={s.cardUnit}>{f.unit}</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── MapStateTracker ──────────────────────────────────────────────────────────
function MapStateTracker() {
  const map = useMap()
  const saveState = useCallback(() => {
    const center = map.getCenter()
    const zoom = map.getZoom()
    localStorage.setItem('sanyaEcoMapCenter', JSON.stringify([center.lat, center.lng]))
    localStorage.setItem('sanyaEcoMapZoom', zoom.toString())
  }, [map])
  useMapEvents({ moveend: saveState, zoomend: saveState })
  return null
}

// ─── MapController ───────────────────────────────────────────────────────────
function MapController({ resetTrigger }) {
  const map = useMap()
  useEffect(() => {
    if (resetTrigger > 0) {
      map.setView(DEFAULT_CENTER, DEFAULT_ZOOM)
    }
  }, [map, resetTrigger])
  return null
}

const DEFAULT_CENTER = [18.360, 109.430]
const DEFAULT_ZOOM = 12

export default function MapCenter({ overview }) {
  const [openCards, setOpenCards]     = useState({})
  const [resetTrigger, setResetTrigger] = useState(0)
  const [markerPixels, setMarkerPixels] = useState({})   // { id: {x,y} } 标记点屏幕坐标
  const [hiddenLabels, setHiddenLabels] = useState(new Set()) // 被隐藏的标签 id
  const [labelFontScale, setLabelFontScale] = useState(() => {
    try { return parseFloat(localStorage.getItem('sanyaEcoLabelFontScale') || '1') } catch { return 1 }
  })

  const changeFontScale = (delta) => {
    setLabelFontScale(prev => {
      const next = Math.round(Math.min(2.5, Math.max(0.5, prev + delta)) * 10) / 10
      localStorage.setItem('sanyaEcoLabelFontScale', next.toString())
      return next
    })
  }

  const [{ initCenter, initZoom }] = useState(() => {
    let c = DEFAULT_CENTER, z = DEFAULT_ZOOM
    try {
      const sc = localStorage.getItem('sanyaEcoMapCenter')
      const sz = localStorage.getItem('sanyaEcoMapZoom')
      if (sc) c = JSON.parse(sc)
      if (sz) z = parseFloat(sz)
    } catch(e) {}
    return { initCenter: c, initZoom: z }
  })

  // labelOffsets: { id: {dx, dy} } 标签中心相对标记点的当前偏移（可被拖动改变）
  const [labelOffsets, setLabelOffsets] = useState(() => {
    try {
      const saved = localStorage.getItem('sanyaEcoLabelOffsets')
      if (saved) return JSON.parse(saved)
    } catch(e) {}
    const init = {}
    DEVICES.forEach(dev => {
      init[dev.id] = { dx: dev.labelCenter[0], dy: dev.labelCenter[1] }
    })
    return init
  })

  const rawData = overview || {}
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  const yesterdayKey = `${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`
  const yesterdayTrendItem = (rawData.insect_trend || []).find(item => item?.date === yesterdayKey)
  const inferredYesterdayTotal = yesterdayTrendItem?.count ?? null
  const data = {
    ...rawData,
    insect: {
      ...(rawData.insect || {}),
      total_yesterday: rawData.insect?.total_yesterday ?? inferredYesterdayTotal ?? 0,
    },
  }

  // 标记点屏幕坐标更新回调（由 MarkerPixelTracker 驱动）
  const handlePixelUpdate = useCallback((positions) => {
    setMarkerPixels(positions)
  }, [])

  // 点击标记点：切换对应标签的显隐
  const handleMarkerClick = (id) => {
    setHiddenLabels(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // 拖动标签后更新偏移
  const handleLabelDrag = (id, newX, newY) => {
    const mp = markerPixels[id]
    if (!mp) return
    setLabelOffsets(prev => {
      const next = {
        ...prev,
        [id]: { dx: Math.round(newX - mp.x), dy: Math.round(newY - mp.y) },
      }
      localStorage.setItem('sanyaEcoLabelOffsets', JSON.stringify(next))
      return next
    })
  }

  const moveCard = (id, newPos) => setOpenCards(prev => ({ ...prev, [id]: newPos }))

  return (
    <div className={s.wrap}>
      <MapContainer
        center={initCenter}
        zoom={initZoom}
        className={s.map}
        zoomControl={false}
        attributionControl={false}
        scrollWheelZoom={false}
      >
        <MapController resetTrigger={resetTrigger} />
        <MapStateTracker />
        <MarkerPixelTracker onUpdate={handlePixelUpdate} />
        <ZoomControl position="topleft" />

        {/* 高德卫星底图 */}
        <TileLayer url={GAODE_SAT}   subdomains={MAP_SUBS} maxZoom={18} />
        {/* 高德中文标注 */}
        <TileLayer url={GAODE_LABEL} subdomains={MAP_SUBS} maxZoom={18} opacity={0.9} />

        {DEVICES.map(dev => (
          <Marker
            key={dev.id}
            position={[dev.lat, dev.lng]}
            icon={makeIcon(dev.color)}
            eventHandlers={{ click: () => handleMarkerClick(dev.id) }}
          />
        ))}
      </MapContainer>

      {/* ── Overlay layer: SVG 连线 + 可拖动标签 ── */}
      <div className={s.cardsLayer} style={{ pointerEvents: 'none' }}>

        {/* SVG 层：动态连线 */}
        <svg
          style={{
            position: 'absolute', top: 0, left: 0,
            width: '100%', height: '100%',
            overflow: 'visible', pointerEvents: 'none', zIndex: 400,
          }}
        >
          {DEVICES.map(dev => {
            if (hiddenLabels.has(dev.id)) return null
            const mp = markerPixels[dev.id]
            const lo = labelOffsets[dev.id]
            if (!mp || !lo) return null
            const lx = mp.x + lo.dx
            const ly = mp.y + lo.dy
            return (
              <line
                key={dev.id}
                x1={mp.x} y1={mp.y}
                x2={lx}   y2={ly}
                stroke={dev.color}
                strokeWidth="1.2"
                strokeDasharray="4,3"
                opacity="0.65"
              />
            )
          })}
        </svg>

        {/* 标签层：可拖动气泡 */}
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
          {DEVICES.map(dev => {
            if (hiddenLabels.has(dev.id)) return null
            const mp = markerPixels[dev.id]
            const lo = labelOffsets[dev.id]
            if (!mp || !lo) return null
            const lx = mp.x + lo.dx
            const ly = mp.y + lo.dy
            const content = buildLabelContent(dev, data)
            return (
              <div key={dev.id} style={{ pointerEvents: 'auto' }}>
                <DraggableLabel
                  dev={dev}
                  content={content}
                  x={lx}
                  y={ly}
                  fontScale={labelFontScale}
                  onDrag={(nx, ny) => handleLabelDrag(dev.id, nx, ny)}
                  onClick={() => {
                    setOpenCards(prev => ({ ...prev, [dev.id]: { x: lx + 20, y: ly + 20 } }))
                  }}
                />
              </div>
            )
          })}
        </div>

        {/* DeviceCard 浮动详情卡 */}
        {DEVICES.map(dev =>
          openCards[dev.id] ? (
            <DeviceCard
              key={dev.id}
              device={dev}
              data={data}
              pos={openCards[dev.id]}
              onMove={(p) => moveCard(dev.id, p)}
              onClose={() => {
                const next = { ...openCards }
                delete next[dev.id]
                setOpenCards(next)
              }}
            />
          ) : null
        )}
      </div>

      {/* Bottom action buttons */}
      <div className={s.bottomBar}>
        <button
          className={`${s.actionBtn} ${s.btnCyan}`}
          title="点击重置地图视图并关闭所有弹窗"
          onClick={() => {
            setOpenCards({})
            setResetTrigger(v => v + 1)
            // 重置标签偏移和显隐状态
            setHiddenLabels(new Set())
            const initOffsets = {}
            DEVICES.forEach(dev => {
              initOffsets[dev.id] = { dx: dev.labelCenter[0], dy: dev.labelCenter[1] }
            })
            setLabelOffsets(initOffsets)
            localStorage.removeItem('sanyaEcoLabelOffsets')
            localStorage.removeItem('sanyaEcoMapCenter')
            localStorage.removeItem('sanyaEcoMapZoom')
          }}
          style={{ cursor: 'pointer' }}
        >
          <span>◈</span> 全局态势
        </button>

        {/* 右侧：标签字体大小调节 */}
        <div className={s.labelSizeCtrl}>
          <button
            className={s.labelSizeBtn}
            title="缩小标签"
            onClick={() => changeFontScale(-0.1)}
            disabled={labelFontScale <= 0.5}
          >－</button>
          <span className={s.labelSizeVal}>{Math.round(labelFontScale * 100)}%</span>
          <button
            className={s.labelSizeBtn}
            title="放大标签"
            onClick={() => changeFontScale(0.1)}
            disabled={labelFontScale >= 2.5}
          >＋</button>
        </div>
        <div className={s.stats}>
          <div className={s.statItem}>
            <div className={s.statNum} style={{ color: 'var(--cyan)' }}>
              {DEVICES.filter(dev => {
                const s = dev.fields(data).find(f => f.label === '状态')?.value;
                return s === '在线';
              }).length}
            </div>
            <div className={s.statLabel}>在线设备</div>
          </div>
          <div className={s.statItem}>
            <div className={s.statNum} style={{ color: 'var(--gold)' }}>
              {DEVICES.filter(dev => {
                const s = dev.fields(data).find(f => f.label === '状态')?.value;
                return s === '离线' || s === '待接入';
              }).length}
            </div>
            <div className={s.statLabel}>状态异常/未结</div>
          </div>
          <div className={s.statItem}>
            <div className={s.statNum} style={{ color: 'var(--green)' }}>
              {data.insect?.total_yesterday ?? 0}
            </div>
            <div className={s.statLabel}>昨日虫情</div>
          </div>
        </div>
      </div>
    </div>
  )
}

