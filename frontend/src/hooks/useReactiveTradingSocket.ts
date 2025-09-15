/**
 * React hook for connecting to the reactive trading intelligence WebSocket.
 * 
 * Provides real-time updates for:
 * - Market events and price changes
 * - AI-powered recommendation updates
 * - Pattern detection notifications
 * - Volume surge alerts
 * - Trading signals
 */

import { useEffect, useRef, useState, useCallback } from 'react'

export interface MarketEvent {
  type: 'market_event'
  event_type: string
  item_id?: number
  data: any
  timestamp: string
}

export interface RecommendationUpdate {
  type: 'recommendation_update'
  route_type: string
  update_type: string
  recommendations: any[]
  timestamp: string
}

export interface PriceUpdate {
  type: 'price_update'
  item_id: number
  high_price: number
  low_price: number
  high_volume: number
  low_volume: number
  timestamp: string
}

export interface PatternDetected {
  type: 'pattern_detected'
  item_id: number
  pattern_name: string
  confidence: number
  predicted_target: number
  timestamp: string
}

export interface VolumeSurge {
  type: 'volume_surge'
  item_id: number
  current_volume: number
  average_volume: number
  surge_factor: number
  timestamp: string
}

export interface MarketAlert {
  id: number
  item_id?: number
  item_name?: string
  alert_type: string
  priority: string
  message: string
  confidence: number
  is_active: boolean
  created_at: string
}

export type TradingSocketMessage = 
  | MarketEvent 
  | RecommendationUpdate 
  | PriceUpdate 
  | PatternDetected 
  | VolumeSurge
  | { type: 'connection_established'; timestamp: string; message: string }
  | { type: 'subscription_confirmed'; subscription: string; message: string }
  | { type: 'unsubscription_confirmed'; subscription: string; message?: string }
  | { type: 'unsubscribe_from_item'; item_id: number; message?: string }  // Backend sends this message
  | { type: 'current_recommendations'; route_type: string; recommendations: any[]; timestamp: string }
  | { type: 'market_alerts'; alerts: MarketAlert[]; timestamp: string }
  | { type: 'error'; message: string }

export interface TradingSocketState {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: TradingSocketMessage | null
  marketEvents: MarketEvent[]
  recommendations: { [routeType: string]: any[] }
  priceUpdates: { [itemId: number]: PriceUpdate }
  patternDetections: PatternDetected[]
  volumeSurges: VolumeSurge[]
  marketAlerts: MarketAlert[]
}

export interface TradingSocketActions {
  subscribeToItem: (itemId: string) => void
  unsubscribeFromItem: (itemId: string) => void
  subscribeToRoute: (routeType: string) => void
  unsubscribe: (subscription: string) => void
  getCurrentRecommendations: (routeType?: string) => void
  getMarketAlerts: () => void
  clearMessages: () => void
  clearAlerts: () => void
}

export interface UseReactiveTradingSocketReturn {
  state: TradingSocketState
  actions: TradingSocketActions
}

const WS_URL = `ws://localhost:8002/ws/trading/`
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 5
const SUBSCRIPTION_RATE_LIMIT = 1000 // Minimum time between subscription attempts (ms)

