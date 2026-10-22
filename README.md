# Video Edit Uygulaması Açmadan Reels: Claude'la Kurduğum Sistem

**Hazırlayan:** Cem Özen · Instagram [@thecemozen](https://www.instagram.com/thecemozen/) · GitHub [@thecemozen](https://github.com/thecemozen) · Lisans: [MIT](LICENSE)

Bu klasör, ham bir telefon çekimini (konuşan kişi, dikey video) hiçbir kurgu programı açmadan, sadece Claude Code ile konuşarak yayına hazır bir Instagram Reels'e dönüştüren sistemin kendisidir. İçinde araçlar, Claude'un iş akışını öğrendiği "skill" dosyaları, Instagram kuralları ve kurulum talimatı var.

Kod bilmen gerekmiyor. Kurulumu da kurguyu da Claude yapıyor; sen ne istediğini söylüyorsun.

---

## 1. Ne yapıyor?

Ham videoyu verip "bunu kurgula" dediğinde Claude sırasıyla şunları yapar:

| Adım | Ne oluyor |
|---|---|
| Yazıya dökme | Konuşma kelime kelime, zamanıyla birlikte yazıya dökülür (Whisper, bilgisayarında çalışır, internete gönderilmez) |
| Kanca seçimi | Videonun kendi cümleleri "ilk 3 saniyede tutar mı" diye 5 ölçütle puanlanır, tablo halinde sana sunulur. Seçtiğin cümle videonun en başına eklenir |
| Kesim | Sessizlikler, tekrarlar ve yarım cümleler atılır. Aynı cümleyi birkaç kez denediysen en temiz deneme seçilir |
| Kadraj | Yüz ölçülür, kesimlerde yakın ve uzak kadraj dönüşümlü kullanılır (jump cut) |
| Altyazı ve kartlar | Markanın renkleri ve fontlarıyla altyazı, başlık kartları, rozetler ve alıntı kartı çizilir. Hiçbiri yüzün ya da Instagram butonlarının üstüne gelmez |
| Ses | Gürültü temizlenir, ses seviyesi Instagram'a uygun hale getirilir (−14 LUFS) |
| Çıktı | 2160x3840 (4K dikey) yüksek kaliteli MP4 |
| Kapak | 12 aday kare sunulur, sen seçersin. Kapak 4K JPG, düzenlenebilir SVG ve profil ızgarası önizlemesi olarak gelir |
| Açıklama | Marka diline uygun Instagram açıklaması yazılır ve yapay zekâ izlerine karşı kontrol edilir |
| Deneme Reels | İstersen aynı videonun farklı kancalı 3–4 sürümünü ve her birine ayrı açıklama hazırlar (Instagram'ın deneme Reels özelliği için) |

Her video kendi klasörüne düzenli şekilde çıkar: `Final/<tarih>_<Kapak-Basligi>/`.

## 2. Nasıl başlarım? (3 adım)

1. **Claude Code'u kur.** claude.com/claude-code adresinden masaüstü uygulamasını ya da terminal sürümünü indir. Ücretli bir Claude planı gerekir.
2. **Bu depoyu indir.** Bu sayfanın üstündeki yeşil **Code** düğmesine bas ve **Download ZIP**'i seç. Zip'i bir klasöre aç (ör. Masaüstü), sonra Claude Code'da o klasörü aç.
3. **Claude'a şunu yaz:**
   > `README.md dosyasını oku ve sistemi bilgisayarıma kur.`

Claude gerekenleri kontrol edip kuracak (yaklaşık 4 GB indirme, 20–40 dakika). Bittiğinde senden kısa bir test videosu isteyecek.

Kurulumdan sonra:
> `Markam için stil oluşturalım. Logom ve tasarımlarım şu klasörde: ...`

> `Taked klasöründeki IMG_1234.MOV videosunu kurgula.`

> `Bu videonun 4 farklı kancalı sürümünü hazırla, deneme Reels'te paylaşacağım.`

## 3. Bilgisayar gereksinimleri

| | Önerilen | En az |
|---|---|---|
| İşletim sistemi | Windows 10/11 | macOS da olur (Claude yolları uyarlar) |
| Ekran kartı | NVIDIA (6 GB+) | Yoksa işlemciyle çalışır, yazıya dökme 5–10 kat yavaşlar |
| Disk | 10 GB boş alan | 6 GB |
| RAM | 16 GB | 8 GB |

## 4. Çekim ipuçları (sistem en iyi böyle çalışır)

- Dikey çek, yüz kadrajın üst yarısında olsun. Telefonun 4K ayarı varsa aç (1080p de olur, Claude söyler).
- Cümleyi beğenmezsen durma, aynı cümleyi baştan tekrar söyle. Claude en temiz denemeyi seçer.
- Kamera arkasından biri metni okuyorsa (süflör) sorun değil. Claude yalnızca kameradaki kişinin sesini kullanır, ama her cümleyi en az bir kez **tam** söylemiş ol.
- Videonun sonunda net bir çağrı söyle ("Kaydet ve birine gönder." gibi).

---

# CLAUDE İÇİN: KURULUM TALİMATI

> Bu bölüm Claude Code içindir. Kullanıcı kod bilmiyor ve terminal kullanmıyor. Bütün komutları sen çalıştır. Her adımda ne yaptığını tek, sade bir Türkçe cümleyle anlat. Bir şey indirmeden önce ne indireceğini ve boyutunu söyle.

## K0. Ortamı tanı

- İşletim sistemini, ekran kartını (`nvidia-smi`), boş disk alanını ve `ffmpeg`/`python` varlığını kontrol et. Sonucu kullanıcıya iki üç cümleyle özetle.
- Bu klasör proje köküdür (`KOK`). Bütün yollar buna göredir: `araclar/`, `markalar/`, `fontlar/`, `modeller/`, `Taked/` (ham çekimler), `Likes/` (beğenilen referans videolar), `Final/` (bitmiş videolar), `calisma/` (ara dosyalar), `.claude/skills/`.
- Windows'ta Python yolu `.venv\Scripts\python.exe`, macOS/Linux'ta `.venv/bin/python`. Skill'lerdeki komutlar Windows yazımıyla verilmiştir; gerekirse uyarla.

## K1. ffmpeg

- Windows: `winget install Gyan.FFmpeg` (tam sürüm). macOS: `brew install ffmpeg`.
- Doğrula: `ffmpeg -version` ve `ffprobe -version`. Sürüm 6 ve üstü olmalı.

## K2. Python ortamı

1. Python 3.12 kur (Windows: `winget install Python.Python.3.12`; macOS: `brew install python@3.12`).
2. Proje kökünde: `python -m venv .venv`
3. `.venv` içindeki pip ile: `pip install -r gereksinimler.txt`
4. NVIDIA ekran kartı varsa ayrıca: `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*`
5. Doğrula: `python -c "import faster_whisper, mediapipe, cv2, librosa, PIL, scipy; print('tamam')"`

## K3. Modeller (`modeller/` klasörü)

| Dosya | Kaynak | Boyut |
|---|---|---|
| `modeller/faster-whisper-large-v3/` | Hugging Face `Systran/faster-whisper-large-v3` (`huggingface_hub.snapshot_download(repo_id=..., local_dir=...)`) | ~3 GB |
| `modeller/blaze_face_short_range.tflite` | `https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite` | ~250 KB |

- Ekran kartı yoksa ve bilgisayar yavaşsa `Systran/faster-whisper-medium` da indirilebilir. Bu durumda araçlardaki model klasör adını değiştir ve Türkçe doğruluğun biraz düşeceğini kullanıcıya söyle.

## K4. Fontlar ve skill'ler

- `fontlar/` klasöründeki fontlar SIL Open Font License ile ücretsizdir, lisansları yanındadır. Yeni marka başka bir font isterse Google Fonts'tan indir. Lisanslı (ücretli) fontları kopyalama; en yakın ücretsiz eşdeğeri seç.
- `.claude/skills/` içindeki iki skill bu klasörde Claude Code tarafından otomatik tanınır:
  - `reels-kurgu`: Bütün kurgu iş akışı ve kuralları. **Kurguya başlamadan önce mutlaka yükle.**
  - `marka-stili-olustur`: Yeni marka için renk, font, kart ve ses tonu dosyalarını kurar.
- İsteğe bağlı: açıklama metinlerini yapay zekâ izlerine karşı temizleyen `ig-human` skill'i. Kaynak: `https://github.com/Jakeschincariol/instagram-agent-skill`. `skills/ig-*` klasörlerini `~/.claude/skills/` içine kopyala. `araclar/metin_kontrol.py` bunu `~/.claude/skills/ig-human/humanize.py` yolundan kullanır; yoksa yalnızca Türkçe klişe kontrolü çalışır.

## K5. Bilinen tuzaklar

1. **Antivirüs SSL denetimi** (ör. Kaspersky): pip ya da indirme `CERTIFICATE_VERIFY_FAILED` verirse güvenliği kapatma. `pip install truststore` kur ve Python içinden indirmeden önce `import truststore; truststore.inject_into_ssl()` çağır.
2. **PyAV sürümü:** faster-whisper yeni PyAV ile hata verir. `av<16` sabit kalmalı (gereksinimlerde var).
3. **Windows'ta CUDA DLL'leri:** Araçlar `.venv/Lib/site-packages/nvidia/*/bin` klasörlerini `os.add_dll_directory` ile ekler. Yeni bir betik yazarsan aynısını yap.
4. **iPhone videoları yan kaydedilmiş olabilir** (döndürme bilgisi). Kareleri her zaman ffmpeg ile oku, OpenCV ile doğrudan açma.
5. **Türkçe çıktı:** Python'u `-X utf8` ile çalıştır.
6. **Bash heredoc içinde kesme işareti (')** betiği bozar. Uzun betikleri önce dosyaya yaz, sonra çalıştır.
7. **Klasör açıkken Windows yeniden adlandırmaya izin vermez** (`PermissionError`). `final.py` dosyaları tek tek taşır.
8. **Skill `description` satırında "iki nokta + boşluk"** YAML'ı bozar.
9. **4K kodlamayı paralel çalıştırma.** Aynı anda birkaç `kes.py` çalışınca dosya yarım kalabilir. Sırayla çalıştır, her çıktının süresini `ffprobe` ile doğrula.

## K6. Test

1. Kullanıcıdan 20–60 saniyelik dikey bir konuşma videosu iste ve `Taked/` klasörüne koymasını söyle (ya da yolunu al ve kopyala; asıl dosyayı taşıma).
2. `reels-kurgu` skill'ini yükle ve `markalar/ornek/` temasıyla akışı baştan sona çalıştır.
3. Örnek kareleri göster. Çalışıyorsa kullanıcıya bir sonraki adımı öner: kendi markasının stilini `marka-stili-olustur` ile kurmak.

## K7. Kurulum bitince

- `KURULUM.md` adında kısa bir not yaz: kurulum tarihi, bilgisayar, kurulan sürümler, karşılaşılan sorunlar ve çözümleri.
- Kullanıcıya şunu söyle: "Artık bir videoyu Taked klasörüne koyup 'kurgula' demen yeterli."

---

# CLAUDE İÇİN: ÇALIŞMA KURALLARI (ÖZET)

Ayrıntılar `.claude/skills/reels-kurgu/SKILL.md` içinde. Bu sistemi kuran kişinin kurgu sırasında koyduğu ve deneyerek oturttuğu kurallar:

**Kullanıcıyla çalışma**
- Kullanıcı kod bilmez. Her adımı tek cümleyle anlat, teknik ayrıntıyı ancak sorulursa ver.
- Onay noktaları: kanca seçimi, plan ve örnek kareler, kapak karesi. Bunlar onaylanmadan tam çıktı alınmaz.
- Kullanıcının dosyalarını silme ya da taşıma. Eski sürümler `eski/` klasörüne taşınır, silinmez.
- Kullanıcı bir düzeltme söylediğinde bunu ilgili skill'e ya da marka dosyasına kalıcı kural olarak yaz, bir dahakine tekrar söyletme.

**Kurgu**
- Konuşmayı hızlandırma; tempo yalnızca kesimle kurulur.
- Sessizlikleri Whisper zamanlarından değil, ses enerjisinden bul.
- Çok denemeli çekimde her denemeyi ayrı ayrı yazıya dök ve son temiz denemeyi seç.
- **Yalnızca kameradaki kişinin sesi kullanılır.** Kamera arkasından okuyan biri (süflör) olabilir; Whisper metni aynı çıkar, fark ancak ses perdesinden anlaşılır. Her seçili aralığı ses perdesiyle kontrol et.
- Kesimden sonra `kesim_kontrol.py` ile kelime kaybı olmadığını doğrula.

**Görünüm**
- Çıktılar her zaman 2160x3840 (4K) ve yüksek kalitede.
- Instagram'ın üst bandı (y<250), alt bandı (y>1470) ve sağ ikon sütunu boş kalır; yüzün üstüne hiçbir şey gelmez. `kurgu.py --kontrol` 0 ihlal vermeden çıktı alınmaz.
- Renk, font ve süs öğeleri yalnızca markanın kendi tasarımlarından gelir.

**Kanca**
- Kanca, videonun kendi cümlelerinden seçilir. Adayları 5 ölçütün (uzunluk, somutluk, gerilim, öne çıkma, hitap) puan dökümüyle **tablo halinde** sun. Kullanıcı onaylamadan ekleme.
- Deneme Reels için her sürüm farklı bir kanca stratejisi olsun (soru, yanlış inanış, şaşırtıcı bilgi) ve biri kancasız kontrol sürümü olsun. Her sürüme ayrı açıklama yaz.

**Teslim**
- Klasör ve dosya adı kapak başlığıdır: `Final/<YYYY-MM-DD>_<Baslik>/` (video, açıklama, `BILGI.md`, `kapak/`, `eski/`).
- Kapak karesini kullanıcı seçer; her kapakla birlikte düzenlenebilir SVG verilir.
- Açıklama ve kart metinleri teslimden önce `metin_kontrol.py` ile kontrol edilir. En fazla 5 etiket.
- Müzik varsayılan olarak yok (telif riski); kullanıcı isterse eklenir.

---

## Dosya haritası

```
README.md   bu belge (insan + Claude)
CLAUDE.md                                Claude Code'un klasörü açınca okuduğu kısa yönlendirme
gereksinimler.txt                        Python paketleri
INSTAGRAM_KURALLARI.md                   güvenli alanlar, kapak ızgarası, açıklama ve etiket kuralları
.claude/skills/reels-kurgu/              kurgu iş akışı (ana skill)
.claude/skills/marka-stili-olustur/      yeni marka kurulumu
araclar/                                 bütün araçlar (Python)
markalar/_sablon/                        yeni marka şablonu (tema.json, marka_kimligi.md, skill şablonu)
markalar/ornek/                          başlangıç markası (test için)
calisma/_ornek/plan_olustur.py           örnek kurgu planı
fontlar/                                 ücretsiz fontlar ve lisansları
modeller/                                kurulumda indirilir
Taked/  Likes/  Final/                   ham çekimler, referanslar, bitmiş videolar
```

## Araçlar

| Araç | Ne yapar |
|---|---|
| `yaziya_dok.py` | Kelime zamanlı metin (Whisper large-v3) |
| `secim_metni.py` | Çok denemeli çekimde seçilen aralıkları ayrı ayrı yazıya döker |
| `kanca_bul.py` | Kanca adaylarını 5 ölçütle Türkçe puanlar |
| `kesim_plani.py` | Sessizlik haritası ve kesim listesi; `--secim`, `--esitle`, `--kanca`, zoom kesimi |
| `kes.py` | Kesim, kadraj ve 4K ölçekleme |
| `kesim_kontrol.py` | Kesik videoyu yeniden yazıya döküp kelime kaybını arar |
| `yuz_olc.py` | Yüz konumu (yazılar yüze binmesin diye) |
| `plan_arac.py` | Kelime tabanlı kurgu planı yardımcısı (`Plan` sınıfı) |
| `kurgu.py` | Altyazı, kart, rozet, alıntı ve geçişleri çizer; `--kontrol` güvenli alan denetimi |
| `cikti.py` | Ses zinciri, geçiş sesi, kapanış ve son 4K kodlama |
| `kapak.py` | Kapak adayları; seçilen kareyle 4K JPG + SVG + ızgara önizlemesi |
| `final.py` | Çıktı klasörü düzeni ve `BILGI.md` |
| `metin_kontrol.py` | Açıklama ve kart metni kontrolü |
| `marka_tara.py` | Marka dosyalarından renk ve font çıkarır |
| `ritim_olc.py` | Referans videonun kesim ritmini ölçer |
