"""Kesik videonun metnini orijinal metinle karşılaştırır ve her kesim noktasını ayrıca dinler.

Kullanım: .venv\\Scripts\\python.exe araclar\\kesim_kontrol.py <calisma_klasoru>
Klasörde metin.json (orijinal), kesimler.json ve kesik.mp4 olmalı.
Çıktı: eksik/fazla kelimeler ve her kesimin ±0,6 sn çevresinde duyulan metin.
"""
import difflib, glob, json, os, pathlib, re, subprocess, sys, tempfile

KOK = pathlib.Path(__file__).resolve().parent.parent
for d in glob.glob(str(KOK / ".venv" / "Lib" / "site-packages" / "nvidia" / "*" / "bin")):
    os.add_dll_directory(d)
    os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
from faster_whisper import WhisperModel
import ctranslate2
# NVIDIA ekran kartı varsa GPU, yoksa işlemci (daha yavaş ama çalışır)
CIHAZ = ("cuda", "float16") if ctranslate2.get_cuda_device_count() else ("cpu", "int8")

k = pathlib.Path(sys.argv[1])
orj = json.load(open(k / "metin.json", encoding="utf-8"))
plan = json.load(open(k / "kesimler.json", encoding="utf-8"))
model = WhisperModel(str(KOK / "modeller" / "faster-whisper-large-v3"), device=CIHAZ[0], compute_type=CIHAZ[1])


def norm(t):
    return re.sub(r"[^\wçğıöşü]", "", t.replace("İ", "i").replace("I", "ı").lower())


def dok(wav):
    segs, _ = model.transcribe(wav, language="tr", word_timestamps=True, condition_on_previous_text=False)
    return [w for s in segs for w in s.words]


with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, "k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(k / "kesik.mp4"), "-ac", "1", "-ar", "16000", wav], check=True)
    yeni = [norm(w.word) for w in dok(wav)]
    eski = [norm(w["kelime"]) for c in orj for w in c["kelimeler"]]
    if plan.get("kanca"):  # kanca başta bir kez daha duyulur
        kb, ke = plan["kanca"]["bas"], plan["kanca"]["son"]
        eski = [norm(w["kelime"]) for c in orj for w in c["kelimeler"] if kb - 0.05 <= (w["bas"] + w["son"]) / 2 <= ke + 0.05] + eski
    sorun = 0
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, eski, yeni).get_opcodes():
        if op != "equal":
            sorun += 1
            print(f"FARK {op}: orijinal={eski[a1:a2]} kesik={yeni[b1:b2]}")
    print(f"Kelime: orijinal {len(eski)}, kesik {len(yeni)}, fark {sorun}")

    t = (plan["kanca"]["son"] - plan["kanca"]["bas"]) if plan.get("kanca") else 0.0
    for i, p in enumerate(plan["parcalar"][:-1]):
        t += p["son"] - p["bas"]
        parca = os.path.join(td, f"c{i}.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t - 0.6, 0):.2f}", "-t", "1.2", "-i",
                        str(k / "kesik.mp4"), "-ac", "1", "-ar", "16000", parca], check=True)
        duyulan = " ".join(w.word.strip() for w in dok(parca))
        print(f"kesim {i + 1:2d} @ {t:6.2f}s  | {duyulan}")
