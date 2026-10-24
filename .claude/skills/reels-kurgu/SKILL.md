---
name: reels-kurgu
description: Ham dikey konuşma videosunu Instagram Reels'e kurgulama iş akışı (kesim, kesim kontrolü, yüz ölçümü, altyazı ve kartlar, ses, 2160x3840 4K çıktı, kapak, kontrol listesi). Markadan bağımsızdır; görünüm ve dil için ilgili marka stili skill'ini (ör. <marka>-stili) birlikte yükle. Kullanıcı "kurgula", "reels yap", "şu videoyu düzenle" dediğinde ya da Taked klasöründeki bir videoyu işlemek istediğinde kullan.
---

# reels-kurgu (genel iş akışı)

Kullanıcı kod bilmiyor ve terminal kullanmıyor. Bütün komutları sen çalıştır, her adımda ne yaptığını tek cümleyle Türkçe anlat.

## 0. Önce marka

**Video hangi marka için?** Kullanıcı söylemediyse ve birden fazla marka varsa sor.

| Marka | Stil skill'i | Ayarlar |
|---|---|---|
| Örnek Marka (başlangıç) | yok (marka-stili-olustur ile kur) | `markalar/ornek/` |

- Markanın stil skill'ini yükle. Renkler, fontlar, ses tonu, açıklama dili, müzik kararı ve kalıcı kullanıcı kuralları oradadır.
- Markanın stili yoksa `marka-stili-olustur` skill'iyle önce stili kur, ya da kullanıcıya sor.
- Yeni marka eklenince bu tabloya bir satır ekle.

## Klasörler ve araçlar

- **Klasörler:**
  - `Taked/` ham çekimler, `Likes/` referanslar, `Final/` bitmiş videolar.
  - `calisma/<video_adi>/` ara dosyalar.
  - `markalar/<marka>/` marka dosyaları (`tema.json`, `marka_kimligi.md`, logo, kapanış).
  - `fontlar/`, `modeller/`.
