"""
TaraNero.py - [FIX 45] taratura della soglia del nero; [UI DOS] finestra VGA/MS-DOS.

Da fare su ogni campo nuovo (la luce cambia), con i LED del robot ACCESI come in gara.
RwdFoto.py NON deve essere acceso. Dalla cartella del codice:
    python3 TaraNero.py

Mettete il robot su un tratto con linea nera e pavimento bianco (meglio un incrocio).
La finestra mostra la camera linea e, accanto, la maschera dei pixel considerati neri.
  + / -   alzano o abbassano la soglia di 5
  a       sceglie la soglia automatica Otsu
  s       salva in taratura_nero.json (RwdFoto.py la legge)
  q       esce senza salvare

La grafica è in stile MS-DOS: sfondo blu, cornice ciano e testo monospaziato.
La linea deve apparire piena nella maschera; il pavimento bianco, il verde e le ombre
non devono diventare neri. Senza schermo (via SSH) misura da solo e chiede se salvare.
"""
import json
import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np
from picamera2 import Picamera2
from libcamera import controls

import ViennaDataConf as RwdConf

QUI = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(QUI, "taratura_nero.json")

# [UI DOS] colori BGR della palette VGA: blu, ciano, bianco, verde e giallo.
DOS_BLU = (128, 0, 0)
DOS_BLU_CHIARO = (190, 0, 0)
DOS_CIANO = (255, 255, 0)
DOS_BIANCO = (255, 255, 255)
DOS_VERDE = (0, 255, 0)
DOS_GIALLO = (0, 255, 255)
DOS_FONT = cv2.FONT_HERSHEY_PLAIN


def finestra_dos(img, soglia, suggerita):
    """Inserisce le due immagini reali in una finestra con intestazione e comandi stile DOS."""
    mk = cv2.cvtColor(maschera(img, soglia), cv2.COLOR_GRAY2BGR)
    anteprima = np.hstack([img, mk])
    h, w = anteprima.shape[:2]
    bordo = 10
    altezza_testa = 34
    altezza_etichetta = 22
    altezza_piede = 64
    larghezza = w + bordo * 2
    altezza = altezza_testa + altezza_etichetta + h + altezza_piede
    schermo = np.full((altezza, larghezza, 3), DOS_BLU, dtype=np.uint8)

    # Barra titolo e cornice esterna.
    cv2.rectangle(schermo, (0, 0), (larghezza - 1, altezza_testa), DOS_BLU_CHIARO, -1)
    cv2.putText(schermo, "ROBOCASSANO27  /  MS-DOS  /  TARATURA NERO", (12, 23),
                DOS_FONT, 1.5, DOS_BIANCO, 2, cv2.LINE_8)
    cv2.rectangle(schermo, (2, 2), (larghezza - 3, altezza - 3), DOS_CIANO, 2)

    y_etichetta = altezza_testa + 17
    cv2.putText(schermo, "CAMERA LINEA", (bordo + 4, y_etichetta), DOS_FONT, 1.2, DOS_VERDE, 1, cv2.LINE_8)
    cv2.putText(schermo, "MASCHERA DEL NERO", (bordo + w // 2 + 4, y_etichetta), DOS_FONT, 1.2,
                DOS_GIALLO, 1, cv2.LINE_8)
    y_img = altezza_testa + altezza_etichetta
    schermo[y_img:y_img + h, bordo:bordo + w] = anteprima

    y_stato = y_img + h + 19
    testo = f"SOGLIA ATTUALE: {soglia:3d}"
    if suggerita:
        testo += f"     OTSU: {suggerita[0]:3d}     NERO TIPICO: {suggerita[1]:3d}     BIANCO TIPICO: {suggerita[3]:3d}"
        colore = DOS_VERDE if 60 <= suggerita[0] <= 170 else DOS_GIALLO
    else:
        testo += "     OTSU: NON DISPONIBILE (serve vedere nero e bianco)"
        colore = DOS_GIALLO
    cv2.putText(schermo, testo, (12, y_stato), DOS_FONT, 1.25, colore, 1, cv2.LINE_8)
    cv2.putText(schermo, "[+/-] CAMBIA   [a] OTSU   [s] SALVA   [q] ESCI", (12, y_stato + 24),
                DOS_FONT, 1.35, DOS_BIANCO, 1, cv2.LINE_8)
    return schermo


def soglia_attuale():
    try:
        return int(json.load(open(FILE))["soglia_nero"])
    except Exception:
        return int(RwdConf.SOGLIA_NERO)


def misura(img):
    """Restituisce (soglia Otsu, V tipico del nero, V più chiaro del nero, V tipico del bianco, V più scuro del bianco)."""
    hsv = cv2.cvtColor(cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV)
    v = hsv[..., 2][hsv[..., 1] <= 150]                     # i colori saturi (verde, rosso) non contano
    otsu, _ = cv2.threshold(v.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    nero, bianco = v[v <= otsu], v[v > otsu]
    if len(nero) < 200 or len(bianco) < 200:
        return None
    return (int(otsu), int(np.median(nero)), int(np.percentile(nero, 97)),
            int(np.median(bianco)), int(np.percentile(bianco, 3)))


def maschera(img, s):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 150, s]))


