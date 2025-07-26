from db.database import DatabaseHandler
from fetching.search_pools import SearchPoolsAPI
from services.mint_fetcher import MintAddressFetcher
from holder_analyzer import analyze_holder_distribution
from jupiter_lp_detector import check_honeypot  # Add this import
from distribution_detector import detect_distribution_patterns  # Add this import
import time
import pandas as pd

class TokenUpdater:
    def __init__(self):
        self.db = DatabaseHandler()
        self.api = SearchPoolsAPI()
        self.mint_fetcher = MintAddressFetcher()
        
    def update_token(self, address):
        """Update a specific token's data"""
        try:
            # Get updated pool info
            pool_info = self.api.get_pool_info(address)
            
            if pool_info and self.should_keep_token(pool_info):
                # Get mint address
                mint_address = self.mint_fetcher.get_mint_address(address)
                
                if mint_address:
                    # Get distribution patterns first
                    distribution_data = detect_distribution_patterns(mint_address)
                    print(f"Distribution data for {mint_address}: {distribution_data}")  # Debug log
                    
                    # Add this check
                    if distribution_data is None or 'entropy_score' not in distribution_data:
                        print(f"No entropy score available for {mint_address}")
                        return
                    
                    update_data = {
                        'fdv_usd': float(pool_info.get('fdv_usd', 0) or 0),
                        'reserve_in_usd': float(pool_info.get('reserve_in_usd', 0) or 0),
                        'transactions_24h': int(pool_info.get('transactions_24h', 0) or 0),
                        'volume_24h': float(pool_info.get('volume_24h', 0) or 0),
                        'last_updated': pd.Timestamp.now(tz='UTC').isoformat(),
                        'entropy_score': float(distribution_data.get('entropy_score', 0))  # Ensure it's a float
                    }
                    
                    print(f"Entropy score for {mint_address}: {update_data['entropy_score']}")  # Debug log
                    self.db.update_token(address, update_data)
                else:
                    print(f"Token {address} no longer meets criteria")
                    self.db.delete_token(address)
        except Exception as e:
            print(f"Error updating token {address}: {e}")

    def update_token_holders(self, pool_address: str):
        try:
            # Get mint address
            mint_address = self.mint_fetcher.get_mint_address(pool_address)
            if mint_address:
                # Get holder distribution
                holder_data = analyze_holder_distribution(mint_address)
                if holder_data:
                    top_holder = holder_data['top_holder']
                    top_20_holders = holder_data['top_20_holders']
                    
                    # Update database with new holder data
                    self.db.update_token_holders(
                        pool_address,
                        mint_address,
                        top_holder,
                        top_20_holders
                    )
        except Exception as e:
            print(f"Error updating holder data: {str(e)}")

    def should_keep_token(self, token_data):
        """Check if token meets criteria to stay in DB"""
        if not token_data:
            return False
            
        fdv = float(token_data.get('fdv_usd', 0) or 0)
        reserve = float(token_data.get('reserve_in_usd', 0) or 0)
        volume = float(token_data.get('volume_24h', 0) or 0)
        
        # Basic filtering criteria
        if fdv < 3000 or fdv > 100_000_000:
            return False
        if reserve < 500:
            return False
        if volume < 1000:
            return False
            
        return True