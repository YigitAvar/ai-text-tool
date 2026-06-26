"""Giriş noktası: tray ikonu + global kısayol kaydı + event loop.

Akış:
- config'teki her eylem, kısayoluna `pynput.keyboard.GlobalHotKeys` ile bağlanır.
- Kısayola basılınca eylem AYRI bir worker thread'de çalışır; böylece kısayol
  dinleyicisi ve tray bloklanmaz, art arda basışlar birikmez.
- Aynı anda yalnızca bir eylem çalışır (hepsi clipboard'ı paylaşıyor); meşgulken
  yeni basış nazikçe reddedilir.
- Tray menüsü: "Config'i yeniden yükle" ve "Çıkış".
- Her aşamada (başla/bitti/hata) masaüstü bildirimi verilir.
"""

from __future__ import annotations

import threading
import time

import pystray
from PIL import Image, ImageDraw
from pynput import keyboard

import actions
import notifier
from actions import ActionError
from clipboard import ClipboardError
from config import ConfigError
from llm import LLMError

# Aynı anda tek eylem çalışsın diye kilit (clipboard paylaşımlı kaynak).
_run_lock = threading.Lock()

# Kısayol tetiklendiğinde kullanıcı genelde Ctrl+Alt'ı hâlâ basılı tutuyordur.
# Hemen Ctrl+C simüle edersek modifier'lar karışır (Ctrl+Alt+C olur). Tuşları
# bırakması için kısa bir an bekleriz.
HOTKEY_RELEASE_DELAY_S = 0.3


def _make_icon_image() -> Image.Image:
    """Tray için basit, programatik bir ikon üret (harici dosya gerekmez)."""
    img = Image.new("RGB", (64, 64), (24, 24, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle([6, 6, 57, 57], outline=(0, 200, 150), width=3)
    draw.text((17, 22), "AI", fill=(0, 200, 150))
    return img


def _run_action_worker(action_name: str) -> None:
    """Bir eylemi arka planda çalıştır; durumları bildirime dönüştür.

    Hiçbir istisna dışarı sızmamalı — worker thread'de patlarsa sessiz kalır,
    o yüzden geniş yakalama yapıp kullanıcıya bildiririz.
    """
    if not _run_lock.acquire(blocking=False):
        notifier.notify("Meşgul: önceki işlem hâlâ sürüyor…")
        return

    try:
        # Kullanıcı kısayol tuşlarını bıraksın.
        time.sleep(HOTKEY_RELEASE_DELAY_S)
        notifier.notify(f"'{action_name}' çalışıyor…")
        actions.run_action(action_name)
        notifier.notify(f"'{action_name}' tamam ✓")
    except (ActionError, ClipboardError) as exc:
        notifier.notify(f"Yapılamadı: {exc}")
    except LLMError as exc:
        notifier.notify(f"LLM hatası: {exc}")
    except ConfigError as exc:
        notifier.notify(f"Config hatası: {exc}")
    except Exception as exc:  # pragma: no cover - beklenmeyen
        notifier.notify(f"Beklenmeyen hata: {exc}")
    finally:
        _run_lock.release()


def _make_hotkey_callback(action_name: str):
    """Kısayol için, eylemi ayrı thread'de başlatan bir callback üret."""

    def callback() -> None:
        threading.Thread(
            target=_run_action_worker, args=(action_name,), daemon=True
        ).start()

    return callback


def _build_hotkey_map(cfg) -> dict:
    """config eylemlerinden {kısayol: callback} eşlemesi kur (GlobalHotKeys formatı)."""
    mapping: dict = {}
    for name, action in cfg.actions.items():
        mapping[action.hotkey] = _make_hotkey_callback(name)
    return mapping


def _tooltip(cfg) -> str:
    """Tray ikonu üzerine gelince görünecek ipucu metni."""
    return f"{notifier.APP_NAME} — {cfg.llm.model}"


def main() -> None:
    try:
        cfg = actions.get_config()
    except ConfigError as exc:
        notifier.notify(f"Başlatılamadı — config hatası: {exc}")
        print(f"Config hatası: {exc}")
        return

    # Kısayol dinleyicisi kendi thread'inde çalışır (start bloklamaz).
    hotkeys = keyboard.GlobalHotKeys(_build_hotkey_map(cfg))
    hotkeys.start()

    # Dinleyici referansını mutable bir kapta tutuyoruz ki "yeniden yükle"
    # eskisini durdurup yenisini takabilsin.
    state = {"hotkeys": hotkeys}

    def on_reload(icon, item) -> None:
        try:
            new_cfg = actions.get_config(reload=True)
        except ConfigError as exc:
            notifier.notify(f"Config yeniden yüklenemedi: {exc}")
            return
        state["hotkeys"].stop()
        new_hotkeys = keyboard.GlobalHotKeys(_build_hotkey_map(new_cfg))
        new_hotkeys.start()
        state["hotkeys"] = new_hotkeys
        notifier.notify("Config yeniden yüklendi.")

    def on_quit(icon, item) -> None:
        state["hotkeys"].stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Config'i yeniden yükle", on_reload),
        pystray.MenuItem("Çıkış", on_quit),
    )
    icon = pystray.Icon("ai_text_tool", _make_icon_image(), _tooltip(cfg), menu)

    # Açılış bildirimi: hangi kısayol neyi yapıyor.
    hotkey_lines = " | ".join(f"{a.hotkey} → {n}" for n, a in cfg.actions.items())
    notifier.notify(f"Çalışıyor. {hotkey_lines}", timeout=6)
    print(f"AI Metin Aracı çalışıyor. Kısayollar: {hotkey_lines}")
    print("Tray ikonundan 'Çıkış' ile kapatabilirsin.")

    # icon.run() ana thread'i bloklar; 'Çıkış' icon.stop() çağırınca döner.
    icon.run()


if __name__ == "__main__":
    main()
