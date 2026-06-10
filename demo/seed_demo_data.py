#!/usr/bin/env python3
"""Seed demo geological data for testing search without uploading PDFs."""
import sys
sys.path.insert(0, '.')

from indexer.bm25_index import BM25Index
from indexer.qdrant_writer import QdrantWriter
from indexer.embedder import Embedder
import uuid

# Demo geological chunks
DEMO_CHUNKS = [
    {
        "doc_id": "demo_report_01",
        "page_num": 1,
        "chunk_id": str(uuid.uuid4()),
        "content": "Скважина № 247 вскрыла баженовскую свиту на глубине 2850 метров. Коэффициент пористости Кп = 0.21, коэффициент нефтенасыщенности Кн = 0.68. Толщина продуктивного пласта составила 12 метров.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_01",
        "page_num": 2,
        "chunk_id": str(uuid.uuid4()),
        "content": "Испытания скважины 247 показали дебит нефти 45 м³/сут при депрессии 8 МПа. Газовый фактор составил 120 м³/м³. Обводнённость продукции 5%.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_02",
        "page_num": 3,
        "chunk_id": str(uuid.uuid4()),
        "content": "Пласт Ю1-3 вскрыт на глубинах от 2790 до 2805 м. Литологически представлен песчаником серым мелкозернистым с прослоями алевролита. Средняя проницаемость 180 мД.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_02",
        "page_num": 5,
        "chunk_id": str(uuid.uuid4()),
        "content": "Скважина 301 пробурена в 2025 году с целью разведки структуры Тенгиз. Вскрыты отложения девона на глубине 4200 метров. Плотность нефти 0.85 г/см³, содержание серы 1.2%.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_03",
        "page_num": 1,
        "chunk_id": str(uuid.uuid4()),
        "content": "Стратиграфический разрез месторождения включает юрские, меловые и палеогеновые отложения. Продуктивными являются горизонты Ю1, Ю2 и АС10.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_03",
        "page_num": 7,
        "chunk_id": str(uuid.uuid4()),
        "content": "По результатам сейсморазведочных работ 3D выявлена антиклинальная структура размером 8x4 км. Амплитуда складки достигает 150 метров. Предполагаемые запасы нефти категории C1 составляют 12 млн тонн.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_04",
        "page_num": 2,
        "chunk_id": str(uuid.uuid4()),
        "content": "Гидродинамические исследования показали пластовое давление 28 МПа при температуре 85°C. Вязкость нефти в пластовых условиях 3.5 мПа·с.",
        "type": "text",
    },
    {
        "doc_id": "demo_report_04",
        "page_num": 4,
        "chunk_id": str(uuid.uuid4()),
        "content": "Керновый материал из интервала 2850-2862 м представлен карбонатными породами с высокой трещиноватостью. Открытая пористость 18%, эффективная пористость 14%.",
        "type": "text",
    },
]


def seed_demo_data():
    print("[DEMO] Seeding demo geological data...")
    
    # Initialize BM25
    bm25 = BM25Index()
    bm25.clear()  # Clear existing if any
    
    for chunk in DEMO_CHUNKS:
        bm25.add_document(
            chunk["chunk_id"],
            chunk["content"],
            metadata={
                "doc_id": chunk["doc_id"],
                "page_num": chunk["page_num"],
                "type": chunk["type"],
            }
        )
    
    bm25.save()
    print(f"[DEMO] ✅ Indexed {len(DEMO_CHUNKS)} demo chunks into BM25")
    
    # Optional: add to Qdrant if available
    try:
        embedder = Embedder()
        qdrant = QdrantWriter()
        
        for chunk in DEMO_CHUNKS:
            embedding = embedder.embed_text(chunk["content"])
            qdrant.upsert_point(
                point_id=chunk["chunk_id"],
                vector=embedding,
                payload={
                    "content": chunk["content"],
                    "doc_id": chunk["doc_id"],
                    "page_num": chunk["page_num"],
                    "type": chunk["type"],
                }
            )
        print(f"[DEMO] ✅ Indexed {len(DEMO_CHUNKS)} demo chunks into Qdrant")
    except Exception as e:
        print(f"[DEMO] ⚠️  Qdrant not available: {e}. BM25-only mode.")
    
    print("[DEMO] 🎉 Demo data ready! You can now search for geological info.")


if __name__ == "__main__":
    seed_demo_data()
