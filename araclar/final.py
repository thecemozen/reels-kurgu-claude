"""Final klasörü düzeni: her video kendi klasöründe.

  Final/<YYYY-MM-DD>_<video>/
      <video>_reels_4K.mp4        son video
      <video>_aciklama.txt        Instagram açıklaması
      BILGI.md                    teknik bilgiler ve kontrol sonuçları
      kapak/                      seçilen kapaklar (.jpg, .svg, _izgara.jpg) + aday tablosu
      eski/                       önceki sürümler

Kullanım:
  .venv\\Scripts\\python.exe araclar\\final.py klasor <video>          -> klasör yolunu yazdırır (yoksa oluşturur)
  .venv\\Scripts\\python.exe araclar\\final.py duzenle                 -> Final/ kökündeki dağınık dosyaları klasörlere taşır
  .venv\\Scripts\\python.exe araclar\\final.py bilgi <klasor> [--calisma <calisma/video>] [--kaynak <ham video>]

Diğer araçlar (cikti.py, kapak.py) çıktı yolu Final/<tarih>_<video>/ altındaysa klasörleri kendileri oluşturur.
"""
import argparse, datetime, json, pathlib, re, shutil, subprocess, sys

KOK = pathlib.Path(__file__).resolve().parent.parent
FINAL = KOK / "Final"
EKLER = ["_reels_marka_aciklama", "_reels_4K", "_reels_marka", "_reels", "_kapak", "_aciklama"]


TR_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def slug(baslik):
    """Kapak başlığından dosya/klasör adı: Türkçe karakter ve boşluk yok.
    "Eşlik mi, işgal mi?" -> "Eslik-mi-Isgal-mi" (her kelimenin ilk harfi büyük)."""
    s = baslik.replace("|", " ").translate(TR_ASCII)
    kelimeler = re.findall(r"[A-Za-z0-9]+", s)
    return "-".join(k[:1].upper() + k[1:] if i == 0 or len(k) > 2 else k for i, k in enumerate(kelimeler))


def adlandir(klasor, baslik):
    """Klasörü <tarih>_<slug(baslik)> yapar; kökteki ve kapak/ içindeki dosyaların ön ekini değiştirir,
    BILGI.md'deki adları günceller. Hedef klasör varsa (aynı bölümün başka sürümü) kaynak, hedefin
    eski/<eski klasör adı>/ alt klasörüne taşınır."""
    k = pathlib.Path(klasor)
    tarih, eski_ad = k.name.split("_", 1)
    yeni_ad = slug(baslik)
    hedef = k.parent / f"{tarih}_{yeni_ad}"
    if not any(FINAL.glob(f"*_{yeni_ad}")) or hedef == k:
        for alt in [k, k / "kapak"]:
            if not alt.exists():
                continue
            for p in alt.iterdir():
                if p.is_file() and p.name.startswith(eski_ad + "_"):
                    p.rename(p.with_name(yeni_ad + p.name[len(eski_ad):]))
        b = k / "BILGI.md"
        if b.exists():
            metin = b.read_text(encoding="utf-8").replace(eski_ad + "_", yeni_ad + "_")
            metin = re.sub(r"^# .*$", f"# {baslik.replace('|', ' ')}", metin, count=1, flags=re.M)
            if "Ham çekim / eski adı:" not in metin:
                metin = metin.replace("\n\n", f"\n\nHam çekim / eski adı: `{eski_ad}`\n\n", 1)
            b.write_text(metin, encoding="utf-8")
        try:
            k.rename(hedef)
        except PermissionError:
            # Windows: klasörde açık bir dosya varsa (Gezgin, önizleme) klasör adı değişmez; dosyaları tek tek taşı
            for p in sorted(k.rglob("*")):
                if p.is_file():
                    h = hedef / p.relative_to(k)
                    h.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(p), str(h))
            for d in sorted([x for x in k.rglob("*") if x.is_dir()], key=lambda x: -len(x.parts)) + [k]:
                try:
                    d.rmdir()
                except OSError:
                    print("  boş klasör silinemedi (açık olabilir):", d)
        print(f"{k.name}  ->  {hedef.name}")
        return hedef
    mevcut = next(FINAL.glob(f"*_{yeni_ad}"))
    arsiv = mevcut / "eski" / k.name
    arsiv.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(k), str(arsiv))
    print(f"{k.name}  ->  {mevcut.name}/eski/{k.name}  (aynı bölümün önceki sürümü)")
    return mevcut


