import logging
import aioredis
import json
import os
from typing import List, Dict, Any, Optional, Union

# Import various LLM clients
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

class LLMRouter:
    """
    Routes LLM requests to the appropriate backend and manages caching.
    Now enhanced with Azure OpenAI support.
    """
    
    def __init__(
        self, 
        redis_url: str = "redis://localhost:6379", 
        default_model: str = "gpt-4-turbo",
        azure_config: Optional[Dict[str, str]] = None,
    ):
        self.redis_url = redis_url
        self.default_model = default_model
        self.azure_config = azure_config
        self.redis_client = None
        self.llm_clients = {}
        
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
        
        # Try to get from cache if enabled
        if use_cache:
            cache_key = self._get_cache_key(messages, model, temperature, max_tokens)
            cached_response = await self.redis_client.get(cache_key)
            if cached_response:
                return cached_response.decode('utf-8')
        
        # Route to appropriate model
        response = await self._route_request(messages, model, temperature, max_tokens)
        
        # Cache the response if caching is enabled
        if use_cache:
            await self.redis_client.set(
                cache_key, 
                response,
                ex=3600  # Cache expiration: 1 hour
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
                return response.content
            except Exception as e:
                logger.error(f"Azure OpenAI request failed: {e}")
                # Fall back to another model
                if "gpt-4-turbo" in self.llm_clients:
                    model = "gpt-4-turbo"
                elif "gemini-pro" in self.llm_clients:
                    model = "gemini-pro"
                else:
                    raise RuntimeError("No available LLM clients to fall back to")
        
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
