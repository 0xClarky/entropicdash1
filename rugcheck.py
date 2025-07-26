import requests
import json
from typing import Dict

class RugcheckAPI:
    def __init__(self):
        self.base_url = "https://api.rugcheck.xyz/v1"
        self.headers = {
            "Content-Type": "application/json"
        }

    def get_token_report(self, token_address: str) -> Dict:
        """Get full token report for a given token mint"""
        try:
            endpoint = f"{self.base_url}/tokens/{token_address}/report"
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Ensure we have a valid response structure
            if not isinstance(data, dict):
                return {
                    "risks": [],
                    "creatorTokens": None,
                    "insiderNetworks": None,
                    "token": {"supply": 1, "decimals": 0}
                }
            
            # Validate and sanitize the response
            sanitized_data = {
                "risks": data.get("risks", []) or [],  # Convert None to empty list
                "creatorTokens": data.get("creatorTokens"),
                "insiderNetworks": data.get("insiderNetworks", []) or [],  # Convert None to empty list
                "token": data.get("token", {}) or {}  # Convert None to empty dict
            }
            
            # Ensure token data has required fields
            if "token" in sanitized_data:
                token_data = sanitized_data["token"]
                sanitized_data["token"] = {
                    "supply": int(token_data.get("supply", 1) or 1),  # Convert None/0 to 1
                    "decimals": int(token_data.get("decimals", 0) or 0)  # Convert None to 0
                }
            
            return sanitized_data
            
        except requests.exceptions.RequestException as e:
            print(f"API Error for {token_address}: {e}")
            return {
                "risks": [],
                "creatorTokens": None,
                "insiderNetworks": None,
                "token": {"supply": 1, "decimals": 0}
            }

def main():
    rugcheck = RugcheckAPI()

    try:
        # Example token address for report
        token_address = "963sLpcVZEyZ7WwgiEZ2BV5EGmcbRPAr9itTuWscTSVq"

        # Get token report
        token_report = rugcheck.get_token_report(token_address)

        # Extract the total supply and decimals from the token data
        total_supply = token_report.get("token", {}).get("supply", 1)  # Default to 1 to avoid division by zero
        decimals = token_report.get("token", {}).get("decimals", 0)
        total_supply_ui = total_supply / (10 ** decimals)  # Adjust for decimals

        # Extract only the requested fields
        filtered_report = {
            "risks": token_report.get("risks"),
            "creatorTokens": token_report.get("creatorTokens"),
            "insiderNetworks": token_report.get("insiderNetworks"),
        }

        # Print the filtered report in a cleaner format
        print("\n--- Token Risk Report ---")
        risks = filtered_report.get("risks", [])
        if risks:
            for risk in risks:
                print(f"- {risk['name']} (Level: {risk['level']}, Value: {risk.get('value', 'N/A')})")
        else:
            print("No risks detected.")

        print("\n--- Creator Tokens ---")
        creator_tokens = filtered_report.get("creatorTokens")
        if creator_tokens:
            print(f"Number of Creator Tokens: {len(creator_tokens)}")
        else:
            print("No creator tokens found.")

        print("\n--- Insider Analysis ---")
        insider_networks = filtered_report.get("insiderNetworks", [])
        if insider_networks:
            for network in insider_networks:
                token_amount = network.get("tokenAmount", 0) / (10 ** decimals)  # Adjust for decimals
                distributed_to_wallets = network.get("activeAccounts", "N/A")
                token_percentage = (token_amount / total_supply_ui) * 100 if total_supply_ui > 0 else 0
                print(f"- Type: {network.get('type')}, "
                      f"Token Amount: {token_amount:.2f} ({token_percentage:.2f}% of Total Supply), "
                      f"Distributed to Wallets: {distributed_to_wallets}")
        else:
            print("No insider networks found.")

    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    main()