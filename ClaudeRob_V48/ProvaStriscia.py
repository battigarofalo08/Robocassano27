"""
ProvaStriscia.py  -  [FIX 39] controlla che il robot veda la striscia NERA dell'uscita.

Robot fermo, motori spenti. Lanciatelo dalla cartella del codice (RwdFoto.py NON deve essere acceso):
    python3 ProvaStriscia.py
Mettete il muso del robot sulla striscia nera dell'uscita, dritto e poi di sbieco:
deve scrivere "STRISCIA NERA". Sul pavimento bianco e sulla striscia argento deve scrivere "niente".
Ctrl+C per uscire.
"""
import time
import ViennaClsWebCam as WebCam

print("Prova striscia nera: Ctrl+C per uscire")
try:
    while True:
        img = WebCam.CamSL.capture_array()
        angolo = WebCam.StrisciaNera(img)
        if angolo is None:
            print("niente")
        else:
            print(f"STRISCIA NERA  (inclinata di {angolo:.0f} gradi)")
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    WebCam.CamSL.stop()
    WebCam.CamAr.stop()