def video_klasoru(ad, tarih=None):
    """Final/<tarih>_<ad>/ (aynı adla klasör varsa onu kullanır)."""
    FINAL.mkdir(exist_ok=True)
    for k in sorted(FINAL.iterdir()):
        if k.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}_" + re.escape(ad), k.name):
            return k
    tarih = tarih or datetime.date.today().isoformat()
    k = FINAL / f"{tarih}_{ad}"
    (k / "kapak").mkdir(parents=True, exist_ok=True)
    return k


def video_adi(dosya):
    ad = dosya.stem
    for e in EKLER:
        i = ad.find(e)
        if i > 0:
            return ad[:i]
    return None


def duzenle():
    tasinan = []
    dosyalar = [p for p in FINAL.iterdir() if p.is_file()]
    # eski_1080 gibi ara klasörlerdeki dosyalar -> ilgili videonun eski/ klasörü
    for alt in [p for p in FINAL.iterdir() if p.is_dir() and not re.match(r"\d{4}-\d{2}-\d{2}_", p.name)]:
        for p in alt.iterdir():
            if p.is_file() and video_adi(p):
                dosyalar.append(p)
    for p in dosyalar:
        ad = video_adi(p)
        if not ad:
            continue
        tarih = datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()
        k = video_klasoru(ad, tarih)
        if p.parent != FINAL:
            hedef = k / "eski" / p.name
        elif "_kapak" in p.stem:
            hedef = k / "kapak" / p.name
        else:
            hedef = k / p.name
        hedef.parent.mkdir(parents=True, exist_ok=True)
        if hedef.exists():
            print("atlandı (hedefte var):", hedef)
            continue
        shutil.move(str(p), str(hedef))
        tasinan.append((p.relative_to(FINAL), hedef.relative_to(FINAL)))
    for alt in [p for p in FINAL.iterdir() if p.is_dir() and not re.match(r"\d{4}-\d{2}-\d{2}_", p.name)]:
        if not any(alt.iterdir()):
            alt.rmdir()
    for a, b in tasinan:
        print(f"  {a}  ->  {b}")
    return tasinan


def olc(video):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "format=duration,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate",
                                   "-of", "json", str(video)], capture_output=True, text=True).stdout)
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=peak=true:framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    v = next(s for s in o["streams"] if s["codec_type"] == "video")
    return {"sure": float(o["format"]["duration"]), "boyut": f'{v["width"]}x{v["height"]}', "kodek": v["codec_name"],
            "fps": v["r_frame_rate"], "mbit": int(o["format"].get("bit_rate", 0)) / 1e6,
            "lufs": float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]),
            "tepe": float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)[-1])}