def salva(s, m):
    dati = {"soglia_nero": int(s), "data": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if m:
        dati.update(nero_tipico=m[1], nero_max=m[2], bianco_tipico=m[3], bianco_min=m[4])
    with open(FILE, "w") as f:
        json.dump(dati, f, indent=1)
    print(f"SALVATO: soglia del nero {s} in {FILE}")


def accendi_led():
    try:
        from ViennaClsRobot import Robot
        r = Robot()
        r.GetOnLed1()
        r.GetOnLed2()
        return r
    except Exception as e:
        print("LED non accesi (accendeteli a mano se servono):", e)
        return None


def main():
    robot = accendi_led()
    cam = Picamera2(0)                                     # stessa camera e stesse impostazioni di ViennaClsWebCam
    cfg = cam.create_preview_configuration(main={"format": "XRGB8888", "size": (440, 260)})
    cam.configure(cfg)
    cam.start()
    with cam.controls as c:
        c.AwbEnable = True
        c.AeEnable = True
        c.FrameRate = max(5, min(30, int(getattr(RwdConf, "CAM_LINEA_FPS", 20))))
    # [FIX 112] La taratura manuale usa lo stesso fuoco fisso della V46.
    try:
        distanza_cm = float(getattr(RwdConf, "CAM_LINEA_FUOCO_CM", 8.3))
        diottrie = 100.0 / distanza_cm
        limiti = getattr(cam, "camera_controls", {}).get("LensPosition")
        if limiti and len(limiti) >= 2:
            diottrie = max(float(limiti[0]), min(float(limiti[1]), diottrie))
        cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": diottrie})
        print(f"[FIX 112] Fuoco manuale: {diottrie:.2f} diottrie ({distanza_cm:.1f} cm richiesti)")
    except Exception as e:
        try:
            cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except Exception:
            pass
        print("[FIX 112] Fuoco manuale non disponibile, uso il ripiego:", e)
    time.sleep(2)                                          # lascio assestare esposizione e bianco
    s = soglia_attuale()
    schermo = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    try:
        if not schermo:
            misure = []
            for _ in range(10):
                m = misura(cv2.cvtColor(cam.capture_array(), cv2.COLOR_BGRA2BGR))
                if m:
                    misure.append(m)
                time.sleep(0.2)
            if not misure:
                print("Non vedo abbastanza nero e bianco: mettete il robot su una linea e riprovate")
                return
            m = tuple(int(np.median([x[i] for x in misure])) for i in range(5))
            print(f"Nero: V tipico {m[1]}, il più chiaro {m[2]}   Bianco: V tipico {m[3]}, il più scuro {m[4]}")
            print(f"Soglia attuale {s}   soglia consigliata {m[0]}")
            if input("Salvo la soglia consigliata? (s/n) ").strip().lower() == "s":
                salva(m[0], m)
            return
        nome_finestra = "TARANERO - ROBOCASSANO27 [MS-DOS]"
        cv2.namedWindow(nome_finestra, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(nome_finestra, 920, 390)
        while True:
            img = cv2.cvtColor(cam.capture_array(), cv2.COLOR_BGRA2BGR)
            m = misura(img)
            vista = finestra_dos(img, s, m)
            cv2.imshow(nome_finestra, vista)
            k = cv2.waitKey(100) & 0xFF
            if k in (ord("+"), ord("=")):
                s = min(200, s + 5)
            elif k == ord("-"):
                s = max(20, s - 5)
            elif k == ord("a") and m:
                s = m[0]
            elif k == ord("s"):
                salva(s, m)
                break
            elif k == ord("q"):
                print("Uscito senza salvare")
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()
        if robot is not None:
            try:
                robot.GetOffLed1()
                robot.GetOffLed2()
                robot.Stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
