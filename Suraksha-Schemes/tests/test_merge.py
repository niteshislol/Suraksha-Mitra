import pytest
import pandas as pd
from src.cleaning import normalize_text, validate_url
from src.schema import map_my_schema, map_hf_schema
from src.merger import merge_datasets, smart_merge_text

def test_normalize_text():
    assert normalize_text("Hello\r\nWorld") == "Hello\nWorld"
    assert normalize_text(None) is None
    assert normalize_text("  ") is None

def test_validate_url():
    assert validate_url("http://example.com") == "http://example.com"
    assert validate_url("invalid_url") is None

def test_smart_merge_text():
    # If one is missing, return the other
    assert smart_merge_text("Text A", None) == "Text A"
    assert smart_merge_text(None, "Text B") == "Text B"
    # If identical
    assert smart_merge_text("Text A", "Text A") == "Text A"
    # If one is substring
    assert smart_merge_text("Text", "Text with more details") == "Text with more details"
    assert smart_merge_text("Text with more details", "Text") == "Text with more details"
    # Conflict
    assert "Source 1" in smart_merge_text("Apple", "Banana")

def test_map_schemas():
    my_df = pd.DataFrame([{
        "Scheme Slug": "slug-1",
        "Scheme Name": "Scheme 1",
        "Level": "State",
        "State / UT / Ministry": "Tamil Nadu",
        "Frequently Asked Questions (FAQs)": "FAQ 1"
    }])
    
    hf_df = pd.DataFrame([{
        "slug": "slug-1",
        "name": "Scheme 1",
        "state": "Tamil Nadu",
        "eligibility_text": "Elig 1"
    }])
    
    my_can = map_my_schema(my_df)
    hf_can = map_hf_schema(hf_df)
    
    assert my_can.iloc[0]['state'] == "Tamil Nadu"
    assert hf_can.iloc[0]['eligibility_text'] == "Elig 1"

def test_merge_datasets():
    my_df = pd.DataFrame([{
        "slug": "slug-1",
        "name": "Scheme 1",
        "state": "Tamil Nadu",
        "faqs": "FAQ 1"
    }])
    
    hf_df = pd.DataFrame([{
        "slug": "slug-1",
        "name": "Scheme 1",
        "state": "Tamil Nadu",
        "eligibility_text": "Elig 1"
    }])
    
    merged_df, report = merge_datasets(my_df, hf_df)
    
    assert len(merged_df) == 1
    row = merged_df.iloc[0]
    assert row['faqs'] == "FAQ 1"
    assert row['eligibility_text'] == "Elig 1"
    assert row['scheme_id'] is not None

def test_qdrant_payloads_metadata():
    from src.qdrant_integration import generate_chunks
    row = pd.Series({
        "scheme_id": "test-id",
        "name": "Test Scheme",
        "category": "Test Category",
        "description": "Test Desc",
        "eligibility_text": "Test Elig"
    })
    chunks = generate_chunks(row)
    # 2 chunks expected: summary and eligibility
    assert len(chunks) == 2
    assert chunks[0]['metadata']['chunk_type'] == "scheme_summary"
    assert chunks[1]['metadata']['chunk_type'] == "eligibility"
