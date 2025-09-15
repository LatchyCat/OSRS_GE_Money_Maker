/**
 * Complete Reactive Trading Page - Integration of all AI-powered trading features.
 * 
 * This page combines:
 * - Real-time trading intelligence dashboard
 * - Live price charts with pattern detection
 * - AI-powered chat integration
 * - Market alerts and notifications
 * - Auto-updating recommendations
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import ReactiveTradingDashboard from './ReactiveTradingDashboard'
import RealtimePriceChart from './RealtimePriceChart'
import { useReactiveTradingContext } from '../../contexts/ReactiveTrading'

interface TradingStats {
  totalRecommendations: number
  activeAlerts: number
  connectedUsers: number
  patternDetections: number
  volumeSurges: number
  lastUpdate: string
}

const ReactiveTradingPage: React.FC = () => {
  const { state: socketState, actions: socketActions } = useReactiveTradingContext()
  const [selectedView, setSelectedView] = useState<'dashboard' | 'charts' | 'analysis'>('dashboard')
  const [featuredItems, setFeaturedItems] = useState<number[]>([995, 4151, 2357]) // Default featured items
  
  // Calculate real-time stats
  const stats: TradingStats = {
    totalRecommendations: Object.values(socketState.recommendations).reduce((total, recs) => total + recs.length, 0),
    activeAlerts: socketState.marketAlerts.filter(alert => alert.is_active).length,
    connectedUsers: socketState.isConnected ? 1 : 0,
    patternDetections: socketState.patternDetections.length,
    volumeSurges: socketState.volumeSurges.length,
    lastUpdate: socketState.lastMessage?.timestamp || new Date().toISOString()
  }

  // Auto-refresh recommendations every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      socketActions.getCurrentRecommendations('all')
      socketActions.getMarketAlerts()
    }, 30000)

    return () => clearInterval(interval)
  }, [socketActions])

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                🚀 AI Super Trader
              </h1>
              <Badge variant={socketState.isConnected ? 'success' : 'danger'}>
                {socketState.isConnected ? '🟢 Live' : '🔴 Offline'}
              </Badge>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="hidden md:flex items-center gap-6 text-sm text-gray-600 dark:text-gray-300">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{stats.totalRecommendations}</span>
                  <span>Active Recommendations</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{stats.activeAlerts}</span>
                  <span>Market Alerts</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{stats.patternDetections}</span>
                  <span>Patterns Detected</span>
                </div>
              </div>
              
              <div className="text-xs text-gray-500">
                Last Update: {formatTimestamp(stats.lastUpdate)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white dark:bg-gray-800 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-2 py-4">
            <Button
              variant={selectedView === 'dashboard' ? 'default' : 'outline'}
              onClick={() => setSelectedView('dashboard')}
              className="flex items-center gap-2"
            >
              📊 Trading Dashboard
            </Button>
            <Button
              variant={selectedView === 'charts' ? 'default' : 'outline'}
              onClick={() => setSelectedView('charts')}
              className="flex items-center gap-2"
            >
              📈 Live Charts
            </Button>
            <Button
              variant={selectedView === 'analysis' ? 'default' : 'outline'}
              onClick={() => setSelectedView('analysis')}
              className="flex items-center gap-2"
            >
              🧠 AI Analysis
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {selectedView === 'dashboard' && (
          <ReactiveTradingDashboard
            defaultRoute="all"
            showCharts={true}
            maxRecommendations={15}
          />
        )}

        {selectedView === 'charts' && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>📈 Featured Live Price Charts</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 lg:grid-cols-2">
                  {featuredItems.map(itemId => (
                    <RealtimePriceChart
                      key={itemId}
                      itemId={itemId}
                      itemName={`Item #${itemId}`}
                      height={350}
                      showVolume={true}
                      showPatterns={true}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Quick Chart Controls */}
            <Card>
              <CardHeader>
                <CardTitle>🎯 Quick Chart Access</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    { id: 995, name: 'Coins', category: 'Currency' },
                    { id: 4151, name: 'Abyssal whip', category: 'Weapons' },
                    { id: 2357, name: 'Gold bar', category: 'Bars' },
                    { id: 1516, name: 'Yew logs', category: 'Logs' },
                  ].map(item => (
                    <Button
                      key={item.id}
                      variant="outline"
                      onClick={() => {
                        if (!featuredItems.includes(item.id)) {
                          setFeaturedItems(prev => [...prev.slice(0, 2), item.id])
                        }
                      }}
                      className="flex flex-col items-start p-4 h-auto"
                    >
                      <span className="font-medium">{item.name}</span>
                      <span className="text-sm text-gray-500">{item.category}</span>
                      <Badge variant="outline" className="mt-2 text-xs">
                        #{item.id}
                      </Badge>
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {selectedView === 'analysis' && (
          <div className="space-y-6">
            {/* Real-time Market Intelligence */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  🧠 AI Market Intelligence
                  <Badge variant="info">Real-time</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Pattern Detection Summary */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">🎯 Pattern Detection</h3>
                    {socketState.patternDetections.length === 0 ? (
                      <p className="text-gray-500">No patterns detected yet. The AI is analyzing market data...</p>
                    ) : (
                      <div className="space-y-2">
                        {socketState.patternDetections.slice(0, 5).map((pattern, index) => (
                          <div key={index} className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="font-medium">Item #{pattern.item_id}</span>
                              <Badge variant="info" className="text-xs">
                                {(pattern.confidence * 100).toFixed(1)}%
                              </Badge>
                            </div>
                            <div className="text-sm text-gray-600 mt-1">
                              {pattern.pattern_name} → Target: {pattern.predicted_target} gp
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatTimestamp(pattern.timestamp)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Volume Analysis */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">📊 Volume Analysis</h3>
                    {socketState.volumeSurges.length === 0 ? (
                      <p className="text-gray-500">No volume surges detected. Monitoring continues...</p>
                    ) : (
                      <div className="space-y-2">
                        {socketState.volumeSurges.slice(0, 5).map((surge, index) => (
                          <div key={index} className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="font-medium">Item #{surge.item_id}</span>
                              <Badge variant="warning" className="text-xs">
                                {surge.surge_factor.toFixed(1)}x
                              </Badge>
                            </div>
                            <div className="text-sm text-gray-600 mt-1">
                              Volume: {surge.current_volume.toLocaleString()} vs {surge.average_volume.toLocaleString()} avg
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatTimestamp(surge.timestamp)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* System Performance */}
            <Card>
              <CardHeader>
                <CardTitle>⚡ System Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{stats.totalRecommendations}</div>
                    <div className="text-sm text-gray-600">Active Recommendations</div>
                  </div>
                  <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{stats.patternDetections}</div>
                    <div className="text-sm text-gray-600">Patterns Detected</div>
                  </div>
                  <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <div className="text-2xl font-bold text-orange-600">{stats.volumeSurges}</div>
                    <div className="text-sm text-gray-600">Volume Surges</div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">{stats.activeAlerts}</div>
                    <div className="text-sm text-gray-600">Active Alerts</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Market Events */}
            <Card>
              <CardHeader>
                <CardTitle>📈 Recent Market Events</CardTitle>
              </CardHeader>
              <CardContent>
                {socketState.marketEvents.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-4xl mb-2">🔄</div>
                    <p>Monitoring market for events...</p>
                    <p className="text-sm">Real-time events will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {socketState.marketEvents.map((event, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-xs">
                            {event.event_type}
                          </Badge>
                          {event.item_id && (
                            <span className="text-sm text-blue-600">Item #{event.item_id}</span>
                          )}
                          <span className="text-sm text-gray-600">
                            {JSON.stringify(event.data).slice(0, 80)}...
                          </span>
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatTimestamp(event.timestamp)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Status Footer */}
      <div className="bg-gray-100 dark:bg-gray-800 border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-300">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${socketState.isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span>WebSocket {socketState.isConnected ? 'Connected' : 'Disconnected'}</span>
              </div>
              {socketState.error && (
                <div className="flex items-center gap-2 text-red-600">
                  <span>⚠️ {socketState.error}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-6">
              <span>Last Update: {formatTimestamp(stats.lastUpdate)}</span>
              <span>🚀 AI Super Trader v2.0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReactiveTradingPage