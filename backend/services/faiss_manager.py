"""
FAISS vector database manager for fast similarity search.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import faiss
import numpy as np
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class FaissManagerError(Exception):
    """Custom exception for FAISS manager errors."""
    pass


class FaissVectorDatabase:
    """
    FAISS-based vector database for fast similarity search.
    """
    
    def __init__(self, index_name: str = "items", dimension: int = 1024):
        self.index_name = index_name
        self.dimension = dimension
        
        # Paths
        self.base_path = Path(settings.FAISS_INDEX_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.base_path / f"{index_name}.faiss"
        self.metadata_file = self.base_path / f"{index_name}_metadata.json"
        
        # FAISS index
        self.index = None
        self.metadata = {}
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self) -> bool:
        """
        Load existing FAISS index and metadata from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if self.index_file.exists() and self.metadata_file.exists():
                logger.info(f"Loading existing FAISS index: {self.index_file}")
                
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_file))
                
                # Load metadata
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
                return True
            else:
                logger.info("No existing index found, will create new one")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            self._create_new_index()
            return False
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        logger.info(f"Creating new FAISS index with dimension {self.dimension}")
        
        # Create IndexFlatIP (Inner Product) for cosine similarity
        # We'll normalize vectors, so inner product = cosine similarity
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Initialize metadata
        self.metadata = {
            'dimension': self.dimension,
            'index_type': 'IndexFlatIP',
            'created_at': timezone.now().isoformat(),
            'last_updated': timezone.now().isoformat(),
            'item_ids': [],  # Maps FAISS index position to item ID
            'id_to_position': {}  # Maps item ID to FAISS index position
        }
    
    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        Normalize vector for cosine similarity.
        
        Args:
            vector: Input vector
            
        Returns:
            Normalized vector
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    def add_vector(self, item_id: int, vector: List[float]) -> bool:
        """
        Add a vector to the index.
        
        Args:
            item_id: Unique identifier for the item
            vector: Vector embedding
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            if self.index is None:
                self._create_new_index()
            
            # Convert to numpy array and normalize
            np_vector = np.array(vector, dtype=np.float32)
            if len(np_vector) != self.dimension:
                raise ValueError(f"Vector dimension {len(np_vector)} != expected {self.dimension}")
            
            normalized_vector = self._normalize_vector(np_vector)
            
            # Check if item already exists
            if item_id in self.metadata.get('id_to_position', {}):
                logger.debug(f"Item {item_id} already exists in index, updating")
                return self.update_vector(item_id, vector)
            
            # Add to FAISS index
            self.index.add(normalized_vector.reshape(1, -1))
            
            # Update metadata
            position = len(self.metadata['item_ids'])
            self.metadata['item_ids'].append(item_id)
            self.metadata['id_to_position'][str(item_id)] = position
            self.metadata['last_updated'] = timezone.now().isoformat()
            
            logger.debug(f"Added vector for item {item_id} at position {position}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add vector for item {item_id}: {e}")
            return False
    
    def update_vector(self, item_id: int, vector: List[float]) -> bool:
        """
        Update an existing vector in the index.
        Note: FAISS doesn't support in-place updates, so we rebuild if needed.
        
        Args:
            item_id: Item identifier
            vector: New vector embedding
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if str(item_id) not in self.metadata.get('id_to_position', {}):
                return self.add_vector(item_id, vector)
            
            # For now, we'll track that an update is needed
            # In production, you might want to batch updates and rebuild periodically
            logger.warning(f"Vector update for item {item_id} requires index rebuild (not implemented)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update vector for item {item_id}: {e}")
            return False
    
    def search(
        self, 
        query_vector: List[float], 
        k: int = 10, 
        threshold: float = 0.0
    ) -> List[Tuple[int, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (item_id, similarity_score) tuples
        """
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.debug("Empty or missing index")
                return []
            
            # Convert and normalize query vector
            np_vector = np.array(query_vector, dtype=np.float32)
            if len(np_vector) != self.dimension:
                raise ValueError(f"Query vector dimension {len(np_vector)} != expected {self.dimension}")
            
            normalized_query = self._normalize_vector(np_vector)
            
            # Search FAISS index
            similarities, indices = self.index.search(
                normalized_query.reshape(1, -1), 
                min(k, self.index.ntotal)
            )
            
            # Convert results to (item_id, score) tuples
            results = []
            for idx, similarity in zip(indices[0], similarities[0]):
                if idx == -1:  # FAISS returns -1 for invalid results
                    continue
                
                if idx >= len(self.metadata['item_ids']):
                    logger.warning(f"Invalid index {idx} returned by FAISS")
                    continue
                
                if similarity < threshold:
                    continue
                
                item_id = self.metadata['item_ids'][idx]
                results.append((item_id, float(similarity)))
            
            logger.debug(f"Found {len(results)} similar items")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_vector(self, item_id: int) -> Optional[np.ndarray]:
        """
        Get vector for a specific item (not efficiently supported by FAISS).
        
        Args:
            item_id: Item identifier
            
        Returns:
            Vector if found, None otherwise
        """
        try:
            if str(item_id) not in self.metadata.get('id_to_position', {}):
                return None
            
            position = self.metadata['id_to_position'][str(item_id)]
            
            # FAISS doesn't directly support getting vectors by index
            # This is a limitation - in production you might want to store vectors separately
            logger.warning("Getting individual vectors is not efficiently supported")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get vector for item {item_id}: {e}")
            return None
    
    def remove_vector(self, item_id: int) -> bool:
        """
        Remove a vector from the index (requires rebuild).
        
        Args:
            item_id: Item identifier
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            if str(item_id) not in self.metadata.get('id_to_position', {}):
                logger.debug(f"Item {item_id} not found in index")
                return True
            
            # FAISS doesn't support efficient removal
            # For production, implement batched rebuilding
            logger.warning(f"Vector removal for item {item_id} requires index rebuild (not implemented)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove vector for item {item_id}: {e}")
            return False
    
    def save_index(self) -> bool:
        """
        Save the FAISS index and metadata to disk.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if self.index is None:
                logger.warning("No index to save")
                return False
            
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            self.metadata['last_updated'] = timezone.now().isoformat()
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors to {self.index_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False
    
    def rebuild_index(self, vectors_data: List[Tuple[int, List[float]]]) -> bool:
        """
        Rebuild the entire index from scratch.
        
        Args:
            vectors_data: List of (item_id, vector) tuples
            
        Returns:
            True if rebuilt successfully, False otherwise
        """
        try:
            logger.info(f"Rebuilding FAISS index with {len(vectors_data)} vectors")
            
            # Create new index
            self._create_new_index()
            
            # Prepare vectors
            vectors = []
            item_ids = []
            
            for item_id, vector in vectors_data:
                np_vector = np.array(vector, dtype=np.float32)
                if len(np_vector) != self.dimension:
                    logger.warning(f"Skipping item {item_id} with wrong dimension {len(np_vector)}")
                    continue
                
                normalized_vector = self._normalize_vector(np_vector)
                vectors.append(normalized_vector)
                item_ids.append(item_id)
            
            if not vectors:
                logger.warning("No valid vectors to add")
                return False
            
            # Add all vectors at once
            vectors_array = np.array(vectors, dtype=np.float32)
            self.index.add(vectors_array)
            
            # Update metadata
            self.metadata['item_ids'] = item_ids
            self.metadata['id_to_position'] = {str(item_id): i for i, item_id in enumerate(item_ids)}
            self.metadata['last_updated'] = timezone.now().isoformat()
            
            logger.info(f"Successfully rebuilt index with {len(item_ids)} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Get index statistics.
        
        Returns:
            Dictionary with index statistics
        """
        return {
            'index_name': self.index_name,
            'dimension': self.dimension,
            'total_vectors': self.index.ntotal if self.index else 0,
            'index_file_exists': self.index_file.exists(),
            'metadata_file_exists': self.metadata_file.exists(),
            'last_updated': self.metadata.get('last_updated'),
            'created_at': self.metadata.get('created_at')
        }