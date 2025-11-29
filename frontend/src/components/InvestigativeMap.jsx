import React, { useEffect, useMemo, useRef, useState } from 'react'
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  CircleMarker,
  Polygon,
  Polyline,
  LayersControl,
  useMap,
  AttributionControl
} from 'react-leaflet'
import L from 'leaflet'
import { 
  Flame, 
  TreePine, 
  Factory, 
  AlertTriangle,
  Layers,
  Eye,
  EyeOff
} from 'lucide-react'

// Fix Leaflet default marker icon issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Custom icons for different marker types
const createIcon = (color, size = 24) => L.divIcon({
  className: 'custom-marker',
  html: `<div style="
    background-color: ${color};
    width: ${size}px;
    height: ${size}px;
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
  "></div>`,
  iconSize: [size, size],
  iconAnchor: [size/2, size/2],
  popupAnchor: [0, -size/2]
})

const ICONS = {
  fire: createIcon('#f97316', 20),      // Orange
  glad: createIcon('#ef4444', 16),       // Red
  radd: createIcon('#eab308', 16),       // Yellow
  factory: createIcon('#3b82f6', 22),    // Blue
  industrial: createIcon('#6366f1', 18), // Indigo
}

// Helper to calculate distance between two points (Haversine formula)
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371000 // Earth's radius in meters
  const φ1 = lat1 * Math.PI / 180
  const φ2 = lat2 * Math.PI / 180
  const Δφ = (lat2 - lat1) * Math.PI / 180
  const Δλ = (lon2 - lon1) * Math.PI / 180

  const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ/2) * Math.sin(Δλ/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))

  return R * c
}

// Component to fit map bounds to dossier bbox
function MapBoundsUpdater({ bbox }) {
  const map = useMap()
  
  useEffect(() => {
    if (bbox) {
      const bounds = [
        [bbox.min_lat, bbox.min_lon],
        [bbox.max_lat, bbox.max_lon]
      ]
      map.fitBounds(bounds, { padding: [20, 20] })
    }
  }, [bbox, map])
  
  return null
}

