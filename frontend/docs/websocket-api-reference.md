# 📡 WebSocket API Reference

## 🌐 Connection Details

- **URL**: `ws://localhost:8002/ws/trading/`
- **Protocol**: WebSocket (Django Channels)
- **Backend**: Django Channels with Redis
- **Reconnection**: Automatic with exponential backoff

---

## 📨 Message Types

### Outgoing Messages (Frontend → Backend)

#### 1. Subscribe to Route
```json
{
  "type": "subscribe_to_route",
  "route_type": "high-alchemy"
}
```

#### 2. Subscribe to Item
```json
{
  "type": "subscribe_to_item", 
  "item_id": "554"
}
```

#### 3. Unsubscribe from Item
```json
{
  "type": "unsubscribe_from_item",
  "item_id": "554"
}
```

#### 4. Get Current Recommendations
```json
{
  "type": "get_current_recommendations",
  "route_type": "rune-trading"
}
```

#### 5. Get Market Alerts
```json
{
  "type": "get_market_alerts"
}
```

### Incoming Messages (Backend → Frontend)

#### 1. Connection Established
```json
{
  "type": "connection_established",
  "timestamp": "2025-09-12T19:30:00Z",
  "message": "Connected to trading intelligence stream"
}
```

#### 2. Subscription Confirmed
```json
{
  "type": "subscription_confirmed",
  "subscription": "route_high-alchemy",
  "message": "Successfully subscribed to high-alchemy route"
}
```

#### 3. Price Update
```json
{
  "type": "price_update",
  "item_id": 554,
  "high_price": 125,
  "low_price": 120,
  "high_volume": 1500,
  "low_volume": 1200,
  "timestamp": "2025-09-12T19:30:00Z"
}
```

#### 4. Recommendation Update
```json
{
  "type": "recommendation_update",
  "route_type": "high-alchemy", 
  "update_type": "new_opportunities",
  "recommendations": [
    {
      "item_id": 554,
      "item_name": "Fire rune",
      "profit": 150,
      "confidence": 0.85
    }
  ],
  "timestamp": "2025-09-12T19:30:00Z"
}
```

#### 5. Market Event
```json
{
  "type": "market_event",
  "event_type": "price_spike",
  "item_id": 554,
  "data": {
    "old_price": 120,
    "new_price": 140,
    "change_percent": 16.67
  },
  "timestamp": "2025-09-12T19:30:00Z"
}
```

#### 6. Pattern Detected
```json
{
  "type": "pattern_detected",
  "item_id": 554,
  "pattern_name": "bullish_breakout",
  "confidence": 0.92,
  "predicted_target": 150,
  "timestamp": "2025-09-12T19:30:00Z"
}
```

#### 7. Volume Surge
```json
{
  "type": "volume_surge",
  "item_id": 554,
  "current_volume": 5000,
  "average_volume": 1200,
  "surge_factor": 4.17,
  "timestamp": "2025-09-12T19:30:00Z"
}
```

#### 8. Market Alerts
```json
{
  "type": "market_alerts",
  "alerts": [
    {
      "id": 1,
      "item_id": 554,
      "item_name": "Fire rune",
      "alert_type": "profit_opportunity",
      "priority": "high",
      "message": "High alchemy profit increased by 25%",
      "confidence": 0.88,
      "is_active": true,
      "created_at": "2025-09-12T19:25:00Z"
    }
  ],
  "timestamp": "2025-09-12T19:30:00Z"
}
```

#### 9. Error Message
```json
{
  "type": "error",
  "message": "Invalid route type: invalid-route"
}
```

---

## 🎯 Available Routes

| Route | Description | Use Case |
|-------|-------------|----------|
| `high-alchemy` | High alchemy opportunities | Items profitable for alching |
| `rune-trading` | Rune crafting and trading | Essence → Rune profit calculations |
| `flipping` | Item flipping opportunities | Buy low, sell high opportunities |
| `decanting` | Potion decanting strategies | Dose combination profits |
| `crafting` | Crafting profit opportunities | Raw materials → Finished goods |
| `set-combining` | Set combining strategies | Individual pieces → Complete sets |

---

## 🔧 TypeScript Interfaces

### Message Types
```tsx
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
```

