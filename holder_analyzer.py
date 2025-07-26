# analyzers/holder_analyzer.py

from others.rpc import get_token_largest_accounts, get_token_supply
from others.settings import TOP_HOLDER_COUNT, DUMP_THRESHOLD, DISPLAY_SUPPLY_FALLBACK
from jupiter_lp_detector import get_lp_addresses_for_token

def analyze_holder_distribution(mint: str) -> dict:
    """Analyze holder distribution for a token, identifying and separating LP holders."""
    try:
        # Get liquidity pool addresses for this token
        lp_info_sol = get_lp_addresses_for_token(mint, use_sol=True)
        lp_info_usdc = get_lp_addresses_for_token(mint, use_sol=False)
        
        # Create normalized sets for case-insensitive comparison
        lp_addresses_set = {addr.lower() for addr in lp_info_sol.get("addresses", []) + lp_info_usdc.get("addresses", [])}
        
        # Store original addresses for labels
        lp_addresses_original = lp_info_sol.get("addresses", []) + lp_info_usdc.get("addresses", [])
        
        # Combine labels from both sources
        lp_labels = {**lp_info_sol.get("labels", {}), **lp_info_usdc.get("labels", {})}
        
        # Improved debug output for LP detection
        print(f"[DEBUG] Found {len(lp_addresses_set)} unique LP addresses for token {mint}")
        for addr in lp_addresses_original:
            label = lp_labels.get(addr, "Unknown")
            print(f"[DEBUG] LP: {addr} ({label})")
        
        try:
            supply_info = get_token_supply(mint)["value"]
            decimals = int(supply_info["decimals"])
            actual_supply = int(supply_info["amount"]) / (10 ** decimals)
        except Exception as e:
            print(f"[DEBUG] Error getting supply: {str(e)}")
            decimals = 9
            actual_supply = DISPLAY_SUPPLY_FALLBACK

        # Fetch token accounts
        largest_accounts = get_token_largest_accounts(mint).get("value", [])
        print(f"[DEBUG] Found {len(largest_accounts)} token accounts")
        
        # Filter and classify holders
        lp_holders = []
        non_lp_holders = []
        
        for acc in largest_accounts:
            address = acc["address"]
            amount = int(acc["amount"]) / (10 ** decimals)
            
            # Use lowercase for comparison (important for Solana addresses)
            is_lp = address.lower() in lp_addresses_set
            
            print(f"[DEBUG] Account: {address}, Amount: {amount}, Is LP: {is_lp}")
            if not is_lp and address in lp_addresses_original:
                # Double check for case issues
                print(f"[DEBUG] WARNING: Case mismatch! {address} is in LP list but not matched in lowercase set")
            
            # For debugging, check if any LP address is close to this one
            if not is_lp:
                for lp_addr in lp_addresses_original:
                    # Calculate similarity between addresses
                    similarity = sum(a == b for a, b in zip(address.lower(), lp_addr.lower())) / len(address)
                    if similarity > 0.8:  # If addresses are 80%+ similar
                        print(f"[DEBUG] Possible similar LP address: {lp_addr} (similarity {similarity:.2f})")
            
            if is_lp:
                # Find original address to get label
                for orig_addr in lp_addresses_original:
                    if orig_addr.lower() == address.lower():
                        label = lp_labels.get(orig_addr, "Unknown LP")
                        break
                else:
                    label = "Unknown LP"
                
                lp_holders.append({
                    "address": address,
                    "amount": amount,
                    "label": label
                })
                print(f"[DEBUG] Added to LP holders: {address} ({label}), amount: {amount}")
            else:
                non_lp_holders.append({
                    "address": address,
                    "amount": amount
                })
        
        # Calculate LP stats
        lp_total_amount = sum(h["amount"] for h in lp_holders)
        lp_pct = (lp_total_amount / actual_supply) * 100 if actual_supply > 0 else 0
        
        print(f"[DEBUG] LP holders found: {len(lp_holders)}")
        print(f"[DEBUG] LP total amount: {lp_total_amount} ({lp_pct:.2f}% of supply)")
        print(f"[DEBUG] Non-LP holders: {len(non_lp_holders)}")
        
        # Calculate holder stats (exclusively using non_lp_holders)
        top_holders = non_lp_holders[:TOP_HOLDER_COUNT]
        
        # Top holder percentage
        top_holder_pct = 0.0
        if top_holders:
            top_holder = top_holders[0]
            top_holder_pct = (top_holder["amount"] / actual_supply) * 100 if actual_supply > 0 else 0
        
        # Top 20 concentration percentage
        total_top_n = sum(h["amount"] for h in top_holders)
        top_20_pct = (total_top_n / actual_supply) * 100 if actual_supply > 0 else 0

        return {
            "top_holder": top_holder_pct,  # Return as float
            "top_20_holders": top_20_pct,  # Return as float
            "dump_risk_flag": top_holder_pct >= (DUMP_THRESHOLD * 100),
            "lp_addresses": lp_addresses_original,
            "lp_count": len(lp_addresses_set),
            "lp_total_amount": lp_total_amount,
            "lp_pct": lp_pct,
            "lp_labels": lp_labels,
            "lp_holders": lp_holders,
            "actual_supply": actual_supply
        }

    except Exception as e:
        print(f"[holder_analyzer] Error: {str(e)}")
        return {
            "top_holder": 0.0,
            "top_20_holders": 0.0,
            "dump_risk_flag": False,
            "lp_addresses": [],
            "lp_count": 0,
            "lp_total_amount": 0,
            "lp_pct": 0,
            "lp_labels": {},
            "lp_holders": [],
            "actual_supply": 0
        }

if __name__ == "__main__":
    # Example usage - run this file directly to test
    test_mint = "BFMChrYX5nQNHC8bpzkYaFzz769yPt7sMRMp2LZppump"  # Replace with test mint
    results = analyze_holder_distribution(test_mint)
    
    # Print key results
    print("\n=== HOLDER ANALYSIS RESULTS ===")
    print(f"LP Count: {results['lp_count']}")
    print(f"LP Total: {results['lp_pct']:.2f}% of supply")
    print(f"Top Holder: {results['top_holder']:.2f}% of supply")
    print(f"Top 20 Holders: {results['top_20_holders']:.2f}% of supply")
    
    # Print LP details
    if results['lp_holders']:
        print("\nLP Holders:")
        for lp in results['lp_holders']:
            label = results['lp_labels'].get(lp['address'], 'Unknown LP')
            print(f"- {label}: {lp['address']}, {lp['amount']}")

