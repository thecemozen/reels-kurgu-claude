"""plan.json üretmek için ortak yardımcılar. Videoya özel plan_olustur.py bunu içe aktarır.

Örnek:
    import sys; sys.path.insert(0, "araclar")
    from plan_arac import Plan
    p = Plan("calisma/<video>", tema="<marka>", duzelt={46.42: "da"})
    t = p.kelime("sabır")                 # "sabır" ile başlayan ilk kelimenin kesik videodaki zamanı
    p.kaydet(ogeler=[...], gecisler=[p.gecis_once("şimdi")], vurgu={"sabır", ...})

Zamanlar: Whisper kelimeleri ham videoya göredir; k() bunları kesik videoya çevirir (kes.py ile aynı kare yuvarlaması).
"""
import json, pathlib, re

from PIL import ImageFont

KOK = pathlib.Path(__file__).resolve().parent.parent


def tr_kucuk(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def kare(t):
    return round(round(t * 30) / 30, 4)


class Plan:
    def __init__(self, klasor, tema, duzelt=None):
        """duzelt: {ham_zaman: "doğru kelime"} Whisper'ın yanlış duyduğu kelimeler (zamana en yakın kelime değişir)."""
        self.k_dir = pathlib.Path(klasor)
        self.tema_ad = tema
        self.tema = json.load(open(KOK / "markalar" / tema / "tema.json", encoding="utf-8"))
        kesim = json.load(open(self.k_dir / "kesimler.json"))
        self.kes = kesim["parcalar"]
        # Kanca (cold open): videonun başına eklenen parça; bütün zamanlar onun süresi kadar kayar
        self.kanca = kesim.get("kanca")
        self.ofset = round(kare(self.kanca["son"]) - kare(self.kanca["bas"]), 4) if self.kanca else 0.0
        metin = json.load(open(self.k_dir / "metin.json", encoding="utf-8"))
        self.kelimeler = [dict(w) for c in metin for w in c["kelimeler"]]
        for t, yeni in (duzelt or {}).items():
            w = min(self.kelimeler, key=lambda w: abs(w["bas"] - t))
            nok = re.findall(r"[.,?!]+$", w["kelime"].strip())
            w["kelime"] = yeni + (nok[0] if nok else "")

    # ---- zaman ----
    def k(self, t):
        """Ham video zamanını kesik video zamanına çevir (ana akış; kanca varsa onun süresi kadar sonra)."""
        acc = self.ofset
        for p in self.kes:
            b, s = kare(p["bas"]), kare(p["son"])
            if t < b:
                return round(acc, 3)
            if t <= s:
                return round(acc + t - b, 3)
            acc += s - b
        return round(acc, 3)

    def sure(self):
        return round(self.ofset + sum(kare(p["son"]) - kare(p["bas"]) for p in self.kes), 3)

    def ham_kelime(self, kok, n=1):
        """kok ile başlayan n. kelime (ham zamanlı sözlük)."""
        kok = tr_kucuk(kok)
        bulunan = [w for w in self.kelimeler if tr_kucuk(re.sub(r"[.,?!]", "", w["kelime"].strip())).startswith(kok)]
        if len(bulunan) < n:
            raise KeyError(f"'{kok}' kelimesinin {n}. geçişi yok")
        return bulunan[n - 1]

    def kelime(self, kok, n=1, son=False):
        """kok ile başlayan n. kelimenin kesik videodaki başlangıç (son=True ise bitiş) zamanı."""
        w = self.ham_kelime(kok, n)
        return self.k(w["son"] if son else w["bas"])

    def kelime_t(self, ham_t, son=False):
        """Ham videodaki ham_t anına en yakın kelimenin kesik videodaki başlangıç (ya da bitiş) zamanı.
        Aynı kelime çok geçtiğinde sıra saymak yerine metin.json'daki zamanla bulmak için."""
        w = min(self.kelimeler, key=lambda w: abs(w["bas"] - ham_t))
        return self.k(w["son"] if son else w["bas"])

    def gecis_t(self, ham_t):
        """Ham videodaki ham_t anında başlayan kelimeden önceki kesim sınırı."""
        w = min(self.kelimeler, key=lambda w: abs(w["bas"] - ham_t))
        i = self.kelimeler.index(w)
        kok = re.sub(r"[.,?!]", "", w["kelime"].strip())
        n = sum(1 for x in self.kelimeler[:i + 1]
                if tr_kucuk(re.sub(r"[.,?!]", "", x["kelime"].strip())).startswith(tr_kucuk(kok)))
        return self.gecis_once(kok, n)

    def gecis_once(self, kok, n=1):
        """Kelimeye en yakın kesim sınırı (bölüm geçişi buraya konur). Whisper kelime başlangıcını önündeki
        sessizliğe kaydırabildiği için sınır, kelimeden önceki ya da hemen sonraki boşluk olabilir."""
        w = self.ham_kelime(kok, n)
        t = w["bas"]
        acc, en_iyi = self.ofset, None
        for i, p in enumerate(self.kes[:-1]):
            b, s = kare(p["bas"]), kare(p["son"])
            acc += s - b
            s_ham, sonraki_bas = s, kare(self.kes[i + 1]["bas"])
            # sınır, kelimenin başladığı boşluğu kapsıyorsa uzaklık 0
            uzak = 0 if s_ham - 0.3 <= t <= sonraki_bas + 0.05 else min(abs(t - s_ham), abs(t - sonraki_bas))
            if uzak < w["son"] - t + 0.3 and (en_iyi is None or uzak < en_iyi[0]):
                en_iyi = (uzak, acc)
        if en_iyi is None:
            raise ValueError(f"'{kok}' yakınında kesim sınırı yok; geçiş için kesim gerekir")
        return round(en_iyi[1], 3)

    # ---- altyazı ----
    def altyazi(self, vurgu=(), kelime_siniri=4):
        out = self._altyazi(self.kelimeler, self.k, self.sure(), vurgu, kelime_siniri)
        if self.kanca:
            kb, ke = kare(self.kanca["bas"]), kare(self.kanca["son"])
            icinde = [w for w in self.kelimeler if kb - 0.05 <= (w["bas"] + w["son"]) / 2 <= ke + 0.05]
            if icinde:
                kanca_alt = self._altyazi(icinde, lambda t: round(min(max(t - kb, 0.0), self.ofset), 3),
                                          self.ofset, vurgu, kelime_siniri)
                kanca_alt[-1]["son"] = self.ofset
                # kancadaki ilk kelime cümle başıysa büyük harfle başlasın
                out = kanca_alt + out
        return out

    def _altyazi(self, kel, esle, son_sinir, vurgu=(), kelime_siniri=4):
        A = self.tema["altyazi"]
        f = ImageFont.truetype(str(KOK / "fontlar" / f"{A['font']}.ttf"), A["boyut"])
        max_g = A["max_genislik"]
        obekler, cur = [], []
        for i, w in enumerate(kel):
            ham = w["kelime"].strip()
            yeni_cumle = i == 0 or kel[i - 1]["kelime"].strip()[-1] in ".?!" or kel[i - 1] is not self._onceki(w)
            yaz = re.sub(r"[.,?!]", "", ham)
            yaz = yaz if yeni_cumle else tr_kucuk(yaz)
            aday = cur + [(yaz, w)]
            if cur and (f.getlength(" ".join(a for a, _ in aday)) > max_g or len(aday) > kelime_siniri):
                obekler.append(cur)
                cur = [(yaz, w)]
            else:
                cur = aday
            if ham[-1] in ".,?!" or (i + 1 < len(kel) and kel[i + 1]["bas"] - w["son"] > 0.3):
                if cur:
                    obekler.append(cur)
                cur = []
        if cur:
            obekler.append(cur)

        def sigar(a, b):
            return f.getlength(" ".join(x for x, _ in a + b)) <= max_g

        def bitis(ob):
            return ob[-1][1]["kelime"].strip()[-1] in ".?!"

        degisti = True
        while degisti:
            degisti = False
            for j, ob in enumerate(obekler):
                if len(ob) == 1 or ob[-1][1]["son"] - ob[0][1]["bas"] < 0.45:
                    if j + 1 < len(obekler) and sigar(ob, obekler[j + 1]) and not bitis(ob):
                        obekler[j:j + 2] = [ob + obekler[j + 1]]
                        degisti = True
                        break
                    if j > 0 and sigar(obekler[j - 1], ob) and not bitis(obekler[j - 1]):
                        obekler[j - 1:j + 1] = [obekler[j - 1] + ob]
                        degisti = True
                        break

        vurgu = {tr_kucuk(v) for v in vurgu}
        out = []
        for j, ob in enumerate(obekler):
            bas = esle(max(ob[0][1]["bas"], 0))
            son = esle(obekler[j + 1][0][1]["bas"]) if j + 1 < len(obekler) else min(esle(ob[-1][1]["son"]) + 0.3,
                                                                                     son_sinir)
            satir = " ".join(a for a, _ in ob)
            out.append({"bas": bas, "son": son, "satirlar": [satir],
                        "vurgu": [w for w in satir.split() if tr_kucuk(w) in vurgu]})
        return out

    def _onceki(self, w):
        i = self.kelimeler.index(w)
        return self.kelimeler[i - 1] if i else None

    def kaydet(self, ogeler, gecisler, vurgu=()):
        alt = self.altyazi(vurgu)
        if self.kanca and not any(abs(g - self.ofset) < 0.05 for g in gecisler):
            gecisler = [round(self.ofset, 3)] + list(gecisler)  # kancadan sonra altın ışıklı geçiş
        if self.kanca:
            # kanca anında ekranda yalnızca kişi ve altyazı: daha önce başlayan öğeler kancanın bitişine kayar
            for o in ogeler:
                if o["bas"] < self.ofset:
                    o["bas"] = round(self.ofset, 3)
                for m in o.get("maddeler", []) + o.get("rozetler", []):
                    if m.get("t", self.ofset) < self.ofset:
                        m["t"] = round(self.ofset, 3)
        plan = {"tema": self.tema_ad, "altyazi": alt, "ogeler": ogeler, "gecisler": gecisler}
        json.dump(plan, open(self.k_dir / "plan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for a in alt:
            print(f"{a['bas']:6.2f}-{a['son']:6.2f}  {a['satirlar'][0]}{'   [' + ', '.join(a['vurgu']) + ']' if a['vurgu'] else ''}")
        print("geçişler:", gecisler)
        for o in ogeler:
            print(f"{o['tur']:9s} {o['bas']:6.2f}-{o['son']:6.2f}  {o.get('baslik', '') or ' / '.join(o.get('satirlar', []))}")
        return plan
