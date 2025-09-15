"""
Enhanced FAISS vector database builder with comprehensive item categorization and market context.
Addresses the 'found 0 relevant items' issue by improving semantic understanding.
"""

import os
import sys
import django
from pathlib import Path

sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

import logging
import re
from django.db import transaction
from django.db.models import Q
from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from services.faiss_manager import FaissVectorDatabase
from services.embedding_service import SyncOllamaEmbeddingService
import time
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedVectorDatabaseBuilder:
    def __init__(self):
        self.embedding_service = SyncOllamaEmbeddingService()
        self.faiss_db = FaissVectorDatabase(index_name="osrs_items", dimension=1024)
        self.batch_size = 15  # Optimized for Ollama
        self.delay_between_batches = 0.3
        
        # Enhanced categorization patterns
        self.category_patterns = {
            # Weapons
            'weapons': {
                'patterns': [
                    r'\b(sword|scimitar|dagger|knife|blade|rapier|sabre)\b',
                    r'\b(axe|hatchet|battleaxe|pickaxe|woodcutting|mining)\b', 
                    r'\b(bow|crossbow|arrow|bolt|javelin|dart|throwing)\b',
                    r'\b(staff|battlestaff|wand|orb|tome|spell)\b',
                    r'\b(mace|warhammer|maul|crusher)\b',
                    r'\b(whip|flail|chain|cat o)\b',
                    r'\b(spear|halberd|hasta|lance)\b'
                ],
                'context': 'combat weapon for fighting monsters and PvP, used in melee, ranged, or magic combat'
            },
            
            # Armor and Equipment
            'armor': {
                'patterns': [
                    r'\b(helmet|helm|coif|hat|hood)\b',
                    r'\b(platebody|chestplate|chainbody|shirt|top|robetop)\b',
                    r'\b(platelegs|chainskirt|skirt|legs|chaps|bottoms)\b',
                    r'\b(boots|gloves|gauntlets|vambraces)\b',
                    r'\b(shield|defender|kiteshield|buckler)\b',
                    r'\b(cape|cloak|back|fire cape|skillcape)\b',
                    r'\b(ring|amulet|necklace|pendant)\b'
                ],
                'context': 'protective equipment worn to defend against damage in combat and provide stat bonuses'
            },
            
            # Magic Items and Runes
            'magic': {
                'patterns': [
                    r'\b(rune|runes)\b',
                    r'\b(nature|law|death|blood|chaos|cosmic|astral|wrath)\b',
                    r'\b(fire|water|earth|air|mind|body|soul)\b',
                    r'\b(staff|battlestaff|wand|orb|tome)\b',
                    r'\b(spell|magic|enchant|teleport|alchemy)\b',
                    r'\b(essence|talisman|tiara)\b'
                ],
                'context': 'magical items used for spellcasting, runecrafting, and magic combat including runes for high alchemy'
            },
            
            # Resources and Materials
            'resources': {
                'patterns': [
                    r'\b(ore|bar|ingot|coal|gem|crystal)\b',
                    r'\b(logs|wood|lumber|plank|bow)\b',
                    r'\b(hide|leather|dragon|skin)\b',
                    r'\b(fish|raw|cooked|food)\b',
                    r'\b(herb|seed|farming|compost|flower)\b',
                    r'\b(bone|ash|crushed|powder)\b',
                    r'\b(feather|fur|claw|scale|horn)\b'
                ],
                'context': 'raw materials and resources used for skilling, crafting, cooking, and training'
            },
            
            # Consumables and Potions
            'consumables': {
                'patterns': [
                    r'\b(potion|elixir|dose|barbarian|herblore)\b',
                    r'\b(food|eat|restore|heal|cake|pie|bread)\b',
                    r'\b(prayer|super|antifire|combat|strength|attack|defence)\b',
                    r'\b(ranging|magic|fishing|agility|thieving)\b',
                    r'\b(energy|stamina|relicyms|serum|cure)\b',
                    r'\b(teleport|tablet|tab|house)\b'
                ],
                'context': 'consumable items including potions, food, and supplies used for healing, skill boosting, and utility'
            },
            
            # High-Value/Boss Items
            'rare_valuable': {
                'patterns': [
                    r'\b(twisted|ancestral|justiciar|inquisitor)\b',
                    r'\b(scythe|rapier|mace|avernic|primordial)\b',
                    r'\b(dragon|barrows|god|bandos|armadyl|saradomin|zamorak)\b',
                    r'\b(abyssal|dragon|rune|adamant|godsword)\b',
                    r'\b(ring|berserker|warrior|archer|seers)\b',
                    r'\b(third|age|gilded|gold|ornament)\b'
                ],
                'context': 'high-value rare items from bosses, minigames, and high-level content with significant trading value'
            },
            
            # Tools and Utilities  
            'tools': {
                'patterns': [
                    r'\b(pick|pickaxe|axe|hatchet|fishing|net|harpoon)\b',
                    r'\b(chisel|hammer|saw|needle|knife|shears)\b',
                    r'\b(tinderbox|rope|spade|bucket|jug|vial)\b',
                    r'\b(secateurs|rake|seed|dibber|watering)\b'
                ],
                'context': 'tools and equipment used for skilling activities like mining, woodcutting, fishing, and crafting'
            }
        }
        
        # Profit tier classifications
        self.profit_tiers = {
            'high_margin': 'items with profit margins over 1000 GP suitable for large-scale flipping',
            'medium_margin': 'items with profit margins 100-1000 GP suitable for regular trading',
            'small_margin': 'items with profit margins under 100 GP suitable for high-frequency trading',
            'high_alchemy': 'items profitable for high alchemy magic training with nature runes',
            'bulk_trading': 'items with high buy limits suitable for bulk trading strategies'
        }

    def categorize_item(self, item: Item) -> List[str]:
        """Enhanced item categorization with semantic understanding."""
        categories = []
        item_text = f"{item.name.lower()} {item.examine.lower() if item.examine else ''}"
        
        # Check each category pattern
        for category, data in self.category_patterns.items():
            for pattern in data['patterns']:
                if re.search(pattern, item_text, re.IGNORECASE):
                    categories.append(category)
                    break
        
        # Add profit-based categories
        if hasattr(item, 'profit_calc') and item.profit_calc:
            profit = getattr(item.profit_calc, 'current_profit', 0)
            if profit > 1000:
                categories.append('high_margin')
            elif profit > 100:
                categories.append('medium_margin')
            elif profit > 0:
                categories.append('small_margin')
            
            # High alchemy viability
            alch_score = getattr(item.profit_calc, 'high_alch_viability_score', 0)
            if alch_score > 0.5:
                categories.append('high_alchemy')
        
        # Buy limit based categories
        if item.limit > 1000:
            categories.append('bulk_trading')
        
        return categories if categories else ['miscellaneous']

    def create_enhanced_item_representation(self, item: Item) -> str:
        """Create comprehensive text representation with market context."""
        parts = []
        
        # Core item info
        parts.append(f"Item: {item.name}")
        parts.append(f"ID: {item.item_id}")
        
        # Enhanced description
        if item.examine:
            parts.append(f"Description: {item.examine}")
            
        # Categories with context
        categories = self.categorize_item(item)
        for category in categories:
            if category in self.category_patterns:
                context = self.category_patterns[category]['context']
                parts.append(f"Category: {category} - {context}")
            elif category in self.profit_tiers:
                context = self.profit_tiers[category]
                parts.append(f"Trading type: {category} - {context}")
        
        # Enhanced economic data
        if item.high_alch > 0:
            parts.append(f"High alchemy value: {item.high_alch} GP suitable for magic training")
            profit_after_runes = item.high_alch - 180  # Nature rune cost
            if profit_after_runes > 0:
                parts.append(f"Alchemy profit potential: {profit_after_runes} GP per cast")
        
        if item.value > 0:
            parts.append(f"Base shop value: {item.value} GP")
            
        # Trading context
        membership_text = "members-only exclusive item" if item.members else "free-to-play accessible item"
        parts.append(f"Access: {membership_text}")
        
        if item.limit > 0:
            if item.limit >= 1000:
                parts.append(f"Grand Exchange buy limit: {item.limit} suitable for bulk trading and volume strategies")
            else:
                parts.append(f"Grand Exchange buy limit: {item.limit} limited quantity trading")
        
        # Market activity
        if item.is_active:
            parts.append("Currently actively traded on Grand Exchange with live price data")
        
        # Profit calculation context
        try:
            profit_calc = ProfitCalculation.objects.filter(item=item).first()
            if profit_calc:
                if profit_calc.current_profit > 0:
                    parts.append(f"Current trading profit: {profit_calc.current_profit} GP per item")
                    parts.append(f"Buy price: {profit_calc.current_buy_price} GP, Sell price: {profit_calc.current_sell_price} GP")
                    
                if profit_calc.current_profit_margin > 0:
                    parts.append(f"Profit margin: {profit_calc.current_profit_margin:.1f}% return on investment")
                    
                # Volume and liquidity info
                if hasattr(profit_calc, 'daily_volume') and profit_calc.daily_volume:
                    if profit_calc.daily_volume > 1000:
                        parts.append(f"High liquidity: {profit_calc.daily_volume} daily volume")
                    else:
                        parts.append(f"Limited liquidity: {profit_calc.daily_volume} daily volume")
        except:
            pass
            
        # Usage context keywords for better semantic matching
        usage_terms = []
        item_name_lower = item.name.lower()
        
        if any(term in item_name_lower for term in ['dragon', 'barrows', 'godsword', 'whip', 'bandos', 'armadyl']):
            usage_terms.append("high-level PvM gear boss drops valuable rare expensive")
            
        if any(term in item_name_lower for term in ['rune', 'nature', 'law', 'death', 'blood']):
            usage_terms.append("magic spellcasting runecrafting alchemy teleport combat")
            
        if any(term in item_name_lower for term in ['potion', 'dose', 'prayer', 'combat', 'super']):
            usage_terms.append("consumable healing boost temporary effect combat preparation")
            
        if any(term in item_name_lower for term in ['ore', 'bar', 'logs', 'raw', 'hide']):
            usage_terms.append("resource material crafting skilling training supplies raw material")
            
        if usage_terms:
            parts.append(f"Usage context: {' '.join(usage_terms)}")
        
        return " | ".join(parts)

    def build_enhanced_database(self):
        """Build the enhanced vector database with comprehensive item understanding."""
        logger.info("🚀 Starting Enhanced FAISS vector database build...")
        logger.info("🎯 Goal: Fix 'found 0 relevant items' by improving semantic understanding")
        
        # Get all items including their profit calculations
        items = Item.objects.select_related('profit_calc').filter(is_active=True).order_by('item_id')
        
        total_items = items.count()
        logger.info(f"📊 Found {total_items} items to process with enhanced categorization")
        
        if total_items == 0:
            logger.error("❌ No items found in database!")
            return False
            
        # Process in batches with enhanced context
        vectors_data = []
        processed = 0
        category_stats = {}
        
        for batch_start in range(0, total_items, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_items)
            batch_items = items[batch_start:batch_end]
            
            batch_num = batch_start // self.batch_size + 1
            total_batches = (total_items - 1) // self.batch_size + 1
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches}: items {batch_start+1}-{batch_end}")
            
            # Create enhanced text representations
            texts = []
            item_ids = []
            
            for item in batch_items:
                try:
                    enhanced_text = self.create_enhanced_item_representation(item)
                    texts.append(enhanced_text)
                    item_ids.append(item.item_id)
                    
                    # Track categories for stats
                    categories = self.categorize_item(item)
                    for category in categories:
                        category_stats[category] = category_stats.get(category, 0) + 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create enhanced text for item {item.item_id}: {e}")
                    continue
            
            if not texts:
                logger.warning("⚠️ No valid texts in batch, skipping")
                continue
                
            # Get embeddings with retry logic
            logger.info(f"🧠 Getting embeddings for {len(texts)} items...")
            max_retries = 3
            embeddings = None
            
            for attempt in range(max_retries):
                try:
                    embeddings = self.embedding_service.generate_embeddings_batch(
                        texts, 
                        batch_size=5,  # Conservative for stability
                        use_cache=True
                    )
                    if embeddings:
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Embedding attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
            
            if not embeddings:
                logger.error("❌ Failed to get embeddings after retries")
                continue
            
            # Store valid embeddings
            valid_count = 0
            for item_id, text, embedding in zip(item_ids, texts, embeddings):
                if embedding is not None:
                    vectors_data.append((item_id, embedding))
                    valid_count += 1
                else:
                    logger.warning(f"⚠️ No embedding for item {item_id}")
            
            processed += valid_count
            logger.info(f"✅ Processed {valid_count}/{len(texts)} items in batch (Total: {processed})")
            
            # Brief pause between batches
            time.sleep(self.delay_between_batches)
        
        logger.info(f"📈 Category distribution:")
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   {category}: {count} items")
        
        if not vectors_data:
            logger.error("❌ No valid embeddings generated!")
            return False
            
        # Rebuild FAISS index
        logger.info(f"🏗️ Building FAISS index with {len(vectors_data)} vectors...")
        
        try:
            success = self.faiss_db.rebuild_index([
                {'item_id': item_id, 'vector': embedding} 
                for item_id, embedding in vectors_data
            ])
            
            if success:
                logger.info(f"✅ Enhanced vector database built successfully!")
                logger.info(f"📊 Total items indexed: {len(vectors_data)}")
                logger.info(f"🎯 Semantic search should now find relevant magic items, resources, and potions")
                return True
            else:
                logger.error("❌ Failed to rebuild FAISS index")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error building index: {e}")
            return False

def main():
    """Main execution function."""
    builder = EnhancedVectorDatabaseBuilder()
    
    print("🚀 Starting Enhanced Vector Database Build")
    print("🎯 This will fix the 'found 0 relevant items' issue")
    print("📝 Enhanced with:")
    print("   - Comprehensive item categorization")  
    print("   - Market context and trading intelligence")
    print("   - Magic items, resources, potions semantic understanding")
    print("   - Profit tier classifications")
    print("   - Usage context keywords")
    print()
    
    success = builder.build_enhanced_database()
    
    if success:
        print("✅ Enhanced vector database build completed successfully!")
        print("🎯 AI should now properly find magic items, resources, and potions")
    else:
        print("❌ Enhanced vector database build failed!")
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)