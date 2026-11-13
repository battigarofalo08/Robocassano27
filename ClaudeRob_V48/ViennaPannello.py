"""
ViennaPannello.py  -  [FIX 42] pannello di stato; [UI DOS] tema VGA/MS-DOS.

Non si lancia a mano: la apre ViennaMonitor.py quando parte RwdFoto.py (se PANNELLO = True in
ViennaDataConf.py e c'è uno schermo, per esempio in VNC). Gira in un processo separato, così:
  - si aggiorna 5 volte al secondo anche quando il robot è dentro una manovra lunga;
  - funziona sia lanciando da terminale sia da Thonny;
  - se la chiudete o si blocca, il robot non se ne accorge e continua.

Riceve lo stato del robot come righe JSON su stdin (le scrive ViennaMonitor).
Prova senza robot:  python3 ViennaPannello.py --prova   (salva pannello_prova.png)
"""
import base64
import json
import math
import sys
import threading
import time
import unicodedata

import cv2
import numpy as np

W, H = 960, 820        # parte "stato"; a sinistra si aggiungono le camere (COL_W)
NOME = "ROBOCASSANO27 - MS-DOS CONTROL"

# [UI DOS] palette VGA classica (OpenCV usa BGR): nero, blu, ciano, verde, giallo e rosso.
FONDO = (0, 0, 0)
RIQUADRO = (64, 0, 0)            # blu scuro
RIGA = (255, 255, 0)             # ciano
TESTO = (255, 255, 255)
TENUE = (170, 170, 170)
VERDE = (0, 255, 0)
GIALLO = (0, 255, 255)
ROSSO = (0, 0, 255)
AZZURRO = (255, 255, 0)
VIOLA = (255, 0, 255)
CATEGORIE = {"linea": VERDE, "incrocio": GIALLO, "ostacolo": VIOLA, "arena": AZZURRO,
             "gara": (230, 160, 120), "errore": ROSSO, "verde": VERDE, "sistema": TENUE, "info": TENUE}
NOMI_YOLO = {"Sx": "verde a SINISTRA", "Dx": "verde a DESTRA", "Fr": "DOPPIO verde", "Ln": "linea",
             "Bi": "bianco (linea persa)", "Di": "linea interrotta", "In": "striscia ARGENTO", "Ro": "linea ROSSA"}

F = cv2.FONT_HERSHEY_PLAIN


def ascii_(s):
    """I font di OpenCV non hanno le lettere accentate: e' al posto di è."""
    s = str(s).replace("°", " gr").replace("→", "->").replace("è", "e'").replace("à", "a'").replace("ù", "u'") \
        .replace("ò", "o'").replace("ì", "i'").replace("é", "e'")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


# [FIX 51] TESTI CON UN CARATTERE VERO. Il carattere di OpenCV ("a stecchini", senza accenti) da piccolo
# non si leggeva. Ora i testi si scrivono con DejaVu Sans (c'è già sul Raspberry) usando Pillow:
# scrivi() mette il testo in una lista e rendi_testi() li disegna tutti insieme alla fine.
# Se Pillow o il carattere mancano, si usa OpenCV come prima.
try:
    from PIL import Image, ImageDraw, ImageFont
    _CARTELLA_FONT = "/usr/share/fonts/truetype/dejavu/"
    ImageFont.truetype(_CARTELLA_FONT + "DejaVuSansMono.ttf", 14)
    PIL_OK = True
except Exception:
    PIL_OK = False
_font = {}
_testi = []           # (x, y, testo, scala, colore BGR, grassetto)
_ox = [0]             # spostamento orizzontale della parte "stato" (a sinistra ci sono le camere)


def _carattere(px, grassetto):
    k = (px, grassetto)
    if k not in _font:
        _font[k] = ImageFont.truetype(_CARTELLA_FONT + ("DejaVuSansMono-Bold.ttf" if grassetto else "DejaVuSansMono.ttf"), px)
    return _font[k]


def scrivi(img, testo, x, y, scala=0.5, col=TESTO, spess=1):
    if PIL_OK:
        _testi.append((int(x) + _ox[0], int(y), str(testo), scala, col, spess >= 2))
    else:
        cv2.putText(img, ascii_(testo), (int(x) + _ox[0], int(y)), F, scala, col, spess, cv2.LINE_AA)


