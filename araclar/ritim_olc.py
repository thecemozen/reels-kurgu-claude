"""Bir videoda kesim noktalarını ve her kesimdeki yakınlaştırma oranını (yüz genişliği) ölçer.

Kullanım: .venv\\Scripts\\python.exe araclar\\ritim_olc.py <video> [cikti.json]
"""
import json, pathlib, subprocess, sys

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

KOK = pathlib.Path(__file__).resolve().parent.parent
G, Y, FPS = 270, 480, 30

video = sys.argv[1]
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={FPS},scale={G}:{Y}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=str(KOK / "modeller" / "blaze_face_short_range.tflite"))))

fark, yuz, onceki = [], [], None
while True:
    b = p.stdout.read(G * Y * 3)
    if len(b) < G * Y * 3:
        break
    img = np.frombuffer(b, np.uint8).reshape(Y, G, 3)
    gri = img.mean(2)
    fark.append(0.0 if onceki is None else float(np.abs(gri - onceki).mean()))
    onceki = gri
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)))
    if r.detections:
        bb = max(r.detections, key=lambda d: d.bounding_box.width).bounding_box
        yuz.append((bb.width / G, (bb.origin_x + bb.width / 2) / G, (bb.origin_y + bb.height / 2) / Y))
    else:
        yuz.append(None)

fark = np.array(fark)
esik = max(np.median(fark) * 4, 6)
kesimler = [i for i in range(1, len(fark)) if fark[i] > esik and fark[i] >= fark[max(0, i - 2):i + 3].max()]
# Yüz boyutunda ani sıçrama da kesimdir (aynı kadrajda zoom değişimi)
for i in range(1, len(yuz)):
    if yuz[i] and yuz[i - 1] and abs(yuz[i][0] - yuz[i - 1][0]) / yuz[i - 1][0] > 0.06:
        if all(abs(i - k) > 3 for k in kesimler):
            kesimler.append(i)
kesimler.sort()

sahneler, bas = [], 0
for k in kesimler + [len(fark)]:
    ys = [y for y in yuz[bas:k] if y]
    sahneler.append({"bas": round(bas / FPS, 2), "son": round(k / FPS, 2), "sure": round((k - bas) / FPS, 2),
                     "yuz_genislik_orani": round(float(np.mean([y[0] for y in ys])), 3) if ys else None,
                     "yuz_merkez_y": round(float(np.mean([y[2] for y in ys])), 3) if ys else None})
    bas = k

sureler = [s["sure"] for s in sahneler]
ozet = {"sahne_sayisi": len(sahneler), "ortalama_sahne_s": round(float(np.mean(sureler)), 2),
        "medyan_sahne_s": round(float(np.median(sureler)), 2), "en_kisa_s": min(sureler), "en_uzun_s": max(sureler)}
print(json.dumps(ozet, indent=1))
for s in sahneler:
    print(s)
if len(sys.argv) > 2:
    pathlib.Path(sys.argv[2]).write_text(json.dumps({"ozet": ozet, "sahneler": sahneler}, indent=1), encoding="utf-8")
