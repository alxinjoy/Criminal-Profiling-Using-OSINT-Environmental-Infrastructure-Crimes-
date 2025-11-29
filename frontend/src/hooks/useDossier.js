/**
 * Custom hook for fetching and managing dossier data
 * 
 * Features:
 * - Automatic retry with backoff
 * - Schema validation (presence of mandatory fields)
 * - Extracted source errors and coverage notes
 * - Loading and error states
 */

import { useState, useEffect, useCallback } from 'react'
import { fetchDossier, logToServer } from '../services/api'

// Mandatory fields that must be present in a valid dossier
const MANDATORY_FIELDS = [
  'bbox',
  'generated_at',
  'confidence_score',
  'source_errors',
  'coverage_notes'
]

/**
 * Validate dossier response has required fields
 */
function validateDossier(dossier) {
  const missingFields = MANDATORY_FIELDS.filter(field => !(field in dossier))
  
  if (missingFields.length > 0) {
    throw new Error(`Invalid dossier: missing fields ${missingFields.join(', ')}`)
  }
  
  // Validate bbox structure
  if (!dossier.bbox || typeof dossier.bbox.min_lon !== 'number') {
    throw new Error('Invalid dossier: malformed bbox')
  }
  
  return true
}

/**
 * Hook for fetching dossier data
 * 
 * @param {Object} params - Query parameters
 * @param {string} params.region - Named region (e.g., 'Riau')
 * @param {number[]} params.bbox - Custom bbox [minLon, minLat, maxLon, maxLat]
 * @param {boolean} autoFetch - Whether to fetch automatically on mount/change
 */
export function useDossier(params, autoFetch = true) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sourceErrors, setSourceErrors] = useState([])
  const [coverageNotes, setCoverageNotes] = useState([])

  // Fetch dossier data
  const fetchData = useCallback(async () => {
    // Need either region or bbox
    if (!params?.region && !params?.bbox) {
      return
    }

    setLoading(true)
    setError(null)
    
    console.info('[useDossier] Fetching dossier...', params)
    const startTime = Date.now()

    try {
      const dossier = await fetchDossier(params)
      
      // Validate response
      validateDossier(dossier)
      
      const duration = Date.now() - startTime
      console.info(`[useDossier] Dossier loaded in ${duration}ms`, {
        region: dossier.region,
        confidence: dossier.confidence_score,
        alerts: (dossier.gfw_glad?.length || 0) + (dossier.gfw_radd?.length || 0),
        fires: dossier.firms?.length || 0,
        suspects: dossier.suspects?.length || 0
      })
      
      setData(dossier)
      setSourceErrors(dossier.source_errors || [])
      setCoverageNotes(dossier.coverage_notes || [])
      
    } catch (err) {
      console.error('[useDossier] Failed to fetch dossier:', err)
      
      setError({
        message: err.message || 'Failed to load dossier',
        status: err.response?.status,
        retryable: !err.response || err.response.status >= 500 || err.response.status === 429
      })
      
      // Log error to server
      logToServer('error', `Dossier fetch failed: ${err.message}`, {
        params,
        status: err.response?.status
      })
      
    } finally {
      setLoading(false)
    }
  }, [params?.region, params?.bbox?.join(',')])

  // Auto-fetch on mount or when params change
  useEffect(() => {
    if (autoFetch) {
      fetchData()
    }
  }, [fetchData, autoFetch])

  // Manual refresh function
  const refresh = useCallback(() => {
    fetchData()
  }, [fetchData])

  // Clear data
  const clear = useCallback(() => {
    setData(null)
    setError(null)
    setSourceErrors([])
    setCoverageNotes([])
  }, [])

  return {
    data,
    loading,
    error,
    sourceErrors,
    coverageNotes,
    refresh,
    clear,
    // Convenience getters for common data
    hasData: !!data,
    hasFires: data?.firms?.length > 0,
    hasAlerts: (data?.gfw_glad?.length || 0) + (data?.gfw_radd?.length || 0) > 0,
    hasSentinel: !!data?.sentinel,
    hasSuspects: data?.suspects?.length > 0,
    confidenceScore: data?.confidence_score || 0
  }
}

/**
 * Hook for fetching health status
 */
export function useHealth() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchHealthData = useCallback(async () => {
    setLoading(true)
    try {
      const { fetchHealth } = await import('../services/api')
      const data = await fetchHealth()
      setHealth(data)
      setError(null)
    } catch (err) {
      setError(err.message)
      console.error('[useHealth] Failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealthData()
    
    // Refresh health every 60 seconds
    const interval = setInterval(fetchHealthData, 60000)
    return () => clearInterval(interval)
  }, [fetchHealthData])

  return { health, loading, error, refresh: fetchHealthData }
}

export default useDossier