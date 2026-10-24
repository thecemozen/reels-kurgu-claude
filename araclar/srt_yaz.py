"""SRT altyazı dosyaları: Türkçe + çeviriler. Her teslimde Final/<klasor>/altyazi/ içine yazılır.

İki adım:
  1) Öneri: son videodaki kelimelerden cümle düzeyinde Türkçe bloklar kurar -> <calisma>/altyazi_bloklar.json
     .venv\\Scripts\\python.exe -X utf8 araclar\\srt_yaz.py oner calisma\\<video>
  2) Bloklara çevirileri ekle (her bloğa "en", "es", ... anahtarları; satır kırmak için \\n), sonra yaz:
     .venv\\Scripts\\python.exe -X utf8 araclar\\srt_yaz.py yaz calisma\\<video> --final Final\\<tarih>_<Baslik> --ad <Baslik>
     -> <Baslik>.tr_TR.srt, <Baslik>.en_US.srt ... (dosya adında Meta dil kodu; Facebook/Business Suite dili tanır)

Neden cümle düzeyi: videoya işlenen 2-4 kelimelik öbekler çevrilemez (söz dizimi dilden dile değişir).
Blok kuralları: en fazla 2 satır, satır başına ~42 karakter, blok en fazla ~7 sn; uzun cümle önce virgülden bölünür.
Zamanlar plan_arac.Plan'dan gelir (kanca kaydırması dahil, kesimde atılan kelimeler hariç); kapanış kartında altyazı yok.
Whisper düzeltmeleri <calisma>/plan_olustur.py içindeki duzelt sözlüğünden okunur.
"""
import argparse, ast, json, pathlib, re, sys

KOK = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from plan_arac import Plan, tr_kucuk  # noqa: E402

META = {"tr": "tr_TR", "en": "en_US", "es": "es_LA", "pt-BR": "pt_BR", "hi": "hi_IN", "id": "id_ID",
        "ar": "ar_AR", "fr": "fr_FR", "de": "de_DE", "ru": "ru_RU", "it": "it_IT", "ja": "ja_JP", "ko": "ko_KR",
        "zh": "zh_CN", "az": "az_AZ", "fa": "fa_IR", "ur": "ur_PK", "bn": "bn_IN", "vi": "vi_VN", "th": "th_TH"}
SATIR, BLOK_SN, BLOK_KAR = 42, 7.0, 84


def plan_ac(klasor, plan_betigi=None):
    """plan_olustur.py'deki tema ve duzelt sözlüğüyle Plan kurar.
    Kanca sürümlerinde (calisma/<video>-V1) betik ortak klasördedir (calisma/<video>/plan_olustur.py)."""
    k = pathlib.Path(klasor)
    tema, duzelt = json.load(open(k / "plan.json", encoding="utf-8"))["tema"], {}
    po = pathlib.Path(plan_betigi) if plan_betigi else k / "plan_olustur.py"
    if not po.exists():
        po = k.parent / re.sub(r"-V\d+$", "", k.name) / "plan_olustur.py"
    if po.exists():
        print("düzeltmeler:", po)
        m = re.search(r"^duzelt\s*=\s*(\{.*?^\})", po.read_text(encoding="utf-8"), re.S | re.M) or \
            re.search(r"duzelt\s*=\s*(\{[^}]*\})", po.read_text(encoding="utf-8"))
        if m:
            duzelt = ast.literal_eval(m.group(1))
    return Plan(k, tema=tema, duzelt=duzelt)


def iki_satir(metin):
    """Metni dengeli en fazla 2 satıra böler (sığmıyorsa yine de 2 satır; kontrol uyarır)."""
    if len(metin) <= SATIR:
        return metin
    kel = metin.split()
    en_iyi = min(range(1, len(kel)), key=lambda i: max(len(" ".join(kel[:i])), len(" ".join(kel[i:]))))
    return " ".join(kel[:en_iyi]) + "\n" + " ".join(kel[en_iyi:])


def bol(kel):
    """Bir cümlenin kelimelerini [(bas, son, kelime)] bloklara böler (uzunsa önce virgülden, yoksa ortadan)."""
    metin = " ".join(w[2] for w in kel)
    if (len(metin) <= BLOK_KAR and kel[-1][1] - kel[0][0] <= BLOK_SN) or len(kel) < 4:
        return [kel]
    orta = len(metin) / 2
    adaylar = []
    for i in range(2, len(kel) - 1):
        sol = len(" ".join(w[2] for w in kel[:i]))
        ceza = abs(sol - orta) - (25 if kel[i - 1][2][-1] in ",;:" else 0)
        adaylar.append((ceza, i))
    i = min(adaylar)[1]
    return bol(kel[:i]) + bol(kel[i:])


