import React, { useMemo, useState } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Area,
  ReferenceLine
} from 'recharts'
import {
  Flame,
  TrendingDown,
  TreePine,
  MessageSquare,
  RefreshCw,
  AlertTriangle,
  Info,
  Calendar
} from 'lucide-react'

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-forensic-dark border border-gray-700 rounded-lg p-3 shadow-lg">
      <p className="text-sm font-medium text-gray-200 mb-2">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-xs">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-400">{entry.name}:</span>
          <span className="text-gray-200 font-medium">
            {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}

// NDVI Change Chart
function NdviChart({ sentinel, hansen }) {
  // Create mock timeline data based on Hansen yearly loss
  const data = useMemo(() => {
    if (!hansen?.loss_by_year) return []

    const years = Object.keys(hansen.loss_by_year).sort()
    const maxLoss = Math.max(...Object.values(hansen.loss_by_year))

    return years.map(year => {
      const loss = hansen.loss_by_year[year]
      // Estimate NDVI based on loss (more loss = lower NDVI)
      const estimatedNdvi = Math.max(0.1, 0.7 - (loss / maxLoss) * 0.4)
      
      return {
        year,
        loss: loss,
        ndvi: estimatedNdvi,
        lossPercent: ((loss / hansen.total_loss_ha) * 100).toFixed(1)
      }
    })
  }, [hansen])

  if (data.length === 0) {
    return (
      <div className="card">
        <h3 className="card-header flex items-center gap-2">
          <TreePine className="w-5 h-5 text-green-400" />
          Forest Loss Trend
        </h3>
        <div className="h-48 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <TreePine className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No Hansen data available</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="card-header flex items-center gap-2">
        <TreePine className="w-5 h-5 text-green-400" />
        Forest Loss by Year
        <span className="text-xs text-gray-500 font-normal ml-auto">
          Total: {hansen.total_loss_ha?.toLocaleString()} ha
        </span>
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="year" 
              stroke="#9ca3af" 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              yAxisId="left"
              stroke="#9ca3af" 
              tick={{ fontSize: 12 }}
              label={{ 
                value: 'Loss (ha)', 
                angle: -90, 
                position: 'insideLeft',
                style: { fill: '#9ca3af', fontSize: 11 }
              }}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              stroke="#22c55e" 
              tick={{ fontSize: 12 }}
              domain={[0, 1]}
              label={{ 
                value: 'Est. NDVI', 
                angle: 90, 
                position: 'insideRight',
                style: { fill: '#22c55e', fontSize: 11 }
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar 
              yAxisId="left"
              dataKey="loss" 
              name="Forest Loss (ha)" 
              fill="#06b6d4" 
              radius={[4, 4, 0, 0]}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="ndvi"
              name="Est. NDVI"
              stroke="#22c55e"
              strokeWidth={2}
              dot={{ fill: '#22c55e', strokeWidth: 2, r: 4 }}
            />
            {sentinel?.ndvi && (
              <ReferenceLine
                yAxisId="right"
                y={sentinel.ndvi}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{
                  value: `Current: ${sentinel.ndvi.toFixed(2)}`,
                  position: 'right',
                  fill: '#ef4444',
                  fontSize: 10
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Fire and Sentiment Chart
function FireSentimentChart({ fires, sentiment }) {
  // Group fires by date
  const data = useMemo(() => {
    if (!fires || fires.length === 0) return []

    // Group fires by date
    const firesByDate = {}
    fires.forEach(fire => {
      const date = new Date(fire.acquisition_time).toLocaleDateString()
      firesByDate[date] = (firesByDate[date] || 0) + 1
    })

    // Get sentiment score (constant for the period)
    const sentimentScore = sentiment?.final_score || 0

    // Create chart data
    const dates = Object.keys(firesByDate).sort((a, b) => new Date(a) - new Date(b))
    
    return dates.map(date => ({
      date,
      fires: firesByDate[date],
      sentiment: sentimentScore,
      // Normalize sentiment to positive scale for visibility
      sentimentDisplay: ((sentimentScore + 1) / 2) * 100
    }))
  }, [fires, sentiment])

  if (data.length === 0) {
    return (
      <div className="card">
        <h3 className="card-header flex items-center gap-2">
          <Flame className="w-5 h-5 text-orange-400" />
          Fire Activity & Sentiment
        </h3>
        <div className="h-48 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <Flame className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No fire data available</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="card-header flex items-center gap-2">
        <Flame className="w-5 h-5 text-orange-400" />
        Fire Activity & Media Sentiment
        <span className="text-xs text-gray-500 font-normal ml-auto">
          {fires?.length || 0} fires detected
        </span>
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="date" 
              stroke="#9ca3af" 
              tick={{ fontSize: 10 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis 
              yAxisId="left"
              stroke="#f97316" 
              tick={{ fontSize: 12 }}
              label={{ 
                value: 'Fire Count', 
                angle: -90, 
                position: 'insideLeft',
                style: { fill: '#f97316', fontSize: 11 }
              }}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              stroke="#8b5cf6" 
              tick={{ fontSize: 12 }}
              domain={[0, 100]}
              label={{ 
                value: 'Sentiment', 
                angle: 90, 
                position: 'insideRight',
                style: { fill: '#8b5cf6', fontSize: 11 }
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar 
              yAxisId="left"
              dataKey="fires" 
              name="Daily Fire Count" 
              fill="#f97316" 
              radius={[4, 4, 0, 0]}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="sentimentDisplay"
              name="Sentiment Index"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={false}
            />
            <ReferenceLine
              yAxisId="right"
              y={50}
              stroke="#6b7280"
              strokeDasharray="3 3"
              label={{
                value: 'Neutral',
                position: 'right',
                fill: '#6b7280',
                fontSize: 10
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      
      {/* Sentiment interpretation */}
      {sentiment && (
        <div className="mt-3 p-3 bg-forensic-darker rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Media Sentiment:</span>
            <span className={`font-medium ${
              sentiment.final_score < -0.3 ? 'text-red-400' :
              sentiment.final_score < 0 ? 'text-yellow-400' :
              'text-green-400'
            }`}>
              {sentiment.final_score.toFixed(2)} 
              ({sentiment.final_score < -0.3 ? 'Strongly Negative' :
                sentiment.final_score < 0 ? 'Negative' :
                sentiment.final_score < 0.3 ? 'Neutral' : 'Positive'})
            </span>
          </div>
          {sentiment.dominant_narrative && (
            <p className="text-xs text-gray-500 mt-1">
              Dominant theme: <span className="text-gray-400">{sentiment.dominant_narrative}</span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// Sentiment Breakdown
function SentimentBreakdown({ sentiment }) {
  if (!sentiment) {
    return (
      <div className="card">
        <h3 className="card-header flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-purple-400" />
          Sentiment Analysis
        </h3>
        <div className="h-32 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No sentiment data available</p>
            <button className="btn btn-secondary mt-2 text-xs">
              <RefreshCw className="w-3 h-3 mr-1" />
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const sources = [
    { key: 'google', name: 'Google News', data: sentiment.google, color: '#4285f4' },
    { key: 'gdelt', name: 'GDELT', data: sentiment.gdelt, color: '#34a853' },
    { key: 'reddit', name: 'Reddit', data: sentiment.reddit, color: '#ff4500' }
  ]

  return (
    <div className="card">
      <h3 className="card-header flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-purple-400" />
        Sentiment Breakdown
        <span className="text-xs text-gray-500 font-normal ml-auto">
          Confidence: {(sentiment.confidence * 100).toFixed(0)}%
        </span>
      </h3>
      
      <div className="space-y-3">
        {sources.map(({ key, name, data, color }) => (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">{name}</span>
              {data ? (
                <span className={`font-medium ${
                  data.score < 0 ? 'text-red-400' : 'text-green-400'
                }`}>
                  {data.score.toFixed(2)} ({data.count} articles)
                </span>
              ) : (
                <span className="text-gray-600 text-xs">Unavailable</span>
              )}
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              {data && (
                <div
                  className="h-full transition-all duration-500"
                  style={{
                    width: `${((data.score + 1) / 2) * 100}%`,
                    backgroundColor: color,
                    opacity: data.score < 0 ? 0.8 : 1
                  }}
                />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Keywords */}
      {sentiment.google?.keywords?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-2">Top Keywords:</p>
          <div className="flex flex-wrap gap-1">
            {sentiment.google.keywords.slice(0, 8).map((keyword, i) => (
              <span 
                key={i}
                className="px-2 py-0.5 bg-forensic-darker rounded text-xs text-gray-400"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sample titles */}
      {sentiment.google?.sample_titles?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-2">Recent Headlines:</p>
          <ul className="space-y-1">
            {sentiment.google.sample_titles.slice(0, 3).map((title, i) => (
              <li key={i} className="text-xs text-gray-400 truncate">
                • {title}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// Main component
function ImpactAnalysis({ dossier, onRetry }) {
  const [selectedView, setSelectedView] = useState('all')

  if (!dossier) {
    return (
      <div className="card">
        <div className="h-64 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg">No data available</p>
            <p className="text-sm text-gray-600 mt-1">
              Select a region or enter a bounding box to analyze
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Analysis Overview */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-header mb-0 flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-forensic-accent" />
            Impact Analysis
          </h3>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Calendar className="w-4 h-4" />
            <span>
              {new Date(dossier.analysis_period_start).toLocaleDateString()} - {' '}
              {new Date(dossier.analysis_period_end).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-forensic-darker rounded-lg p-3 text-center">
            <Flame className="w-6 h-6 text-orange-400 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-100">{dossier.firms?.length || 0}</p>
            <p className="text-xs text-gray-500">Fire Detections</p>
          </div>
          <div className="bg-forensic-darker rounded-lg p-3 text-center">
            <TreePine className="w-6 h-6 text-red-400 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-100">
              {(dossier.gfw_glad?.length || 0) + (dossier.gfw_radd?.length || 0)}
            </p>
            <p className="text-xs text-gray-500">Deforestation Alerts</p>
          </div>
          <div className="bg-forensic-darker rounded-lg p-3 text-center">
            <TrendingDown className="w-6 h-6 text-cyan-400 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-100">
              {dossier.hansen?.total_loss_ha?.toLocaleString() || 'N/A'}
            </p>
            <p className="text-xs text-gray-500">Hectares Lost</p>
          </div>
          <div className="bg-forensic-darker rounded-lg p-3 text-center">
            <MessageSquare className="w-6 h-6 text-purple-400 mx-auto mb-1" />
            <p className={`text-2xl font-bold ${
              (dossier.sentiment?.final_score || 0) < 0 ? 'text-red-400' : 'text-green-400'
            }`}>
              {dossier.sentiment?.final_score?.toFixed(2) || 'N/A'}
            </p>
            <p className="text-xs text-gray-500">Sentiment Score</p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <NdviChart 
          sentinel={dossier.sentinel} 
          hansen={dossier.hansen}
        />
        <FireSentimentChart 
          fires={dossier.firms}
          sentiment={dossier.sentiment}
        />
      </div>

      {/* Sentiment breakdown */}
      <SentimentBreakdown sentiment={dossier.sentiment} />

      {/* Interpretation help */}
      <div className="card bg-blue-900/20 border-blue-700">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-blue-300 mb-1">Understanding the Data</h4>
            <ul className="text-xs text-blue-200/70 space-y-1">
              <li>• <strong>Fire detections</strong> show active burning detected by MODIS/VIIRS satellites</li>
              <li>• <strong>GLAD/RADD alerts</strong> indicate probable deforestation from optical/radar analysis</li>
              <li>• <strong>Negative sentiment</strong> suggests media coverage of environmental damage</li>
              <li>• <strong>Correlation</strong> between fire spikes and negative sentiment may indicate newsworthy events</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ImpactAnalysis