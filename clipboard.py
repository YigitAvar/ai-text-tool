"""Seçili metni kopyalama / sonucu yapıştırma yardımcıları (timing dahil).

Akışın en kırılgan kısmı burası. `Ctrl+C` simüle edildikten sonra clipboard
ANINDA dolmaz; mutlaka küçük bir bekleme gerekir. Aynı şekilde yapıştırmadan
önce clipboard'ın yazıldığından emin olmak için kısa bir bekleme konur. Bu
süreler makineye göre değişebildiğinden Faz 3'te config'ten okunacak; şimdilik
plandaki makul varsayılanlar kullanılıyor.

Tasarım notu: orijinal clipboard içeriği işlemden önce yedeklenir ve işlem
sonrası geri yüklenir; böylece kullanıcının panosu bizim ara metnimizle
bozulmaz.
"""

from __future__ import annotations

import time

import pyperclip
from pynput.keyboard import Controller, Key

# Faz 3'te config'ten (clipboard.copy_delay_ms / paste_delay_ms /
# restore_original) gelecek; şimdilik plandaki varsayılanlar.
DEFAULT_COPY_DELAY_MS = 120
DEFAULT_PASTE_DELAY_MS = 80
DEFAULT_RESTORE_ORIGINAL = True
# Ctrl+V gönderildikten SONRA, orijinal panoyu geri yüklemeden önce beklenecek
# süre. Hedef uygulama yapıştırmayı tamamlamadan panoyu geri yüklersek
# (özellikle uzun metinlerde) boş/eski içerik yapışır. Bu yüzden cömert.
DEFAULT_RESTORE_DELAY_MS = 300

# pynput Controller'ı modül düzeyinde bir kez oluştur; her çağrıda yeniden
# kurmaya gerek yok.
_keyboard = Controller()


class ClipboardError(Exception):
    """Clipboard işlemleriyle ilgili, kullanıcıya gösterilebilir hatalar.

    `actions.py` bu istisnayı yakalayıp bir bildirime dönüştürebilir; uygulama
    çökmemeli.
    """


def _ms_to_seconds(ms: float) -> float:
    return ms / 1000.0


def _press_combo(*keys: Key | str) -> None:
    """Verilen tuş kombinasyonunu (örn. Ctrl+C) sırayla bas, ters sırayla bırak."""
    for key in keys:
        _keyboard.press(key)
    for key in reversed(keys):
        _keyboard.release(key)


def get_selected_text(
    copy_delay_ms: float = DEFAULT_COPY_DELAY_MS,
) -> str:
    """Aktif uygulamadaki seçili metni `Ctrl+C` simüle ederek oku.

    Orijinal clipboard içeriğini DEĞİŞTİRİR (Ctrl+C onu seçili metinle ezer).
    Çağıran taraf orijinali korumak istiyorsa önce yedeklemeli ya da
    `replace_selection(..., restore_original=True)` akışını kullanmalı.

    Boş seçimde (kopyalanacak bir şey yoksa) genelde clipboard'da önceki
    içerik kalır; çağıran tarafın "boş/anlamsız seçim" durumunu kendisi
    değerlendirmesi beklenir (Faz 5).
    """
    _press_combo(Key.ctrl, "c")
    time.sleep(_ms_to_seconds(copy_delay_ms))
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException as exc:  # pragma: no cover - platforma bağlı
        raise ClipboardError(
            "Clipboard okunamadı. Sistemde bir pano mekanizması (ör. Windows'ta "
            "varsayılan olarak mevcut) bulunmalı."
        ) from exc


def replace_selection(
    text: str,
    paste_delay_ms: float = DEFAULT_PASTE_DELAY_MS,
    restore_original: bool = DEFAULT_RESTORE_ORIGINAL,
    restore_delay_ms: float = DEFAULT_RESTORE_DELAY_MS,
) -> None:
    """`text`'i clipboard'a yazıp `Ctrl+V` ile seçili metnin üzerine yapıştır.

    `restore_original` True ise, işlemden önce clipboard'da bulunan içerik
    yapıştırmadan sonra geri yüklenir; böylece kullanıcının panosu korunur.

    Önemli: geri yükleme yapıştırma TAMAMLANDIKTAN sonra olmalı. Aksi halde
    hedef uygulama `Ctrl+V` ile panoyu okumayı bitirmeden orijinali geri
    koyarsak boş/eski içerik yapışır. `restore_delay_ms` bu pencereyi açar ve
    uzun metinler için cömert tutulmalıdır.
    """
    try:
        original = pyperclip.paste() if restore_original else None
    except pyperclip.PyperclipException:  # pragma: no cover - platforma bağlı
        # Orijinali okuyamadıysak en azından yapıştırmayı denemeye devam et;
        # geri yükleyecek bir şey de yok demektir.
        original = None

    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:  # pragma: no cover - platforma bağlı
        raise ClipboardError(
            "Sonuç clipboard'a yazılamadı; yapıştırma yapılamadı."
        ) from exc

    # Panoya yazma ile Ctrl+V arasında kısa bir bekleme (pano set olsun).
    time.sleep(_ms_to_seconds(paste_delay_ms))
    _press_combo(Key.ctrl, "v")

    if restore_original and original is not None:
        # Yapıştırma tamamlanana kadar bekle, SONRA orijinali geri yükle.
        time.sleep(_ms_to_seconds(restore_delay_ms))
        try:
            pyperclip.copy(original)
        except pyperclip.PyperclipException:  # pragma: no cover - platforma bağlı
            # Geri yükleme başarısızsa bu kritik değil; sessiz geç.
            pass
