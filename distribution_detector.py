# analyzers/pattern_detector.py

from others.rpc import get_token_largest_accounts, get_token_supply
import math
from collections import Counter
from others.settings import TOP_HOLDER_COUNT

def detect_distribution_patterns(mint: str) -> dict:
    try:
        largest_accounts = get_token_largest_accounts(mint).get("value", [])
        supply_info = get_token_supply(mint)["value"]
        decimals = int(supply_info["decimals"])
        actual_supply = int(supply_info["amount"]) / (10 ** decimals)

        balances = [int(acc["amount"]) / (10 ** decimals) for acc in largest_accounts[:TOP_HOLDER_COUNT]]
        total_top = sum(balances)
        proportions = [bal / total_top for bal in balances if total_top > 0]

        results = {
            "uniform_balance": False,
            "cliff_distribution": False,
            "decimal_pattern": False,
            "low_entropy": False,
            "entropy_score": 0
        }

        # --- Uniform Balance Check ---
        counts = Counter(balances)
        if any(count >= 3 for count in counts.values()):
            results["uniform_balance"] = True

        # --- Cliff Distribution Check ---
        if len(balances) >= 2 and balances[1] > 0 and (balances[0] / balances[1]) > 3:
            results["cliff_distribution"] = True

        # --- Decimal Pattern Check ---
        clean_ints = sum(1 for b in balances if float(b).is_integer())
        if clean_ints >= 3:
            results["decimal_pattern"] = True

        # --- Entropy Check ---
        entropy = -sum(p * math.log2(p) for p in proportions if p > 0)
        results["entropy_score"] = round(entropy, 3)
        if entropy < 2.5:
            results["low_entropy"] = True

        return results

    except Exception as e:
        print(f"[pattern_detector] Error: {str(e)}")
        return {
            "uniform_balance": False,
            "cliff_distribution": False,
            "decimal_pattern": False,
            "low_entropy": False,
            "entropy_score": 0
        }
