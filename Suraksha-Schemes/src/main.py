import argparse
import pandas as pd
import json
import os
import subprocess
from src.schema import map_my_schema, map_hf_schema
from src.merger import merge_datasets
from src.qdrant_integration import build_qdrant_payloads, upload_to_qdrant

def get_git_revision(repo_dir):
    try:
        rev = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, text=True).strip()
        return rev
    except Exception:
        return "unknown"

def main():
    parser = argparse.ArgumentParser(description="Merge Indian Government Scheme Datasets and Ingest into Qdrant")
    parser.add_argument("--my_csv", default="gov_myscheme_data.csv", help="Path to existing dataset CSV")
    parser.add_argument("--hf_csv", default="indian-government-schemes-2025/Schemes.csv", help="Path to HF dataset CSV")
    parser.add_argument("--out_csv", default="data/processed/schemes_canonical.csv")
    parser.add_argument("--out_json", default="data/processed/schemes_canonical.json")
    parser.add_argument("--out_jsonl", default="data/processed/qdrant_documents.jsonl")
    parser.add_argument("--report", default="reports/merge_summary.json")
    parser.add_argument("--upload", action="store_true", help="Upload to Qdrant (disables dry-run)")
    args = parser.parse_args()

    print("Loading datasets...")
    my_df = pd.read_csv(args.my_csv)
    hf_df = pd.read_csv(args.hf_csv)

    print("Mapping schemas...")
    my_canonical = map_my_schema(my_df)
    hf_canonical = map_hf_schema(hf_df)

    print("Merging datasets...")
    merged_df, report = merge_datasets(my_canonical, hf_canonical)
    
    # Metadata gathering
    hf_repo_dir = os.path.dirname(args.hf_csv)
    if os.path.isdir(os.path.join(hf_repo_dir, '.git')):
        report['hf_git_revision'] = get_git_revision(hf_repo_dir)

    print("Writing outputs...")
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    
    merged_df.to_csv(args.out_csv, index=False)
    merged_df.to_json(args.out_json, orient='records', indent=2)
    
    with open(args.report, 'w') as f:
        json.dump(report, f, indent=2)

    print("Generating RAG chunks...")
    chunks = build_qdrant_payloads(merged_df, args.out_jsonl)
    report['total_chunks'] = len(chunks)
    
    print(json.dumps(report, indent=2))
    
    dry_run = not args.upload
    upload_to_qdrant(chunks, dry_run=dry_run)

if __name__ == "__main__":
    main()
