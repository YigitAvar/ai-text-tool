"""Bir eylemi uçtan uca çalıştırma.

Akış (plandaki en kritik kısım):
  1. clipboard.get_selected_text() ile seçili metni al.
  2. Eylemin prompt şablonuna metni göm ({text}).
  3. llm.complete() ile sonucu üret.
  4. clipboard.replace_selection() ile seçili metnin üzerine yaz.

config ve LLM sağlayıcısı her çağrıda yeniden kurulmasın diye modül düzeyinde
tembel (lazy) önbelleğe alınır; main.py (Faz 4) isterse kendi örneklerini
geçebilir. Hotkey callback'leri ayrı thread'de çağıracağı için fonksiyonlar
durum tutmadan, parametreyle çalışacak biçimde tasarlandı.
"""

from __future__ import annotations

import re

import clipboard
import config as config_module
import llm

# "İşte çeviri:" / "The translation ... is:" gibi tek satırlık önsözleri yakalar:
# en fazla ~120 karakterlik, iki nokta ile biten ilk satır + ardından boş satır
# + asıl içerik. Küçük modeller (llama3.2:3b) prompt'ta "sadece sonucu döndür"
# dense bile sık sık böyle bir önsöz ekliyor.
_PREAMBLE_RE = re.compile(r"^[^\n]{0,120}:\s*\n+(.+)$", re.DOTALL)

# Tembel önbellek: ilk kullanımda kurulur, sonraki çağrılarda yeniden kullanılır.
_config: config_module.Config | None = None
_provider: llm.LLMProvider | None = None


class ActionError(Exception):
    """Eylem akışında kullanıcıya gösterilebilir hata (boş seçim, bilinmeyen eylem vb.)."""


def get_config(reload: bool = False) -> config_module.Config:
    """Önbelleğe alınmış config'i döndür; `reload=True` ile diskten yeniden oku."""
    global _config, _provider
    if _config is None or reload:
        _config = config_module.load_config()
        # Config değiştiyse sağlayıcıyı da tazele (model/base_url değişmiş olabilir).
        _provider = None
    return _config


def get_provider(cfg: config_module.Config | None = None) -> llm.LLMProvider:
    """config'teki llm ayarlarına göre LLM sağlayıcısını (önbellekli) döndür."""
    global _provider
    if cfg is None:
        cfg = get_config()
    if _provider is None:
        _provider = llm.get_provider(
            provider=cfg.llm.provider,
            model=cfg.llm.model,
            base_url=cfg.llm.base_url,
            timeout_seconds=cfg.llm.timeout_seconds,
        )
    return _provider


# Türkçeye özgü harfler — varsa metin neredeyse kesin Türkçedir.
_TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")

# ASCII'ye sadeleşmiş metinlerde (ör. "Bugun nasilsin") harf ipucu olmaz; bu
# durumda yaygın işlev sözcüklerini sayıp karar veririz.
_ENGLISH_HINTS = {
    "the", "a", "an", "is", "are", "was", "were", "you", "your", "i", "we",
    "they", "he", "she", "it", "this", "that", "can", "could", "will", "would",
    "to", "of", "and", "or", "for", "in", "on", "with", "do", "does", "did",
    "have", "has", "not", "be", "me", "my", "please", "before", "after",
}
_TURKISH_HINTS = {
    "ve", "bir", "bu", "icin", "için", "ile", "mi", "mı", "mu", "mü", "da",
    "de", "ne", "nasil", "nasıl", "cok", "çok", "daha", "ben", "sen", "biz",
    "siz", "ama", "gibi", "kadar", "var", "yok", "degil", "değil", "misin",
    "musun", "bana", "seni", "sana",
}


def detect_language(text: str) -> str:
    """Metnin dilini kabaca 'Turkish' veya 'English' olarak tahmin et.

    Yalnızca bu iki dil için tasarlanmış basit bir sezgisel yöntemdir:
    önce Türkçeye özgü harflere bakar; yoksa işlev sözcüklerini sayar.
    Eşitlik/ipucu yoksa Türkçeye düşer (asıl kullanım TR→EN ağırlıklı).
    """
    if any(ch in _TURKISH_CHARS for ch in text):
        return "Turkish"

    words = re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ']+", text.lower())
    english_score = sum(1 for w in words if w in _ENGLISH_HINTS)
    turkish_score = sum(1 for w in words if w in _TURKISH_HINTS)
    return "English" if english_score > turkish_score else "Turkish"


