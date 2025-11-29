import React, { useState } from 'react'
import {
  Building2,
  MapPin,
  Link as LinkIcon,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  TrendingDown,
  ExternalLink,
  Shield,
  Globe,
  FileText,
  Flame,
  Info
} from 'lucide-react'

// Confidence level thresholds
const CONFIDENCE_LEVELS = {
  high: { min: 80, color: 'text-red-400', bg: 'bg-red-900/30', border: 'border-red-700', label: 'High Confidence' },
  medium: { min: 60, color: 'text-yellow-400', bg: 'bg-yellow-900/30', border: 'border-yellow-700', label: 'Medium Confidence' },
  low: { min: 0, color: 'text-gray-400', bg: 'bg-gray-800', border: 'border-gray-700', label: 'Low Confidence' }
}

function getConfidenceLevel(score) {
  if (score >= CONFIDENCE_LEVELS.high.min) return CONFIDENCE_LEVELS.high
  if (score >= CONFIDENCE_LEVELS.medium.min) return CONFIDENCE_LEVELS.medium
  return CONFIDENCE_LEVELS.low
}

// Animated negative sentiment badge
function SentimentBadge({ score }) {
  if (score === null || score === undefined) return null
  
  const isNegative = score < -0.2
  const isStronglyNegative = score < -0.4
  
  if (!isNegative) return null
  
  return (
    <div 
      className={`
        inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium
        ${isStronglyNegative 
          ? 'bg-red-900/50 text-red-300 border border-red-600 glow-danger' 
          : 'bg-yellow-900/50 text-yellow-300 border border-yellow-600'
        }
      `}
    >
      <TrendingDown className={`w-3 h-3 ${isStronglyNegative ? 'animate-pulse' : ''}`} />
      <span>
        {isStronglyNegative ? 'Strongly Negative' : 'Negative'} Sentiment
      </span>
    </div>
  )
}

