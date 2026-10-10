# Install required libraries (Run this line in a separate cell with a ! if not already installed)
# !pip install -q qdrant-client sentence-transformers

import json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
import time

# 1. Credentials
QDRANT_URL = "https://2ef173e3-b519-4f8a-b003-2d095e6a6771.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6NzJkNzQ1YTktMDdhZC00NzI2LTkxZjYtM2JhMmY2MTFiZWI1In0.XdpEOBpexsyGS6LMI_HegTgOYwjbf5pw5SxuqthntY4"

# 2. Connect to Qdrant Cloud
print("Connecting to Qdrant...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60.0)

# 3. Load Model specifically onto the GPU (The secret sauce for speed)
print("Loading LaBSE model on GPU...")
model = SentenceTransformer('sentence-transformers/LaBSE', device='cuda')

# 4. Read Chunks
print("Reading data...")
chunks = []
with open('qdrant_documents.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        chunks.append(json.loads(line))

# Resume by skipping the first 2,500 that your laptop already completed
chunks = chunks[2500:]
print(f"Uploading the remaining {len(chunks)} chunks...")

# 5. Upload in Batches
collection_name = "indian_schemes"
batch_size = 500
start_time = time.time()

for i in range(0, len(chunks), batch_size):
    batch_chunks = chunks[i:i+batch_size]
    texts = [c['text'] for c in batch_chunks]
    
    # Encode on GPU
    embeddings = model.encode(texts, show_progress_bar=False)
    
    batch_points = []
    for j, chunk in enumerate(batch_chunks):
        batch_points.append(PointStruct(
            id=chunk['chunk_id'],
            vector=embeddings[j].tolist(),
            payload={**chunk['metadata'], "text": chunk['text']}
        ))
        
    client.upsert(collection_name=collection_name, points=batch_points)
    
    done = i + len(batch_chunks)
    pct = done / len(chunks) * 100
    elapsed = time.time() - start_time
    rate = done / elapsed if elapsed > 0 else 1
    eta_min = (len(chunks) - done) / rate / 60 if rate > 0 else 0
    print(f"[{pct:5.1f}%] {done:,}/{len(chunks):,} uploaded | ETA: {eta_min:.1f} min")

print("✅ Upload completely finished!")
