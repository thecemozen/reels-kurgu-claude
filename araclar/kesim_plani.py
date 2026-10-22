"""Ses enerjisinden sessizlikleri bulur ve kes.py için kesimler.json yazar.

Kullanım: .venv\\Scripts\\python.exe araclar\\kesim_plani.py <video> <calisma_klasoru> --yuz <yuz_olc.json> \\
          [--bas 0.8] [--son 61.6] [--atla "36.37-37.11,..."] [--min 0.35] [--olcek 1.30,1.45]

- Eşik: gürültü + %35 × (konuşma − gürültü). min süreden uzun sessizlikler kesilir;
  sessizliğin başına 0,10 sn, sonuna 0,08 sn pay bırakılır.
- --atla: kesilmemesi gereken sessizlikler (ör. uzatılmış ünlü), "bas-son" biçiminde.
- --yuz: ham videoda yuz_olc.py çıktısı (1080x1920 ölçeğinde); kaynak çözünürlüğe çevrilir.
- --bas/--son verilmezse ilk ve son konuşma anı enerjiden bulunur.
Çıktılar: sessizlik.json, kesimler.json
"""
import argparse, json, pathlib, subprocess, tempfile

import librosa
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("klasor")
    ap.add_argument("--yuz", required=True)
    ap.add_argument("--bas", type=float)
    ap.add_argument("--son", type=float)
    ap.add_argument("--atla", default="")
    ap.add_argument("--min", type=float, default=0.35)
    ap.add_argument("--olcek", default="1.30,1.45")
    ap.add_argument("--metin", help="metin.json: verilirse uzun parçalar kelime arasından bölünür (zoom kesimi)")
    ap.add_argument("--secim", help='çok denemeli çekim: yalnızca bu ham aralıklar kullanılır, "b1-e1,b2-e2,..." (sıralı; sınırlar sessizliğe denk gelmeli). Diğer denemeler ve kamera arkası konuşmalar atılır')
    ap.add_argument("--esitle", action="store_true", help="her parçanın konuşma seviyesini eşitler (kısık denemeler)")
    ap.add_argument("--kanca", help='onaylı kanca, ham saniye "bas-son" (kanca_bul.py çıktısı): videonun başına '
                                    'bir kez daha eklenir; sessizlik sınırına göre pay bırakılır')
    ap.add_argument("--max", type=float, default=4.5, help="bundan uzun parçalar bölünür")
    a = ap.parse_args()
    k = pathlib.Path(a.klasor)

    olc = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                     "stream=width,height:stream_side_data=rotation", "-of", "json", a.video],
                                    capture_output=True, text=True).stdout)["streams"][0]
    w, h = olc["width"], olc["height"]
    rot = abs(int(next((s.get("rotation", 0) for s in olc.get("side_data_list", [])), 0)))
    if rot in (90, 270):
        w, h = h, w

    with tempfile.TemporaryDirectory() as td:
        wav = f"{td}/s.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vn", "-ac", "1", "-ar", "48000", wav], check=True)
        y, sr = librosa.load(wav, sr=None)
    hop = int(sr * 0.01)
    db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=hop * 3, hop_length=hop)[0] + 1e-9)
    gercek = db[db > -90]  # dijital sessizlik (kayıt durdurulmuş/susturulmuş bölümler) gürültü sayılmaz
    gurultu, konusma = np.percentile(gercek, 10), np.percentile(gercek, 90)
    esik = gurultu + 0.35 * (konusma - gurultu)
    sessiz = db < esik
    bolgeler, i = [], 0
    while i < len(sessiz):
        if sessiz[i]:
            j = i
            while j < len(sessiz) and sessiz[j]:
                j += 1
            if (j - i) * 0.01 >= 0.25:
                bolgeler.append((round(i * 0.01, 2), round(j * 0.01, 2), round((j - i) * 0.01, 2)))
            i = j
        else:
            i += 1
    sure = len(db) * 0.01
    konusan = np.where(~sessiz)[0]
    bas = a.bas if a.bas is not None else max(konusan[0] * 0.01 - 0.08, 0)
    son = a.son if a.son is not None else min(konusan[-1] * 0.01 + 0.10, sure)

    atla = []
    for p in filter(None, a.atla.split(",")):
        s1, s2 = map(float, p.split("-"))
        atla.append((s1, s2))

    parcalar, cur = [], round(bas, 2)
    for s1, s2, d in bolgeler:
        if d < a.min or s2 <= bas or s1 + 0.10 >= son:
            continue
        if s1 <= bas:  # başlangıcı kapsayan sessizlik: sadece başlangıcı ileri al
            cur = max(cur, round(s2 - 0.08, 2))
            continue
        if any(s1 >= x1 - 0.01 and s2 <= x2 + 0.01 for x1, x2 in atla):
            continue
        parcalar.append([cur, round(s1 + 0.10, 2)])
        cur = round(s2 - 0.08, 2)
    parcalar.append([cur, round(son, 2)])

    if a.secim:
        pencereler = [tuple(map(float, x.split("-"))) for x in a.secim.split(",") if x.strip()]
        yeni = []
        for w0, w1 in pencereler:
            for p0, p1 in parcalar:
                b0, b1 = max(p0, w0), min(p1, w1)
                if b1 - b0 > 0.12:
                    yeni.append([round(b0, 2), round(b1, 2)])
        parcalar = yeni
        print(f"seçim: {len(pencereler)} deneme aralığı -> {len(parcalar)} parça")

    # Zoom kesimi: uzun parçayı, ortasına en yakın kelime arasından böl. Hiçbir şey atılmaz; ses kesintisiz kalır
    # (kes.py "bitisik" sınırlarda fade uygulamaz), yalnızca kadraj ölçeği değişir.
    bitisik = set()
    if a.metin:
        kel = [w for c in json.load(open(a.metin, encoding="utf-8")) for w in c["kelimeler"]]
        # içinde hiç kelime olmayan çok kısa parçalar (tık, nefes) atılır
        once = len(parcalar)
        parcalar = [p for p in parcalar
                    if p[1] - p[0] >= 0.3 or any(p[0] <= (w["bas"] + w["son"]) / 2 <= p[1] for w in kel)]
        if len(parcalar) < once:
            print(f"kelimesiz kısa parça atıldı: {once - len(parcalar)}")
        degisti = True
        while degisti:
            degisti = False
            for n, (p1, p2) in enumerate(parcalar):
                if p2 - p1 <= a.max:
                    continue
                orta = (p1 + p2) / 2
                adaylar = [(abs((w1["son"] + w2["bas"]) / 2 - orta), round((w1["son"] + w2["bas"]) / 2, 2))
                           for w1, w2 in zip(kel, kel[1:])
                           if p1 + 1.2 < w1["son"] and w2["bas"] < p2 - 1.2 and w2["bas"] - w1["son"] >= 0.02]
                if not adaylar:
                    continue
                kes_t = min(adaylar)[1]
                parcalar[n:n + 1] = [[p1, kes_t], [kes_t, p2]]
                bitisik.add(kes_t)
                degisti = True
                break

    yz = json.load(open(a.yuz))["ozet"]["ortalama_yuz"]
    oran = w / 1080
    merkez = [int((yz[0] + yz[2]) / 2 * oran), int((yz[1] + yz[3]) / 2 * oran)]
    olcekler = [float(x) for x in a.olcek.split(",")]
    kazanclar = {}
    if a.esitle:
        # parça başına konuşma seviyesi (eşik üstü kareler); hedef: parçaların üst çeyreği
        sev = {}
        for p0, p1 in parcalar:
            dilim = db[int(p0 / 0.01):int(p1 / 0.01)]
            konus = dilim[dilim > esik]
            if len(konus):
                sev[(p0, p1)] = float(np.median(konus))
        hedef = float(np.percentile(list(sev.values()), 75)) if sev else 0
        for kp, v in sev.items():
            kazanclar[kp] = round(float(np.clip(hedef - v, -6, 15)), 1)
        print("seviye eşitleme (dB):", [kazanclar.get((p[0], p[1]), 0) for p in parcalar])
    plan = {"kaynak_boyut": [w, h], "yuz_merkez": merkez,
            "parcalar": [{"bas": p[0], "son": p[1], "olcek": olcekler[n % len(olcekler)],
                          **({"bitisik": True} if p[1] in bitisik else {}),
                          **({"kazanc_db": kazanclar[(p[0], p[1])]} if kazanclar.get((p[0], p[1])) else {})}
                         for n, p in enumerate(parcalar)]}
    if a.kanca:
        kb, ke = map(float, a.kanca.split("-"))
        # Whisper sınırları kayabilir: kancanın başını/sonunu en yakın sessizliğe oturt (yoksa 0,08 / 0,10 pay)
        once = [s2 for s1, s2, d in bolgeler if s2 <= kb + 0.25 and s2 >= kb - 0.8]
        sonra = [s1 for s1, s2, d in bolgeler if s1 >= ke - 0.25 and s1 <= ke + 0.8]
        kb2 = round((max(once) - 0.08) if once else kb - 0.08, 2)
        ke2 = round((min(sonra) + 0.10) if sonra else ke + 0.10, 2)
        plan["kanca"] = {"bas": kb2, "son": ke2, "olcek": olcekler[-1] + 0.1}
        print(f"kanca: {kb2}-{ke2} sn ({ke2 - kb2:.2f} sn) videonun başına eklenecek")
    json.dump({"esik_db": float(esik), "sessiz": bolgeler}, open(k / "sessizlik.json", "w"))
    json.dump(plan, open(k / "kesimler.json", "w"), indent=1)
    toplam = sum(p[1] - p[0] for p in parcalar)
    print(f"gürültü {gurultu:.1f} dB, konuşma {konusma:.1f} dB, eşik {esik:.1f} dB")
    print(f"{len(parcalar)} parça, {toplam:.2f} sn (ham {sure:.2f} sn), ortalama {toplam / len(parcalar):.2f} sn")
    print("yüz merkezi (kaynak px):", merkez)
    print("kesilmeyen uzun sessizlikler (atla):", atla)
    for b1, b2, d in bolgeler:
        if d >= a.min:
            print(f"  sessizlik {b1:6.2f}-{b2:6.2f} ({d:.2f} sn)")


if __name__ == "__main__":
    main()