def rendi_testi(img):
    """Disegna con Pillow tutti i testi raccolti da scrivi() (stessa posizione: x a sinistra, y = riga di base)."""
    if not PIL_OK or not _testi:
        _testi.clear()
        return img
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    for x, y, testo, scala, col, grassetto in _testi:
        px = max(14, int(round(29 * scala)))          # mai sotto 14 pixel
        d.text((x, y), testo, font=_carattere(px, grassetto), fill=(col[2], col[1], col[0]), anchor="ls")
    _testi.clear()
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def riquadro(img, x, y, w, h, titolo):
    cv2.rectangle(img, (x, y), (x + w, y + h), RIQUADRO, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), RIGA, 2)
    scrivi(img, "[ " + titolo.upper() + " ]", x + 10, y + 18, 0.42, AZZURRO, 2)


def barra(img, x, y, w, h, frazione, col):
    cv2.rectangle(img, (x, y), (x + w, y + h), (80, 0, 0), -1)
    fw = int(max(0.0, min(1.0, frazione)) * w)
    if fw > 0:
        cv2.rectangle(img, (x, y), (x + fw, y + h), col, -1)


def disegna(c, eventi, connesso=True, registro=None, tutti=True, pausa=False):
    img = np.full((H, W, 3), FONDO, np.uint8)
    if not c:
        scrivi(img, "In attesa dei dati del robot...", 30, 60, 0.8, TENUE, 2)
        return img
    cat = CATEGORIE.get(c.get("cat"), TENUE)
    # ---------- operazione in corso (grande) ----------
    cv2.rectangle(img, (0, 0), (W, 112), (128, 0, 0), -1)  # intestazione blu DOS
    cv2.rectangle(img, (0, 0), (10, 112), cat, -1)
    scrivi(img, "ROBOCASSANO27 // MS-DOS CONTROL PANEL", 190, 18, 0.58, AZZURRO, 2)
    m, s = divmod(max(c.get("t", 0), 0), 60)
    scrivi(img, f"{int(m):02d}:{s:04.1f}", 24, 30, 0.7, TENUE, 2)
    sw = c.get("sw")
    scrivi(img, "SWITCH ON" if sw else "SWITCH OFF", 24, 62, 0.6, VERDE if sw else ROSSO, 2)
    stato = c.get("stato", "")
    parti = stato.split(" > ")
    dettaglio = ""
    if len(parti) > 1 and parti[-1] in ("giro sul posto", "avanzo dritto"):
        dettaglio = parti.pop()                     # la manovra va sotto, in grande l'operazione vera
    principale = parti[-1] if parti else stato
    scrivi(img, principale, 190, 38, 1.0 if len(principale) < 34 else 0.8, cat, 2)
    sotto = " > ".join(parti[:-1])
    scrivi(img, sotto, 190, 64, 0.5, TENUE, 1)
    # [FIX 43] riga ORA: cosa fanno le ruote in questo istante (sempre visibile, anche durante le svolte)
    ora = c.get("manovra") or c.get("azione") or dettaglio
    scrivi(img, "ORA:", 24, 98, 0.65, GIALLO, 2)
    scrivi(img, ora, 90, 98, 0.72 if len(ora) < 52 else 0.6, GIALLO, 2)
    if c.get("manovra") and c.get("azione"):
        scrivi(img, "ruote: " + c["azione"], 620, 98, 0.45, TENUE, 1)
    if not connesso:
        scrivi(img, "NESSUN DATO DAL ROBOT", W - 300, 64, 0.55, ROSSO, 2)

    # ---------- laser ----------
    x0, y0 = 12, 122
    riquadro(img, x0, y0, 456, 128, "Laser VL53L1X (cm)")
    d = (c.get("d") or [0, 0, 0]) + [0, 0, 0]
    du = (c.get("d_ult") or [[0, 99]] * 3) + [[0, 99]] * 3
    if not c.get("ard", True):
        # [FIX 43] Arduino zitto: tutti i valori sono 0 finti, lo diciamo chiaro
        cv2.rectangle(img, (x0 + 10, y0 + 34), (x0 + 446, y0 + 118), (40, 40, 150), -1)
        scrivi(img, "ARDUINO ZITTO: switch spento?", x0 + 20, y0 + 70, 0.75, TESTO, 2)   # [FIX 104]
        scrivi(img, f"da {c.get('ard_muto', 0):.1f} s: laser e giroscopio NON validi", x0 + 60, y0 + 100, 0.5, TESTO, 1)
    else:
        for i, (nome, v) in enumerate(zip(("Sinistra", "Fronte", "Destra"), d[:3])):
            yy = y0 + 40 + i * 30
            scrivi(img, nome, x0 + 12, yy + 12, 0.55)
            col = ROSSO if 0 < v < 15 else GIALLO if 0 < v < 30 else VERDE
            uv, ue = du[i]
            if v:
                barra(img, x0 + 92, yy, 190, 16, v / 100.0, col)
                scrivi(img, "libero" if v >= 150 else f"{v:3d} cm", x0 + 294, yy + 14, 0.6, col, 2)
            else:
                # [FIX 43] laser fuori portata (o raggio troppo obliquo mentre gira): manda 0.
                # Non spariamo il dato: barra grigia con l'ultimo valore buono e da quanto tempo.
                barra(img, x0 + 92, yy, 190, 16, (uv / 100.0) if ue < 5 else 0, RIGA)
                scrivi(img, "fuori portata", x0 + 294, yy + 6, 0.42, TENUE, 1)
                if uv and ue < 5:
                    scrivi(img, f"era {uv} cm, {ue:.1f} s fa", x0 + 294, yy + 20, 0.38, TENUE, 1)
            cv2.line(img, (x0 + 92 + int(0.15 * 190), yy - 3), (x0 + 92 + int(0.15 * 190), yy + 19), ROSSO, 1)

    # ---------- assetto ----------
    x1 = 480
    riquadro(img, x1, y0, 468, 128, "Giroscopio")
    if not c.get("ard", True):
        scrivi(img, "NON VALIDO", x1 + 300, y0 + 24, 0.5, ROSSO, 2)
    becc, roll, rotta = ((c.get("imu") or [0, 0, 0]) + [0, 0, 0])[:3]
    cx, cy, r = x1 + 70, y0 + 80, 36
    cv2.circle(img, (cx, cy), r, RIGA, 2)
    for a, lab in ((0, "0"), (90, "90"), (180, "180"), (270, "270")):
        ax, ay = cx + (r + 10) * math.sin(math.radians(a)), cy - (r + 10) * math.cos(math.radians(a))
        scrivi(img, lab, ax - 8, ay + 4, 0.32, TENUE)
    ax, ay = cx + (r - 6) * math.sin(math.radians(rotta)), cy - (r - 6) * math.cos(math.radians(rotta))
    cv2.arrowedLine(img, (cx, cy), (int(ax), int(ay)), GIALLO, 3, cv2.LINE_AA, tipLength=0.3)
    scrivi(img, f"rotta {rotta:.0f} gr", x1 + 140, y0 + 44, 0.7, TESTO, 2)
    scrivi(img, f"beccheggio {becc:+.0f} gr", x1 + 140, y0 + 68, 0.5)
    scrivi(img, f"rollio {roll:+.0f} gr     tilt {c.get('tilt')}", x1 + 140, y0 + 90, 0.5)
    # [FIX 82] il tratto inclinato capito dal giroscopio (mediana di mezzo secondo, con due soglie)
    p = c.get("pend") or {}
    if p:
        piano = p.get("tipo") == "piano"
        scrivi(img, p.get("testo", "").upper() if piano else p.get("testo", ""), x1 + 140, y0 + 116,
               0.55 if piano else 0.5, VERDE if piano else GIALLO, 2)

    # ---------- YOLO ----------
    y1 = 262
    riquadro(img, x0, y1, 300, 150, "YOLO camera linea")
    cls, conf = ((c.get("yolo") or [None, 0]) + [None, 0])[:2]
    scrivi(img, cls or "--", x0 + 14, y1 + 78, 1.6, GIALLO if cls in ("Sx", "Dx", "Fr") else TESTO, 3)
    scrivi(img, NOMI_YOLO.get(cls, "nessuna decisione") if cls else "nessuna decisione", x0 + 110, y1 + 52, 0.5)
    barra(img, x0 + 110, y1 + 64, 170, 10, conf or 0, GIALLO)
    scrivi(img, f"{c.get('dec_s', 0):.1f} decisioni/s", x0 + 110, y1 + 96, 0.5, TENUE)
    scrivi(img, f"camera {c.get('fps', 0):.1f} fps", x0 + 110, y1 + 118, 0.5, TENUE)
    if c.get("verde"):
        scrivi(img, "verde: " + c["verde"][:40], x0 + 12, y1 + 142, 0.4, VERDE)

    # ---------- motori ----------
    riquadro(img, x0 + 312, y1, 312, 150, "Motori, braccio, LED")
    cmd, vel, sterzo = ((c.get("mot") or ["Stop", 0, 0]) + ["Stop", 0, 0])[:3]
    scrivi(img, {"Stop": "FERMO", "Dritto": "DRITTO col giroscopio"}.get(cmd, "STERZO"), x0 + 324, y1 + 46, 0.6, TESTO, 2)
    scrivi(img, f"vel {vel:.0f}   sterzo {sterzo:+.0f}", x0 + 324, y1 + 72, 0.55)
    bx, bw = x0 + 324, 280
    cv2.rectangle(img, (bx, y1 + 82), (bx + bw, y1 + 94), (80, 0, 0), -1)
    mid = bx + bw // 2
    sx = int(max(-100, min(100, sterzo or 0)) / 100 * bw / 2)
    cv2.rectangle(img, (min(mid, mid + sx), y1 + 82), (max(mid, mid + sx), y1 + 94), GIALLO, -1)
    cv2.line(img, (mid, y1 + 78), (mid, y1 + 98), TENUE, 1)
    br, pz = c.get("br"), c.get("pz")
    scrivi(img, f"braccio {br if br is not None else '-'} gr   pinza {pz if pz is not None else '-'} gr", x0 + 324, y1 + 118, 0.5)
    led = c.get("led") or [False, False]
    scrivi(img, "LED", x0 + 324, y1 + 141, 0.5, TENUE)
    for k, on in enumerate(led[:2]):
        cv2.circle(img, (x0 + 372 + k * 22, y1 + 136), 7, (250, 240, 220) if on else (70, 62, 55), -1)

    # ---------- raspberry / gara ----------
    riquadro(img, x0 + 636, y1, 300, 150, "Raspberry, batteria, gara")
    p = c.get("pi") or {}
    t = p.get("cpu_temp")
    scrivi(img, f"CPU {t:.0f} gr C" if t is not None else "CPU -", x0 + 648, y1 + 44, 0.55,
           ROSSO if (t or 0) > 80 else GIALLO if (t or 0) > 70 else TESTO)
    v5 = p.get("v5")
    scrivi(img, f"5V {v5:.2f} V" if v5 else "5V -", x0 + 790, y1 + 44, 0.55,
           ROSSO if v5 and v5 < 4.8 else GIALLO if v5 and v5 < 4.95 else TESTO)
    if p.get("sottotensione"):
        scrivi(img, "SOTTOTENSIONE ADESSO", x0 + 648, y1 + 70, 0.55, ROSSO, 2)
    elif p.get("sottotensione_avvenuta"):
        scrivi(img, "fulmine visto dall'avvio", x0 + 648, y1 + 70, 0.5, GIALLO)
    else:
        scrivi(img, "alimentazione OK", x0 + 648, y1 + 70, 0.5, VERDE)
    bv = p.get("batt_v")
    scrivi(img, f"LiPo {bv:.2f} V  {p.get('batt_pct')}%" if bv else "LiPo non misurata", x0 + 648, y1 + 96, 0.5)
    pal = c.get("pal") or [0, 0]
    scrivi(img, f"palline: argento {pal[0]}   nera {pal[1]}", x0 + 648, y1 + 122, 0.5)
    if c.get("arena"):
        scrivi(img, c["arena"][:38], x0 + 648, y1 + 142, 0.38, AZZURRO)

    # ---------- eventi ----------
    # [FIX 47] TUTTI gli eventi in tempo reale: ogni print del programma (in grigio) e gli eventi
    # importanti tradotti (a colori). Il più recente è in alto.
    #   t = solo importanti / tutti     spazio = pausa (la lista si ferma per leggerla)
    y2 = 424
    alto = H - y2 - 10
    modo = "TUTTI" if tutti else "SOLO IMPORTANTI"
    riquadro(img, x0, y2, 936, alto, f"Eventi in tempo reale - {modo}   (t = cambia, spazio = pausa, m = maschera nero)")
    if pausa:
        scrivi(img, "IN PAUSA (spazio per ripartire)", x0 + 640, y2 + 18, 0.45, GIALLO, 2)
    righe = registro if (tutti and registro) else [dict(e, imp=True) for e in eventi]
    if not tutti:
        righe = [r for r in righe if r.get("imp", True)]
    n_righe = (alto - 34) // 20
    for k, e in enumerate(list(righe)[-n_righe:][::-1]):
        yy = y2 + 42 + k * 20
        em, es = divmod(max(e.get("t", 0), 0), 60)
        imp = e.get("imp", True)
        scrivi(img, f"{int(em):02d}:{es:04.1f}", x0 + 12, yy, 0.42, TENUE)
        col = CATEGORIE.get(e.get("cat"), TESTO) if imp else (175, 170, 165)   # [FIX 51] prima (125, 118, 110)
        scrivi(img, e.get("testo", "")[:105], x0 + 86, yy, 0.5 if imp else 0.46, col, 1)
    return img


