"""reels-stilim kurgu motoru: kesik videonun üstüne altyazı, rozet ve kartları çizer, geçişleri uygular.

Kullanım:
  .venv\\Scripts\\python.exe araclar\\kurgu.py <calisma_klasoru> --kareler 1.0,8.5,...   (örnek kareler -> kare_<t>.png)
  .venv\\Scripts\\python.exe araclar\\kurgu.py <calisma_klasoru> --kontrol                 (yüz/bant ihlali sayımı)
  .venv\\Scripts\\python.exe araclar\\kurgu.py <calisma_klasoru> --tam <cikti.mp4>         (görüntü, sessiz)

Klasörde kesik.mp4, yuz.json ve plan.json olmalı. plan.json (zamanlar kesik videoya göre, saniye):
{
 "altyazi": [{"bas": 0.0, "son": 1.2, "satirlar": ["yeni bir seriye", "başlıyoruz"]}, ...],
 "ogeler": [
   {"tur": "rozetler", "bas": 4.5, "son": 12, "merkez_y": 1290, "boyut": 190,
    "rozetler": [{"metin": "SABIR", "renk": "#0FBBA3", "t": 4.5, "x": 400}, ...]},
   {"tur": "kart", "bas": 15, "son": 26, "y": 1222, "x": 90, "g": 900, "y_yuk": 140,
    "baslik": "İşin sana getirdikleri", "rozet": {"metin": "İŞ", "renk": "#0980AB"} | null,
    "maddeler": [{"metin": "Faturalar", "t": 17.2, "renk": "#0FBBA3"}, ...]}
 ],
 "gecisler": [12.12, 27.25, 38.07]
}
"""
import argparse, json, pathlib, subprocess, sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = pathlib.Path(__file__).resolve().parent.parent
FONT = KOK / "fontlar"
G, Y, FPS = 1080, 1920, 30
ALTYAZI_MERKEZ_X = 525  # sağdaki Instagram ikonlarından uzak durmak için ortanın biraz solu
# Güvenli alanlar: INSTAGRAM_KURALLARI.md
UST_BANT, ALT_BANT, PAY = 250, 1470, 24
SAG_IKON = (900, 900)  # x > 900 ve y > 900
ALTYAZI_ALT = ALT_BANT - 8  # altyazının (gölge dahil) alt kenarı
KART_ZEMIN = (0xEE, 0xED, 0xE9, 255)


# Çizim ölçeği: bütün yerleşim mantıksal 1080x1920 koordinatlarındadır; çizim S katı çözünürlükte yapılır
# (S=2 -> 2160x3840). Kurgu() bunu kesik videonun genişliğinden ayarlar.
S = 1


def olcek_ayarla(genislik):
    global S
    S = genislik / G


def font(ad, boyut):
    return ImageFont.truetype(str(FONT / f"{ad}.ttf"), max(1, round(boyut * S)))


def _p(v):
    return v * S


class Cizim:
    """ImageDraw sarmalayıcısı: mantıksal koordinatları S ile çarpar, ölçüleri (textlength) S'e böler."""

    def __init__(self, im):
        self.d = ImageDraw.Draw(im)

    @staticmethod
    def _xy(xy):
        if isinstance(xy, (list, tuple)) and xy and isinstance(xy[0], (list, tuple)):
            return [(a * S, b * S) for a, b in xy]
        return [v * S for v in xy]

    def text(self, xy, metin, font=None, fill=None, stroke_width=0, stroke_fill=None, **kw):
        self.d.text((xy[0] * S, xy[1] * S), metin, font=font, fill=fill, stroke_width=round(stroke_width * S),
                    stroke_fill=stroke_fill, **kw)

    def textlength(self, metin, font=None):
        return self.d.textlength(metin, font=font) / S

    def polygon(self, xy, **kw):
        self.d.polygon(self._xy(xy), **kw)

    def line(self, xy, fill=None, width=1, **kw):
        self.d.line(self._xy(xy), fill=fill, width=max(1, round(width * S)), **kw)

    def rectangle(self, xy, **kw):
        if "width" in kw:
            kw["width"] = max(1, round(kw["width"] * S))
        self.d.rectangle(self._xy(xy), **kw)

    def rounded_rectangle(self, xy, radius=0, **kw):
        if "width" in kw:
            kw["width"] = max(1, round(kw["width"] * S))
        self.d.rounded_rectangle(self._xy(xy), radius=radius * S, **kw)

    def ellipse(self, xy, **kw):
        self.d.ellipse(self._xy(xy), **kw)


