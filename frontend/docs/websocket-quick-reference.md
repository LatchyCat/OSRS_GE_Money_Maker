# ⚡ WebSocket Quick Reference

## 🚀 5-Minute Setup

### 1. Import & Setup
```tsx
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';

const YourView = () => {
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  const [websocketError, setWebsocketError] = useState<string | null>(null);
```

### 2. Subscribe to Route
```tsx
useEffect(() => {
  if (!socketState?.isConnected || !socketActions) return;
  
  socketActions.subscribeToRoute('your-route-name'); // ⚠️ Replace with your route
  socketActions.getCurrentRecommendations('your-route-name');
  socketActions.getMarketAlerts();
}, [socketState?.isConnected]); // ✅ Only socketState?.isConnected!
```

### 3. Handle Price Updates
```tsx
const priceUpdates = useMemo(() => Object.values(socketState?.priceUpdates || {}), [socketState?.priceUpdates]);

useEffect(() => {
  if (priceUpdates.length === 0) return;
  // Update your data state here
}, [priceUpdates]);
```

---

## 🎯 Available Routes

| Route | Description |
|-------|-------------|
| `'high-alchemy'` | High alchemy opportunities |
| `'rune-trading'` | Rune crafting and trading |
| `'flipping'` | Item flipping opportunities |
| `'decanting'` | Potion decanting strategies |
| `'crafting'` | Crafting profit opportunities |
| `'set-combining'` | Set combining strategies |

---

## ⚠️ Common Pitfalls

### ❌ NEVER DO THIS:
```tsx
// Causes infinite loops!
useEffect(() => {
  socketActions.subscribeToRoute('route');
}, [socketState?.isConnected, socketActions]); // ❌ socketActions in deps!
```

### ✅ ALWAYS DO THIS:
```tsx
// Stable and safe
useEffect(() => {
  if (!socketState?.isConnected || !socketActions) return;
  socketActions.subscribeToRoute('route');
}, [socketState?.isConnected]); // ✅ Only stable references
```

---

## 🔧 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Infinite loop logs | Remove `socketActions` from useEffect deps |
| Connection failed | Check backend on port 8002: `lsof -i :8002` |
| CORS errors | Add your port to Django CORS_ALLOWED_ORIGINS |
| No price updates | Subscribe to items: `subscribeToItem(itemId.toString())` |

---

## 📋 Cheat Sheet

### Essential Imports:
```tsx
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import type { PriceUpdate } from '../hooks/useReactiveTradingSocket';
```

### Connection Status UI:
```tsx
<div className={`w-2 h-2 rounded-full ${socketState?.isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
<span>WebSocket: {socketState?.isConnected ? 'Connected' : 'Disconnected'}</span>
```

### Item Subscription Pattern:
```tsx
const stableSubscribeToItem = useCallback(
  (itemId: string) => socketActions?.subscribeToItem?.(itemId),
  [socketActions?.subscribeToItem]
);

useEffect(() => {
  if (!socketState?.isConnected) return;
  itemIds.forEach(id => stableSubscribeToItem(id.toString()));
}, [socketState?.isConnected, itemIds.join(','), stableSubscribeToItem]);
```

---

## 🏁 Complete Minimal Example

```tsx
import React, { useState, useEffect, useMemo } from 'react';
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';

const MinimalWebSocketView = () => {
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  const [data, setData] = useState([]);

  // Subscribe to route
  useEffect(() => {
    if (!socketState?.isConnected || !socketActions) return;
    socketActions.subscribeToRoute('your-route');
  }, [socketState?.isConnected]);

  // Handle updates
  const priceUpdates = useMemo(() => 
    Object.values(socketState?.priceUpdates || {}), 
    [socketState?.priceUpdates]
  );

  useEffect(() => {
    if (priceUpdates.length === 0) return;
    // Update your data
  }, [priceUpdates]);

  return (
    <div>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          socketState?.isConnected ? 'bg-green-400' : 'bg-red-400'
        }`} />
        <span>WebSocket: {socketState?.isConnected ? 'Connected' : 'Disconnected'}</span>
      </div>
      {/* Your content */}
    </div>
  );
};
```

---

💡 **Need more details?** See the full `WEBSOCKET_SETUP_GUIDE.md` for comprehensive documentation.