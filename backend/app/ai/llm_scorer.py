import httpx
import json
import time
from typing import Dict, Any
from app.config import settings
import redis

class LLMScorer:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.max_retries = 3
        self.backoff_base = 2
        self.cache_ttl = 3600
        
        try:
            self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        except:
            self.redis_client = None
    
    def _get_cache_key(self, transcript: str) -> str:
        import hashlib
        return f"llm_score:{hashlib.md5(transcript.encode()).hexdigest()}"
    
    def _get_cached(self, cache_key: str) -> Dict[str, Any]:
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        return None
    
    def _set_cached(self, cache_key: str, data: Dict[str, Any]):
        if self.redis_client:
            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(data))
    
    async def score_segment(self, transcript: str, duration: float, video_topic: str) -> Dict[str, Any]:
        cache_key = self._get_cache_key(transcript)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        prompt = self._build_prompt(transcript, duration, video_topic)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.api_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://autoclip.ai",
                            "X-Title": "AutoClip AI"
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": "Anda adalah AI video editor senior yang mengevaluasi segmen video."},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.3,
                            "max_tokens": 800,
                            "response_format": {"type": "json_object"}
                        }
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        result = json.loads(content)
                    except json.JSONDecodeError:
                        # Try to extract JSON from markdown
                        import re
                        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group(1))
                        else:
                            raise Exception("Failed to parse LLM response")
                    
                    scores = {
                        "completeness": self._clamp_score(result.get("completeness", {}).get("score", 5)),
                        "relevance": self._clamp_score(result.get("relevance", {}).get("score", 5)),
                        "engagement": self._clamp_score(result.get("engagement", {}).get("score", 5)),
                        "clarity": self._clamp_score(result.get("clarity", {}).get("score", 5)),
                        "emotion": self._clamp_score(result.get("emotion", {}).get("score", 5)),
                        "reasoning": result.get("completeness", {}).get("reasoning", "")
                    }
                    
                    self._set_cached(cache_key, scores)
                    return scores
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base ** attempt
                    time.sleep(wait_time)
                else:
                    # Fallback ke nilai default
                    return {
                        "completeness": 5.0,
                        "relevance": 5.0,
                        "engagement": 5.0,
                        "clarity": 5.0,
                        "emotion": 5.0,
                        "reasoning": f"Error: {str(e)}"
                    }
    
    def _build_prompt(self, transcript: str, duration: float, video_topic: str) -> str:
        return f"""Kamu adalah AI video editor senior. Tugasmu mengevaluasi segmen video berikut berdasarkan 5 dimensi. Berikan skor 1-10 untuk setiap dimensi dan penjelasan singkat.

SEGmen:
- Transkrip: "{transcript}"
- Durasi: {duration:.1f} detik
- Topik Video: {video_topic}

DIMENSI EVALUASI:
1. Completeness (Kelengkapan): Apakah segmen berisi pikiran/informasi yang utuh dan tidak terpotong di tengah kalimat?
2. Relevance (Relevansi): Seberapa relevan konten segmen dengan topik utama video?
3. Engagement Potential: Seberapa besar kemungkinan segmen menarik perhatian penonton dalam 3 detik pertama?
4. Standalone Clarity: Apakah segmen dapat dipahami tanpa konteks video lainnya?
5. Energy & Emotion: Apakah ada emosi, humor, kejutan, atau momen impactful?

FORMAT OUTPUT (JSON):
{{
    "completeness": {{"score": 0, "reasoning": ""}},
    "relevance": {{"score": 0, "reasoning": ""}},
    "engagement": {{"score": 0, "reasoning": ""}},
    "clarity": {{"score": 0, "reasoning": ""}},
    "emotion": {{"score": 0, "reasoning": ""}}
}}"""
    
    def _clamp_score(self, score: Any) -> float:
        try:
            s = float(score)
            return max(1.0, min(10.0, s))
        except (TypeError, ValueError):
            return 5.0

llm_scorer = LLMScorer()
