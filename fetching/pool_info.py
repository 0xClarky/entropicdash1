import requests
import logging
import json
import time
import random  # Add this import
from datetime import datetime, timedelta

class PoolInfoAPI:
    def __init__(self):
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self.headers = {"Accept": "application/json"}
        self.sol_address = "So11111111111111111111111111111111111111112"
        self.logger = logging.getLogger(__name__)
        self.retry_count = 3
        self.retry_delay = 1
        self.update_cache = {}
        self.update_delay = 120
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Increase to 2 seconds
        self.cache_timeout = 30  # 30 seconds cache timeout

    def get_pool_info(self, pool_address, network="solana"):
        """Fetch pool information with better rate limiting"""
        now = datetime.now()
        
        # Check cache first
        if pool_address in self.update_cache:
            last_update, cached_result = self.update_cache[pool_address]
            if (now - last_update).total_seconds() < self.cache_timeout:
                return cached_result
        
        # If not in cache or cache expired, fetch new data
        result = self._fetch_pool_info(pool_address, network)
        
        # Only retry if we get zeros AND haven't hit rate limits
        if (result['gt_score'] == 0.0 and 
            result['top_10_holders'] == 0.0 and 
            'rate_limited' not in result):  # Add this flag in _fetch_pool_info
            time.sleep(self.min_request_interval)
            retry_result = self._fetch_pool_info(pool_address, network)
            if retry_result['gt_score'] > 0.0 or retry_result['top_10_holders'] > 0.0:
                result = retry_result
        
        # Update cache
        self.update_cache[pool_address] = (now, result)
        return result

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _fetch_pool_info(self, pool_address, network="solana"):
        """Internal method to fetch pool information with rate limiting"""
        default_response = {
            'mint_authority': False,
            'freeze_authority': False,
            'top_10_holders': 0.0,
            'gt_score': 0.0,
            'mint_address': None  # Add mint_address to default response
        }

        retries = 0
        while retries < self.retry_count:
            try:
                self._wait_for_rate_limit()
                
                endpoint = f"{self.base_url}/networks/{network}/pools/{pool_address}/info"
                response = requests.get(endpoint, headers=self.headers)
                
                if response.status_code == 429:
                    self.logger.warning(f"Rate limit hit for pool {pool_address}")
                    retry_after = int(response.headers.get('Retry-After', 5))
                    time.sleep(retry_after + random.uniform(0.1, 1.0))
                    retries += 1
                    continue
                    
                response.raise_for_status()
                
                data = response.json()
                tokens = data.get('data', [])
                
                if not tokens:
                    self.logger.warning(f"No tokens found for pool {pool_address}")
                    return default_response
                    
                # Find non-SOL token and log all tokens for debugging
                non_sol_token = None
                for token in tokens:
                    attrs = token.get('attributes', {})
                    addr = attrs.get('address')
                    self.logger.debug(f"Found token: {attrs.get('symbol')} at {addr}")
                    if addr != self.sol_address:
                        non_sol_token = token
                        break
                        
                if not non_sol_token:
                    self.logger.warning(f"No non-SOL token found for pool {pool_address}")
                    return default_response
                        
                attrs = non_sol_token.get('attributes', {})
                
                # Get the mint address (token address)
                mint_address = attrs.get('address')
                
                # Get other data as before
                holders = attrs.get('holders', {}) or {}
                distribution = holders.get('distribution_percentage', {}) or {}
                top_10 = distribution.get('top_10', '0')
                if isinstance(top_10, str):
                    top_10 = top_10.replace('%', '')
                
                return {
                    'mint_authority': attrs.get('mint_authority') == "yes",
                    'freeze_authority': attrs.get('freeze_authority') == "yes",
                    'top_10_holders': float(top_10 or 0),
                    'gt_score': float(attrs.get('gt_score', 0) or 0),
                    'mint_address': mint_address  # Include mint_address in response
                }
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching pool info for {pool_address}: {e}")
                if retries < self.retry_count - 1:
                    sleep_time = (2 ** retries) + random.uniform(0.1, 1.0)
                    time.sleep(sleep_time)
                retries += 1
            except Exception as e:
                self.logger.error(f"Unexpected error for {pool_address}: {e}")
                break

        return default_response