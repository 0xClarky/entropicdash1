# utils/rpc.py

import requests
from others.settings import HELIUS_ENDPOINT

HEADERS = {"Content-Type": "application/json"}

def helius_rpc_request(method: str, params: list):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    response = requests.post(HELIUS_ENDPOINT, headers=HEADERS, json=payload)
    response.raise_for_status()
    result = response.json()
    if "error" in result:
        raise Exception(result["error"])
    return result["result"]

def get_account_info(pubkey: str, encoding="base64"):
    return helius_rpc_request("getAccountInfo", [pubkey, {"encoding": encoding}])

def get_token_largest_accounts(mint: str):
    return helius_rpc_request("getTokenLargestAccounts", [mint])

def get_token_supply(mint: str):
    return helius_rpc_request("getTokenSupply", [mint])

def get_transaction(signature: str):
    return helius_rpc_request("getTransaction", [signature, {
        "encoding": "json",
        "maxSupportedTransactionVersion": 0
    }])

def get_signatures_for_address(address: str, limit=20, before=None, until=None):
    params = [address, {"limit": limit}]
    if before:
        params[1]["before"] = before
    if until:
        params[1]["until"] = until
    result = helius_rpc_request("getSignaturesForAddress", params)
    if isinstance(result, list):  # Ensure the result is wrapped in a dictionary
        return {"value": result}
    return result
