"""ÖRNEK plan üreticisi. Her yeni video için calisma/<video>/plan_olustur.py olarak kopyala ve içeriğe göre değiştir.

Kullanım: .venv\\Scripts\\python.exe -X utf8 calisma\\<video>\\plan_olustur.py [calisma\\<video>-V1]
(Argüman verilmezse bu dosyanın klasörü kullanılır. Klasörde kesimler.json, metin.json ve kesik.mp4 olmalı.)

Kurallar:
- Zamanları saniyeyle değil kelimeyle yaz: p.kelime("kök") ya da ham zamanla p.kelime_t(12.3).
- Kartın bitişi bölüm geçişine bağlanır: p.gecis_once("ama") ya da p.gecis_t(ham_zaman).
- Bu örnekteki kelimeler ("konu", "birinci"...) yer tutucudur; videonun gerçek kelimeleriyle değiştir.
"""
import pathlib, sys

KOK = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from plan_arac import Plan  # noqa: E402

klasor = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).parent
# Whisper'ın yanlış duyduğu kelimeler: {ham_video_saniyesi: "doğru yazım"} (kullanıcıya sorup onaylat)
duzelt = {}
p = Plan(klasor, tema="ornek", duzelt=duzelt)  # tema = markalar/<marka>/ klasörünün adı
son = p.sure()

KART = {"x": 60, "g": 840, "y": 1203, "y_yuk": 130}  # göğüs hizası; güvenli alan kuralları için SKILL.md
ogeler = [
    # Açılış kartı: büyük başlık + tek madde
    dict(tur="kart", bas=0.0, son=p.gecis_once("ama"), baslik="Serinin adı", buyuk=True,
         maddeler=[{"metin": "Bölümün konusu", "t": p.kelime("konu")}], **KART),
    # Rozetler: ana kavramlar söylendiği anda belirir
    dict(tur="rozetler", bas=p.kelime("birinci"), son=p.gecis_once("şimdi"), merkez_y=1262, boyut=78,
         rozetler=[{"metin": "BİRİNCİ", "t": p.kelime("birinci"), "x": 335},
                   {"metin": "İKİNCİ", "t": p.kelime("ikinci"), "x": 640}]),
    # Madde kartı: maddeler söylendikçe birer birer gelir (büyük harfle başlar)
    dict(tur="kart", bas=p.kelime("şimdi"), son=p.gecis_once("oysa"), baslik="Bölüm başlığı",
         maddeler=[{"metin": "Birinci madde", "t": p.kelime("madde")},
                   {"metin": "İkinci madde", "t": p.kelime("madde", 2)}], **KART),
    # Alıntı kartı: konuşmacının en güçlü cümlesi, en fazla 2 satır, sona kadar kalır
    dict(tur="alinti", bas=p.kelime("oysa"), son=son,
         satirlar=["Videodaki en güçlü", "cümle buraya."], **{**KART, "y": 1175, "y_yuk": 158}),
]
gecisler = [p.gecis_once("ama"), p.gecis_once("şimdi"), p.gecis_once("oysa")]
p.kaydet(ogeler, gecisler, vurgu={"birinci", "ikinci"})
