import axios from 'axios'

const BASE_URL = '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ── KPIs ──────────────────────────────────────────────────────────────────
export const kpisApi = {
  getOverview: () => api.get('/kpis'),
}

// ── Agents ────────────────────────────────────────────────────────────────
export const agentsApi = {
  list: (params = {}) => api.get('/agents', { params }),
  updateStatus: (agentId, status) =>
    api.post(`/agents/${agentId}/status`, { status }),
  disconnectBatch: (count = 20) =>
    api.post('/agents/disconnect-batch', { count }),
}

// ── Borrowers ─────────────────────────────────────────────────────────────
export const borrowersApi = {
  list: (params = {}) => api.get('/borrowers', { params }),
}

// ── Campaigns ─────────────────────────────────────────────────────────────
export const campaignsApi = {
  list: (params = {}) => api.get('/campaigns', { params }),
  start: (campaignId) => api.post(`/campaigns/${campaignId}/start`),
  pause: (campaignId) => api.post(`/campaigns/${campaignId}/pause`),
  setMode: (campaignId, mode) =>
    api.post(`/campaigns/${campaignId}/mode`, { mode }),
}

// ── Calls ─────────────────────────────────────────────────────────────────
export const callsApi = {
  list: (params = {}) => api.get('/calls', { params }),
  triggerProgressive: (payload) => api.post('/calls/dial/progressive', payload),
  triggerPredictive: (payload) => api.post('/calls/dial/predictive', payload),
}

// ── Providers ─────────────────────────────────────────────────────────────
export const providersApi = {
  list: () => api.get('/providers'),
  toggleOutage: (providerName, isOutage) =>
    api.post(`/providers/${providerName}/outage`, { is_outage: isOutage }),
  resetCircuit: (providerName) =>
    api.post(`/providers/${providerName}/reset-circuit`),
}

// ── Safety ────────────────────────────────────────────────────────────────
export const safetyApi = {
  getStatus: () => api.get('/safety/status'),
}

// ── Simulation ────────────────────────────────────────────────────────────
export const simulationApi = {
  listScenarios: () => api.get('/simulation/scenarios'),
  run: (payload) => api.post('/simulation/run', payload),
  history: (limit = 10) => api.get('/simulation/history', { params: { limit } }),
}

// ── Analytics ─────────────────────────────────────────────────────────────
export const analyticsApi = {
  campaigns: (limit = 10) =>
    api.get('/analytics/campaigns', { params: { limit } }),
  vendors: () => api.get('/analytics/vendors'),
  dispositions: () => api.get('/analytics/dispositions'),
}

// ── Health ────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => axios.get('/health'),
}

export default api
