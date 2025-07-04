import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get HELIUS_ENDPOINT with a more descriptive error
HELIUS_ENDPOINT = os.getenv("HELIUS_ENDPOINT")
if not HELIUS_ENDPOINT:
    raise ValueError(
        "HELIUS_ENDPOINT is not set. Please:\n"
        "1. Create a .env file in the project root\n"
        "2. Add HELIUS_ENDPOINT='your-endpoint-url' to it\n"
        "3. Make sure you have python-dotenv installed"
    )

# Heuristics
TOP_HOLDER_COUNT = 20
DUMP_THRESHOLD = 0.10  # 10%
DISPLAY_SUPPLY_FALLBACK = 1_000_000_000

# RPC defaults
TX_FETCH_LIMIT = 5
ACCOUNT_FETCH_LIMIT = 1000

# Risky Token-2022 extension IDs
RISKY_EXTENSIONS = {
    1: "transfer_fee_config",
    6: "permanent_delegate",
    9: "default_account_state",
    12: "non_transferable",
    13: "transfer_hook",
}
