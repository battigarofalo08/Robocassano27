"""
ViennaCabina.py  -  [FIX 107] il terminale "CABINA DI PILOTAGGIO" del robot.

Una schermata fissa a riquadri che si ridisegna 5 volte al secondo (al posto delle 8 righe del pannello):
  testata (versione, switch, CPU, alimentazione), fascia colorata della FASE e riga "ORA",
  LASER visti dall'alto, ASSETTO (bussola, beccheggio, rollio, pendenza, storia di 20 s), CRONOMETRO,
  CAMERA LINEA e CAMERA ARENA in piccolo (mezzi blocchi colorati), MOTORI E PINZA, LA GARA (fasi con i tempi),
  EVENTI (il più recente in alto).

Non tocca il robot: riceve il campione che ViennaMonitor registra anche nella scatola nera e restituisce le righe
da stampare. Per questo la stessa schermata serve anche a rivedere una scatola nera sul Mac
(Strumenti_prove_Claude/terminale_nuovo.py, la "moviola").
Si sceglie in ViennaDataConf.py: TERMINALE = "cabina". Serve una finestra di almeno 100 x 38 caratteri
(in VNC: ingrandite il terminale); se è più piccola il monitor torna da solo al "pannello" di prima.
"""
import re
import time

try:
    import cv2
    import numpy as np
except Exception:                       # senza OpenCV la cabina funziona lo stesso, senza camere
    cv2 = np = None

COLONNE_MIN, RIGHE_MIN = 100, 38

# ---------------------------------------------------------------------------------------------
#  colori (256 colori: terminale del Raspberry, VNC, Terminale del Mac)
# ---------------------------------------------------------------------------------------------
R = "\033[0m"
B = "\033[1m"


def fg(n):
    return f"\033[38;5;{n}m"


def bg(n):
    return f"\033[48;5;{n}m"


DIM, TESTO, CORNICE, TITOLO = fg(244), fg(253), fg(67), fg(117)
VERDE, GIALLO, ARANCIO, ROSSO, AZZURRO, VIOLA, BIANCO = fg(78), fg(220), fg(208), fg(203), fg(81), fg(177), fg(255)
FASI = [("SEGUILINEA", 29), ("INGRESSO", 31), ("VITTIME", 25), ("USCITA", 97), ("ALTALENA", 130), ("ARRIVO", 160)]
NOMI_FASI = [f[0] for f in FASI]
COL_CAT = {"linea": VERDE, "incrocio": GIALLO, "ostacolo": VIOLA, "arena": AZZURRO, "gara": fg(147),
           "errore": ROSSO, "verde": VERDE, "sistema": DIM, "info": DIM}
ICONA_CAT = {"linea": "━", "incrocio": "◆", "ostacolo": "■", "arena": "◉", "gara": "★", "errore": "✖",
             "verde": "▶", "sistema": "·", "info": "·"}
NOMI_YOLO = {"Sx": ("VERDE A SINISTRA", VERDE), "Dx": ("VERDE A DESTRA", VERDE), "Fr": ("DOPPIO VERDE", VERDE),
             "Ln": ("LINEA", BIANCO), "Bi": ("BIANCO: persa", GIALLO), "Di": ("INTERROTTA", GIALLO),
             "In": ("ARGENTO", fg(250)), "Ro": ("LINEA ROSSA", ROSSO), "No": ("niente", DIM)}
SPARK = "▁▂▃▄▅▆▇█"
_ANSI = re.compile(r"\033\[[0-9;]*m")

# cifre grandi del cronometro (3 righe)
CIFRE = {
    "0": ["█▀█", "█ █", "▀▀▀"], "1": [" ▀█", "  █", "  ▀"], "2": ["▀▀█", "█▀▀", "▀▀▀"], "3": ["▀▀█", " ▀█", "▀▀▀"],
    "4": ["█ █", "▀▀█", "  ▀"], "5": ["█▀▀", "▀▀█", "▀▀▀"], "6": ["█▀▀", "█▀█", "▀▀▀"], "7": ["▀▀█", "  █", "  ▀"],
    "8": ["█▀█", "█▀█", "▀▀▀"], "9": ["█▀█", "▀▀█", "▀▀▀"], ":": [" ", "▀", "▀"], ".": [" ", " ", "▄"],
}


def vis(s):
    """Lunghezza visibile di una riga (senza i codici colore)."""
    return len(_ANSI.sub("", s))


