import React from 'react'
import { 
  CheckCircle, 
  AlertCircle, 
  XCircle, 
  RefreshCw,
  Satellite,
  Globe,
  Newspaper,
  Building,
  MessageSquare
} from 'lucide-react'
import { useHealth } from '../hooks/useDossier'

// Map service names to icons
const SERVICE_ICONS = {
  'google_earth_engine': Globe,
  'global_forest_watch': Satellite,
  'sentinel_hub': Satellite,
  'google_custom_search': Newspaper,
  'gdelt': Newspaper,
  'overpass_osm': Building,
  'gleif': Building,
  'reddit': MessageSquare
}

// Friendly names
const SERVICE_NAMES = {
  'google_earth_engine': 'Earth Engine',
  'global_forest_watch': 'Forest Watch',
  'sentinel_hub': 'Sentinel Hub',
  'google_custom_search': 'Google News',
  'gdelt': 'GDELT',
  'overpass_osm': 'OpenStreetMap',
  'gleif': 'GLEIF (LEI)',
  'reddit': 'Reddit'
}

function StatusIcon({ status }) {
  switch (status) {
    case 'healthy':
      return <CheckCircle className="w-3 h-3 text-forensic-success" />
    case 'degraded':
      return <AlertCircle className="w-3 h-3 text-forensic-warning" />
    case 'unhealthy':
      return <XCircle className="w-3 h-3 text-forensic-danger" />
    default:
      return <AlertCircle className="w-3 h-3 text-gray-500" />
  }
}

function DataSourceStatus() {
  const { health, loading, error, refresh } = useHealth()

  if (loading && !health) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-400">Data Sources</h3>
          <RefreshCw className="w-3 h-3 text-gray-500 animate-spin" />
        </div>
        <div className="space-y-1">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton h-5 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-400">Data Sources</h3>
          <button onClick={refresh} className="p-1 hover:bg-gray-700 rounded">
            <RefreshCw className="w-3 h-3 text-gray-500" />
          </button>
        </div>
        <p className="text-xs text-forensic-danger">Failed to load status</p>
      </div>
    )
  }

  // Count statuses
  const statusCounts = health?.services?.reduce((acc, s) => {
    acc[s.status] = (acc[s.status] || 0) + 1
    return acc
  }, {}) || {}

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-400">Data Sources</h3>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs">
            {statusCounts.healthy > 0 && (
              <span className="text-forensic-success">{statusCounts.healthy}✓</span>
            )}
            {statusCounts.degraded > 0 && (
              <span className="text-forensic-warning">{statusCounts.degraded}!</span>
            )}
            {statusCounts.unhealthy > 0 && (
              <span className="text-forensic-danger">{statusCounts.unhealthy}✗</span>
            )}
          </div>
          <button 
            onClick={refresh} 
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title="Refresh status"
          >
            <RefreshCw className={`w-3 h-3 text-gray-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="space-y-1">
        {health?.services?.map(service => {
          const Icon = SERVICE_ICONS[service.name] || Globe
          const displayName = SERVICE_NAMES[service.name] || service.name
          
          return (
            <div 
              key={service.name}
              className="flex items-center justify-between py-1 px-2 rounded bg-forensic-darker/50 group"
              title={service.message || `Latency: ${service.latency_ms?.toFixed(0)}ms`}
            >
              <div className="flex items-center gap-2">
                <Icon className="w-3 h-3 text-gray-500" />
                <span className="text-xs text-gray-400">{displayName}</span>
              </div>
              <div className="flex items-center gap-1">
                {service.latency_ms && (
                  <span className="text-[10px] text-gray-600">
                    {service.latency_ms.toFixed(0)}ms
                  </span>
                )}
                <StatusIcon status={service.status} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Overall status badge */}
      <div className={`text-center py-1 rounded text-xs ${
        health?.status === 'healthy' ? 'bg-green-900/30 text-green-400' :
        health?.status === 'degraded' ? 'bg-yellow-900/30 text-yellow-400' :
        'bg-red-900/30 text-red-400'
      }`}>
        System: {health?.status || 'unknown'}
      </div>
    </div>
  )
}

export default DataSourceStatus