def _clean_response(text: str) -> str:
    """Modelin eklediği yaygın önsöz/sarmalayıcıları hafifçe temizle.

    Prompt'lar zaten "sadece sonucu döndür" diyor; bu yalnızca emniyet kemeri.
    Tüm metni kırpacak agresif bir temizlik yapmaz — sadece tek satırlık
    "İşte çeviri:" türü önekleri ve metni saran tırnakları alır.
    """
    cleaned = text.strip()

    # "The translation ... is:\n\n<içerik>" gibi önsözü at, sadece içeriği bırak.
    match = _PREAMBLE_RE.match(cleaned)
    if match:
        cleaned = match.group(1).strip()

    # Metni tamamen saran çift tırnakları kaldır (model bazen "..." döndürür).
    if len(cleaned) >= 2 and cleaned[0] in "\"'" and cleaned[-1] == cleaned[0]:
        cleaned = cleaned[1:-1].strip()

    return cleaned


def run_action(
    action_name: str,
    cfg: config_module.Config | None = None,
    provider: llm.LLMProvider | None = None,
) -> str:
    """`action_name` eylemini çalıştır ve LLM'in ürettiği (yapıştırılan) metni döndür.

    Hata durumlarında ActionError / llm.LLMError / clipboard.ClipboardError
    fırlatabilir; çağıran taraf (Faz 4'te main.py) bunları yakalayıp bildirime
    dönüştürmeli. Uygulama çökmemeli.
    """
    if cfg is None:
        cfg = get_config()
    if provider is None:
        provider = get_provider(cfg)

    action = cfg.actions.get(action_name)
    if action is None:
        bilinen = ", ".join(sorted(cfg.actions)) or "(yok)"
        raise ActionError(
            f"Bilinmeyen eylem: '{action_name}'. Tanımlı eylemler: {bilinen}."
        )

    selected = clipboard.get_selected_text(copy_delay_ms=cfg.clipboard.copy_delay_ms)
    if not selected or not selected.strip():
        raise ActionError(
            "Seçili metin okunamadı. Bir metin seçtiğinden ve doğru pencerenin "
            "odakta olduğundan emin ol."
        )

    # Çok uzun seçimleri işleme almadan reddet: yerel modelin context penceresini
    # taşırmaz ve yanlışlıkla tüm belgeyi seçtiğinde dakikalarca beklemezsin.
    max_chars = cfg.llm.max_input_chars
    if max_chars and len(selected) > max_chars:
        raise ActionError(
            f"Seçili metin çok uzun ({len(selected)} karakter; sınır {max_chars}). "
            "Daha kısa bir bölüm seç ya da config.yaml'da llm.max_input_chars'ı artır."
        )

    if action.prompt_mode == "system_user":
        # Talimat (şablonun {text} öncesi kısmı) system rolüne, ham metin user
        # rolüne gider. Model talimatı içerikle karıştırıp kuralları işlemez.
        # ({text} şablonlarda en sonda olduğu için system = tüm talimattır.)
        prefix, _, suffix = action.prompt.partition("{text}")
        system_instruction = prefix.strip()
        if suffix.strip():
            system_instruction = f"{system_instruction}\n\n{suffix.strip()}".strip()
        result = provider.complete(system_instruction, selected)
    else:
        # single mod: her şey tek user mesajı. Çeviri için dil yönünü tespit
        # edip {source_lang}/{target_lang}'ı doldur (koşulsuz tek-yön talimat).
        prompt = action.prompt
        if "{source_lang}" in prompt or "{target_lang}" in prompt:
            source_lang = detect_language(selected)
            target_lang = "English" if source_lang == "Turkish" else "Turkish"
            prompt = prompt.replace("{source_lang}", source_lang)
            prompt = prompt.replace("{target_lang}", target_lang)
        prompt = prompt.replace("{text}", selected)
        result = provider.complete(prompt)

    result = _clean_response(result)

    if not result:
        raise ActionError("LLM boş yanıt döndürdü; yapıştırılacak bir şey yok.")

    clipboard.replace_selection(
        result,
        paste_delay_ms=cfg.clipboard.paste_delay_ms,
        restore_original=cfg.clipboard.restore_original,
        restore_delay_ms=cfg.clipboard.restore_delay_ms,
    )
    return result
