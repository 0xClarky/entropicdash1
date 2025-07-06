import requests
import time
from datetime import datetime
import random

class MintAddressFetcher:
    def __init__(self):
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self.cache = {}  # Add cache
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Minimum time between requests in seconds
        self.max_retries = 3
        
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get_mint_address(self, pool_address: str) -> str:
        """
        Get the mint address for a token from its pool address.
        Returns the non-SOL token mint address.
        """
        # Check cache first
        if pool_address in self.cache:
            return self.cache[pool_address]

        retries = 0
        while retries < self.max_retries:
            try:
                self._wait_for_rate_limit()  # Rate limiting
                
                url = f"{self.base_url}/networks/solana/pools/{pool_address}/info"
                response = requests.get(url)
                
                if response.status_code == 429:  # Rate limit hit
                    retry_after = int(response.headers.get('Retry-After', 5))
                    time.sleep(retry_after + random.uniform(0.1, 1.0))
                    retries += 1
                    continue
                    
                response.raise_for_status()
                
                data = response.json()['data']
                
                # Find the token that isn't SOL
                for token in data:
                    address = token['attributes']['address']
                    if address != "So11111111111111111111111111111111111111112":
                        # Cache the result
                        self.cache[pool_address] = address
                        return address
                        
                raise ValueError("Could not find non-SOL token mint address")
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching mint address for pool {pool_address}: {str(e)}")
                if retries < self.max_retries - 1:  # Don't sleep on last retry
                    sleep_time = (2 ** retries) + random.uniform(0.1, 1.0)  # Exponential backoff
                    time.sleep(sleep_time)
                retries += 1
            except Exception as e:
                print(f"Unexpected error for pool {pool_address}: {str(e)}")
                break

        # Cache failed attempts as None to avoid repeated failures
        self.cache[pool_address] = None
        return None