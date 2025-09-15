/**
 * Real-time price chart component with live updates via WebSocket.
 * 
 * Features:
 * - Live price data streaming
 * - Interactive candlestick/line charts
 * - Volume indicators
 * - Pattern detection overlays
 * - AI signal annotations
 */

import React, { useEffect, useState, useMemo, useRef } from 'react'
import { Line, ResponsiveContainer, LineChart, XAxis, YAxis, CartesianGrid, Tooltip, Area, ComposedChart, Bar } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { useReactiveTradingContext } from '../../contexts/ReactiveTrading'
import { 
  XMarkIcon, 
  ChartBarIcon, 
  PresentationChartLineIcon,
  ArrowsPointingOutIcon,
  CogIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline'

interface PriceDataPoint {
  timestamp: string
  time: number
  high_price: number
  low_price: number
  high_volume: number
  low_volume: number
  midPrice: number
  spread: number
  avgVolume: number
}

interface RealtimePriceChartProps {
  itemId: number
  itemName: string
  timeframe?: '1m' | '5m' | '15m' | '1h' | '4h' | '24h' | '7d'
  height?: number
  showVolume?: boolean
  showPatterns?: boolean
  className?: string
  displayMode?: 'inline' | 'modal' | 'sidebar'
  onClose?: () => void
  chartType?: 'line' | 'area' | 'candlestick' | 'ohlc'
  showTechnicalIndicators?: boolean
}

const RealtimePriceChart: React.FC<RealtimePriceChartProps> = ({
  itemId,
  itemName,
  timeframe = '5m',
  height = 400,
  showVolume = true,
  showPatterns = true,
  className = '',
  displayMode = 'inline',
  onClose,
  chartType = 'line',
  showTechnicalIndicators = false
}) => {
  const { state: socketState, actions: socketActions } = useReactiveTradingContext()
  const [priceHistory, setPriceHistory] = useState<PriceDataPoint[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedTimeframe, setSelectedTimeframe] = useState(timeframe)
  const [selectedChartType, setSelectedChartType] = useState(chartType)
  const [showTechnicalIndicatorsState, setShowTechnicalIndicatorsState] = useState(showTechnicalIndicators)
  const chartContainerRef = useRef<HTMLDivElement>(null)

  // Calculate technical indicators if enabled - MOVED TO TOP TO FIX HOOKS ORDER
  const technicalIndicators = useMemo(() => {
    if (!showTechnicalIndicatorsState || priceHistory.length < 20) return null;
    
    const prices = priceHistory.map(p => p.midPrice);
    
    // Simple Moving Average (20 period)
    const sma20 = prices.map((_, index) => {
      if (index < 19) return null;
      const sum = prices.slice(index - 19, index + 1).reduce((a, b) => a + b, 0);
      return sum / 20;
    });
    
    // RSI calculation (simplified)
    const rsi = prices.map((_, index) => {
      if (index < 14) return 50;
      const changes = prices.slice(index - 13, index + 1).map((price, i, arr) => 
        i === 0 ? 0 : price - arr[i - 1]
      );
      const gains = changes.filter(c => c > 0).reduce((a, b) => a + b, 0) / 14;
      const losses = Math.abs(changes.filter(c => c < 0).reduce((a, b) => a + b, 0)) / 14;
      return losses === 0 ? 100 : 100 - (100 / (1 + gains / losses));
    });
    
    return priceHistory.map((point, index) => ({
      ...point,
      sma20: sma20[index],
      rsi: rsi[index]
    }));
  }, [priceHistory, showTechnicalIndicatorsState]);

  const chartData = technicalIndicators || priceHistory;

  // Subscribe to item updates on mount - FIXED: removed socketActions from deps
  useEffect(() => {
    // Reduced logging: only log chart subscriptions if debugging
    const success = socketActions.subscribeToItem(itemId.toString());
    setIsLoading(true);
    
    // Load initial historical data
    loadHistoricalData();

    if (success) {
      return () => {
        socketActions.unsubscribe(`item_${itemId}`);
      };
    }
  }, [itemId, selectedTimeframe]); // Removed socketActions from deps to prevent infinite loops

  // Handle real-time price updates
  useEffect(() => {
    const priceUpdate = socketState.priceUpdates[itemId]
    if (priceUpdate) {
      const newDataPoint: PriceDataPoint = {
        timestamp: priceUpdate.timestamp,
        time: new Date(priceUpdate.timestamp).getTime(),
        high_price: priceUpdate.high_price,
        low_price: priceUpdate.low_price,
        high_volume: priceUpdate.high_volume,
        low_volume: priceUpdate.low_volume,
        midPrice: (priceUpdate.high_price + priceUpdate.low_price) / 2,
        spread: priceUpdate.high_price - priceUpdate.low_price,
        avgVolume: (priceUpdate.high_volume + priceUpdate.low_volume) / 2
      }

      setPriceHistory(prev => {
        const updated = [...prev, newDataPoint]
        // Keep only last 100 data points for performance
        return updated.slice(-100)
      })
    }
  }, [socketState.priceUpdates, itemId])

  const loadHistoricalData = async () => {
    try {
      // Load historical price data from backend API
      const response = await fetch(`/api/v1/prices/historical/${itemId}?timeframe=${selectedTimeframe}&limit=50`)
      if (response.ok) {
        const data = await response.json()
        const formattedData: PriceDataPoint[] = data.map((point: any) => ({
          timestamp: point.timestamp,
          time: new Date(point.timestamp).getTime(),
          high_price: point.high_price,
          low_price: point.low_price,
          high_volume: point.high_volume,
          low_volume: point.low_volume,
          midPrice: (point.high_price + point.low_price) / 2,
          spread: point.high_price - point.low_price,
          avgVolume: (point.high_volume + point.low_volume) / 2
        }))
        setPriceHistory(formattedData)
        console.log(`✅ Loaded ${formattedData.length} historical data points for item ${itemId}`)
      } else {
        console.warn(`⚠️ Historical API returned ${response.status}: ${response.statusText}`)
        generateMockHistoricalData()
      }
    } catch (error) {
      console.warn('⚠️ Historical price data API connection failed, using mock data for demo:', error)
      // Use mock data for demonstration until backend API is fully connected
      generateMockHistoricalData()
    } finally {
      setIsLoading(false)
    }
  }

  const generateMockHistoricalData = () => {
    const now = Date.now()
    const points: PriceDataPoint[] = []
    
    for (let i = 50; i >= 0; i--) {
      const timestamp = new Date(now - i * 5 * 60 * 1000) // 5-minute intervals
      const basePrice = 1000 + Math.sin(i * 0.1) * 100
      const volatility = 20
      
      const high_price = basePrice + Math.random() * volatility
      const low_price = basePrice - Math.random() * volatility
      const volume = 100 + Math.random() * 500
      
      points.push({
        timestamp: timestamp.toISOString(),
        time: timestamp.getTime(),
        high_price: Math.round(high_price),
        low_price: Math.round(low_price),
        high_volume: Math.round(volume * (1 + Math.random() * 0.3)),
        low_volume: Math.round(volume * (1 - Math.random() * 0.3)),
        midPrice: Math.round((high_price + low_price) / 2),
        spread: Math.round(high_price - low_price),
        avgVolume: Math.round(volume)
      })
    }
    
    setPriceHistory(points)
  }

  // Get relevant patterns for this item
  const itemPatterns = useMemo(() => {
    return socketState.patternDetections.filter(pattern => pattern.item_id === itemId)
  }, [socketState.patternDetections, itemId])

  // Get recent volume surges for this item
  const itemVolumeSurges = useMemo(() => {
    return socketState.volumeSurges.filter(surge => surge.item_id === itemId)
  }, [socketState.volumeSurges, itemId])

  // Calculate price statistics
  const priceStats = useMemo(() => {
    if (priceHistory.length === 0) return null

    const prices = priceHistory.map(p => p.midPrice)
    const volumes = priceHistory.map(p => p.avgVolume)
    
    const currentPrice = prices[prices.length - 1]
    const previousPrice = prices[prices.length - 2]
    const change = currentPrice - previousPrice
    const changePercent = previousPrice ? (change / previousPrice) * 100 : 0
    
    return {
      current: currentPrice,
      change: change,
      changePercent: changePercent,
      high24h: Math.max(...prices),
      low24h: Math.min(...prices),
      avgVolume: volumes.reduce((a, b) => a + b, 0) / volumes.length
    }
  }, [priceHistory])

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US').format(Math.round(price))
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white dark:bg-gray-800 p-3 border rounded-lg shadow-lg">
          <p className="text-sm font-medium">{formatTimestamp(data.timestamp)}</p>
          <div className="space-y-1 text-sm">
            <p className="text-green-600">High: {formatPrice(data.high_price)} gp</p>
            <p className="text-red-600">Low: {formatPrice(data.low_price)} gp</p>
            <p className="text-blue-600">Mid: {formatPrice(data.midPrice)} gp</p>
            {showVolume && (
              <p className="text-purple-600">Volume: {formatPrice(data.avgVolume)}</p>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-gray-400 animate-pulse" />
            Loading Price Chart...
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        </CardContent>
      </Card>
    )
  }

  // Modal wrapper for modal display mode
  const ChartContent = () => (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${socketState.isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            {itemName} #{itemId}
            {socketState.isConnected && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                Live
              </Badge>
            )}
          </CardTitle>
          
          <div className="flex gap-2 flex-wrap items-center">
            {/* Timeframe Buttons */}
            <div className="flex gap-1">
              {['1m', '5m', '15m', '1h', '4h', '24h', '7d'].map((tf) => (
                <Button
                  key={tf}
                  variant={selectedTimeframe === tf ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedTimeframe(tf as any)}
                >
                  {tf}
                </Button>
              ))}
            </div>
            
            {/* Chart Type Selector */}
            <div className="flex gap-1 border-l pl-2 ml-2">
              <Button
                variant={selectedChartType === 'line' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedChartType('line')}
                title="Line Chart"
              >
                <PresentationChartLineIcon className="w-4 h-4" />
              </Button>
              <Button
                variant={selectedChartType === 'area' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedChartType('area')}
                title="Area Chart"
              >
                <ChartBarIcon className="w-4 h-4" />
              </Button>
            </div>
            
            {/* Technical Indicators Toggle */}
            <Button
              variant={showTechnicalIndicatorsState ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowTechnicalIndicatorsState(!showTechnicalIndicatorsState)}
              title="Technical Indicators"
            >
              <CogIcon className="w-4 h-4" />
            </Button>
            
            {/* Export Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // Export chart data as CSV
                const csvData = priceHistory.map(point => ({
                  timestamp: point.timestamp,
                  high_price: point.high_price,
                  low_price: point.low_price,
                  mid_price: point.midPrice,
                  volume: point.avgVolume
                }));
                const csv = [
                  'timestamp,high_price,low_price,mid_price,volume',
                  ...csvData.map(row => Object.values(row).join(','))
                ].join('\n');
                const blob = new Blob([csv], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${itemName}_price_data.csv`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              title="Export Data"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
            </Button>
            
            {/* Close Button for Modal Mode */}
            {displayMode === 'modal' && onClose && (
              <Button
                variant="outline"
                size="sm"
                onClick={onClose}
                title="Close Chart"
              >
                <XMarkIcon className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
        
        {priceStats && (
          <div className="flex items-center gap-4 text-sm">
            <div className="font-semibold">
              {formatPrice(priceStats.current)} gp
            </div>
            <div className={`flex items-center gap-1 ${priceStats.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              <span>{priceStats.change >= 0 ? '↗' : '↘'}</span>
              <span>{formatPrice(Math.abs(priceStats.change))} ({priceStats.changePercent.toFixed(2)}%)</span>
            </div>
            <div className="text-gray-500">
              H: {formatPrice(priceStats.high24h)} L: {formatPrice(priceStats.low24h)}
            </div>
          </div>
        )}
      </CardHeader>
      
      <CardContent>
        <div ref={chartContainerRef} style={{ height: `${height}px` }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis 
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                interval="preserveStartEnd"
              />
              <YAxis 
                domain={['dataMin - 20', 'dataMax + 20']}
                tickFormatter={formatPrice}
              />
              {showVolume && (
                <YAxis 
                  yAxisId="volume"
                  orientation="right"
                  domain={[0, 'dataMax']}
                  hide
                />
              )}
              <Tooltip content={<CustomTooltip />} />
              
              {/* Volume bars (if enabled) */}
              {showVolume && (
                <Bar 
                  yAxisId="volume"
                  dataKey="avgVolume" 
                  fill="#8884d8" 
                  opacity={0.3}
                />
              )}
              
              {/* Chart Type Rendering */}
              {selectedChartType === 'area' && (
                <>
                  {/* Price range area */}
                  <Area
                    type="monotone"
                    dataKey="high_price"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.1}
                  />
                  <Area
                    type="monotone"
                    dataKey="low_price"
                    stroke="#ef4444"
                    fill="#ef4444"
                    fillOpacity={0.1}
                  />
                  {/* Mid price area */}
                  <Area
                    type="monotone"
                    dataKey="midPrice"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.2}
                  />
                </>
              )}
              
              {selectedChartType === 'line' && (
                <>
                  {/* High/Low lines */}
                  <Line
                    type="monotone"
                    dataKey="high_price"
                    stroke="#10b981"
                    strokeWidth={1}
                    dot={false}
                    strokeDasharray="3 3"
                  />
                  <Line
                    type="monotone"
                    dataKey="low_price"
                    stroke="#ef4444"
                    strokeWidth={1}
                    dot={false}
                    strokeDasharray="3 3"
                  />
                  {/* Mid price line */}
                  <Line
                    type="monotone"
                    dataKey="midPrice"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </>
              )}
              
              {/* Technical Indicators */}
              {showTechnicalIndicatorsState && technicalIndicators && (
                <>
                  <Line
                    type="monotone"
                    dataKey="sma20"
                    stroke="#ff7c00"
                    strokeWidth={1.5}
                    dot={false}
                    name="SMA 20"
                    connectNulls={false}
                  />
                </>
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        
        {/* Pattern Detection & Volume Surge Alerts */}
        {(showPatterns && (itemPatterns.length > 0 || itemVolumeSurges.length > 0)) && (
          <div className="mt-4 space-y-2">
            {itemPatterns.map((pattern, index) => (
              <div key={index} className="flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
                <Badge variant="secondary">Pattern</Badge>
                <span className="font-medium">{pattern.pattern_name}</span>
                <span className="text-gray-600">
                  {(pattern.confidence * 100).toFixed(1)}% confidence
                </span>
                <span className="text-green-600">
                  Target: {formatPrice(pattern.predicted_target)} gp
                </span>
                <span className="text-xs text-gray-500 ml-auto">
                  {formatTimestamp(pattern.timestamp)}
                </span>
              </div>
            ))}
            
            {itemVolumeSurges.map((surge, index) => (
              <div key={index} className="flex items-center gap-2 p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg text-sm">
                <Badge variant="outline" className="border-orange-500 text-orange-600">
                  Volume Surge
                </Badge>
                <span className="font-medium">{surge.surge_factor.toFixed(1)}x normal volume</span>
                <span className="text-gray-600">
                  {formatPrice(surge.current_volume)} vs {formatPrice(surge.average_volume)} avg
                </span>
                <span className="text-xs text-gray-500 ml-auto">
                  {formatTimestamp(surge.timestamp)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );

  // Return based on display mode
  if (displayMode === 'modal') {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
          <ChartContent />
        </div>
      </div>
    );
  }

  if (displayMode === 'sidebar') {
    return (
      <div className="fixed right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-700 z-40 overflow-y-auto">
        <ChartContent />
      </div>
    );
  }

  // Default inline mode
  return <ChartContent />;
}

export default RealtimePriceChart