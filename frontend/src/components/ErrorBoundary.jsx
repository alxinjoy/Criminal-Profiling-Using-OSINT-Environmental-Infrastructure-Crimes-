import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { logToServer } from '../services/api'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null 
    }
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    // Store error info
    this.setState({ errorInfo })
    
    // Post error to backend /internal/logs
    logToServer('error', `React Error: ${error.message}`, {
      componentStack: errorInfo?.componentStack,
      stack: error.stack,
      url: window.location.href
    })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-forensic-darker flex items-center justify-center p-4">
          <div className="card max-w-lg w-full text-center">
            {/* Error Icon */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-red-900/30 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-forensic-danger" />
              </div>
            </div>
            
            {/* Error Message */}
            <h1 className="text-xl font-bold text-gray-100 mb-2">
              Something went wrong
            </h1>
            <p className="text-gray-400 mb-4">
              An unexpected error occurred in the application.
            </p>
            
            {/* Error Details (collapsible) */}
            {this.state.error && (
              <details className="mb-4 text-left">
                <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-300">
                  View error details
                </summary>
                <div className="mt-2 p-3 bg-forensic-darker rounded text-xs font-mono text-red-400 overflow-auto max-h-40">
                  <p className="font-bold">{this.state.error.toString()}</p>
                  {this.state.errorInfo?.componentStack && (
                    <pre className="mt-2 text-gray-500 whitespace-pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}
            
            {/* Action Buttons */}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="btn btn-secondary flex items-center gap-2"
              >
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="btn btn-primary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Reload Page
              </button>
            </div>
            
            {/* Log notice */}
            <p className="mt-4 text-xs text-gray-600">
              This error has been logged for investigation.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary