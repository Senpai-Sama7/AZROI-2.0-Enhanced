"""
Enhanced LLM Router with circuit breaker pattern and Redis caching.
Part of PHASE 03: CORE_ORCHESTRATION in the AI Architect system.
"""

import logging
import aioredis
import json
import os
import time
import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Union, Callable
import threading
from datetime import datetime, timedelta

# Import various LLM clients
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# Optional imports for additional providers
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern for LLM API calls.
    Helps prevent cascading failures when an LLM provider is experiencing issues.
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before attempting to close the circuit
            half_open_timeout: Time in seconds to wait in half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.lock = threading.RLock()
    
    def is_closed(self) -> bool:
        """Check if circuit is closed and requests can flow through."""
        with self.lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                # Check if it's time to try again
                if self.last_failure_time and time.time() - self.last_failure_time > self.reset_timeout:
                    logger.info("Circuit transitioning from OPEN to HALF-OPEN")
                    self.state = "HALF-OPEN"
                    return True
                return False
            
            if self.state == "HALF-OPEN":
                # In HALF-OPEN state, allow only one request through to test
                return True
                
            return False
    
    def record_success(self) -> None:
        """Record a successful API call."""
        with self.lock:
            if self.state == "HALF-OPEN":
                logger.info("Circuit successful in HALF-OPEN, closing circuit")
                self.state = "CLOSED"
                
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed API call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == "HALF-OPEN" or (self.state == "CLOSED" and self.failure_count >= self.failure_threshold):
                logger.warning(f"Circuit opening after {self.failure_count} failures")
                self.state = "OPEN"


class LLMRouter:
    """
    Routes LLM requests to the appropriate backend and manages caching.
    Enhanced with circuit breakers, fallback chains, and improved caching.
    """
    
    def __init__(
        self, 
        redis_url: str = "redis://localhost:6379", 
        default_model: str = "gpt-4-turbo",
        azure_config: Optional[Dict[str, str]] = None,
        cache_ttl: int = 3600,
    ):
        self.redis_url = redis_url
        self.default_model = default_model
        self.azure_config = azure_config
        self.cache_ttl = cache_ttl
        self.redis_client = None
        self.llm_clients = {}
        
        # Circuit breakers for each provider
        self.circuit_breakers = {
            "azure": CircuitBreaker(failure_threshold=3),
            "openai": CircuitBreaker(failure_threshold=3),
            "gemini": CircuitBreaker(failure_threshold=3),
            "anthropic": CircuitBreaker(failure_threshold=3),
            "local": CircuitBreaker(failure_threshold=3),
        }
        
        # Define fallback chains (order of provider preference)
        self.fallback_chains = {
            "azure": ["openai", "gemini", "anthropic", "local"],
            "openai": ["azure", "gemini", "anthropic", "local"],
            "gemini": ["azure", "openai", "anthropic", "local"],
            "anthropic": ["azure", "openai", "gemini", "local"],
            "local": ["azure", "openai", "gemini", "anthropic"],
        }
        
        # Map model names to provider
        self.model_to_provider = {
            "azure": "azure",
            "gpt-4-turbo": "openai",
            "gpt-4": "openai",
            "gpt-3.5-turbo": "openai",
            "gemini-pro": "gemini",
            "gemini-2.5-flash-preview-04-17": "gemini",
            "claude-3-opus": "anthropic",
            "claude-3-sonnet": "anthropic",
            "claude-instant": "anthropic",
            "llama3": "local",
            "mistral": "local",
        }
        
    async def initialize(self):
        """Initialize connections and LLM clients."""
        # Initialize Redis for caching
        self.redis_client = await aioredis.from_url(self.redis_url)
        
        # Initialize LLM clients
        await self._initialize_llm_clients()
    
    async def _initialize_llm_clients(self):
        """Initialize LLM clients based on available credentials."""
        # Check Azure OpenAI credentials
        if self.azure_config and all(self.azure_config.values()):
            try:
                logger.info("Initializing Azure OpenAI client")
                self.llm_clients["azure"] = AzureChatOpenAI(
                    openai_api_key=self.azure_config["azure_api_key"],
                    openai_api_base=self.azure_config["azure_api_base"],
                    openai_api_version=self.azure_config["azure_api_version"],
                    deployment_name=self.azure_config["azure_deployment_id"],
                    temperature=0,
                )
                # Set default model to Azure if available
                self.default_model = "azure"
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI client: {e}")
        
        # Check OpenAI credentials
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                self.llm_clients["gpt-4-turbo"] = ChatOpenAI(
                    model_name="gpt-4-turbo",
                    temperature=0,
                    openai_api_key=openai_api_key,
                )
                self.llm_clients["gpt-4"] = ChatOpenAI(
                    model_name="gpt-4",
                    temperature=0,
                    openai_api_key=openai_api_key,
                )
                self.llm_clients["gpt-3.5-turbo"] = ChatOpenAI(
                    model_name="gpt-3.5-turbo",
                    temperature=0,
                    openai_api_key=openai_api_key,
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Check Google API key for Gemini
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            try:
                genai.configure(api_key=google_api_key)
                self.llm_clients["gemini-pro"] = ChatGoogleGenerativeAI(
                    model="gemini-pro",
                    temperature=0,
                    google_api_key=google_api_key,
                )
                self.llm_clients["gemini-2.5-flash-preview-04-17"] = ChatGoogleGenerativeAI(
                    model="models/gemini-2.5-flash-preview-04-17",
                    temperature=0,
                    google_api_key=google_api_key,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Google Gemini client: {e}")
    
    def set_monitoring_system(self, monitoring_system):
        """
        Attach a monitoring system for metrics and logging.
        """
        self.monitoring_system = monitoring_system

    async def generate(
        self, 
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0,
        max_tokens: int = 1024,
        use_cache: bool = True,
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use cache
            
        Returns:
            Generated text response
        """
        model = model or self.default_model
        
        # Check if Redis is initialized
        if self.redis_client is None:
            await self.initialize()
        
        # Monitoring: record LLM API call
        if hasattr(self, 'monitoring_system') and self.monitoring_system:
            self.monitoring_system.record_event(
                event_type="llm_api_call",
                event_data={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
        
        # Try to get from cache if enabled
        if use_cache:
            cache_key = self._get_cache_key(messages, model, temperature, max_tokens)
            cached_response = await self.redis_client.get(cache_key)
            # Monitoring: record cache hit/miss
            if use_cache and hasattr(self, 'monitoring_system') and self.monitoring_system:
                if 'cached_response' in locals() and cached_response:
                    self.monitoring_system.record_event(event_type="cache_hit", event_data={"model": model})
                else:
                    self.monitoring_system.record_event(event_type="cache_miss", event_data={"model": model})
            if cached_response:
                return cached_response.decode('utf-8')
        
        # Route to appropriate model
        response = await self._route_request(messages, model, temperature, max_tokens)
        
        # Cache the response if caching is enabled
        if use_cache:
            await self.redis_client.set(
                cache_key, 
                response,
                ex=self.cache_ttl  # Cache expiration: configurable TTL
            )
        
        return response
    
    async def _route_request(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Route the request to the appropriate model."""
        provider = self.model_to_provider.get(model, None)
        if not provider:
            raise ValueError(f"Unknown model: {model}")
        
        circuit_breaker = self.circuit_breakers.get(provider, None)
        if not circuit_breaker:
            raise ValueError(f"No circuit breaker configured for provider: {provider}")
        
        if not circuit_breaker.is_closed():
            logger.warning(f"Circuit breaker for {provider} is OPEN, attempting fallback")
            fallback_chain = self.fallback_chains.get(provider, [])
            for fallback_provider in fallback_chain:
                fallback_circuit = self.circuit_breakers.get(fallback_provider, None)
                if fallback_circuit and fallback_circuit.is_closed():
                    model = next(
                        (m for m, p in self.model_to_provider.items() if p == fallback_provider),
                        None
                    )
                    if model:
                        logger.info(f"Falling back to provider: {fallback_provider}")
                        # Monitoring: record fallback event
                        if hasattr(self, 'monitoring_system') and self.monitoring_system:
                            self.monitoring_system.record_event(
                                event_type="fallback",
                                event_data={"from_provider": provider, "to_provider": fallback_provider}
                            )
                        return await self._route_request(messages, model, temperature, max_tokens)
            raise RuntimeError(f"All fallback providers for {provider} are unavailable")
        
        # Prioritize Azure OpenAI if that's the selected model
        if model == "azure" and "azure" in self.llm_clients:
            try:
                logger.info(f"Routing request to Azure OpenAI")
                # Convert to LangChain message format
                from langchain.schema import HumanMessage, SystemMessage, AIMessage
                lc_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        lc_messages.append(SystemMessage(content=msg["content"]))
                    elif msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))
                
                # Call the LLM
                response = await self.llm_clients["azure"].ainvoke(
                    lc_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                circuit_breaker.record_success()
                return response.content
            except Exception as e:
                logger.error(f"Azure OpenAI request failed: {e}")
                circuit_breaker.record_failure()
                # Fall back to another model
                fallback_chain = self.fallback_chains.get(provider, [])
                for fallback_provider in fallback_chain:
                    fallback_circuit = self.circuit_breakers.get(fallback_provider, None)
                    if fallback_circuit and fallback_circuit.is_closed():
                        model = next(
                            (m for m, p in self.model_to_provider.items() if p == fallback_provider),
                            None
                        )
                        if model:
                            logger.info(f"Falling back to provider: {fallback_provider}")
                            # Monitoring: record fallback event
                            if hasattr(self, 'monitoring_system') and self.monitoring_system:
                                self.monitoring_system.record_event(
                                    event_type="fallback",
                                    event_data={"from_provider": provider, "to_provider": fallback_provider}
                                )
                            return await self._route_request(messages, model, temperature, max_tokens)
                raise RuntimeError(f"All fallback providers for {provider} are unavailable")
        
        # Use the specified model if available
        if model in self.llm_clients:
            # Convert to appropriate format and call the model
            # Implementation depends on specific LLM client
            # ...
            pass  # Placeholder to satisfy indentation requirements

        # Fall back to default if model not available
        logger.warning(f"Model {model} not available, falling back to default")
        # Implement fallback logic
        pass
        
        raise NotImplementedError("LLM routing not fully implemented")
    
    async def close(self):
        """Close connections and clean up resources."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_cache_key(self, messages, model, temperature, max_tokens):
        """Generate a cache key from request parameters."""
        key_parts = [
            model,
            str(temperature),
            str(max_tokens),
            json.dumps(messages)
        ]
        return ":".join(key_parts)
