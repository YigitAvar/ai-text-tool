# AI Metin Aracı — Build Planı

> Bu belge, projenin tasarımını ve aşamalı build planını anlatır.
> Amaç: sistem genelinde çalışan, kısayolla tetiklenen, seçili metni LLM ile
> işleyip yerine yazan bir tray uygulaması. **Yerel-öncelikli** (Ollama) çalışır.
>
> **Yöntem:** Aşağıdaki fazlar SIRAYLA uygulanır. Her fazın sonunda "Test"
> bölümündeki adım çalıştırılıp doğrulanmadan bir sonrakine geçilmez; bir faz
> çalışmadan üstüne kod eklenmez.

---

## 1. Ne Yapıyoruz (Tek Cümle)

Herhangi bir uygulamada bir metni seç → global kısayola bas → LLM o metni
(çevirir / dil-bilgisi düzeltir / tonunu resmileştirir / özetler / açıklar) →
sonuç seçili metnin yerine yazılır.

**Hedef kullanıcı:** Geliştiricinin kendisi. Günlük mail, döküman, kod yazarken
kullanılacak. Bu yüzden hız ve "her zaman çalışıyor olması" güzellikten önemli.

---

## 2. MVP Kapsamı

### Dahil (bu sürümde yapılacak)
- Tray (sistem tepsisi) uygulaması, arka planda çalışır.
- En az 4 eylem, her biri ayrı global kısayolla:
  - `Ctrl+Alt+T` → Türkçe ⇄ İngilizce çeviri (dili otomatik algıla, karşıya çevir)
  - `Ctrl+Alt+F` → dil bilgisi / yazım düzeltme (anlamı koru)
  - `Ctrl+Alt+R` → tonu resmileştir / profesyonelleştir
  - `Ctrl+Alt+S` → kısa özet
- Yerel LLM (Ollama) ile çalışma.
- İşlem durumunu gösteren küçük masaüstü bildirimi ("Çevriliyor...", "Tamam", "Hata").
- Eylemleri ve prompt'ları bir config dosyasından okuma (kod değiştirmeden yeni eylem eklenebilsin).

### Dahil değil (sonraki sürümlere bırak)
- Sesli kontrol, GUI pencere, ayar ekranı.
- Bulut/abonelik, çoklu kullanıcı.
- Clipboard geçmişi.

---

## 3. Teknoloji Yığını

- **Dil:** Python 3.11+
- **LLM:** Ollama (yerel). Varsayılan model: `qwen2.5:7b-instruct` (fonksiyon/talimat takibi iyi, Türkçe destekli). Alternatif: `llama3.1:8b`.
- **Global kısayol & klavye simülasyonu:** `pynput` (cross-platform).
- **Clipboard:** `pyperclip`.
- **Tray ikonu:** `pystray` + `Pillow`.
- **Bildirim:** `plyer` (cross-platform). Windows'ta daha şık isteniyorsa `win11toast` alternatif.
- **Config:** `pyyaml` (YAML dosyası).
- **HTTP (Ollama'ya):** `httpx` veya resmi `ollama` paketi.

> Not: Geliştirici Windows kullanıyor olabilir ama kod cross-platform kalsın.
> Windows'a özel bir şey gerekirse `sys.platform` ile ayır.

---

## 4. Mimari ve Dosya Yapısı

```
ai-text-tool/
├── main.py            # Giriş noktası: tray + hotkey kaydı + event loop
├── config.py          # config.yaml okuma/doğrulama
├── config.yaml        # Kısayol -> eylem eşleşmesi ve prompt'lar
├── clipboard.py       # Seçimi kopyala / sonucu yapıştır (timing dahil)
├── llm.py             # LLM sağlayıcı soyutlaması (Ollama varsayılan)
├── actions.py         # Eylemi çalıştırma: metin al -> prompt kur -> LLM -> yapıştır
├── notifier.py        # Masaüstü bildirimleri
├── requirements.txt
└── README.md          # Kurulum ve kullanım
```

**Akış (en kritik kısım):**
1. Kullanıcı bir uygulamada metni seçer ve kısayola basar.
2. `clipboard.py`: mevcut clipboard'ı yedekle → `Ctrl+C` simüle et → kısa bekle (clipboard'ın dolması için ~120ms) → seçili metni oku.
3. `actions.py`: kısayola karşılık gelen eylemin prompt şablonuna metni göm.
4. `llm.py`: Ollama'ya gönder, yanıtı al.
5. `clipboard.py`: yanıtı clipboard'a yaz → `Ctrl+V` simüle et (seçili metnin üzerine yazılır) → sonra orijinal clipboard'ı geri yükle.
6. `notifier.py`: her aşamada durum bildirimi.

