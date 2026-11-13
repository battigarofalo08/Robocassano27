"""
FOTO DI CALIBRAZIONE PER IL SIMULATORE

Scatta foto a piena risoluzione (440 x 260, senza ridimensionarle) dalle DUE camere, con le
stesse impostazioni usate in gara e con i LED accesi. Servono a misurare il punto di vista
delle camere e a tarare il simulatore (altezza, inclinazione, campo visivo).

Uso, dalla cartella del robot e con il robot FERMO:
    python3 ScattaCalibrazione.py

Per ogni foto lo script dice come posizionare il robot. Premete INVIO per scattare,
"s" + INVIO per saltare, "q" + INVIO per uscire. Dopo ogni scatto potete scrivere
la misura reale (es. "muso a 12 cm dall'incrocio"): finisce nel file note.txt.
Le foto vanno in /home/pi/OneDrive/Calibrazione/ (formato PNG, senza perdita di qualità).
"""
import os
import time
import cv2
from ViennaClsRobot import CreaLuci     # [FIX 50] luci senza gpiozero
import ViennaClsWebCam as WebCam      # stessa configurazione delle camere usata in gara

CARTELLA = "/home/pi/OneDrive/Calibrazione/"

SCATTI = [
    ("linea_01_dritta",     "Robot su una linea DRITTA, centrato e allineato alla linea."),
    ("linea_02_righello",   "Metro a nastro o righello sul pavimento, lungo l'asse del robot, con lo 0 sotto il muso."),
    ("linea_03_trasversale","Righello messo DI TRAVERSO davanti al robot, a 10 cm dal muso (misurate)."),
    ("linea_04_incrocio",   "Robot prima di un incrocio con un verde: misurate la distanza muso-incrocio e scrivetela."),
    ("linea_05_piastrella", "Robot dritto al centro di una piastrella, con le giunture ben visibili."),
    ("arena_01_palla_10",   "Pallina argento dritta davanti, a 10 cm dal muso."),
    ("arena_02_palla_20",   "Pallina argento dritta davanti, a 20 cm dal muso."),
    ("arena_03_palla_40",   "Pallina argento dritta davanti, a 40 cm dal muso."),
    ("arena_04_palla_lato", "Pallina argento a 20 cm dal muso e 10 cm a DESTRA del centro."),
    ("arena_05_uscita",     "Robot dentro l'arena, dritto davanti all'uscita, a 40 cm dalla striscia nera."),
    ("arena_06_ingresso",   "Robot sulla linea, dritto, a 20 cm dalla striscia argento dell'ingresso."),
    ("arena_07_triangolo",  "Robot dentro l'arena, dritto verso il triangolo verde, a 40 cm."),
]


def salva(nome, img):
    if img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    cv2.imwrite(os.path.join(CARTELLA, nome), img)


def main():
    os.makedirs(CARTELLA, exist_ok=True)
    luci = CreaLuci()
    led1, led2 = luci['Luce1'], luci['Luce2']
    led1.value = 0          # relè attivi bassi: 0 = acceso, come in gara
    led2.value = 0
    WebCam.AutoregolaCam(WebCam.CamSL)
    WebCam.AutoregolaCam(WebCam.CamAr)
    time.sleep(1.0)
    with open(os.path.join(CARTELLA, "note.txt"), "a", encoding="utf-8") as note:
        note.write(f"\n=== Sessione {time.strftime('%Y-%m-%d %H:%M')} ===\n")
        for nome, istruzione in SCATTI:
            print("\n" + "=" * 60)
            print(nome)
            print(istruzione)
            r = input("INVIO = scatta, s = salta, q = esci > ").strip().lower()
            if r == "q":
                break
            if r == "s":
                continue
            time.sleep(0.5)                       # il robot si ferma, l'esposizione si assesta
            salva(nome + "_camlinea.png", WebCam.CamSL.capture_array())
            salva(nome + "_camarena.png", WebCam.CamAr.capture_array())
            misura = input("Misura reale o note (INVIO se niente) > ").strip()
            note.write(f"{nome}: {istruzione} | NOTE: {misura}\n")
            note.flush()
            print("Salvate:", nome + "_camlinea.png", "e", nome + "_camarena.png")
    led1.value = 1
    led2.value = 1
    print("\nFatto. Le foto sono in", CARTELLA)


if __name__ == "__main__":
    main()
