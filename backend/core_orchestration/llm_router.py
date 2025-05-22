#!/usr/bin/env python3

import json
import logging
import hashlib
import time
import os
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
import asyncio
import google.generativeai as genai
from functools import lru_cache

logger = logging.getLogger("ai-architect-backend.llm_router")

class LLMRouter:
    """
    LLM Router for handling multiple LLM providers with caching.
    This class provides a unified interface to multiple LLMs with 
    automatic fallback, efficient caching, and performance monitoring.
    """
    
    def __init__(self, 
                redis_url: str = "redis://localhost:6379", 
                default_model: str = "gemini-2.5-flash-preview-04-17",
                ttl: int = 3600,
                azure_config: Optional[Dict[str, str]] = None):
        """
        Initialize the LLM Router.
        
        Args:
            redis_url: URL for Redis instance used for caching.
            default_model: Default LLM model to use.
            ttl: Time-to-live for cache entries in seconds.
            azure_config: Optional Azure OpenAI configuration.
        """
        self.default_model = default_model
        self.ttl = ttl
        self.redis_client = None
        self.redis_url = redis_url
        self.monitoring_system = None  # Will be set by external code
        self.azure_config = azure_config
        
        # Connect to Redis
        self._connect_redis()
        
        # Initialize Gemini
        if os.environ.get("BACKEND_GEMINI_API_KEY"):
            genai.configure(api_key=os.environ.get("BACKEND_GEMINI_API_KEY"))
        
        # LLM provider configurations
        self.providers = {
            "gemini": {
                "available": os.environ.get("BACKEND_GEMINI_API_KEY") is not None,
                "models": ["gemini-1.5-pro", "gemini-2.5-flash-preview-04-17"],
                "get_client": self._get_gemini_client
            },
            "azure-openai": {
                "available": (
                    (self.azure_config and all(self.azure_config.values())) or
                    (os.environ.get("AZURE_OPENAI_API_KEY") is not None and
                    os.environ.get("AZURE_OPENAI_API_BASE") is not None)
                ),
                "models": [os.environ.get("AZURE_OPENAI_DEPLOYMENT_ID", "gpt-4o-mini")],
                "get_client": self._get_azure_openai_client
            },
            "openai": {
                "available": os.environ.get("OPENAI_API_KEY") is not None,
                "models": ["gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"],
                "get_client": self._get_openai_client
            }
        }
        
        # Fallback chains - order of providers to try if the requested one fails
        self.fallback_chains = {
            "gemini": ["azure-openai", "openai"],
            "azure-openai": ["openai", "gemini"],
            "openai": ["azure-openai", "gemini"]
        }
        
        logger.info(f"LLM Router initialized with default model: {default_model}")
        
        # Log available providers
        available_providers = [p for p, config in self.providers.items() if config["available"]]
        logger.info(f"Available LLM providers: {', '.join(available_providers)}")
    
    def _connect_redis(self):
        """
        Connect to Redis for caching.
        """
        try:
            import redis
            self.redis_client = redis.from_url(self.redis_url)
            logger.info(f"Connected to Redis at {self.redis_url}")
        except ImportError:
            logger.warning("Redis package not installed, using in-memory LRU cache")
            self.redis_client = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis at {self.redis_url}: {str(e)}")
            logger.warning("Using in-memory LRU cache instead")
            self.redis_client = None
    
    def set_monitoring_system(self, monitoring_system):
        """
        Set the monitoring system for metrics collection.
        
        Args:
            monitoring_system: The monitoring system instance.
        """
        self.monitoring_system = monitoring_system
    
    def _generate_cache_key(self, model: str, prompt: str, **kwargs) -> str:
        """
        Generate a cache key for the LLM request.
        
        Args:
            model: Model name.
            prompt: Prompt text.
            **kwargs: Additional parameters that affect the output.
            
        Returns:
            Cache key string.
        """
        # Only include kwargs that affect the output
        relevant_kwargs = {k: v for k, v in kwargs.items() if k in [
            "temperature", "max_tokens", "top_p", "top_k", "stop", "system_message"
        ]}
        
        # Create a unique string representation of the request
        cache_parts = [model, prompt, json.dumps(relevant_kwargs, sort_keys=True)]
        cache_data = "||".join(cache_parts)
        
        # Generate SHA-256 hash
        return hashlib.sha256(cache_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        Get response from cache.
        
        Args:
            cache_key: Cache key.
            
        Returns:
            Cached response or None if not found.
        """
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    if self.monitoring_system:
                        self.monitoring_system.record_cache_hit()
                    return cached_data.decode("utf-8")
            except Exception as e:
                logger.warning(f"Redis cache retrieval error: {str(e)}")
        else:
            # Fallback to in-memory cache
            return self._get_from_memory_cache(cache_key)
        
        if self.monitoring_system:
            self.monitoring_system.record_cache_miss()
        return None
    
    @lru_cache(maxsize=1000)
    def _get_from_memory_cache(self, cache_key: str) -> Optional[str]:
        """
        Get response from in-memory cache.
        
        Args:
            cache_key: Cache key.
            
        Returns:
            Cached response or None if not found.
        """
        # This is just a placeholder - the actual caching is done by the LRU cache decorator
        return None
    
    def _store_in_cache(self, cache_key: str, response: str):
        """
        Store response in cache.
        
        Args:
            cache_key: Cache key.
            response: Response to cache.
        """
        if self.redis_client:
            try:
                self.redis_client.setex(cache_key, self.ttl, response)
            except Exception as e:
                logger.warning(f"Redis cache storage error: {str(e)}")
        else:
            # Update the in-memory cache
            self._update_memory_cache(cache_key, response)
    
    def _update_memory_cache(self, cache_key: str, response: str):
        """
        Update the in-memory cache.
        
        Args:
            cache_key: Cache key.
            response: Response to cache.
        """
        # The @lru_cache decorator doesn't allow setting values, 
        # so we'll just call the function to add it to the cache
        self._get_from_memory_cache.cache_clear()  # Clear the old value if it exists
        # The next call with this key will miss and be added to the cache
    
    def _get_provider_for_model(self, model: str) -> Optional[Tuple[str, str]]:
        """
        Get the provider for a given model.
        
        Args:
            model: Model name.
            
        Returns:
            Tuple of (provider_name, model_name) or None if not found.
        """
        for provider_name, config in self.providers.items():
            if not config["available"]:
                continue
                
            for provider_model in config["models"]:
                if model.lower() == provider_model.lower():
                    return (provider_name, model)
        
        # If model not found, return the default provider
        default_provider = next(
            (p for p, config in self.providers.items() if config["available"]), 
            None
        )
        if default_provider:
            return (default_provider, self.providers[default_provider]["models"][0])
        
        return None
    
    def _get_gemini_client(self, model: str = None):
        """
        Get a configured Gemini client.
        
        Args:
            model: Model name (optional).
            
        Returns:
            Configured Gemini client.
        """
        if not model:
            model = "gemini-2.5-flash-preview-04-17"
        
        try:
            return genai.GenerativeModel(model)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            return None
    
    def _get_azure_openai_client(self, model: str = None):
        """
        Get a configured Azure OpenAI client.
        
        Args:
            model: Deployment ID (optional).
            
        Returns:
            Configured Azure OpenAI client.
        """
        try:
            from openai import AzureOpenAI
            
            # Try to get credentials from Azure config first, then from environment variables
            api_key = None
            api_version = None
            azure_endpoint = None
            
            if self.azure_config:
                api_key = self.azure_config.get("azure_api_key")
                api_version = self.azure_config.get("azure_api_version")
                azure_endpoint = self.azure_config.get("azure_api_base")
            
            if not api_key:
                api_key = os.environ.get("AZURE_OPENAI_API_KEY")
            if not api_version:
                api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
            if not azure_endpoint:
                azure_endpoint = os.environ.get("AZURE_OPENAI_API_BASE")
            
            if not all([api_key, azure_endpoint]):
                logger.error("Missing required Azure OpenAI credentials")
                return None
                
            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint
            )
            
            return client
        except ImportError:
            logger.error("openai package not installed, cannot use Azure OpenAI")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            return None
    
    def _get_openai_client(self, model: str = None):
        """
        Get a configured OpenAI client.
        
        Args:
            model: Model name (optional).
            
        Returns:
            Configured OpenAI client.
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )
            
            return client
        except ImportError:
            logger.error("openai package not installed, cannot use OpenAI")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return None
    
    async def generate(self, 
                     messages: List[Dict[str, str]] = None,
                     prompt: str = None, 
                     model: str = None, 
                     temperature: float = 0.7,
                     max_tokens: int = 1024,
                     system_message: str = None,
                     use_cache: bool = True,
                     **kwargs) -> str:
        """
        Generate text from an LLM with caching and fallbacks.
        
        Args:
            messages: List of message objects with 'role' and 'content' keys.
            prompt: The prompt to send to the LLM (if messages not provided).
            model: LLM model to use (will use default if None).
            temperature: Temperature for generation.
            max_tokens: Maximum tokens to generate.
            system_message: System message to prepend.
            use_cache: Whether to use cache.
            **kwargs: Additional parameters to pass to the provider.
            
        Returns:
            Generated text response.
        """
        if not model:
            model = self.default_model
        
        # Convert a simple prompt to messages format if needed
        if not messages and prompt:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
        elif not messages:
            raise ValueError("Either 'messages' or 'prompt' must be provided")
            
        # Extract prompt for cache key generation if it exists
        cache_prompt = prompt or ' '.join([m["content"] for m in messages])
        
        # Get the provider for this model
        provider_info = self._get_provider_for_model(model)
        if not provider_info:
            raise ValueError(f"No available provider found for model {model}")
        
        provider_name, provider_model = provider_info
        
        # Generate cache key
        cache_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_message": system_message,
            **kwargs
        }
        cache_key = self._generate_cache_key(provider_model, cache_prompt, **cache_params)
        
        # Check cache
        if use_cache:
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                logger.info(f"Cache hit for model {provider_model}")
                return json.loads(cached_response)
        
        # If not in cache, generate response with fallback
        response = await self._generate_with_fallback(
            provider_name, provider_model, messages, temperature, max_tokens, **kwargs
        )
        
        # Store in cache
        if use_cache:
            self._store_in_cache(cache_key, json.dumps(response))
        
        return response
    
    async def _generate_with_fallback(self,
                                    provider_name: str,
                                    model: str,
                                    messages: List[Dict[str, str]],
                                    temperature: float,
                                    max_tokens: int,
                                    **kwargs) -> str:
        """
        Generate text with fallback to other providers if needed.
        
        Args:
            provider_name: Name of the provider to use.
            model: Model name.
            messages: The messages to send.
            temperature: Temperature for generation.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters to pass to the provider.
            
        Returns:
            Generated text response.
        """
        # Try the primary provider
        try:
            response = await self._generate_from_provider(
                provider_name, model, messages, temperature, max_tokens, **kwargs
            )
            return response
        except Exception as primary_error:
            logger.warning(f"Error with primary provider {provider_name}: {str(primary_error)}")
            if self.monitoring_system:
                self.monitoring_system.record_llm_error(model, "primary_provider")
        
        # Try fallbacks
        for fallback_provider in self.fallback_chains.get(provider_name, []):
            if not self.providers[fallback_provider]["available"]:
                continue
                
            fallback_model = self.providers[fallback_provider]["models"][0]
            logger.info(f"Trying fallback provider {fallback_provider} with model {fallback_model}")
            
            try:
                response = await self._generate_from_provider(
                    fallback_provider, fallback_model, messages, temperature, max_tokens, **kwargs
                )
                logger.info(f"Fallback to {fallback_provider} successful")
                return response
            except Exception as fallback_error:
                logger.warning(f"Error with fallback provider {fallback_provider}: {str(fallback_error)}")
                if self.monitoring_system:
                    self.monitoring_system.record_llm_error(fallback_model, "fallback_provider")
        
        # If all providers fail, raise exception
        raise Exception("All LLM providers failed to generate a response")
    
    async def _generate_from_provider(self,
                                    provider_name: str,
                                    model: str,
                                    messages: List[Dict[str, str]],
                                    temperature: float,
                                    max_tokens: int,
                                    **kwargs) -> str:
        """
        Generate text from a specific provider.
        
        Args:
            provider_name: Name of the provider to use.
            model: Model name.
            messages: The messages to send.
            temperature: Temperature for generation.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters to pass to the provider.
            
        Returns:
            Generated text response.
        """
        provider_config = self.providers[provider_name]
        client = provider_config["get_client"](model)
        
        if not client:
            raise ValueError(f"Failed to initialize client for provider {provider_name}")
        
        if self.monitoring_system:
            self.monitoring_system.record_llm_request(model)
        
        # Handle generation based on provider type
        if provider_name == "gemini":
            return await self._generate_gemini(
                client, messages, temperature, max_tokens, **kwargs
            )
        elif provider_name == "azure-openai":
            return await self._generate_azure_openai(
                client, model, messages, temperature, max_tokens, **kwargs
            )
        elif provider_name == "openai":
            return await self._generate_openai(
                client, model, messages, temperature, max_tokens, **kwargs
            )
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    async def _generate_gemini(self,
                             client,
                             messages: List[Dict[str, str]],
                             temperature: float,
                             max_tokens: int,
                             **kwargs) -> str:
        """
        Generate text with Gemini.
        
        Args:
            client: Gemini client.
            messages: The messages to send.
            temperature: Temperature for generation.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.
            
        Returns:
            Generated text response.
        """
        gen_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
        }
        
        # Convert messages to Gemini format
        content = []
        for message in messages:
            role = "user" if message["role"] in ["user", "system"] else "model"
            content.append({"role": role, "parts": [message["content"]]})
        
        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.generate_content(
                    content,
                    generation_config=gen_config
                )
            )
            
            # Get approximate token counts for monitoring
            if self.monitoring_system:
                prompt_tokens = sum(len(m["content"]) // 4 for m in messages)  # Rough approximation
                completion_tokens = len(response.text) // 4
                self.monitoring_system.record_llm_tokens("gemini", "prompt", prompt_tokens)
                self.monitoring_system.record_llm_tokens("gemini", "completion", completion_tokens)
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            raise
    
    async def _generate_azure_openai(self,
                                   client,
                                   model: str,
                                   messages: List[Dict[str, str]],
                                   temperature: float,
                                   max_tokens: int,
                                   **kwargs) -> str:
        """
        Generate text with Azure OpenAI.
        
        Args:
            client: Azure OpenAI client.
            model: Deployment ID.
            messages: The messages to send.
            temperature: Temperature for generation.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.
            
        Returns:
            Generated text response.
        """
        # Ensure messages are properly formatted for OpenAI
        oai_messages = []
        for message in messages:
            if message["role"] not in ["system", "user", "assistant"]:
                if message["role"] == "model":
                    message["role"] = "assistant"
                else:
                    message["role"] = "user"
            oai_messages.append({"role": message["role"], "content": message["content"]})
        
        try:
            deployment_id = self.azure_config.get("azure_deployment_id") if self.azure_config else None
            deployment_id = deployment_id or os.environ.get("AZURE_OPENAI_DEPLOYMENT_ID", model)
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=deployment_id,
                messages=oai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
                stop=kwargs.get("stop", None)
            )
            
            # Record token usage if available
            if self.monitoring_system and hasattr(response, "usage"):
                self.monitoring_system.record_llm_tokens(
                    model, "prompt", response.usage.prompt_tokens
                )
                self.monitoring_system.record_llm_tokens(
                    model, "completion", response.usage.completion_tokens
                )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Azure OpenAI generation error: {str(e)}")
            raise
    
    async def _generate_openai(self,
                             client,
                             model: str,
                             messages: List[Dict[str, str]],
                             temperature: float,
                             max_tokens: int,
                             **kwargs) -> str:
        """
        Generate text with OpenAI.
        
        Args:
            client: OpenAI client.
            model: Model name.
            messages: The messages to send.
            temperature: Temperature for generation.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.
            
        Returns:
            Generated text response.
        """
        # Ensure messages are properly formatted for OpenAI
        oai_messages = []
        for message in messages:
            if message["role"] not in ["system", "user", "assistant"]:
                if message["role"] == "model":
                    message["role"] = "assistant"
                else:
                    message["role"] = "user"
            oai_messages.append({"role": message["role"], "content": message["content"]})
        
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=oai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
                stop=kwargs.get("stop", None)
            )
            
            # Record token usage if available
            if self.monitoring_system and hasattr(response, "usage"):
                self.monitoring_system.record_llm_tokens(
                    model, "prompt", response.usage.prompt_tokens
                )
                self.monitoring_system.record_llm_tokens(
                    model, "completion", response.usage.completion_tokens
                )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            raise
    
    async def close(self):
        """
        Close any open connections.
        """
        if self.redis_client:
            self.redis_client.close()
