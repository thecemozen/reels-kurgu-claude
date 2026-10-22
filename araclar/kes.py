"""Kesim listesine göre ham videoyu keser, her parçayı kırpıp 1080x1920'ye ölçekler ve birleştirir.

Kullanım: .venv\\Scripts\\python.exe araclar\\kes.py <video> <kesimler.json> <cikti.mp4>

kesimler.json: {"kaynak_boyut": [2160, 3840], "yuz_merkez": [x, y],
                "parcalar": [{"bas": 0.83, "son": 5.53, "olcek": 1.3}, ...]}
olcek: kaynak genişliğinin kaçta biri kırpılacak (1.3 = %77'si). Kırpma yüz merkezine göre yapılır.
"""
import json, subprocess, sys

# Çıktı her zaman 2160x3840 (4K dikey). İstisna gerekirse 4. argüman: "1080x1920"
video, plan_yolu, cikti = sys.argv[1:4]
CG, CY = map(int, (sys.argv[4] if len(sys.argv) > 4 else "2160x3840").split("x"))
plan = json.load(open(plan_yolu, encoding="utf-8"))
KG, KY = plan["kaynak_boyut"]
fx, fy = plan["yuz_merkez"]
FADE = 0.012

def kare(t):
    """Zamanı kare sınırına (1/30 sn) yuvarla: görüntü ve ses aynı uzunlukta kesilir, kayma birikmez."""
    return round(round(t * 30) / 30, 4)


v, a, girdiler = [], [], []
parcalar = plan["parcalar"]
# Kanca (cold open): onaylı kanca cümlesi videonun en başında bir kez daha, daha yakın kadrajla oynar.
# plan["kanca"] = {"bas": .., "son": .., "olcek": 1.45}  (ham video zamanı; kesim_plani.py --kanca yazar)
if plan.get("kanca"):
    kc = plan["kanca"]
    parcalar = [{"bas": kc["bas"], "son": kc["son"], "olcek": kc.get("olcek", 1.45), "kanca": True}] + parcalar
for i, p in enumerate(parcalar):
    w = round(KG / p["olcek"] / 2) * 2
    h = round(w * 16 / 9 / 2) * 2
    x0 = int(min(max(fx - 0.45 * w, 0), KG - w))
    y0 = int(min(max(fy - 0.40 * h, 0), KY - h))
    b, s = kare(p["bas"]), kare(p["son"])
    d = s - b
    # "bitisik": sonraki parça kesintisiz devam ediyor (zoom kesimi) -> bu sınırda fade yok
    fade_in = "" if i and parcalar[i - 1].get("bitisik") else f",afade=t=in:d={FADE}"
    fade_out = "" if p.get("bitisik") else f",afade=t=out:st={d - FADE:.3f}:d={FADE}"
    v.append(f"[0:v]trim={b}:{s},setpts=PTS-STARTPTS,crop={w}:{h}:{x0}:{y0},"
             f"scale={CG}:{CY}:flags=lanczos,setsar=1,fps=30[v{i}]")
    kazanc = f",volume={p['kazanc_db']}dB" if p.get("kazanc_db") else ""  # --esitle: kısık denemeyi yükselt
    a.append(f"[0:a]atrim={b}:{s},asetpts=PTS-STARTPTS{kazanc}{fade_in}{fade_out}[a{i}]")
    girdiler.append(f"[v{i}][a{i}]")

fc = ";".join(v + a) + ";" + "".join(girdiler) + f"concat=n={len(girdiler)}:v=1:a=1[vo][ao]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-filter_complex", fc, "-map", "[vo]", "-map", "[ao]",
                "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "pcm_s16le", "-ar", "48000", cikti], check=True)
print("tamam", cikti)