- **Python:** `.venv\Scripts\python.exe`. Tuzaklar için `KURULUM.md` dosyasına bak (Kaspersky SSL, CUDA DLL, `av<16`). Türkçe çıktı için `PYTHONIOENCODING=utf-8`. Bash heredoc içinde kesme işareti (') sorun çıkarır; uzun betikleri dosyaya yazıp çalıştır.
- **Araçlar:**

| Araç | Ne yapar |
|---|---|
| `araclar/yaziya_dok.py <video> <json> [--terimler "..."]` | Kelime zamanlı metin (GPU, large-v3) |
| `araclar/kesim_plani.py <video> <klasor> --yuz <ham_yuz.json> --metin <metin.json> [--olcek 1.30,1.45] [--atla "a-b"]` | Sessizlikleri enerjiden bulur, `kesimler.json` yazar; 4,5 sn'den uzun parçaları kelime arasından **zoom kesimiyle** böler (hiçbir şey atılmaz) |
| `araclar/kes.py <video> <kesimler.json> <kesik.mp4>` | Kesim ve ölçek değişimi. Zamanları kare sınırına yuvarlar; zoom kesiminde (`bitisik`) ses fade'i yapmaz |
| `araclar/kesim_kontrol.py <klasor>` | Kelime kaybı ve kesik hece kontrolü |
| `araclar/yuz_olc.py <video> <json> --aralik 0.2` | Yüz kutuları (1080x1920) |
| `araclar/kurgu.py <klasor> --kareler t1,t2 / --kontrol / --tam out.mp4` | Altyazı, kart, rozet ve geçişleri `plan.json`'a göre çizer. `"tema": "<marka>"` ilgili `markalar/<marka>/tema.json` dosyasını yükler |
| `araclar/ritim_olc.py <video>` | Yalnızca **yazısız referans** videolarda kesim ritmi ölçer |
| `araclar/kapak.py --adaylar 12 --video <kesik.mp4> --cikti Final/<ad>_kapak.jpg` | Kapak için numaralı aday kare tablosu (`_kapak_adaylari.jpg`) |
| `araclar/kapak.py --tema <marka> --video .. --aday N --ust .. --baslik "a\|b" --vurgu 2 --cikti ..` | Seçilen kareyle kapak: 4K JPG + **düzenlenebilir SVG** + 3:4 ızgara önizlemesi |
| `araclar/marka_tara.py <cikti> <kaynaklar..>` | Marka dosyalarından renk, font ve tasarım tablosu çıkarır |
| `araclar/plan_arac.py` (içe aktarılır) | `Plan` sınıfı: `p.kelime("sabır")` kesik zamanı, `p.gecis_once("ama")` bölüm geçişi, `duzelt={zaman: "kelime"}` Whisper düzeltmesi, `p.kaydet(ogeler, gecisler, vurgu)` altyazıyla birlikte `plan.json` |
| `araclar/kanca_bul.py calisma/<video> [--duzelt "46.42=da;..."] [--en 5]` | Videonun kendi konuşmasından kanca adaylarını bulur, `ig-reel`'in 5 ölçütüyle **Türkçe** puanlar (`kanca_adaylari.json`) |
| `araclar/srt_yaz.py oner <calisma>` / `yaz <calisma> --final <Final/..> --ad <Baslik>` | SRT altyazı: son videonun kelimelerinden cümle düzeyinde Türkçe bloklar önerir (`altyazi_bloklar.json`); çeviriler eklenince bütün dilleri denetleyip `altyazi/` klasörüne yazar |
| `araclar/metin_kontrol.py <dosya.txt> [--uygula]` | Açıklama/kart metni son kontrolü: `ig-human` temizliği (görünmez karakter, uzun tire) + Türkçe klişe, etiket ve emoji sayımı |
| `araclar/cikti.py <klasor> <Final/..mp4> --ses temiz\|ham` | Görüntü, whoosh, kapanış, −14 LUFS ve son kodlama |
| `araclar/kurgu_v1.py` | Eski v1 motoru (yalnızca eski videoları yeniden üretmek için) |

- **Örnek plan üreticisi** (kelime tabanlı, önerilen): `calisma/_ornek/plan_olustur.py`. Yeni videoda kopyala; kart ve rozet zamanlarını kelimelerle yaz, saniye yazma.
- **Ses modu:**
  - Kullanıcı sesi kendisi düzelttiyse (yüksek LUFS, düşük LRA) `--ses temiz` kullan. Gürültü azaltma ve kompresör tekrar uygulanmaz.
  - Telefon sesi ise `--ses ham`.
- **Kadraj:** Yüz kameraya yakın çekilmişse (1,45 ölçekte çene y > 1200'e iniyorsa) `--olcek 1.15,1.28` kullan.
- **Kullanıcının eklediği giriş efektleri** (ör. ışık patlaması) korunur; kullanıcıya belirt.
- iPhone videolarını her zaman ffmpeg ile oku (döndürme bilgisi).

## Çıktı klasörü

Her video kendi klasörüne çıkar; `Final/` köküne dağınık dosya bırakılmaz.
**Klasör ve dosya adı = kapak başlığı**: Kullanıcı ham çekim verir (IMG_xxxx); ad bilgi taşımalı.
Türkçe karakter ve boşluk yok: `final.py slug "Eşlik mi,|işgal mi?"` → `Eslik-mi-Isgal-mi`.

```
Final/<YYYY-MM-DD>_<Baslik>/
    <Baslik>_reels_4K.mp4     son video
    <Baslik>_aciklama.txt     Instagram açıklaması
    BILGI.md                  teknik bilgiler + kontrol sonuçları (cikti.py otomatik yazar)
    kapak/                    seçilen kapaklar (.jpg + .svg + _izgara.jpg) ve aday tablosu
    altyazi/                  <Baslik>.tr_TR.srt + çeviriler (<Baslik>.en_US.srt ...)
    eski/                     önceki sürümler (silinmez, buraya taşınır)
```

- **Klasör yolu:** Kapak başlığı plan aşamasında belirlenir; `final.py klasor <Baslik>` ile klasörü aç (çalışma klasörü `calisma/<IMG_xxxx>` kalabilir).
- **Sonradan adlandırma:** `final.py adlandir Final/<tarih>_<eski> --baslik "Başlık"` klasörü ve içindeki dosyaları yeniden adlandırır, BILGI.md'ye eski adı (ham çekim adı) yazar. Aynı başlıkta klasör varsa (aynı bölümün başka sürümü) eskisini o klasörün `eski/` bölümüne taşır.
- **Ham çekim adı** BILGI.md'de durur (`Ham çekim / eski adı`, `Kaynak`).
- **Düzenleme:** Kökte dağınık dosya kalırsa `final.py duzenle` ile topla.
- **BILGI.md'yi yenileme:** Açıklama ya da kapak ekledikten sonra `final.py bilgi <klasor> --calisma calisma/<video>`.
- **Yeni sürüm:** Aynı videonun yeni sürümü çıkarken öncekini `eski/` klasörüne taşı.

## Çözünürlük ve kalite

- **Bütün çıktılar her zaman 2160x3840 (4K dikey) ve yüksek kalitede.** Video, kapak ve kapanış kartı dahil.
- **Kesim:** `kes.py` kaynaktan kırpıp 2160x3840'a ölçekler. Kaynak 4K değilse kullanıcıya söyle.
- **Yazı ve kartlar:** Yerleşim mantıksal 1080x1920 koordinatlarında kalır; `kurgu.py` çizimi kesik videonun çözünürlüğünde (2 kat) yapar. Yazılar büyütülmez, doğrudan 4K çizilir.
- **Ara dosyalar:** CRF 10. **Son dosya:** H.264 High L5.2, CRF 16, preset slow, aq-mode 3, en fazla 60 Mbit/sn, bt709, AAC 192k 48 kHz, faststart.
- **Netlik:** Zoom ölçeği büyüdükçe (1,28–1,45) kırpılan alan 4K'ya büyütülür ve bir miktar yumuşar. Netlik önemliyse ölçeği düşük tut.

## Ekran düzeni (mantıksal 1080x1920, her marka için aynı)

Kaynak ve gerekçe: `INSTAGRAM_KURALLARI.md`. Meta resmi piksel değeri yayınlamıyor; değerler güvenli tarafta seçildi.

| Bölge | Sınır | Kural |
|---|---|---|
| Instagram üst bandı | y < 250 | Hiçbir şey yok |
| Instagram alt bandı (açıklama, butonlar) | y > 1470 | Hiçbir şey yok |
| Sağ ikon sütunu | x > 900 ve y > 900 | Boş |
| Yüz | `yuz_olc.py` kutusu + 24 px, her sahne ayrı | Hiçbir şey girmez |
| Kartlar | Başın üstü (boşluk varsa, y ≥ 260) ya da göğüs hizası (y ≈1203–1333, x 60–900). Alıntı kartı y ≈1175–1333 | |
| Altyazı | Tek satır, gölge dahil alt kenar y=1462, merkez x=525, en fazla `tema.altyazi.max_genislik` | |

`kurgu.py --kontrol` şunları sayar: yüz ihlali, bant ihlali, ikon sütunu ihlali ve **öğelerin birbirine binmesi** (ör. kart ile altyazı). 0 ihlal olmadan tam çıktı alınmaz.

## Kurgu ve ritim

1. **Konuşmayı hızlandırma.** Tempo yalnızca kesimle kurulur.
2. Tekrarların **son temiz hâlini** bırak; yarım cümleleri ve dolguları at.
3. Sessizlikleri Whisper zamanlarından değil, **ses enerjisinden** bul. Eşik: gürültü + %35 × (konuşma − gürültü). 0,35 sn'den uzun boşluğu kes; önde 0,10 sn, arkada 0,08 sn pay bırak. Kelime içindeki kısa sessizliklere (uzatılmış ünlü olabilir) dokunma.
4. **Jump cut ve ölçek değişimi:** Kesim başına ~2–2,5 sn. Ölçek 1,30 ↔ 1,45 arasında dönüşümlü, kırpma yüz merkezine göre. Yüz genişliği kare genişliğinin %45–55'i.
5. **Bölüm geçişi:** 5 karelik zoom-in (1,0 → 1,35) ve dikey hareket bulanıklığı. Tema `gecis.isik` açıksa vurgu renginde ışık eklenir.
6. Videonun en az %90'ı tam ekran kişi. Bölünmüş ekran yok; gerekirse önce sor.

## Altyazı, kart ve rozet (yerleşim; görünüm temadan gelir)

- **Altyazı:**
  - 2–4 kelimelik öbekler, tek satır.
  - Cümle sınırında birleştirme yok. Tek kelimelik öbeği aynı cümledeki komşusuna ekle.
  - Vurgu kelimeleri `"vurgu": [...]` ile verilir (öbek başına en fazla 1–2).
  - Konuşulduğu gibi yazılır; Türkçe büyük/küçük harf kuralı uygulanır (İ/i, I/ı).
- **Kart:**
  - Kartın başlığı (eyebrow) konuyu adlandırır.
  - Maddeler söylendikçe birer birer belirir.
  - Kart bölüm boyunca ekranda kalır.
  - Açılış kartı için `"buyuk": true` ve tek madde.
- **Rozet:** İlk saniyelerde ana kavramlar, söylenen kelimeyle birlikte belirir. İki rozet altyazı merkezine göre ortalanır.
- **Alıntı kartı** (`"tur": "alinti"`, `"satirlar": [..]`, `"imza": ".."`): Konuşmacının videodaki en güçlü cümlesi için, en fazla 2 satır. Marka teması `alinti` bölümünü tanımlamalı.
- Her yeri doldurma. Geçiş cümlelerinde yalnızca kişi ve altyazı kalır.

## Ses

- **Konuşma:** 80 Hz yüksek geçiren filtre ve `afftdn=nf=-25`. Kesimlerde 12 ms fade.
- **Dinamik:** `acompressor` (threshold 0.08, ratio 3, attack 5, release 90) ve `alimiter`. Sonra −14 LUFS için kazanç ve 0,84 limit. Hedef: **−14 LUFS**, tepe ≤ −1 dBTP.
- **Geçiş sesi:** Bölüm geçişlerinde kodla üretilmiş çok kısık whoosh (−30 dBFS, 0,25 sn). Telifli ses yok.
- **Müzik:** Marka skill'indeki karara göre. Karar yoksa sor; varsayılan müziksiz.

## Çok denemeli çekim ve süflör

- Ham çekimde aynı cümle 2–4 kez denenmiş olabilir. Her denemeyi `secim_metni.py` ile ayrı ayrı yazıya dök, **son temiz denemeyi** seç ve `kesim_plani.py --secim "b1-e1,..." --esitle` kullan (`--esitle` denemeler arasındaki seviye farkını eşitler).
- **Kamera dışından cümleyi okuyan biri (süflör) olabilir.** Kurguda yalnızca kameradaki kişinin sesi kullanılır. Whisper metni aynı olduğu için süflör denemesi fark edilmeyebilir. Seçilen her aralığın ses perdesine bak (`librosa.yin`). Konuşmacının ortalaması ölçülür (ör. erkek ≈ 105 Hz). 0,5 sn'lik bloklarda sesli karelerin yarısından çoğu 170 Hz üstündeyse orası başka biridir. Bir parçanın +6 dB ve üstü kazanç istemesi uyarı işaretidir.
- Kişi bir cümleyi hiç tam söylememişse süflörün hâli kullanılmaz: cümleyi çıkar (akış bozuluyorsa kullanıcıya sor).
- Çıktıdan önce `kesik.mp4` üzerinde aynı perde kontrolünü tekrarla.

## Deneme Reels (A/B) sürümleri

Instagram'ın deneme Reels özelliği için aynı videonun farklı kancalı sürümleri istenebilir:
- Her sürüm ayrı bir kanca **stratejisi** olmalı (soru, yanlış inanış, şaşırtıcı bilgi…); aynı fikrin tekrarı olmamalı. Biri **kancasız kontrol sürümü** olsun, karşılaştırma ancak böyle anlamlı olur.
- Gövde kurgusu ortaktır: `calisma/<video>/` içinde bir kez kesilir. Her sürüm `calisma/<video>-V1..Vn/` klasöründe aynı `kesimler.json`'a kendi `kanca` alanını ekler. Tek bir `plan_olustur.py <klasor>` hepsine uygulanır.
- `kes.py`'yi **paralel çalıştırma**, sırayla çalıştır. Paralel 4K kodlamada dosya yarım kalabilir. Her `kesik.mp4`'ün süresini `ffprobe` ile kontrol et.
- Her sürüme **ayrı açıklama** yaz; ilk cümlesi o sürümün kancasıyla aynı yönde olsun: `<Baslik>_V1_<Strateji>_aciklama.txt`. Hepsi tek klasörde: `Final/<tarih>_<Baslik>/<Baslik>_V1_<Strateji>.mp4`.
- **Her sürüme ayrı SRT** (kanca açılışı farklı olduğu için zamanlar kayar): `srt_yaz.py oner calisma/<video>-V1`, dosya adı `<Baslik>_V1_<Strateji>`. Gövde çevirileri ortaktır; yalnızca kanca bloğu ve zamanlar değişir, önceki sürümün `altyazi_bloklar.json` çevirilerini kopyala.

## SRT altyazı ve çeviriler

Her videonun teslimine Türkçe SRT ve popüler dillerde çevirileri eklenir: `Final/<tarih>_<Baslik>/altyazi/`.
- **Varsayılan diller:** tr + en, es, pt-BR, hi, id, ar, fr, de, ru (Instagram'ın büyük pazarları). Kullanıcı başka dil isterse `srt_yaz.py` içindeki `META` sözlüğünde kodu varsa eklenir.
- **Dosya adı:** `<Baslik>.<dil_BOLGE>.srt` (Meta dil kodu: tr_TR, en_US, es_LA, pt_BR, hi_IN, id_ID, ar_AR, fr_FR, de_DE, ru_RU). Facebook / Meta Business Suite dili addan tanır.
- **Adımlar:**
  1. `srt_yaz.py oner calisma/<video>`: son videodaki kelimelerden (kanca dahil, kesimde atılanlar hariç, `plan_olustur.py` düzeltmeleriyle) Türkçe blok taslağı üretir.
  2. Taslağı gözden geçir: blokları konuşmanın doğal duraklarına ve yan cümlelere göre düzelt. Altyazı konuşulduğu gibi kalır (videoya işlenen altyazıyla aynı kelimeler); noktalama ve büyük harf düzgün olur.
  3. Her bloğa çevirileri ekle (`"en": "..."`, satır kırmak için `\n`). Blok cümle düzeyinde olduğu için her çeviri kendi söz dizimiyle o bloğa sığmalı.
  4. `srt_yaz.py yaz ...`: eksik çeviri, 2 satır sınırı, satır uzunluğu (~42 kar.) ve okuma hızı (> 25 kar/sn uyarı) denetlenir. Uyarı varsa çeviriyi kısalt.
- **Çeviri kuralları:**
  - Terimleri bir videoda her dilde tutarlı kullan (ör. eşlik → accompanying / acompañar / Begleiten; işgal → invading / invadir / Vereinnahmen; tekâmül → spiritual growth).
  - Bir kelimenin birebir karşılığı başka bir çağrışım taşıyorsa anlamı veren karşılığı seç (ör. işgal: Hintçe दख़ल, Endonezce mencampuri, Arapça التدخّل) ve kullanıcıya söyle.
  - Marka terimleri ve özel kavramlar çoğu dilde aynen kalır.
  - Çağrı cümlesi o dilin Instagram alışkanlığıyla çevrilir ("Kaydet ve birine gönder." → "Save this and send it to someone.").
- **Kullanıcıya söyle:** Çeviriler ana dili o dil olan biri tarafından okunmadı; özellikle Arapça ve Hintçe yayından önce okutulmalı. Instagram uygulaması SRT yüklemeyi her hesapta sunmaz; Meta Business Suite üzerinden yüklenebilir.

## Metin doğruluğu

- Whisper alan terimlerini yanlış duyar. Markanın düzeltme sözlüğünü uygula, emin olmadığın kelimeyi sor.
- Ekranda rakam ya da bilimsel iddia gösterilecekse önce internetten doğrula ve kaynağını söyle.
- Gerçek kişi görseli, logo ya da arşiv videosu gerekiyorsa önce sor.

## Kanca adımı

`ig-reel` mantığıyla, ama **videonun kendi konuşmasından**:
1. Yazıya dökme ve düzeltmeden sonra `kanca_bul.py calisma/<video> --duzelt "..."` çalıştır.
2. Kullanıcıya göster: şu anki açılış cümlesi ve puanı, en iyi 5 aday. **Her zaman tablo halinde ve beş ölçütün (uzunluk, somutluk, gerilim, öne çıkma, hitap) puan dökümüyle**; kullanıcı seçimini buna bakarak yapar. Öneri yap, gerekçesini bir cümleyle söyle.
   - Marka etik sınırına takılan aday (ör. "seni hasta eder" gibi sağlık benzetmesi) varsa belirt.
   - Yarım cümleler "(yarım cümle)" olarak işaretlidir; tek başına anlamı kalıyor mu, söyle.
3. **Kullanıcı onayı olmadan kanca eklenmez.** Seçenekler: (a) seçilen aday videonun başına kanca olarak eklenir, (b) mevcut açılış kalır.
4. Onaylanırsa: `kesim_plani.py ... --kanca "<ham_bas>-<ham_son>"`. Kanca, sessizlik sınırına oturtulup videonun en başına bir kez daha (biraz daha yakın kadrajla) eklenir; cümle kendi yerinde de kalır. Plan aracı bütün zamanları kanca süresi kadar kaydırır, kancaya kendi altyazısını yazar, kanca bitiminde geçiş ekler ve kanca anında kart/rozet göstermez.
5. Puan bir tahmin değildir (boş açılış, somut olmayan ve uzun cümleyi yakalar); son karar kullanıcınındır.

## Çalışma sırası

1. Markayı belirle ve marka skill'ini yükle. `ffprobe` ile videoya bak. `calisma/<video_adi>/` klasörünü aç.
2. `yaziya_dok.py` ile metni çıkar ve düzelt. Ardından **kanca adımı**: `kanca_bul.py`, kullanıcıya göster, onay al.
3. Sessizlikleri enerjiden bul, `kesimler.json` dosyasını yaz, `kes.py` ile kes.
4. `kesim_kontrol.py` çalıştır. Kelime farkı 0 olmalı (yazım farkları hariç).
5. `yuz_olc.py` ile kesik videoda yüzü ölç.
6. `plan_olustur.py` ile `plan.json` üret: altyazı ve vurgu, kartlar, rozetler, geçişler, `"tema": "<marka>"`.
7. `kurgu.py --kontrol`: 0 ihlal.
8. **Onay:** Saniye saniye plan tablosu ve 6 örnek kare göster (kanca, rozet, geçiş, kartlar, kapanış). **Onay gelmeden tam çıktı alma.**
9. Tam çıktı:
   - `kurgu.py --tam` ile görüntü.
   - Ses zinciri ve whoosh.
   - Markanın kapanışı (`tema.dosyalar.kapanis`) 0,15 sn xfade ile eklenir.
   - Biçim: 2160x3840, 30 fps, H.264 High L5.2, CRF 16, slow, yuv420p, bt709, AAC 192k 48 kHz, faststart (`cikti.py` bunu yapar).
   - Dosya: `Final/<tarih>_<Baslik>/<Baslik>_reels_4K.mp4` (klasör: `final.py klasor <Baslik>`).
10. **Kontrol listesi:**
    - `ebur128` ile −14 ±0,5 LUFS.
    - İhlal 0.
    - Kesim ritmini `kesimler.json` üzerinden say.
    - Bitmiş videoyu yeniden yazıya döküp kelime kaybı olmadığını doğrula.
    - Saniyede bir kareyle görsel tarama yap.
    - **Kapak:** Kapak karesini **kullanıcı seçer**.
      1. `kapak.py --adaylar 12 --cikti Final/<tarih>_<Baslik>/kapak/<Baslik>_kapak.jpg` ile numaralı aday tablosunu üret ve kullanıcıya göster.
      2. Kullanıcının seçtiği her kare için `--aday N --cikti Final/<tarih>_<Baslik>/kapak/<Baslik>_kapak_<N>.jpg`.
      3. Çıktılar: `<ad>_kapak.jpg` (4K), `<ad>_kapak.svg` (yazılar ayrı düzenlenebilir katman, fontlar gömülü), `<ad>_kapak_izgara.jpg`.
      4. Izgara önizlemesinde başlık ve logo tam görünmeli. Kullanıcı seçmeden kapağı kesinleştirme.
    - Açıklamayı marka diliyle `ig-caption` skill'iyle yaz: `Final/<tarih>_<Baslik>/<Baslik>_aciklama.txt`.
    - **`ig-human` kontrolü:** `metin_kontrol.py <aciklama>`; görünmez karakter/uzun tire varsa `--uygula`. Klişe çıkarsa elle yeniden yaz. Kart başlık ve maddelerini de geçici bir dosyaya yazıp aynı kontrolden geçir. Not: `ig-human`'ın `detect.py` puanı İngilizceye göredir, Türkçede kullanılmaz.
    - **SRT altyazılar:** `srt_yaz.py oner` → blokları gözden geçir → çevirileri ekle → `srt_yaz.py yaz` (0 hata, uyarılar giderilmiş). Ayrıntı: "SRT altyazı ve çeviriler".
    - En sonda `final.py bilgi` ile `BILGI.md` dosyasını güncelle ve kullanıcıya klasörün yolunu ver.
    - Dosya yolunu ver.
