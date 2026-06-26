"""Faz 3 elle doğrulama scripti — config.py + actions.py için.

İki bölüm var:

  A) config.py — interaktif değil. config.yaml düzgün yükleniyor mu kontrol eder.
  B) actions.py — İNTERAKTİF. Gerçek bir uygulamadaki seçimi LLM'e gönderip
     üzerine yazmayı doğrular (Ollama çalışıyor olmalı).

Kullanım:
  python test_actions.py                       -> sadece config testi (B'yi atlar)
  python test_actions.py --live                -> config + canlı 'translate' testi
  python test_actions.py --live --action summarize  -> canlı 'summarize' testi
  (--action ile config'teki herhangi bir eylem: translate / fix / formal / summarize)

Canlı test için:
  1. Bir not defterine ilgili metni yaz (özet için birkaç cümlelik bir paragraf).
  2. Metni SEÇ (highlight). O pencere ODAKTA kalmalı.
  3. python test_actions.py --live --action <eylem>  çalıştır, geri sayımı bekle.

Beklenen (canlı):
  - Konsol seçilen ham metni, modele giden TAM prompt'u ve LLM sonucunu yazdırır.
  - Hedef penceredeki seçili metin sonuçla değişir.
"""

import sys
import time

import config as config_module


def test_config() -> None:
    print("=" * 60)
    print("A) config.py testi")
    print("=" * 60)
    cfg = config_module.load_config()
    print(f"  provider        : {cfg.llm.provider}")
    print(f"  model           : {cfg.llm.model}")
    print(f"  base_url        : {cfg.llm.base_url}")
    print(f"  timeout_seconds : {cfg.llm.timeout_seconds}")
    print(f"  copy_delay_ms   : {cfg.clipboard.copy_delay_ms}")
    print(f"  paste_delay_ms  : {cfg.clipboard.paste_delay_ms}")
    print(f"  restore_original: {cfg.clipboard.restore_original}")
    print(f"  eylemler        : {', '.join(sorted(cfg.actions))}")
    for name, action in cfg.actions.items():
        assert "{text}" in action.prompt, f"{name} promptunda {{text}} yok!"
        print(f"    - {name:10s} hotkey={action.hotkey}")
    print("  config.py OK\n")


def _show_prompt(cfg, action_name: str, raw: str) -> None:
    """run_action ile AYNI mantıkla modele gidecek mesaj(lar)ı göster."""
    import actions

    action = cfg.actions[action_name]
    if action.prompt_mode == "system_user":
        prefix, _, suffix = action.prompt.partition("{text}")
        system = prefix.strip()
        if suffix.strip():
            system = f"{system}\n\n{suffix.strip()}".strip()
        print(f"[MOD] system_user — talimat 'system', metin 'user' rolünde")
        print("[SYSTEM mesajı] (talimat/kurallar):")
        print("-" * 60)
        print(system)
        print("-" * 60)
        print(f"[USER mesajı] (işlenecek ham metin):\n  >>> {raw!r}\n")
        return

    prompt = action.prompt
    if "{source_lang}" in prompt or "{target_lang}" in prompt:
        src = actions.detect_language(raw)
        tgt = "English" if src == "Turkish" else "Turkish"
        print(f"[DİL TESPİTİ] kaynak={src}  ->  hedef={tgt}")
        prompt = prompt.replace("{source_lang}", src).replace("{target_lang}", tgt)
    filled = prompt.replace("{text}", raw)
    print("[MOD] single — tek user mesajı")
    print("[TAM PROMPT] modele gönderilen:")
    print("-" * 60)
    print(filled)
    print("-" * 60 + "\n")


def test_live_action(action_name: str) -> None:
    import actions
    import clipboard

    print("=" * 60)
    print(f"B) actions.py canlı testi — eylem: '{action_name}' (Ollama gerekli)")
    print("=" * 60)

    cfg = actions.get_config()
    if action_name not in cfg.actions:
        print(f"HATA: '{action_name}' config'te yok. Mevcut: {', '.join(cfg.actions)}")
        return

    print(
        "\nHazırlık: hedef metni yaz ve SEÇ (özet için birkaç cümlelik paragraf).\n"
        "Pencere ODAKTA kalmalı; bu konsola geri dönme.\n"
    )
    print(
        f"Kullanılan gecikmeler: copy={cfg.clipboard.copy_delay_ms}ms, "
        f"paste={cfg.clipboard.paste_delay_ms}ms\n"
    )

    for remaining in range(6, 0, -1):
        print(f"  Okuma {remaining}...", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30, end="\r")

    # --- Teşhis: get_selected_text gerçekten ne okuyor? ---
    raw = clipboard.get_selected_text(copy_delay_ms=cfg.clipboard.copy_delay_ms)
    print(f"[HAM OKUMA] get_selected_text döndürdü ({len(raw)} karakter):")
    print(f"  >>> {raw!r}\n")
    if not raw.strip():
        print(
            "UYARI: Ham okuma BOŞ. Metni seçmedin ya da pencere odakta değildi. "
            "Sonuç bu yüzden anlamsız olabilir.\n"
        )

    # Modele giden mesaj(lar)ı göster (run_action içeride aynısını kurar).
    _show_prompt(cfg, action_name, raw)

    print("LLM'e gönderiliyor (model yavaşsa biraz sürebilir)...\n")
    result = actions.run_action(action_name)
    print(f"[{action_name}] LLM sonucu ({len(result)} karakter, yapıştırıldı):")
    print(f"  >>> {result!r}\n")
    if action_name == "summarize" and raw.strip():
        oran = len(result) / max(len(raw), 1)
        print(
            f"[ÖZET KONTROL] çıktı/girdi uzunluk oranı = {oran:.0%} "
            f"({'kısaldı ✓' if oran < 0.8 else 'yeterince kısalmadı ✗'})"
        )
    print("Hedef penceredeki seçili metin bu sonuçla değişmiş olmalı.")


def _parse_action() -> str:
    """--action <ad> argümanını oku; yoksa 'translate'."""
    argv = sys.argv
    if "--action" in argv:
        i = argv.index("--action")
        if i + 1 < len(argv):
            return argv[i + 1]
    return "translate"


def main() -> None:
    test_config()
    if "--live" in sys.argv:
        test_live_action(_parse_action())
    else:
        print(
            "Canlı eylem testi atlandı. Çalıştırmak için:\n"
            "  python test_actions.py --live                     (translate)\n"
            "  python test_actions.py --live --action summarize  (özet)"
        )


if __name__ == "__main__":
    main()
