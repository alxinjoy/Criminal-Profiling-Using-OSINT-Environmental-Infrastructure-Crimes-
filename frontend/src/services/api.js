/**
 * Centralized API client for Eco-Forensics Dashboard
 * 
 * Features:
 * - Automatic retry with backoff (matches backend config)
 * - Request/response logging
 * - Error logging to backend /internal/logs
 * - Mock mode support
 */

import axios from 'axios'

// API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true'

// Retry configuration (matches backend: 3 attempts, 1s, 2s, 4s delays)
const MAX_RETRIES = 3
const RETRY_DELAYS = [1000, 2000, 4000]

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout for dossier requests
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - log outgoing requests
apiClient.interceptors.request.use(
  (config) => {
    console.info(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data
    })
    config.metadata = { startTime: Date.now() }
    return config
  },
  (error) => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor - log responses and handle errors
apiClient.interceptors.response.use(
  (response) => {
    const duration = Date.now() - response.config.metadata?.startTime
    console.info(`[API] Response ${response.status} in ${duration}ms`, {
      url: response.config.url,
      dataSize: JSON.stringify(response.data).length
    })
    return response
  },
  async (error) => {
    const duration = Date.now() - error.config?.metadata?.startTime
    const status = error.response?.status
    
    console.error(`[API] Error ${status || 'NETWORK'} in ${duration}ms`, {
      url: error.config?.url,
      message: error.message
    })
    
    // Log 5xx errors to backend
    if (status >= 500) {
      await logToServer('error', `API Error ${status}: ${error.config?.url}`, {
        status,
        message: error.message,
        response: error.response?.data
      })
    }
    
    return Promise.reject(error)
  }
)

/**
 * Sleep for specified milliseconds
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Make API request with retry logic
 */
async function requestWithRetry(config, retries = MAX_RETRIES) {
  let lastError
  
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      return await apiClient(config)
    } catch (error) {
      lastError = error
      const status = error.response?.status
      
      // Don't retry client errors (4xx) except 429 (rate limit)
      if (status && status >= 400 && status < 500 && status !== 429) {
        throw error
      }
      
      // Don't retry on last attempt
      if (attempt < retries - 1) {
        const delay = RETRY_DELAYS[attempt] || RETRY_DELAYS[RETRY_DELAYS.length - 1]
        console.warn(`[API] Retry ${attempt + 1}/${retries} after ${delay}ms`)
        await sleep(delay)
      }
    }
  }
  
  throw lastError
}

/**
 * Log message to server /internal/logs
 */
export async function logToServer(level, message, context = {}) {
  try {
    // Don't use retry for logging to avoid infinite loops
    await apiClient.post('/internal/logs', [{
      level,
      message,
      timestamp: new Date().toISOString(),
      context: {
        ...context,
        userAgent: navigator.userAgent,
        url: window.location.href
      }
    }])
  } catch (error) {
    // Silently fail - don't want logging errors to break the app
    console.warn('[API] Failed to send log to server:', error.message)
  }
}

/**
 * Fetch health status from /health
 */
export async function fetchHealth() {
  if (MOCK_MODE) {
    return getMockHealth()
  }
  
  const response = await requestWithRetry({ method: 'GET', url: '/health' })
  return response.data
}

/**
 * Fetch dossier for a region or bbox
 */
export async function fetchDossier(params) {
  if (MOCK_MODE) {
    return getMockDossier()
  }
  
  const { region, bbox, startDate, endDate } = params
  
  const queryParams = {}
  if (region) {
    queryParams.region = region
  } else if (bbox) {
    queryParams.bbox = bbox.join(',')
  }
  if (startDate) queryParams.start_date = startDate
  if (endDate) queryParams.end_date = endDate
  
  const response = await requestWithRetry({
    method: 'GET',
    url: '/dossier',
    params: queryParams,
    timeout: 60000 // Dossier can take longer
  })
  
  return response.data
}

/**
 * Fetch fire data
 */
