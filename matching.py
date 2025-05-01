# File: matching.py
from thefuzz import process
import constants  # Import constants

# Attempt to import Gemini library, handle if not installed
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    print(
        "WARNING: google-generativeai library not found. Gemini AI functionality will be disabled."
    )
    GEMINI_AVAILABLE = False
    genai = None


def find_best_sku_match_fuzzy(product_name, sku_list, threshold):
    """Finds the best matching SKU using fuzzy matching."""
    if not product_name or not sku_list:
        return constants.NO_MATCH_TEXT
    try:
        result = process.extractOne(str(product_name), sku_list)
        if result:
            best_match, score = result
            if score >= threshold:
                return best_match
            else:
                return constants.NO_MATCH_TEXT
        else:
            return constants.NO_MATCH_TEXT
    except Exception as e:
        print(f"Error during fuzzy matching for '{product_name}': {e}")
        return "--- ERROR DURING FUZZY MATCH ---"


def find_best_sku_match_gemini(
    product_name, sku_list, api_key, model_name, instructions
):
    """Matches product name to SKU list using Gemini AI."""
    if not GEMINI_AVAILABLE:
        return "--- GEMINI LIBRARY NOT INSTALLED ---"
    if not product_name or not sku_list:
        return constants.NO_MATCH_TEXT
    if not api_key:
        print("Error: Gemini API key not provided.")
        return "--- ERROR: MISSING API KEY ---"
    if not model_name:
        print("Error: Gemini model name not provided.")
        return "--- ERROR: MISSING MODEL NAME ---"
    if not instructions:
        print("Error: Gemini prompt instructions not provided.")
        return "--- ERROR: MISSING INSTRUCTIONS ---"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt = f"""Analyze the following product name and list of SKUs. Identify the single best matching SKU from the list provided.

Product Name: "{product_name}"

Available SKUs:
{chr(10).join(f"- {sku}" for sku in sku_list)}

{instructions}
"""
        response = model.generate_content(prompt)
        try:
            gemini_result = response.text.strip()
            if gemini_result == "NO MATCH":
                return constants.NO_MATCH_TEXT  # Use constant
            elif gemini_result in sku_list:
                return gemini_result
            else:
                print(
                    f"Warning: Gemini returned ('{gemini_result}') not exactly in SKU list or 'NO MATCH'. Treating as no match."
                )
                return constants.NO_MATCH_TEXT
        except ValueError:
            print(
                f"Warning: Gemini response blocked or empty for '{product_name}'. Parts: {response.parts}"
            )
            return "--- GEMINI RESPONSE BLOCKED/EMPTY ---"
        except Exception as e_parse:
            print(f"Error parsing Gemini response for '{product_name}': {e_parse}")
            return "--- ERROR PARSING GEMINI RESPONSE ---"

    except Exception as e_api:
        print(
            f"Error during Gemini API call for '{product_name}' (Model: {model_name}): {e_api}"
        )
        if "API key not valid" in str(e_api):
            return "--- ERROR: INVALID API KEY ---"
        if (
            "not found" in str(e_api).lower()
            or "permission denied" in str(e_api).lower()
        ):
            return f"--- ERROR: MODEL '{model_name}' NOT FOUND/ACCESSIBLE ---"
        return "--- ERROR DURING GEMINI API CALL ---"
