import React, { useState, useMemo } from 'react'
import { 
  Globe, 
  AlertTriangle, 
  Activity, 
  FileText, 
  Download,
  Menu,
  X,
  MapPin,
  Info
} from 'lucide-react'
import { useDossier } from '../hooks/useDossier'
import DataSourceStatus from './DataSourceStatus'
import InvestigativeMap from './InvestigativeMap'
import SentinelPreview from './SentinelPreview'
import ImpactAnalysis from './ImpactAnalysis'
import SuspectCard from './SuspectCard'
import EvidenceDossier from './EvidenceDossier'

function DashboardLayout({
  regions,
  selectedRegion,
  onRegionChange,
  onCustomBbox,
  currentBbox,
  currentRegionName,
  isTropicalRegion
}) {
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('map')
  const [customBboxInput, setCustomBboxInput] = useState('')

  // Fetch dossier for current region/bbox
  const dossierParams = useMemo(() => {
    if (selectedRegion) {
      return { region: selectedRegion.id }
    } else if (currentBbox) {
      return { bbox: currentBbox }
    }
    return null
  }, [selectedRegion, currentBbox])

  const {
    data: dossier,
    loading,
    error,
    sourceErrors,
    coverageNotes,
    refresh,
    confidenceScore
  } = useDossier(dossierParams)

  // Handle custom bbox submission
  const handleCustomBboxSubmit = (e) => {
    e.preventDefault()
    if (customBboxInput.trim()) {
      onCustomBbox(customBboxInput.trim())
    }
  }

  // Export dossier as JSON
  const handleExportDossier = () => {
    if (!dossier) return
    
    const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `dossier_${currentRegionName.toLowerCase().replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Tab content
  const tabs = [
    { id: 'map', label: 'Map', icon: Globe },
    { id: 'analysis', label: 'Analysis', icon: Activity },
    { id: 'evidence', label: 'Evidence', icon: FileText }
  ]

  return (
    <div className="flex h-screen bg-forensic-darker overflow-hidden">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-300 bg-forensic-dark border-r border-gray-700 flex flex-col overflow-hidden`}>
        {/* Sidebar Header */}
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold text-gray-100 flex items-center gap-2">
            <Globe className="w-6 h-6 text-forensic-accent" />
            Eco-Forensics
          </h1>
          <p className="text-xs text-gray-500 mt-1">Environmental Investigation Dashboard</p>
        </div>

        {/* Region Selector */}
        <div className="p-4 border-b border-gray-700">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Select Region
          </label>
          <select
            value={selectedRegion?.id || ''}
            onChange={(e) => onRegionChange(e.target.value)}
            className="select w-full"
          >
            <option value="" disabled>Choose a region...</option>
            {regions.map(region => (
              <option key={region.id} value={region.id}>
                {region.name} {region.zone !== 'tropical' && '⚠️'}
              </option>
            ))}
          </select>

          {/* Non-tropical warning */}
          {!isTropicalRegion && selectedRegion && (
            <div className="mt-2 p-2 bg-yellow-900/30 border border-yellow-700 rounded text-xs text-yellow-400 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>GLAD/RADD alerts limited outside tropical regions</span>
            </div>
          )}

          {/* Custom Bbox Input */}
          <form onSubmit={handleCustomBboxSubmit} className="mt-3">
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Or enter custom bbox
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={customBboxInput}
                onChange={(e) => setCustomBboxInput(e.target.value)}
                placeholder="minLon,minLat,maxLon,maxLat"
                className="input flex-1 text-xs"
              />
              <button type="submit" className="btn btn-secondary px-2">
                <MapPin className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>

        {/* Data Source Status */}
        <div className="p-4 border-b border-gray-700 flex-shrink-0">
          <DataSourceStatus />
        </div>

        {/* Confidence Score */}
        {dossier && (
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Confidence Score</span>
              <span className={`text-lg font-bold ${
                confidenceScore >= 70 ? 'text-forensic-danger' :
                confidenceScore >= 50 ? 'text-forensic-warning' :
                'text-gray-400'
              }`}>
                {confidenceScore.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-500 ${
                  confidenceScore >= 70 ? 'bg-forensic-danger' :
                  confidenceScore >= 50 ? 'bg-forensic-warning' :
                  'bg-forensic-accent'
                }`}
                style={{ width: `${confidenceScore}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {confidenceScore >= 70 ? 'High confidence - strong evidence' :
               confidenceScore >= 50 ? 'Moderate confidence - investigate further' :
               'Low confidence - limited data'}
            </p>
          </div>
        )}

        {/* Quick Stats */}
        {dossier && (
          <div className="p-4 flex-1 overflow-y-auto">
            <h3 className="text-sm font-medium text-gray-400 mb-3">Quick Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Fire Detections</span>
                <span className="text-orange-400 font-medium">{dossier.firms?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">GLAD Alerts</span>
                <span className="text-red-400 font-medium">{dossier.gfw_glad?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">RADD Alerts</span>
                <span className="text-yellow-400 font-medium">{dossier.gfw_radd?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Infrastructure</span>
                <span className="text-blue-400 font-medium">{dossier.nearby_infra?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Suspects</span>
                <span className="text-purple-400 font-medium">{dossier.suspects?.length || 0}</span>
              </div>
              {dossier.hansen && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Forest Loss</span>
                  <span className="text-cyan-400 font-medium">{dossier.hansen.total_loss_ha?.toLocaleString()} ha</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Export Button */}
        {dossier && (
          <div className="p-4 border-t border-gray-700">
            <button
              onClick={handleExportDossier}
              className="btn btn-secondary w-full flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export Dossier (JSON)
            </button>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation */}
        <header className="bg-forensic-dark border-b border-gray-700 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            
            <div>
              <h2 className="text-lg font-semibold text-gray-100">{currentRegionName}</h2>
              {currentBbox && (
                <p className="text-xs text-gray-500">
                  Bbox: {currentBbox.map(n => n.toFixed(2)).join(', ')}
                </p>
              )}
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex gap-1">
            {tabs.map(tab => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                    activeTab === tab.id 
                      ? 'bg-forensic-accent text-white' 
                      : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </nav>

          {/* Refresh Button */}
          <button
            onClick={refresh}
            disabled={loading}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Activity className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {/* Loading State */}
          {loading && !dossier && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 border-4 border-forensic-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-gray-400">Loading dossier for {currentRegionName}...</p>
                <p className="text-xs text-gray-600 mt-1">This may take up to a minute</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="h-full flex items-center justify-center p-4">
              <div className="card max-w-md text-center">
                <AlertTriangle className="w-12 h-12 text-forensic-danger mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-100 mb-2">Failed to Load Dossier</h3>
                <p className="text-gray-400 mb-4">{error.message}</p>
                {error.retryable && (
                  <button onClick={refresh} className="btn btn-primary">
                    Try Again
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Content Tabs */}
          {dossier && (
            <div className="h-full overflow-auto">
              {/* Source Errors Banner */}
              {sourceErrors.length > 0 && (
                <div className="bg-yellow-900/30 border-b border-yellow-700 px-4 py-2">
                  <div className="flex items-center gap-2 text-yellow-400 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    <span>
                      {sourceErrors.length} data source{sourceErrors.length > 1 ? 's' : ''} unavailable — 
                      {sourceErrors.map(e => e.source).join(', ')}
                    </span>
                    <button className="ml-auto text-xs underline hover:text-yellow-300">
                      View details
                    </button>
                  </div>
                </div>
              )}

              {/* Coverage Notes Banner */}
              {coverageNotes.length > 0 && (
                <div className="bg-blue-900/30 border-b border-blue-700 px-4 py-2">
                  <div className="flex items-center gap-2 text-blue-400 text-sm">
                    <Info className="w-4 h-4" />
                    <span>
                      {coverageNotes.map(n => `${n.dataset}: ${n.reason || n.status}`).join(' | ')}
                    </span>
                  </div>
                </div>
              )}

              {/* Map Tab */}
              {activeTab === 'map' && (
                <div className="h-full flex flex-col lg:flex-row">
                  <div className="flex-1 min-h-[400px] lg:min-h-0">
                    <InvestigativeMap dossier={dossier} />
                  </div>
                  <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-gray-700 overflow-y-auto">
                    <SentinelPreview 
                      bbox={currentBbox} 
                      sentinel={dossier.sentinel}
                    />
                  </div>
                </div>
              )}

              {/* Analysis Tab */}
              {activeTab === 'analysis' && (
                <div className="p-4 space-y-4">
                  <ImpactAnalysis dossier={dossier} />
                  
                  {/* Suspects Grid */}
                  {dossier.suspects?.length > 0 && (
                    <div>
                      <h3 className="card-header">Identified Suspects</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {dossier.suspects.map((suspect, index) => (
                          <SuspectCard 
                            key={suspect.lei || index}
                            suspect={suspect}
                            evidenceChain={dossier.evidence_chain?.find(e => e.suspect?.name === suspect.name)}
                            sentiment={dossier.sentiment}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Evidence Tab */}
              {activeTab === 'evidence' && (
                <div className="p-4">
                  <EvidenceDossier 
                    dossier={dossier}
                    sourceErrors={sourceErrors}
                    coverageNotes={coverageNotes}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default DashboardLayout