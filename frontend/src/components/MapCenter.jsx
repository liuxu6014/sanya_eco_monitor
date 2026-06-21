import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, ZoomControl, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import s from './MapCenter.module.css'

const GAODE_SAT = 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}'
const GAODE_LABEL = 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}'
const MAP_SUBS = ['1', '2', '3', '4']
const STATUS_LABEL = '状态'

delete L.Icon.Default.prototype._getIconUrl

function makeIcon(color) {
  return L.divIcon({
    className: '',
    iconSize: [0, 0],
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
          animation:ripple_${color.replace('#', '')} 2s linear infinite;
          z-index:2;
        "></div>
      </div>
      <style>
        @keyframes ripple_${color.replace('#', '')} {
          0%   { transform:scale(0.5);opacity:1 }
          100% { transform:scale(1.8);opacity:0 }
        }
      </style>
    `,
  })
}

function buildDeviceMetaEntry(meta, fields) {
  if (!meta?.code || meta.map_lat == null || meta.map_lng == null) return null
  return {
    id: meta.id || meta.code,
    name: meta.map_name || meta.panel_name || meta.name || meta.code,
    code: meta.code,
    lat: meta.map_lat,
    lng: meta.map_lng,
    color: meta.map_color || '#38bdf8',
    labelCenter: meta.map_label_offset || [0, 0],
    fields,
  }
}

function normalizeDeviceStatus(status) {
  if (status === 'online') return 'online'
  if (status === 'timeout') return 'timeout'
  if (status === 'offline') return 'offline'
  return 'pending'
}

function statusDisplayText(status, pendingLabel) {
  const normalized = normalizeDeviceStatus(status)
  if (normalized === 'online') return '在线'
  if (normalized === 'timeout') return '超时'
  if (normalized === 'offline') return '离线'
  return pendingLabel
}

function buildStatusField(status, pendingLabel) {
  return {
    label: STATUS_LABEL,
    value: statusDisplayText(status, pendingLabel),
    unit: '',
    rawValue: normalizeDeviceStatus(status),
  }
}

function buildDevices(deviceMeta) {
  const devices = []

  const insect = buildDeviceMetaEntry(deviceMeta?.insect, (d) => {
    const status = d?.insect?.status
    return [
      { label: '昨日捕获', value: d?.insect?.total_yesterday ?? '--', unit: '只' },
      buildStatusField(status, '待接入'),
    ]
  })
  if (insect) devices.push(insect)

  const spore = buildDeviceMetaEntry(deviceMeta?.spore, (d) => {
    const status = d?.spore?.status
    return [
      { label: '最新捕获', value: d?.spore?.latest_count ?? '--', unit: '个' },
      buildStatusField(status, '待接入'),
    ]
  })
  if (spore) devices.push(spore)

  const water = buildDeviceMetaEntry(deviceMeta?.water_quality, (d) => {
    const status = d?.water_quality?.status
    return [
      { label: '氨氮', value: d?.water_quality?.nh4n ?? '--', unit: 'mg/L' },
      { label: '高锰酸盐', value: d?.water_quality?.permanganate ?? '--', unit: 'mg/L' },
      buildStatusField(status, '未接入'),
    ]
  })
  if (water) devices.push(water)

  ;(deviceMeta?.runoff_devices || []).forEach((meta) => {
    const device = buildDeviceMetaEntry(meta, (d) => {
      const station = d?.runoff_stations?.[meta.code]
      const status = station?.status
      return [
        { label: '流量', value: station?.flow_rate ?? '--', unit: 'm³/s' },
        buildStatusField(status, '待接入'),
      ]
    })
    if (device) devices.push(device)
  })

  ;(deviceMeta?.rain_gauges || []).forEach((meta) => {
    const device = buildDeviceMetaEntry(meta, (d) => {
      const station = d?.rain_gauges?.[meta.code]
      const status = station?.status
      return [
        { label: '实时雨量', value: station?.realtime_rainfall ?? '--', unit: 'mm' },
        buildStatusField(status, '待接入'),
      ]
    })
    if (device) devices.push(device)
  })

  return devices
}

function formatMapLabelValue(value, unit) {
  if (value == null || value === '--') return '--'

  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) return value

  if (unit === '只' || unit === '个') {
    return String(Math.round(numericValue))
  }

  return typeof value === 'number' ? value.toFixed(2) : value
}

function buildLabelContent(dev, data) {
  const fields = dev.fields(data)
  const main = fields[0]
  const formattedValue = formatMapLabelValue(main.value, main.unit)
  return { name: dev.name, label: main.label, value: formattedValue, unit: main.unit }
}

function getDeviceStatusValue(dev, data) {
  const statusField = dev.fields(data).find((field) => field.label === STATUS_LABEL)
  return statusField?.rawValue || 'pending'
}

function MarkerPixelTracker({ devices, onUpdate }) {
  const map = useMap()

  const update = useCallback(() => {
    const positions = {}
    devices.forEach((dev) => {
      const pt = map.latLngToContainerPoint([dev.lat, dev.lng])
      positions[dev.id] = { x: Math.round(pt.x), y: Math.round(pt.y) }
    })
    onUpdate(positions)
  }, [devices, map, onUpdate])

  useMapEvents({ move: update, zoom: update, resize: update })
  useEffect(() => { update() }, [update])
  return null
}

function MapVisibilityController({ active, onVisible, devices }) {
  const map = useMap()

  useEffect(() => {
    if (!active) return undefined

    let cancelled = false
    const refresh = () => {
      if (cancelled) return
      map.invalidateSize()
      const positions = {}
      devices.forEach((dev) => {
        const pt = map.latLngToContainerPoint([dev.lat, dev.lng])
        positions[dev.id] = { x: Math.round(pt.x), y: Math.round(pt.y) }
      })
      onVisible(positions)
    }

    refresh()
    const first = window.setTimeout(refresh, 80)
    const second = window.setTimeout(refresh, 240)

    return () => {
      cancelled = true
      window.clearTimeout(first)
      window.clearTimeout(second)
    }
  }, [active, devices, map, onVisible])

  return null
}

function DraggableLabel({ dev, content, x, y, onDrag, fontScale = 1 }) {
  const dragRef = useRef(null)
  const baseName = 11 * fontScale
  const baseVal = 10 * fontScale
  const baseUnit = 9 * fontScale

  const onMouseDown = (e) => {
    if (e.button !== 0) return
    e.stopPropagation()
    e.preventDefault()
    dragRef.current = { startX: e.clientX - x, startY: e.clientY - y }
    const move = (event) => {
      if (!dragRef.current) return
      onDrag(event.clientX - dragRef.current.startX, event.clientY - dragRef.current.startY)
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

export default function MapCenter({ overview, deviceMeta, active = true }) {
  const devices = useMemo(() => buildDevices(deviceMeta), [deviceMeta])
  const [resetTrigger, setResetTrigger] = useState(0)
  const [markerPixels, setMarkerPixels] = useState({})
  const [hiddenLabels, setHiddenLabels] = useState(new Set())
  const [labelFontScale, setLabelFontScale] = useState(() => {
    try { return parseFloat(localStorage.getItem('sanyaEcoLabelFontScale') || '1') } catch { return 1 }
  })

  const changeFontScale = (delta) => {
    setLabelFontScale((prev) => {
      const next = Math.round(Math.min(2.5, Math.max(0.5, prev + delta)) * 10) / 10
      localStorage.setItem('sanyaEcoLabelFontScale', next.toString())
      return next
    })
  }

  const [{ initCenter, initZoom }] = useState(() => {
    let c = DEFAULT_CENTER
    let z = DEFAULT_ZOOM
    try {
      const sc = localStorage.getItem('sanyaEcoMapCenter')
      const sz = localStorage.getItem('sanyaEcoMapZoom')
      if (sc) c = JSON.parse(sc)
      if (sz) z = parseFloat(sz)
    } catch {}
    return { initCenter: c, initZoom: z }
  })

  const [labelOffsets, setLabelOffsets] = useState({})

  useEffect(() => {
    setLabelOffsets((prev) => {
      const next = {}
      devices.forEach((dev) => {
        const saved = prev[dev.id]
        next[dev.id] = saved || { dx: dev.labelCenter[0], dy: dev.labelCenter[1] }
      })
      return next
    })
  }, [devices])

  const rawData = overview || {}
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  const yesterdayKey = `${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`
  const yesterdayTrendItem = (rawData.insect_trend || []).find((item) => item?.date === yesterdayKey)
  const inferredYesterdayTotal = yesterdayTrendItem?.count ?? null
  const data = {
    ...rawData,
    insect: {
      ...(rawData.insect || {}),
      total_yesterday: rawData.insect?.total_yesterday ?? inferredYesterdayTotal ?? 0,
    },
  }

  const onlineDeviceCount = devices.filter((dev) => getDeviceStatusValue(dev, data) === 'online').length
  const abnormalDeviceCount = devices.filter((dev) => getDeviceStatusValue(dev, data) !== 'online').length

  const handlePixelUpdate = useCallback((positions) => {
    setMarkerPixels(positions)
  }, [])

  const handleMapVisible = useCallback((positions) => {
    setMarkerPixels(positions)
  }, [])

  const handleMarkerClick = (id) => {
    setHiddenLabels((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleLabelDrag = (id, newX, newY) => {
    const marker = markerPixels[id]
    if (!marker) return
    setLabelOffsets((prev) => {
      const next = {
        ...prev,
        [id]: { dx: Math.round(newX - marker.x), dy: Math.round(newY - marker.y) },
      }
      localStorage.setItem('sanyaEcoLabelOffsets', JSON.stringify(next))
      return next
    })
  }

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
        <MarkerPixelTracker devices={devices} onUpdate={handlePixelUpdate} />
        <MapVisibilityController active={active} devices={devices} onVisible={handleMapVisible} />
        <ZoomControl position="topleft" />

        <TileLayer url={GAODE_SAT} subdomains={MAP_SUBS} maxZoom={18} />
        <TileLayer url={GAODE_LABEL} subdomains={MAP_SUBS} maxZoom={18} opacity={0.9} />

        {devices.map((dev) => (
          <Marker
            key={dev.id}
            position={[dev.lat, dev.lng]}
            icon={makeIcon(dev.color)}
            eventHandlers={{ click: () => handleMarkerClick(dev.id) }}
          />
        ))}
      </MapContainer>

      <div className={s.cardsLayer} style={{ pointerEvents: 'none' }}>
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            overflow: 'visible',
            pointerEvents: 'none',
            zIndex: 400,
          }}
        >
          {devices.map((dev) => {
            if (hiddenLabels.has(dev.id)) return null
            const marker = markerPixels[dev.id]
            const offset = labelOffsets[dev.id]
            if (!marker || !offset) return null
            const lx = marker.x + offset.dx
            const ly = marker.y + offset.dy
            return (
              <line
                key={dev.id}
                x1={marker.x}
                y1={marker.y}
                x2={lx}
                y2={ly}
                stroke={dev.color}
                strokeWidth="1.2"
                strokeDasharray="4,3"
                opacity="0.65"
              />
            )
          })}
        </svg>

        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
          {devices.map((dev) => {
            if (hiddenLabels.has(dev.id)) return null
            const marker = markerPixels[dev.id]
            const offset = labelOffsets[dev.id]
            if (!marker || !offset) return null
            const lx = marker.x + offset.dx
            const ly = marker.y + offset.dy
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
                />
              </div>
            )
          })}
        </div>
      </div>

      <div className={s.bottomBar}>
        <button
          className={`${s.actionBtn} ${s.btnCyan}`}
          title="点击重置地图视图和标签位置"
          onClick={() => {
            setResetTrigger((value) => value + 1)
            setHiddenLabels(new Set())
            const initOffsets = {}
            devices.forEach((dev) => {
              initOffsets[dev.id] = { dx: dev.labelCenter[0], dy: dev.labelCenter[1] }
            })
            setLabelOffsets(initOffsets)
            localStorage.removeItem('sanyaEcoLabelOffsets')
            localStorage.removeItem('sanyaEcoMapCenter')
            localStorage.removeItem('sanyaEcoMapZoom')
          }}
          style={{ cursor: 'pointer' }}
        >
          <span>◎</span> 全局态势
        </button>

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
              {onlineDeviceCount}
            </div>
            <div className={s.statLabel}>在线设备</div>
          </div>
          <div className={s.statItem}>
            <div className={s.statNum} style={{ color: 'var(--gold)' }}>
              {abnormalDeviceCount}
            </div>
            <div className={s.statLabel}>状态异常/未接入</div>
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
