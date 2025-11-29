import React, { useState, useEffect } from 'react'
import { 
  Satellite, 
  RefreshCw, 
  AlertTriangle, 
  TrendingDown,
  Flame,
  Leaf,
  Calendar,
  Info,
  ExternalLink
} from 'lucide-react'
import { fetchSentinelPreview } from '../services/api'

// Thresholds for highlighting concerning values
const NDVI_WARNING_THRESHOLD = 0.3
const NDVI_DANGER_THRESHOLD = 0.2
const NBR_WARNING_THRESHOLD = 0.2
const BURN_INDEX_WARNING = 0.2
const BURN_INDEX_DANGER = 0.3

function MetricCard({ label, value, icon: Icon, color, tooltip, status }) {
  const getStatusClasses = () => {
    switch (status) {
      case 'danger': return 'border-red-500 bg-red-900/20'
      case 'warning': return 'border-yellow-500 bg-yellow-900/20'
      default: return 'border-gray-600 bg-forensic-darker'
    }
  }

  const getValueColor = () => {
    switch (status) {
      case 'danger': return 'text-red-400'
      case 'warning': return 'text-yellow-400'
      default: return 'text-gray-100'
    }
  }

  return (
    <div className={`border rounded-lg p-3 ${getStatusClasses()} group relative`}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${color}`} />
          <span className="text-xs text-gray-400">{label}</span>
        </div>
        {tooltip && (
          <div className="relative">
            <Info className="w-3 h-3 text-gray-600 cursor-help" />
            <div className="tooltip -left-24 top-6 w-48">
              {tooltip}
            </div>
          </div>
        )}
      </div>
      <div className={`text-xl font-bold ${getValueColor()}`}>
        {value !== null && value !== undefined ? value.toFixed(3) : 'N/A'}
      </div>
      {status === 'danger' && (
        <div className="flex items-center gap-1 mt-1 text-xs text-red-400">
          <AlertTriangle className="w-3 h-3" />
          <span>Critical level</span>
        </div>
      )}
      {status === 'warning' && (
        <div className="flex items-center gap-1 mt-1 text-xs text-yellow-400">
          <TrendingDown className="w-3 h-3" />
          <span>Below normal</span>
        </div>
      )}
    </div>
  )
}

function SentinelPreview({ bbox, sentinel, date }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [previewData, setPreviewData] = useState(null)
  const [selectedDate, setSelectedDate] = useState(
    date || new Date().toISOString().split('T')[0]
  )

  // Use passed sentinel data or fetch new
  useEffect(() => {
    if (sentinel) {
      setPreviewData(sentinel)
    }
  }, [sentinel])

  // Fetch fresh preview
  const fetchPreview = async () => {
    if (!bbox) return

    setLoading(true)
    setError(null)

    try {
      const result = await fetchSentinelPreview(bbox, selectedDate)
      if (result.sentinel) {
        setPreviewData(result.sentinel)
      } else {
        setError('No imagery available for this date')
      }
    } catch (err) {
      console.error('Failed to fetch Sentinel preview:', err)
      setError(err.message || 'Failed to load preview')
    } finally {
      setLoading(false)
    }
  }

  // Determine status for each metric
  const getNdviStatus = (value) => {
    if (value === null || value === undefined) return 'normal'
    if (value < NDVI_DANGER_THRESHOLD) return 'danger'
    if (value < NDVI_WARNING_THRESHOLD) return 'warning'
    return 'normal'
  }

  const getNbrStatus = (value) => {
    if (value === null || value === undefined) return 'normal'
    if (value < 0) return 'danger' // Negative NBR indicates burn
    if (value < NBR_WARNING_THRESHOLD) return 'warning'
    return 'normal'
  }

  const getBurnStatus = (value) => {
    if (value === null || value === undefined) return 'normal'
    if (value > BURN_INDEX_DANGER) return 'danger'
    if (value > BURN_INDEX_WARNING) return 'warning'
    return 'normal'
  }

  const data = previewData || sentinel

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-100 flex items-center gap-2">
            <Satellite className="w-4 h-4 text-forensic-accent" />
            Sentinel Analysis
          </h3>
          <button
            onClick={fetchPreview}
            disabled={loading || !bbox}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
            title="Refresh imagery"
          >
            <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Date selector */}
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-gray-500" />
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="input text-xs flex-1"
            max={new Date().toISOString().split('T')[0]}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Error state */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-medium">Failed to load</span>
            </div>
            <p className="text-xs text-red-400">{error}</p>
            <button
              onClick={fetchPreview}
              className="mt-2 text-xs text-red-300 underline hover:text-red-200"
            >
              Try again
            </button>
          </div>
        )}

        {/* Loading state */}
        {loading && !data && (
          <div className="space-y-3">
            <div className="skeleton h-40 w-full rounded-lg" />
            <div className="grid grid-cols-2 gap-3">
              <div className="skeleton h-20 rounded-lg" />
              <div className="skeleton h-20 rounded-lg" />
            </div>
          </div>
        )}

        {/* True color preview */}
        {data?.truecolor_url && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-gray-400">True Color Preview</h4>
            <div className="relative rounded-lg overflow-hidden border border-gray-700">
              <img
                src={data.truecolor_url}
                alt="Sentinel true color"
                className="w-full h-auto"
                onError={(e) => {
                  e.target.style.display = 'none'
                }}
              />
              <a
                href={data.truecolor_url}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute top-2 right-2 p-1 bg-black/50 rounded hover:bg-black/70 transition-colors"
              >
                <ExternalLink className="w-3 h-3 text-white" />
              </a>
            </div>
          </div>
        )}

        {/* No image placeholder */}
        {data && !data.truecolor_url && (
          <div className="bg-forensic-darker rounded-lg border border-gray-700 p-6 text-center">
            <Satellite className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No preview image available</p>
            <p className="text-xs text-gray-600 mt-1">
              Imagery may be cloud-covered or unavailable for this date
            </p>
          </div>
        )}

        {/* Spectral Indices */}
        {data && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-gray-400">Spectral Indices</h4>
            <div className="grid grid-cols-1 gap-3">
              <MetricCard
                label="NDVI"
                value={data.ndvi}
                icon={Leaf}
                color="text-green-400"
                status={getNdviStatus(data.ndvi)}
                tooltip="Normalized Difference Vegetation Index. Values < 0.2 indicate severe vegetation loss. Healthy forest: 0.6-0.9"
              />
              <MetricCard
                label="NBR"
                value={data.nbr}
                icon={TrendingDown}
                color="text-cyan-400"
                status={getNbrStatus(data.nbr)}
                tooltip="Normalized Burn Ratio. Negative values indicate burn damage. Healthy vegetation: > 0.3"
              />
              <MetricCard
                label="Burn Index"
                value={data.burn_index}
                icon={Flame}
                color="text-orange-400"
                status={getBurnStatus(data.burn_index)}
                tooltip="Combined burn severity indicator. Values > 0.3 indicate active or recent burning"
              />
            </div>
          </div>
        )}

        {/* Interpretation guide */}
        {data && (
          <div className="bg-forensic-darker rounded-lg border border-gray-700 p-3">
            <h4 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              <Info className="w-3 h-3" />
              How to Interpret
            </h4>
            <ul className="text-xs text-gray-500 space-y-1">
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 mt-1 flex-shrink-0" />
                <span><strong>NDVI:</strong> Measures vegetation health. Lower = less/damaged vegetation.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-500 mt-1 flex-shrink-0" />
                <span><strong>NBR:</strong> Detects burn scars. Negative = burn damage present.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-orange-500 mt-1 flex-shrink-0" />
                <span><strong>Burn Index:</strong> Combined severity. Higher = more severe burning.</span>
              </li>
            </ul>
          </div>
        )}

        {/* Acquisition date */}
        {data?.acquisition_date && (
          <p className="text-xs text-gray-600 text-center">
            Acquired: {new Date(data.acquisition_date).toLocaleDateString()}
          </p>
        )}

        {/* No data state */}
        {!loading && !error && !data && (
          <div className="text-center py-8">
            <Satellite className="w-12 h-12 text-gray-700 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No Sentinel data available</p>
            <p className="text-xs text-gray-600 mt-1">
              Select a date and click refresh to load imagery
            </p>
            <button
              onClick={fetchPreview}
              disabled={!bbox}
              className="btn btn-secondary mt-4 text-sm"
            >
              Load Preview
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default SentinelPreview