> **Timing tuzağı (önemli):** `Ctrl+C` sonrası clipboard hemen dolmaz; mutlaka
> küçük bir `sleep` (80–150ms) koy. Yapıştırma öncesi de clipboard'ın
> set edildiğinden emin ol. Bu zamanlamalar config'ten ayarlanabilir olsun.

---

## 5. Aşamalı Build Planı

### Faz 0 — İskelet ve bağımlılıklar
- Proje klasörünü ve dosyaları oluştur, `requirements.txt` yaz, sanal ortam kur.
- `pip install -r requirements.txt`.
- **Test:** `python -c "import pynput, pyperclip, pystray, plyer, yaml, httpx; print('ok')"` hatasız çalışmalı.

### Faz 1 — Ollama bağlantısı (`llm.py`)
- Ollama'nın `http://localhost:11434/api/chat` (veya `/api/generate`) endpoint'ine basit bir `complete(prompt: str) -> str` fonksiyonu yaz.
- Model adı config'ten gelsin. Sağlayıcıyı soyutla: bir `LLMProvider` arayüzü, `OllamaProvider` implementasyonu. (İleride başka sağlayıcılar eklenebilsin diye.)
- Hata yönetimi: Ollama kapalıysa anlamlı bir mesaj döndür.
- **Test:** Küçük bir script'le `complete("Translate to English: Merhaba")` çağır, doğru sonucu konsola yazdır.

### Faz 2 — Clipboard yardımcıları (`clipboard.py`)
- `get_selected_text() -> str`: orijinal clipboard'ı yedekle, `Ctrl+C` gönder (pynput controller), bekle, oku, döndür.
- `replace_selection(text: str)`: clipboard'a yaz, `Ctrl+V` gönder, bekle, orijinal clipboard'ı geri yükle.
- Bekleme süreleri config'ten.
- **Test:** Bir not defterine metin yaz, seç, küçük bir test script'i ile `get_selected_text()` çağrılınca doğru metni okumalı; `replace_selection("DEĞİŞTİ")` çağrılınca seçili yer değişmeli.

### Faz 3 — Eylemler ve config (`config.yaml`, `config.py`, `actions.py`)
- `config.yaml` şemasını oluştur (aşağıda örnek var).
- `config.py`: YAML'ı yükle, eksik alan varsa makul varsayılan ver.
- `actions.py`: `run_action(action_name)` → seçimi al → prompt'u doldur → LLM'e gönder → sonucu yapıştır. LLM'in açıklama/önsöz eklememesi için prompt'larda "sadece sonucu döndür, yorum ekleme" talimatı olsun.
- **Test:** Test script'i ile `run_action("translate")` çağır; seçili Türkçe metin İngilizceye çevrilip yerine yazılmalı.

### Faz 4 — Global kısayollar + tray (`main.py`, `notifier.py`)
- `pynput.keyboard.GlobalHotKeys` ile config'teki kısayolları ilgili eyleme bağla.
- `pystray` ile tray ikonu: menüde "Çıkış" ve (opsiyonel) "Config'i yeniden yükle".
- `notifier.py`: başla/bitti/hata bildirimleri.
- Hotkey handler'larını ayrı thread'de çalıştır ki UI/loop bloklanmasın.
- **Test:** Uygulamayı çalıştır, gerçek bir uygulamada (mail/Word/tarayıcı) metni seçip her kısayolu dene. 4 eylem de çalışmalı, bildirimler görünmeli.

### Faz 5 — Cila
- LLM çağrısı sırasında "işleniyor" bildirimi; uzun sürerse takılmasın (timeout).
- Boş seçim / çok uzun metin durumlarını yönet (uyarı bildirimi).
- `README.md`: kurulum (Ollama kurulumu dahil), model indirme, çalıştırma, kısayol listesi.
- (Opsiyonel) Windows'ta başlangıçta otomatik çalışma notu.

---

## 6. `config.yaml` Örnek Şeması