def tuval_yeni(g, y):
    """Mantıksal g x y boyutunda saydam tuval (fiziksel boyut S katı)."""
    return Image.new("RGBA", (round(g * S), round(y * S)), (0, 0, 0, 0))


def kutu_mantiksal(k):
    return tuple(v / S for v in k) if k else k


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------- çizim ----------

def altyazi_katmani(satirlar):
    f = font("RobotoCondensed-BoldItalic", 78)
    sat_y = 78
    tuval = tuval_yeni(G, 200)
    def ciz(d, **kw):
        for i, s in enumerate(satirlar):
            w = d.textlength(s, font=f)
            d.text((ALTYAZI_MERKEZ_X - w / 2, 10 + i * sat_y), s, font=f, **kw)
    parilti = Image.new("RGBA", tuval.size, (0, 0, 0, 0))
    ciz(Cizim(parilti), fill=(23, 102, 219, 255), stroke_width=10, stroke_fill=(23, 102, 219, 255))
    parilti = parilti.filter(ImageFilter.GaussianBlur(6 * S))
    tuval.alpha_composite(parilti)
    ciz(Cizim(tuval), fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(10, 30, 90, 255))
    kutu = kutu_mantiksal(tuval.getbbox())
    if not kutu:
        return tuval, (0, 0), None
    y0 = ALTYAZI_ALT - kutu[3]
    return tuval, (0, y0), (kutu[0], y0 + kutu[1], kutu[2], y0 + kutu[3])


def rozet_ciz(d, cx, cy, boyut, metin, renk):
    r = boyut / 2
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=hex2rgb(renk) + (255,))
    fs = int(boyut * 0.17)
    f = font("Inter-Regular", fs)
    while d.textlength(metin, font=f) > boyut * 0.78 and fs > 12:
        fs -= 1
        f = font("Inter-Regular", fs)
    w = d.textlength(metin, font=f)
    d.text((cx - w / 2, cy - fs * 0.62), metin, font=f, fill=(255, 255, 255, 255))
    return (int(cx - r), int(cy - r), int(cx + r), int(cy + r))


def oge_katmani(o, t, tema="v1"):
    """t anındaki öğe görüntüsü (RGBA, tam kare) ve kapladığı kutu."""
    tuval = tuval_yeni(G, Y)
    d = Cizim(tuval)
    kutular = []
    if tema == "marka":
        if o["tur"] == "rozetler":
            for r in o["rozetler"]:
                if t >= r["t"]:
                    kutular.append(rozet_marka(d, r["x"], o["merkez_y"], o["boyut"], r["metin"]))
        elif o["tur"] == "kart":
            kutular += kart_marka(d, o, t, tuval)
        elif o["tur"] == "alinti":
            kutular += alinti_marka(tuval, d, o, t)
        return tuval, kutular
    if o["tur"] == "rozetler":
        for r in o["rozetler"]:
            if t >= r["t"]:
                kutular.append(rozet_ciz(d, r["x"], o["merkez_y"], o["boyut"], r["metin"], r["renk"]))
    elif o["tur"] == "kart":
        x, y, g, h = o["x"], o["y"], o["g"], o["y_yuk"]
        d.rectangle([x, y, x + g, y + h], fill=KART_ZEMIN)
        kutular.append((x, y, x + g, y + h))
        sol = x + 34
        if o.get("rozet"):
            rb = int(h * 1.18)
            kutular.append(rozet_ciz(d, x, y + h / 2, rb, o["rozet"]["metin"], o["rozet"]["renk"]))
            sol = x + rb / 2 + 26
        fb = font("Inter-SemiBold", 30)
        d.text((sol, y + 18), o["baslik"], font=fb, fill=(90, 90, 85, 255))
        fs = 40
        fm = font("Inter-Bold", fs)
        while sum(d.textlength(m["metin"], font=fm) + 68 for m in o["maddeler"]) > x + g - sol - 10 and fs > 24:
            fs -= 1
            fm = font("Inter-Bold", fs)
        mx = sol
        for m in o["maddeler"]:
            w = d.textlength(m["metin"], font=fm)
            if t >= m["t"]:
                cy = y + h - 44
                d.ellipse([mx, cy - 9, mx + 18, cy + 9], fill=hex2rgb(m.get("renk", "#1A1A1A")) + (255,))
                d.text((mx + 28, cy - fs * 0.65), m["metin"], font=fm, fill=(20, 20, 20, 255))
            mx += 28 + w + 40
    return tuval, kutular


