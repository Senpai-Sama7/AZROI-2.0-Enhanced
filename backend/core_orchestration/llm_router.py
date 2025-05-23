#!/usr/bin/env python3
"""
LLM Router with intelligent routing and load balancing
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import json
import random

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    MOCK = "mock"

class LLMRouter:
    """Intelligent LLM router with load balancing and fallback support"""
    
    def __init__(self, 
                 providers: Optional[Dict[str, Dict[str, Any]]] = None,
                 default_provider: str = "mock",
                 max_retries: int = 3,
                 timeout: float = 30.0):
        self.providers = providers or self._get_default_providers()
        self.default_provider = default_provider
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Provider health tracking
        self._provider_health = {name: True for name in self.providers.keys()}
        self._provider_metrics = {name: {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'avg_response_time': 0.0,
            'last_used': 0.0
        } for name in self.providers.keys()}
        
        # Request history
        self._request_history = []
        
        logger.info(f"LLMRouter initialized with providers: {list(self.providers.keys())}")
    
    def _get_default_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get default provider configurations"""
        return {
            "mock": {
                "type": "mock",
                "priority": 1,
                "weight": 1.0,
                "max_requests_per_minute": 1000,
                "config": {}
            },
            "local": {
                "type": "local",
                "priority": 2,
                "weight": 0.8,
                "max_requests_per_minute": 100,
                "config": {
                    "endpoint": "http://localhost:11434",
                    "model": "llama2"
                }
            }
        }
    
    async def route_request(self, 
                           prompt: str,
                           context: Optional[Dict[str, Any]] = None,
                           preferred_provider: Optional[str] = None,
                           temperature: float = 0.7,
                           max_tokens: int = 1000) -> Dict[str, Any]:
        """Route request to the best available LLM provider"""
        start_time = time.time()
        
        # Determine provider order
        provider_order = self._get_provider_order(preferred_provider)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            for provider_name in provider_order:
                if not self._provider_health[provider_name]:
                    continue
                
                try:
                    result = await self._call_provider(
                        provider_name,
                        prompt,
                        context,
                        temperature,
                        max_tokens
                    )
                    
                    # Update metrics on success
                    response_time = time.time() - start_time
                    self._update_provider_metrics(provider_name, True, response_time)
                    
                    # Record request
                    self._record_request(provider_name, prompt, result, response_time)
                    
                    return {
                        "success": True,
                        "provider": provider_name,
                        "response": result,
                        "response_time": response_time,
                        "attempt": attempt + 1
                    }
                    
                except Exception as e:
                    last_error = e
                    self._update_provider_metrics(provider_name, False, time.time() - start_time)
                    
                    # Mark provider unhealthy if multiple failures
                    if self._provider_metrics[provider_name]['failures'] > 3:
                        self._provider_health[provider_name] = False
                        logger.warning(f"Marking provider {provider_name} as unhealthy")
                    
                    logger.error(f"Provider {provider_name} failed: {e}")
                    continue
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All providers failed
        total_time = time.time() - start_time
        return {
            "success": False,
            "error": f"All providers failed. Last error: {str(last_error)}",
            "response_time": total_time,
            "attempts": self.max_retries
        }
    
    def _get_provider_order(self, preferred_provider: Optional[str]) -> List[str]:
        """Get ordered list of providers to try"""
        if preferred_provider and preferred_provider in self.providers:
            # Preferred provider first, then others by priority
            others = [p for p in self.providers.keys() if p != preferred_provider and self._provider_health[p]]
            others.sort(key=lambda p: (
                -self.providers[p].get("priority", 0),
                -self.providers[p].get("weight", 1.0),
                self._provider_metrics[p]['avg_response_time']
            ))
            return [preferred_provider] + others
        else:
            # Sort by health, priority, weight, and performance
            healthy_providers = [p for p in self.providers.keys() if self._provider_health[p]]
            healthy_providers.sort(key=lambda p: (
                -self.providers[p].get("priority", 0),
                -self.providers[p].get("weight", 1.0),
                self._provider_metrics[p]['avg_response_time']
            ))
            return healthy_providers
    
    async def _call_provider(self, 
                            provider_name: str,
                            prompt: str,
                            context: Optional[Dict[str, Any]],
                            temperature: float,
                            max_tokens: int) -> Dict[str, Any]:
        """Call specific LLM provider"""
        provider_config = self.providers[provider_name]
        provider_type = provider_config.get("type", "mock")
        
        if provider_type == "mock":
            return await self._call_mock_provider(prompt, context, temperature, max_tokens)
        elif provider_type == "local":
            return await self._call_local_provider(provider_config, prompt, context, temperature, max_tokens)
        elif provider_type == "openai":
            return await self._call_openai_provider(provider_config, prompt, context, temperature, max_tokens)
        elif provider_type == "anthropic":
            return await self._call_anthropic_provider(provider_config, prompt, context, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    async def _call_mock_provider(self, 
                                 prompt: str,
                                 context: Optional[Dict[str, Any]],
                                 temperature: float,
                                 max_tokens: int) -> Dict[str, Any]:
        """Mock provider for testing"""
        await asyncio.sleep(0.1)  # Simulate API call delay
        
        # Generate mock response based on prompt
        if "plan" in prompt.lower():
            response = {
                "response": f"Mock planning response for: {prompt[:50]}...",
                "type": "planning",
                "confidence": 0.8
            }
        elif "analyze" in prompt.lower():
            response = {
                "response": f"Mock analysis response for: {prompt[:50]}...",
                "type": "analysis",
                "confidence": 0.75
            }
        else:
            response = {
                "response": f"Mock response for: {prompt[:50]}...",
                "type": "general",
                "confidence": 0.7
            }
        
        if context:
            response["context_used"] = True
            response["context_summary"] = f"Used context with {len(context)} keys"
        
        return response
    
    async def _call_local_provider(self,
                                  provider_config: Dict[str, Any],
                                  prompt: str,
                                  context: Optional[Dict[str, Any]],
                                  temperature: float,
                                  max_tokens: int) -> Dict[str, Any]:
        """Call local LLM provider (e.g., Ollama)"""
        config = provider_config.get("config", {})
        endpoint = config.get("endpoint", "http://localhost:11434")
        model = config.get("model", "llama2")
        
        # Simulate local API call
        await asyncio.sleep(0.5)  # Simulate longer processing time
        
        return {
            "response": f"Local LLM response using {model}: {prompt[:50]}...",
            "model": model,
            "provider": "local",
            "endpoint": endpoint
        }
    
    async def _call_openai_provider(self,
                                   provider_config: Dict[str, Any],
                                   prompt: str,
                                   context: Optional[Dict[str, Any]],
                                   temperature: float,
                                   max_tokens: int) -> Dict[str, Any]:
        """Call OpenAI API (placeholder)"""
        # This would contain actual OpenAI API integration
        await asyncio.sleep(0.3)
        
        return {
            "response": f"OpenAI response: {prompt[:50]}...",
            "model": "gpt-3.5-turbo",
            "provider": "openai"
        }
    
    async def _call_anthropic_provider(self,
                                      provider_config: Dict[str, Any],
                                      prompt: str,
                                      context: Optional[Dict[str, Any]],
                                      temperature: float,
                                      max_tokens: int) -> Dict[str, Any]:
        """Call Anthropic API (placeholder)"""
        # This would contain actual Anthropic API integration
        await asyncio.sleep(0.4)
        
        return {
            "response": f"Anthropic response: {prompt[:50]}...",
            "model": "claude-3",
            "provider": "anthropic"
        }
    
    def _update_provider_metrics(self, provider_name: str, success: bool, response_time: float):
        """Update provider performance metrics"""
        metrics = self._provider_metrics[provider_name]
        metrics['requests'] += 1
        metrics['last_used'] = time.time()
        
        if success:
            metrics['successes'] += 1
        else:
            metrics['failures'] += 1
        
        # Update average response time
        total_requests = metrics['requests']
        current_avg = metrics['avg_response_time']
        metrics['avg_response_time'] = (current_avg * (total_requests - 1) + response_time) / total_requests
    
    def _record_request(self, provider_name: str, prompt: str, response: Dict[str, Any], response_time: float):
        """Record request in history"""
        self._request_history.append({
            'timestamp': time.time(),
            'provider': provider_name,
            'prompt_length': len(prompt),
            'response_time': response_time,
            'success': True
        })
        
        # Keep only recent history
        if len(self._request_history) > 1000:
            self._request_history = self._request_history[-500:]
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return {
            'provider_health': self._provider_health.copy(),
            'provider_metrics': self._provider_metrics.copy(),
            'total_requests': len(self._request_history),
            'providers_configured': list(self.providers.keys())
        }
    
    def reset_provider_health(self, provider_name: Optional[str] = None):
        """Reset provider health status"""
        if provider_name:
            if provider_name in self._provider_health:
                self._provider_health[provider_name] = True
                logger.info(f"Reset health for provider: {provider_name}")
        else:
            for name in self._provider_health:
                self._provider_health[name] = True
            logger.info("Reset health for all providers")
    
    def add_provider(self, name: str, config: Dict[str, Any]):
        """Add new provider configuration"""
        self.providers[name] = config
        self._provider_health[name] = True
        self._provider_metrics[name] = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'avg_response_time': 0.0,
            'last_used': 0.0
        }
        logger.info(f"Added provider: {name}")
    
    def remove_provider(self, name: str):
        """Remove provider configuration"""
        if name in self.providers:
            del self.providers[name]
            del self._provider_health[name]
            del self._provider_metrics[name]
            logger.info(f"Removed provider: {name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all providers"""
        results = {}
        
        for provider_name in self.providers.keys():
            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    self._call_provider(provider_name, "health check", None, 0.1, 10),
                    timeout=5.0
                )
                response_time = time.time() - start_time
                
                results[provider_name] = {
                    'healthy': True,
                    'response_time': response_time,
                    'last_check': time.time()
                }
                
                self._provider_health[provider_name] = True
                
            except Exception as e:
                results[provider_name] = {
                    'healthy': False,
                    'error': str(e),
                    'last_check': time.time()
                }
                
                self._provider_health[provider_name] = False
        
        return results
