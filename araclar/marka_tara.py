"""Bir markanın tasarım dosyalarını tarar: renk kodları, kullanılan fontlar, dosya envanteri ve görsel tablolar.

Kullanım: .venv\\Scripts\\python.exe -I araclar\\marka_tara.py <cikti_klasoru> <kaynak1> [kaynak2 ...]
Kaynak: klasör ya da dosya. Çıktı: <cikti_klasoru>/tarama.md ve tablo_*.jpg

Dosyalar yalnızca okunur, hiçbir şey çalıştırılmaz. Renkler SVG/HTML/CSS/TXT/MD içindeki #RRGGBB
kodlarından, fontlar .ai/.pdf/.svg/.html içindeki font adlarından çıkarılır.
"""
import collections, pathlib, re, sys

from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).resolve().parent.parent
GORSEL = {".jpg", ".jpeg", ".png", ".webp"}
METIN = {".svg", ".html", ".htm", ".css", ".txt", ".md", ".json"}
FONTLU = {".ai", ".pdf", ".svg", ".html", ".htm", ".css", ".eps"}
ATLA = {"node_modules", ".git", ".venv", "__pycache__"}


def dosyalar(kaynaklar):
    for k in map(pathlib.Path, kaynaklar):
        if k.is_file():
            yield k
        elif k.is_dir():
            for p in k.rglob("*"):
                if p.is_file() and not (ATLA & set(p.parts)):
                    yield p


def fontlari_bul(p):
    """Font adlarını bulur. Büyük .ai/.pdf dosyalarında baştan ve sondan 30 MB okur."""
    boyut = p.stat().st_size
    with open(p, "rb") as f:
        if boyut > 60_000_000:
            veri = f.read(30_000_000)
            f.seek(boyut - 30_000_000)
            veri += f.read()
        else:
            veri = f.read()
    adlar = re.findall(rb"/BaseFont\s*/([A-Za-z0-9+_-]+)", veri)
    adlar += re.findall(rb"stFnt:fontName[=>\"]+([^<\"]+)", veri)
    adlar += re.findall(rb"font-family\s*[:=]\s*[\"']?([^;\"'<>]+)", veri)
    out = []
    for a in adlar:
        a = a.decode("latin-1").strip()
        a = re.sub(r"^[A-Z]{6}\+", "", a)  # PDF alt küme öneki
        if a:
            out.append(a)
    return out


def tablo(gorseller, ad, cikti, cols=8, w=240):
    ims = []
    for g in gorseller:
        try:
            im = Image.open(g).convert("RGB")
            im.thumbnail((w, w * 2))
            ims.append((g.name, im))
        except Exception:
            pass
    if not ims:
        return None
    rowh = max(i.height for _, i in ims) + 22
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * (w + 6), rows * (rowh + 6)), "white")
    d = ImageDraw.Draw(S)
    f = ImageFont.truetype(str(KOK / "fontlar" / "Inter-Regular.ttf"), 13)
    for i, (n, im) in enumerate(ims):
        x, y = (i % cols) * (w + 6), (i // cols) * (rowh + 6)
        S.paste(im, (x, y))
        d.text((x + 2, y + rowh - 20), n[:34], font=f, fill=(60, 60, 60))
    yol = cikti / f"{ad}.jpg"
    S.save(yol, quality=86)
    return yol


def main():
    cikti = pathlib.Path(sys.argv[1])
    cikti.mkdir(parents=True, exist_ok=True)
    tum = list(dosyalar(sys.argv[2:]))

    uzanti = collections.Counter(p.suffix.lower() for p in tum)
    renk, font_say = collections.Counter(), collections.Counter()
    for p in tum:
        s = p.suffix.lower()
        if s in METIN and p.stat().st_size < 20_000_000:
            renk.update(h.upper() for h in re.findall(r"#[0-9a-fA-F]{6}\b", p.read_text("utf-8", "ignore")))
        if s in FONTLU:
            try:
                font_say.update(fontlari_bul(p))
            except OSError:
                pass

    gorseller = sorted([p for p in tum if p.suffix.lower() in GORSEL], key=lambda p: (str(p.parent), p.name))
    tablolar = [tablo(gorseller[i:i + 32], f"tablo_{i // 32 + 1}", cikti) for i in range(0, min(len(gorseller), 160), 32)]

    r = ["# Marka taraması", "", f"Kaynaklar: {', '.join(sys.argv[2:])}", f"Toplam dosya: {len(tum)}", "",
         "## Dosya türleri", ""]
    r += [f"- `{u or '(uzantısız)'}`: {n}" for u, n in uzanti.most_common(15)]
    r += ["", "## Renk kodları (SVG/HTML/CSS/metin içinden, sıklık)", ""]
    r += [f"- {h}: {n}" for h, n in renk.most_common(20)] or ["- bulunamadı"]
    r += ["", "## Fontlar (.ai/.pdf/.svg/.html içinden, sıklık)", ""]
    r += [f"- {a}: {n}" for a, n in font_say.most_common(25)] or ["- bulunamadı"]
    r += ["", "## Metin belgeleri (marka notu olabilir, oku)", ""]
    r += [f"- {p}" for p in tum if p.suffix.lower() in {".txt", ".md", ".docx", ".pdf"}][:40]
    r += ["", "## Logo adayları", ""]
    r += [f"- {p}" for p in tum if re.search(r"logo", p.name, re.I)][:20] or ["- bulunamadı (adında 'logo' geçen dosya yok)"]
    r += ["", "## Görsel tabloları", ""]
    r += [f"- {t}" for t in tablolar if t] + [f"- (ilk 160 görsel; toplam {len(gorseller)})"]
    (cikti / "tarama.md").write_text("\n".join(r), encoding="utf-8")
    print("\n".join(r))


if __name__ == "__main__":
    main()
