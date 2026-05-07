const BASE = '/api'

async function request(path, init = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...init,
  })

  if (res.status === 401 && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }

  if (!res.ok) {
    let detail = `API ${path} failed: ${res.status}`
    try {
      const data = await res.json()
      if (data?.detail) {
        detail = data.detail
      }
    } catch {}
    const error = new Error(detail)
    error.status = res.status
    throw error
  }

  return res.json()
}

function get(path) {
  return request(path)
}

function post(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
}

function del(path) {
  return request(path, { method: 'DELETE' })
}

export const api = {
  authStatus: () => get('/auth/status'),
  authLogin: (password) => post('/auth/login', { password }),
  authLogout: () => post('/auth/logout'),
  overview: () => get('/summary/overview'),
  deviceStatus: () => get('/summary/device-status'),
  insectLatest: () => get('/insect/latest'),
  insectTrend: (days = 7) => get(`/insect/trend?days=${days}`),
  insectSpecies: (days = 7) => get(`/insect/species-stats?days=${days}`),
  insectCombinedTrend: (days = 30) => get(`/insect/combined-trend?days=${days}`),
  insectHeatmap: (days = 14) => get(`/insect/species-heatmap?days=${days}`),
  insectImages: (days = 30, species = '') => get(`/insect/images?days=${days}${species ? `&species=${encodeURIComponent(species)}` : ''}`),
  insectAnalysisDetail: (species = '', days = 30) => get(`/insect/analysis-detail?days=${days}${species ? `&species=${encodeURIComponent(species)}` : ''}`),
  sporeLatest: () => get('/insect/spore/latest'),
  sporeTrend: (days = 7) => get(`/insect/spore/trend?days=${days}`),
  sporeImages: (days = 30, name = '') => get(`/insect/spore/images?days=${days}${name ? `&name=${encodeURIComponent(name)}` : ''}`),
  sporeAnalysisDetail: (name = '', days = 30) => get(`/insect/spore/analysis-detail?days=${days}${name ? `&name=${encodeURIComponent(name)}` : ''}`),
  rainfallDaily: (days = 30) => get(`/sensor/rainfall/daily?days=${days}`),
  rainfallAnalysis: (days = 30) => get(`/sensor/rainfall/analysis?days=${days}`),
  waterQualityDaily: (days = 30) => get(`/sensor/water_quality/daily?days=${days}`),
  waterQualityAnalysis: (days = 30) => get(`/sensor/water_quality/analysis?days=${days}`),
  runoffDaily: (days = 30) => get(`/sensor/runoff/daily?days=${days}`),
  runoffAnalysis: (days = 30) => get(`/sensor/runoff/analysis?days=${days}`),
  ecoIndex: () => get('/analysis/eco-index'),
  guidelineMetrics: () => get('/analysis/guideline-metrics'),
  analysisDashboard: () => get('/analysis/dashboard'),
  triggerCollect: () => post('/collect/trigger'),
  deleteReport: (id) => del(`/report/${id}`),
}
