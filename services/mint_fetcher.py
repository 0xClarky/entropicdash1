import requests
import time

class MintAddressFetcher:
    def __init__(self):
        self.base_url = "https://api.geckoterminal.com/api/v2"
        
    def get_mint_address(self, pool_address: str) -> str:
        """
        Get the mint address for a token from its pool address.
        Returns the non-SOL token mint address.
        """
        try:
            url = f"{self.base_url}/networks/solana/pools/{pool_address}/info"
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()['data']
            
            # Find the token that isn't SOL
            for token in data:
                address = token['attributes']['address']
                if address != "So11111111111111111111111111111111111111112":
                    return address
                    
            raise ValueError("Could not find non-SOL token mint address")
            
        except Exception as e:
            print(f"Error fetching mint address for pool {pool_address}: {str(e)}")
            return None