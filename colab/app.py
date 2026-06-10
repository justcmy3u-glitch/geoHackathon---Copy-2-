import os
import base64
from io import BytesIO
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
import torch
import traceback
import hmac
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from PIL import Image

# Rate Limiter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Geo-RAG Colab API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

COLAB_API_KEY = os.environ.get("COLAB_API_KEY", "default_insecure_key")

async def verify_api_key(x_api_key: str = Header(...)):
    if not hmac.compare_digest(x_api_key.encode('utf-8'), COLAB_API_KEY.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid API key")

MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ"
try:
    print(f"Loading model {MODEL_ID}...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        torch_dtype="auto",
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None
    processor = None

SYSTEM_OCR = """Ты — специализированный OCR для геологических отчётов.
Распознай страницу и верни структурированный Markdown.
ПРАВИЛА:
- Таблицы → строгий GitHub Markdown (|col1|col2|)
- Формулы → LaTeX обёртка ($...$)
- НЕ ИЗМЕНЯЙ геологические термины, индексы пластов, номера скважин
- Заголовки → ## Заголовок (уровень по иерархии страницы)
- Подписи к рисункам → **Рис. N:** Описание
- Если страница нечитаема → верни {"error": "low_quality", "confidence": 0.0}
Верни ТОЛЬКО Markdown, никакого вводного текста."""

SYSTEM_VISION = """Проанализируй геологический графический объект.
Верни JSON строго по схеме:
{
  "graphic_type": "карта_структурная|каротажная_диаграмма|геологический_разрез|корреляционная_схема|фото_керна|другое",
  "key_entities": ["скважина_247", "пласт_БС10", "баженовская_свита"],
  "numerical_values": [{"label": "глубина", "value": 2847, "unit": "м"}],
  "scale_info": "1:50000 или null",
  "coordinates": "координаты углов если есть или null",
  "text_annotations": ["все подписи на рисунке"],
  "description_for_indexing": "Структурная карта кровли пласта БС10 месторождения X. Показаны изолинии глубины от -2700 до -3100 м. Нанесены скважины №247, №312, №445."
}
Отвечай ТОЛЬКО валидным JSON."""

SYSTEM_NER = """Ты — геологический NER-экстрактор. 
Извлеки сущности и связи из геологического текста.
ОТВЕЧАЙ ТОЛЬКО ВАЛИДНЫМ JSON строго по предоставленной схеме:
{
  "entities": [{"entity_id": "уникальный_id", "type": "СКВАЖИНА", "canonical_name": "каноническое имя", "raw_mention": "как написано", "value": "число", "unit": "м"}],
  "relations": [{"subject": "entity_id субъекта", "relation": "ВСКРЫЛ", "object": "entity_id объекта", "meta": {"doc_id": "id", "page": 12, "chunk_id": "uuid", "confidence": 0.95}}]
}
Не добавляй комментарии. Не выдумывай данные.
Нормализуй синонимы к каноническому виду (пласт Ю1-3, а не горизонт Ю₁³)."""

SYSTEM_ANSWER = """Ты — геологический аналитик. Отвечай СТРОГО на основе предоставленного контекста.

ПРАВИЛА (ОБЯЗАТЕЛЬНЫЕ):
1. Для КАЖДОГО факта в ответе вставь ссылку [doc_id:page]
2. Если информации нет в контексте → напиши "Недостаточно информации в предоставленных документах"
3. НЕ используй знания вне контекста
4. Числа, термины, индексы пластов — переписывай точно как в источнике
5. Если несколько источников противоречат → укажи оба с разными ссылками

Формат ответа:
[Прямой ответ на вопрос с ссылками]

Источники использованы: [список doc_id:page]"""

class ImageRequest(BaseModel):
    image_base64: str

class TextRequest(BaseModel):
    text: str
    doc_id: Optional[str] = "doc"
    page: Optional[int] = 1

class GenerateRequest(BaseModel):
    context: str
    question: str
    system_prompt: Optional[str] = SYSTEM_ANSWER
    max_new_tokens: Optional[int] = 1024

def generate_response(messages, max_new_tokens=1024):
    if not model or not processor:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    from qwen_vl_utils import process_vision_info
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to("cuda")
    
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs, 
            max_new_tokens=max_new_tokens,
            do_sample=False
        )
    
    generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
    output_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    return output_text

@app.post("/ocr", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def ocr(request: Request, req: ImageRequest):
    try:
        messages = [{"role": "system", "content": SYSTEM_OCR}, {"role": "user", "content": [{"type": "image", "image": f"data:image/png;base64,{req.image_base64}"}, {"type": "text", "text": "Распознай эту страницу."}]}]
        return {"markdown": generate_response(messages, max_new_tokens=2048)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vision", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def vision(request: Request, req: ImageRequest):
    try:
        messages = [{"role": "system", "content": SYSTEM_VISION}, {"role": "user", "content": [{"type": "image", "image": f"data:image/png;base64,{req.image_base64}"}, {"type": "text", "text": "Верни JSON описание."}]}]
        return {"json_string": generate_response(messages, max_new_tokens=1024)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ner", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
def ner(request: Request, req: TextRequest):
    try:
        user_content = f"Извлеки сущности из текста:\n\n{req.text}\n\nMeta: doc_id={req.doc_id}, page={req.page}"
        messages = [
            {"role": "system", "content": SYSTEM_NER},
            {"role": "user",   "content": user_content},
        ]
        return {"json_string": generate_response(messages, max_new_tokens=1500)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
def generate(request: Request, req: GenerateRequest):
    try:
        user_content = f"Контекст:\n{req.context}\n\nВопрос:\n{req.question}"
        messages = [
            {"role": "system", "content": req.system_prompt},
            {"role": "user",   "content": user_content},
        ]
        return {"response": generate_response(messages, max_new_tokens=req.max_new_tokens)}
    except Exception as e:
        return {"response": f"❌ ОШИБКА НА COLAB СЕРВЕРЕ: {str(e)}\n\nТрассировка:\n{traceback.format_exc()}"}
