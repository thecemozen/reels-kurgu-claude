"""Son çıktı: grafikli görüntü + geçiş sesleri + marka kapanışı + -14 LUFS ses -> Final/*.mp4

Kullanım: .venv\\Scripts\\python.exe araclar\\cikti.py <calisma_klasoru> <cikti.mp4> [--ses temiz|ham] [--gorsel-var]

--ses temiz : ses kullanıcı tarafından işlenmiş (gürültü/kompresör yapılmış); yalnızca seviye ve tepe sınırlama.
--ses ham   : telefon sesi; 80 Hz yüksek geçiren, afftdn, kompresör + sınırlayıcı, sonra seviye.
--gorsel-var: <klasor>/gorsel.mp4 zaten üretildiyse kurgu.py --tam tekrar çalışmaz.
Kapanış ve tema plan.json'daki "tema" alanından gelir (markalar/<marka>/tema.json -> dosyalar.kapanis).
"""
import argparse, json, pathlib, re, subprocess, sys

import numpy as np
import scipy.io.wavfile as wf
import scipy.signal as ss

KOK = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
SR = 48000
HEDEF_LUFS, TEPE = -14.0, 0.84  # 0.84 ≈ -1.5 dBFS


def sure(yol):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(yol)],
                                capture_output=True, text=True).stdout)


def lufs(yol):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor")
    ap.add_argument("cikti")
    ap.add_argument("--ses", choices=["temiz", "ham"], default="ham")
    ap.add_argument("--gorsel-var", action="store_true")
    a = ap.parse_args()
    k = pathlib.Path(a.klasor)
    plan = json.load(open(k / "plan.json", encoding="utf-8"))
    tema_ad = plan.get("tema", "v1")
    tema = json.load(open(KOK / "markalar" / tema_ad / "tema.json", encoding="utf-8")) if tema_ad != "v1" else {}
    kapanis = (tema.get("dosyalar") or {}).get("kapanis")

    # 1) grafikli görüntü
    gorsel = k / "gorsel.mp4"
    if not (a.gorsel_var and gorsel.exists()):
        print("görüntü çiziliyor…", flush=True)
        subprocess.run([PY, str(KOK / "araclar" / "kurgu.py"), str(k), "--tam", str(gorsel)], check=True,
                       stderr=subprocess.DEVNULL)
    D = sure(gorsel)
    GP, YP = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "csv=p=0", str(gorsel)],
                                     capture_output=True, text=True).stdout.strip().split(","))

    # 2) geçiş sesi (kodla üretilmiş, çok kısık whoosh)
    iz = np.zeros(int((D + 1) * SR), np.float32)
    rng = np.random.default_rng(7)
    b, aa = ss.butter(2, [600 / (SR / 2), 5000 / (SR / 2)], btype="band")
    for g in plan.get("gecisler", []):
        n = int(0.25 * SR)
        x = ss.lfilter(b, aa, rng.standard_normal(n).astype(np.float32)) * np.sin(np.linspace(0, np.pi, n)) ** 2
        x = x / np.abs(x).max() * 10 ** (-30 / 20)
        s = max(int((g - 0.15) * SR), 0)
        n2 = min(n, len(iz) - s)  # görüntü beklenenden kısaysa geçiş sesi taşmasın
        if n2 <= 0:
            print(f"UYARI: {g:.2f} sn geçişi görüntü süresinin ({D:.2f} sn) dışında, atlandı")
            continue
        iz[s:s + n2] += x[:n2]
    wf.write(k / "whoosh.wav", SR, iz)

    # 3) ses zinciri + kapanış (görüntü xfade, ses acrossfade)
    on = "highpass=f=80,afftdn=nf=-25,acompressor=threshold=0.08:ratio=3:attack=5:release=90:knee=4," \
         "alimiter=limit=0.5:attack=2:release=40:level=false," if a.ses == "ham" else ""
    girdiler = ["-i", str(gorsel), "-i", str(k / "kesik.mp4"), "-i", str(k / "whoosh.wav")]
    fc = f"[1:a]{on}aresample={SR},aformat=channel_layouts=mono[sp];[2:a]aresample={SR}[wh];" \
         f"[sp][wh]amix=inputs=2:normalize=0:duration=first[mix]"
    if kapanis:
        girdiler += ["-i", str(KOK / kapanis)]
        fc += f";[0:v]fps=30,format=yuv420p,setsar=1[v0];[3:v]scale={GP}:{YP}:flags=lanczos,fps=30,format=yuv420p,setsar=1[v1];" \
              f"[v0][v1]xfade=transition=fade:duration=0.15:offset={D - 0.15:.3f}[vo];" \
              f"[3:a]aresample={SR},aformat=channel_layouts=mono[oa];[mix][oa]acrossfade=d=0.15[ao]"
    else:
        fc += ";[0:v]fps=30,format=yuv420p,setsar=1[vo];[mix]anull[ao]"
    ara = k / "ara.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *girdiler, "-filter_complex", fc, "-map", "[vo]", "-map", "[ao]",
                    "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-c:a", "pcm_s16le", str(ara)], check=True)

    # 4) seviye: -14 LUFS, tepe sınırlı
    ses0 = k / "ses_ara.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ara), "-vn", "-c:a", "pcm_s16le", str(ses0)], check=True)
    kazanc = HEDEF_LUFS - lufs(ses0)
    ses1 = k / "ses_son.wav"
    for _ in range(2):  # sınırlayıcı seviyeyi biraz düşürebilir; bir kez daha düzelt
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ses0), "-af",
                        f"volume={kazanc:.2f}dB,alimiter=limit={TEPE}:attack=1:release=50:level=false",
                        "-c:a", "pcm_s16le", str(ses1)], check=True)
        fark = HEDEF_LUFS - lufs(ses1)
        if abs(fark) < 0.3:
            break
        kazanc += fark

    # 5) son kodlama
    cikti = pathlib.Path(a.cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ara), "-i", str(ses1), "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-profile:v", "high", "-level:v", "5.2", "-crf", "16", "-preset", "slow",
                    "-x264-params", "aq-mode=3", "-maxrate", "60M", "-bufsize", "120M", "-pix_fmt", "yuv420p",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                    "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
                    "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                    "-shortest", str(cikti)], check=True)
    print(f"tamam: {cikti}  süre {sure(cikti):.2f} sn  ses {lufs(cikti):.1f} LUFS")
    # Final/<tarih>_<video>/ düzeni: BILGI.md otomatik
    if cikti.parent.parent.resolve() == (KOK / "Final").resolve():
        sys.path.insert(0, str(KOK / "araclar"))
        import final
        final.bilgi(cikti.parent, calisma=k.resolve())


if __name__ == "__main__":
    main()
