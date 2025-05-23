#!/usr/bin/env python3
"""
Enhanced API Tester Agent with proper fallback handling
"""

import logging
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union
import socket
import urllib.parse
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class APITesterAgent:
    """Enhanced API testing agent with built-in HTTP support"""
    
    def __init__(self, timeout: int = 30, max_concurrent: int = 10):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.request_history = []
        
        logger.info(f"APITesterAgent initialized (timeout: {timeout}s, max_concurrent: {max_concurrent})")
    
    async def test_endpoint(self, 
                           url: str, 
                           method: str = "GET",
                           data: Optional[Union[Dict, str]] = None,
                           headers: Optional[Dict[str, str]] = None,
                           params: Optional[Dict[str, str]] = None,
                           timeout: Optional[int] = None) -> Dict[str, Any]:
        """Test a single API endpoint"""
        start_time = time.time()
        timeout = timeout or self.timeout
        
        try:
            # Build URL with parameters
            if params:
                url_parts = urllib.parse.urlparse(url)
                query = urllib.parse.urlencode(params)
                if url_parts.query:
                    query = url_parts.query + "&" + query
                url = urllib.parse.urlunparse((
                    url_parts.scheme, url_parts.netloc, url_parts.path,
                    url_parts.params, query, url_parts.fragment
                ))
            
            # Prepare request data
            request_data = None
            if data:
                if isinstance(data, dict):
                    request_data = json.dumps(data).encode('utf-8')
                    if not headers:
                        headers = {}
                    headers['Content-Type'] = 'application/json'
                else:
                    request_data = data.encode('utf-8') if isinstance(data, str) else data
            
            # Create request
            req = urllib.request.Request(url, data=request_data, method=method.upper())
            
            # Add headers
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            
            # Execute request in thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=timeout)
            )
            
            response_time = time.time() - start_time
            
            # Read response
            response_data = response.read()
            response_text = response_data.decode('utf-8', errors='ignore')
            
            # Try to parse as JSON
            try:
                response_body = json.loads(response_text)
                body_format = 'json'
            except (json.JSONDecodeError, ValueError):
                response_body = response_text
                body_format = 'text'
            
            result = {
                'status_code': response.getcode(),
                'response_time': response_time,
                'headers': dict(response.headers),
                'success': 200 <= response.getcode() < 300,
                'url': url,
                'method': method.upper(),
                'body': response_body,
                'body_format': body_format
            }
            
            # Record in history
            self._record_request(url, method, start_time, response_time, response.getcode(), result['success'])
            
            return result
            
        except urllib.error.HTTPError as e:
            response_time = time.time() - start_time
            try:
                error_body = e.read().decode('utf-8', errors='ignore')
            except:
                error_body = str(e)
            
            result = {
                'status_code': e.code,
                'response_time': response_time,
                'headers': dict(e.headers) if e.headers else {},
                'success': False,
                'url': url,
                'method': method.upper(),
                'body': error_body,
                'body_format': 'text',
                'error': f'HTTP {e.code}: {e.reason}'
            }
            
            self._record_request(url, method, start_time, response_time, e.code, False)
            return result
            
        except urllib.error.URLError as e:
            response_time = time.time() - start_time
            return self._create_error_result(url, method, f'URL Error: {str(e)}', response_time)
        
        except socket.timeout:
            return self._create_error_result(url, method, 'Request timeout', timeout)
        
        except Exception as e:
            response_time = time.time() - start_time
            error_type = type(e).__name__
            return self._create_error_result(url, method, f'{error_type}: {str(e)}', response_time)
    
    def _create_error_result(self, url: str, method: str, error: str, response_time: float) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'error': error,
            'response_time': response_time,
            'success': False,
            'url': url,
            'method': method.upper()
        }
    
    def _record_request(self, url: str, method: str, start_time: float, response_time: float, status_code: int, success: bool):
        """Record request in history"""
        self.request_history.append({
            'url': url,
            'method': method,
            'timestamp': start_time,
            'response_time': response_time,
            'status_code': status_code,
            'success': success
        })
    
    async def batch_test(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Test multiple endpoints concurrently"""
        logger.info(f"Batch testing {len(endpoints)} endpoints")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def test_with_semaphore(endpoint):
            async with semaphore:
                return await self.test_endpoint(
                    url=endpoint["url"],
                    method=endpoint.get("method", "GET"),
                    data=endpoint.get("data"),
                    headers=endpoint.get("headers"),
                    params=endpoint.get("params"),
                    timeout=endpoint.get("timeout")
                )
        
        # Execute all tests concurrently
        tasks = [test_with_semaphore(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'url': endpoints[i].get('url', 'unknown'),
                    'method': endpoints[i].get('method', 'GET')
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def test_api_availability(self, base_url: str) -> Dict[str, Any]:
        """Test if an API is available and responding"""
        logger.info(f"Testing API availability: {base_url}")
        
        url_parts = urllib.parse.urlparse(base_url)
        host = url_parts.netloc.split(':')[0]
        
        result = {
            "base_url": base_url,
            "available": False,
            "dns_resolution": False,
            "http_response": False,
            "response_time": None,
            "error": None
        }
        
        # Check DNS resolution
        try:
            await asyncio.get_event_loop().run_in_executor(None, socket.gethostbyname, host)
            result["dns_resolution"] = True
        except socket.gaierror as e:
            result["error"] = f"DNS resolution failed: {str(e)}"
            return result
        
        # Test HTTP response
        try:
            response = await self.test_endpoint(base_url, timeout=10)
            result["http_response"] = True
            result["response_time"] = response.get("response_time")
            result["status_code"] = response.get("status_code")
            result["available"] = response.get("success", False) or (response.get("status_code", 500) < 500)
            
            if response.get("status_code", 500) >= 400:
                result["warning"] = f"HTTP status code: {response.get('status_code')}"
                
        except Exception as e:
            result["error"] = f"HTTP request failed: {str(e)}"
        
        return result
    
    async def load_test(self, 
                       url: str, 
                       num_requests: int = 100, 
                       concurrency: int = 10) -> Dict[str, Any]:
        """Perform load testing on an endpoint"""
        logger.info(f"Load testing {url}: {num_requests} requests, {concurrency} concurrent")
        
        start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(min(concurrency, self.max_concurrent))
        
        async def single_request():
            async with semaphore:
                return await self.test_endpoint(url)
        
        # Execute requests
        tasks = [single_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        return self._process_load_test_results(url, results, total_time, num_requests)
    
    def _process_load_test_results(self, url: str, results: List, total_time: float, total_requests: int) -> Dict[str, Any]:
        """Process and analyze load test results"""
        successful_requests = 0
        failed_requests = 0
        response_times = []
        status_codes = {}
        
        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
                continue
                
            if result.get("success", False):
                successful_requests += 1
            else:
                failed_requests += 1
            
            if "response_time" in result:
                response_times.append(result["response_time"])
            
            status_code = result.get("status_code")
            if status_code:
                status_codes[status_code] = status_codes.get(status_code, 0) + 1
        
        # Calculate statistics
        stats = {
            "url": url,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / max(total_requests, 1),
            "total_time": total_time,
            "requests_per_second": total_requests / max(total_time, 0.001),
            "status_codes": status_codes
        }
        
        if response_times:
            response_times.sort()
            stats["response_times"] = {
                "min": min(response_times),
                "max": max(response_times),
                "avg": sum(response_times) / len(response_times),
                "median": response_times[len(response_times) // 2],
                "p95": response_times[int(len(response_times) * 0.95)] if len(response_times) > 20 else max(response_times),
                "p99": response_times[int(len(response_times) * 0.99)] if len(response_times) > 100 else max(response_times)
            }
        
        return stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get API tester statistics"""
        if not self.request_history:
            return {"total_requests": 0}
        
        total_requests = len(self.request_history)
        successful_requests = sum(1 for req in self.request_history if req.get("success", False))
        
        response_times = [req["response_time"] for req in self.request_history if "response_time" in req]
        
        stats = {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": successful_requests / total_requests,
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0
        }
        
        return stats
    
    def clear_history(self):
        """Clear request history"""
        self.request_history.clear()
        logger.info("Request history cleared")
