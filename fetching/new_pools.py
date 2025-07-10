import requests
import logging
import pandas as pd
from datetime import datetime
import time
from .pool_info import PoolInfoAPI
from services.mint_fetcher import MintAddressFetcher
from holder_analyzer import analyze_holder_distribution
from distribution_detector import detect_distribution_patterns  # Add this import

class GeckoTerminalAPI:
    MIN_FDV_RESERVE_RATIO = 1.2  # Adjust this value as needed

    def __init__(self):
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self.headers = {
            "Accept": "application/json"
        }
        self.pool_info_api = PoolInfoAPI()  # Initialize here
        self.logger = logging.getLogger(__name__)  # Add logger
        self.mint_fetcher = MintAddressFetcher()

    def get_new_pools(self, network="solana", page_size=100):
        """Fetch new token pairs from GeckoTerminal"""
        endpoint = f"{self.base_url}/networks/{network}/new_pools"
        params = {"page_size": page_size}

        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            pools = data.get("data", [])
            
            # Extract relevant information from pools
            processed_data = []
            for pool in pools:
                attributes = pool.get("attributes", {})
                
                # Extract 24h transactions data
                h24_trans = attributes.get('transactions', {}).get('h24', {})
                total_24h_transactions = h24_trans.get('buys', 0) + h24_trans.get('sells', 0)
                
                # Extract 24h volume
                h24_volume = attributes.get('volume_usd', {}).get('h24', 0)
                
                # Apply initial filtering conditions
                fdv = float(attributes.get('fdv_usd', 0) or 0)
                reserve = float(attributes.get('reserve_in_usd', 0) or 0)
                volume = float(h24_volume or 0)
                
                # Skip pools that don't meet criteria
                if (fdv < 5000 or 
                    fdv > 500000 or  # Upper limit for FDV
                    reserve < 1000 or 
                    total_24h_transactions < 25 or 
                    volume < 1000 or
                    fdv <= reserve or
                    (fdv / reserve) < self.MIN_FDV_RESERVE_RATIO):  # Add ratio check
                    continue
                
                # Get pool info before adding to processed_data
                pool_info = self.pool_info_api.get_pool_info(attributes.get('address'))
                if pool_info is None:
                    pool_info = {
                        'mint_authority': False,
                        'freeze_authority': False,
                        'top_10_holders': 0.0,
                        'gt_score': 0.0
                    }
                
                mint_address = self.mint_fetcher.get_mint_address(attributes.get('address'))
                processed_data.append({
                    'name': attributes.get('name'),
                    'address': attributes.get('address'),
                    'created_at': attributes.get('pool_created_at'),  # Changed to pool_created_at
                    'fdv_usd': fdv,
                    'reserve_in_usd': reserve,
                    'transactions_24h': total_24h_transactions,
                    'volume_24h': volume,
                    'mint_authority': pool_info['mint_authority'],
                    'freeze_authority': pool_info['freeze_authority'],
                    'top_10_holders': pool_info['top_10_holders'],
                    'gt_score': pool_info['gt_score'],
                    'entropy_score': detect_distribution_patterns(mint_address)['entropy_score'] if mint_address else 0.0
                })
            
            # Convert to DataFrame
            df = pd.DataFrame(processed_data)
            
            # Only process if we have data
            if not df.empty:
                # Clean up timestamps
                df['created_at'] = pd.to_datetime(df['created_at'])
                
                # Sort by volume
                df = df.sort_values('volume_24h', ascending=False)
                
                # Add holder data to dataframe
                df['mint_address'] = df['address'].apply(self.mint_fetcher.get_mint_address)
                
                def get_holder_data(mint_address):
                    if mint_address:
                        holder_data = analyze_holder_distribution(mint_address)
                        return holder_data if holder_data else {'top_holder': 0, 'top_20_holders': 0}
                    return {'top_holder': 0, 'top_20_holders': 0}
                    
                holder_data = df['mint_address'].apply(get_holder_data)
                df['top_holder'] = holder_data.apply(lambda x: x['top_holder'])
                df['top_20_holders'] = holder_data.apply(lambda x: x['top_20_holders'])
            
            return df

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching data: {e}")
            return pd.DataFrame()  # Return empty DataFrame instead of None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return pd.DataFrame()