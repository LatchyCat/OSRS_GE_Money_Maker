/**
 * Reactive Trading Dashboard with AI-powered auto-updating recommendations.
 * 
 * Features:
 * - Real-time recommendation updates
 * - Live market alerts and signals
 * - AI pattern insights
 * - Route-specific trading intelligence
 * - Market sentiment indicators
 */

import React, { useEffect, useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Alert, AlertDescription } from '../ui/Alert'
import { useReactiveTradingContext } from '../../contexts/ReactiveTrading';
import type { MarketAlert } from '../../hooks/useReactiveTradingSocket'
import RealtimePriceChart from './RealtimePriceChart'

interface TradingRoute {
  id: string
  name: string
  description: string
  color: string
}

const TRADING_ROUTES: TradingRoute[] = [
  { id: 'high_alch', name: 'High Alchemy', description: 'Magic training with profit', color: 'purple' },
  { id: 'flipping', name: 'Item Flipping', description: 'Buy low, sell high', color: 'green' },
  { id: 'decanting', name: 'Decanting', description: 'Potion consolidation', color: 'blue' },
  { id: 'set_combining', name: 'Set Combining', description: 'Armor set arbitrage', color: 'orange' },
  { id: 'crafting', name: 'Crafting', description: 'Skill training profits', color: 'indigo' },
  { id: 'magic_runes', name: 'Rune Magic', description: 'Spell component trading', color: 'red' }
]

interface RecommendationItem {
  item_id: number
  item_name: string
  confidence: number
  profit_estimate: number
  roi_percentage: number
  volume_24h: number
  price_trend: 'bullish' | 'bearish' | 'neutral'
  ai_reasoning: string
  patterns_detected?: string[]
  risk_level: 'low' | 'medium' | 'high'
  updated_at: string
}

interface ReactiveTradingDashboardProps {
  defaultRoute?: string
  showCharts?: boolean
  maxRecommendations?: number
  className?: string
}

