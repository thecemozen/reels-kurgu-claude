"""Videodaki Türkçe konuşmayı kelime kelime zamanlarıyla yazıya döker.

Kullanım: .venv\\Scripts\\python.exe araclar\\yaziya_dok.py <video> [cikti.json] [--bas SANIYE] [--sure SANIYE]
"""
import argparse, glob, json, os, pathlib, subprocess, tempfile

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
    ap.add_argument("cikti", nargs="?")
    ap.add_argument("--bas", type=float, default=0)
    ap.add_argument("--sure", type=float)
    ap.add_argument("--terimler", default="",
                    help="Whisper'ın doğru duyması gereken özel kelimeler")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        wav = pathlib.Path(td) / "ses.wav"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a.bas)]
        if a.sure:
            cmd += ["-t", str(a.sure)]
        subprocess.run(cmd + ["-i", a.video, "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)

        model = WhisperModel(str(KOK / "modeller" / "faster-whisper-large-v3"),
                             device=CIHAZ[0], compute_type=CIHAZ[1])
        segs, _ = model.transcribe(str(wav), language="tr", word_timestamps=True,
                                   vad_filter=False, condition_on_previous_text=False,
                                   initial_prompt=a.terimler or None)
        cumleler = []
        for s in segs:
            cumleler.append({
                "bas": round(s.start + a.bas, 2), "son": round(s.end + a.bas, 2), "metin": s.text.strip(),
                "kelimeler": [{"bas": round(w.start + a.bas, 2), "son": round(w.end + a.bas, 2),
                               "kelime": w.word.strip(), "guven": round(w.probability, 2)} for w in s.words],
            })

    if a.cikti:
        pathlib.Path(a.cikti).write_text(json.dumps(cumleler, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in cumleler:
        print(f"[{c['bas']:6.2f} - {c['son']:6.2f}] {c['metin']}")


if __name__ == "__main__":
    main()
