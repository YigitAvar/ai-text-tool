"""Masaüstü bildirimleri.

`plyer` üzerinden cross-platform bildirim gösterir. Bildirimler hiçbir zaman
uygulamayı çökertmemeli; bu yüzden her şey try/except içinde ve plyer yoksa /
hata verirse sessizce konsola düşülür.
"""

from __future__ import annotations

APP_NAME = "AI Metin Aracı"

try:
    from plyer import notification as _plyer_notification
except Exception:  # pragma: no cover - platforma/bağımlılığa bağlı
    _plyer_notification = None


def notify(message: str, title: str = APP_NAME, timeout: int = 4) -> None:
    """Bir masaüstü bildirimi göster. Hata olursa sessizce konsola yazar.

    Bazı platformlar çok uzun mesajlarda bildirimi kırptığından/yutabildiğinden
    metni makul bir uzunlukta tutarız.
    """
    text = (message or "").strip()
    if len(text) > 256:
        text = text[:253] + "..."

    if _plyer_notification is not None:
        try:
            _plyer_notification.notify(
                title=title,
                message=text or " ",
                app_name=APP_NAME,
                timeout=timeout,
            )
            return
        except Exception as exc:  # pragma: no cover - backend'e bağlı
            print(f"[notifier] bildirim gösterilemedi ({exc}); konsola düşülüyor.")

    print(f"[{title}] {text}")
