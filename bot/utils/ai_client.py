import os
from typing import Optional

import aiohttp


class AIClient:
    def __init__(self, config: dict):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    def _ai_cfg(self) -> dict:
        return self.config.get("ai", {})

    def _provider_order(self) -> list[str]:
        cfg = self._ai_cfg()
        providers = cfg.get("providers")
        if isinstance(providers, list) and providers:
            return [str(p).lower() for p in providers]
        return ["gemini"]

    def _provider_cfg(self, provider: str) -> dict:
        cfg = self._ai_cfg()
        if provider in cfg and isinstance(cfg[provider], dict):
            return cfg[provider]
        return cfg

    def _api_key_for(self, provider: str) -> str | None:
        provider = provider.lower()
        if provider == "gemini":
            return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if provider == "groq":
            return os.getenv("GROQ_API_KEY")
        if provider == "openrouter":
            return os.getenv("OPENROUTER_API_KEY")
        return None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def _call_gemini(self, prompt: str, system_prompt: str | None = None) -> str:
        await self._ensure_session()
        api_key = self._api_key_for("gemini")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set")

        cfg = self._provider_cfg("gemini")
        model = cfg.get("model", "gemini-1.5-flash")
        temperature = float(cfg.get("temperature", 0.6))
        max_tokens = int(cfg.get("max_tokens", 512))
        top_p = float(cfg.get("top_p", 0.9))
        top_k = int(cfg.get("top_k", 40))

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": top_p,
                "topK": top_k,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with self.session.post(url, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Gemini API error {resp.status}: {text}")
            data = await resp.json()

        candidates = data.get("candidates") or []
        if not candidates:
            return "No response from model."

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return "No response from model."

        return "".join(part.get("text", "") for part in parts).strip() or "No response from model."

    async def _call_openai_like(self, provider: str, prompt: str, system_prompt: str | None = None) -> str:
        await self._ensure_session()
        api_key = self._api_key_for(provider)
        if not api_key:
            raise RuntimeError(f"{provider.upper()}_API_KEY not set")

        cfg = self._provider_cfg(provider)
        if provider == "groq":
            model_default = "llama-3.1-8b-instant"
            url = "https://api.groq.com/openai/v1/chat/completions"
        else:
            model_default = "meta-llama/llama-3.1-8b-instruct"
            url = "https://openrouter.ai/api/v1/chat/completions"

        model = cfg.get("model", model_default)
        temperature = float(cfg.get("temperature", 0.6))
        max_tokens = int(cfg.get("max_tokens", 512))
        top_p = float(cfg.get("top_p", 0.9))

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if provider == "openrouter":
            site_url = cfg.get("site_url")
            app_name = cfg.get("app_name")
            if site_url:
                headers["HTTP-Referer"] = site_url
            if app_name:
                headers["X-Title"] = app_name

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }

        async with self.session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"{provider} API error {resp.status}: {text}")
            data = await resp.json()

        choices = data.get("choices") or []
        if not choices:
            return "No response from model."

        content = choices[0].get("message", {}).get("content", "")
        return content.strip() or "No response from model."

    async def call(self, prompt: str, system_prompt: str | None = None) -> str:
        errors = []
        for provider in self._provider_order():
            try:
                if provider == "gemini":
                    return await self._call_gemini(prompt, system_prompt=system_prompt)
                if provider == "groq":
                    return await self._call_openai_like("groq", prompt, system_prompt=system_prompt)
                if provider == "openrouter":
                    return await self._call_openai_like("openrouter", prompt, system_prompt=system_prompt)
                errors.append(f"{provider}: unknown provider")
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue
        raise RuntimeError("All AI providers failed: " + "; ".join(errors))

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