# ---------- [FIX 51] colonna di sinistra: le due camere ----------
CAM_W, CAM_H, COL_W = 320, 189, 340
_cam = {"linea": None, "arena": None}       # ultimo fotogramma ricevuto (già decodificato)


def _decodifica(b64):
    try:
        buf = np.frombuffer(base64.b64decode(b64), np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _maschera_nero(img, soglia):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 150, soglia]))
    return cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)


def colonna_camere(cam, maschera=False):
    col = np.full((H, COL_W, 3), FONDO, np.uint8)
    cam = cam or {}
    for chiave in ("linea", "arena"):
        if cam.get(chiave):
            im = _decodifica(cam[chiave])
            if im is not None:
                _cam[chiave] = im
    voci = (("linea", "CAMERA LINEA", 10, cam.get("linea_eta")),
            ("arena", "CAMERA ARENA", 10 + CAM_H + 62, cam.get("arena_eta")))
    for chiave, titolo, y, eta in voci:
        riquadro(col, 8, y, COL_W - 16, CAM_H + 52, titolo)
        im = _cam[chiave]
        x0c, y0c = 10 + (COL_W - 20 - CAM_W) // 2, y + 30
        if im is not None:
            vista = _maschera_nero(im, cam.get("soglia", 110)) if (maschera and chiave == "linea") else im
            col[y0c:y0c + CAM_H, x0c:x0c + CAM_W] = cv2.resize(vista, (CAM_W, CAM_H))
        else:
            scrivi(col, "nessuna immagine", x0c + 90, y0c + 95, 0.5, TENUE)
        # da quanto tempo non arriva un fotogramma nuovo
        if eta is None:
            testo, colore = "", TENUE
        elif eta < 1.0:
            testo, colore = "dal vivo", VERDE
        elif chiave == "arena":
            testo, colore = f"ultima immagine {eta:.0f} s fa (si usa in arena)", TENUE
        else:
            testo, colore = f"FERMA da {eta:.1f} s", ROSSO
        if eta is not None and eta >= 1.0 and chiave == "linea":
            cv2.rectangle(col, (x0c - 2, y0c - 2), (x0c + CAM_W + 1, y0c + CAM_H + 1), ROSSO, 2)
        scrivi(col, testo, 18, y + CAM_H + 46, 0.42, colore, 1)
        if maschera and chiave == "linea":
            scrivi(col, f"maschera nero ({cam.get('soglia', 110)})", 165, y + 18, 0.42, GIALLO)
    # tasti
    yk = 10 + 2 * (CAM_H + 62) + 10
    riquadro(col, 8, yk, COL_W - 16, 120, "Tasti (con questa finestra selezionata)")
    for i, t in enumerate(("t   tutti gli eventi / solo importanti", "spazio   pausa degli eventi",
                           "m   maschera del nero sulla camera linea", "q   chiude la finestra (il robot continua)")):
        scrivi(col, t, 20, yk + 44 + i * 22, 0.44, TESTO)
    return col


