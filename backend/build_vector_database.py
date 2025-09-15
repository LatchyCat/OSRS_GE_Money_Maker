"""
Build FAISS vector database with embeddings for all OSRS items.
This script creates embeddings for all items in the database using OpenAI's text-embedding-3-small model.
"""

import os
import sys
import django
from pathlib import Path

sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

import logging
from django.db import transaction
from django.db.models import Q
from apps.items.models import Item
from services.faiss_manager import FaissVectorDatabase
from services.embedding_service import SyncOllamaEmbeddingService
import time
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDatabaseBuilder:
    def __init__(self):
        self.embedding_service = SyncOllamaEmbeddingService()
        # snowflake-arctic-embed2 has 1024 dimensions
        self.faiss_db = FaissVectorDatabase(index_name="osrs_items", dimension=1024)
        self.batch_size = 20  # Smaller batches for local Ollama
        self.delay_between_batches = 0.5
        
    def create_item_text_representation(self, item: Item) -> str:
        """Create a rich text representation of an item for embedding."""
        parts = []
        
        # Basic info
        parts.append(f"Item: {item.name}")
        parts.append(f"ID: {item.item_id}")
        
        # Examine text
        if item.examine:
            parts.append(f"Description: {item.examine}")
            
        # High alch info
        if item.high_alch:
            parts.append(f"High alch value: {item.high_alch} gp")
            
        # Value
        if item.value:
            parts.append(f"Base value: {item.value} gp")
            
        # Members/F2P
        parts.append(f"Members: {'Yes' if item.members else 'No'}")
            
        # Buy limit
        if item.limit > 0:
            parts.append(f"GE buy limit: {item.limit}")
            
        # Active trading status
        if item.is_active:
            parts.append("Actively traded")
                
        # Add price context for trading
        parts.append("Used for Grand Exchange trading and high alchemy profit calculations")
        
        return " | ".join(parts)
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts."""
        try:
            # Use the existing Ollama embedding service
            embeddings = self.embedding_service.generate_embeddings_batch(
                texts, 
                batch_size=self.batch_size,
                use_cache=True
            )
            # Filter out None values and return valid embeddings
            valid_embeddings = []
            for embedding in embeddings:
                if embedding is not None:
                    valid_embeddings.append(embedding)
                else:
                    logger.warning("Received None embedding from service")
            return valid_embeddings
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return []
    
    def build_database(self):
        """Build the complete vector database."""
        logger.info("🚀 Starting FAISS vector database build...")
        
        # Get all active items
        items = Item.objects.filter(is_active=True).order_by('item_id')
        
        total_items = items.count()
        logger.info(f"📊 Found {total_items} items to process")
        
        if total_items == 0:
            logger.error("No items found in database!")
            return False
            
        # Process in batches
        vectors_data = []
        processed = 0
        
        for batch_start in range(0, total_items, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_items)
            batch_items = items[batch_start:batch_end]
            
            logger.info(f"🔄 Processing batch {batch_start//self.batch_size + 1}/{(total_items-1)//self.batch_size + 1}: items {batch_start+1}-{batch_end}")
            
            # Create text representations
            texts = []
            item_ids = []
            
            for item in batch_items:
                try:
                    text = self.create_item_text_representation(item)
                    texts.append(text)
                    item_ids.append(item.item_id)
                except Exception as e:
                    logger.warning(f"Failed to create text for item {item.item_id}: {e}")
                    continue
            
            if not texts:
                logger.warning("No valid texts in batch, skipping")
                continue
                
            # Get embeddings
            logger.info(f"🧠 Getting embeddings for {len(texts)} items...")
            embeddings = self.embedding_service.generate_embeddings_batch(
                texts, 
                batch_size=5,  # Small batches for Ollama
                use_cache=True
            )
            
            if not embeddings:
                logger.error("No embeddings returned from service")
                continue
            
            # Store valid embeddings for batch rebuild
            valid_count = 0
            for item_id, text, embedding in zip(item_ids, texts, embeddings):
                if embedding is not None:
                    vectors_data.append((item_id, embedding))
                    valid_count += 1
                else:
                    logger.warning(f"Skipping item {item_id} due to failed embedding")
                    
            processed += valid_count
            logger.info(f"✅ Got embeddings for {valid_count}/{len(texts)} items. Total: {processed}/{total_items}")
            
            # Rate limiting
            time.sleep(self.delay_between_batches)
        
        if not vectors_data:
            logger.error("No vectors created!")
            return False
            
        # Rebuild index with all vectors
        logger.info(f"🔧 Building FAISS index with {len(vectors_data)} vectors...")
        success = self.faiss_db.rebuild_index(vectors_data)
        
        if success:
            # Save to disk
            logger.info("💾 Saving index to disk...")
            save_success = self.faiss_db.save_index()
            
            if save_success:
                stats = self.faiss_db.get_stats()
                logger.info("🎉 Vector database build completed successfully!")
                logger.info(f"📈 Statistics: {stats}")
                return True
            else:
                logger.error("Failed to save index to disk")
                return False
        else:
            logger.error("Failed to build FAISS index")
            return False
    
    def test_search(self):
        """Test the built vector database with sample queries."""
        logger.info("🧪 Testing vector database...")
        
        test_queries = [
            "combat weapon sword",
            "magic rune fire spell",
            "profitable high alch item",
            "expensive rare equipment",
            "food healing consumable"
        ]
        
        for query in test_queries:
            logger.info(f"🔍 Testing query: '{query}'")
            
            # Get query embedding
            query_embedding = self.embedding_service.generate_embedding(query, use_cache=False)
            if not query_embedding:
                logger.error(f"Failed to get embedding for query: {query}")
                continue
                
            # Search
            results = self.faiss_db.search(query_embedding, k=5, threshold=0.0)
            
            if results:
                logger.info(f"📋 Results:")
                for item_id, similarity in results:
                    try:
                        item = Item.objects.get(item_id=item_id)
                        logger.info(f"   • {item.name} (ID: {item_id}, similarity: {similarity:.3f})")
                    except Item.DoesNotExist:
                        logger.warning(f"   • Item {item_id} not found (similarity: {similarity:.3f})")
            else:
                logger.warning(f"No results found for: {query}")
            logger.info("")

def main():
    """Main function to build the vector database."""
    builder = VectorDatabaseBuilder()
    
    try:
        # Build database
        success = builder.build_database()
        
        if success:
            # Test the database
            builder.test_search()
            logger.info("🎯 Vector database is ready for use!")
        else:
            logger.error("❌ Vector database build failed")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Build failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)