def pad(s, n):
    """Allunga o taglia una riga a n caratteri visibili."""
    v = vis(s)
    if v <= n:
        return s + " " * (n - v)
    out, k, i = [], 0, 0
    while i < len(s) and k < n:
        m = _ANSI.match(s, i)
        if m:
            out.append(m.group())
            i = m.end()
            continue
        out.append(s[i])
        k += 1
        i += 1
    return "".join(out) + R


def scatola(titolo, righe, larg, alt=None, colore=CORNICE):
    """Riquadro con angoli arrotondati e il titolo nel bordo; alt = righe interne (si riempie con righe vuote)."""
    righe = list(righe)
    if alt is not None:
        righe = (righe + [""] * alt)[:alt]
    t = f" {titolo} " if titolo else ""
    su = colore + "╭─" + TITOLO + B + t + R + colore + "─" * max(0, larg - 3 - vis(t)) + "╮" + R
    giu = colore + "╰" + "─" * (larg - 2) + "╯" + R
    return [su] + [colore + "│" + R + pad(r, larg - 2) + colore + "│" + R for r in righe] + [giu]


def affianca(*blocchi):
    alt = max(len(b) for b in blocchi)
    out = []
    for i in range(alt):
        out.append("".join(b[i] if i < len(b) else " " * vis(b[0][0]) for b in blocchi))
    return out


def col_dist(d):
    if not d:
        return DIM
    return ROSSO if d < 15 else (GIALLO if d < 30 else VERDE)


def barra_centro(v, vmax, larg, colore):
    """Barra con lo zero in mezzo: a sinistra i valori negativi, a destra i positivi."""
    m = larg // 2
    n = int(round(max(-1.0, min(1.0, (v or 0) / vmax)) * m))
    s = [DIM + "·" + R] * larg
    s[m] = fg(250) + "┼" + R
    for i in range(min(m, m + n), max(m, m + n) + (0 if n == 0 else 1)):
        if i != m and 0 <= i < larg:
            s[i] = colore + "█" + R
    return "".join(s)


def spark(valori, vmin, vmax, n):
    v = [x for x in valori if x is not None]
    if not v:
        return DIM + "·" * n + R
    if len(v) > n:                              # tutta la storia (20 s) in n caratteri
        v = [v[int(i * len(v) / n)] for i in range(n)]
    out = "".join(SPARK[int((max(vmin, min(vmax, x)) - vmin) / (vmax - vmin + 1e-9) * 7.999)] for x in v)
    return AZZURRO + out.rjust(n, " ") + R


# ---------------------------------------------------------------------------------------------
#  CAMERE in piccolo: ogni carattere "▀" mostra due pixel (sopra il colore del testo, sotto lo sfondo)
# ---------------------------------------------------------------------------------------------
def _c256(b, g, r):
    """Colore BGR -> indice dei 256 colori del terminale (cubo 6x6x6 o scala di grigi)."""
    if max(int(r), int(g), int(b)) - min(int(r), int(g), int(b)) < 28:   # poco colorato: scala di grigi (24 toni)
        v = (int(r) + int(g) + int(b)) / 3
        if v < 8:
            return 16
        if v > 246:
            return 231
        return 232 + int((v - 8) / 247 * 24)
    q = lambda x: int(round(int(x) / 255 * 5))
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


def miniatura(img, larg, alt):
    """Immagine (BGR o BGRA) -> 'alt' righe di 'larg' caratteri a mezzi blocchi. None se non c'è l'immagine."""
    if img is None or cv2 is None:
        return None
    try:
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        piccola = cv2.resize(img, (larg, alt * 2), interpolation=cv2.INTER_AREA)
        righe = []
        for y in range(alt):
            s, prima = [], None
            for x in range(larg):
                a, b = piccola[2 * y, x], piccola[2 * y + 1, x]
                cod = f"\033[38;5;{_c256(*a)};48;5;{_c256(*b)}m"
                s.append(("" if cod == prima else cod) + "▀")
                prima = cod
            righe.append("".join(s) + R)
        return righe
    except Exception:
        return None