export async function fetchFires(params) {
  if (MOCK_MODE) {
    return { fires: [], count: 0 }
  }
  
  const { region, bbox, days = 30 } = params
  
  const queryParams = { days }
  if (region) {
    queryParams.region = region
  } else if (bbox) {
    queryParams.bbox = bbox.join(',')
  }
  
  const response = await requestWithRetry({
    method: 'GET',
    url: '/fires',
    params: queryParams
  })
  
  return response.data
}

/**
 * Fetch forest loss data
 */
export async function fetchLoss(params) {
  if (MOCK_MODE) {
    return { hansen_stats: null }
  }
  
  const { region, bbox, years } = params
  
  const queryParams = {}
  if (region) queryParams.region = region
  else if (bbox) queryParams.bbox = bbox.join(',')
  if (years) queryParams.years = years.join(',')
  
  const response = await requestWithRetry({
    method: 'GET',
    url: '/loss',
    params: queryParams
  })
  
  return response.data
}

/**
 * Fetch sentiment analysis
 */
export async function fetchSentiment(params) {
  if (MOCK_MODE) {
    return { sentiment: null, query: '' }
  }
  
  const { region, bbox, query } = params
  
  const queryParams = {}
  if (region) queryParams.region = region
  else if (bbox) queryParams.bbox = bbox.join(',')
  if (query) queryParams.query = query
  
  const response = await requestWithRetry({
    method: 'GET',
    url: '/sentiment',
    params: queryParams
  })
  
  return response.data
}

/**
 * Fetch Sentinel preview image
 */
export async function fetchSentinelPreview(bbox, date) {
  if (MOCK_MODE) {
    return { sentinel: null, bbox, date }
  }
  
  const response = await requestWithRetry({
    method: 'GET',
    url: '/sentinel/preview',
    params: {
      bbox: bbox.join(','),
      date: date || undefined
    },
    timeout: 45000 // Sentinel can be slow
  })
  
  return response.data
}

// ============== Mock Data ==============

function getMockHealth() {
  return {
    status: 'healthy',
    services: [
      { name: 'google_earth_engine', status: 'healthy', latency_ms: 120 },
      { name: 'global_forest_watch', status: 'healthy', latency_ms: 85 },
      { name: 'sentinel_hub', status: 'healthy', latency_ms: 200 },
      { name: 'google_custom_search', status: 'degraded', latency_ms: 150, message: 'Quota low' },
      { name: 'gdelt', status: 'healthy', latency_ms: 90 },
      { name: 'overpass_osm', status: 'healthy', latency_ms: 300 },
      { name: 'gleif', status: 'healthy', latency_ms: 110 },
      { name: 'reddit', status: 'unhealthy', message: 'API access restricted' }
    ],
    timestamp: new Date().toISOString()
  }
}