const ReactiveTradingDashboard: React.FC<ReactiveTradingDashboardProps> = ({
  defaultRoute = 'all',
  showCharts = true,
  maxRecommendations = 10,
  className = ''
}) => {
  const { state: socketState, actions: socketActions } = useReactiveTradingContext()
  const [selectedRoute, setSelectedRoute] = useState(defaultRoute)
  const [chartItemId, setChartItemId] = useState<number | null>(null)
  const [showAlertsOnly, setShowAlertsOnly] = useState(false)

  // Subscribe to route updates on mount and route change
  useEffect(() => {
    if (selectedRoute !== 'all') {
      socketActions.subscribeToRoute(selectedRoute)
    }
    socketActions.getCurrentRecommendations(selectedRoute)
    socketActions.getMarketAlerts()

    return () => {
      if (selectedRoute !== 'all') {
        socketActions.unsubscribe(`route_${selectedRoute}`)
      }
    }
  }, [selectedRoute, socketActions])

  // Auto-refresh recommendations every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      socketActions.getCurrentRecommendations(selectedRoute)
    }, 10000)

    return () => clearInterval(interval)
  }, [selectedRoute, socketActions])

  // Get current recommendations for selected route
  const currentRecommendations = useMemo(() => {
    const routeRecs = socketState.recommendations[selectedRoute] || []
    return routeRecs.slice(0, maxRecommendations)
  }, [socketState.recommendations, selectedRoute, maxRecommendations])

  // Filter alerts by priority if needed
  const displayedAlerts = useMemo(() => {
    if (showAlertsOnly) {
      return socketState.marketAlerts.filter(alert => alert.priority === 'high' || alert.priority === 'critical')
    }
    return socketState.marketAlerts
  }, [socketState.marketAlerts, showAlertsOnly])

  // Calculate market sentiment
  const marketSentiment = useMemo(() => {
    const recentEvents = socketState.marketEvents.slice(0, 20)
    if (recentEvents.length === 0) return 'neutral'

    const bullishEvents = recentEvents.filter(event => 
      event.event_type.includes('surge') || 
      event.event_type.includes('breakout') ||
      event.event_type.includes('bullish')
    ).length

    const bearishEvents = recentEvents.filter(event => 
      event.event_type.includes('drop') || 
      event.event_type.includes('bearish') ||
      event.event_type.includes('crash')
    ).length

    if (bullishEvents > bearishEvents * 1.5) return 'bullish'
    if (bearishEvents > bullishEvents * 1.5) return 'bearish'
    return 'neutral'
  }, [socketState.marketEvents])

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US').format(Math.round(price))
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'text-red-600 border-red-600'
      case 'high': return 'text-orange-600 border-orange-600'
      case 'medium': return 'text-yellow-600 border-yellow-600'
      default: return 'text-blue-600 border-blue-600'
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-600 bg-green-50 border-green-200'
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'high': return 'text-red-600 bg-red-50 border-red-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'bullish': return '📈'
      case 'bearish': return '📉'
      default: return '➡️'
    }
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with connection status and controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${socketState.isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              AI Trading Intelligence
              {socketState.isConnected && (
                <Badge variant="outline" className="text-green-600 border-green-600">
                  Live Updates
                </Badge>
              )}
            </CardTitle>
            
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={marketSentiment === 'bullish' ? 'text-green-600' : marketSentiment === 'bearish' ? 'text-red-600' : 'text-gray-600'}>
                {marketSentiment === 'bullish' ? '📈 Bullish' : marketSentiment === 'bearish' ? '📉 Bearish' : '➡️ Neutral'}
              </Badge>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAlertsOnly(!showAlertsOnly)}
              >
                {showAlertsOnly ? 'Show All Alerts' : 'High Priority Only'}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Route Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Trading Routes</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedRoute === 'all' ? 'default' : 'outline'}
              onClick={() => setSelectedRoute('all')}
            >
              All Routes
            </Button>
            {TRADING_ROUTES.map(route => (
              <Button
                key={route.id}
                variant={selectedRoute === route.id ? 'default' : 'outline'}
                onClick={() => setSelectedRoute(route.id)}
                className="flex items-center gap-2"
              >
                {route.name}
                {socketState.recommendations[route.id]?.length > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {socketState.recommendations[route.id].length}
                  </Badge>
                )}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Live Market Alerts */}
      {displayedAlerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              🚨 Live Market Alerts
              <Badge variant="outline">{displayedAlerts.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {displayedAlerts.map(alert => (
                <Alert key={alert.id} className="border-l-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className={getPriorityColor(alert.priority)}>
                        {alert.priority.toUpperCase()}
                      </Badge>
                      <span className="font-medium">{alert.alert_type}</span>
                      {alert.item_name && (
                        <span className="text-blue-600 cursor-pointer hover:underline" 
                              onClick={() => setChartItemId(alert.item_id || null)}>
                          {alert.item_name}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {formatTimestamp(alert.created_at)} | {(alert.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  <AlertDescription className="mt-1">
                    {alert.message}
                  </AlertDescription>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🤖 AI Recommendations
            {selectedRoute !== 'all' && (
              <Badge variant="outline">
                {TRADING_ROUTES.find(r => r.id === selectedRoute)?.name}
              </Badge>
            )}
            <Badge variant="secondary">{currentRecommendations.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {currentRecommendations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-2xl mb-2">🔄</div>
              <p>Loading AI recommendations...</p>
              <p className="text-sm">The AI is analyzing market data and patterns</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {currentRecommendations.map((rec: RecommendationItem, index) => (
                <Card key={`${rec.item_id}-${index}`} className="hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => setChartItemId(rec.item_id)}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-blue-600 hover:underline">
                        {rec.item_name}
                      </div>
                      <Badge className={getRiskColor(rec.risk_level)}>
                        {rec.risk_level} risk
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span>{getTrendIcon(rec.price_trend)}</span>
                      <span className="font-medium">{formatPrice(rec.profit_estimate)} gp profit</span>
                      <span className="text-green-600">({rec.roi_percentage.toFixed(1)}% ROI)</span>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Confidence:</span>
                        <span className="font-medium">{(rec.confidence * 100).toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">24h Volume:</span>
                        <span>{formatPrice(rec.volume_24h)}</span>
                      </div>
                      {rec.patterns_detected && rec.patterns_detected.length > 0 && (
                        <div className="mt-2">
                          <div className="text-gray-600 text-xs mb-1">Patterns:</div>
                          <div className="flex flex-wrap gap-1">
                            {rec.patterns_detected.map((pattern, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">
                                {pattern}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {rec.ai_reasoning && (
                        <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs">
                          <div className="font-medium mb-1">AI Insight:</div>
                          <div className="text-gray-600">{rec.ai_reasoning}</div>
                        </div>
                      )}
                      <div className="text-xs text-gray-500 pt-2 border-t">
                        Updated: {formatTimestamp(rec.updated_at)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Live Price Chart */}
      {showCharts && chartItemId && (
        <RealtimePriceChart
          itemId={chartItemId}
          itemName={currentRecommendations.find(r => r.item_id === chartItemId)?.item_name || `Item #${chartItemId}`}
          height={400}
          showVolume={true}
          showPatterns={true}
        />
      )}

      {/* Recent Market Events */}
      {socketState.marketEvents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              📊 Live Market Events
              <Badge variant="outline">{socketState.marketEvents.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {socketState.marketEvents.slice(0, 10).map((event, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {event.event_type}
                    </Badge>
                    {event.item_id && (
                      <span className="text-blue-600 cursor-pointer hover:underline"
                            onClick={() => setChartItemId(event.item_id!)}>
                        Item #{event.item_id}
                      </span>
                    )}
                    <span className="text-gray-600">{JSON.stringify(event.data).slice(0, 50)}...</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(event.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default ReactiveTradingDashboard