# ---------- marka teması ----------
# Her markanın ayarları markalar/<marka>/tema.json içinde. plan.json -> "tema": "<marka>".

T = {}  # etkin tema (tema_yukle ile dolar)


def tema_yukle(ad):
    yol = KOK / "markalar" / ad / "tema.json"
    t = json.load(open(yol, encoding="utf-8"))
    t["_renk"] = {k: hex2rgb(v) for k, v in t["renkler"].items()}
    r = t["_renk"]
    r.setdefault("vurgu_metin", r["vurgu"])   # vurgu renginde yazılar (eyebrow, vurgulu kelime)
    r.setdefault("cizgi", r["vurgu"])         # çizgi ve çerçeveler
    T.clear()
    T.update(t)
    return t


def aralikli_yaz(d, xy, metin, f, renk, aralik):
    """Harf aralıklı yazı (eyebrow başlıklar için). Genişliği döndürür."""
    x, y = xy
    for ch in metin:
        d.text((x, y), ch, font=f, fill=renk)
        x += d.textlength(ch, font=f) + aralik
    return x - xy[0] - aralik


def aralikli_genislik(d, metin, f, aralik):
    return sum(d.textlength(ch, font=f) for ch in metin) + aralik * (len(metin) - 1)


def tr_buyuk(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def tr_kucuk(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def tr_bas_buyuk(s):
    """Yalnızca ilk harfi Türkçe kurala göre büyütür (idare -> İdare, ılık -> Ilık)."""
    return tr_buyuk(s[:1]) + s[1:] if s else s


def altyazi_marka(satirlar, vurgu=()):
    """Tema fontu; vurgu kelimeleri vurgu renginde. Yumuşak gölge + ince kontur."""
    R, A = T["_renk"], T["altyazi"]
    f = font(A["font"], A["boyut"])
    vurgu = {tr_kucuk(v) for v in vurgu}
    tuval = tuval_yeni(G, 200)
    golge = Image.new("RGBA", tuval.size, (0, 0, 0, 0))
    gd, td = Cizim(golge), Cizim(tuval)
    go = R["golge"] + (A["golge_opaklik"],)
    for i, s in enumerate(satirlar):
        w = td.textlength(s, font=f)
        x, y = ALTYAZI_MERKEZ_X - w / 2, 10 + i * (A["boyut"] + 10)
        gd.text((x, y + 4), s, font=f, fill=go, stroke_width=A["golge_kontur"], stroke_fill=go)
        for k in s.split(" "):
            renk = R["vurgu_metin"] if tr_kucuk(k.strip(".,?!")) in vurgu else R["altyazi"]
            td.text((x, y), k, font=f, fill=renk + (255,), stroke_width=A["kontur"], stroke_fill=R["golge"] + (255,))
            x += td.textlength(k + " ", font=f)
    golge = golge.filter(ImageFilter.GaussianBlur(A["golge_bulaniklik"] * S))
    golge.alpha_composite(tuval)
    # kutu: gözle görülür pikseller (çok silik gölge kenarı sayılmaz)
    kutu = kutu_mantiksal(golge.getchannel("A").point(lambda a: 255 if a > 60 else 0).getbbox())
    if not kutu:
        return golge, (0, 0), None
    y0 = ALTYAZI_ALT - kutu[3]
    return golge, (0, y0), (kutu[0], y0 + kutu[1], kutu[2], y0 + kutu[3])


def elmas(d, cx, cy, r, renk):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=renk)


def isaret_ciz(d, cx, cy, r, renk):
    """Tema işareti: "elmas", "nokta" ya da "yok"."""
    tur = T["kart"].get("isaret", "elmas")
    if tur == "elmas":
        elmas(d, cx, cy, r, renk)
    elif tur == "nokta":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=renk)


