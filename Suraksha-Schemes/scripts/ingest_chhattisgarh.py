import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Add the parent directory to the path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.qdrant_integration import build_qdrant_payloads, upload_to_qdrant

def main():
    load_dotenv()
    
    csv_path = r"C:\Users\nites\Downloads\Suraksha-Schemes\Chhattisgarh Data\chhattisgarh_schemes_canonical_asof_2026-09-30.csv"
    jsonl_output = "chhattisgarh_chunks.jsonl"
    
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} schemes.")
    
    print("Chunking data...")
    chunks = build_qdrant_payloads(df, jsonl_output)
    print(f"Generated {len(chunks)} chunks and saved to {jsonl_output}.")
    print("\n✅ JSONL Conversion Complete!")
    print("You can now upload 'chhattisgarh_chunks.jsonl' to Google Colab to perform the high-speed CUDA embedding.")
    
if __name__ == "__main__":
    main()