### Socket State
```tsx
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
```

### Socket Actions
```tsx
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
```

---

## 🔄 Connection Lifecycle

### 1. Initial Connection
```
Frontend → ws://localhost:8002/ws/trading/
Backend  → {"type": "connection_established", "message": "Connected..."}
```

### 2. Route Subscription
```
Frontend → {"type": "subscribe_to_route", "route_type": "high-alchemy"}
Backend  → {"type": "subscription_confirmed", "subscription": "route_high-alchemy"}
```

### 3. Item Subscription
```
Frontend → {"type": "subscribe_to_item", "item_id": "554"}
Backend  → {"type": "subscription_confirmed", "subscription": "item_554"}
```

### 4. Real-Time Updates
```
Backend → {"type": "price_update", "item_id": 554, "high_price": 125, ...}
Backend → {"type": "recommendation_update", "route_type": "high-alchemy", ...}
Backend → {"type": "market_event", "event_type": "price_spike", ...}
```

### 5. Disconnection & Reconnection
```
Connection Lost → Automatic reconnection with exponential backoff
Reconnected    → Re-subscribe to all previous subscriptions
```

---

## ⚙️ Configuration

### Rate Limiting
- **Subscription Rate**: 1000ms minimum between subscription attempts
- **Message Rate**: No client-side limiting (server handles)
- **Reconnection**: Exponential backoff starting at 3000ms

### Subscription Management
- **Reference Counting**: Prevents duplicate subscriptions
- **Automatic Cleanup**: Unsubscribes on component unmount
- **Batch Operations**: Groups multiple item subscriptions

### Error Handling
- **Connection Errors**: Automatic retry with backoff
- **Invalid Messages**: Error response with details
- **Rate Limiting**: Queue messages if connection busy

---

## 🛠️ Backend Integration

### Django Channels Consumer
Located at: `backend/apps/realtime/consumers.py`

### Supported Commands
- `subscribe_to_route` - Subscribe to trading route updates
- `subscribe_to_item` - Subscribe to specific item price updates  
- `unsubscribe_from_item` - Unsubscribe from item updates
- `get_current_recommendations` - Get current data snapshot
- `get_market_alerts` - Get active market alerts

### Data Sources
- **OSRS Wiki API**: Real-time price data
- **Trading Strategies**: AI-generated recommendations
- **Pattern Detection**: Technical analysis signals
- **Volume Analysis**: Market activity monitoring

---

## 🔍 Debugging

### Client-Side Logging
```tsx
// Enable detailed logging in useReactiveTradingSocket.ts
console.log('📡 Subscribing to route:', routeType);
console.log('✅ Route subscription confirmed:', subscription);
console.log('📊 Price update received:', priceUpdate);
```

### Network Debugging
```bash
# Check WebSocket connection
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" \
  http://localhost:8002/ws/trading/
```

### Backend Logs
```bash
# Monitor Django Channels logs
cd backend && python manage.py runserver --log-level=DEBUG
```

---

## 📈 Performance

### Optimization Features
- **Connection Pooling**: Single connection per application
- **Message Batching**: Group related updates
- **Selective Updates**: Only send changed data
- **Compression**: WebSocket compression enabled

### Monitoring
- **Connection Status**: Real-time connection state
- **Message Latency**: Track message round-trip time  
- **Subscription Health**: Monitor active subscriptions
- **Error Rates**: Track connection failures

---

## 🎯 Usage Examples

### Basic Route Subscription
```tsx
const { state, actions } = useReactiveTradingContext();

useEffect(() => {
  if (state.isConnected) {
    actions.subscribeToRoute('high-alchemy');
  }
}, [state.isConnected]);
```

### Item Price Monitoring
```tsx
useEffect(() => {
  if (state.isConnected && itemIds.length > 0) {
    itemIds.forEach(id => actions.subscribeToItem(id.toString()));
  }
}, [state.isConnected, itemIds.join(',')]);
```

### Real-Time Data Updates
```tsx
useEffect(() => {
  const priceUpdates = Object.values(state.priceUpdates || {});
  if (priceUpdates.length > 0) {
    // Handle price updates
    updateItemPrices(priceUpdates);
  }
}, [state.priceUpdates]);
```