```yaml
llm:
  provider: ollama
  model: qwen2.5:7b-instruct
  base_url: http://localhost:11434
  timeout_seconds: 60

clipboard:
  copy_delay_ms: 120
  paste_delay_ms: 80
  restore_original: true

actions:
  translate:
    hotkey: "<ctrl>+<alt>+t"
    prompt: |
      Aşağıdaki metnin dilini algıla. Türkçeyse İngilizceye, İngilizceyse
      Türkçeye çevir. SADECE çeviriyi döndür, başka hiçbir şey yazma.

      Metin:
      {text}

  fix:
    hotkey: "<ctrl>+<alt>+f"
    prompt: |
      Aşağıdaki metnin yazım ve dil bilgisi hatalarını düzelt. Anlamı ve dili
      değiştirme. SADECE düzeltilmiş metni döndür.

      Metin:
      {text}

  formal:
    hotkey: "<ctrl>+<alt>+r"
    prompt: |
      Aşağıdaki metni profesyonel ve resmi bir tona dönüştür, aynı dilde kal.
      SADECE yeniden yazılmış metni döndür.

      Metin:
      {text}

  summarize:
    hotkey: "<ctrl>+<alt>+s"
    prompt: |
      Aşağıdaki metni kısa ve net biçimde özetle, aynı dilde. SADECE özeti döndür.

      Metin:
      {text}
```

> Yeni bir eylem eklemek = sadece bu dosyaya bir blok eklemek. Kod değişmez.
> Bu, ileride Jarvis'e büyütürken çok işine yarar.

---

## 7. Kurulum (README'ye girecek özet)

1. Ollama'yı kur (ollama.com), ardından modeli indir:
   `ollama pull qwen2.5:7b-instruct`
2. Sanal ortam: `python -m venv .venv` ve aktive et.
3. `pip install -r requirements.txt`
4. `python main.py` → tray ikonu çıkar.
5. Bir uygulamada metni seç, kısayollardan birine bas.

**requirements.txt:**
```
pynput
pyperclip
pystray
Pillow
plyer
pyyaml
httpx
```

---

## 8. Test Kontrol Listesi (bitince hepsi geçmeli)

- [ ] Ollama kapalıyken kısayola basınca düzgün hata bildirimi çıkıyor (uygulama çökmüyor).
- [ ] Türkçe metin seçip `Ctrl+Alt+T` → İngilizce yerine yazılıyor.
- [ ] İngilizce metin seçip `Ctrl+Alt+T` → Türkçe yerine yazılıyor.
- [ ] Hatalı metin `Ctrl+Alt+F` ile düzeliyor, anlam korunuyor.
- [ ] `Ctrl+Alt+R` tonu resmileştiriyor.
- [ ] `Ctrl+Alt+S` özet veriyor.
- [ ] İşlem sonrası orijinal clipboard içeriği geri geliyor.
- [ ] Boş seçimde uyarı veriyor, çökmiyor.
- [ ] Tray menüsünden "Çıkış" düzgün kapatıyor.

---

## 9. Bilinen Tuzaklar

- **Clipboard timing:** En sık hata burada. Süreleri config'ten ayarlanabilir tut; bazı makinelerde 120ms yetmez, 200ms gerekebilir.
- **pynput hotkey formatı:** Modifier'lar `<ctrl>+<alt>+t` biçiminde. Tuş çakışmasına dikkat (başka uygulamanın kısayoluyla çakışmasın).
- **Windows izinleri:** Bazı yönetici-modunda çalışan uygulamalara klavye simülasyonu gönderilemeyebilir. Bu durumda not düş.
- **LLM önsöz ekleme:** Model "İşte çeviri:" gibi önek eklerse prompt'a "sadece sonucu döndür" vurgusunu güçlendir; gerekirse yanıtı temizleyen küçük bir post-process ekle.
- **Thread güvenliği:** Hotkey callback'lerini ana loop'u bloklamayacak şekilde ayrı thread'de çalıştır.

---

## 10. İleri Adımlar (Jarvis'e doğru — şimdilik yapma)

- Sağlayıcı soyutlamasına bir bulut sağlayıcı ekle (yerel ↔ bulut geçişi config'ten).
- Seçili metin yerine ekran görüntüsü alıp görüntülü modele sorma eylemi.
- Bas-konuş dikte modülünü (Whisper) aynı tray altına ekle.
- "Komut paleti" penceresi: bu araçların hepsini doğal dil ile çağırma katmanı.

> Mimariyi (config-driven eylemler + sağlayıcı soyutlaması) bu yüzden böyle
> kurduk: her yeni yetenek mevcut iskelete bir eylem olarak takılacak.