def da_jpeg_base64(testo):
    """Miniatura della scatola nera (JPEG in base64) -> immagine BGR."""
    if not testo or cv2 is None:
        return None
    try:
        import base64
        buf = np.frombuffer(base64.b64decode(testo), np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------
#  CRONOMETRO: parte quando si accende lo switch, non si azzera con le LoP
# ---------------------------------------------------------------------------------------------
class Cronometro:
    def __init__(self, durata=480.0, nuova_gara_dopo=120.0):
        self.durata = durata                    # 8 minuti di gara (regolamento)
        self.nuova_gara_dopo = nuova_gara_dopo  # switch spento più di così: la prossima accensione è una gara nuova
        self.azzera()

    def azzera(self):
        self.inizio = None                      # prima accensione dello switch
        self.ripartenza = None                  # ultima accensione (dopo una LoP)
        self.spento_da = None
        self.lop = 0
        self.sw = False

    def aggiorna(self, sw, t):
        if sw and not self.sw:                                   # switch appena acceso
            if self.inizio is None or (self.spento_da is not None and t - self.spento_da > self.nuova_gara_dopo):
                self.azzera()
                self.inizio = t
            else:
                self.lop += 1                                    # si riparte dopo una LoP
            self.ripartenza = t
            self.spento_da = None
        elif not sw and self.sw:
            self.spento_da = t
        self.sw = sw

    def tempi(self, t):
        if self.inizio is None:
            return None
        return {"gara": t - self.inizio, "tratto": (t - self.ripartenza) if self.sw else None,
                "spento": (t - self.spento_da) if self.spento_da is not None else None,
                "mancano": self.durata - (t - self.inizio), "lop": self.lop}


def cifre_grandi(testo, colore):
    righe = ["", "", ""]
    for ch in testo:
        g = CIFRE.get(ch, ["   "] * 3)
        for i in range(3):
            righe[i] += g[i] + " "
    return [colore + B + r + R for r in righe]


def riquadro_crono(tm, larg, alt):
    if tm is None:
        righe = ["", f"  {GIALLO}{B}PRONTO{R}", f"  {DIM}il cronometro parte quando{R}", f"  {DIM}accendete lo switch{R}"]
        return scatola("CRONOMETRO", righe, larg, alt)
    g = max(0.0, tm["gara"])
    m, s = divmod(g, 60)
    mancano = tm["mancano"]
    col = ROSSO if mancano <= 0 else (GIALLO if mancano <= 60 else BIANCO)
    big = cifre_grandi(f"{int(m)}:{int(s):02d}.{int((s % 1) * 10)}", col)
    if mancano > 0:
        mm, ms = divmod(mancano, 60)
        manca = f"{col}mancano {int(mm)}:{int(ms):02d} agli 8 minuti{R}"
    else:
        manca = f"{bg(160)}{BIANCO}{B} 8 MINUTI FINITI {R}"
    if tm["tratto"] is not None:
        tr = f"{DIM}dall'ultima partenza{R} {int(tm['tratto'] // 60)}:{int(tm['tratto'] % 60):02d}"
    else:
        tr = f"{ARANCIO}{B}switch spento da {tm['spento'] or 0:.0f} s{R}"
    lop = f"{DIM}LoP{R} {B}{tm['lop']}{R}"
    righe = [""] + ["  " + r for r in big] + ["", f"  {manca}", f"  {tr}   {lop}"]
    return scatola("CRONOMETRO", righe, larg, alt)


# ---------------------------------------------------------------------------------------------
#  FASI DELLA GARA: vanno solo avanti (dopo l'uscita il seguilinea è il tratto finale con l'altalena)
# ---------------------------------------------------------------------------------------------
def fase_di(c):
    s = (c.get("stato") or "").upper()
    cat = c.get("cat")
    if "ROSSA" in s or "ARRIVO" in s:
        return "ARRIVO"
    if "ALTALENA" in s:
        return "ALTALENA"
    if "USCITA" in s or "USCIRE" in s:
        return "USCITA"
    if "INGRESSO" in s or "ENTRA" in s:
        return "INGRESSO"
    if cat == "arena" or "ARENA" in s or "PALLIN" in s:
        return "VITTIME"
    return "SEGUILINEA"


class Fasi:
    """Una fase conta solo se dura almeno 3 s di fila (un riflesso argento di mezzo secondo non è l'ingresso)."""

    def __init__(self):
        self.azzera()

    def azzera(self, t=None):
        self.k = 0
        self.inizio = {"SEGUILINEA": t} if t is not None else {}
        self.cand, self.cand_t = None, 0.0

    def aggiorna(self, c, t=None):
        t = c.get("t", 0) if t is None else t
        if not self.inizio:
            self.inizio["SEGUILINEA"] = t
        f = fase_di(c)
        j = NOMI_FASI.index(f)
        if self.k >= NOMI_FASI.index("USCITA") and f == "SEGUILINEA":
            j = NOMI_FASI.index("ALTALENA")
        if j <= self.k:
            self.cand = None
            return
        if self.cand != j:
            self.cand, self.cand_t = j, t
        if t - self.cand_t >= 3.0:
            self.k = j
            self.inizio.setdefault(NOMI_FASI[j], self.cand_t)
            self.cand = None

    def evento(self, testo, t):
        u = testo.upper()
        if "LINEA ROSSA" in u or "ARRIVO" in u:
            self.k = NOMI_FASI.index("ARRIVO")
            self.inizio.setdefault("ARRIVO", t)

    def adesso(self):
        return NOMI_FASI[self.k]

    def durate(self):
        ordine = sorted(self.inizio.items(), key=lambda kv: kv[1])
        return {f: ordine[i + 1][1] - t0 for i, (f, t0) in enumerate(ordine[:-1])}


# ---------------------------------------------------------------------------------------------
#  i riquadri
# ---------------------------------------------------------------------------------------------
def riquadro_laser(c, larg, alt):
    """Il robot visto dall'alto con i tre laser: più il raggio è lungo, più c'è spazio."""
    d = list(c.get("d") or [0, 0, 0]) + [0, 0, 0]
    W = larg - 2
    if not c.get("ard", True):
        righe = ["", "", bg(160) + BIANCO + B + pad("  ARDUINO ZITTO", W) + R,
                 bg(160) + BIANCO + pad(f"  da {c.get('ard_muto', 0):.1f} s: switch spento?", W) + R,
                 bg(160) + BIANCO + pad("  laser e giroscopio NON validi", W) + R]
        return scatola("LASER", righe, larg, alt)
    H = alt
    g = [[" "] * W for _ in range(H)]
    cx, cy = W // 2, H - 3
    for dx, ch in ((-2, "▐"), (-1, "█"), (0, "▲"), (1, "█"), (2, "▌")):
        g[cy][cx + dx] = fg(208) + B + ch + R
    g[cy + 1][cx - 1] = fg(240) + "▀" + R
    g[cy + 1][cx + 1] = fg(240) + "▀" + R
    passo = 60.0 / max(1, cy - 1)                     # davanti: fino a 60 cm
    n = min(cy - 1, int(round(d[1] / passo))) if d[1] else cy - 1
    for k in range(1, n + 1):
        g[cy - k][cx] = col_dist(d[1]) + ("┃" if d[1] else "┆") + R
    if d[1] and n < cy - 1:
        g[cy - n - 1][cx] = col_dist(d[1]) + B + "▬" + R
    for lato, i in ((-1, 0), (1, 2)):                # ai lati: 5 cm per carattere
        n = min(cx - 3, int(round(d[i] / 5))) if d[i] else cx - 3
        for k in range(3, 3 + n):
            g[cy][cx + lato * k] = col_dist(d[i]) + ("━" if d[i] else "┄") + R
        if d[i] and 3 + n < cx:
            g[cy][cx + lato * (3 + n)] = col_dist(d[i]) + B + ("▌" if lato < 0 else "▐") + R
    righe = ["".join(r) for r in g]

    def num(v):
        return (col_dist(v) + B + f"{v} cm" + R) if v else (DIM + "libero" + R)
    fronte = "Fronte " + num(d[1])
    righe[0] = " " * max(0, (W - vis(fronte)) // 2) + fronte
    sx, dx = "Sx " + num(d[0]), "Dx " + num(d[2])
    righe[H - 1] = sx + " " * max(1, W - vis(sx) - vis(dx)) + dx
    return scatola("LASER", righe, larg, alt)


def riquadro_assetto(c, storia, larg, alt):
    b, ro, rt = (list(c.get("imu") or []) + [0, 0, 0])[:3]
    rt = c.get("rotta", rt) or 0
    p = c.get("pend") or {}
    inclinato = p.get("tipo") not in (None, "piano", "sconosciuto")
    freccia = "↑↗→↘↓↙←↖"[int((rt + 22.5) // 45) % 8]
    n = larg - 15
    righe = [
        f" {AZZURRO}{B}{freccia}{R}  rotta {B}{rt:4.0f}°{R}  {DIM}{(c.get('bus') or '')[:larg - 19]}{R}",
        f" becc {barra_centro(b, 30, 13, GIALLO if abs(b) > 8 else VERDE)} {b:+3.0f}°",
        f" roll {barra_centro(ro, 30, 13, GIALLO if abs(ro) > 8 else VERDE)} {ro:+3.0f}°",
        (bg(136) + fg(16) + B + pad(" " + (p.get("testo") or "").upper(), larg - 4) + R) if inclinato
        else f" {VERDE}{(p.get('testo') or '').upper()}{R}",
        "",
        f" {DIM}rotta 20s{R} " + spark([s.get("rotta") for s in storia], 0, 360, n),
        f" {DIM}becc. 20s{R} " + spark([(s.get("imu") or [0])[0] for s in storia], -25, 25, n),
    ]
    return scatola("ASSETTO", righe, larg, alt)


def riquadro_camera(titolo, img, testo, larg, alt, eta=None):
    """Camera in piccolo a sinistra e due-tre righe di spiegazione a destra."""
    w_img = min(larg - 20, int(alt * 2 * 1.7))       # le camere sono 440 x 260 circa
    mini = miniatura(img, w_img, alt) if img is not None else None
    if mini is None:
        mini = [DIM + pad("", w_img) + R] * alt
        mini[alt // 2] = DIM + pad("   nessuna immagine", w_img) + R
    vecchia = eta is not None and eta > 2.0
    destra = list(testo) + ([""] * alt)
    if vecchia:
        destra[alt - 1] = f"{ARANCIO}ferma da {eta:.0f} s{R}"
    righe = [" " + mini[i] + "  " + destra[i] for i in range(alt)]
    return scatola(titolo, righe, larg, alt)


def riquadro_motori(c, larg):
    m = list(c.get("mot") or ["Stop", 0, 0]) + [0, 0]
    cmd, vel, st = m[0], m[1] or 0, m[2] or 0
    sx, dx = vel + st, vel - st              # come vanno le due ruote, a occhio

    def ruota(nome, v):
        col = VERDE if v > 0 else (ARANCIO if v < 0 else DIM)
        return f"{nome} {barra_centro(v, 100, 17, col)} {col}{int(v):+4d}{R}"
    led = c.get("led") or [False, False]
    pal = list(c.get("pal") or [0, 0]) + [0, 0]
    br, pz = c.get("br"), c.get("pz")
    pinza = "-" if pz is None else ("chiusa" if pz < 110 else "aperta")
    vittime = (fg(250) + "●" * pal[0] + R) + (fg(240) + "●" * pal[1] + R) + DIM + "○" * max(0, 3 - pal[0] - pal[1]) + R
    r1 = f" {ruota('SX', sx)}   {ruota('DX', dx)}   {DIM}{cmd}{R}"
    r2 = (f" braccio {B}{br if br is not None else '-'}°{R}   pinza {B}{pinza}{R}   "
          f"luci {''.join((GIALLO + '●' if l else DIM + '○') + R for l in led)}   vittime salvate {vittime}")
    return scatola("MOTORI E PINZA", [r1, r2], larg)


def riquadro_gara(adesso, durate, larg):
    """La gara come una linea della metropolitana: fasi fatte (con il tempo), quella di adesso accesa."""
    pezzi = []
    for nome, sf in FASI:
        if nome == adesso:
            pezzi.append(bg(sf) + BIANCO + B + f" ◉ {nome} " + R)
        elif nome in durate:
            pezzi.append(VERDE + "● " + R + fg(250) + nome.lower() + DIM + f" {durate[nome]:.0f}s" + R)
        else:
            pezzi.append(DIM + "○ " + nome.lower() + R)
    return scatola("LA GARA", [" " + (DIM + " ── " + R).join(pezzi)], larg)


# ---------------------------------------------------------------------------------------------
#  la schermata intera
# ---------------------------------------------------------------------------------------------
def schermo(c, storia, eventi, fase, durate, versione, crono=None, cam_linea=None, cam_arena=None,
            eta_linea=None, eta_arena=None, colonne=100, righe_tot=40):
    """Restituisce le righe (con i colori) di tutta la schermata. c = campione come nella scatola nera."""
    L = max(COLONNE_MIN, colonne)
    pi = c.get("pi") if isinstance(c.get("pi"), dict) else {}
    sw = (VERDE + B + "● SWITCH ON" + R) if c.get("sw") else (ROSSO + B + "○ SWITCH OFF" + R)
    temp = pi.get("cpu_temp")
    temp_s = (ROSSO if temp and temp > 75 else TESTO) + (f"{temp:.0f}°C" if temp else "-") + R
    alim = (bg(160) + BIANCO + B + " SOTTOTENSIONE " + R) if pi.get("sottotensione") else (VERDE + "alimentazione ok" + R)
    batt = f"   {DIM}batteria{R} {pi['batt_v']:.2f} V" if pi.get("batt_v") else ""
    testa = (bg(236) + fg(117) + B + " ROBOCASSANO27 " + R + bg(236) + fg(250) + f" {versione} " + R
             + f"   {sw}   {DIM}CPU{R} {temp_s}   {alim}{batt}")
    sf = dict(FASI).get(fase, 29)
    stato = c.get("stato") or ""
    banda = bg(sf) + BIANCO + B + pad(f" {fase} " + R + bg(sf) + BIANCO + f"  {stato}", L) + R
    ora = c.get("manovra") or c.get("azione") or ""
    out = [pad(testa, L), banda]
    vista = c.get("vista") or {}
    if vista.get("testo"):
        cv = VERDE if vista.get("ok") else (ROSSO if vista.get("ok") is False else GIALLO)
        out.append(pad(f" {B}{cv}{vista.get('testo', '')}{R}", L))
    out.append(pad(f" {GIALLO}{B}ORA ▸{R} {BIANCO}{B}{ora}{R}", L))
    # riga 1: laser, assetto, cronometro
    l1 = 31
    l2 = 30
    out += affianca(riquadro_laser(c, l1, 7), riquadro_assetto(c, storia, l2, 7), riquadro_crono(crono, L - l1 - l2, 7))
    # riga 2: le due camere
    y = c.get("yolo") or [None, 0]
    nome, col = NOMI_YOLO.get(y[0], ("—", DIM))
    conf = y[1] or 0
    barra = "".join((VERDE + "█") if i < conf * 10 else (DIM + "·") for i in range(10)) + R
    verde = c.get("verde") or ""
    t_lin = [f"{DIM}YOLO vede{R}", f"{col}{B}{nome}{R}", f"{barra} {conf:.2f}",
             (f"{VERDE}{verde[:16]}{R}" if verde else ""), f"{DIM}{c.get('fps', 0):.0f} fps · {c.get('dec_s', 0):.0f} dec/s{R}"]
    t_ar = [f"{DIM}vede{R}", f"{AZZURRO}{B}{(c.get('arena') or '—')[:17]}{R}"]
    # [FIX 113] Lux, tempo di esposizione e gain delle due camere (anche nella moviola).
    meta = c.get("cam_meta") or {}
    def dati_cam(m):
        lux, exp, gain = m.get("lux"), m.get("exposure_us"), m.get("gain")
        return "{} lux | Exp {} us | Gain {}".format("-" if lux is None else round(lux),
            "-" if exp is None else round(exp), "-" if gain is None else round(gain, 2))
    t_lin.append(f"{DIM}{dati_cam(meta.get('linea') or {})}{R}")
    t_ar.append(f"{DIM}{dati_cam(meta.get('arena') or {})}{R}")
    meta = L // 2
    # [FIX 108] le camere crescono con la finestra: 8 righe (100 x 38), fino a 20 con un terminale grande
    alt_cam = max(8, min(20, int((meta - 22) / 3.4), righe_tot - 32))
    out += affianca(riquadro_camera("CAMERA LINEA", cam_linea, t_lin, meta, alt_cam, eta_linea),
                    riquadro_camera("CAMERA ARENA", cam_arena, t_ar, L - meta, alt_cam, eta_arena))
    out += riquadro_motori(c, L)
    out += riquadro_gara(fase, durate, L)
    resto = max(2, righe_tot - len(out) - 3)
    ev = []
    for e in list(eventi)[-resto:][::-1]:
        em, es = divmod(max(e.get("t", 0), 0), 60)
        colc = COL_CAT.get(e.get("cat"), DIM)
        ev.append(f" {DIM}{int(em):02d}:{es:04.1f}{R}  {colc}{ICONA_CAT.get(e.get('cat'), '·')} {e.get('testo', '')}{R}")
    out += scatola("EVENTI (il più recente in alto)", ev, L, resto)
    out.append(pad(f" {DIM}ultima print: {c.get('msg') or ''}{R}", L))
    return out


def disegna(righe):
    """Stringa che ridisegna tutta la schermata dall'angolo in alto (senza farla lampeggiare)."""
    return "\033[H" + "\n".join(r + "\033[K" for r in righe) + "\033[J"
