"""
ProvaVerde.py  -  [FIX 36] prova il "secondo parere sui verdi" sulle foto già scattate dal robot.

Non muove il robot, non apre le camere e non carica YOLO. Si lancia dalla cartella del codice:
    python3 ProvaVerde.py                      (usa /home/pi/OneDrive/Incroci/)
    python3 ProvaVerde.py /percorso/cartella   (un'altra cartella di foto)

Per ogni foto che YOLO aveva classificato come Sx, Dx o Fr (il nome del file inizia così)
ricalcola la decisione con i colori e scrive le foto disegnate in <cartella>_ControlloVerde/:
  - riga blu: la linea orizzontale dell'incrocio
  - riquadro verde: verde valido (prima dell'incrocio)
  - riquadro rosso: falso verde (dopo l'incrocio)
Guardate soprattutto le foto dove YOLO e i colori non sono d'accordo.
"""
import os, sys, glob
import cv2
import numpy as np
import ViennaDataConf as RwdConf
import ast, types

# Prendo VerdiGeometria e le soglie dei colori direttamente da ViennaClsWebCam.py SENZA importarlo:
# importarlo aprirebbe le camere e caricherebbe i modelli YOLO. Così la regola è sempre la stessa del robot.
_qui = os.path.dirname(os.path.abspath(__file__))
_albero = ast.parse(open(os.path.join(_qui, "ViennaClsWebCam.py"), encoding="utf-8").read())
_pezzi = [n for n in _albero.body
          if (isinstance(n, ast.FunctionDef) and n.name == "VerdiGeometria")
          or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in
              ("lower_green", "upper_green", "lower_black", "upper_black") for t in n.targets))]
WebCam = types.SimpleNamespace()
_spazio = {"cv2": cv2, "np": np, "RwdConf": RwdConf, "SOGLIA_NERO": RwdConf.SOGLIA_NERO}   # [FIX 45]
try:
    import json
    _spazio["SOGLIA_NERO"] = int(json.load(open(os.path.join(_qui, "taratura_nero.json")))["soglia_nero"])
except Exception:
    pass
exec(compile(ast.Module(body=_pezzi, type_ignores=[]), "ViennaClsWebCam.py", "exec"), _spazio)
for _k in ("VerdiGeometria", "lower_green", "upper_green", "lower_black", "upper_black"):
    setattr(WebCam, _k, _spazio[_k])

cartella = sys.argv[1] if len(sys.argv) > 1 else RwdConf.CARTELLA_FOTO
uscita = cartella.rstrip("/") + "_ControlloVerde"
os.makedirs(uscita, exist_ok=True)

foto = sorted(glob.glob(os.path.join(cartella, "*.jpg")) + glob.glob(os.path.join(cartella, "*.png")))
provate = d_accordo = diverse = indecise = 0
for f in foto:
    nome = os.path.basename(f)
    yolo = nome[:2]
    if yolo not in ("Sx", "Dx", "Fr"):
        continue
    img = cv2.imread(f)
    if img is None:
        continue
    array = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
    dett = {}
    geo, perche = WebCam.VerdiGeometria(array, dett)
    provate += 1
    if geo is None:
        indecise += 1
        esito = "INDECISO"
    elif geo == yolo:
        d_accordo += 1
        esito = "OK"
    else:
        diverse += 1
        esito = "DIVERSO"
        print(f"{nome}: YOLO {yolo} -> colori {geo}  ({perche})")
    # disegno [FIX 78]: la linea dell'incrocio con la sua inclinazione, i verdi validi (verde), i falsi (rosso)
    # e le macchie ignorate perché sottili o sfilacciate, cioè il bordo del nastro (grigio)
    if "y_banda" in dett:
        k = np.tan(np.radians(dett["angolo"]))
        y0 = dett["y_banda"] - 112 * k
        cv2.line(array, (0, int(y0)), (223, int(y0 + 223 * k)), (255, 0, 0), 2)
    for x, y, w, h, stato in dett.get("macchie", []):
        col = {"valido": (0, 200, 0), "falso": (0, 0, 255), "ignorata": (160, 160, 160)}[stato]
        cv2.rectangle(array, (int(x), int(y)), (int(x + w), int(y + h)), col, 2)
    cv2.putText(array, f"YOLO {yolo}  colori {geo}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
    cv2.putText(array, f"YOLO {yolo}  colori {geo}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    cv2.imwrite(os.path.join(uscita, f"{esito}_{nome}"), array)

print(f"\nFoto di incroci provate: {provate}")
print(f"  d'accordo con YOLO: {d_accordo}")
print(f"  diverse da YOLO:    {diverse}   <- controllatele una per una")
print(f"  indecise:           {indecise}   (incrocio troppo in alto/basso, storto o verde non trovato: decide YOLO)")
print(f"Foto disegnate in {uscita}")
