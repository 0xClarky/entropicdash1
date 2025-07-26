import requests
import time
from datetime import datetime
import random

class MintAddressFetcher:
    def __init__(self):
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Increased from 0.5 to 1.0
        self.max_retries = 5  # Increased from 3 to 5
        
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get_mint_address(self, pool_address: str) -> str:
        """Get the mint address for a token from its pool address."""
        if not pool_address:
            print(f"Invalid pool address: {pool_address}")
            return None

        # Check cache first
        if pool_address in self.cache:
            cached_value = self.cache[pool_address]
            if cached_value is None:
                print(f"Cache hit (None) for pool {pool_address}")
            return cached_value

        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                self._wait_for_rate_limit()
                
                url = f"{self.base_url}/networks/solana/pools/{pool_address}/info"
                print(f"Fetching mint address for pool {pool_address} (attempt {retries + 1})")
                
                response = requests.get(url)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    wait_time = retry_after + random.uniform(0.1, 1.0)
                    print(f"Rate limited, waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    retries += 1
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                if 'data' not in data:
                    print(f"No data in response for pool {pool_address}")
                    raise ValueError("No data in response")
                
                tokens = data['data']
                if not tokens:
                    print(f"No tokens found for pool {pool_address}")
                    raise ValueError("No tokens in response")
                
                # Find the token that isn't SOL
                for token in tokens:
                    if 'attributes' not in token:
                        continue
                    
                    address = token['attributes'].get('address')
                    if not address:
                        continue
                        
                    if address != "So11111111111111111111111111111111111111112":
                        self.cache[pool_address] = address
                        print(f"Found mint address {address} for pool {pool_address}")
                        return address
                
                print(f"No non-SOL token found in pool {pool_address}")
                raise ValueError("Could not find non-SOL token mint address")
                
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)}"
                print(f"Error fetching mint address for pool {pool_address}: {last_error}")
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                print(f"Error processing pool {pool_address}: {last_error}")
            
            # Exponential backoff
            if retries < self.max_retries - 1:
                wait_time = (2 ** retries) + random.uniform(0.1, 1.0)
                print(f"Retrying in {wait_time:.2f}s (attempt {retries + 1}/{self.max_retries})")
                time.sleep(wait_time)
            retries += 1

        # If we get here, all retries failed
        print(f"All retries failed for pool {pool_address}. Last error: {last_error}")
        self.cache[pool_address] = None
        return None