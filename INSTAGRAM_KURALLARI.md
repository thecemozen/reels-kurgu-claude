# Instagram teknik kuralları (her marka için)

Son araştırma: 20 Ekim 2026. **Meta resmi piksel değerleri yayınlamıyor**; aşağıdakiler üçüncü taraf kaynakların ortak noktasıdır ve güvenli tarafta seçilmiştir. Değerler değişebilir; şüphede telefonda önizle.

## Reels videosu
- **Boyut:** 9:16. Instagram en az 1080x1920 ister. **Bizim çıktımız her zaman 2160x3840 (4K)**, 30 fps, H.264 + AAC, MP4. Instagram yüklemeyi kendi sıkıştırır; yüksek kaynak daha temiz sonuç verir. Güvenli alan değerleri aşağıda 1080x1920 ölçeğinde verilmiştir; 4K'da hepsi 2 kat.
- **Süre:** Uygulamada genellikle 3 dakikaya kadar (hesaba göre değişebilir). Bizim formatımız 30–70 sn.
- **Ses:** −14 LUFS civarı. Telifli müzik ve başka uygulamaların filigranı yok.
- **Altyazı:** Şart. İzleyicilerin büyük kısmı sessiz izliyor.
- **Kanca:** İlk 2–3 saniyede yüz, kanca cümlesi ve altyazı birlikte.

## Güvenli alanlar (1080x1920) — `kurgu.py` bunları kontrol eder
| Bölge | Kaynakların aralığı | **Bizim kuralımız** |
|---|---|---|
| Üst (kullanıcı adı, ses bandı) | 108–270 px | **y < 250 boş** |
| Alt (açıklama, ses adı, butonlar) | 250–670 px | **y > 1470 boş** (alttan 450 px) |
| Sağ ikon sütunu | 120–230 px | **x > 900 ve y > 900 boş** |
| Kenarlar | ~60 px | Önemli metin x 60–900 arasında |

Not: Reklam (sponsorlu) Reels için alt alan daha büyük olur (Meta'nın reklam yönergesinde yaklaşık %35). Reklam videosu çıkarılacaksa alt sınırı 1250'ye çek.

## Kapak ve profil ızgarası
- **Kapak:** Ayrı bir görsel olarak yükle (bizde 2160x3840); otomatik seçilen kareye güvenme.
- **Izgara 3:4:** Profilde kapak 1080x1440 olarak ortadan kırpılır (Ocak 2025'ten beri). **Üstten ve alttan 240 px görünmez.** Kapak başlığı y 300–1600 arasında olmalı.
- `araclar/kapak.py` bu kurala göre kapak üretir: 2160x3840 JPG, düzenlenebilir SVG ve ızgara önizlemesi. Kapak karesini kullanıcı aday tablosundan seçer.

## Story
- **Boyut:** 1080x1920.
- **Güvenli alan:** Üstten ~250 px ve alttan ~340 px boş (yanıt çubuğu, stickerlar).
- **Etkileşim:** Etkileşim öğeleri (anket, soru, emoji kaydırıcı) Instagram'ın kendi stickerlarıyla eklenir. Tasarımdaki "seçenek hapları" görsel yönlendirmedir.

## Açıklama ve etiketler
- **Uzunluk:** En fazla 2.200 karakter. "… daha fazla" kesiminden önce ilk ~125 karakter görünür.
- **Etiket:** **En fazla 5** (18 Aralık 2025'ten beri sınır). Etiketler erişim kaldıracı değil, konu etiketidir.
- **Arama:** Instagram araması açıklama metnini okur. Aranacak ifade cümle içinde geçmeli.
- **Link:** Açıklamada link tıklanmaz. Linki biyografiye ya da DM'e koy.

## Kaynaklar
- [Hopper HQ: Instagram Reel Size 2026](https://www.hopperhq.com/blog/instagram-reel-size/)
- [Argil: Instagram Reel Size 2026](https://argil.ai/blog/instagram-reel-size-e350f)
- [Frameo: Reel Size Guide 2026](https://frameo.ai/blog/reel-size/)
- [Firstpier: Instagram Ad Safe Zones](https://www.firstpier.com/resources/instagram-ad-safe-zones)
- [Trymypost: Social Media Safe Zones 2026](https://www.trymypost.com/blog/social-media-safe-zones-templates-2026)
- [Inro: Instagram Story Size 2026](https://www.inro.social/blog/instagram-story-size)
- [Moonb: Instagram Story Specs 2026](https://www.moonb.io/blog/instagram-story-specs)
- [Inmagic: Instagram Post Size Guide 2026](https://inmagic.ai/instagram-post-size/)
- [Postsyncer: Reels size and safe areas](https://postsyncer.com/tips/instagram-reels-size-and-safe-areas)
