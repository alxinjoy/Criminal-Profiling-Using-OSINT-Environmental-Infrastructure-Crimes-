import React, { useState } from 'react'
import {
  FileText,
  Calendar,
  MapPin,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Copy,
  Check,
  Info,
  Flame,
  TreePine,
  Building2,
  Satellite,
  Globe
} from 'lucide-react'

// Timeline event component
function TimelineEvent({ event, index, isLast }) {
  const getEventIcon = () => {
    switch (event.type) {
      case 'fire': return <Flame className="w-4 h-4 text-orange-400" />
      case 'glad': return <TreePine className="w-4 h-4 text-red-400" />
      case 'radd': return <TreePine className="w-4 h-4 text-yellow-400" />
      case 'sentinel': return <Satellite className="w-4 h-4 text-cyan-400" />
      default: return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <div className="flex gap-3">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-forensic-dark border border-gray-600 flex items-center justify-center">
          {getEventIcon()}
        </div>
        {!isLast && <div className="w-0.5 h-full bg-gray-700 mt-1" />}
      </div>
      
      {/* Event content */}
      <div className="flex-1 pb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-200">{event.title}</span>
          <span className="text-xs text-gray-500">{event.date}</span>
        </div>
        <p className="text-xs text-gray-400 mt-1">{event.description}</p>
        {event.location && (
          <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
            <MapPin className="w-3 h-3" />
            <span>{event.location}</span>
          </div>
        )}
      </div>
    </div>
  )
}

// Source error item
function SourceErrorItem({ error }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-red-900/20 border border-red-800 rounded-lg">
      <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-red-300">{error.source}</span>
          <span className="text-xs text-red-400/70">{error.error_type}</span>
        </div>
        <p className="text-xs text-red-200/70 mt-1">{error.message}</p>
        <div className="flex items-center gap-3 mt-2 text-xs">
          <span className={`flex items-center gap-1 ${error.retryable ? 'text-yellow-400' : 'text-gray-500'}`}>
            {error.retryable ? (
              <>
                <Clock className="w-3 h-3" />
                Retryable
              </>
            ) : (
              <>
                <XCircle className="w-3 h-3" />
                Not retryable
              </>
            )}
          </span>
          {error.timestamp && (
            <span className="text-gray-600">
              {new Date(error.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// Coverage note item
function CoverageNoteItem({ note }) {
  const getStatusIcon = () => {
    switch (note.status) {
      case 'available': return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'skipped': return <AlertTriangle className="w-4 h-4 text-yellow-400" />
      case 'partial': return <Info className="w-4 h-4 text-blue-400" />
      default: return <Info className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusColor = () => {
    switch (note.status) {
      case 'available': return 'border-green-700 bg-green-900/20'
      case 'skipped': return 'border-yellow-700 bg-yellow-900/20'
      case 'partial': return 'border-blue-700 bg-blue-900/20'
      default: return 'border-gray-700 bg-gray-800'
    }
  }

  return (
    <div className={`flex items-start gap-3 p-3 border rounded-lg ${getStatusColor()}`}>
      {getStatusIcon()}
      <div>
        <span className="text-sm font-medium text-gray-200">{note.dataset}</span>
        <p className="text-xs text-gray-400 mt-0.5">
          Status: {note.status}
          {note.reason && ` — ${note.reason}`}
        </p>
      </div>
    </div>
  )
}

// Collapsible section
function CollapsibleSection({ title, icon: Icon, children, defaultOpen = false, count }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 bg-forensic-dark hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-forensic-accent" />
          <span className="font-medium text-gray-200">{title}</span>
          {count !== undefined && (
            <span className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-400">
              {count}
            </span>
          )}
        </div>
        {open ? (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronRight className="w-5 h-5 text-gray-500" />
        )}
      </button>
      {open && (
        <div className="p-4 border-t border-gray-700 bg-forensic-darker">
          {children}
        </div>
      )}
    </div>
  )
}

// JSON viewer
function JsonViewer({ data, title }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">{title}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-green-400" />
              <span className="text-green-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="text-xs text-gray-400 bg-black/30 rounded-lg p-3 overflow-auto max-h-64">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

function EvidenceDossier({ dossier, sourceErrors, coverageNotes }) {
  // Build timeline from dossier events
  const timeline = React.useMemo(() => {
    if (!dossier) return []

    const events = []

    // Add fire events
    dossier.firms?.forEach(fire => {
      events.push({
        type: 'fire',
        title: `Fire Detection (${fire.satellite})`,
        description: `Brightness: ${fire.brightness?.toFixed(1)}K, Confidence: ${fire.confidence}%`,
        date: new Date(fire.acquisition_time).toLocaleString(),
        timestamp: new Date(fire.acquisition_time).getTime(),
        location: `${fire.latitude.toFixed(4)}, ${fire.longitude.toFixed(4)}`
      })
    })

    // Add GLAD alerts
    dossier.gfw_glad?.forEach(alert => {
      events.push({
        type: 'glad',
        title: 'GLAD Deforestation Alert',
        description: `Optical satellite detection, Confidence: ${alert.confidence || 'N/A'}%`,
        date: new Date(alert.date).toLocaleDateString(),
        timestamp: new Date(alert.date).getTime(),
        location: `${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}`
      })
    })

    // Add RADD alerts
    dossier.gfw_radd?.forEach(alert => {
      events.push({
        type: 'radd',
        title: 'RADD Radar Alert',
        description: `Radar-based detection, Confidence: ${alert.confidence || 'N/A'}`,
        date: new Date(alert.date).toLocaleDateString(),
        timestamp: new Date(alert.date).getTime(),
        location: `${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}`
      })
    })

    // Sort by timestamp descending (newest first)
    return events.sort((a, b) => b.timestamp - a.timestamp).slice(0, 20) // Limit to 20 events
  }, [dossier])

  if (!dossier) {
    return (
      <div className="card">
        <div className="h-64 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No dossier data available</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
              <FileText className="w-6 h-6 text-forensic-accent" />
              Forensic Dossier
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              {dossier.region || 'Custom Area'} — Generated {new Date(dossier.generated_at).toLocaleString()}
            </p>
          </div>
          
          {/* Confidence badge */}
          <div className={`
            px-4 py-2 rounded-lg text-center
            ${dossier.confidence_score >= 70 
              ? 'bg-red-900/30 border border-red-700' 
              : dossier.confidence_score >= 50
              ? 'bg-yellow-900/30 border border-yellow-700'
              : 'bg-gray-800 border border-gray-700'
            }
          `}>
            <div className={`text-2xl font-bold ${
              dossier.confidence_score >= 70 ? 'text-red-400' :
              dossier.confidence_score >= 50 ? 'text-yellow-400' :
              'text-gray-400'
            }`}>
              {dossier.confidence_score.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">Confidence</div>
          </div>
        </div>

        {/* Metadata */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-forensic-darker rounded-lg">
          <div>
            <div className="text-xs text-gray-500 mb-1">Analysis Period</div>
            <div className="text-sm text-gray-300 flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {new Date(dossier.analysis_period_start).toLocaleDateString()} - {' '}
              {new Date(dossier.analysis_period_end).toLocaleDateString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Bounding Box</div>
            <div className="text-sm text-gray-300 flex items-center gap-1">
              <MapPin className="w-4 h-4" />
              {dossier.bbox.min_lon.toFixed(2)}, {dossier.bbox.min_lat.toFixed(2)} → {' '}
              {dossier.bbox.max_lon.toFixed(2)}, {dossier.bbox.max_lat.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Total Events</div>
            <div className="text-sm text-gray-300">
              {(dossier.firms?.length || 0) + 
               (dossier.gfw_glad?.length || 0) + 
               (dossier.gfw_radd?.length || 0)} detected
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Suspects Identified</div>
            <div className="text-sm text-gray-300">
              {dossier.suspects?.length || 0} entities
            </div>
          </div>
        </div>
      </div>

      {/* Source Errors */}
      {sourceErrors && sourceErrors.length > 0 && (
        <CollapsibleSection 
          title="Data Source Errors" 
          icon={AlertTriangle}
          count={sourceErrors.length}
          defaultOpen={true}
        >
          <div className="space-y-3">
            {sourceErrors.map((error, index) => (
              <SourceErrorItem key={index} error={error} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Coverage Notes */}
      {coverageNotes && coverageNotes.length > 0 && (
        <CollapsibleSection 
          title="Coverage Notes" 
          icon={Info}
          count={coverageNotes.length}
          defaultOpen={true}
        >
          <div className="space-y-3">
            {coverageNotes.map((note, index) => (
              <CoverageNoteItem key={index} note={note} />
            ))}
          </div>
          <div className="mt-3 p-3 bg-blue-900/20 border border-blue-800 rounded-lg">
            <p className="text-xs text-blue-200/70">
              <strong>Note:</strong> GLAD and RADD alerts are only available for tropical regions 
              (approximately 30°N to 30°S). Non-tropical areas will have limited deforestation alert coverage.
            </p>
          </div>
        </CollapsibleSection>
      )}

      {/* Event Timeline */}
      <CollapsibleSection 
        title="Event Timeline" 
        icon={Clock}
        count={timeline.length}
        defaultOpen={true}
      >
        {timeline.length > 0 ? (
          <div className="space-y-0">
            {timeline.map((event, index) => (
              <TimelineEvent 
                key={index} 
                event={event} 
                index={index}
                isLast={index === timeline.length - 1}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 text-center py-4">No events recorded</p>
        )}
      </CollapsibleSection>

      {/* Evidence Chains */}
      {dossier.evidence_chain && dossier.evidence_chain.length > 0 && (
        <CollapsibleSection 
          title="Evidence Chains" 
          icon={Building2}
          count={dossier.evidence_chain.length}
          defaultOpen={true}
        >
          <div className="space-y-4">
            {dossier.evidence_chain.map((chain, index) => (
              <div key={index} className="p-4 bg-forensic-dark rounded-lg border border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-forensic-accent" />
                    <span className="font-medium text-gray-200">{chain.suspect?.name}</span>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${
                    chain.total_weight >= 0.5 
                      ? 'bg-red-900/30 text-red-400 border border-red-700'
                      : 'bg-gray-700 text-gray-400'
                  }`}>
                    Weight: {(chain.total_weight * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-sm text-gray-400 italic mb-3">{chain.summary}</p>
                <div className="space-y-2">
                  {chain.links?.map((link, linkIndex) => (
                    <div key={linkIndex} className="flex items-center justify-between text-xs p-2 bg-forensic-darker rounded">
                      <span className="text-gray-400">{link.evidence_type}</span>
                      <span className="text-gray-500">{(link.weight * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Hansen Stats */}
      {dossier.hansen && (
        <CollapsibleSection title="Forest Loss Statistics" icon={TreePine}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-forensic-dark rounded-lg text-center">
              <div className="text-2xl font-bold text-cyan-400">
                {dossier.hansen.total_loss_ha?.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">Total Loss (hectares)</div>
            </div>
            <div className="p-4 bg-forensic-dark rounded-lg text-center">
              <div className="text-2xl font-bold text-green-400">
                {dossier.hansen.tree_cover_percent?.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500">Tree Cover (2000)</div>
            </div>
          </div>
          
          {dossier.hansen.loss_by_year && (
            <div className="space-y-2">
              <div className="text-xs text-gray-500 mb-2">Loss by Year</div>
              {Object.entries(dossier.hansen.loss_by_year)
                .sort(([a], [b]) => b - a)
                .map(([year, loss]) => (
                  <div key={year} className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">{year}</span>
                    <span className="text-gray-300">{loss.toLocaleString()} ha</span>
                  </div>
                ))
              }
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* Sentinel Data */}
      {dossier.sentinel && (
        <CollapsibleSection title="Sentinel Analysis" icon={Satellite}>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-forensic-dark rounded-lg text-center">
              <div className={`text-2xl font-bold ${
                dossier.sentinel.ndvi < 0.2 ? 'text-red-400' :
                dossier.sentinel.ndvi < 0.4 ? 'text-yellow-400' :
                'text-green-400'
              }`}>
                {dossier.sentinel.ndvi?.toFixed(3) || 'N/A'}
              </div>
              <div className="text-xs text-gray-500">NDVI</div>
            </div>
            <div className="p-4 bg-forensic-dark rounded-lg text-center">
              <div className={`text-2xl font-bold ${
                dossier.sentinel.nbr < 0 ? 'text-red-400' :
                'text-cyan-400'
              }`}>
                {dossier.sentinel.nbr?.toFixed(3) || 'N/A'}
              </div>
              <div className="text-xs text-gray-500">NBR</div>
            </div>
            <div className="p-4 bg-forensic-dark rounded-lg text-center">
              <div className={`text-2xl font-bold ${
                dossier.sentinel.burn_index > 0.3 ? 'text-red-400' :
                'text-orange-400'
              }`}>
                {dossier.sentinel.burn_index?.toFixed(3) || 'N/A'}
              </div>
              <div className="text-xs text-gray-500">Burn Index</div>
            </div>
          </div>
        </CollapsibleSection>
      )}

      {/* Raw JSON */}
      <CollapsibleSection title="Raw Dossier Data" icon={FileText}>
        <JsonViewer data={dossier} title="Complete dossier JSON" />
      </CollapsibleSection>
    </div>
  )
}

export default EvidenceDossier