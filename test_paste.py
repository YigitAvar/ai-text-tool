"""Yalnızca YAPIŞTIRMAYI izole eden teşhis scripti.

LLM yok, seçim okuma yok, restore yok. Sadece: panoya bilinen bir metin koy,
sen Notepad++ penceresine geç, script iki farklı yöntemle yapıştırmayı dener:
  1) Ctrl+V       (uygulamanın kullandığı varsayılan)
  2) Shift+Insert (birçok editörün, Notepad++ dahil, desteklediği alternatif)

Böylece "yapıştırma hiç çalışmıyor mu, yoksa sadece Ctrl+V mi sorunlu" ayrılır.

Kullanım:
  python test_paste.py
Adımlar:
  1. Notepad++ aç, BOŞ bir satıra imleci koy.
  2. Bu scripti çalıştır.
  3. Geri sayım sırasında Notepad++ penceresine TIKLA (odak orada olsun).

Beklenen:
  - "[Ctrl+V]" işaretli metin göründüyse Ctrl+V çalışıyor.
  - Sadece "[Shift+Insert]" göründüyse Ctrl+V sorunlu, alternatife geçeriz.
  - HİÇBİRİ görünmediyse: Notepad++ büyük olasılıkla YÖNETİCİ olarak çalışıyor;
    bu terminali de yönetici olarak açıp tekrar dene (ya da Notepad++'ı normal aç).
"""

import time

import pyperclip
from pynput.keyboard import Controller, Key

_kb = Controller()


def _countdown(seconds: int, message: str) -> None:
    print(message)
    for remaining in range(seconds, 0, -1):
        print(f"  {remaining}...", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30, end="\r")


def _paste_ctrl_v() -> None:
    _kb.press(Key.ctrl)
    _kb.press("v")
    _kb.release("v")
    _kb.release(Key.ctrl)


def _paste_shift_insert() -> None:
    _kb.press(Key.shift)
    _kb.press(Key.insert)
    _kb.release(Key.insert)
    _kb.release(Key.shift)


def main() -> None:
    print("=" * 60)
    print("YAPIŞTIRMA izolasyon testi (Notepad++)")
    print("=" * 60)
    print("Notepad++ aç, BOŞ bir satıra imleci koy. Geri sayımda oraya TIKLA.\n")

    pyperclip.copy("[Ctrl+V] yapistirma calisiyor 12345")
    _countdown(6, "Notepad++'a tıkla — Ctrl+V deneniyor:")
    _paste_ctrl_v()
    time.sleep(0.8)

    pyperclip.copy("[Shift+Insert] yapistirma calisiyor 67890")
    _countdown(4, "Şimdi Shift+Insert deneniyor (alternatif):")
    _paste_shift_insert()
    time.sleep(0.5)

    print("\nBitti. Notepad++'taki sonuca bak:")
    print("  - İki satır da göründü  -> her iki yöntem çalışıyor.")
    print("  - Sadece [Shift+Insert] -> Ctrl+V sorunlu; uygulamayı buna çeviririz.")
    print("  - Hiçbiri görünmedi     -> Notepad++ yönetici olarak çalışıyor olabilir;")
    print("    bu terminali yönetici olarak açıp tekrar dene.")


if __name__ == "__main__":
    main()