// Layer visibility controls
function LayerControls({ layers, onToggle }) {
  return (
    <div className="absolute top-4 right-4 z-[1000] bg-forensic-dark rounded-lg border border-gray-700 p-2 shadow-lg">
      <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700">
        <Layers className="w-4 h-4 text-gray-400" />
        <span className="text-xs font-medium text-gray-300">Layers</span>
      </div>
      <div className="space-y-1">
        {Object.entries(layers).map(([key, { visible, label, color, count }]) => (
          <button
            key={key}
            onClick={() => onToggle(key)}
            className={`flex items-center gap-2 w-full px-2 py-1 rounded text-xs transition-colors ${
              visible ? 'bg-gray-700 text-gray-200' : 'text-gray-500 hover:bg-gray-800'
            }`}
          >
            {visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            <span 
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="flex-1 text-left">{label}</span>
            {count > 0 && (
              <span className="text-[10px] text-gray-500">({count})</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

// Warning banner component
function LayerWarningBanner({ warnings }) {
  if (warnings.length === 0) return null
  
  return (
    <div className="absolute bottom-4 left-4 right-4 z-[1000] space-y-1">
      {warnings.map((warning, index) => (
        <div 
          key={index}
          className="bg-yellow-900/90 border border-yellow-700 rounded px-3 py-2 text-xs text-yellow-300 flex items-center gap-2"
        >
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{warning}</span>
        </div>
      ))}
    </div>
  )
}

function InvestigativeMap({ dossier }) {
  const mapRef = useRef(null)
  const [layerCount, setLayerCount] = useState(0)
  const [warnings, setWarnings] = useState([])
  
  // Layer visibility state
  const [layerVisibility, setLayerVisibility] = useState({
    fires: { visible: true, label: 'Fires (FIRMS)', color: '#f97316', count: 0 },
    glad: { visible: true, label: 'GLAD Alerts', color: '#ef4444', count: 0 },
    radd: { visible: true, label: 'RADD Alerts', color: '#eab308', count: 0 },
    infrastructure: { visible: true, label: 'Infrastructure', color: '#3b82f6', count: 0 },
    evidence: { visible: true, label: 'Evidence Links', color: '#dc2626', count: 0 },
  })

  // Toggle layer visibility
  const toggleLayer = (key) => {
    setLayerVisibility(prev => ({
      ...prev,
      [key]: { ...prev[key], visible: !prev[key].visible }
    }))
  }

  // Process dossier data into map layers
  const { fires, gladAlerts, raddAlerts, infrastructure, evidenceLines } = useMemo(() => {
    if (!dossier) return { fires: [], gladAlerts: [], raddAlerts: [], infrastructure: [], evidenceLines: [] }

    const fires = dossier.firms || []
    const gladAlerts = dossier.gfw_glad || []
    const raddAlerts = dossier.gfw_radd || []
    const infrastructure = dossier.nearby_infra || []
    
    // Calculate evidence lines (factory <5km from fire/alert)
    const evidenceLines = []
    const MAX_EVIDENCE_DISTANCE = 5000 // 5km

    infrastructure.forEach(infra => {
      // Check proximity to fires
      fires.forEach(fire => {
        const distance = calculateDistance(
          infra.latitude, infra.longitude,
          fire.latitude, fire.longitude
        )
        if (distance <= MAX_EVIDENCE_DISTANCE) {
          evidenceLines.push({
            from: [infra.latitude, infra.longitude],
            to: [fire.latitude, fire.longitude],
            distance,
            type: 'fire',
            infraName: infra.name || `Industrial (${infra.node_type})`,
            targetType: 'fire detection'
          })
        }
      })

      // Check proximity to GLAD alerts
      gladAlerts.forEach(alert => {
        const distance = calculateDistance(
          infra.latitude, infra.longitude,
          alert.latitude, alert.longitude
        )
        if (distance <= MAX_EVIDENCE_DISTANCE) {
          evidenceLines.push({
            from: [infra.latitude, infra.longitude],
            to: [alert.latitude, alert.longitude],
            distance,
            type: 'glad',
            infraName: infra.name || `Industrial (${infra.node_type})`,
            targetType: 'deforestation alert'
          })
        }
      })

      // Check proximity to RADD alerts
      raddAlerts.forEach(alert => {
        const distance = calculateDistance(
          infra.latitude, infra.longitude,
          alert.latitude, alert.longitude
        )
        if (distance <= MAX_EVIDENCE_DISTANCE) {
          evidenceLines.push({
            from: [infra.latitude, infra.longitude],
            to: [alert.latitude, alert.longitude],
            distance,
            type: 'radd',
            infraName: infra.name || `Industrial (${infra.node_type})`,
            targetType: 'radar alert'
          })
        }
      })
    })

    return { fires, gladAlerts, raddAlerts, infrastructure, evidenceLines }
  }, [dossier])

  // Update layer counts
  useEffect(() => {
    setLayerVisibility(prev => ({
      ...prev,
      fires: { ...prev.fires, count: fires.length },
      glad: { ...prev.glad, count: gladAlerts.length },
      radd: { ...prev.radd, count: raddAlerts.length },
      infrastructure: { ...prev.infrastructure, count: infrastructure.length },
      evidence: { ...prev.evidence, count: evidenceLines.length },
    }))
  }, [fires.length, gladAlerts.length, raddAlerts.length, infrastructure.length, evidenceLines.length])

  // Count loaded layers and log
  useEffect(() => {
    let count = 0
    if (fires.length > 0) count++
    if (gladAlerts.length > 0) count++
    if (raddAlerts.length > 0) count++
    if (infrastructure.length > 0) count++
    if (evidenceLines.length > 0) count++
    // Base tile layer always counts
    count++
    
    setLayerCount(count)
    console.info("Map Layers Loaded:", count)
  }, [fires.length, gladAlerts.length, raddAlerts.length, infrastructure.length, evidenceLines.length])

  // Check for warnings from source_errors
  useEffect(() => {
    const newWarnings = []
    
    if (dossier?.source_errors) {
      dossier.source_errors.forEach(error => {
        if (error.source === 'firms') {
          newWarnings.push('Fire data (FIRMS) unavailable — check logs')
        } else if (error.source === 'gfw_glad') {
          newWarnings.push('GLAD alerts unavailable — check logs')
        } else if (error.source === 'gfw_radd') {
          newWarnings.push('RADD alerts unavailable — check logs')
        } else if (error.source === 'sentinel_hub') {
          newWarnings.push('Sentinel imagery unavailable — check logs')
        }
      })
    }

    // Check sentinel for concerning values
    if (dossier?.sentinel) {
      if (dossier.sentinel.ndvi !== null && dossier.sentinel.ndvi < 0.2) {
        // Will be highlighted on map
      }
      if (dossier.sentinel.burn_index !== null && dossier.sentinel.burn_index > 0.3) {
        // Will be highlighted on map
      }
    }
    
    setWarnings(newWarnings)
  }, [dossier?.source_errors, dossier?.sentinel])

  // Default center if no bbox
  const defaultCenter = [0, 100]
  const defaultZoom = 8

  // Calculate center from bbox
  const center = useMemo(() => {
    if (dossier?.bbox) {
      return [
        (dossier.bbox.min_lat + dossier.bbox.max_lat) / 2,
        (dossier.bbox.min_lon + dossier.bbox.max_lon) / 2
      ]
    }
    return defaultCenter
  }, [dossier?.bbox])

  // Check if sentinel shows concerning values (for glow effect)
  const showDamageHighlight = useMemo(() => {
    if (!dossier?.sentinel) return false
    const { ndvi, burn_index } = dossier.sentinel
    return (ndvi !== null && ndvi < 0.2) || (burn_index !== null && burn_index > 0.3)
  }, [dossier?.sentinel])

  return (
    <div className={`relative h-full w-full ${showDamageHighlight ? 'glow-danger' : ''}`}>
      <MapContainer
        ref={mapRef}
        center={center}
        zoom={defaultZoom}
        className="h-full w-full"
        attributionControl={false}
      >
        {/* Attribution */}
        <AttributionControl position="bottomright" prefix="" />

        {/* Update bounds when bbox changes */}
        <MapBoundsUpdater bbox={dossier?.bbox} />

        {/* Base Layers */}
        <LayersControl position="topleft">
          <LayersControl.BaseLayer checked name="Dark">
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Terrain">
            <TileLayer
              url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {/* Evidence Lines (dashed red) - Render first so they're below markers */}
        {layerVisibility.evidence.visible && evidenceLines.map((line, index) => (
          <Polyline
            key={`evidence-${index}`}
            positions={[line.from, line.to]}
            pathOptions={{
              color: '#dc2626',
              weight: 2,
              dashArray: '10, 10',
              opacity: 0.8,
              className: 'evidence-line'
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-red-600">Evidence Link</p>
                <p><strong>From:</strong> {line.infraName}</p>
                <p><strong>To:</strong> {line.targetType}</p>
                <p><strong>Distance:</strong> {(line.distance / 1000).toFixed(2)} km</p>
                <p className="text-xs text-gray-500 mt-1">
                  Proximity &lt;5km suggests potential connection
                </p>
              </div>
            </Popup>
          </Polyline>
        ))}

        {/* GLAD Alerts (red circles) */}
        {layerVisibility.glad.visible && gladAlerts.map((alert, index) => (
          <CircleMarker
            key={`glad-${index}`}
            center={[alert.latitude, alert.longitude]}
            radius={8}
            pathOptions={{
              color: '#ef4444',
              fillColor: '#ef4444',
              fillOpacity: 0.6,
              weight: 2
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-red-600">GLAD Deforestation Alert</p>
                <p><strong>Date:</strong> {new Date(alert.date).toLocaleDateString()}</p>
                <p><strong>Confidence:</strong> {alert.confidence || 'N/A'}%</p>
                <p><strong>Location:</strong> {alert.latitude.toFixed(4)}, {alert.longitude.toFixed(4)}</p>
                <p className="text-xs text-gray-500 mt-1 italic">
                  Optical satellite detection of tree cover loss
                </p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* RADD Alerts (yellow circles) */}
        {layerVisibility.radd.visible && raddAlerts.map((alert, index) => (
          <CircleMarker
            key={`radd-${index}`}
            center={[alert.latitude, alert.longitude]}
            radius={7}
            pathOptions={{
              color: '#eab308',
              fillColor: '#eab308',
              fillOpacity: 0.6,
              weight: 2
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-yellow-600">RADD Radar Alert</p>
                <p><strong>Date:</strong> {new Date(alert.date).toLocaleDateString()}</p>
                <p><strong>Confidence:</strong> {alert.confidence || 'N/A'}</p>
                <p><strong>Location:</strong> {alert.latitude.toFixed(4)}, {alert.longitude.toFixed(4)}</p>
                <p className="text-xs text-gray-500 mt-1 italic">
                  Radar-based detection (works through clouds)
                </p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Fire Markers (orange) */}
        {layerVisibility.fires.visible && fires.map((fire, index) => (
          <Marker
            key={`fire-${index}`}
            position={[fire.latitude, fire.longitude]}
            icon={ICONS.fire}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-orange-600 flex items-center gap-1">
                  <Flame className="w-4 h-4" /> Active Fire Detection
                </p>
                <p><strong>Date:</strong> {new Date(fire.acquisition_time).toLocaleString()}</p>
                <p><strong>Satellite:</strong> {fire.satellite}</p>
                <p><strong>Brightness:</strong> {fire.brightness?.toFixed(1)} K</p>
                <p><strong>Confidence:</strong> {fire.confidence}%</p>
                <p><strong>FRP:</strong> {fire.frp?.toFixed(1)} MW</p>
                <p><strong>Day/Night:</strong> {fire.daynight === 'D' ? 'Day' : 'Night'}</p>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Infrastructure Markers (blue) */}
        {layerVisibility.infrastructure.visible && infrastructure.map((infra, index) => (
          <Marker
            key={`infra-${index}`}
            position={[infra.latitude, infra.longitude]}
            icon={infra.node_type === 'factory' || infra.node_type === 'palm_oil_mill' 
              ? ICONS.factory 
              : ICONS.industrial}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-blue-600 flex items-center gap-1">
                  <Factory className="w-4 h-4" /> {infra.name || 'Industrial Facility'}
                </p>
                <p><strong>Type:</strong> {infra.node_type}</p>
                <p><strong>Distance from center:</strong> {(infra.distance_m / 1000).toFixed(2)} km</p>
                <p><strong>OSM ID:</strong> {infra.osm_id}</p>
                {infra.tags && Object.keys(infra.tags).length > 0 && (
                  <details className="mt-1">
                    <summary className="text-xs text-gray-500 cursor-pointer">Tags</summary>
                    <pre className="text-xs bg-gray-100 p-1 rounded mt-1">
                      {JSON.stringify(infra.tags, null, 2)}
                    </pre>
                  </details>
                )}
                <p className="text-xs text-gray-500 mt-1 italic">
                  Why this matters: Industrial sites near deforestation may indicate involvement
                </p>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Bbox Outline */}
        {dossier?.bbox && (
          <Polygon
            positions={[
              [dossier.bbox.min_lat, dossier.bbox.min_lon],
              [dossier.bbox.min_lat, dossier.bbox.max_lon],
              [dossier.bbox.max_lat, dossier.bbox.max_lon],
              [dossier.bbox.max_lat, dossier.bbox.min_lon],
            ]}
            pathOptions={{
              color: '#6366f1',
              weight: 2,
              fillOpacity: 0.05,
              dashArray: '5, 5'
            }}
          />
        )}
      </MapContainer>

      {/* Layer Controls */}
      <LayerControls 
        layers={layerVisibility} 
        onToggle={toggleLayer}
      />

      {/* Warning Banners */}
      <LayerWarningBanner warnings={warnings} />

      {/* Layer Count Badge */}
      <div className="absolute bottom-4 right-4 z-[1000] bg-forensic-dark/90 rounded px-2 py-1 text-xs text-gray-400">
        {layerCount} layers loaded
      </div>
    </div>
  )
}

export default InvestigativeMap