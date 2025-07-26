# utils/parser.py

import base64
from construct import Struct, Int8ul, Int64ul, Flag, Bytes
from utils.settings import RISKY_EXTENSIONS

# === SPL Token Base Mint Layout ===
BASE_MINT_LAYOUT = Struct(
    "mint_authority_option" / Int8ul,
    "mint_authority" / Bytes(32),
    "supply" / Int64ul,
    "decimals" / Int8ul,
    "is_initialized" / Flag,
    "freeze_authority_option" / Int8ul,
    "freeze_authority" / Bytes(32),
)

def decode_base64_to_bytes(data: str) -> bytes:
    return base64.b64decode(data)

def parse_mint_layout(account_data: str) -> dict:
    decoded = decode_base64_to_bytes(account_data)
    return BASE_MINT_LAYOUT.parse(decoded)

def extract_extension_status(account_data: str) -> dict:
    decoded = decode_base64_to_bytes(account_data)
    extensions = {}
    for byte in decoded[82:]:
        ext_id = int(byte)
        if ext_id in RISKY_EXTENSIONS:
            extensions[RISKY_EXTENSIONS[ext_id]] = True
    return extensions