// Evidence link item
function EvidenceLinkItem({ link }) {
  const getIcon = () => {
    switch (link.evidence_type) {
      case 'spatial_proximity': return <MapPin className="w-4 h-4 text-blue-400" />
      case 'temporal_correlation': return <Flame className="w-4 h-4 text-orange-400" />
      case 'sentinel_ndvi': return <TrendingDown className="w-4 h-4 text-green-400" />
      case 'sentinel_nbr': return <TrendingDown className="w-4 h-4 text-cyan-400" />
      case 'sentinel_burn': return <Flame className="w-4 h-4 text-red-400" />
      case 'sentiment_negative': return <TrendingDown className="w-4 h-4 text-purple-400" />
      default: return <LinkIcon className="w-4 h-4 text-gray-400" />
    }
  }

  const getTypeLabel = () => {
    switch (link.evidence_type) {
      case 'spatial_proximity': return 'Spatial Link'
      case 'temporal_correlation': return 'Temporal Link'
      case 'sentinel_ndvi': return 'Vegetation Loss'
      case 'sentinel_nbr': return 'Burn Detection'
      case 'sentinel_burn': return 'Active Burning'
      case 'sentiment_negative': return 'Media Coverage'
      case 'alert_density': return 'Alert Concentration'
      default: return link.evidence_type
    }
  }

  // Weight as percentage
  const weightPercent = Math.round(link.weight * 100)

  return (
    <div className="flex items-start gap-3 p-2 bg-forensic-darker rounded-lg group">
      <div className="mt-0.5">{getIcon()}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-gray-300">{getTypeLabel()}</span>
          <span className="text-xs text-gray-500">{weightPercent}% weight</span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{link.description}</p>
        
        {/* Supporting data tooltip */}
        {link.supporting_data && Object.keys(link.supporting_data).length > 0 && (
          <div className="relative inline-block">
            <button className="text-[10px] text-forensic-accent hover:underline mt-1 flex items-center gap-1">
              <Info className="w-3 h-3" />
              View details
            </button>
            <div className="tooltip left-0 top-5 w-48 opacity-0 invisible group-hover:opacity-100 group-hover:visible">
              <pre className="text-[10px] whitespace-pre-wrap">
                {JSON.stringify(link.supporting_data, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Why this matters tooltip content
function WhyThisMatters({ evidenceType }) {
  const explanations = {
    spatial_proximity: "Industrial facilities located near deforestation or fire events may be directly involved in land clearing activities. Palm oil mills, sawmills, and processing plants often drive local deforestation.",
    temporal_correlation: "When fire events occur shortly before or after deforestation alerts, it often indicates deliberate slash-and-burn land clearing - a common illegal practice.",
    sentinel_ndvi: "Low NDVI values indicate reduced vegetation cover. A sudden drop suggests recent clearing or damage to the forest canopy.",
    sentinel_burn: "Elevated burn indices from satellite imagery provide direct evidence of fire activity in the area.",
    sentiment_negative: "Negative media coverage often accompanies environmental controversies. Companies facing scrutiny may have documented issues."
  }

  return (
    <div className="text-xs text-gray-400">
      {explanations[evidenceType] || "This evidence type contributes to the overall confidence score."}
    </div>
  )
}

function SuspectCard({ suspect, evidenceChain, sentiment, expanded: initialExpanded = false }) {
  const [expanded, setExpanded] = useState(initialExpanded)
  
  // Calculate combined confidence from evidence chain
  const confidence = evidenceChain?.total_weight 
    ? Math.min(100, evidenceChain.total_weight * 100)
    : suspect.match_score || 0
  
  const confidenceLevel = getConfidenceLevel(confidence)
  
  // Get sentiment score
  const sentimentScore = sentiment?.final_score

  return (
    <div className={`card ${confidenceLevel.border} ${confidenceLevel.bg} transition-all duration-300`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className={`p-2 rounded-lg ${confidenceLevel.bg}`}>
            <Building2 className={`w-5 h-5 ${confidenceLevel.color}`} />
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="font-semibold text-gray-100 truncate" title={suspect.name}>
              {suspect.name}
            </h4>
            {suspect.parent_name && (
              <p className="text-xs text-gray-500 truncate" title={`Parent: ${suspect.parent_name}`}>
                Parent: {suspect.parent_name}
              </p>
            )}
          </div>
        </div>
        
        {/* Confidence badge */}
        <div className={`
          px-2 py-1 rounded text-xs font-medium whitespace-nowrap
          ${confidenceLevel.bg} ${confidenceLevel.color} ${confidenceLevel.border} border
        `}>
          {confidence.toFixed(0)}%
        </div>
      </div>

      {/* Sentiment badge */}
      {sentimentScore !== null && sentimentScore !== undefined && (
        <div className="mt-3">
          <SentimentBadge score={sentimentScore} />
        </div>
      )}

      {/* Quick info */}
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        {suspect.country && (
          <div className="flex items-center gap-1.5 text-gray-400">
            <Globe className="w-3 h-3" />
            <span>{suspect.country}</span>
            {suspect.jurisdiction && <span className="text-gray-600">/ {suspect.jurisdiction}</span>}
          </div>
        )}
        {suspect.lei && (
          <div className="flex items-center gap-1.5 text-gray-400">
            <Shield className="w-3 h-3" />
            <span className="truncate" title={suspect.lei}>{suspect.lei.slice(0, 10)}...</span>
          </div>
        )}
      </div>

      {/* LEI lookup link */}
      {suspect.lei && (
        <a
          href={`https://search.gleif.org/#/record/${suspect.lei}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1 text-xs text-forensic-accent hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          View GLEIF Record
        </a>
      )}

      {/* Evidence chain toggle */}
      {evidenceChain && evidenceChain.links?.length > 0 && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-3 w-full flex items-center justify-between py-2 px-3 bg-forensic-darker rounded-lg hover:bg-gray-800 transition-colors"
          >
            <span className="text-xs font-medium text-gray-300 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Evidence Chain ({evidenceChain.links.length} links)
            </span>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {/* Expanded evidence */}
          {expanded && (
            <div className="mt-3 space-y-2">
              {/* Summary */}
              <p className="text-xs text-gray-400 italic px-1">
                {evidenceChain.summary}
              </p>
              
              {/* Evidence links */}
              <div className="space-y-2">
                {evidenceChain.links.map((link, index) => (
                  <EvidenceLinkItem key={index} link={link} />
                ))}
              </div>

              {/* Why this matters */}
              <div className="mt-3 p-3 bg-blue-900/20 border border-blue-800 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium text-blue-300 mb-1">Why this matters</p>
                    <p className="text-xs text-blue-200/70">
                      The combination of spatial proximity, temporal patterns, and satellite evidence 
                      creates a forensic link between this entity and environmental damage. 
                      {confidence >= 70 
                        ? " The high confidence score suggests strong evidence of involvement."
                        : confidence >= 50
                        ? " Further investigation is recommended to confirm involvement."
                        : " More evidence needed to establish clear connection."
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* No evidence chain */}
      {(!evidenceChain || evidenceChain.links?.length === 0) && (
        <div className="mt-3 p-2 bg-gray-800/50 rounded-lg text-xs text-gray-500 text-center">
          <AlertTriangle className="w-4 h-4 mx-auto mb-1 opacity-50" />
          Limited evidence available
        </div>
      )}

      {/* Match score (from GLEIF) */}
      {suspect.match_score && (
        <div className="mt-3 pt-3 border-t border-gray-700/50">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Name Match Confidence</span>
            <span className="text-gray-400">{suspect.match_score.toFixed(1)}%</span>
          </div>
          <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-forensic-accent transition-all duration-500"
              style={{ width: `${suspect.match_score}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default SuspectCard