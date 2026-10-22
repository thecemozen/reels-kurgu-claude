"""Videonun kendi konuşmasından kanca (ilk 2-3 saniye) adaylarını bulur ve Türkçe puanlar.

ig-reel/hookscore.py'nin beş ölçütünün Türkçe uyarlaması (orijinal İngilizce kelime listeleriyle çalışır,
Türkçe cümleye haksız düşük puan verir):
  UZUNLUK    söylenmesi ~3 sn'yi geçmesin (Türkçede 4-10 kelime)
  SOMUTLUK   sayı, özel ad ya da markanın kavram kelimesi (sabır, işgal, bilinçaltı...)
  GERİLİM    olumsuzluk, karşıtlık, soru, kayıp/korku: izleyicinin kaybedeceği bir şey
  ÖNE        önemli kelime ilk 3 kelimede mi; "şimdi, bugün, kabul edelim..." gibi boş açılış var mı
  HİTAP      izleyiciye mi konuşuyor (sen, -sun/-sin, emir), yoksa havada mı

Puan bir tahmin değildir: boş açılışı, somut olmayan ve uzun cümleleri yakalar; iki iyi kancadan hangisinin
tutacağını söyleyemez. Son karar kullanıcınındır.

Kullanım:
  .venv\\Scripts\\python.exe -X utf8 araclar\\kanca_bul.py calisma/<video> [--marka <marka>] [--en 5]
  .venv\\Scripts\\python.exe -X utf8 araclar\\kanca_bul.py --kanca "Sabır mı, tahammül mü?"   (tek cümle)
Çıktı: ekrana sıralı tablo + calisma/<video>/kanca_adaylari.json
"""
import argparse, json, pathlib, re, statistics, sys

KOK = pathlib.Path(__file__).resolve().parent.parent

SAYILAR = {"iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on", "yirmi", "otuz", "kırk",
           "elli", "yüz", "bin", "milyon", "yarım", "çeyrek", "ilk", "son", "tek"}
GERILIM = {
    "değil", "değilsin", "asla", "hiç", "hiçbir", "kimse", "yanlış", "hata", "sorun", "sıkıntı", "sıkıntılı", "zor",
    "korku", "korkuyorsun", "kork", "öfke", "acı", "yük", "kayıp", "kaybetmek", "kaybediyorsun", "unutuyorsun",
    "hastalık", "hasta", "tehlike", "risk", "ama", "oysa", "fakat", "aslında", "sanki", "gerçek", "gerçekten",
    "sır", "gizli", "neden", "niye", "nasıl", "farkı", "fark", "karmaşa", "karmaşası", "kaçının", "kaçın", "dur",
    "bırak", "işgal", "tahammül", "ciddiyet", "dengesizleştirebiliyor", "şiddet", "kavga", "yalnız", "yetersiz",
}
# markanın kavram kelimeleri (markalar/<marka>/kanca_kelimeleri.txt ile genişletilir)
KAVRAM_VARSAYILAN = {
    "sabır", "sabr", "tahammül", "eşlik", "işgal", "ciddi", "resmi", "regresyon", "bilinçaltı", "bilinç", "korku",
    "karma", "ego", "şükür", "niyet", "sevgi", "atalar", "ruh", "beden", "döngü", "kalıp", "tekâmül", "tekamül",
}
BOS_ACILIS = [
    "şimdi", "evet", "merhaba", "selam", "arkadaşlar", "bugün", "yani", "işte", "ve", "o yüzden", "bu yüzden",
    "kabul edelim", "bu videoda", "bu video", "burada şöyle", "şöyle bir", "bir şey", "biraz", "ee", "şey",
    "aslında", "dediğim gibi", "bakın", "tamam", "peki",
]
EMIR = {"bak", "dur", "yaz", "kaçın", "kaçının", "bırak", "dinle", "dinleyin", "düşün", "sor", "kaydet", "unutma"}
SORU_EKI = re.compile(r"\b(mı|mi|mu|mü|mısın|misin|musun|müsün|mıyım|miyim)\b", re.I)
IKINCI_TEKIL = re.compile(r"\b(sen|sana|seni|senin|sende|senden|kendin|kendini|kendinin)\b|\w+(sun|sün|sin|sın|sunuz|sünüz|siniz|sınız)\b", re.I)
KELIME = re.compile(r"[\wçğıöşüÇĞİÖŞÜâîû]+")

DETAY_TR = {"UZUNLUK": "uzunluk", "SOMUTLUK": "somutluk", "GERİLİM": "gerilim", "ÖNE": "öne çıkma", "HİTAP": "hitap"}


