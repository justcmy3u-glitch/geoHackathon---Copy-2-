import os
from openai import OpenAI
from core.answer_rules import SYSTEM_PROMPT_ANSWER

class OpenAIClient:
    """
    OpenAI API client for text generation / question answering.
    """
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        else:
            self.client = None
            self.model = None

    def _is_configured(self) -> bool:
        return bool(self.client)

    def generate_answer(self, context: str, question: str) -> str:
        """
        Generate an answer using OpenAI API.
        
        Args:
            context: Context/documents to answer from
            question: User's question
            
        Returns:
            Generated answer as string
        """
        if not self._is_configured():
            return "⚠️ OpenAI API не настроен. Добавьте OPENAI_API_KEY в .env"
        
        try:
            # Build messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
                {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос: {question}"}
            ]
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"❌ Ошибка OpenAI API: {str(e)}"

    def generate(self, question: str, context: str = "") -> str:
        """Alias for generate_answer - used in tests."""
        return self.generate_answer(context=context, question=question)

    def health_check(self) -> dict:
        """
        Check if OpenAI API is configured and accessible.
        """
        if not self._is_configured():
            return {"status": "error", "message": "OPENAI_API_KEY not configured"}
        
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return {"status": "ok", "model": self.model}
        except Exception as e:
            return {"status": "error", "message": str(e)}