function getMockDossier() {
  // Return mock dossier data for offline development
  return {
    region: 'Riau',
    bbox: { min_lon: 100, min_lat: -1, max_lon: 104, max_lat: 3 },
    generated_at: new Date().toISOString(),
    analysis_period_start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
    analysis_period_end: new Date().toISOString(),
    hansen: {
      total_loss_ha: 15420.5,
      loss_by_year: { 2021: 4500.2, 2022: 5120.8, 2023: 5799.5 },
      tree_cover_percent: 45.2
    },
    gfw_glad: [
      { latitude: 1.234, longitude: 102.456, date: '2023-12-01T00:00:00Z', confidence: 85 },
      { latitude: 1.456, longitude: 102.789, date: '2023-12-05T00:00:00Z', confidence: 90 },
      { latitude: 0.987, longitude: 101.234, date: '2023-12-10T00:00:00Z', confidence: 75 }
    ],
    gfw_radd: [
      { latitude: 1.345, longitude: 102.567, date: '2023-12-03T00:00:00Z', confidence: 'high' }
    ],
    firms: [
      { latitude: 1.235, longitude: 102.457, brightness: 345.5, confidence: 90, frp: 25.3, acquisition_time: '2023-12-02T14:30:00Z', satellite: 'VIIRS', daynight: 'D' },
      { latitude: 1.456, longitude: 102.790, brightness: 320.0, confidence: 85, frp: 18.5, acquisition_time: '2023-12-06T10:15:00Z', satellite: 'MODIS', daynight: 'D' },
      { latitude: 0.988, longitude: 101.235, brightness: 380.0, confidence: 95, frp: 35.0, acquisition_time: '2023-12-11T08:45:00Z', satellite: 'VIIRS', daynight: 'D' }
    ],
    sentinel: {
      ndvi: 0.32,
      nbr: 0.15,
      burn_index: 0.28,
      truecolor_url: null,
      acquisition_date: '2023-12-15T00:00:00Z'
    },
    nearby_infra: [
      { osm_id: 12345678, node_type: 'palm_oil_mill', name: 'PT Sawit Mas Mill', latitude: 1.230, longitude: 102.450, distance_m: 1200, tags: { industrial: 'palm_oil_mill' } },
      { osm_id: 23456789, node_type: 'factory', name: 'Riau Processing Plant', latitude: 1.350, longitude: 102.600, distance_m: 2500, tags: { industrial: 'factory' } },
      { osm_id: 34567890, node_type: 'industrial', name: null, latitude: 0.950, longitude: 101.300, distance_m: 4800, tags: { landuse: 'industrial' } }
    ],
    suspects: [
      { name: 'PT Sawit Mas', lei: '529900ABC123DEF456GH', country: 'ID', jurisdiction: 'Riau', parent_name: 'Asian Agri Holdings', parent_lei: '529900XYZ789ABC123DE', status: 'active', match_score: 92.5, source: 'gleif' },
      { name: 'Riau Palm Industries', lei: null, country: 'ID', jurisdiction: 'Riau', parent_name: null, parent_lei: null, status: null, match_score: 67.0, source: 'gleif' }
    ],
    sentiment: {
      google: { count: 15, score: -0.45, keywords: ['deforestation', 'fire', 'palm oil'], sample_titles: ['Riau fires linked to palm oil expansion', 'Deforestation accelerates in Sumatra'] },
      gdelt: { count: 32, score: -0.38, keywords: ['forest fire', 'environmental damage'], sample_titles: [] },
      reddit: null,
      final_score: -0.42,
      confidence: 0.65,
      dominant_narrative: 'deforestation'
    },
    evidence_chain: [
      {
        suspect: { name: 'PT Sawit Mas', lei: '529900ABC123DEF456GH', country: 'ID', match_score: 92.5, source: 'gleif' },
        links: [
          { evidence_type: 'spatial_proximity', description: 'Palm oil mill within 1.2km of 3 fire detections', weight: 0.20, supporting_data: { proximity_count: 3, closest_distance_m: 1200 } },
          { evidence_type: 'temporal_correlation', description: 'Fire events occurred within 7 days of deforestation alerts', weight: 0.15, supporting_data: { correlation_count: 2, avg_days_apart: 5 } },
          { evidence_type: 'sentinel_ndvi', description: 'Low NDVI (0.32) indicates vegetation loss', weight: 0.12, supporting_data: { score: 0.65 } },
          { evidence_type: 'sentiment_negative', description: 'Negative media coverage (-0.42)', weight: 0.08, supporting_data: { score: 0.55 } }
        ],
        total_weight: 0.55,
        summary: 'PT Sawit Mas: Evidence shows strong spatial correlation with damage sites, temporal pattern of fires preceding deforestation.'
      }
    ],
    confidence_score: 72.5,
    source_errors: [
      { source: 'reddit', error_type: 'HTTPStatusError', message: '403 Forbidden - Reddit API access restricted', retryable: false, timestamp: new Date().toISOString() }
    ],
    coverage_notes: []
  }
}

export default apiClient