"""Reels kapağı: 4K JPG + düzenlenebilir SVG + profil ızgarası önizlemesi. Kapak karesini KULLANICI seçer.

1) Aday kareleri göster (kullanıcı numara seçer):
  .venv\\Scripts\\python.exe araclar\\kapak.py --adaylar 12 --video <kesik.mp4> --cikti Final\\<ad>_kapak.jpg
     -> Final\\<ad>_kapak_adaylari.jpg (numaralı tablo) ve calisma için _kapak_adaylari.json (numara -> saniye)

2) Seçilen kareyle kapak üret:
  .venv\\Scripts\\python.exe araclar\\kapak.py --tema <marka> --video <kesik.mp4> --t 12.4 (ya da --aday 5) \\
      --ust "Kavramlar ve Karmaşalar · 1" --baslik "Sabır mı,|tahammül mü?" --vurgu 2 --cikti Final\\<ad>_kapak.jpg
     -> <ad>_kapak.jpg (2160x3840), <ad>_kapak.svg (düzenlenebilir), <ad>_kapak_izgara.jpg (3:4 önizleme)

--baslik satırları | ile ayrılır; --vurgu: vurgu renginde yazılacak satır numaraları (1'den başlar, virgülle).
Izgara kuralı (INSTAGRAM_KURALLARI.md): üstten ve alttan 240 px profilde görünmez; bütün yazılar y 300–1600 içinde.
SVG: arka plan karesi ve logo gömülü görsel; geçiş, üst başlık ve başlık satırları ayrı düzenlenebilir öğeler.
Yazıların düzgün görünmesi için SVG'yi açan bilgisayarda markanın fontları kurulu olmalı (fontlar/ klasörü).
"""
import argparse, base64, io, json, pathlib, subprocess, sys
from xml.sax.saxutils import escape

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kurgu as K  # noqa: E402

G, Y = 1080, 1920  # mantıksal yerleşim
IZGARA_UST, IZGARA_ALT = 240, 1680
CIKTI_G, CIKTI_Y = 2160, 3840  # kapak her zaman 4K dikey

# SVG için font dosyası -> (aile adı, ağırlık, stil)
SVG_FONT = {
    "Cinzel-Regular": ("Cinzel", 400, "normal"), "Cinzel-SemiBold": ("Cinzel", 600, "normal"),
    "Cinzel-Bold": ("Cinzel", 700, "normal"),
    "CormorantGaramond-Medium": ("Cormorant Garamond", 500, "normal"),
    "CormorantGaramond-SemiBold": ("Cormorant Garamond", 600, "normal"),
    "CormorantGaramond-Bold": ("Cormorant Garamond", 700, "normal"),
    "CormorantGaramond-MediumItalic": ("Cormorant Garamond", 500, "italic"),
}


def svg_font(ad):
    if ad in SVG_FONT:
        return SVG_FONT[ad]
    aile, _, agirlik = ad.partition("-")
    w = {"Light": 300, "Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800,
         "Black": 900}.get(agirlik.replace("Italic", ""), 400)
    return aile, w, "italic" if "Italic" in agirlik else "normal"


def kare_al(video, t):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                        f"scale={CIKTI_G}:{CIKTI_Y}:force_original_aspect_ratio=increase:flags=lanczos,"
                        f"crop={CIKTI_G}:{CIKTI_Y}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.fromarray(np.frombuffer(b, np.uint8).reshape(CIKTI_Y, CIKTI_G, 3)).convert("RGBA")


def b64(im, bicim):
    buf = io.BytesIO()
    if bicim == "JPEG":
        im.convert("RGB").save(buf, "JPEG", quality=93)
    else:
        im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ---------- aday kareler ----------

