"""config.yaml okuma ve doğrulama.

Tasarım: uygulamanın geri kalanı (actions.py, main.py) düz dict yerine tipli
nesnelerle çalışsın diye config dataclass'lara dönüştürülür. Eksik alanlar
makul varsayılanlarla doldurulur; böylece kullanıcı config.yaml'da sadece
değiştirmek istediği alanı yazabilir.

Yeni bir eylem eklemek = config.yaml'a bir blok eklemek. Kod değişmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# config.yaml bu dosyanın yanında durur; çalışma dizininden bağımsız bulunabilsin.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

# llm.py'deki varsayılanlarla uyumlu kalsın.
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 60
# Bu uzunluğun üstündeki seçimler işlenmeden reddedilir: yerel modelin context
# penceresini taşırmamak ve "yanlışlıkla tüm belgeyi seçtim" durumlarında uzun
# uzun beklememek için. 0 = sınır yok.
DEFAULT_MAX_INPUT_CHARS = 8000

DEFAULT_COPY_DELAY_MS = 120
DEFAULT_PASTE_DELAY_MS = 80
DEFAULT_RESTORE_ORIGINAL = True
DEFAULT_RESTORE_DELAY_MS = 300


class ConfigError(Exception):
    """config.yaml okunamadığında / geçersiz olduğunda kullanıcıya gösterilecek hata."""


@dataclass
class LLMConfig:
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    # Seçili metnin izin verilen en fazla karakter sayısı (0 = sınırsız).
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS


@dataclass
class ClipboardConfig:
    copy_delay_ms: float = DEFAULT_COPY_DELAY_MS
    paste_delay_ms: float = DEFAULT_PASTE_DELAY_MS
    restore_original: bool = DEFAULT_RESTORE_ORIGINAL
    restore_delay_ms: float = DEFAULT_RESTORE_DELAY_MS


@dataclass
class ActionConfig:
    name: str
    hotkey: str
    prompt: str
    # "single": tüm prompt tek user mesajı (translate). "system_user": talimat
    # system rolüne, {text} ayrı user mesajına gider (summarize/fix/formal).
    prompt_mode: str = "single"


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    clipboard: ClipboardConfig = field(default_factory=ClipboardConfig)
    actions: dict[str, ActionConfig] = field(default_factory=dict)


def _as_dict(value: object, where: str) -> dict:
    """`value` bir mapping değilse anlamlı bir hata fırlat."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"config.yaml: '{where}' bir sözlük (mapping) olmalı.")
    return value


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """config.yaml'ı yükleyip doğrulanmış bir `Config` döndür.

    Dosya yoksa / bozuksa `ConfigError` fırlatır. Eksik alanlar varsayılanlarla
    doldurulur; `actions` bloğu en az bir eylem içermelidir (yoksa uygulamanın
    yapacak bir şeyi olmaz).
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"config.yaml bulunamadı: {path}. Örnek için plana bak veya repo'daki "
            "config.yaml'ı kopyala."
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"config.yaml ayrıştırılamadı (YAML hatası): {exc}") from exc

    raw = _as_dict(raw, "(kök)")

    llm_raw = _as_dict(raw.get("llm"), "llm")
    llm = LLMConfig(
        provider=str(llm_raw.get("provider", DEFAULT_PROVIDER)),
        model=str(llm_raw.get("model", DEFAULT_MODEL)),
        base_url=str(llm_raw.get("base_url", DEFAULT_BASE_URL)),
        timeout_seconds=float(llm_raw.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
        max_input_chars=int(llm_raw.get("max_input_chars", DEFAULT_MAX_INPUT_CHARS)),
    )

    clip_raw = _as_dict(raw.get("clipboard"), "clipboard")
    clipboard_cfg = ClipboardConfig(
        copy_delay_ms=float(clip_raw.get("copy_delay_ms", DEFAULT_COPY_DELAY_MS)),
        paste_delay_ms=float(clip_raw.get("paste_delay_ms", DEFAULT_PASTE_DELAY_MS)),
        restore_original=bool(clip_raw.get("restore_original", DEFAULT_RESTORE_ORIGINAL)),
        restore_delay_ms=float(clip_raw.get("restore_delay_ms", DEFAULT_RESTORE_DELAY_MS)),
    )

    actions_raw = _as_dict(raw.get("actions"), "actions")
    actions: dict[str, ActionConfig] = {}
    for name, block in actions_raw.items():
        block = _as_dict(block, f"actions.{name}")
        hotkey = block.get("hotkey")
        prompt = block.get("prompt")
        if not hotkey:
            raise ConfigError(f"config.yaml: 'actions.{name}' için 'hotkey' eksik.")
        if not prompt:
            raise ConfigError(f"config.yaml: 'actions.{name}' için 'prompt' eksik.")
        if "{text}" not in prompt:
            raise ConfigError(
                f"config.yaml: 'actions.{name}.prompt' içinde '{{text}}' yer tutucusu "
                "olmalı (seçili metin oraya gömülür)."
            )
        prompt_mode = str(block.get("prompt_mode", "single"))
        if prompt_mode not in ("single", "system_user"):
            raise ConfigError(
                f"config.yaml: 'actions.{name}.prompt_mode' geçersiz: '{prompt_mode}'. "
                "'single' veya 'system_user' olmalı."
            )
        actions[name] = ActionConfig(
            name=name, hotkey=str(hotkey), prompt=str(prompt), prompt_mode=prompt_mode
        )

    if not actions:
        raise ConfigError(
            "config.yaml: en az bir eylem tanımlanmalı ('actions' bloğu boş olamaz)."
        )

    return Config(llm=llm, clipboard=clipboard_cfg, actions=actions)
