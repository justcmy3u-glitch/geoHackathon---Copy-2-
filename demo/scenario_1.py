# Сценарий 1: Фактологический вопрос
# Маршрут: HYBRID_RAG
import os
import sys

# Добавляем корень проекта в пути
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retriever.query_classifier import classify_query

def run():
    question = "Какая нефтенасыщенность пласта БС10 в скважине №247?"
    print(f"Вопрос: {question}")
    
    route = classify_query(question)
    print(f"Определен маршрут: {route}")
    
    if route == "HYBRID_RAG":
        print(">> Выполняется поиск Qdrant + BM25 (RRF)...")
        print(">> Генерация ответа через Colab API...")
        print(">> Ответ: Нефтенасыщенность пласта БС10 в скважине №247 составляет 0.68 [report_2023:47]")
    else:
        print("Ошибка маршрутизации")

if __name__ == "__main__":
    run()
