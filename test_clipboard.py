"""Faz 2 elle doğrulama scripti — clipboard.py için.

Bu test İNTERAKTİFTİR çünkü gerçek bir uygulamadaki seçimi okuyup üzerine
yazmayı doğrular. Adımlar:

  1. Bir not defteri / metin editörü aç, içine bir cümle yaz.
  2. O cümleyi FARE/KLAVYE ile SEÇ (highlight).
  3. Bu scripti çalıştır:  python test_clipboard.py
  4. Geri sayım bitmeden pencereyi DEĞİŞTİRME — seçili metin önde kalsın
     (script çalışırken o uygulama odakta olmalı).

Beklenen:
  - Script seçtiğin metni konsola yazdırır (get_selected_text doğru okudu).
  - Ardından seçili yere "DEĞİŞTİ (Faz 2 testi)" yazılır (replace_selection).
  - İşlemden sonra panondaki ESKİ içerik geri gelmiş olmalı.
"""

import time

import clipboard


def countdown(seconds: int, message: str) -> None:
    print(message)
    for remaining in range(seconds, 0, -1):
        print(f"  {remaining}...", end="\r", flush=True)
        time.sleep(1)
    print(" " * 20, end="\r")


def main() -> None:
    print("=" * 60)
    print("Faz 2 — clipboard.py testi")
    print("=" * 60)
    print(
        "\nHazırlık: bir not defterine cümle yaz ve SEÇ (highlight).\n"
        "Bu pencereye geri dönme; seçili metnin olduğu pencere ODAKTA kalmalı.\n"
    )

    # Panoya tanınabilir bir işaret koy ki "geri yükleme" çalışıyor mu görelim.
    sentinel = "ORIJINAL-PANO-ICERIGI-12345"
    try:
        import pyperclip

        pyperclip.copy(sentinel)
    except Exception:
        sentinel = None

    countdown(6, "Lütfen şimdi hedef pencerede metni seç. Okuma başlıyor:")

    selected = clipboard.get_selected_text()
    print(f"\n[get_selected_text] okunan metin:\n  >>> {selected!r}\n")

    if not selected:
        print("UYARI: Hiçbir şey okunamadı. Metni seçtin mi? Pencere odakta mıydı?")

    countdown(4, "Şimdi seçili metnin ÜZERİNE yazılacak. Pencere yine odakta olsun:")

    replacement = "DEĞİŞTİ (Faz 2 testi)"
    clipboard.replace_selection(replacement)
    print(f"\n[replace_selection] yapıştırılan metin:\n  >>> {replacement!r}")
    print("Hedef penceredeki seçili yer bununla değişmiş olmalı.\n")

    # Geri yükleme kontrolü.
    if sentinel is not None:
        time.sleep(0.3)
        import pyperclip

        now = pyperclip.paste()
        if now == sentinel:
            print(f"[restore] OK — orijinal pano içeriği geri geldi: {now!r}")
        else:
            print(
                f"[restore] DİKKAT — pano şu an: {now!r}\n"
                f"          beklenen (orijinal): {sentinel!r}"
            )

    print("\nTest bitti. Hedef penceredeki sonucu gözle doğrula.")


if __name__ == "__main__":
    main()
