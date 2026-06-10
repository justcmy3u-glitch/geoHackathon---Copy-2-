#!/usr/bin/env python3
"""Load PDF files from demo/documents/ folder and index them."""
import sys
import os
from pathlib import Path
sys.path.insert(0, '.')

from indexer.bm25_index import BM25Index
from indexer.qdrant_writer import QdrantWriter
from indexer.embedder import Embedder
from parser.pdf_extractor import extract_text_from_pdf
from indexer.geo_chunker import chunk_text
import uuid

# Folder to scan for PDFs
DOCUMENTS_FOLDER = Path("demo/documents")

def load_pdfs():
    """Scan documents folder and index all PDFs."""
    
    # Create documents folder if it doesn't exist
    DOCUMENTS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(DOCUMENTS_FOLDER.glob("*.pdf"))
    
    if not pdf_files:
        print(f"[LOAD] ⚠️  No PDF files found in {DOCUMENTS_FOLDER}")
        print(f"[LOAD] 📁 Put your PDF files into: {DOCUMENTS_FOLDER.absolute()}")
        return
    
    print(f"[LOAD] 📄 Found {len(pdf_files)} PDF file(s) to process")
    
    # Initialize indexers
    bm25 = BM25Index()
    bm25.clear()
    
    try:
        embedder = Embedder()
        qdrant = QdrantWriter()
        use_qdrant = True
        print("[LOAD] ✅ Qdrant connection available")
    except Exception as e:
        use_qdrant = False
        print(f"[LOAD] ⚠️  Qdrant not available: {e}. Using BM25 only.")
    
    total_chunks = 0
    
    for pdf_file in pdf_files:
        print(f"\n[LOAD] Processing: {pdf_file.name}")
        doc_id = pdf_file.stem  # filename without extension
        
        try:
            # Extract text from PDF
            pages = extract_text_from_pdf(str(pdf_file))
            
            for page_num, page_text in enumerate(pages, start=1):
                if not page_text.strip():
                    continue
                    
                # Chunk the page text
                chunks = chunk_text(page_text, max_chunk_size=500)
                
                for chunk_text in chunks:
                    if len(chunk_text.strip()) < 50:  # Skip very short chunks
                        continue
                    
                    chunk_id = str(uuid.uuid4())
                    
                    # Add to BM25
                    bm25.add_document(
                        chunk_id,
                        chunk_text,
                        metadata={
                            "doc_id": doc_id,
                            "page_num": page_num,
                            "type": "text",
                            "filename": pdf_file.name
                        }
                    )
                    
                    # Add to Qdrant if available
                    if use_qdrant:
                        try:
                            embedding = embedder.embed_text(chunk_text)
                            qdrant.upsert_point(
                                point_id=chunk_id,
                                vector=embedding,
                                payload={
                                    "content": chunk_text,
                                    "doc_id": doc_id,
                                    "page_num": page_num,
                                    "type": "text",
                                    "filename": pdf_file.name
                                }
                            )
                        except Exception as e:
                            print(f"[LOAD] ⚠️  Qdrant error for chunk: {e}")
                    
                    total_chunks += 1
            
            print(f"[LOAD] ✅ {pdf_file.name}: Indexed {total_chunks} chunks")
            
        except Exception as e:
            print(f"[LOAD] ❌ Error processing {pdf_file.name}: {e}")
            continue
    
    # Save BM25 index
    bm25.save()
    
    print(f"\n[LOAD] 🎉 Complete! Indexed {total_chunks} chunks from {len(pdf_files)} PDF(s)")
    print(f"[LOAD] 💡 You can now search for information from your documents!")

if __name__ == "__main__":
    load_pdfs()
