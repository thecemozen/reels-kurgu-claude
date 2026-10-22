"""Çok denemeli çekimde seçilen aralıkları ayrı ayrı yazıya döker; metin.json'u yalnızca kullanılan denemelerle kurar.

Neden: Whisper ham çekimin tamamında aynı cümlenin denemelerini birleştirip zamanlarını kaydırabiliyor. Plan aracı
kelimeleri ham zamana göre eşlediği için altyazı yanlış denemeye düşer. Her aralığı ayrı dökmek bunu önler.

Kullanım:
  .venv\\Scripts\\python.exe -X utf8 araclar\\secim_metni.py <video> <calisma_klasoru> --secim "b1-e1,b2-e2,..." [--terimler "..."]
Ham metin.json varsa metin_ham.json olarak saklanır; yeni metin.json yalnızca seçilen aralıkların kelimelerini içerir.
"""
import argparse, glob, json, os, pathlib, shutil, subprocess, tempfile

KOK = pathlib.Path(__file__).resolve().parent.parent
for d in glob.glob(str(KOK / ".venv" / "Lib" / "site-packages" / "nvidia" / "*" / "bin")):
    os.add_dll_directory(d)
    os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
from faster_whisper import WhisperModel
import ctranslate2
# NVIDIA ekran kartı varsa GPU, yoksa işlemci (daha yavaş ama çalışır)
CIHAZ = ("cuda", "float16") if ctranslate2.get_cuda_device_count() else ("cpu", "int8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("klasor")
    ap.add_argument("--secim", required=True)
    ap.add_argument("--terimler", default="")
    a = ap.parse_args()
    k = pathlib.Path(a.klasor)
    if (k / "metin.json").exists() and not (k / "metin_ham.json").exists():
        shutil.copy(k / "metin.json", k / "metin_ham.json")
    model = WhisperModel(str(KOK / "modeller" / "faster-whisper-large-v3"), device=CIHAZ[0], compute_type=CIHAZ[1])
    cumleler = []
    with tempfile.TemporaryDirectory() as td:
        for parca in a.secim.split(","):
            b, e = map(float, parca.split("-"))
            w = f"{td}/p.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(b), "-to", str(e), "-i", a.video,
                            "-vn", "-ac", "1", "-ar", "16000", w], check=True)
            segs, _ = model.transcribe(w, language="tr", word_timestamps=True, beam_size=5,
                                       condition_on_previous_text=False, initial_prompt=a.terimler or None)
            for s in segs:
                cumleler.append({
                    "bas": round(s.start + b, 2), "son": round(s.end + b, 2), "metin": s.text.strip(),
                    "kelimeler": [{"bas": round(x.start + b, 2), "son": round(x.end + b, 2), "kelime": x.word.strip(),
                                   "guven": round(x.probability, 2)} for x in s.words]})
            print(f"[{b:6.1f}-{e:6.1f}] " + " ".join(s["metin"] for s in cumleler if b <= s["bas"] < e))
    json.dump(cumleler, open(k / "metin.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("yazıldı:", k / "metin.json", f"({sum(len(c['kelimeler']) for c in cumleler)} kelime)")


if __name__ == "__main__":
    main()
