# AI Metin Aracı

> Seçili metni **global kısayolla** yerel bir LLM ([Ollama](https://ollama.com))
> ile **çeviren / düzelten / resmileştiren / özetleyen** tray uygulaması.
> Metni seç → kısayola bas → sonuç **seçili metnin yerine yazılır.**

Arka planda sistem tepsisinde (tray) çalışan, üretkenliğe yönelik küçük bir
yardımcı. Tamamen **yerel** çalışır: metin Ollama üzerinden makinende işlenir,
hiçbir veri buluta gönderilmez, internet gerekmez.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Ekran görüntüsü

<!-- Buraya bir ekran görüntüsü / GIF ekle (örn. docs/demo.gif):
     metni seç → Ctrl+Alt+T → yerine İngilizcesi yazılıyor. -->
<!-- ![Demo](docs/demo.gif) -->

_Ekran görüntüsü yakında._

## Özellikler

- 🔌 **Sistem genelinde çalışır** — hangi uygulamada olursan ol (Word, tarayıcı, mail…).
- ⌨️ **Global kısayollar** — fareye gerek yok, seç ve bas.
- 🔒 **Yerel ve gizli** — model makinende çalışır (Ollama), metin dışarı çıkmaz.
- 🧩 **Config'ten yönetilir** — yeni eylem/kısayol eklemek için sadece `config.yaml`'ı düzenle, kod yazma.
- 🪶 **Hafif** — sade bir tray uygulaması, GUI penceresi yok.
- 🔁 **Sağlayıcı soyutlaması** — bugün Ollama; ileride başka bir sağlayıcı eklemek kolay.

### Hazır eylemler

| Kısayol      | Eylem       | Ne yapar                                                |
| ------------ | ----------- | ------------------------------------------------------- |
| `Ctrl+Alt+T` | `translate` | Türkçe ⇄ İngilizce çeviri (dil yönü otomatik algılanır) |
| `Ctrl+Alt+F` | `fix`       | Yazım / dil bilgisi düzeltir (anlamı ve dili korur)     |
| `Ctrl+Alt+R` | `formal`    | Tonu resmî / profesyonel hâle getirir (dili korur)      |
| `Ctrl+Alt+S` | `summarize` | Kısa özet çıkarır (aynı dilde)                          |

## Kurulum

### 1. Ollama'yı kur ve modeli indir

[ollama.com](https://ollama.com) adresinden Ollama'yı kur, ardından modeli indir:

```bash
ollama pull qwen2.5:7b-instruct
```

Ollama arka planda bir sunucu olarak çalışır (`http://localhost:11434`); kurulum
sonrası genelde otomatik başlar. Başlamazsa `ollama serve` ile başlatabilirsin.

> **Model seçimi:** `qwen2.5:7b-instruct` çeviride güvenilir sonuç verir. Daha
> hızlı ama daha az tutarlı bir alternatif için `llama3.2:3b` indirip
> `config.yaml`'daki `llm.model` alanını değiştir.

### 2. Python ortamı

Python 3.11+ gerekir.

```bash
git clone https://github.com/YigitAvar/ai-text-tool.git
cd ai-text-tool

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Çalıştır

```bash
python main.py
```

Tray'de bir "AI" ikonu belirir ve açılışta kısayolları gösteren bir bildirim
çıkar. Kapatmak için tray ikonuna sağ tıkla → **Çıkış**.

## Kullanım

1. Bir uygulamada (Word, tarayıcı, mail…) bir metin seç.
2. İlgili kısayola bas (örn. çeviri için `Ctrl+Alt+T`).
3. "`translate` çalışıyor…" bildirimi çıkar; bitince "`translate` tamam ✓".
4. Seçili metin, modelin ürettiği sonuçla değiştirilir.

Tray menüsündeki **"Config'i yeniden yükle"**, `config.yaml`'ı düzenledikten
sonra uygulamayı kapatmadan yeni ayarları yükler.

## Yapılandırma (`config.yaml`)

```yaml
llm:
  provider: ollama
  model: qwen2.5:7b-instruct
  base_url: http://localhost:11434
  timeout_seconds: 120     # model yanıt vermezse bu süre sonunda hata bildirir
  max_input_chars: 8000    # daha uzun seçimler reddedilir (0 = sınırsız)

clipboard:
  copy_delay_ms: 250       # Ctrl+C sonrası clipboard'ın dolması için bekleme
  paste_delay_ms: 200      # clipboard'a yazma ile Ctrl+V arasındaki bekleme
  restore_original: false  # işlem sonrası orijinal pano içeriğini geri yükle
  restore_delay_ms: 400    # Ctrl+V sonrası geri yüklemeden önceki bekleme

actions:
  translate:
    hotkey: "<ctrl>+<alt>+t"
    prompt: |
      ...{text}...
```

- **Yeni eylem eklemek** = `actions` altına yeni bir blok eklemek. `hotkey` ve
  `prompt` (içinde `{text}` yer tutucusu zorunlu) yeterli.
- **`prompt_mode`**: `single` (varsayılan) tüm prompt'u tek bir `user` mesajı
  yapar; `system_user` talimatı `system` rolüne, ham metni `user` rolüne ayırır
  (düzeltme/özet/resmileştirme bunu kullanır — model talimatı içerikle karıştırmaz).
- **Clipboard zamanlamaları** makineye göre değişir. Yapıştırma boş geliyorsa
  `copy_delay_ms` / `paste_delay_ms` değerlerini artır.

## Sorun giderme

| Belirti                              | Çözüm                                                              |
| ------------------------------------ | ------------------------------------------------------------------ |
| "Ollama'ya bağlanılamadı"            | Ollama çalışmıyor. `ollama serve` ile başlat.                      |
| "Model bulunamadı"                   | `ollama pull qwen2.5:7b-instruct` ile modeli indir.                |
| "Ollama … sn içinde yanıt vermedi"   | Soğuk başlangıçta 7B yavaş olabilir; `timeout_seconds`'ı artır.    |
| Sonuç yerine yazılmıyor / boş yapışıyor | `copy_delay_ms` / `paste_delay_ms` değerlerini artır.           |

### Bilinen sorunlar

- **Notepad'de boş yapıştırma:** Bazı durumlarda Notepad'e sonuç boş yapışabiliyor
  (Word ve tarayıcıda sorun yok). Araştırılmak üzere ertelendi;
  `clipboard.restore_original` geçici olarak `false` bırakıldı.
- **Yönetici modundaki uygulamalar:** Windows'ta yönetici olarak çalışan bir
  uygulamaya klavye simülasyonu gönderilemeyebilir; uygulamayı da yönetici olarak çalıştır.
- **Kısayol çakışması:** Başka bir uygulamanın global kısayoluyla çakışırsa
  çalışmaz; `config.yaml`'dan değiştir.

## (Opsiyonel) Windows'ta başlangıçta otomatik çalıştırma

Oturum açılışında otomatik başlaması için bir kısayol oluştur:

1. `Win+R` → `shell:startup` → Enter (Başlangıç klasörü açılır).
2. Bu klasöre yeni bir kısayol ekle; hedef olarak (kendi kurulum yolunla
   değiştirerek) şunu ver:

   ```
   <KURULUM_YOLU>\.venv\Scripts\pythonw.exe <KURULUM_YOLU>\main.py
   ```

   `pythonw.exe` (sondaki `w`), konsol penceresi açmadan sessizce çalıştırır.

## Mimari

```
ai-text-tool/
├── main.py        # Tray + global kısayol kaydı + event loop
├── config.py      # config.yaml okuma/doğrulama (tipli dataclass'lar)
├── config.yaml    # Kısayol → eylem eşleşmesi ve prompt'lar
├── clipboard.py   # Seçimi kopyala / sonucu yapıştır (timing dahil)
├── llm.py         # LLM sağlayıcı soyutlaması (Ollama varsayılan)
├── actions.py     # Eylem akışı: metin al → prompt kur → LLM → yapıştır
├── notifier.py    # Masaüstü bildirimleri (plyer)
└── docs/
    └── build-plan.md   # Ayrıntılı tasarım ve build planı
```

Ayrıntılı tasarım kararları ve aşamalı build planı için:
[`docs/build-plan.md`](docs/build-plan.md).

## Lisans

[MIT](LICENSE) © Yiğit Avar
