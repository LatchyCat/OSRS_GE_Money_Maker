"""
Seasonal Pattern Recognition and Forecasting Engine for OSRS Trading Terminal

Identifies and forecasts seasonal patterns in OSRS market data, optimized for MacBook M1 8GB RAM.
Uses efficient statistical methods to detect recurring patterns without heavy ML training.

Features:
- OSRS-specific seasonal patterns (Double XP weekends, holidays, updates)
- Statistical pattern detection using FFT and autocorrelation
- Day-of-week, hour-of-day, and monthly patterns
- Holiday and event impact analysis
- Forecast generation with confidence intervals
- Pattern strength scoring and trend analysis
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models import Avg, Count, Q, StdDev
from asgiref.sync import sync_to_async
from scipy import stats
from scipy.signal import find_peaks, periodogram
import calendar

logger = logging.getLogger(__name__)


class SeasonalAnalysisEngine:
    """
    Seasonal pattern recognition and forecasting engine optimized for OSRS market data.
    """
    
    def __init__(self):
        # OSRS-specific seasonal events and their typical durations
        self.osrs_events = {
            'double_xp_weekend': {
                'frequency': 'quarterly',  # ~4 times per year
                'duration_days': 3,
                'impact_categories': ['combat', 'skilling', 'supplies'],
                'price_impact': {'combat': 1.2, 'skilling': 1.5, 'supplies': 0.8}
            },
            'christmas_event': {
                'frequency': 'yearly',
                'duration_days': 14,
                'typical_dates': [(12, 15), (12, 30)],  # (month, day) ranges
                'impact_categories': ['cosmetic', 'food', 'rare'],
                'price_impact': {'cosmetic': 0.7, 'food': 1.1, 'rare': 1.3}
            },
            'halloween_event': {
                'frequency': 'yearly',
                'duration_days': 14,
                'typical_dates': [(10, 20), (11, 5)],
                'impact_categories': ['cosmetic', 'rare'],
                'price_impact': {'cosmetic': 0.6, 'rare': 1.4}
            },
            'summer_event': {
                'frequency': 'yearly',
                'duration_days': 14,
                'typical_dates': [(7, 1), (8, 15)],
                'impact_categories': ['cosmetic', 'skilling'],
                'price_impact': {'cosmetic': 0.8, 'skilling': 1.2}
            },
            'deadman_mode': {
                'frequency': 'biannual',  # ~2 times per year
                'duration_days': 30,
                'impact_categories': ['combat', 'supplies', 'food'],
                'price_impact': {'combat': 1.3, 'supplies': 1.1, 'food': 1.2}
            },
            'leagues': {
                'frequency': 'yearly',
                'duration_days': 60,
                'impact_categories': ['all'],  # Affects everything
                'price_impact': {'all': 0.9}  # Generally decreases main game activity
            }
        }
        
        # Weekly patterns (RuneScape players' behavior)
        self.weekly_patterns = {
            'weekend_effect': {
                'days': [5, 6],  # Saturday, Sunday (0=Monday)
                'expected_volume_multiplier': 1.3,
                'expected_volatility_multiplier': 1.1
            },
            'monday_effect': {
                'days': [0],  # Monday
                'expected_volume_multiplier': 1.1,
                'description': 'Post-weekend trading catch-up'
            },
            'friday_effect': {
                'days': [4],  # Friday
                'expected_volume_multiplier': 0.9,
                'description': 'Lower activity before weekend'
            }
        }
        
        # Daily time patterns (UTC based, typical OSRS peak times)
        self.daily_patterns = {
            'eu_peak': {
                'hours': [18, 19, 20, 21],  # 6-9 PM UTC (EU evening)
                'expected_volume_multiplier': 1.4
            },
            'us_peak': {
                'hours': [23, 0, 1, 2],  # 11 PM - 2 AM UTC (US evening)
                'expected_volume_multiplier': 1.3
            },
            'off_peak': {
                'hours': [6, 7, 8, 9, 10],  # Morning UTC (low activity)
                'expected_volume_multiplier': 0.7
            }
        }
        
        # Pattern detection parameters
        self.pattern_params = {
            'min_data_points': 100,
            'seasonal_window_days': 365,  # Look back 1 year for seasonal patterns
            'trend_window_days': 90,      # 3 months for trend analysis
            'confidence_threshold': 0.6,
            'pattern_strength_threshold': 0.3,
        }
    
    async def analyze_seasonal_patterns(
        self,
        item_id: int,
        analysis_types: List[str] = None,
        lookback_days: int = 365
    ) -> Dict[str, Any]:
        """
        Comprehensive seasonal pattern analysis for an item.
        """
        try:
            analysis_types = analysis_types or ['weekly', 'monthly', 'yearly', 'events', 'forecasting']
            
            # Get historical data
            price_data = await self._get_seasonal_data(item_id, lookback_days)
            
            if price_data.empty:
                return {'error': f'Insufficient data for seasonal analysis of item {item_id}'}
            
            # Prepare analysis results
            analysis_results = {
                'item_id': item_id,
                'analysis_timestamp': timezone.now(),
                'lookback_days': lookback_days,
                'data_points': len(price_data),
                'patterns': {},
                'forecasts': {},
                'strength_scores': {},
                'recommendations': []
            }
            
            # Analyze different pattern types
            for analysis_type in analysis_types:
                if analysis_type == 'weekly':
                    analysis_results['patterns']['weekly'] = await self._analyze_weekly_patterns(price_data)
                elif analysis_type == 'monthly':
                    analysis_results['patterns']['monthly'] = await self._analyze_monthly_patterns(price_data)
                elif analysis_type == 'yearly':
                    analysis_results['patterns']['yearly'] = await self._analyze_yearly_patterns(price_data)
                elif analysis_type == 'events':
                    analysis_results['patterns']['events'] = await self._analyze_event_patterns(price_data, item_id)
                elif analysis_type == 'forecasting':
                    analysis_results['forecasts'] = await self._generate_seasonal_forecasts(price_data)
            
            # Calculate overall pattern strengths
            analysis_results['strength_scores'] = await self._calculate_pattern_strengths(analysis_results['patterns'])
            
            # Generate recommendations
            analysis_results['recommendations'] = await self._generate_seasonal_recommendations(
                analysis_results, item_id
            )
            
            return analysis_results
            
        except Exception as e:
            logger.exception(f"Seasonal analysis failed for item {item_id}")
            return {'error': str(e)}
    
    async def _get_seasonal_data(self, item_id: int, lookback_days: int) -> pd.DataFrame:
        """Get historical price and volume data for seasonal analysis."""
        try:
            from apps.prices.models import Price
            
            cutoff_date = timezone.now() - timedelta(days=lookback_days)
            
            prices = await sync_to_async(list)(
                Price.objects.filter(
                    item_id=item_id,
                    created_at__gte=cutoff_date
                ).order_by('created_at').values(
                    'created_at', 'high_price', 'low_price', 'volume'
                )
            )
            
            if not prices:
                return pd.DataFrame()
            
            # Convert to DataFrame with comprehensive datetime features
            df = pd.DataFrame(prices)
            df['timestamp'] = pd.to_datetime(df['created_at'])
            df['price'] = df['high_price']
            df['volume'] = df['volume'].fillna(0)
            
            # Add datetime features for pattern analysis
            df['year'] = df['timestamp'].dt.year
            df['month'] = df['timestamp'].dt.month
            df['day'] = df['timestamp'].dt.day
            df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_year'] = df['timestamp'].dt.dayofyear
            df['week_of_year'] = df['timestamp'].dt.isocalendar().week
            df['quarter'] = df['timestamp'].dt.quarter
            
            # Calculate returns and volatility
            df['price_return'] = df['price'].pct_change()
            df['log_return'] = np.log(df['price'] / df['price'].shift(1))
            df['volatility'] = df['price_return'].rolling(window=7).std()
            
            return df.set_index('timestamp').sort_index()
            
        except Exception as e:
            logger.exception(f"Failed to get seasonal data for item {item_id}")
            return pd.DataFrame()
    
    async def _analyze_weekly_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze weekly seasonal patterns."""
        try:
            if len(data) < 14:  # Need at least 2 weeks
                return {'error': 'Insufficient data for weekly analysis'}
            
            weekly_analysis = {
                'day_of_week_effects': {},
                'weekend_effect': {},
                'statistical_significance': {},
                'pattern_strength': 0
            }
            
            # Analyze day-of-week effects
            dow_stats = data.groupby('day_of_week').agg({
                'price': ['mean', 'std', 'count'],
                'volume': ['mean', 'std'],
                'price_return': ['mean', 'std'],
                'volatility': ['mean']
            }).round(4)
            
            # Calculate day-of-week price effects
            overall_mean_price = data['price'].mean()
            for day in range(7):
                day_name = calendar.day_name[day]
                day_data = data[data['day_of_week'] == day]
                
                if len(day_data) > 0:
                    day_mean_price = day_data['price'].mean()
                    price_effect = (day_mean_price / overall_mean_price - 1) * 100
                    
                    volume_mean = day_data['volume'].mean()
                    overall_volume_mean = data['volume'].mean()
                    volume_effect = (volume_mean / overall_volume_mean - 1) * 100 if overall_volume_mean > 0 else 0
                    
                    weekly_analysis['day_of_week_effects'][day_name] = {
                        'price_effect_pct': price_effect,
                        'volume_effect_pct': volume_effect,
                        'avg_return': day_data['price_return'].mean() * 100 if not day_data['price_return'].isna().all() else 0,
                        'volatility': day_data['volatility'].mean() if not day_data['volatility'].isna().all() else 0,
                        'sample_size': len(day_data)
                    }
            
            # Weekend effect analysis
            weekend_data = data[data['day_of_week'].isin([5, 6])]  # Saturday, Sunday
            weekday_data = data[data['day_of_week'].isin([0, 1, 2, 3, 4])]  # Monday-Friday
            
            if len(weekend_data) > 0 and len(weekday_data) > 0:
                weekend_price = weekend_data['price'].mean()
                weekday_price = weekday_data['price'].mean()
                weekend_volume = weekend_data['volume'].mean()
                weekday_volume = weekday_data['volume'].mean()
                
                weekly_analysis['weekend_effect'] = {
                    'price_premium_pct': (weekend_price / weekday_price - 1) * 100,
                    'volume_difference_pct': (weekend_volume / weekday_volume - 1) * 100 if weekday_volume > 0 else 0,
                    'weekend_volatility': weekend_data['volatility'].mean() if not weekend_data['volatility'].isna().all() else 0,
                    'weekday_volatility': weekday_data['volatility'].mean() if not weekday_data['volatility'].isna().all() else 0
                }
                
                # Statistical significance test
                weekend_prices = weekend_data['price'].dropna()
                weekday_prices = weekday_data['price'].dropna()
                
                if len(weekend_prices) > 10 and len(weekday_prices) > 10:
                    t_stat, p_value = stats.ttest_ind(weekend_prices, weekday_prices)
                    weekly_analysis['statistical_significance']['weekend_vs_weekday'] = {
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'significant': p_value < 0.05
                    }
            
            # Calculate overall weekly pattern strength
            day_effects = [abs(effect['price_effect_pct']) for effect in weekly_analysis['day_of_week_effects'].values()]
            weekly_analysis['pattern_strength'] = np.mean(day_effects) / 100 if day_effects else 0
            
            return weekly_analysis
            
        except Exception as e:
            logger.exception("Failed to analyze weekly patterns")
            return {'error': str(e)}
    
    async def _analyze_monthly_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze monthly seasonal patterns."""
        try:
            if len(data) < 60:  # Need at least 2 months
                return {'error': 'Insufficient data for monthly analysis'}
            
            monthly_analysis = {
                'month_effects': {},
                'quarterly_effects': {},
                'month_end_effects': {},
                'pattern_strength': 0
            }
            
            # Monthly effects
            overall_mean_price = data['price'].mean()
            
            for month in range(1, 13):
                month_name = calendar.month_name[month]
                month_data = data[data['month'] == month]
                
                if len(month_data) > 0:
                    month_mean_price = month_data['price'].mean()
                    price_effect = (month_mean_price / overall_mean_price - 1) * 100
                    
                    volume_mean = month_data['volume'].mean()
                    overall_volume_mean = data['volume'].mean()
                    volume_effect = (volume_mean / overall_volume_mean - 1) * 100 if overall_volume_mean > 0 else 0
                    
                    monthly_analysis['month_effects'][month_name] = {
                        'price_effect_pct': price_effect,
                        'volume_effect_pct': volume_effect,
                        'avg_return': month_data['price_return'].mean() * 100 if not month_data['price_return'].isna().all() else 0,
                        'sample_size': len(month_data)
                    }
            
            # Quarterly effects
            for quarter in range(1, 5):
                quarter_data = data[data['quarter'] == quarter]
                
                if len(quarter_data) > 0:
                    quarter_mean_price = quarter_data['price'].mean()
                    price_effect = (quarter_mean_price / overall_mean_price - 1) * 100
                    
                    monthly_analysis['quarterly_effects'][f'Q{quarter}'] = {
                        'price_effect_pct': price_effect,
                        'volume_effect_pct': (quarter_data['volume'].mean() / overall_mean_price - 1) * 100,
                        'sample_size': len(quarter_data)
                    }
            
            # Month-end effects (last 5 days vs first 5 days)
            data['is_month_start'] = data['day'] <= 5
            data['is_month_end'] = data['day'] >= 25
            
            month_start_data = data[data['is_month_start']]
            month_end_data = data[data['is_month_end']]
            
            if len(month_start_data) > 0 and len(month_end_data) > 0:
                start_price = month_start_data['price'].mean()
                end_price = month_end_data['price'].mean()
                
                monthly_analysis['month_end_effects'] = {
                    'end_vs_start_price_pct': (end_price / start_price - 1) * 100,
                    'end_volume_vs_start_pct': (
                        month_end_data['volume'].mean() / month_start_data['volume'].mean() - 1
                    ) * 100 if month_start_data['volume'].mean() > 0 else 0
                }
            
            # Calculate monthly pattern strength
            month_effects = [abs(effect['price_effect_pct']) for effect in monthly_analysis['month_effects'].values()]
            monthly_analysis['pattern_strength'] = np.mean(month_effects) / 100 if month_effects else 0
            
            return monthly_analysis
            
        except Exception as e:
            logger.exception("Failed to analyze monthly patterns")
            return {'error': str(e)}
    
    async def _analyze_yearly_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze yearly seasonal patterns using spectral analysis."""
        try:
            if len(data) < 200:  # Need substantial data for yearly analysis
                return {'error': 'Insufficient data for yearly analysis'}
            
            yearly_analysis = {
                'seasonal_decomposition': {},
                'dominant_frequencies': [],
                'cyclical_patterns': {},
                'pattern_strength': 0
            }
            
            # Prepare time series data
            price_series = data['price'].dropna()
            
            if len(price_series) < 100:
                return {'error': 'Insufficient clean price data'}
            
            # Simple seasonal decomposition using moving averages
            # Trend component (30-day moving average)
            trend = price_series.rolling(window=30, center=True).mean()
            
            # Detrended series
            detrended = price_series - trend
            detrended = detrended.dropna()
            
            # Seasonal component (using day-of-year averages)
            seasonal_component = data.groupby('day_of_year')['price'].mean()
            
            # Find dominant frequencies using periodogram
            if len(detrended) > 50:
                frequencies, power = periodogram(detrended.values, fs=1.0)  # Assuming daily data
                
                # Find peaks in the power spectrum
                peaks, properties = find_peaks(power, height=np.percentile(power, 80))
                
                # Convert to periods (days)
                dominant_periods = []
                for peak in peaks[:5]:  # Top 5 peaks
                    if frequencies[peak] > 0:
                        period_days = 1.0 / frequencies[peak]
                        if 7 <= period_days <= 400:  # Reasonable range for OSRS patterns
                            dominant_periods.append({
                                'period_days': period_days,
                                'power': power[peak],
                                'interpretation': self._interpret_period(period_days)
                            })
                
                yearly_analysis['dominant_frequencies'] = sorted(
                    dominant_periods, key=lambda x: x['power'], reverse=True
                )
            
            # Analyze year-over-year patterns if we have multiple years
            unique_years = data['year'].unique()
            if len(unique_years) > 1:
                yearly_patterns = {}
                for year in sorted(unique_years):
                    year_data = data[data['year'] == year]
                    if len(year_data) > 50:  # Minimum data for meaningful analysis
                        yearly_patterns[year] = {
                            'mean_price': year_data['price'].mean(),
                            'std_price': year_data['price'].std(),
                            'mean_volume': year_data['volume'].mean(),
                            'total_return': (
                                year_data['price'].iloc[-1] / year_data['price'].iloc[0] - 1
                            ) * 100 if len(year_data) > 1 else 0
                        }
                
                yearly_analysis['yearly_patterns'] = yearly_patterns
            
            # Calculate pattern strength based on seasonal variance
            if len(seasonal_component) > 0:
                seasonal_cv = seasonal_component.std() / seasonal_component.mean()
                yearly_analysis['pattern_strength'] = min(seasonal_cv, 1.0)  # Cap at 1.0
            
            return yearly_analysis
            
        except Exception as e:
            logger.exception("Failed to analyze yearly patterns")
            return {'error': str(e)}
    
    def _interpret_period(self, period_days: float) -> str:
        """Interpret the meaning of a detected period."""
        if 6 <= period_days <= 8:
            return "Weekly cycle"
        elif 13 <= period_days <= 16:
            return "Bi-weekly cycle"
        elif 28 <= period_days <= 32:
            return "Monthly cycle"
        elif 60 <= period_days <= 95:
            return "Quarterly cycle"
        elif 350 <= period_days <= 380:
            return "Annual cycle"
        else:
            return f"Custom cycle ({period_days:.1f} days)"
    
    async def _analyze_event_patterns(self, data: pd.DataFrame, item_id: int) -> Dict[str, Any]:
        """Analyze patterns around OSRS events."""
        try:
            event_analysis = {
                'detected_events': [],
                'event_impact_analysis': {},
                'upcoming_event_predictions': []
            }
            
            # Get item category to determine which events are relevant
            item_category = await self._get_item_category(item_id)
            
            # Analyze impact around known OSRS events
            for event_name, event_info in self.osrs_events.items():
                if self._is_event_relevant(item_category, event_info):
                    event_impact = await self._analyze_single_event_impact(data, event_name, event_info)
                    if event_impact:
                        event_analysis['event_impact_analysis'][event_name] = event_impact
            
            # Detect unusual activity periods that might be events
            unusual_periods = await self._detect_unusual_activity(data)
            event_analysis['detected_events'] = unusual_periods
            
            # Predict upcoming event impacts
            upcoming_predictions = await self._predict_upcoming_events(item_category)
            event_analysis['upcoming_event_predictions'] = upcoming_predictions
            
            return event_analysis
            
        except Exception as e:
            logger.exception("Failed to analyze event patterns")
            return {'error': str(e)}
    
    async def _get_item_category(self, item_id: int) -> str:
        """Get item category for event relevance analysis."""
        try:
            # This would normally query your items database for category
            # For now, using a simple heuristic based on item_id ranges
            # You'd want to implement proper category lookup here
            
            if 10000 <= item_id <= 15000:
                return 'combat'
            elif 15000 <= item_id <= 20000:
                return 'skilling'
            elif 20000 <= item_id <= 25000:
                return 'food'
            else:
                return 'misc'
                
        except Exception:
            return 'unknown'
    
    def _is_event_relevant(self, item_category: str, event_info: Dict) -> bool:
        """Check if an event is relevant for the item category."""
        impact_categories = event_info.get('impact_categories', [])
        return 'all' in impact_categories or item_category in impact_categories
    
    async def _analyze_single_event_impact(
        self, 
        data: pd.DataFrame, 
        event_name: str, 
        event_info: Dict
    ) -> Optional[Dict[str, Any]]:
        """Analyze the impact of a single event type."""
        try:
            # For this implementation, we'll use date heuristics
            # In a real system, you'd have an events database
            
            impact_analysis = {
                'average_price_impact': 0,
                'average_volume_impact': 0,
                'duration_days': event_info.get('duration_days', 7),
                'confidence': 0.5,
                'sample_events': 0
            }
            
            # Detect potential event periods based on unusual activity
            volume_threshold = data['volume'].quantile(0.8)  # Top 20% volume days
            price_change_threshold = data['price_return'].abs().quantile(0.8)  # Top 20% price changes
            
            # Find periods with both high volume and high price volatility
            event_candidates = data[
                (data['volume'] > volume_threshold) & 
                (data['price_return'].abs() > price_change_threshold)
            ]
            
            if len(event_candidates) > 5:  # Need minimum events for analysis
                # Calculate average impact during these periods
                normal_periods = data[
                    (data['volume'] <= volume_threshold) & 
                    (data['price_return'].abs() <= price_change_threshold)
                ]
                
                if len(normal_periods) > 0:
                    event_avg_price = event_candidates['price'].mean()
                    normal_avg_price = normal_periods['price'].mean()
                    price_impact = (event_avg_price / normal_avg_price - 1) * 100
                    
                    event_avg_volume = event_candidates['volume'].mean()
                    normal_avg_volume = normal_periods['volume'].mean()
                    volume_impact = (event_avg_volume / normal_avg_volume - 1) * 100 if normal_avg_volume > 0 else 0
                    
                    impact_analysis.update({
                        'average_price_impact': price_impact,
                        'average_volume_impact': volume_impact,
                        'sample_events': len(event_candidates),
                        'confidence': min(len(event_candidates) / 20, 0.9)  # Higher confidence with more samples
                    })
            
            return impact_analysis if impact_analysis['sample_events'] > 0 else None
            
        except Exception as e:
            logger.exception(f"Failed to analyze event {event_name}")
            return None
    
    async def _detect_unusual_activity(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect unusual activity periods that might indicate events."""
        try:
            unusual_periods = []
            
            # Calculate rolling statistics
            data['volume_zscore'] = (data['volume'] - data['volume'].rolling(30).mean()) / data['volume'].rolling(30).std()
            data['price_change_zscore'] = (data['price_return'].abs() - data['price_return'].abs().rolling(30).mean()) / data['price_return'].abs().rolling(30).std()
            
            # Find periods with unusual activity (z-score > 2)
            unusual_mask = (data['volume_zscore'].abs() > 2) | (data['price_change_zscore'].abs() > 2)
            unusual_data = data[unusual_mask]
            
            # Group consecutive unusual days
            if len(unusual_data) > 0:
                unusual_dates = unusual_data.index.date
                current_period = []
                
                for i, date in enumerate(unusual_dates):
                    if not current_period:
                        current_period = [date]
                    elif (date - current_period[-1]).days <= 3:  # Within 3 days
                        current_period.append(date)
                    else:
                        # End current period, start new one
                        if len(current_period) >= 2:  # Minimum 2 days for event
                            period_data = unusual_data[unusual_data.index.date.isin(current_period)]
                            unusual_periods.append({
                                'start_date': str(current_period[0]),
                                'end_date': str(current_period[-1]),
                                'duration_days': len(current_period),
                                'avg_volume_increase': period_data['volume_zscore'].mean(),
                                'avg_price_volatility': period_data['price_change_zscore'].mean(),
                                'max_price_change': period_data['price_return'].abs().max() * 100
                            })
                        current_period = [date]
                
                # Don't forget the last period
                if len(current_period) >= 2:
                    period_data = unusual_data[unusual_data.index.date.isin(current_period)]
                    unusual_periods.append({
                        'start_date': str(current_period[0]),
                        'end_date': str(current_period[-1]),
                        'duration_days': len(current_period),
                        'avg_volume_increase': period_data['volume_zscore'].mean(),
                        'avg_price_volatility': period_data['price_change_zscore'].mean(),
                        'max_price_change': period_data['price_return'].abs().max() * 100
                    })
            
            return unusual_periods
            
        except Exception as e:
            logger.exception("Failed to detect unusual activity periods")
            return []
    
    async def _predict_upcoming_events(self, item_category: str) -> List[Dict[str, Any]]:
        """Predict upcoming event impacts based on calendar and historical patterns."""
        try:
            upcoming_predictions = []
            current_date = timezone.now().date()
            
            # Check for upcoming known events
            for event_name, event_info in self.osrs_events.items():
                if self._is_event_relevant(item_category, event_info):
                    # Predict next occurrence based on frequency
                    if event_info['frequency'] == 'quarterly':
                        # Assume next event is within next 90 days
                        predicted_date = current_date + timedelta(days=np.random.randint(30, 90))
                    elif event_info['frequency'] == 'yearly':
                        # Check if we're approaching typical dates
                        typical_dates = event_info.get('typical_dates')
                        if typical_dates:
                            for month, day in typical_dates:
                                event_date = date(current_date.year, month, day)
                                if event_date < current_date:
                                    event_date = date(current_date.year + 1, month, day)
                                
                                days_until = (event_date - current_date).days
                                if days_until <= 60:  # Within next 60 days
                                    predicted_impact = event_info['price_impact'].get(item_category, 1.0)
                                    
                                    upcoming_predictions.append({
                                        'event_name': event_name,
                                        'predicted_date': str(event_date),
                                        'days_until': days_until,
                                        'predicted_price_impact': (predicted_impact - 1) * 100,
                                        'confidence': 0.7,
                                        'preparation_recommendation': self._get_preparation_advice(
                                            event_name, predicted_impact, days_until
                                        )
                                    })
            
            return sorted(upcoming_predictions, key=lambda x: x['days_until'])
            
        except Exception as e:
            logger.exception("Failed to predict upcoming events")
            return []
    
    def _get_preparation_advice(self, event_name: str, impact: float, days_until: int) -> str:
        """Generate preparation advice for upcoming events."""
        if impact > 1.1:  # Expect price increase
            if days_until > 14:
                return "Consider accumulating inventory before event"
            else:
                return "Event approaching - inventory accumulation window closing"
        elif impact < 0.9:  # Expect price decrease
            return "Consider reducing inventory before event"
        else:
            return "Minimal impact expected - monitor for opportunities"
    
    async def _generate_seasonal_forecasts(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate seasonal forecasts using historical patterns."""
        try:
            if len(data) < 100:
                return {'error': 'Insufficient data for forecasting'}
            
            forecasts = {
                'short_term': {},  # Next 7 days
                'medium_term': {},  # Next 30 days
                'long_term': {},   # Next 90 days
                'confidence_intervals': {},
                'forecast_method': 'seasonal_naive_with_trend'
            }
            
            # Extract current seasonality patterns
            current_date = timezone.now()
            current_day_of_week = current_date.weekday()
            current_month = current_date.month
            current_day_of_year = current_date.timetuple().tm_yday
            
            # Simple seasonal naive forecasting with trend
            recent_data = data.tail(30)  # Last 30 days for trend
            trend_slope = self._calculate_trend_slope(recent_data['price'])
            
            # Weekly pattern forecast (next 7 days)
            weekly_pattern = data.groupby('day_of_week')['price'].mean()
            base_price = data['price'].iloc[-1]
            
            for i in range(1, 8):  # Next 7 days
                forecast_day = (current_day_of_week + i) % 7
                seasonal_factor = weekly_pattern[forecast_day] / weekly_pattern.mean() if not weekly_pattern.empty else 1.0
                trend_adjustment = trend_slope * i
                
                forecasted_price = (base_price + trend_adjustment) * seasonal_factor
                forecasts['short_term'][f'day_{i}'] = {
                    'forecasted_price': forecasted_price,
                    'seasonal_factor': seasonal_factor,
                    'trend_adjustment': trend_adjustment
                }
            
            # Monthly pattern forecast
            monthly_pattern = data.groupby('month')['price'].mean()
            for i in range(1, 4):  # Next 3 months
                forecast_month = ((current_month + i - 1) % 12) + 1
                seasonal_factor = monthly_pattern[forecast_month] / monthly_pattern.mean() if not monthly_pattern.empty else 1.0
                trend_adjustment = trend_slope * i * 30  # Approximate days
                
                forecasted_price = (base_price + trend_adjustment) * seasonal_factor
                forecasts['medium_term'][f'month_{i}'] = {
                    'forecasted_price': forecasted_price,
                    'seasonal_factor': seasonal_factor,
                    'month': forecast_month
                }
            
            # Calculate confidence intervals based on historical volatility
            price_volatility = data['price'].pct_change().std()
            
            for term, term_forecasts in [('short_term', forecasts['short_term']), ('medium_term', forecasts['medium_term'])]:
                term_confidence = {}
                for period, forecast_data in term_forecasts.items():
                    price = forecast_data['forecasted_price']
                    # Simple confidence interval: ±2 standard deviations
                    margin = price * price_volatility * 2
                    
                    term_confidence[period] = {
                        'lower_bound': max(0, price - margin),
                        'upper_bound': price + margin,
                        'confidence_level': 0.95
                    }
                
                forecasts['confidence_intervals'][term] = term_confidence
            
            return forecasts
            
        except Exception as e:
            logger.exception("Failed to generate seasonal forecasts")
            return {'error': str(e)}
    
    def _calculate_trend_slope(self, price_series: pd.Series) -> float:
        """Calculate trend slope using linear regression."""
        try:
            if len(price_series) < 2:
                return 0
            
            x = np.arange(len(price_series))
            y = price_series.values
            
            # Remove any NaN values
            mask = ~np.isnan(y)
            if mask.sum() < 2:
                return 0
            
            x_clean = x[mask]
            y_clean = y[mask]
            
            # Linear regression
            slope, _, _, _, _ = stats.linregress(x_clean, y_clean)
            return slope
            
        except Exception:
            return 0
    
    async def _calculate_pattern_strengths(self, patterns: Dict[str, Any]) -> Dict[str, float]:
        """Calculate overall strength scores for different pattern types."""
        try:
            strength_scores = {}
            
            # Weekly pattern strength
            if 'weekly' in patterns and 'pattern_strength' in patterns['weekly']:
                strength_scores['weekly'] = patterns['weekly']['pattern_strength']
            
            # Monthly pattern strength
            if 'monthly' in patterns and 'pattern_strength' in patterns['monthly']:
                strength_scores['monthly'] = patterns['monthly']['pattern_strength']
            
            # Yearly pattern strength
            if 'yearly' in patterns and 'pattern_strength' in patterns['yearly']:
                strength_scores['yearly'] = patterns['yearly']['pattern_strength']
            
            # Event pattern strength (based on number of detected events)
            if 'events' in patterns:
                event_count = len(patterns['events'].get('detected_events', []))
                impact_count = len(patterns['events'].get('event_impact_analysis', {}))
                strength_scores['events'] = min((event_count + impact_count) / 20, 1.0)
            
            # Overall seasonal strength (weighted average)
            if strength_scores:
                weights = {'weekly': 0.3, 'monthly': 0.25, 'yearly': 0.35, 'events': 0.1}
                weighted_sum = sum(
                    strength_scores.get(pattern, 0) * weights.get(pattern, 0)
                    for pattern in weights.keys()
                )
                total_weight = sum(weights.get(pattern, 0) for pattern in strength_scores.keys())
                strength_scores['overall'] = weighted_sum / total_weight if total_weight > 0 else 0
            
            return strength_scores
            
        except Exception as e:
            logger.exception("Failed to calculate pattern strengths")
            return {}
    
    async def _generate_seasonal_recommendations(
        self, 
        analysis_results: Dict[str, Any], 
        item_id: int
    ) -> List[str]:
        """Generate actionable recommendations based on seasonal analysis."""
        try:
            recommendations = []
            
            patterns = analysis_results.get('patterns', {})
            forecasts = analysis_results.get('forecasts', {})
            strengths = analysis_results.get('strength_scores', {})
            
            # Weekly recommendations
            if 'weekly' in patterns and patterns['weekly'].get('weekend_effect'):
                weekend_premium = patterns['weekly']['weekend_effect'].get('price_premium_pct', 0)
                if abs(weekend_premium) > 2:  # Significant weekend effect
                    if weekend_premium > 0:
                        recommendations.append(
                            f"Strong weekend premium ({weekend_premium:.1f}%) - consider selling on weekends"
                        )
                    else:
                        recommendations.append(
                            f"Weekend discount ({abs(weekend_premium):.1f}%) - consider buying on weekends"
                        )
            
            # Monthly recommendations
            if 'monthly' in patterns and patterns['monthly'].get('month_effects'):
                month_effects = patterns['monthly']['month_effects']
                best_month = max(month_effects.items(), key=lambda x: x[1]['price_effect_pct'])
                worst_month = min(month_effects.items(), key=lambda x: x[1]['price_effect_pct'])
                
                if abs(best_month[1]['price_effect_pct']) > 5:
                    recommendations.append(
                        f"Historically highest prices in {best_month[0]} "
                        f"(+{best_month[1]['price_effect_pct']:.1f}%)"
                    )
                
                if abs(worst_month[1]['price_effect_pct']) > 5:
                    recommendations.append(
                        f"Historically lowest prices in {worst_month[0]} "
                        f"({worst_month[1]['price_effect_pct']:.1f}%)"
                    )
            
            # Event-based recommendations
            if 'events' in patterns and patterns['events'].get('upcoming_event_predictions'):
                upcoming_events = patterns['events']['upcoming_event_predictions']
                for event in upcoming_events[:2]:  # Top 2 upcoming events
                    recommendations.append(
                        f"Upcoming {event['event_name']} in {event['days_until']} days: "
                        f"{event['preparation_recommendation']}"
                    )
            
            # Forecast-based recommendations
            if 'short_term' in forecasts:
                # Find the most significant forecasted move
                short_term = forecasts['short_term']
                if short_term:
                    day_1_forecast = short_term.get('day_1', {})
                    current_price_estimate = analysis_results.get('data_points', 0)  # This would be better with actual current price
                    
                    if day_1_forecast and 'forecasted_price' in day_1_forecast:
                        # This is a simplified recommendation
                        recommendations.append("Short-term forecast available - monitor for entry/exit opportunities")
            
            # Overall strength-based recommendations
            overall_strength = strengths.get('overall', 0)
            if overall_strength > 0.6:
                recommendations.append(
                    f"Strong seasonal patterns detected (strength: {overall_strength:.1f}) - "
                    f"consider seasonal trading strategy"
                )
            elif overall_strength < 0.3:
                recommendations.append(
                    "Weak seasonal patterns - focus on other analysis methods"
                )
            
            return recommendations[:5]  # Limit to top 5 recommendations
            
        except Exception as e:
            logger.exception("Failed to generate seasonal recommendations")
            return ["Error generating recommendations - check data quality"]
    
    async def analyze_multiple_items_seasonal(
        self,
        item_ids: List[int],
        analysis_types: List[str] = None,
        lookback_days: int = 365
    ) -> Dict[int, Dict[str, Any]]:
        """Analyze seasonal patterns for multiple items."""
        try:
            results = {}
            
            # Process items in batches to manage memory
            batch_size = 5  # Smaller batch size for seasonal analysis (more memory intensive)
            for i in range(0, len(item_ids), batch_size):
                batch = item_ids[i:i + batch_size]
                
                # Analyze batch concurrently
                tasks = [
                    self.analyze_seasonal_patterns(item_id, analysis_types, lookback_days)
                    for item_id in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for item_id, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to analyze seasonal patterns for item {item_id}: {result}")
                        results[item_id] = {'error': str(result)}
                    else:
                        results[item_id] = result
            
            return results
            
        except Exception as e:
            logger.exception("Failed to analyze multiple items seasonal patterns")
            return {}


# Global instance
seasonal_analysis_engine = SeasonalAnalysisEngine()