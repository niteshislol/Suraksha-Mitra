import json
import uuid
import pandas as pd
import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance

def split_text_into_chunks(text, max_length=1000):
    """Splits text into chunks of max_length characters without breaking words."""
    if not text:
        return []
    words = text.split()
    chunks = []
    current_chunk = []
    current_len = 0
    
    for word in words:
        if current_len + len(word) + 1 > max_length and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_len = len(word)
        else:
            current_chunk.append(word)
            current_len += len(word) + 1
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def generate_chunks(row):
    chunks = []
    base_meta = {
        "scheme_id": row.get('scheme_id'),
        "scheme_name": row.get('name'),
        "slug": row.get('slug'),
        "state": row.get('state'),
        "ministry": row.get('ministry'),
        "department": row.get('department'),
        "level": row.get('level'),
        "category": row.get('category'),
        "source_provenance": row.get('source_provenance'),
        "verification_status": row.get('verification_status'),
        "eligibility_gender": row.get('eligibility_gender'),
        "eligibility_bpl": row.get('eligibility_bpl')
    }
    
    seen_texts = set()
    
    def add_chunk(chunk_type, text):
        if pd.isna(text) or not str(text).strip(): return
        
        # Split long text to avoid embedding truncation (model limit is ~256 tokens)
        text_parts = split_text_into_chunks(str(text), max_length=800)
        
        for i, part in enumerate(text_parts):
            # Basic deduplication of identical text chunks within the same scheme
            if part in seen_texts:
                continue
            seen_texts.add(part)
            
            meta = base_meta.copy()
            meta['chunk_type'] = chunk_type
            
            # Unique ID for each sub-chunk
            unique_id_str = str(row.get('scheme_id')) + chunk_type + str(i) + part[:20]
            
            chunks.append({
                "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_URL, unique_id_str)),
                "text": f"Scheme Name: {row.get('name')}\nCategory: {row.get('category')}\n{chunk_type.replace('_', ' ').title()}:\n{part}",
                "metadata": meta
            })
            
    add_chunk("scheme_summary", row.get('description'))
    add_chunk("eligibility", row.get('eligibility_text'))
    add_chunk("benefits", row.get('benefits'))
    add_chunk("application_process", row.get('application_process'))
    add_chunk("documents_required", row.get('documents_required'))
    add_chunk("exclusions", row.get('exclusions'))
    
    # FAQ parsing
    faqs_text = str(row.get('faqs')) if pd.notna(row.get('faqs')) else ""
    if "Q:" in faqs_text and "A:" in faqs_text:
        parts = faqs_text.split("Q:")
        for idx, part in enumerate(parts):
            if not part.strip(): continue
            if "A:" in part:
                add_chunk(f"faq_{idx}", f"Q:{part.strip()}")
            else:
                add_chunk(f"faq_{idx}", part.strip())
    else:
        add_chunk("faq", row.get('faqs'))
        
    return chunks

def build_qdrant_payloads(merged_df, output_jsonl):
    all_chunks = []
    for _, row in merged_df.iterrows():
        chunks = generate_chunks(row)
        all_chunks.extend(chunks)
        
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        for c in all_chunks:
            f.write(json.dumps(c) + '\n')
            
    return all_chunks

def upload_to_qdrant(chunks, collection_name="indian_schemes", db_path="data/qdrant_db", dry_run=True):
    print(f"Loading embedding model (LaBSE - multilingual 109 languages)...")
    # LaBSE supports 109 languages including Hindi, Tamil, Telugu, Bengali, etc.
    model = SentenceTransformer('sentence-transformers/LaBSE')
    
    if dry_run:
        print(f"DRY RUN: Would upload {len(chunks)} chunks to Qdrant collection '{collection_name}'.")
        return
        
    qdrant_url = os.environ.get("QDRANT_CLUSTER_URL")
    qdrant_key = os.environ.get("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        print(f"Connecting to Qdrant Cloud at {qdrant_url}...")
        client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=60.0)
    else:
        print(f"Connecting to local Qdrant at {db_path}...")
        client = QdrantClient(path=db_path, timeout=60.0)
    
    # Check if collection exists
    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)  # LaBSE = 768 dims
        )
        print(f"Created collection {collection_name}")
        
    import sys, time
    batch_size = 500
    print(f"Generating embeddings and upserting {len(chunks):,} points in batches of {batch_size}...")
    sys.stdout.flush()
    
    # Process in batches
    start_time = time.time()
    
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        texts = [c['text'] for c in batch_chunks]
        embeddings = model.encode(texts, show_progress_bar=False)
        
        batch_points = []
        for j, chunk in enumerate(batch_chunks):
            batch_points.append(PointStruct(
                id=chunk['chunk_id'],
                vector=embeddings[j].tolist(),
                payload={**chunk['metadata'], "text": chunk['text']}
            ))
            
        client.upsert(
            collection_name=collection_name,
            points=batch_points
        )
        
        done = i + len(batch_chunks)
        pct = done / len(chunks) * 100
        elapsed = time.time() - start_time
        rate = done / elapsed if elapsed > 0 else 1
        eta_sec = (len(chunks) - done) / rate if rate > 0 else 0
        eta_min = eta_sec / 60
        print(f"  [{pct:5.1f}%] {done:,}/{len(chunks):,} points | ETA: {eta_min:.1f} min", flush=True)
    
    print("✅ Upload complete!")
