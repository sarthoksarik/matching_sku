# File: constants.py

# Matching Settings
DEFAULT_THRESHOLD = 70
NO_MATCH_TEXT = "--- NO MATCH FOUND ---"

# Engine Names
ENGINE_FUZZY = "fuzzy"
ENGINE_GEMINI = "gemini"

# API Key Handling
GEMINI_API_ENV_VAR = "GEMINI_API_KEY"
API_KEY_FILENAME = "api_key.txt"

# Gemini Model Settings
AVAILABLE_GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    # Add newer models here as needed, e.g.:
    # 'gemini-2.5-pro'
]
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"  # Default model selection

# Default Gemini Prompt Instructions
DEFAULT_GEMINI_INSTRUCTIONS = """Your Task: Carefully analyze the 'Product Name'. First, determine if it describes a product potentially related to the 'Available SKUs'.

- If the 'Product Name' appears irrelevant (e.g., contains non-product text like "Total:", "Notes:", "--", "Subtotal:", random characters, or seems like metadata rather than a product) OR if it describes a product but no SKU in the provided 'Available SKUs' list is a good semantic match, respond ONLY with the exact text: NO MATCH

- Otherwise (if the 'Product Name' is relevant and a suitable match exists in the list), respond ONLY with the single best matching SKU name exactly as it appears in the list.

Strictly adhere to the output format: only the matching SKU from the list or the exact phrase "NO MATCH". Do not add any explanations or other text."""

# Database Settings Key
DB_SETTING_GEMINI_INSTRUCTIONS = "gemini_instructions"
