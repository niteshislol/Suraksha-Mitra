import re
import unicodedata
import pandas as pd
import numpy as np

def normalize_text(text):
    if pd.isna(text) or text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    # Unicode normalization
    text = unicodedata.normalize('NFKC', text)
    # Fix line endings
    text = re.sub(r'\r\n', '\n', text)
    # Remove multiple newlines
    text = re.sub(r'\n+', '\n', text)
    text = text.strip()
    return text if text else None

def validate_url(url):
    if pd.isna(url) or url is None:
        return None
    if not isinstance(url, str):
        url = str(url)
    url = url.strip()
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return None

def deduplicate_list_str(list_str):
    if pd.isna(list_str) or list_str is None:
        return None
    if isinstance(list_str, list):
        return list(dict.fromkeys(list_str))
    
    # Try parsing string representation of list safely
    try:
        import ast
        val = ast.literal_eval(list_str)
        if isinstance(val, list):
             return list(dict.fromkeys(val))
    except (ValueError, SyntaxError):
        pass
    
    return [x.strip() for x in str(list_str).split(',')]

def safe_int(val):
    if pd.isna(val) or val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None

def safe_bool(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, bool):
        return val
    if str(val).lower() in ['true', 'yes', '1']:
        return True
    if str(val).lower() in ['false', 'no', '0']:
        return False
    return None