def componi(c, eventi, connesso, registro, tutti, pausa, cam, maschera):
    """Finestra completa: camere a sinistra, stato a destra; poi tutti i testi in una volta."""
    _testi.clear()
    _ox[0] = 0
    sinistra = colonna_camere(cam, maschera)
    _ox[0] = COL_W
    destra = disegna(c, eventi, connesso, registro, tutti, pausa)
    _ox[0] = 0
    return rendi_testi(np.hstack([sinistra, destra]))


def main():
    if "--prova" in sys.argv:
        c = {"t": 83.4, "stato": "Seguilinea > Incrocio: giro a DESTRA > giro sul posto", "cat": "incrocio",
             "manovra": "giro a DESTRA di 75 gr: fatti 41", "azione": "ruoto SUL POSTO verso DESTRA (vel 47)",
             "d": [42, 0, 200], "d_ult": [[42, 0], [31, 0.4], [200, 0]], "ard": True,
             "sw": True, "imu": [2, -23, 182], "tilt": [0, 0],
             "pend": {"tipo": "di lato", "testo": "INCLINATO verso sinistra 23 gradi (da 6 s)", "becc": 2, "roll": -23},
             "mot": ["Sterzo", 47, 100], "br": 40, "pz": 160, "led": [True, True], "yolo": ["Dx", 0.91],
             "verde": "", "arena": "", "dec_s": 11.5, "fps": 24.0, "pal": [0, 0], "msg": "IA Incrocio Dx 0.91",
             "pi": {"cpu_temp": 63.2, "v5": 5.06, "sottotensione": False, "sottotensione_avvenuta": True}}
        ev = [{"t": 75.1, "cat": "ostacolo", "testo": "Ostacolo superato"},
              {"t": 81.2, "cat": "incrocio", "testo": "Incrocio con verde a DESTRA -> giro a destra  (sicurezza 0.91)"},
              {"t": 82.0, "cat": "incrocio", "testo": "Incrocio: velocita' 16 cm/s, ruote sopra l'incrocio"}]
        reg = []
        for k in range(10):
            reg += [{"t": 79.0 + k * 0.07, "cat": "grezzo", "testo": t, "imp": False} for t in ("Alto", f"Basso {k * 3 - 12}")]
        reg += [dict(ev[1], imp=True), {"t": 81.3, "cat": "grezzo", "testo": "distanze (42, 31, 200) Posizione (4, -1, 182)", "imp": False},
                dict(ev[2], imp=True)]
        cam = {"linea_eta": 0.2, "arena_eta": 12.0, "soglia": 110}
        for chiave, nome in (("linea", "prova_linea.jpg"), ("arena", "prova_arena.jpg")):
            im = cv2.imread(nome)
            if im is not None:
                cam[chiave] = base64.b64encode(cv2.imencode(".jpg", cv2.resize(im, (CAM_W, CAM_H)))[1].tobytes()).decode()
        cv2.imwrite("pannello_prova.png", componi(c, ev, True, reg, True, False, cam, "--maschera" in sys.argv))
        return
    stato = {"c": {}, "eventi": [], "registro": [], "cam": {}, "t": 0.0, "fine": False}

    def leggi():
        for riga in sys.stdin:
            try:
                d = json.loads(riga)
                stato["c"] = d.get("c", {})
                stato["eventi"] = d.get("eventi", [])
                stato["registro"] = d.get("registro", [])
                stato["cam"] = d.get("cam", {})
                stato["t"] = time.time()
            except Exception:
                pass
        stato["fine"] = True
    threading.Thread(target=leggi, daemon=True).start()
    cv2.namedWindow(NOME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(NOME, W + COL_W, H)
    cv2.setWindowTitle(NOME, NOME + " // VGA 16 COLORI")
    tutti, pausa, maschera = True, False, False
    fermo = {}
    while not stato["fine"]:
        if not pausa:
            fermo = {"eventi": list(stato["eventi"]), "registro": list(stato["registro"])}
        cv2.imshow(NOME, componi(stato["c"], fermo.get("eventi", []), time.time() - stato["t"] < 2.0,
                                 fermo.get("registro", []), tutti, pausa, stato["cam"], maschera))
        stato["cam"] = {k_: v for k_, v in stato["cam"].items() if not k_ in ("linea", "arena")}   # immagini già usate
        k = cv2.waitKey(100) & 0xFF
        if k in (ord('m'), ord('M')):
            maschera = not maschera      # [FIX 51] mostra cosa il robot considera NERO
        if k == ord('q'):
            break
        if k in (ord('t'), ord('T')):
            tutti = not tutti            # [FIX 47] tutti gli eventi / solo importanti
        if k == ord(' '):
            pausa = not pausa            # [FIX 47] ferma la lista per leggerla (i sensori continuano)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