def bilgi(klasor, calisma=None, kaynak=None, baslik=None):
    k = pathlib.Path(klasor)
    satir = [f"# {baslik.replace('|', ' ') if baslik else k.name.split('_', 1)[1].replace('-', ' ')}", ""]
    if kaynak:
        satir += [f"Ham çekim / eski adı: `{pathlib.Path(str(kaynak).split(' ')[0]).stem}`", ""]
    satir += [f"Oluşturma: {datetime.datetime.now():%Y-%m-%d %H:%M}", ""]
    videolar = sorted(k.glob("*.mp4"))
    if videolar:
        satir += ["## Video", "", "| Dosya | Boyut | Süre | Ses | Tepe | Bit hızı |", "|---|---|---|---|---|---|"]
        for v in videolar:
            m = olc(v)
            satir.append(f"| {v.name} | {m['boyut']} {m['kodek']} {m['fps']} | {m['sure']:.1f} sn | {m['lufs']:.1f} LUFS | "
                         f"{m['tepe']:.1f} dBFS | {m['mbit']:.1f} Mbit/sn |")
        satir.append("")
    if calisma:
        c = pathlib.Path(calisma)
        satir += ["## Kurgu", ""]
        if kaynak:
            satir.append(f"- **Kaynak:** `{kaynak}`")
        if (c / "plan.json").exists():
            plan = json.load(open(c / "plan.json", encoding="utf-8"))
            satir.append(f"- **Stil:** {plan.get('tema')}")
            satir.append(f"- **Altyazı öbeği:** {len(plan['altyazi'])}, **grafik öğesi:** {len(plan['ogeler'])}, "
                         f"**bölüm geçişi:** {len(plan['gecisler'])}")
        if (c / "kesimler.json").exists():
            p = json.load(open(c / "kesimler.json"))["parcalar"]
            sure = sum(x["son"] - x["bas"] for x in p)
            satir.append(f"- **Kesim:** {len(p)} parça, ortalama {sure / len(p):.2f} sn "
                         f"(zoom kesimi: {sum(1 for x in p if x.get('bitisik'))})")
        satir.append(f"- **Çalışma klasörü:** `{c.relative_to(KOK) if c.is_absolute() else c}`")
        satir.append("")
    kapaklar = sorted((k / "kapak").glob("*_kapak*.jpg")) if (k / "kapak").exists() else []
    kapaklar = [x for x in kapaklar if not x.stem.endswith(("_izgara", "_adaylari"))]
    if kapaklar:
        aday = {}
        for j in (k / "kapak").glob("*_adaylari.json"):
            aday = json.load(open(j))
        satir += ["## Kapaklar", ""]
        for x in kapaklar:
            no = re.findall(r"_kapak_(\d+)$", x.stem)
            ne = f" (aday {no[0]}, {aday.get(no[0])} sn)" if no and aday.get(no[0]) is not None else ""
            svg = " + `.svg`" if x.with_suffix(".svg").exists() else ""
            satir.append(f"- `kapak/{x.name}`{svg}{ne}")
        satir.append("")
    ac = sorted(k.glob("*aciklama*.txt"))
    if ac:
        satir += ["## Açıklama", "", f"`{ac[0].name}`:", "", "```", ac[0].read_text(encoding="utf-8").strip(), "```", ""]
    eski = sorted((k / "eski").glob("*")) if (k / "eski").exists() else []
    if eski:
        satir += ["## Önceki sürümler (`eski/`)", ""] + [f"- {x.name}" for x in eski] + [""]
    (k / "BILGI.md").write_text("\n".join(satir), encoding="utf-8")
    print("yazıldı:", k / "BILGI.md")


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    a1 = alt.add_parser("klasor")
    a1.add_argument("ad")
    alt.add_parser("duzenle")
    a2 = alt.add_parser("adlandir")
    a2.add_argument("klasor")
    a2.add_argument("--baslik", required=True)
    a4 = alt.add_parser("slug")
    a4.add_argument("baslik")
    a3 = alt.add_parser("bilgi")
    a3.add_argument("klasor")
    a3.add_argument("--calisma")
    a3.add_argument("--kaynak")
    a3.add_argument("--baslik", help="kapak başlığı (Türkçe karakterlerle)")
    a = ap.parse_args()
    if a.komut == "klasor":
        print(video_klasoru(a.ad))
    elif a.komut == "duzenle":
        duzenle()
    elif a.komut == "adlandir":
        adlandir(a.klasor, a.baslik)
    elif a.komut == "slug":
        print(slug(a.baslik))
    else:
        bilgi(a.klasor, a.calisma, a.kaynak, a.baslik)


if __name__ == "__main__":
    main()
