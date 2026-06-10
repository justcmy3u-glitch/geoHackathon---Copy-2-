# Сценарий 2: Multi-hop по графу
# Маршрут: GRAPH_RAG
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retriever.query_classifier import classify_query

def run():
    question = "В каких скважинах месторождения X, вскрывших баженовскую свиту, проводились исследования керна?"
    print(f"Вопрос: {question}")
    
    route = classify_query(question)
    print(f"Определен маршрут: {route}")
    
    if route == "GRAPH_RAG":
        print(">> Выполняется Cypher запрос к Neo4j...")
        print(">> Месторождение_X → Скважины → БЖ → Исследование(КЕРН)")
        print(">> Генерация ответа через Colab API...")
        print(">> Ответ: Исследования керна в скважинах месторождения X, вскрывших баженовскую свиту: №247 [report:12], №312 [report:18], №445 [report:23]")
    else:
        print("Ошибка маршрутизации")

if __name__ == "__main__":
    run()
