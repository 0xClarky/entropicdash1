import requests
import json
import base58
from solders.pubkey import Pubkey
from others.rpc import get_account_info

def get_lp_addresses_for_token(mint_address: str, use_sol: bool = True, debug=False) -> dict:
    """
    Get LP addresses for a token-SOL pair or token-USDC pair.
    """
    if use_sol:
        input_mint = "So11111111111111111111111111111111111111112"  # SOL
        pair_name = "SOL"
    else:
        input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        pair_name = "USDC"
    
    output_mint = mint_address
    amount = 1_000_000
    
    try:
        url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": 100
        }
        
        print(f"[DEBUG] Querying Jupiter API for {pair_name} pair with {mint_address}")
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if debug:
            print(f"Jupiter response for {pair_name} pair: {json.dumps(data, indent=2)}")
        
        lp_addresses = []
        lp_labels = {}
        
        # Parse route information - look for both ammKey and lpAddress
        if "routePlan" in data:
            for i, route_step in enumerate(data.get("routePlan", [])):
                if "swapInfo" in route_step:
                    swap_info = route_step["swapInfo"]
                    
                    if "ammKey" in swap_info:
                        amm_key = swap_info["ammKey"]
                        if amm_key not in lp_addresses:
                            lp_addresses.append(amm_key)
                            if "label" in swap_info:
                                lp_labels[amm_key] = swap_info["label"]
                    
                    if "lpAddress" in swap_info:
                        lp_addr = swap_info["lpAddress"]
                        if lp_addr not in lp_addresses:
                            lp_addresses.append(lp_addr)
                            if "label" in swap_info:
                                lp_labels[lp_addr] = swap_info["label"]
        
        # Also check routes/marketInfos
        for route in data.get("routes", []):
            for market in route.get("marketInfos", []):
                if "lpAddress" in market:
                    lp_addr = market["lpAddress"]
                    if lp_addr not in lp_addresses:
                        lp_addresses.append(lp_addr)
                        if "label" in market:
                            lp_labels[lp_addr] = market["label"]
                
                if "ammKey" in market:
                    amm_key = market["ammKey"]
                    if amm_key not in lp_addresses:
                        lp_addresses.append(amm_key)
                        if "label" in market:
                            lp_labels[amm_key] = market["label"]
        
        if debug:
            print(f"Found {len(lp_addresses)} LP addresses for {pair_name} pair:")
            for addr in lp_addresses:
                print(f"  {addr} ({lp_labels.get(addr, 'Unknown')})")
        
        # Try reverse direction (token to SOL/USDC)
        try:
            params = {
                "inputMint": output_mint,
                "outputMint": input_mint,
                "amount": amount,
                "slippageBps": 100
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Use the same parsing logic for reverse direction
            if "routePlan" in data:
                for route_step in data.get("routePlan", []):
                    if "swapInfo" in route_step:
                        swap_info = route_step["swapInfo"]
                        
                        if "ammKey" in swap_info:
                            amm_key = swap_info["ammKey"]
                            if amm_key not in lp_addresses:
                                lp_addresses.append(amm_key)
                                if "label" in swap_info:
                                    lp_labels[amm_key] = swap_info["label"]
                        
                        if "lpAddress" in swap_info:
                            lp_addr = swap_info["lpAddress"]
                            if lp_addr not in lp_addresses:
                                lp_addresses.append(lp_addr)
                                if "label" in swap_info:
                                    lp_labels[lp_addr] = swap_info["label"]
            
            for route in data.get("routes", []):
                for market in route.get("marketInfos", []):
                    if "lpAddress" in market:
                        lp_addr = market["lpAddress"]
                        if lp_addr not in lp_addresses:
                            lp_addresses.append(lp_addr)
                            if "label" in market:
                                lp_labels[lp_addr] = market["label"]
                    
                    if "ammKey" in market:
                        amm_key = market["ammKey"]
                        if amm_key not in lp_addresses:
                            lp_addresses.append(amm_key)
                            if "label" in market:
                                lp_labels[amm_key] = market["label"]
        
        except Exception as e:
            if debug:
                print(f"Error in reverse direction: {str(e)}")
        
        # Get token accounts for LPs too
        token_account_addresses = get_lp_token_accounts(lp_addresses, mint_address)
        
        # Add these token accounts to our collection of LP addresses
        for acc in token_account_addresses:
            if acc not in lp_addresses:
                lp_addresses.append(acc)
                lp_labels[acc] = f"LP Token Account ({lp_labels.get(acc, 'Unknown')})"
                
        print(f"[DEBUG] Jupiter API LP detection for {pair_name}: Found {len(lp_addresses)} addresses "
              f"({len(token_account_addresses)} token accounts)")
        
        for addr in lp_addresses:
            print(f"[DEBUG]   - {addr} ({lp_labels.get(addr, 'Unknown')})")
        
        return {
            "found": len(lp_addresses) > 0,
            "addresses": lp_addresses,
            "count": len(lp_addresses),
            "labels": lp_labels,
            "error": None
        }
    
    except Exception as e:
        print(f"[DEBUG] Jupiter LP detection error for {pair_name}: {str(e)}")
        return {
            "found": False,
            "addresses": [],
            "count": 0,
            "labels": {},
            "error": str(e)
        }

def is_address_an_lp(address: str, token_mint: str) -> bool:
    """Check if a given address is a liquidity pool for the token"""
    lp_info = get_lp_addresses_for_token(token_mint)
    return address in lp_info.get("addresses", [])

# Add this function to resolve LP program addresses to token accounts
def get_lp_token_accounts(lp_program_addresses, mint_address):
    """
    For each LP program address, try to find its associated token account
    that holds the token being analyzed.
    """
    token_accounts = []
    
    for lp_address in lp_program_addresses:
        try:
            # Use getTokenAccountsByOwner RPC method to find token accounts owned by the LP
            params = [
                lp_address,
                {"mint": mint_address},
                {"encoding": "jsonParsed"}
            ]
            
            from others.rpc import helius_rpc_request
            response = helius_rpc_request("getTokenAccountsByOwner", params)
            
            if "value" in response and response["value"]:
                for account in response["value"]:
                    token_accounts.append(account["pubkey"])
                    print(f"[DEBUG] Found token account {account['pubkey']} for LP {lp_address}")
        except Exception as e:
            print(f"[DEBUG] Error getting token accounts for LP {lp_address}: {str(e)}")
    
    return token_accounts

def check_honeypot(mint_address: str) -> dict:
    """
    Analyzes buy/sell slippage to detect potential honeypot characteristics.
    A honeypot usually has significantly worse sell conditions than buy conditions.
    
    Returns:
        dict: Analysis results including buy/sell prices and warnings
    """
    # Define test amounts
    test_sol_amount = 100_000_000  # 0.1 SOL in lamports
    slippage_bps = 150  # 1.5% slippage tolerance
    
    result = {
        "buy_price": 0,
        "sell_price": 0,
        "price_impact_buy": 0,
        "price_impact_sell": 0,
        "slippage_ratio": 0,
        "is_possible_honeypot": False,
        "warning_message": "",
        "error": None
    }
    
    try:
        # SOL -> Token (BUY)
        url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": "So11111111111111111111111111111111111111112",  # SOL
            "outputMint": mint_address,
            "amount": test_sol_amount,
            "slippageBps": slippage_bps
        }
        
        print(f"[DEBUG] Simulating BUY for {mint_address}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        buy_data = response.json()
        
        # After parsing buy_data, add:
        if "error" in buy_data:
            error_msg = buy_data.get("error", "Unknown buy error")
            print(f"[DEBUG] Jupiter API buy error: {error_msg}")
            result["error"] = f"Buy error: {error_msg}"
            return result
        
        # Extract buy data
        if "outAmount" in buy_data:
            token_amount = int(buy_data["outAmount"])
            price_impact_buy = float(buy_data.get("priceImpactPct", 0))
            result["buy_price"] = test_sol_amount / token_amount if token_amount > 0 else 0
            result["price_impact_buy"] = price_impact_buy
            
            print(f"[DEBUG] BUY: {test_sol_amount} SOL lamports -> {token_amount} token units")
            print(f"[DEBUG] BUY price impact: {price_impact_buy}%")
            
            # Now try selling the tokens we would get
            params = {
                "inputMint": mint_address,
                "outputMint": "So11111111111111111111111111111111111111112",  # SOL
                "amount": token_amount,
                "slippageBps": slippage_bps
            }
            
            print(f"[DEBUG] Simulating SELL for {mint_address}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            sell_data = response.json()
            
            # After parsing sell_data, add:
            if "error" in sell_data:
                error_msg = sell_data.get("error", "Unknown sell error")
                print(f"[DEBUG] Jupiter API sell error: {error_msg}")
                result["error"] = f"Sell error: {error_msg}"
                return result
            
            # Extract sell data
            if "outAmount" in sell_data:
                sol_received = int(sell_data["outAmount"])
                price_impact_sell = float(sell_data.get("priceImpactPct", 0))
                result["sell_price"] = token_amount / sol_received if sol_received > 0 else float('inf')
                result["price_impact_sell"] = price_impact_sell
                
                print(f"[DEBUG] SELL: {token_amount} token units -> {sol_received} SOL lamports")
                print(f"[DEBUG] SELL price impact: {price_impact_sell}%")
                
                # Calculate recovery percentage
                recovery_pct = (sol_received / test_sol_amount) * 100
                result["recovery_pct"] = recovery_pct
                
                # Calculate slippage ratio (how much worse is selling than buying)
                if price_impact_buy > 0:
                    result["slippage_ratio"] = price_impact_sell / price_impact_buy
                else:
                    result["slippage_ratio"] = price_impact_sell * 2  # Arbitrary multiplier if buy impact is 0
                
                print(f"[DEBUG] Recovery: {recovery_pct:.2f}% of original SOL")
                print(f"[DEBUG] Slippage ratio (sell/buy): {result['slippage_ratio']:.2f}x")
                
                # Detect potential honeypot with improved logic
                is_honeypot = False
                warning_message = ""
                
                # Recovery check
                if recovery_pct < 80:
                    is_honeypot = True
                    warning_message = f"Severe sell penalty detected: only {recovery_pct:.1f}% recovery"
                
                # Impact ratio check - apply only when impacts are meaningful
                elif (price_impact_buy > 0.1 or price_impact_sell > 0.1):  # Only check if either impact exceeds 0.1%
                    # Check both ratio and absolute difference
                    if result["slippage_ratio"] > 3 and (price_impact_sell - price_impact_buy) > 1.0:
                        is_honeypot = True
                        warning_message = f"Sell impact {result['slippage_ratio']:.1f}x higher than buy impact"
                
                # Check for extreme conditions
                if recovery_pct < 50:
                    is_honeypot = True
                    warning_message = f"CRITICAL: Extreme sell penalty ({recovery_pct:.1f}% recovery)"
                
                result["is_possible_honeypot"] = is_honeypot
                result["warning_message"] = warning_message
    
    except Exception as e:
        print(f"[DEBUG] Honeypot detection error: {str(e)}")
        result["error"] = str(e)
    
    return result

# Add a debug function to test directly
def debug_lp_detection(mint_address: str):
    """Run LP detection with debug output"""
    print(f"\n=== DEBUGGING LP DETECTION FOR {mint_address} ===")
    
    # Check SOL pair
    sol_result = get_lp_addresses_for_token(mint_address, use_sol=True, debug=True)
    print(f"\nSOL pair result: {json.dumps(sol_result, indent=2)}")
    
    # Check USDC pair
    usdc_result = get_lp_addresses_for_token(mint_address, use_sol=False, debug=True)
    print(f"\nUSDC pair result: {json.dumps(usdc_result, indent=2)}")
    
    # Combined results
    all_addresses = set(sol_result["addresses"] + usdc_result["addresses"])
    print(f"\nTotal unique LP addresses found: {len(all_addresses)}")
    print("Addresses:")
    for addr in all_addresses:
        label = sol_result["labels"].get(addr) or usdc_result["labels"].get(addr) or "Unknown"
        print(f"  - {addr} ({label})")

if __name__ == "__main__":
    # Example usage - run this file directly to test
    test_mint = "FEhChTj13MxpHuyb2uTSTrPcbzojDM9gavrTzWUP8Ek5"  # Replace with your test mint
    debug_lp_detection(test_mint)