"""
Embedding service for generating vector embeddings using Ollama.
"""

import asyncio
import hashlib
import logging
from typing import List, Optional, Tuple
import numpy as np
import ollama
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Custom exception for embedding service errors."""
    pass


class OllamaEmbeddingService:
    """
    Service for generating embeddings using Ollama with snowflake-arctic-embed2.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = getattr(settings, 'EMBEDDING_MODEL', 'snowflake-arctic-embed2:latest')
        self.client = ollama.Client(host=self.base_url)
        
    async def _ensure_model_available(self) -> bool:
        """
        Ensure the embedding model is available in Ollama.
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            # Check if model is already pulled
            models = await asyncio.get_event_loop().run_in_executor(
                None, self.client.list
            )
            
            model_names = [model.model for model in models.models] if hasattr(models, 'models') else []
            
            if self.model_name not in model_names:
                logger.info(f"Model {self.model_name} not found. Attempting to pull...")
                
                # Pull the model
                await asyncio.get_event_loop().run_in_executor(
                    None, self.client.pull, self.model_name
                )
                
                logger.info(f"Successfully pulled model {self.model_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure model availability: {e}")
            return False
    
    async def generate_embedding(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """
        Generate embedding for a given text.
        
        Args:
            text: Text to generate embedding for
            use_cache: Whether to use Redis cache for embeddings
            
        Returns:
            List of floats representing the embedding vector, or None if failed
        """
        if not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        # Create cache key
        cache_key = None
        if use_cache:
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            cache_key = f"embedding:{self.model_name}:{text_hash}"
            
            # Check cache first
            cached_embedding = cache.get(cache_key)
            if cached_embedding:
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return cached_embedding
        
        # Ensure model is available
        if not await self._ensure_model_available():
            raise EmbeddingServiceError(f"Model {self.model_name} is not available")
        
        try:
            logger.debug(f"Generating embedding for text: {text[:100]}...")
            
            # Generate embedding using Ollama
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.embeddings(
                    model=self.model_name,
                    prompt=text
                )
            )
            
            if 'embedding' not in response:
                raise EmbeddingServiceError("No embedding in response")
            
            embedding = response['embedding']
            
            # Cache the result
            if use_cache and cache_key:
                cache.set(cache_key, embedding, timeout=86400)  # 24 hours
                logger.debug(f"Cached embedding for text: {text[:50]}...")
            
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingServiceError(f"Embedding generation failed: {e}")
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 10, 
        use_cache: bool = True
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts to process concurrently
            use_cache: Whether to use Redis cache
            
        Returns:
            List of embedding vectors (or None for failed embeddings)
        """
        logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}: texts {i+1}-{min(i+batch_size, len(texts))}")
            
            # Create tasks for this batch
            tasks = [
                self.generate_embedding(text, use_cache=use_cache) 
                for text in batch
            ]
            
            try:
                # Execute batch concurrently
                batch_embeddings = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for j, (text, embedding) in enumerate(zip(batch, batch_embeddings)):
                    if isinstance(embedding, Exception):
                        logger.warning(f"Failed to embed text {i+j+1}: {embedding}")
                        all_embeddings.append(None)
                    else:
                        all_embeddings.append(embedding)
                
                # Small delay between batches to avoid overwhelming Ollama
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in batch {i//batch_size + 1}: {e}")
                # Add None for failed batch
                all_embeddings.extend([None] * len(batch))
        
        successful_count = sum(1 for emb in all_embeddings if emb is not None)
        logger.info(f"Generated {successful_count}/{len(texts)} embeddings successfully")
        
        return all_embeddings
    
    def calculate_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure result is between 0 and 1
            return float(max(0.0, min(1.0, similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def generate_item_embedding(self, item_id: int, text: str) -> Optional[List[float]]:
        """
        Generate and store embedding for an item.
        
        Args:
            item_id: ID of the item
            text: Text to generate embedding for (item name + description)
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Generate embedding
            embedding = await self.generate_embedding(text, use_cache=True)
            
            if embedding:
                # Store in database or file system for FAISS indexing
                # For now, we'll rely on the cache for storage
                logger.debug(f"Generated embedding for item {item_id}: {text[:50]}...")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate item embedding for {item_id}: {e}")
            return None
    
    async def build_search_index(self) -> bool:
        """
        Build FAISS search index from stored embeddings.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # For now, this is a placeholder since we're using cache-based storage
            # In a full implementation, this would build a FAISS index from all embeddings
            logger.info("FAISS index building completed (placeholder implementation)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build search index: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if the embedding service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test with a simple text
            test_embedding = await self.generate_embedding("test", use_cache=False)
            return test_embedding is not None and len(test_embedding) > 0
            
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False


# Synchronous wrapper for compatibility
class SyncOllamaEmbeddingService:
    """
    Synchronous wrapper for OllamaEmbeddingService.
    """
    
    def __init__(self):
        self.async_service = OllamaEmbeddingService()
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create new loop in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)
    
    def generate_embedding(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """Sync version of generate_embedding."""
        return self._run_async(
            self.async_service.generate_embedding(text, use_cache=use_cache)
        )
    
    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 10, 
        use_cache: bool = True
    ) -> List[Optional[List[float]]]:
        """Sync version of generate_embeddings_batch."""
        return self._run_async(
            self.async_service.generate_embeddings_batch(texts, batch_size, use_cache)
        )
    
    def calculate_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity (synchronous)."""
        return self.async_service.calculate_similarity(embedding1, embedding2)
    
    def health_check(self) -> bool:
        """Sync version of health_check."""
        return self._run_async(self.async_service.health_check())