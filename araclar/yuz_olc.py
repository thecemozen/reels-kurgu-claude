"""Videoda yüzün 1080x1920 dikey ekranda nerede durduğunu ölçer.

Kullanım: .venv\\Scripts\\python.exe araclar\\yuz_olc.py <video> [cikti.json] [--aralik SANIYE] [--ornek ornek.png]
Kareler ffmpeg ile okunur, böylece telefonun döndürme bilgisi otomatik uygulanır.
"""
import argparse, json, pathlib, subprocess

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

KOK = pathlib.Path(__file__).resolve().parent.parent
G, Y = 1080, 1920
PAY = 24  # yüz çevresine bırakılan güvenlik payı (piksel)


def kareler(video, aralik):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf",
                          f"fps=1/{aralik},scale={G}:{Y}:force_original_aspect_ratio=decrease,"
                          f"pad={G}:{Y}:(ow-iw)/2:(oh-ih)/2",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = p.stdout.read(G * Y * 3)
        if len(b) < G * Y * 3:
            break
        yield i * aralik, np.frombuffer(b, np.uint8).reshape(Y, G, 3)
        i += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("cikti", nargs="?")
    ap.add_argument("--aralik", type=float, default=0.5)
    ap.add_argument("--ornek")
    a = ap.parse_args()

    det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(KOK / "modeller" / "blaze_face_short_range.tflite")),
        min_detection_confidence=0.5))

    olcumler, ornek = [], None
    for t, img in kareler(a.video, a.aralik):
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)))
        if not r.detections:
            olcumler.append({"t": round(t, 2), "yuz": None})
            continue
        # en büyük kutu değil, en güvenli algılama (el/yumruk bazen büyük ama düşük güvenli "yüz" sanılır)
        bb = max(r.detections, key=lambda d: d.categories[0].score).bounding_box
        # BlazeFace kutusu alından çeneye kadar; saç ve kulaklar için biraz büyütüyoruz
        x0, y0 = bb.origin_x - 0.15 * bb.width, bb.origin_y - 0.45 * bb.height
        x1, y1 = bb.origin_x + 1.15 * bb.width, bb.origin_y + 1.1 * bb.height
        olcumler.append({"t": round(t, 2), "yuz": [int(x0), int(y0), int(x1), int(y1)]})
        if ornek is None:
            ornek = (img.copy(), (x0, y0, x1, y1))

    # Sıçrama ayıklama: merkezi, komşu ölçümlerin (±3) ortancasından yüz yüksekliğinin %40'ından fazla
    # uzaklaşan kutu yanlış algılamadır; komşuların ortanca kutusuyla değiştirilir.
    ayiklanan = 0
    for i, o in enumerate(olcumler):
        if not o["yuz"]:
            continue
        komsu = [q["yuz"] for q in olcumler[max(0, i - 3):i + 4] if q["yuz"] and q is not o]
        if len(komsu) < 2:
            continue
        orta = np.median(np.array(komsu), axis=0)
        yuk = orta[3] - orta[1]
        mx, my = (o["yuz"][0] + o["yuz"][2]) / 2, (o["yuz"][1] + o["yuz"][3]) / 2
        if abs(mx - (orta[0] + orta[2]) / 2) > 0.4 * yuk or abs(my - (orta[1] + orta[3]) / 2) > 0.4 * yuk:
            o["yuz"] = [int(v) for v in orta]
            o["duzeltildi"] = True
            ayiklanan += 1
    bulunan = [o["yuz"] for o in olcumler if o["yuz"]]
    ozet = {"kare_sayisi": len(olcumler), "yuz_bulunan": len(bulunan), "ayiklanan_yanlis_algilama": ayiklanan}
    if bulunan:
        arr = np.array(bulunan)
        birlesik = [int(arr[:, 0].min()) - PAY, int(arr[:, 1].min()) - PAY,
                    int(arr[:, 2].max()) + PAY, int(arr[:, 3].max()) + PAY]
        ozet.update({
            "ortalama_yuz": [int(v) for v in arr.mean(0)],
            "yuz_genisligi_px": int((arr[:, 2] - arr[:, 0]).mean()),
            "tum_video_yasak_alan": birlesik,
            "basin_ustu_bos_alan_px": [220, birlesik[1]],
            "gogus_hizasi_bos_alan_px": [birlesik[3], Y - 420],
        })
    if a.cikti:
        pathlib.Path(a.cikti).write_text(json.dumps({"ozet": ozet, "olcumler": olcumler}, indent=1), encoding="utf-8")
    print(json.dumps(ozet, indent=1))

    if a.ornek and ornek is not None:
        img, (x0, y0, x1, y1) = ornek
        im = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        kat = im.copy()
        cv2.rectangle(kat, (0, 0), (G, 220), (60, 60, 230), -1)              # Instagram üst bant
        cv2.rectangle(kat, (0, Y - 420), (G, Y), (60, 60, 230), -1)          # Instagram alt bant
        cv2.rectangle(kat, (G - 160, Y // 2), (G, Y - 420), (60, 60, 230), -1)  # sağ ikonlar
        b = ozet["tum_video_yasak_alan"]
        cv2.rectangle(kat, (b[0], b[1]), (b[2], b[3]), (40, 200, 255), -1)   # yüz (tüm video)
        im = cv2.addWeighted(kat, 0.4, im, 0.6, 0)
        cv2.rectangle(im, (int(x0), int(y0)), (int(x1), int(y1)), (31, 210, 255), 4)
        cv2.imwrite(a.ornek, im)


if __name__ == "__main__":
    main()
