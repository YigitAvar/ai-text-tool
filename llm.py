"""LLM sağlayıcı soyutlaması.

Varsayılan sağlayıcı Ollama (yerel). İleride bulut tabanlı başka sağlayıcılar
aynı `LLMProvider` arayüzünü uygulayarak eklenebilir; çağıran kod (`actions.py`)
hangi sağlayıcının kullanıldığını bilmek zorunda kalmaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

# Faz 3'te config'ten gelecek; şimdilik makul varsayılanlar.
# Not: Makinede kurulu olan model llama3.2:3b (hızlı, ~2GB). Plan başta
# qwen2.5:7b-instruct öneriyordu; istenirse config'ten değiştirilebilir.
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 60


class LLMError(Exception):
    """Sağlayıcıyla ilgili, kullanıcıya gösterilebilir hatalar.

    `actions.py`/`notifier.py` bu istisnayı yakalayıp mesajı bildirime
    dönüştürebilir; uygulama çökmemeli.
    """


class LLMProvider(ABC):
    """Tüm LLM sağlayıcılarının uyması gereken arayüz."""

    @abstractmethod
    def complete(self, prompt: str, user: str | None = None) -> str:
        """Modelin yanıtını döndür. İki kullanım biçimi vardır:

        - `complete(prompt)`: her şey tek bir `user` mesajıdır. Çeviri (translate)
          bunu kullanır; qwen2.5'te ölçüldü, çeviride en güvenilir biçim bu.
        - `complete(system, user)`: talimat/kurallar `system` rolüne, işlenecek
          ham metin `user` rolüne gider. summarize/fix/formal bunu kullanır;
          böylece model talimatı içerikle karıştırıp kuralları işlemez.
        """
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """Yerel Ollama sunucusuna `/api/chat` üzerinden bağlanan sağlayıcı."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = 0.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        # Çeviri/düzeltme gibi görevlerde yaratıcılık değil tutarlılık isteriz;
        # temperature=0 modeli deterministik yapıp aynı girdiye aynı çıktıyı
        # vermesini sağlar (küçük modellerde savrulmayı azaltır).
        self.temperature = temperature

    def complete(self, prompt: str, user: str | None = None) -> str:
        url = f"{self.base_url}/api/chat"
        if user is None:
            # Tek user mesajı (translate için).
            messages = [{"role": "user", "content": prompt}]
        else:
            # Talimat system'e, ham metin user'a (summarize/fix/formal için).
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ]
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }

        try:
            response = httpx.post(url, json=payload, timeout=self.timeout_seconds)
        except httpx.ConnectError as exc:
            raise LLMError(
                f"Ollama'ya bağlanılamadı ({self.base_url}). "
                "Ollama çalışıyor mu? `ollama serve` ile başlatmayı dene."
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"Ollama {self.timeout_seconds} sn içinde yanıt vermedi. "
                "Model çok büyük olabilir veya makine yavaş; timeout'u artırmayı dene."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama'ya istek başarısız oldu: {exc}") from exc

        if response.status_code == 404:
            raise LLMError(
                f"Model bulunamadı: '{self.model}'. "
                f"`ollama pull {self.model}` ile indirmen gerekebilir."
            )
        if response.status_code >= 400:
            raise LLMError(
                f"Ollama hata döndürdü (HTTP {response.status_code}): {response.text[:300]}"
            )

        try:
            data = response.json()
            content = data["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError(
                f"Ollama yanıtı beklenen biçimde değil: {response.text[:300]}"
            ) from exc

        return content.strip()


def get_provider(
    provider: str = "ollama",
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LLMProvider:
    """Sağlayıcı adına göre uygun `LLMProvider` örneğini üret.

    Faz 3'te config'ten okunan değerlerle çağrılacak.
    """
    provider = provider.lower()
    if provider == "ollama":
        return OllamaProvider(model=model, base_url=base_url, timeout_seconds=timeout_seconds)
    raise LLMError(f"Bilinmeyen sağlayıcı: '{provider}'. Şimdilik sadece 'ollama' destekleniyor.")