def oner(a):
    p = plan_ac(a.klasor, a.plan)
    kel = p.son_kelimeler()
    cumleler, cur = [], []
    for w in kel:
        cur.append(w)
        if w[2][-1] in ".?!":
            cumleler.append(cur)
            cur = []
    if cur:
        cumleler.append(cur)
    bloklar = []
    for c in cumleler:
        for b in bol(c):
            metin = " ".join(w[2] for w in b)
            if not bloklar or bloklar[-1]["tr"].rstrip()[-1] in ".?!":
                metin = metin[0].upper() + metin[1:] if not metin.startswith("i") else "İ" + metin[1:]
            bloklar.append({"bas": round(b[0][0], 3), "tr": iki_satir(metin)})
    son = round(min(kel[-1][1] + 0.3, p.sure()), 3)
    yol = pathlib.Path(a.klasor) / "altyazi_bloklar.json"
    if yol.exists() and not a.uzerine:
        sys.exit(f"{yol} zaten var (çeviriler kaybolmasın). Yeniden kurmak için --uzerine.")
    json.dump({"son": son, "bloklar": bloklar}, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for b in bloklar:
        print(f"{b['bas']:7.2f}  {b['tr'].replace(chr(10), ' / ')}")
    print(f"\n{len(bloklar)} blok, son {son} sn -> {yol}")
    print("Türkçeyi gözden geçir (noktalama, büyük harf, Whisper hataları), sonra çevirileri ekleyip 'yaz' çalıştır.")


def zaman(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def yaz(a):
    veri = json.load(open(pathlib.Path(a.klasor) / "altyazi_bloklar.json", encoding="utf-8"))
    bloklar, son = veri["bloklar"], veri["son"]
    diller = [d for d in bloklar[0] if d != "bas"]
    hatalar, uyarilar = [], []
    for i, b in enumerate(bloklar):
        if i and b["bas"] <= bloklar[i - 1]["bas"]:
            hatalar.append(f"blok {i + 1}: başlangıç bir öncekinden önce")
        sure = (bloklar[i + 1]["bas"] if i + 1 < len(bloklar) else son) - b["bas"]
        for d in diller:
            m = b.get(d, "").strip()
            if not m:
                hatalar.append(f"blok {i + 1}: '{d}' çevirisi yok")
                continue
            satirlar = m.split("\n")
            if len(satirlar) > 2:
                hatalar.append(f"blok {i + 1} [{d}]: {len(satirlar)} satır (en fazla 2)")
            uzun = [s for s in satirlar if len(s) > SATIR + 3]
            if uzun:
                uyarilar.append(f"blok {i + 1} [{d}]: uzun satır ({len(uzun[0])} kar.)")
            if sure > 0 and len(m) / sure > 25:
                uyarilar.append(f"blok {i + 1} [{d}]: hızlı ({len(m) / sure:.0f} kar/sn)")
    bilinmeyen = [d for d in diller if d not in META]
    if bilinmeyen:
        hatalar.append(f"Meta dil kodu bilinmiyor: {bilinmeyen} (META sözlüğüne ekle)")
    for u in uyarilar:
        print("UYARI:", u)
    if hatalar:
        for h in hatalar:
            print("HATA:", h)
        sys.exit("SRT yazılmadı.")
    cikis = pathlib.Path(a.final) / "altyazi"
    cikis.mkdir(parents=True, exist_ok=True)
    sonl = [b["bas"] for b in bloklar[1:]] + [son]
    for d in diller:
        srt = "\n".join(f"{i + 1}\n{zaman(b['bas'])} --> {zaman(s)}\n{b[d].strip()}\n"
                        for i, (b, s) in enumerate(zip(bloklar, sonl)))
        yol = cikis / f"{a.ad}.{META[d]}.srt"
        yol.write_text(srt, encoding="utf-8")
        print(f"{d:6} {len(bloklar)} blok  {yol}")


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    o = alt.add_parser("oner")
    o.add_argument("klasor")
    o.add_argument("--uzerine", action="store_true", help="var olan altyazi_bloklar.json dosyasının üzerine yaz")
    o.add_argument("--plan", help="duzelt sözlüğünü içeren plan_olustur.py (varsayılan: klasördeki)")
    y = alt.add_parser("yaz")
    y.add_argument("klasor")
    y.add_argument("--final", required=True, help="Final/<tarih>_<Baslik> klasörü")
    y.add_argument("--ad", required=True, help="dosya adı (kapak başlığı, ör. Eslik-mi-Isgal-mi)")
    a = ap.parse_args()
    oner(a) if a.komut == "oner" else yaz(a)


if __name__ == "__main__":
    main()