def panel(d, x, y, g, h, tuval=None):
    """Tema paneli. panel.degrade: ["#ust", "#alt"] (tuval gerekir), panel.cift_cerceve: iç ince çerçeve."""
    R, P = T["_renk"], T["panel"]
    if P.get("degrade") and tuval is not None:
        ust, alt = (hex2rgb(c) for c in P["degrade"])
        gp, hp = round(g * S), round(h * S)
        katman = Image.new("RGBA", (gp + 1, hp + 1))
        kd = ImageDraw.Draw(katman)
        for i in range(hp + 1):
            a = i / max(hp, 1)
            kd.line([(0, i), (gp, i)], fill=tuple(int(ust[j] * (1 - a) + alt[j] * a) for j in range(3)) + (P["opaklik"],))
        maske = Image.new("L", katman.size, 0)
        ImageDraw.Draw(maske).rounded_rectangle([0, 0, gp, hp], radius=P["kose"] * S, fill=255)
        tuval.paste(katman, (round(x * S), round(y * S)), maske)
    else:
        d.rounded_rectangle([x, y, x + g, y + h], radius=P["kose"], fill=R["panel"] + (P["opaklik"],))
    if P["cerceve"]:
        d.rounded_rectangle([x, y, x + g, y + h], radius=P["kose"], outline=R["cizgi"] + (P["cerceve_opaklik"],),
                            width=P["cerceve"])
    if P.get("cift_cerceve"):
        ic = P.get("ic_bosluk", 8)
        d.rounded_rectangle([x + ic, y + ic, x + g - ic, y + h - ic], radius=max(P["kose"] - ic // 2, 0),
                            outline=R["cizgi"] + (int(P["cerceve_opaklik"] * 0.6),), width=1)


def rozet_marka(d, cx, cy, boyut, metin):
    """Tema rozeti. bicim "hap": marka butonu gibi hap, başta işaret. bicim "elmas": elmas.
    boyut: hap yüksekliği ya da elmas köşegeni."""
    R, Z = T["_renk"], T["rozet"]
    if Z["bicim"] == "elmas":
        r = boyut / 2
        nokta = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        d.polygon(nokta, fill=R["panel"] + (Z["opaklik"],))
        d.line(nokta + [nokta[0]], fill=R["vurgu"] + (255,), width=Z["cerceve"] + 1, joint="curve")
        fs = int(boyut * 0.15)
        f = font(Z["font"], fs)
        while aralikli_genislik(d, metin, f, 2) > boyut * 0.7 and fs > 12:
            fs -= 1
            f = font(Z["font"], fs)
        w = aralikli_genislik(d, metin, f, 2)
        aralikli_yaz(d, (cx - w / 2, cy - fs * 0.62), metin, f, R["kart_metin"] + (255,), 2)
        return (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    h = boyut
    fs = int(h * 0.36)
    f = font(Z["font"], fs)
    tw = aralikli_genislik(d, metin, f, Z["harf_araligi"])
    isaretli = Z.get("isaret", T["kart"].get("isaret", "elmas")) != "yok"
    g = int(tw + h * 0.9 + (22 if isaretli else 0))
    x0, y0 = int(cx - g / 2), int(cy - h / 2)
    kose = h // 2 if Z.get("kose", "hap") == "hap" else int(Z["kose"])
    d.rounded_rectangle([x0, y0, x0 + g, y0 + h], radius=kose, fill=R["panel"] + (Z["opaklik"],))
    d.rounded_rectangle([x0, y0, x0 + g, y0 + h], radius=kose, outline=R["cizgi"] + (Z.get("cerceve_opaklik", 255),),
                        width=Z["cerceve"])
    ex = x0 + h * 0.45
    if isaretli:
        isaret_ciz(d, ex, cy, 8, R["vurgu"] + (255,))
        ex += 22
    renk = R["vurgu_metin"] if Z.get("metin") == "vurgu" else R["kart_metin"]
    aralikli_yaz(d, (ex, cy - fs * Z.get("dikey_oran", 0.68)), metin, f, renk + (255,), Z["harf_araligi"])
    return (x0, y0, x0 + g, y0 + h)


def kart_orta(tuval, d, o, t):
    """Ortalı kart (story düzeni): ortada eyebrow + altında ortalı ince çizgi; maddeler tek satırda ortalı,
    aralarında ayraç. Maddeler söylendikçe belirir ama yerleri baştan sabittir."""
    R, K = T["_renk"], T["kart"]
    x, y, g, h = o["x"], o["y"], o["g"], o["y_yuk"]
    panel(d, x, y, g, h, tuval)
    cx = x + g / 2
    fe = font(K["eyebrow_font"], K["eyebrow_boyut"])
    baslik = tr_buyuk(o["baslik"]) if K.get("eyebrow_buyuk_harf", True) else o["baslik"]
    ew = aralikli_genislik(d, baslik, fe, K["eyebrow_harf_araligi"])
    aralikli_yaz(d, (cx - ew / 2, y + 16), baslik, fe, R["vurgu_metin"] + (235,), K["eyebrow_harf_araligi"])
    c = K.get("cizgi_uzunluk", 0)
    if c:
        d.line([(cx - c / 2, y + 52), (cx + c / 2, y + 52)], fill=R["cizgi"] + (160,), width=2)
    buyuk = o.get("buyuk")
    fs = K["buyuk_boyut"] if buyuk else K["madde_boyut"]
    ad = K["buyuk_font"] if buyuk else K["madde_font"]
    ayrac = "  " + K.get("ayrac", "·") + "  "
    fm = font(ad, fs)
    while d.textlength(ayrac.join(m["metin"] for m in o["maddeler"]), font=fm) > g - 60 and fs > 22:
        fs -= 1
        fm = font(ad, fs)
    renk = R["vurgu_metin"] if K.get("madde_renk") == "vurgu" else R["kart_metin"]
    tam = ayrac.join(m["metin"] for m in o["maddeler"])
    mx, cy = cx - d.textlength(tam, font=fm) / 2, y + h - 40
    for i, m in enumerate(o["maddeler"]):
        if t >= m["t"]:
            if i:
                d.text((mx, cy - fs * 0.62), ayrac, font=fm, fill=R["cizgi"] + (200,))
            d.text((mx + (d.textlength(ayrac, font=fm) if i else 0), cy - fs * 0.62), m["metin"], font=fm,
                   fill=renk + (255,))
        mx += (d.textlength(ayrac, font=fm) if i else 0) + d.textlength(m["metin"], font=fm)
    return [(x, y, x + g, y + h)]


def alinti_marka(tuval, d, o, t):
    """Alıntı kartı: panel, büyük soluk tırnak, ortalı italik satırlar, isteğe bağlı küçük imza."""
    R, A = T["_renk"], T.get("alinti", {})
    imza = o.get("imza") if A.get("imza", True) else None
    x, y, g, h = o["x"], o["y"], o["g"], o["y_yuk"]
    panel(d, x, y, g, h, tuval)
    cx = x + g / 2
    ft = font(A.get("tirnak_font", T["kart"]["madde_font"]), A.get("tirnak_boyut", 150))
    d.text((x + 34, y - A.get("tirnak_boyut", 150) * 0.12), "“", font=ft, fill=R["vurgu_metin"] + (A.get("tirnak_opaklik", 90),))
    fs = A.get("boyut", 48)
    fm = font(A.get("font", T["kart"]["madde_font"]), fs)
    while max(d.textlength(s, font=fm) for s in o["satirlar"]) > g - 120 and fs > 24:
        fs -= 1
        fm = font(A.get("font", T["kart"]["madde_font"]), fs)
    sat = fs * 1.18
    y0 = y + (h - sat * len(o["satirlar"])) / 2 - (20 if imza else 0)
    for i, s in enumerate(o["satirlar"]):
        w = d.textlength(s, font=fm)
        d.text((cx - w / 2, y0 + i * sat), s, font=fm, fill=R["kart_metin"] + (255,))
    if imza:
        fe = font(T["kart"]["eyebrow_font"], max(T["kart"]["eyebrow_boyut"] - 4, 14))
        im = tr_buyuk(imza)
        ew = aralikli_genislik(d, im, fe, 4)
        aralikli_yaz(d, (cx - ew / 2, y + h - 32), im, fe, R["vurgu_metin"] + (200,), 4)
    return [(x, y, x + g, y + h)]


def kart_marka(d, o, t, tuval=None):
    """Tema paneli, vurgu renginde eyebrow ve kısa çizgi, kart metni renginde maddeler."""
    R, K = T["_renk"], T["kart"]
    if K.get("madde_buyuk_bas"):
        o = {**o, "maddeler": [{**m, "metin": tr_bas_buyuk(m["metin"])} for m in o["maddeler"]]}
    if K.get("duzen") == "orta":
        return kart_orta(tuval, d, o, t)
    x, y, g, h = o["x"], o["y"], o["g"], o["y_yuk"]
    panel(d, x, y, g, h, tuval)
    sol = x + 36
    fe = font(K["eyebrow_font"], K["eyebrow_boyut"])
    ebx = sol
    if K.get("isaret", "elmas") != "yok":
        isaret_ciz(d, sol + 8, y + 36, 8, R["vurgu"] + (255,))
        ebx = sol + 30
    baslik = tr_buyuk(o["baslik"]) if K.get("eyebrow_buyuk_harf", True) else o["baslik"]
    aralikli_yaz(d, (ebx, y + 20), baslik, fe, R["vurgu"] + (255,), K["eyebrow_harf_araligi"])
    if K.get("cizgi_uzunluk"):
        d.line([(sol, y + 62), (sol + K["cizgi_uzunluk"], y + 62)], fill=R["vurgu"] + (255,), width=3)
    buyuk = o.get("buyuk")
    fs = K["buyuk_boyut"] if buyuk else K["madde_boyut"]
    ad = K["buyuk_font"] if buyuk else K["madde_font"]
    fm = font(ad, fs)
    isaret = 0 if buyuk or K.get("isaret", "elmas") == "yok" else 30
    while sum(d.textlength(m["metin"], font=fm) + isaret + 38 for m in o["maddeler"]) > g - 70 and fs > 22:
        fs -= 1
        fm = font(ad, fs)
    mx, cy = sol, y + h - 42
    for m in o["maddeler"]:
        w = d.textlength(m["metin"], font=fm)
        if t >= m["t"]:
            if isaret:
                isaret_ciz(d, mx + 9, cy, 9, R["vurgu"] + (255,))
            d.text((mx + isaret, cy - fs * 0.62), m["metin"], font=fm, fill=R["kart_metin"] + (255,))
        mx += isaret + w + 38
    return [(x, y, x + g, y + h)]


def isik(img, guc):
    """Alttan yükselen vurgu renginde ışık (ör. altın ışık), geçişlerde kullanılır."""
    Yp, Gp = img.shape[:2]
    yy, xx = np.mgrid[0:Yp:8, 0:Gp:8]
    m = np.exp(-(((xx - Gp / 2) / (Gp * 0.55)) ** 2 + ((yy - Yp * 0.95) / (Yp * 0.45)) ** 2))
    m = cv2.resize(m.astype(np.float32), (Gp, Yp))[..., None] * guc
    renk = np.array(T["_renk"]["vurgu"], np.float32)[None, None, :]
    return np.clip(img.astype(np.float32) * (1 - 0.25 * m) + renk * m * 0.9, 0, 255).astype(np.uint8)


# ---------- yüz ----------

class Yuz:
    def __init__(self, yol):
        self.o = [o for o in json.load(open(yol))["olcumler"] if o["yuz"]]
        self.t = np.array([o["t"] for o in self.o])

    def kutu(self, t):
        # t'ye en yakın iki ölçümün birleşimi (hareket payı)
        i = np.argsort(np.abs(self.t - t))[:2]
        k = np.array([self.o[j]["yuz"] for j in i])
        return (k[:, 0].min() - PAY, k[:, 1].min() - PAY, k[:, 2].max() + PAY, k[:, 3].max() + PAY)


def kesisir(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def ihlaller(kutu, yuz):
    s = []
    if kesisir(kutu, yuz):
        s.append("yüz")
    if kutu[1] < UST_BANT:
        s.append("üst bant")
    if kutu[3] > ALT_BANT:
        s.append("alt bant")
    if kutu[2] > SAG_IKON[0] and kutu[3] > SAG_IKON[1]:
        s.append("sağ ikonlar")
    return s


# ---------- kare üretimi ----------

class Kurgu:
    def __init__(self, k):
        self.k = pathlib.Path(k)
        self.plan = json.load(open(self.k / "plan.json", encoding="utf-8"))
        self.tema = self.plan.get("tema", "v1")
        if self.tema != "v1":
            tema_yukle(self.tema)
        self.yuz = Yuz(self.k / "yuz.json")
        self._alt = {}
        self.boyut = video_boyutu(self.k / "kesik.mp4")
        olcek_ayarla(self.boyut[0])

    def altyazi(self, t):
        for i, a in enumerate(self.plan["altyazi"]):
            if a["bas"] <= t < a["son"]:
                if i not in self._alt:
                    self._alt[i] = (altyazi_marka(a["satirlar"], a.get("vurgu", ())) if self.tema != "v1"
                                    else altyazi_katmani(a["satirlar"]))
                return self._alt[i]
        return None

    def katmanlar(self, t):
        """(RGBA tuval, konum, kutu listesi) listesi."""
        out = []
        for o in self.plan["ogeler"]:
            if o["bas"] <= t < o["son"]:
                tv, kutular = oge_katmani(o, t, "v1" if self.tema == "v1" else "marka")
                out.append((tv, (0, 0), kutular))
        a = self.altyazi(t)
        if a:
            out.append((a[0], a[1], [a[2]] if a[2] else []))
        return out

    def gecis(self, img, t):
        """Bölüm geçişi: ±2 kare zoom-in ve dikey hareket bulanıklığı."""
        for g in self.plan["gecisler"]:
            dk = (t - g) * FPS
            if -2.5 < dk < 2.5:
                guc = 1 - abs(dk) / 2.5
                s = 1 + 0.35 * guc
                Yp, Gp = img.shape[:2]
                M = cv2.getRotationMatrix2D((Gp / 2, Yp * 0.42), 0, s)
                img = cv2.warpAffine(img, M, (Gp, Yp), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                n = int((10 + 70 * guc) * S)
                ker = np.zeros((n, 1), np.float32)
                ker[:] = 1 / n
                img = cv2.filter2D(img, -1, ker)
                if self.tema != "v1" and T["gecis"].get("isik"):
                    img = isik(img, T["gecis"]["isik_gucu"] * guc)
        return img

    def kare(self, img, t):
        img = self.gecis(img, t)
        pil = Image.fromarray(img).convert("RGBA")
        for tv, konum, _ in self.katmanlar(t):
            pil.alpha_composite(tv, (round(konum[0] * S), round(konum[1] * S)))
        return np.array(pil.convert("RGB"))

    def kontrol(self, sure, adim=0.1):
        say, ornek = 0, []
        t = 0.0
        while t < sure:
            yz = self.yuz.kutu(t)
            katmanlar = self.katmanlar(t)
            for _, _, kutular in katmanlar:
                for kb in kutular:
                    s = ihlaller(kb, yz)
                    if s:
                        say += 1
                        if len(ornek) < 15:
                            ornek.append((round(t, 1), kb, s))
            # farklı öğeler (ör. kart ile altyazı) birbirine binmemeli
            for i in range(len(katmanlar)):
                for j in range(i + 1, len(katmanlar)):
                    for a in katmanlar[i][2]:
                        for b in katmanlar[j][2]:
                            if kesisir(a, b):
                                say += 1
                                if len(ornek) < 15:
                                    ornek.append((round(t, 1), (a, b), ["öğeler üst üste"]))
            t += adim
        return say, ornek


def video_boyutu(video):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip().split(",")
    return int(o[0]), int(o[1])


def kare_oku(video, t):
    gp, yp = video_boyutu(video)
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(yp, gp, 3).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor")
    ap.add_argument("--kareler")
    ap.add_argument("--kontrol", action="store_true")
    ap.add_argument("--tam")
    a = ap.parse_args()
    k = Kurgu(a.klasor)
    video = str(k.k / "kesik.mp4")
    sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                capture_output=True, text=True).stdout)
    if a.kareler:
        for t in map(float, a.kareler.split(",")):
            Image.fromarray(k.kare(kare_oku(video, t), t)).save(k.k / f"kare_{t:05.2f}.png")
            print("kare", t)
    if a.kontrol:
        say, ornek = k.kontrol(sure)
        print(f"IHLAL: {say}")
        for o in ornek:
            print("  ", o)
    if a.tam:
        oku = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               stdout=subprocess.PIPE)
        gp, yp = k.boyut
        # ara dosya: neredeyse kayıpsız (son kalite cikti.py'de belirlenir)
        yaz = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{gp}x{yp}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "10", "-preset", "fast",
                                "-pix_fmt", "yuv420p", a.tam], stdin=subprocess.PIPE)
        i = 0
        while True:
            b = oku.stdout.read(gp * yp * 3)
            if len(b) < gp * yp * 3:
                break
            img = np.frombuffer(b, np.uint8).reshape(yp, gp, 3)
            yaz.stdin.write(k.kare(img, i / FPS).tobytes())
            i += 1
            if i % 300 == 0:
                print(f"{i / FPS:.0f} sn", flush=True)
        yaz.stdin.close()
        yaz.wait()
        print("tamam", a.tam, i, "kare")


if __name__ == "__main__":
    main()
