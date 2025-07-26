import requests
from datetime import datetime
import pytz
import logging
from .pool_info import PoolInfoAPI  # Import from pool_info.py

class PoolInfoAPI:
    def get_pool_info(self, address):
        """
        Fetch updated information for a specific pool
        """
        base_url = "https://api.geckoterminal.com/api/v2"
        headers = {
            "Accept": "application/json"
        }
        endpoint = f"{base_url}/search/pools"
        params = {
            "query": address,
            "page": 1
        }
        
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            pools = data.get("data", [])
            
            if not pools:
                return None
                
            # Get the first (and should be only) pool
            pool = pools[0]
            attributes = pool.get("attributes", {})
            
            # Extract 24h transactions data
            h24_trans = attributes.get('transactions', {}).get('h24', {})
            total_24h_transactions = h24_trans.get('buys', 0) + h24_trans.get('sells', 0)
            
            # Extract 24h volume
            h24_volume = attributes.get('volume_usd', {}).get('h24', 0)
            
            return {
                'fdv_usd': float(attributes.get('fdv_usd', 0) or 0),
                'reserve_in_usd': float(attributes.get('reserve_in_usd', 0) or 0),
                'transactions_24h': total_24h_transactions,
                'volume_24h': float(h24_volume or 0),
                'last_updated': datetime.now(pytz.UTC)
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {address}: {e}")
            return None

class SearchPoolsAPI:
    def __init__(self):
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self.headers = {"Accept": "application/json"}
        self.pool_info = PoolInfoAPI()
        self.logger = logging.getLogger(__name__)

    def get_pool_info(self, address):
        """Get pool info with proper error handling"""
        try:
            return self.pool_info.get_pool_info(address)
        except Exception as e:
            self.logger.error(f"Failed to get pool info for {address}: {e}")
            return None