def kucuk(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def kelimeler(t):
    return KELIME.findall(t)


def kavramlar(marka):
    k = set(KAVRAM_VARSAYILAN)
    dosya = KOK / "markalar" / (marka or "") / "kanca_kelimeleri.txt"
    if marka and dosya.exists():
        k |= {kucuk(x.strip()) for x in dosya.read_text(encoding="utf-8").split() if x.strip()}
    return k


def puanla(metin, sure=None, kavram=KAVRAM_VARSAYILAN):
    w = kelimeler(metin)
    low = [kucuk(x) for x in w]
    n = len(w)
    s = {}
    # UZUNLUK: 4-10 kelime, mümkünse gerçek konuşma süresiyle
    sn = sure if sure else n / 2.4
    if 4 <= n <= 10 and sn <= 3.5:
        u = 100.0
    elif n < 4:
        u = 100 - (4 - n) * 22
    else:
        u = 100 - max(n - 10, 0) * 11 - max(sn - 3.5, 0) * 18
    s["UZUNLUK"] = (max(0.0, min(100.0, u)), f"{n} kelime, ~{sn:.1f} sn (hedef 4-10 kelime, ≤3,5 sn)")
    # SOMUTLUK
    sayi = [x for x in low if x in SAYILAR or x.isdigit()]
    ozel = [w[i] for i in range(1, n) if w[i][0].isupper()]
    kav = sorted({x for x in low if any(x.startswith(k) for k in kavram)})
    isabet = len(sayi) + len(ozel) + len(kav)
    s["SOMUTLUK"] = (15.0 if isabet == 0 else min(100.0, 45 + isabet * 25),
                     f"{isabet} somut iz" + (f": {', '.join((kav + ozel + sayi)[:4])}" if isabet else " (sayı, ad ya da kavram yok)"))
    # GERİLİM
    ger = sorted({x for x in low if x in GERILIM})
    soru = bool(SORU_EKI.search(kucuk(metin))) or metin.strip().endswith("?")
    karsitlik = bool(re.search(r"\b(mı|mi|mu|mü)\b.*\b(mı|mi|mu|mü)\b", kucuk(metin)))  # "X mı, Y mi?"
    isaret = len(ger) + (1 if soru else 0) + (1 if karsitlik else 0)
    s["GERİLİM"] = ({0: 20.0, 1: 70.0}.get(isaret, 100.0),
                    f"{isaret} gerilim işareti" + (f": {', '.join(ger[:3] + (['soru'] if soru else []) + (['karşıtlık'] if karsitlik else []))}" if isaret else " (ortada kaybedilecek bir şey yok)"))
    # ÖNE
    acilis = " ".join(low[:2])
    bos = next((b for b in BOS_ACILIS if acilis.startswith(b) or (low and low[0] == b)), None)
    yuk = next((i for i, x in enumerate(low) if x in GERILIM or any(x.startswith(k) for k in kavram)
                or x in SAYILAR or (i and w[i][0].isupper())), None)
    taban = 30.0 if yuk is None else 100.0 if yuk <= 2 else 70.0 if yuk <= 5 else 40.0
    s["ÖNE"] = (max(0.0, taban - (30 if bos else 0)),
                ("önemli kelime yok" if yuk is None else f"önemli kelime {yuk + 1}. sırada")
                + (f"; boş açılış \"{bos}\"" if bos else ""))
    # HİTAP
    if IKINCI_TEKIL.search(kucuk(metin)):
        h, d = 100.0, "izleyiciye konuşuyor (sen)"
    elif low and low[0] in EMIR or any(x in EMIR for x in low):
        h, d = 90.0, "emir kipi"
    elif re.search(r"\b(ben|benim|biz|bizim|hepimiz|hepimizi)\b", kucuk(metin)):
        h, d = 70.0, "birinci şahıs, izleyici yok"
    elif soru:
        h, d = 75.0, "izleyiciye soru"
    else:
        h, d = 35.0, "üçüncü şahıs, kimseye konuşmuyor"
    s["HİTAP"] = (h, d)
    puanlar = [v[0] for v in s.values()]
    genel = statistics.mean(puanlar) * 0.6 + min(puanlar) * 0.4
    karar = "GÜÇLÜ" if genel >= 70 and min(puanlar) >= 55 else "İYİ" if genel >= 50 else "ZAYIF"
    return s, round(genel, 1), karar


def adaylar(metin_json, duzelt=None):
    """Cümle ve yan cümle adayları: (metin, ham_bas, ham_son)."""
    segs = json.load(open(metin_json, encoding="utf-8"))
    kel = []
    for c in segs:
        for j, w in enumerate(c["kelimeler"]):
            kel.append(dict(w, segment_sonu=(j == len(c["kelimeler"]) - 1)))
    for t, yeni in (duzelt or {}).items():
        w = min(kel, key=lambda w: abs(w["bas"] - t))
        w["kelime"] = yeni
    cumleler, cur = [], []
    for w in kel:
        cur.append(w)
        if w["kelime"].strip()[-1:] in ".?!" or w.get("segment_sonu"):
            cumleler.append(cur)
            cur = []
    if cur:
        cumleler.append(cur)
    out = []

    def ekle(parca):
        metin = " ".join(x["kelime"].strip() for x in parca)
        n = len(kelimeler(metin))
        if 3 <= n <= 14:
            out.append((metin, parca[0]["bas"], parca[-1]["son"]))

    for i, c in enumerate(cumleler):
        ekle(c)
        # virgülle ayrılan yan cümleler
        parca = []
        for w in c:
            parca.append(w)
            if w["kelime"].strip().endswith(","):
                if parca != c:
                    ekle(parca)
                parca = []
        if parca and parca != c:
            ekle(parca)
        # kısa iki cümle art arda ("Doğru olan eşlik, sıkıntılı olan işgal. İşgalden kaçının.")
        if i + 1 < len(cumleler):
            ekle(c + cumleler[i + 1])
    tekil, gorulen = [], set()
    for a in out:
        if a[0] not in gorulen:
            gorulen.add(a[0])
            tekil.append(a)
    return tekil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor", nargs="?")
    ap.add_argument("--kanca")
    ap.add_argument("--marka", default=None)
    ap.add_argument("--en", type=int, default=5)
    ap.add_argument("--duzelt", help='onaylı Whisper düzeltmeleri: "46.42=da;82.8=resmiyet iyi" (ham saniye=kelime, ; ile)')
    a = ap.parse_args()
    kavram = kavramlar(a.marka)
    if a.kanca:
        s, g, k = puanla(a.kanca, kavram=kavram)
        print(f"\n  \"{a.kanca}\"  ->  {g}  {k}")
        for ad, (p, d) in s.items():
            print(f"    {DETAY_TR[ad]:<11} {p:5.1f}  {d}")
        return
    k = pathlib.Path(a.klasor)
    sonuc = []
    duzelt = {}
    for parca in filter(None, (a.duzelt or "").split(";")):
        t, _, yeni = parca.partition("=")
        duzelt[float(t)] = yeni
    for metin, b, e in adaylar(k / "metin.json", duzelt):
        s, g, karar = puanla(metin, e - b, kavram)
        yarim = metin.rstrip().endswith(",")
        if yarim:
            g = round(max(0.0, g - 10), 1)
            karar = "GÜÇLÜ" if g >= 70 and karar == "GÜÇLÜ" else "İYİ" if g >= 50 else "ZAYIF"
        sonuc.append({"kanca": metin, "ham_bas": round(b, 2), "ham_son": round(e, 2), "sure": round(e - b, 2),
                      "puan": g, "karar": karar, "yarim_cumle": yarim,
                      "olcutler": {DETAY_TR[ad]: {"puan": round(p, 1), "detay": d} for ad, (p, d) in s.items()}})
    sonuc.sort(key=lambda r: -r["puan"])
    for i, r in enumerate(sonuc, 1):
        r["no"] = i
    json.dump(sonuc, open(k / "kanca_adaylari.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ilk = min(sonuc, key=lambda r: (r["ham_bas"], len(r["kanca"])))  # videonun ilk cümlesi
    print(f"\nKANCA ADAYLARI · {k.name}   (şu anki açılış: \"{ilk['kanca'][:60]}\" → {ilk['puan']} {ilk['karar']})")
    print("=" * 96)
    for r in sonuc[:a.en]:
        zayif = min(r["olcutler"], key=lambda x: r["olcutler"][x]["puan"])
        print(f"{r['no']:>2}. {r['puan']:5.1f} {r['karar']:<6} {r['ham_bas']:6.1f}-{r['ham_son']:5.1f} sn  \"{r['kanca']}\""
              + ("   (yarım cümle)" if r["yarim_cumle"] else ""))
        print(f"    en zayıf: {zayif} ({r['olcutler'][zayif]['puan']:.0f}) - {r['olcutler'][zayif]['detay']}")
    print("\nPuan bir tahmin değil: boş açılışı, somut olmayanı ve uzunu yakalar. Son karar kullanıcının.")


if __name__ == "__main__":
    main()
