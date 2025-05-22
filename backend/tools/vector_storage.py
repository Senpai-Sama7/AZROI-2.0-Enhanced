#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/tools/vector_storage.py

import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid

logger = logging.getLogger("ai-architect-backend.vector_storage")

class VectorStorage:
    """
    Vector storage implementation using Qdrant.
    This replaces ChromaDB with Qdrant for better performance and scalability.
    """
    
    def __init__(self, 
               collection_name: str = "ai_architect_memory",
               url: Optional[str] = None,
               path: Optional[str] = "./backend/vectorstore_data",
               vector_size: int = 1536):
        """
        Initialize the vector storage.
        
        Args:
            collection_name: Name of the collection to use.
            url: URL to a Qdrant server (if None, use local).
            path: Path for local Qdrant storage (ignored if url is provided).
            vector_size: Size of embedding vectors.
        """
        self.collection_name = collection_name
        self.url = url
        self.path = path
        self.vector_size = vector_size
        self.client = None
        self.initialized = False
        self.monitoring_system = None
    
    def set_monitoring_system(self, monitoring_system):
        """Set the monitoring system for tracking metrics."""
        self.monitoring_system = monitoring_system
    
    async def initialize(self):
        """
        Initialize the vector storage.
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            
            logger.info(f"Initializing Qdrant vector storage: {self.collection_name}")
            
            # Create client (local or remote)
            if self.url:
                self.client = QdrantClient(url=self.url)
                logger.info(f"Connected to Qdrant server at {self.url}")
            else:
                os.makedirs(self.path, exist_ok=True)
                self.client = QdrantClient(path=self.path)
                logger.info(f"Using local Qdrant at {self.path}")
            
            # Check if collection exists, create if not
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    )
                )
            
            self.initialized = True
            logger.info(f"Qdrant vector storage initialized: {self.collection_name}")
            
            # Update collection count metric
            if self.monitoring_system:
                await self._update_collection_metrics()
            
        except ImportError:
            logger.error("qdrant-client package not installed. Run 'pip install qdrant-client'")
            raise
        except Exception as e:
            logger.error(f"Error initializing Qdrant: {str(e)}")
            raise
    
    async def _update_collection_metrics(self):
        """Update metrics about the collection."""
        if not self.monitoring_system or not self.initialized:
            return
        
        try:
            info = self.client.get_collection(self.collection_name)
            count = info.points_count
            self.monitoring_system.update_vector_store_items(self.collection_name, count)
        except Exception as e:
            logger.error(f"Error updating collection metrics: {str(e)}")
    
    async def _get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for text.
        
        Args:
            text: Text to embed.
            
        Returns:
            List of embedding values.
        """
        try:
            # Use Google's embedding model via LangChain
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            # Initialize the embedding model
            embedding_model = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=os.environ.get("BACKEND_GEMINI_API_KEY"),
            )
            
            # Get the embedding
            embedding = await asyncio.to_thread(embedding_model.embed_query, text)
            return embedding
        
        except ImportError:
            logger.error("langchain-google-genai package not installed. Run 'pip install langchain-google-genai'")
            raise
        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}")
            
            # Fallback: Return a zero vector
            logger.warning("Using fallback zero embedding vector")
            return [0.0] * self.vector_size
    
    async def store(self, 
                  data: Dict[str, Any], 
                  metadata: Optional[Dict[str, Any]] = None,
                  doc_id: Optional[str] = None) -> str:
        """
        Store data in the vector storage.
        
        Args:
            data: Data to store.
            metadata: Additional metadata.
            doc_id: Optional document ID.
            
        Returns:
            Document ID.
        """
        if not self.initialized:
            await self.initialize()
        
        if self.monitoring_system:
            self.monitoring_system.record_vector_store_operation("store")
        
        try:
            from qdrant_client.http import models
            
            # Generate an ID if not provided
            doc_id = doc_id or str(uuid.uuid4())
            
            # Prepare payload
            payload = data.copy()
            if metadata:
                payload.update(metadata)
            
            # Make sure text_for_embedding exists
            text_for_embedding = payload.get("text_for_embedding")
            if not text_for_embedding:
                if "goal" in payload:
                    text_for_embedding = payload["goal"]
                elif "content" in payload:
                    text_for_embedding = payload["content"]
                else:
                    # Use a JSON representation of the whole object
                    text_for_embedding = json.dumps(payload)
                
                payload["text_for_embedding"] = text_for_embedding
            
            # Get embeddings for the text
            embedding = await self._get_embeddings(text_for_embedding)
            
            # Upsert into Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=doc_id,
                        payload=payload,
                        vector=embedding
                    )
                ]
            )
            
            logger.info(f"Stored document in vector storage: {doc_id}")
            
            # Update metrics
            if self.monitoring_system:
                await self._update_collection_metrics()
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            raise
    
    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID.
            
        Returns:
            Document data or None if not found.
        """
        if not self.initialized:
            await self.initialize()
        
        if self.monitoring_system:
            self.monitoring_system.record_vector_store_operation("get_by_id")
        
        try:
            # Retrieve from Qdrant
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id],
                with_vectors=False,
                with_payload=True
            )
            
            if not results:
                return None
            
            # Return the payload
            return results[0].payload
            
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {str(e)}")
            return None
    
    async def search(self, 
                   query: str, 
                   limit: int = 5, 
                   filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for documents by similarity.
        
        Args:
            query: Query text.
            limit: Maximum number of results.
            filter_dict: Optional filter.
            
        Returns:
            List of matching documents.
        """
        if not self.initialized:
            await self.initialize()
        
        if self.monitoring_system:
            self.monitoring_system.record_vector_store_operation("search")
        
        try:
            from qdrant_client.http import models
            
            # Get query embedding
            query_embedding = await self._get_embeddings(query)
            
            # Prepare filter if needed
            filter_obj = None
            if filter_dict:
                # Convert the filter dict to a Qdrant filter object
                # Basic implementation - this would need to be expanded for complex filters
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    ))
                
                filter_obj = models.Filter(
                    must=conditions
                )
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                filter=filter_obj
            )
            
            # Extract and return results
            results = []
            for result in search_results:
                doc = result.payload.copy()
                doc["_score"] = result.score
                doc["_id"] = result.id
                results.append(doc)
            
            logger.info(f"Search found {len(results)} matches for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            return []
    
    async def delete(self, doc_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: Document ID.
            
        Returns:
            True if deleted, False otherwise.
        """
        if not self.initialized:
            await self.initialize()
        
        if self.monitoring_system:
            self.monitoring_system.record_vector_store_operation("delete")
        
        try:
            # Delete from Qdrant
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[doc_id]
            )
            
            logger.info(f"Deleted document: {doc_id}")
            
            # Update metrics
            if self.monitoring_system:
                await self._update_collection_metrics()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return False
    
    async def list_documents(self, 
                         limit: int = 100, 
                         offset: int = 0,
                         filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List documents in the collection.
        
        Args:
            limit: Maximum number of results.
            offset: Offset for pagination.
            filter_dict: Optional filter.
            
        Returns:
            List of documents.
        """
        if not self.initialized:
            await self.initialize()
        
        if self.monitoring_system:
            self.monitoring_system.record_vector_store_operation("list")
        
        try:
            from qdrant_client.http import models
            
            # Prepare filter if needed
            filter_obj = None
            if filter_dict:
                # Convert the filter dict to a Qdrant filter object
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    ))
                
                filter_obj = models.Filter(
                    must=conditions
                )
            
            # Retrieve scrolled batch (Qdrant's version of pagination)
            scroll_results = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                filter=filter_obj,
                with_vectors=False,
                with_payload=True
            )
            
            # Extract results
            results = []
            for result in scroll_results[0]:
                doc = result.payload.copy()
                doc["_id"] = result.id
                results.append(doc)
            
            logger.info(f"Listed {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Collection information.
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Get collection info
            info = self.client.get_collection(self.collection_name)
            
            # Convert to dict
            info_dict = {
                "name": info.name,
                "points_count": info.points_count,
                "vectors_config": {
                    "size": info.config.params.vectors.size,
                    "distance": str(info.config.params.vectors.distance)
                },
                "status": "ready"
            }
            
            return info_dict
            
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {
                "name": self.collection_name,
                "status": "error",
                "error": str(e)
            }
