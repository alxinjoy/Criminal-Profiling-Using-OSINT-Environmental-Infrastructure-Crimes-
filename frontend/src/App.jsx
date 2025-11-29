import React, { useState, useCallback } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import DashboardLayout from './components/DashboardLayout'
import { logToServer } from './services/api'

// Available regions matching backend GLOBAL_REGIONS
const REGIONS = [
  { id: 'amazon', name: 'Amazon', bbox: [-73.0, -15.0, -45.0, 5.0], zone: 'tropical' },
  { id: 'congo', name: 'Congo Basin', bbox: [9.0, -13.0, 31.0, 10.0], zone: 'tropical' },
  { id: 'riau', name: 'Riau', bbox: [100.0, -1.0, 104.0, 3.0], zone: 'tropical' },
  { id: 'borneo', name: 'Borneo', bbox: [108.0, -4.5, 119.5, 7.5], zone: 'tropical' },
  { id: 'se_brazil', name: 'SE Brazil', bbox: [-53.0, -28.0, -40.0, -18.0], zone: 'tropical' },
  { id: 'california', name: 'California', bbox: [-124.5, 32.5, -114.0, 42.0], zone: 'temperate' },
  { id: 'siberia', name: 'Siberia', bbox: [60.0, 50.0, 140.0, 75.0], zone: 'boreal' },
  { id: 'australia', name: 'Australia', bbox: [113.0, -44.0, 154.0, -10.0], zone: 'temperate' },
]

function App() {
  // Global region state
  const [selectedRegion, setSelectedRegion] = useState(REGIONS[2]) // Default to Riau
  const [customBbox, setCustomBbox] = useState(null)

  // Handle region selection
  const handleRegionChange = useCallback((regionId) => {
    const region = REGIONS.find(r => r.id === regionId)
    if (region) {
      setSelectedRegion(region)
      setCustomBbox(null)
      console.info(`Region changed to: ${region.name}`)
    }
  }, [])

  // Handle custom bbox input
  const handleCustomBbox = useCallback((bboxString) => {
    try {
      const parts = bboxString.split(',').map(s => parseFloat(s.trim()))
      if (parts.length === 4 && parts.every(n => !isNaN(n))) {
        const [minLon, minLat, maxLon, maxLat] = parts
        
        // Validate ranges
        if (minLon < -180 || maxLon > 180 || minLat < -90 || maxLat > 90) {
          throw new Error('Coordinates out of range')
        }
        if (minLon >= maxLon || minLat >= maxLat) {
          throw new Error('Invalid bbox order')
        }
        
        setCustomBbox(parts)
        setSelectedRegion(null)
        console.info(`Custom bbox set: ${bboxString}`)
      }
    } catch (error) {
      console.error('Invalid bbox:', error.message)
      logToServer('error', `Invalid bbox input: ${bboxString}`, { error: error.message })
    }
  }, [])

  // Get current bbox (from region or custom)
  const currentBbox = customBbox || (selectedRegion?.bbox)
  const currentRegionName = selectedRegion?.name || 'Custom Area'

  // Check if current region is tropical (for GLAD/RADD warnings)
  const isTropicalRegion = selectedRegion?.zone === 'tropical' || 
    (customBbox && customBbox[1] >= -30 && customBbox[3] <= 30)

  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route 
            path="/*" 
            element={
              <DashboardLayout
                regions={REGIONS}
                selectedRegion={selectedRegion}
                onRegionChange={handleRegionChange}
                onCustomBbox={handleCustomBbox}
                currentBbox={currentBbox}
                currentRegionName={currentRegionName}
                isTropicalRegion={isTropicalRegion}
              />
            } 
          />
        </Routes>
      </Router>
    </ErrorBoundary>
  )
}

export default App