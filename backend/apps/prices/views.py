from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import random
import json
import math
import logging
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Create your views here.

def historical_price_data(request, item_id):
    """
    Enhanced historical price data endpoint with realistic mock data.
    Supports different timeframes and generates market-realistic price movements.
    """
    try:
        timeframe = request.GET.get('timeframe', '5m')
        limit = min(int(request.GET.get('limit', 50)), 200)
        
        # Generate realistic base price based on item_id
        base_price = 1000 + (item_id % 10000)
        
        # Enhanced timeframe configurations
        timeframe_config = {
            '1m': {'minutes': 1, 'volatility': 0.005, 'trend_strength': 0.0001},
            '5m': {'minutes': 5, 'volatility': 0.02, 'trend_strength': 0.001},
            '15m': {'minutes': 15, 'volatility': 0.03, 'trend_strength': 0.002},
            '1h': {'minutes': 60, 'volatility': 0.05, 'trend_strength': 0.003},
            '4h': {'minutes': 240, 'volatility': 0.08, 'trend_strength': 0.005},
            '24h': {'minutes': 1440, 'volatility': 0.15, 'trend_strength': 0.01},
            '7d': {'minutes': 10080, 'volatility': 0.25, 'trend_strength': 0.02}
        }
        
        config = timeframe_config.get(timeframe, timeframe_config['5m'])
        
        now = timezone.now()
        data_points = []
        
        # Generate more realistic market data
        price = base_price
        trend = random.uniform(-0.02, 0.02)  # Overall trend
        
        # Market cycle effects (simulate daily/weekly patterns)
        cycle_factor = 0.1 if timeframe in ['1m', '5m', '15m'] else 0.05
        
        for i in range(limit):
            # Time goes backwards from now
            timestamp = now - timedelta(minutes=config['minutes'] * (limit - i))
            
            # Market hours effect (higher volatility during peak hours)
            hour = timestamp.hour
            market_activity = 1.0
            if timeframe in ['1m', '5m', '15m', '1h']:
                if 14 <= hour <= 22:  # Peak trading hours (UTC)
                    market_activity = 1.3
                elif 2 <= hour <= 10:  # Low activity hours
                    market_activity = 0.7
            
            # Market volatility with mean reversion and cycles
            volatility_factor = config['volatility'] * market_activity
            
            # Add market cycle patterns
            cycle_phase = (i / limit) * 2 * math.pi  # Full cycle over the data range
            cycle_influence = math.sin(cycle_phase) * cycle_factor
            
            # Price movement calculation
            price_change = random.normalvariate(
                (trend + cycle_influence) * config['trend_strength'], 
                volatility_factor
            )
            
            price = max(10, price * (1 + price_change))  # Ensure price stays reasonable
            
            # Add some mean reversion to prevent extreme values
            if price > base_price * 1.8:
                trend -= 0.01
            elif price < base_price * 0.3:
                trend += 0.01
            
            # Generate volume with more realistic patterns
            base_volume = 500 + (item_id % 1000)
            
            # Volume correlation with price movement
            volume_multiplier = 1 + abs(price_change) * 10  # More volume on big moves
            volume_multiplier *= market_activity  # Higher volume during active hours
            
            # Random volume variance
            volume_variance = random.uniform(0.4, 2.0)
            high_volume = int(base_volume * volume_multiplier * volume_variance)
            low_volume = int(base_volume * volume_multiplier * volume_variance * 0.75)
            
            # Create realistic high/low spread
            spread_percent = random.uniform(0.005, 0.03)  # 0.5-3% spread
            if timeframe in ['1m', '5m']:
                spread_percent *= 0.5  # Tighter spreads on short timeframes
            
            spread = price * spread_percent
            high_price = int(price + spread * random.uniform(0.5, 1.5))
            low_price = max(1, int(price - spread * random.uniform(0.5, 1.5)))
            
            # Ensure high > low
            if high_price <= low_price:
                high_price = low_price + max(1, int(price * 0.01))
            
            data_points.append({
                'timestamp': timestamp.isoformat(),
                'high_price': high_price,
                'low_price': low_price,
                'high_volume': high_volume,
                'low_volume': low_volume,
            })
        
        # Sort by timestamp (oldest first)
        data_points.sort(key=lambda x: x['timestamp'])
        
        return JsonResponse(data_points, safe=False)
        
    except Exception as e:
        logger.error(f"Historical price data error for item {item_id}: {str(e)}")
        return JsonResponse({
            'error': 'Unable to fetch historical data',
            'message': 'Using fallback data generation'
        }, status=500)

def price_api_health(request):
    """Health check endpoint for price API."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'price-api',
        'timestamp': timezone.now().isoformat()
    })