def adaylar(video, n, cikti):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(K.KOK / "modeller" / "blaze_face_short_range.tflite"))))
    gw, gy = 270, 480
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=4,scale={gw}:{gy}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    puanlar, i = [], 0
    while True:
        b = p.stdout.read(gw * gy * 3)
        if len(b) < gw * gy * 3:
            break
        img = np.frombuffer(b, np.uint8).reshape(gy, gw, 3)
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)))
        if r.detections:
            d = max(r.detections, key=lambda d: d.categories[0].score)
            bb = d.bounding_box
            yuz = img[max(bb.origin_y, 0):bb.origin_y + bb.height, max(bb.origin_x, 0):bb.origin_x + bb.width]
            netlik = cv2.Laplacian(cv2.cvtColor(yuz, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var() if yuz.size else 0
            # güven * netlik; yüz karenin üst yarısında ve ortaya yakınsa artı
            merkez = 1 - abs((bb.origin_x + bb.width / 2) / gw - 0.5)
            puanlar.append((d.categories[0].score * np.log1p(netlik) * merkez, i / 4))
        i += 1
    secilen = []
    for puan, t in sorted(puanlar, reverse=True):
        if all(abs(t - s) >= 2.0 for s in secilen):
            secilen.append(t)
        if len(secilen) >= n:
            break
    secilen.sort()
    cikti = pathlib.Path(cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    harita = {str(no): round(t, 2) for no, t in enumerate(secilen, 1)}
    json.dump(harita, open(cikti.with_name(cikti.stem + "_adaylari.json"), "w"), indent=1)

    w, h, sut = 300, 533, 4
    satir = (len(secilen) + sut - 1) // sut
    tablo = Image.new("RGB", (sut * (w + 10) + 10, satir * (h + 60) + 10), (16, 19, 46))
    d = ImageDraw.Draw(tablo)
    f = ImageFont.truetype(str(K.FONT / "Cinzel-SemiBold.ttf"), 30)
    for no, t in enumerate(secilen, 1):
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                            f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        im = Image.fromarray(np.frombuffer(b, np.uint8).reshape(h, w, 3))
        x, y = 10 + (no - 1) % sut * (w + 10), 10 + (no - 1) // sut * (h + 60)
        tablo.paste(im, (x, y))
        d.text((x + 6, y + h + 10), f"{no}   ·   {t:.1f} sn", font=f, fill=(234, 193, 99))
    yol = cikti.with_name(cikti.stem + "_adaylari.jpg")
    tablo.save(yol, quality=90)
    print("aday tablosu:", yol)
    for no, t in harita.items():
        print(f"  {no}: {t} sn")


# ---------- kapak ----------

def kapak(a):
    T = K.tema_yukle(a.tema)
    R, KR = T["_renk"], T["kart"]
    K.olcek_ayarla(CIKTI_G)
    S = K.S
    cikti = pathlib.Path(a.cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    t = a.t
    if a.aday is not None:
        listeler = sorted(cikti.parent.glob("*_adaylari.json"))
        if not listeler:
            sys.exit(f"{cikti.parent} içinde aday listesi yok; önce --adaylar çalıştır.")
        t = json.load(open(listeler[-1]))[str(a.aday)]
    if t is None:
        sys.exit("Kapak karesini kullanıcı seçer: önce --adaylar ile tabloyu göster, sonra --aday N ya da --t SANİYE ver.")
    arka = kare_al(a.video, t)
    img = arka.copy()

    # alttan yükselen panel rengi (yazının okunması için)
    ust_renk = K.hex2rgb(T["panel"].get("degrade", [T["renkler"]["panel"]])[0])
    GECIS_BAS, GECIS_UZUN, GECIS_MAX = 0.40, 0.28, 240
    katman = Image.new("RGBA", (CIKTI_G, CIKTI_Y))
    kd = ImageDraw.Draw(katman)
    bas = int(CIKTI_Y * GECIS_BAS)
    for yy in range(bas, CIKTI_Y):
        oran = min((yy - bas) / (CIKTI_Y * GECIS_UZUN), 1.0)
        kd.line([(0, yy), (CIKTI_G, yy)], fill=ust_renk + (int(GECIS_MAX * oran ** 1.2),))
    img.alpha_composite(katman)
    d = K.Cizim(img)

    satirlar = a.baslik.split("|")
    vurgu = {int(v) for v in a.vurgu.split(",") if v.strip()}
    fs = 108
    fb = K.font(KR["buyuk_font"], fs)
    while max(d.textlength(s, font=fb) for s in satirlar) > 900 and fs > 60:
        fs -= 2
        fb = K.font(KR["buyuk_font"], fs)
    sat = int(fs * 1.08)

    logo_yol = (T.get("dosyalar") or {}).get("logo_koyu_zemin")
    logo = None
    if logo_yol and (K.KOK / logo_yol).exists():
        logo = Image.open(K.KOK / logo_yol).convert("RGBA")
        logo = logo.resize((round(240 * S), round(240 * S * logo.height / logo.width)), Image.LANCZOS)

    alt_sinir = 1600 - (logo.height / S + 40 if logo else 0)
    y_baslik = alt_sinir - sat * len(satirlar)
    svg_yazi = []  # (x_orta, baseline_y, metin, font_adi, boyut, renk, opaklik, harf_araligi)
    if a.ust:
        fe_ad, fe_boy, fe_ara = KR["eyebrow_font"], 30, 6
        fe = K.font(fe_ad, fe_boy)
        ust = K.tr_buyuk(a.ust)
        ew = K.aralikli_genislik(d, ust, fe, fe_ara)
        ye = y_baslik - 78
        K.aralikli_yaz(d, ((G - ew) / 2, ye), ust, fe, R["vurgu_metin"] + (240,), fe_ara)
        svg_yazi.append((G / 2, ye + fe.getmetrics()[0] / S, ust, fe_ad, fe_boy, R["vurgu_metin"], 240 / 255, fe_ara))
        c = KR.get("cizgi_uzunluk", 0)
        if c:
            d.line([(G / 2 - c / 2, ye + 46), (G / 2 + c / 2, ye + 46)], fill=R["cizgi"] + (170,), width=2)
    for i, s in enumerate(satirlar, 1):
        w = d.textlength(s, font=fb)
        renk = R["vurgu_metin"] if i in vurgu else R["kart_metin"]
        yy = y_baslik + (i - 1) * sat
        d.text(((G - w) / 2, yy), s, font=fb, fill=renk + (255,))
        svg_yazi.append((G / 2, yy + fb.getmetrics()[0] / S, s, KR["buyuk_font"], fs, renk, 1.0, 0))
    logo_xy = None
    if logo:
        logo_xy = ((CIKTI_G - logo.width) // 2, round((alt_sinir + 30) * S))
        img.alpha_composite(logo, logo_xy)

    # JPG + ızgara önizlemesi
    img.convert("RGB").save(cikti, quality=95)
    izgara = img.crop((0, round(IZGARA_UST * S), CIKTI_G, round(IZGARA_ALT * S))).convert("RGB")
    izgara.save(cikti.with_name(cikti.stem + "_izgara.jpg"), quality=90)

    # Düzenlenebilir SVG (mantıksal 1080x1920 koordinat, 2160x3840 boyut)
    hx = lambda c: "#%02X%02X%02X" % tuple(c)  # noqa: E731
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
         f'width="{CIKTI_G}" height="{CIKTI_Y}" viewBox="0 0 {G} {Y}">',
         '<defs><linearGradient id="gecis" x1="0" y1="0" x2="0" y2="1">']
    for adim in range(0, 11):  # JPG'deki geçişin aynısı (11 duraklı yaklaşım)
        oran = adim / 10
        konum = GECIS_BAS + GECIS_UZUN * oran
        g.append(f'<stop offset="{konum:.3f}" stop-color="{hx(ust_renk)}" stop-opacity="{GECIS_MAX / 255 * oran ** 1.2:.3f}"/>')
    g.append('</linearGradient>')
    # Kullanılan fontları göm: tarayıcı/önizleme doğru gösterir; Illustrator vb. bilgisayarda kurulu fontu kullanır
    stil = []
    for ad in sorted({s[3] for s in svg_yazi}):
        aile, agirlik, st = svg_font(ad)
        veri = base64.b64encode((K.FONT / f"{ad}.ttf").read_bytes()).decode()
        stil.append(f'@font-face{{font-family:"{aile}";font-weight:{agirlik};font-style:{st};'
                    f'src:url(data:font/ttf;base64,{veri}) format("truetype");}}')
    g.append(f'<style>{"".join(stil)}</style></defs>')
    g.append(f'<g id="arka_plan"><image width="{G}" height="{Y}" xlink:href="data:image/jpeg;base64,{b64(arka, "JPEG")}"/></g>')
    g.append(f'<rect id="gecis_katmani" width="{G}" height="{Y}" fill="url(#gecis)"/>')
    g.append('<g id="yazilar">')
    for n, (x, yb, metin, ad, boy, renk, opak, ara) in enumerate(svg_yazi):
        aile, agirlik, stil = svg_font(ad)
        kimlik = "ust_baslik" if (a.ust and n == 0) else f"baslik_{n if a.ust else n + 1}"
        g.append(f'<text id="{kimlik}" x="{x:.1f}" y="{yb:.1f}" text-anchor="middle" font-family="{aile}, serif" '
                 f'font-weight="{agirlik}" font-style="{stil}" font-size="{boy}" letter-spacing="{ara}" '
                 f'fill="{hx(renk)}" fill-opacity="{opak:.2f}">{escape(metin)}</text>')
    g.append('</g>')
    if logo:
        g.append(f'<g id="logo"><image x="{logo_xy[0] / S:.1f}" y="{logo_xy[1] / S:.1f}" width="{logo.width / S:.1f}" '
                 f'height="{logo.height / S:.1f}" xlink:href="data:image/png;base64,{b64(logo, "PNG")}"/></g>')
    g.append('</svg>')
    svg_yol = cikti.with_suffix(".svg")
    svg_yol.write_text("\n".join(x for x in g if x), encoding="utf-8")
    print(f"kapak ({t} sn): {cikti}\n  düzenlenebilir: {svg_yol}\n  ızgara önizleme: {cikti.with_name(cikti.stem + '_izgara.jpg')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--adaylar", type=int, help="aday kare sayısı: yalnızca numaralı tabloyu üretir")
    ap.add_argument("--tema")
    ap.add_argument("--t", type=float)
    ap.add_argument("--aday", type=int, help="aday tablosundaki numara")
    ap.add_argument("--ust", default="")
    ap.add_argument("--baslik")
    ap.add_argument("--vurgu", default="")
    a = ap.parse_args()
    if a.adaylar:
        adaylar(a.video, a.adaylar, a.cikti)
    else:
        if not (a.tema and a.baslik):
            sys.exit("--tema ve --baslik gerekli")
        kapak(a)


if __name__ == "__main__":
    main()