export const useReactiveTradingSocket = (): UseReactiveTradingSocketReturn => {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)
  const lastSubscriptionTime = useRef<{ [key: string]: number }>({}) // Rate limiting for subscriptions
  const activeSubscriptions = useRef<Set<string>>(new Set()) // Track active subscriptions for deduplication
  const subscriptionRefCounts = useRef<{ [key: string]: number }>({}) // Reference counting for shared subscriptions
  const isConnecting = useRef(false) // Prevent multiple concurrent connection attempts
  const hasConnectedOnce = useRef(false) // Track if we've ever connected to prevent re-mounting issues
  
  const [state, setState] = useState<TradingSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
    marketEvents: [],
    recommendations: {},
    priceUpdates: {},
    patternDetections: [],
    volumeSurges: [],
    marketAlerts: []
  })

  // All callback functions removed - using direct inline logic in useEffect

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
      return true
    } else {
      // Only log warning if we're not in a cleanup phase
      if (message.type !== 'unsubscribe' && message.type !== 'unsubscribe_from_item') {
        console.warn('Trading WebSocket not connected, cannot send message:', message)
      }
      return false
    }
  }, [])

  // Actions
  const subscribeToItem = useCallback((itemId: string) => {
    if (ws.current?.readyState !== WebSocket.OPEN) {
      console.warn(`⚠️ Cannot subscribe to item ${itemId} - WebSocket not connected`)
      return false
    }
    
    const subscriptionKey = `item_${itemId}`
    
    // Check if already subscribed (deduplication)
    if (activeSubscriptions.current.has(subscriptionKey)) {
      // Increment reference count for shared subscription
      subscriptionRefCounts.current[subscriptionKey] = (subscriptionRefCounts.current[subscriptionKey] || 0) + 1
      console.log(`🔄 Item ${itemId} already subscribed, ref count: ${subscriptionRefCounts.current[subscriptionKey]}`)
      return true // Return success since subscription exists
    }
    
    // Add to tracking before sending message
    activeSubscriptions.current.add(subscriptionKey)
    subscriptionRefCounts.current[subscriptionKey] = 1
    
    const success = sendMessage({
      type: 'subscribe_to_item',
      item_id: parseInt(itemId)
    })
    
    if (!success) {
      // Remove from tracking if send failed
      activeSubscriptions.current.delete(subscriptionKey)
      delete subscriptionRefCounts.current[subscriptionKey]
    }
    
    return success
  }, [sendMessage])

  const unsubscribeFromItem = useCallback((itemId: string) => {
    const subscriptionKey = `item_${itemId}`
    
    // Check if subscription exists - if not, silently ignore to prevent spam logs
    if (!activeSubscriptions.current.has(subscriptionKey)) {
      // Only log if debug mode or significant issue
      if (console.debug) {
        console.debug(`📋 Skipping unsubscribe for item ${itemId} - not currently subscribed`)
      }
      return true // Return true to indicate "successful" cleanup
    }
    
    // Decrement reference count
    const currentRefCount = subscriptionRefCounts.current[subscriptionKey] || 1
    subscriptionRefCounts.current[subscriptionKey] = currentRefCount - 1
    
    console.log(`🔄 Item ${itemId} unsubscribe request, ref count: ${subscriptionRefCounts.current[subscriptionKey]}`)
    
    // Only actually unsubscribe when ref count reaches 0
    if (subscriptionRefCounts.current[subscriptionKey] <= 0) {
      activeSubscriptions.current.delete(subscriptionKey)
      delete subscriptionRefCounts.current[subscriptionKey]
      
      console.log(`🔗 Actually unsubscribing from item ${itemId} - ref count reached 0`)
      
      // Only send unsubscribe message if WebSocket is connected
      if (ws.current?.readyState === WebSocket.OPEN) {
        return sendMessage({
          type: 'unsubscribe',
          subscription: subscriptionKey
        })
      }
    }
    
    return true // Successful "unsubscribe" (just decremented ref count)
  }, [sendMessage])

  const subscribeToRoute = useCallback((routeType: string) => {
    // Enhanced rate limiting and deduplication
    const subscriptionKey = `route_${routeType}`
    const now = Date.now()
    const lastTime = lastSubscriptionTime.current[subscriptionKey] || 0
    
    if (now - lastTime < SUBSCRIPTION_RATE_LIMIT) {
      console.warn(`⚠️ Rate limiting subscription to ${routeType}, waiting ${SUBSCRIPTION_RATE_LIMIT}ms between attempts`)
      return false
    }
    
    if (ws.current?.readyState !== WebSocket.OPEN) {
      console.warn(`⚠️ Cannot subscribe to ${routeType} - WebSocket not connected`)
      return false
    }
    
    // Check if already subscribed (deduplication)
    if (activeSubscriptions.current.has(subscriptionKey)) {
      subscriptionRefCounts.current[subscriptionKey] = (subscriptionRefCounts.current[subscriptionKey] || 0) + 1
      console.log(`🔄 Route ${routeType} already subscribed, ref count: ${subscriptionRefCounts.current[subscriptionKey]}`)
      return true
    }
    
    // Add to tracking
    activeSubscriptions.current.add(subscriptionKey)
    subscriptionRefCounts.current[subscriptionKey] = 1
    lastSubscriptionTime.current[subscriptionKey] = now
    
    console.log(`📡 Subscribing to route: ${routeType}`)
    
    const success = sendMessage({
      type: 'subscribe_to_route',
      route_type: routeType
    })
    
    if (!success) {
      // Remove from tracking if send failed
      activeSubscriptions.current.delete(subscriptionKey)
      delete subscriptionRefCounts.current[subscriptionKey]
    }
    
    return success
  }, [sendMessage])

  const unsubscribe = useCallback((subscription: string) => {
    if (ws.current?.readyState !== WebSocket.OPEN) {
      console.warn(`⚠️ Cannot unsubscribe from ${subscription} - WebSocket not connected`)
      return false
    }
    
    return sendMessage({
      type: 'unsubscribe',
      subscription: subscription
    })
  }, [sendMessage])

  const getCurrentRecommendations = useCallback((routeType: string = 'all') => {
    sendMessage({
      type: 'get_current_recommendations',
      route_type: routeType
    })
  }, [sendMessage])

  const getMarketAlerts = useCallback(() => {
    sendMessage({
      type: 'get_market_alerts'
    })
  }, [sendMessage])

  const clearMessages = useCallback(() => {
    setState(prev => ({
      ...prev,
      marketEvents: [],
      patternDetections: [],
      volumeSurges: [],
      lastMessage: null,
      error: null
    }))
  }, [])

  const clearAlerts = useCallback(() => {
    setState(prev => ({
      ...prev,
      marketAlerts: []
    }))
  }, [])

  // Effect for connection management
  // CRITICAL: Empty dependency array to prevent infinite loop!
  // This effect MUST only run once on mount, never again.
  useEffect(() => {
    // Inline connection logic to avoid dependency issues
    const initConnection = () => {
      if (isConnecting.current || ws.current?.readyState === WebSocket.OPEN) {
        return
      }
      
      isConnecting.current = true
      setState(prev => ({ ...prev, isConnecting: true, error: null }))
      console.log('🔌 Attempting WebSocket connection to:', WS_URL)

      try {
        ws.current = new WebSocket(WS_URL)

        ws.current.onopen = () => {
          console.log('🚀 Trading WebSocket connected successfully')
          isConnecting.current = false
          hasConnectedOnce.current = true
          reconnectAttempts.current = 0
          setState(prev => ({ 
            ...prev,
            isConnected: true, 
            isConnecting: false, 
            error: null 
          }))
        }

        ws.current.onmessage = (event) => {
          try {
            const message: TradingSocketMessage = JSON.parse(event.data)
            setState(prev => ({ ...prev, lastMessage: message }))

            switch (message.type) {
              case 'connection_established':
                console.log('🔌 Trading WebSocket connected:', message.message)
                break

              case 'market_event':
                setState(prev => ({
                  ...prev,
                  marketEvents: [message, ...prev.marketEvents.slice(0, 99)]
                }))
                break

              case 'recommendation_update':
                setState(prev => ({
                  ...prev,
                  recommendations: {
                    ...prev.recommendations,
                    [message.route_type]: message.recommendations
                  }
                }))
                break

              case 'price_update':
                setState(prev => ({
                  ...prev,
                  priceUpdates: {
                    ...prev.priceUpdates,
                    [message.item_id]: message
                  }
                }))
                break

              case 'pattern_detected':
                setState(prev => ({
                  ...prev,
                  patternDetections: [message, ...prev.patternDetections.slice(0, 49)]
                }))
                break

              case 'volume_surge':
                setState(prev => ({
                  ...prev,
                  volumeSurges: [message, ...prev.volumeSurges.slice(0, 49)]
                }))
                break

              case 'current_recommendations':
                setState(prev => ({
                  ...prev,
                  recommendations: {
                    ...prev.recommendations,
                    [message.route_type]: message.recommendations
                  }
                }))
                break

              case 'market_alerts':
                setState(prev => ({ ...prev, marketAlerts: message.alerts }))
                break

              case 'subscription_confirmed':
                // Reduced logging: only log initial route subscriptions, not every item
                if (message.subscription.startsWith('route_')) {
                  console.log('✅ Route subscription confirmed:', message.subscription)
                }
                break

              case 'unsubscription_confirmed':
                // Reduced logging: only log route unsubscriptions, not every item
                if (message.subscription.startsWith('route_')) {
                  console.log('🔌 Route unsubscription confirmed:', message.subscription)
                }
                break

              case 'unsubscribe_from_item':
                console.log('📤 Backend unsubscribed from item:', message.item_id)
                break

              case 'error':
                console.error('❌ Trading WebSocket error:', message.message)
                setState(prev => ({ ...prev, error: message.message }))
                break

              default:
                console.log('📨 Unknown trading message type:', message)
            }
          } catch (error) {
            console.error('Error parsing trading WebSocket message:', error)
            setState(prev => ({ ...prev, error: 'Failed to parse message' }))
          }
        }

        ws.current.onclose = (event) => {
          console.log(`🔌 Trading WebSocket disconnected: code ${event.code}, reason: ${event.reason || 'None'}`)
          isConnecting.current = false
          setState(prev => ({ 
            ...prev,
            isConnected: false, 
            isConnecting: false 
          }))

          // Only attempt to reconnect for unexpected closures
          if (event.code !== 1000 && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts.current++
            console.log(`🔄 Attempting to reconnect... (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`)
            
            const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttempts.current - 1)
            reconnectTimeout.current = setTimeout(() => {
              // Restart connection with same inline logic
              if (!isConnecting.current && (!ws.current || ws.current.readyState === WebSocket.CLOSED)) {
                initConnection()
              }
            }, Math.min(delay, 30000))
          } else if (event.code !== 1000) {
            console.error('❌ Max reconnection attempts reached')
            setState(prev => ({ ...prev, error: 'Max reconnection attempts reached' }))
          }
        }

        ws.current.onerror = (error) => {
          console.error('❌ Trading WebSocket error occurred:', error)
          isConnecting.current = false
          setState(prev => ({ 
            ...prev,
            error: 'WebSocket connection error',
            isConnecting: false 
          }))
        }
      } catch (error) {
        console.error('Failed to create trading WebSocket:', error)
        isConnecting.current = false
        setState(prev => ({ 
          ...prev,
          error: 'Failed to create WebSocket connection',
          isConnecting: false 
        }))
      }
    }

    initConnection()

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current)
        reconnectTimeout.current = null
      }

      if (ws.current) {
        ws.current.close()
        ws.current = null
      }

      setState(prev => ({ 
        ...prev,
        isConnected: false, 
        isConnecting: false 
      }))
    }
  }, []) // ABSOLUTELY NO DEPENDENCIES - run only once

  return {
    state,
    actions: {
      subscribeToItem,
      unsubscribeFromItem,
      subscribeToRoute,
      unsubscribe,
      getCurrentRecommendations,
      getMarketAlerts,
      clearMessages,
      clearAlerts
    }
  }
}