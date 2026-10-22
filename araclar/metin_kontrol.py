"""Açıklama ve kart metinleri için son kontrol (ig-human'ın Türkçeye uyarlanmış kullanımı).

ig-human'ın iki parçası var:
  - humanize.py: görünmez karakterler, uzun tire, kıvrık tırnak, üç nokta... Dil bağımsız -> aynen kullanılır.
  - detect.py: "insan gibi mi" puanı İngilizceye göre (kısaltmalar, I/you zamirleri). Türkçede anlamsız
    sonuç verir (doğal Türkçe metne ~30/100) -> KULLANILMAZ. Yerine aşağıdaki Türkçe klişe listesi.

Kullanım:
  .venv\\Scripts\\python.exe -X utf8 araclar\\metin_kontrol.py <dosya.txt> [--uygula]
--uygula: temizlenmiş metni dosyanın üzerine yazar (önce .yedek alır).
"""
import argparse, pathlib, re, shutil, subprocess, sys, tempfile

IG_HUMAN = pathlib.Path.home() / ".claude" / "skills" / "ig-human" / "humanize.py"

# Türkçe yapay zekâ / reklam dili klişeleri (marka dili sade ve sakin olmalı)
KLISE = [
    "günümüzün hızlı dünyasında", "hiç olmadığı kadar", "derinlemesine", "keşfetmeye hazır mısın", "hazır mısınız",
    "sihirli", "eşsiz bir", "benzersiz bir", "mükemmel bir", "kesinlikle", "harika bir", "inanılmaz",
    "çığır açan", "oyunun kurallarını", "bir sonraki seviyeye", "potansiyelini açığa", "dönüştürücü",
    "bu yazıda", "bu videoda", "bu gönderide", "takip etmeyi unutma", "beğenmeyi unutma", "kaydırmayı bırak",
    "hadi başlayalım", "sonuç olarak", "unutmayın ki", "şunu belirtmek gerekir", "özetle", "öncelikle belirtmek",
    "her şeyin ötesinde", "yalnızca bir .* değil", "sadece bir .* değil", "hem .* hem de .* hem de",
    "📌", "✨", "💯", "🚀", "🔥",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dosya")
    ap.add_argument("--uygula", action="store_true")
    a = ap.parse_args()
    yol = pathlib.Path(a.dosya)
    metin = yol.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        temiz_yol = pathlib.Path(td) / "temiz.txt"
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(IG_HUMAN), str(yol), "-o", str(temiz_yol), "--report"],
                           capture_output=True, text=True, encoding="utf-8")
        temiz = temiz_yol.read_text(encoding="utf-8") if temiz_yol.exists() else metin
    rapor = (r.stdout or "") + (r.stderr or "")  # ig-human raporu stderr'e yazar
    kaldirilan = re.search(r"(\d+) machine artefacts removed", rapor)
    kaldirilan = int(kaldirilan.group(1)) if kaldirilan else 0
    yapisal = re.findall(r"^\s+\d+x\s+(.+)$", rapor, re.M)

    print(f"METİN KONTROLÜ · {yol.name}")
    print("=" * 60)
    print(f"  Görünmez karakter / noktalama düzeltmesi (ig-human): {kaldirilan}")
    for y in yapisal:
        if "Hashtag wall" in y:
            continue  # Instagram'da en fazla 5 etiket kuralımız var; 5 etiket sorun değil
        print(f"  Yapı uyarısı (ig-human): {y}")
    bulunan = []
    kucuk = metin.replace("İ", "i").replace("I", "ı").lower()
    for k in KLISE:
        if re.search(k, kucuk):
            bulunan.append(k)
    print(f"  Türkçe klişe: {len(bulunan)}" + (f"  -> {', '.join(bulunan)}" if bulunan else ""))
    etiket = re.findall(r"#\w+", metin)
    print(f"  Etiket sayısı: {len(etiket)}" + ("  (en fazla 5!)" if len(etiket) > 5 else ""))
    emoji = re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", metin)
    print(f"  Emoji: {len(emoji)}" + ("  (marka: en fazla 1-2)" if len(emoji) > 2 else ""))
    temiz_mi = kaldirilan == 0 and not bulunan and len(etiket) <= 5 and len(emoji) <= 2
    print("-" * 60)
    print("  SONUÇ: " + ("TEMİZ" if temiz_mi else "GÖZDEN GEÇİR"))
    if a.uygula and kaldirilan:
        shutil.copy(yol, yol.with_suffix(yol.suffix + ".yedek"))
        yol.write_text(temiz, encoding="utf-8")
        print(f"  temizlenmiş metin yazıldı (yedek: {yol.name}.yedek)")


if __name__ == "__main__":
    main()
