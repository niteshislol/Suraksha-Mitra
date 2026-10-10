import json
from src.qdrant_integration import upload_to_qdrant

def main():
    print("Loading chunks from qdrant_documents.jsonl...")
    chunks = []
    with open('data/processed/qdrant_documents.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
            
    print(f"Total chunks found: {len(chunks)}")
    
    # We know 2500 points were successfully uploaded.
    skip_count = 2500
    
    if len(chunks) > skip_count:
        remaining_chunks = chunks[skip_count:]
        print(f"Skipping the first {skip_count} chunks that were already uploaded.")
        print(f"Resuming upload for the remaining {len(remaining_chunks)} chunks...")
        
        upload_to_qdrant(remaining_chunks, dry_run=False)
    else:
        print("All chunks have already been processed.")

if __name__ == "__main__":
    main()
