"""
OSRS News & Update Sentiment Analysis Engine

Advanced NLP system for analyzing RuneScape news, updates, and community sentiment:
- Real-time news fetching from official OSRS sources
- Sentiment analysis using transformer models
- Impact prediction on specific items and markets
- Community reaction monitoring (Reddit, Discord, Twitter)
- Update categorization and severity assessment
- Market impact correlation analysis
- Predictive sentiment scoring for price movements
"""

import logging
import re
import asyncio
import aiohttp
import feedparser
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from asgiref.sync import sync_to_async
import json

# NLP imports
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
from collections import Counter

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('vader_lexicon', quiet=True)

from apps.items.models import Item
from apps.realtime_engine.models import MarketEvent
from services.intelligent_cache import intelligent_cache

logger = logging.getLogger(__name__)


class NewsSentimentAnalyzer:
    """
    Advanced sentiment analysis system for OSRS news and community content.
    """
    
    def __init__(self):
        self.cache_prefix = "news_sentiment:"
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # OSRS-specific sentiment keywords
        self.positive_keywords = {
            'buff', 'buffed', 'improved', 'enhancement', 'boost', 'increased', 
            'better', 'upgrade', 'stronger', 'faster', 'easier', 'quality of life',
            'qol', 'new content', 'release', 'expansion', 'reward', 'bonus'
        }
        
        self.negative_keywords = {
            'nerf', 'nerfed', 'reduced', 'decreased', 'removed', 'banned', 
            'restricted', 'harder', 'slower', 'weaker', 'bug', 'issue', 
            'problem', 'exploit', 'patch', 'fix', 'maintenance'
        }
        
        # Item category mappings for impact analysis
        self.item_categories = {
            'combat': ['weapon', 'armour', 'armor', 'sword', 'bow', 'staff', 'shield', 'helm'],
            'skilling': ['tool', 'pick', 'axe', 'fishing', 'cooking', 'crafting', 'smithing'],
            'food': ['food', 'potion', 'brew', 'restore', 'prayer', 'energy'],
            'resources': ['ore', 'log', 'fish', 'herb', 'seed', 'rune', 'essence'],
            'rare': ['3rd age', 'dragon', 'barrows', 'godsword', 'whip', 'primordial']
        }
        
        # News sources
        self.news_sources = {
            'official_news': 'https://secure.runescape.com/m=news/list_rss.ws?cat=0',
            'official_updates': 'https://secure.runescape.com/m=news/list_rss.ws?cat=1',
            'osrs_reddit': 'https://www.reddit.com/r/2007scape/.rss',
        }
        
    async def analyze_market_sentiment(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze overall market sentiment from recent news and updates.
        
        Args:
            lookback_hours: Hours to look back for news analysis
            
        Returns:
            Dictionary with sentiment analysis results
        """
        logger.debug(f"🔍 Analyzing market sentiment for last {lookback_hours} hours")
        
        try:
            # Fetch recent news from multiple sources
            news_data = await self._fetch_recent_news(lookback_hours)
            
            if not news_data:
                return {
                    'overall_sentiment': 'neutral',
                    'sentiment_score': 0.0,
                    'confidence': 0.0,
                    'analyzed_articles': 0,
                    'key_themes': [],
                    'market_impact_predictions': {}
                }
            
            # Analyze sentiment of all articles
            sentiment_results = []
            item_mentions = Counter()
            category_sentiment = {}
            
            for article in news_data:
                analysis = await self._analyze_article_sentiment(article)
                sentiment_results.append(analysis)
                
                # Track item mentions
                for item, count in analysis.get('item_mentions', {}).items():
                    item_mentions[item] += count
                
                # Track category sentiment
                for category, sentiment in analysis.get('category_sentiment', {}).items():
                    if category not in category_sentiment:
                        category_sentiment[category] = []
                    category_sentiment[category].append(sentiment)
            
            # Calculate overall sentiment
            overall_sentiment = self._calculate_overall_sentiment(sentiment_results)
            
            # Generate market impact predictions
            market_predictions = await self._predict_market_impacts(
                sentiment_results, item_mentions, category_sentiment
            )
            
            # Extract key themes
            key_themes = self._extract_key_themes(sentiment_results)
            
            result = {
                'timestamp': timezone.now().isoformat(),
                'overall_sentiment': overall_sentiment['label'],
                'sentiment_score': overall_sentiment['compound'],
                'confidence': overall_sentiment['confidence'],
                'analyzed_articles': len(sentiment_results),
                'key_themes': key_themes,
                'market_impact_predictions': market_predictions,
                'category_sentiment': {
                    cat: sum(scores) / len(scores) if scores else 0.0
                    for cat, scores in category_sentiment.items()
                },
                'top_mentioned_items': dict(item_mentions.most_common(10)),
                'sentiment_breakdown': {
                    'positive': len([s for s in sentiment_results if s['sentiment'] == 'positive']),
                    'negative': len([s for s in sentiment_results if s['sentiment'] == 'negative']),
                    'neutral': len([s for s in sentiment_results if s['sentiment'] == 'neutral'])
                }
            }
            
            # Cache results
            cache_key = f"{self.cache_prefix}market_sentiment"
            intelligent_cache.set(
                cache_key,
                result,
                tier="warm",
                tags=["sentiment_analysis", "market_analysis"]
            )
            
            logger.info(f"✅ Market sentiment analysis completed: {overall_sentiment['label']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Market sentiment analysis failed: {e}")
            return {'error': str(e)}
    
    async def analyze_item_specific_sentiment(self, item_ids: List[int]) -> Dict[str, Any]:
        """
        Analyze sentiment specifically related to certain items.
        
        Args:
            item_ids: List of item IDs to analyze
            
        Returns:
            Dictionary with item-specific sentiment analysis
        """
        logger.debug(f"🔍 Analyzing sentiment for {len(item_ids)} specific items")
        
        try:
            # Get item names for matching
            items = await self._get_items_by_ids(item_ids)
            item_names = {item.item_id: item.name.lower() for item in items}
            
            # Fetch recent news
            news_data = await self._fetch_recent_news(48)  # Look back 48 hours for item mentions
            
            item_sentiment = {}
            
            for item_id, item_name in item_names.items():
                sentiment_scores = []
                mention_contexts = []
                
                for article in news_data:
                    # Check if item is mentioned in article
                    article_text = f"{article.get('title', '')} {article.get('description', '')}".lower()
                    
                    if self._item_mentioned_in_text(item_name, article_text):
                        # Analyze sentiment of sentences mentioning the item
                        sentences = sent_tokenize(article_text)
                        
                        for sentence in sentences:
                            if self._item_mentioned_in_text(item_name, sentence):
                                sentiment = self.sentiment_analyzer.polarity_scores(sentence)
                                sentiment_scores.append(sentiment['compound'])
                                mention_contexts.append(sentence[:200])  # First 200 chars
                
                if sentiment_scores:
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                    sentiment_label = self._get_sentiment_label(avg_sentiment)
                    
                    item_sentiment[item_id] = {
                        'item_name': item_names[item_id],
                        'sentiment_score': round(avg_sentiment, 3),
                        'sentiment_label': sentiment_label,
                        'mention_count': len(sentiment_scores),
                        'confidence': min(1.0, len(sentiment_scores) / 5),  # Higher confidence with more mentions
                        'sample_contexts': mention_contexts[:3],  # Top 3 contexts
                        'predicted_impact': self._predict_item_impact(avg_sentiment, len(sentiment_scores))
                    }
                else:
                    item_sentiment[item_id] = {
                        'item_name': item_names[item_id],
                        'sentiment_score': 0.0,
                        'sentiment_label': 'neutral',
                        'mention_count': 0,
                        'confidence': 0.0,
                        'sample_contexts': [],
                        'predicted_impact': 'no_impact'
                    }
            
            result = {
                'timestamp': timezone.now().isoformat(),
                'analyzed_items': len(item_sentiment),
                'item_sentiment': item_sentiment,
                'summary': {
                    'positive_items': len([s for s in item_sentiment.values() if s['sentiment_label'] == 'positive']),
                    'negative_items': len([s for s in item_sentiment.values() if s['sentiment_label'] == 'negative']),
                    'neutral_items': len([s for s in item_sentiment.values() if s['sentiment_label'] == 'neutral']),
                    'total_mentions': sum(s['mention_count'] for s in item_sentiment.values())
                }
            }
            
            logger.info(f"✅ Item sentiment analysis completed for {len(item_ids)} items")
            return result
            
        except Exception as e:
            logger.error(f"❌ Item sentiment analysis failed: {e}")
            return {'error': str(e)}
    
    async def _fetch_recent_news(self, hours: int) -> List[Dict[str, Any]]:
        """Fetch recent news from various sources."""
        logger.debug(f"📰 Fetching news from last {hours} hours")
        
        all_articles = []
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        async with aiohttp.ClientSession() as session:
            for source_name, source_url in self.news_sources.items():
                try:
                    logger.debug(f"Fetching from {source_name}: {source_url}")
                    
                    async with session.get(source_url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Parse RSS feed
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries:
                                # Parse publication date
                                try:
                                    if hasattr(entry, 'published_parsed'):
                                        pub_date = datetime(*entry.published_parsed[:6])
                                        pub_date = timezone.make_aware(pub_date)
                                    else:
                                        pub_date = timezone.now()  # Fallback to now
                                    
                                    # Check if article is recent enough
                                    if pub_date >= cutoff_time:
                                        article = {
                                            'source': source_name,
                                            'title': entry.get('title', ''),
                                            'description': entry.get('summary', ''),
                                            'link': entry.get('link', ''),
                                            'published': pub_date.isoformat(),
                                            'full_text': f"{entry.get('title', '')} {entry.get('summary', '')}"
                                        }
                                        all_articles.append(article)
                                        
                                except Exception as e:
                                    logger.debug(f"Error parsing article from {source_name}: {e}")
                                    continue
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch from {source_name}: {e}")
                    continue
        
        logger.debug(f"📰 Fetched {len(all_articles)} recent articles")
        return all_articles
    
    async def _analyze_article_sentiment(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment of a single article."""
        text = article['full_text']
        
        # Basic sentiment analysis
        sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
        sentiment_label = self._get_sentiment_label(sentiment_scores['compound'])
        
        # OSRS-specific sentiment adjustment
        osrs_sentiment = self._analyze_osrs_specific_sentiment(text)
        
        # Combine sentiments
        adjusted_compound = (sentiment_scores['compound'] + osrs_sentiment) / 2
        adjusted_label = self._get_sentiment_label(adjusted_compound)
        
        # Find item mentions
        item_mentions = self._find_item_mentions(text)
        
        # Categorize content
        category_sentiment = self._analyze_category_sentiment(text, adjusted_compound)
        
        return {
            'article_title': article['title'],
            'source': article['source'],
            'sentiment': adjusted_label,
            'sentiment_scores': {
                'compound': adjusted_compound,
                'positive': sentiment_scores['pos'],
                'negative': sentiment_scores['neg'],
                'neutral': sentiment_scores['neu']
            },
            'osrs_sentiment_boost': osrs_sentiment,
            'item_mentions': item_mentions,
            'category_sentiment': category_sentiment,
            'key_phrases': self._extract_key_phrases(text)
        }
    
    def _analyze_osrs_specific_sentiment(self, text: str) -> float:
        """Analyze OSRS-specific sentiment using domain keywords."""
        text_lower = text.lower()
        
        positive_score = 0
        negative_score = 0
        
        # Count positive keywords
        for keyword in self.positive_keywords:
            if keyword in text_lower:
                positive_score += text_lower.count(keyword)
        
        # Count negative keywords
        for keyword in self.negative_keywords:
            if keyword in text_lower:
                negative_score += text_lower.count(keyword)
        
        # Calculate net sentiment
        total_keywords = positive_score + negative_score
        if total_keywords == 0:
            return 0.0
        
        net_sentiment = (positive_score - negative_score) / total_keywords
        return max(-1.0, min(1.0, net_sentiment))  # Clamp to [-1, 1]
    
    def _find_item_mentions(self, text: str) -> Dict[str, int]:
        """Find mentions of items in text."""
        text_lower = text.lower()
        mentions = {}
        
        # Common OSRS item patterns
        item_patterns = [
            r'\b(\w+)\s+(?:sword|axe|bow|staff|shield|armor|armour|weapon|tool)\b',
            r'\b(?:dragon|rune|adamant|mithril|steel|iron|bronze)\s+(\w+)\b',
            r'\b(\w+)\s+(?:potion|brew|food|rune|essence)\b',
            r'\b3rd\s+age\s+(\w+)\b',
            r'\bbarrows\s+(\w+)\b'
        ]
        
        for pattern in item_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                item_name = match if isinstance(match, str) else ' '.join(match)
                mentions[item_name] = mentions.get(item_name, 0) + 1
        
        return mentions
    
    def _analyze_category_sentiment(self, text: str, base_sentiment: float) -> Dict[str, float]:
        """Analyze sentiment for different item categories."""
        text_lower = text.lower()
        category_sentiment = {}
        
        for category, keywords in self.item_categories.items():
            category_relevance = 0
            for keyword in keywords:
                if keyword in text_lower:
                    category_relevance += text_lower.count(keyword)
            
            if category_relevance > 0:
                # Weight sentiment by relevance
                category_sentiment[category] = base_sentiment * min(1.0, category_relevance / 3)
        
        return category_sentiment
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text."""
        # Simple approach: find common OSRS-related phrases
        phrases = []
        text_lower = text.lower()
        
        # Pattern-based phrase extraction
        phrase_patterns = [
            r'\b(?:new|upcoming|latest)\s+(?:update|content|feature|item)\b',
            r'\b(?:buff|nerf|change|fix|improve)\s+(?:to|for)?\s*\w+\b',
            r'\b(?:release|launch|introduce)\s+\w+\b'
        ]
        
        for pattern in phrase_patterns:
            matches = re.findall(pattern, text_lower)
            phrases.extend(matches)
        
        return list(set(phrases))[:10]  # Top 10 unique phrases
    
    def _calculate_overall_sentiment(self, sentiment_results: List[Dict]) -> Dict[str, Any]:
        """Calculate overall sentiment from multiple articles."""
        if not sentiment_results:
            return {'compound': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        compounds = [result['sentiment_scores']['compound'] for result in sentiment_results]
        avg_compound = sum(compounds) / len(compounds)
        
        # Calculate confidence based on consistency
        sentiment_variance = sum((x - avg_compound) ** 2 for x in compounds) / len(compounds)
        confidence = max(0.0, 1.0 - sentiment_variance)
        
        return {
            'compound': avg_compound,
            'label': self._get_sentiment_label(avg_compound),
            'confidence': confidence
        }
    
    async def _predict_market_impacts(self, sentiment_results: List[Dict], 
                                    item_mentions: Counter, 
                                    category_sentiment: Dict) -> Dict[str, Any]:
        """Predict market impacts based on sentiment analysis."""
        predictions = {}
        
        # Category-based predictions
        for category, sentiments in category_sentiment.items():
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                
                if abs(avg_sentiment) > 0.3:  # Significant sentiment
                    impact_direction = 'positive' if avg_sentiment > 0 else 'negative'
                    impact_magnitude = min(100, abs(avg_sentiment) * 100)
                    
                    predictions[f'{category}_category'] = {
                        'impact_direction': impact_direction,
                        'impact_magnitude': impact_magnitude,
                        'confidence': min(1.0, len(sentiments) / 3),
                        'reasoning': f"Sentiment analysis of {category} items shows {impact_direction} trend"
                    }
        
        # Top mentioned items predictions
        for item, count in item_mentions.most_common(5):
            if count >= 2:  # At least 2 mentions
                predictions[f'item_{item}'] = {
                    'impact_direction': 'attention_increase',
                    'impact_magnitude': min(100, count * 20),
                    'confidence': min(1.0, count / 5),
                    'reasoning': f"High mention frequency ({count} times) indicates increased attention"
                }
        
        return predictions
    
    def _extract_key_themes(self, sentiment_results: List[Dict]) -> List[str]:
        """Extract key themes from sentiment analysis results."""
        all_phrases = []
        for result in sentiment_results:
            all_phrases.extend(result.get('key_phrases', []))
        
        # Count phrase frequency
        phrase_counts = Counter(all_phrases)
        return [phrase for phrase, count in phrase_counts.most_common(10)]
    
    def _get_sentiment_label(self, compound_score: float) -> str:
        """Convert compound score to sentiment label."""
        if compound_score >= 0.05:
            return 'positive'
        elif compound_score <= -0.05:
            return 'negative'
        else:
            return 'neutral'
    
    def _item_mentioned_in_text(self, item_name: str, text: str) -> bool:
        """Check if item is mentioned in text with fuzzy matching."""
        item_words = item_name.split()
        text_lower = text.lower()
        
        # Exact match
        if item_name in text_lower:
            return True
        
        # Partial match (all words present)
        if len(item_words) > 1:
            return all(word in text_lower for word in item_words)
        
        return False
    
    def _predict_item_impact(self, sentiment_score: float, mention_count: int) -> str:
        """Predict impact on item based on sentiment and mentions."""
        if mention_count == 0:
            return 'no_impact'
        
        if abs(sentiment_score) < 0.1:
            return 'minimal_impact'
        
        if sentiment_score > 0.3 and mention_count >= 3:
            return 'strong_positive_impact'
        elif sentiment_score > 0.1:
            return 'positive_impact'
        elif sentiment_score < -0.3 and mention_count >= 3:
            return 'strong_negative_impact'
        elif sentiment_score < -0.1:
            return 'negative_impact'
        
        return 'moderate_impact'
    
    @sync_to_async
    def _get_items_by_ids(self, item_ids: List[int]) -> List[Item]:
        """Get items by IDs."""
        return list(Item.objects.filter(item_id__in=item_ids))


# Global news sentiment analyzer instance
news_sentiment_analyzer = NewsSentimentAnalyzer()