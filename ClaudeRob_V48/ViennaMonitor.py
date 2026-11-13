"""
ViennaMonitor.py  -  [FIX 37] terminale chiaro, scatola nera e cruscotto 3D del robot.
[FIX 107] TERMINALE = "cabina": la "cabina di pilotaggio" (ViennaCabina.py) con le camere in piccolo e il cronometro.

Si attiva con una riga in RwdFoto.py, subito dopo  Rwd = Robot():
    Monitor.avvia(Rwd, WebCam, globals())

Cosa fa (tutto si regola in ViennaDataConf.py, sezione FIX 37):
  1) TERMINALE: invece di centinaia di numeri al secondo mostra
       - in alto gli EVENTI importanti, tradotti in italiano, con orario e colore;
       - in basso un PANNELLO fisso che si aggiorna sul posto: cosa sta facendo il robot,
         laser, giroscopio, YOLO, motori, braccio, LED, Raspberry, batteria.
  2) SCATOLA NERA: durante la run scrive 10 volte al secondo stato e sensori in un file
     (/home/pi/OneDrive/ScatolaNera/). Non comunica con niente: si può usare anche in gara.
     Il file si apre dopo con cruscotto/cruscotto.html.
  3) CRUSCOTTO: solo in laboratorio, una pagina web con il robot in 3D e tutti i dati dal vivo:
     dal PC o dal telefono sulla stessa rete aprite  http://<indirizzo del robot>:8000
     IN GARA il WiFi va spento (regolamento RCJ Rescue 3.2.4): mettete CRUSCOTTO = False.

Il monitor non deve MAI fermare il robot: ogni sua parte è protetta da try/except.
"""
import builtins
import collections
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime

import cv2
import numpy as np

import ViennaDataConf as RwdConf

# nel simulatore (finto_hw caricato) niente thread, niente pannello, niente server: solo scatola nera
SIM = "finto_hw" in sys.modules

_print_orig = builtins.print
_out = sys.stdout
_lock = threading.RLock()          # protegge i dati
_lock_term = threading.RLock()     # protegge le scritture sul terminale

_rwd = None
_webcam = None
_G = {}                            # globals() di RwdFoto: Immagine, Arg, Nera...
_t_avvio = time.time()
_t_run = None                      # inizio della run (switch acceso)
_attivo = False

# ultimo stato noto (scritto dai "ganci" sulle funzioni del robot)
_cmd = {"motore": "Stop", "vel": 0, "sterzo": 0, "manovra": "", "braccio": None, "pinza": None,
        "gira_h0": None, "gira_gradi": 0}
# [FIX 43] ultimo valore VALIDO di ogni laser (un laser fuori portata manda 0): [valore, istante]
_laser_ult = [[0, 0.0], [0, 0.0], [0, 0.0]]
_arduino = {"ok": True, "da": 0.0}
_yolo = {"cls": None, "conf": 0.0, "t": 0.0, "verde": "", "verde_t": 0.0}
_arena = {"cosa": "", "t": 0.0, "box": None}
_frame_arena = [None]
_t_arena = [0.0]                   # [FIX 51] quando è arrivato l'ultimo fotogramma della camera arena
_t_linea = [0.0]
# [FIX 113]: metadati delle camere aggiornati a 1 Hz
_cam_meta = {"linea": {"lux": None, "exposure_us": None, "gain": None, "t": 0.0},
             "arena": {"lux": None, "exposure_us": None, "gain": None, "t": 0.0}}
_vista = {"ok": None, "testo": "CONTROLLO VISTA IN ATTESA", "dettagli": [], "t": 0.0}
# [FIX 114] gli eventi di sistema dell'AVVIO (versione, taratura della camera linea, VISTA, esposizione arena).
# Prima finivano nel file aperto all'accensione del programma, che si cancella quando parte la gara (FIX 108):
# nella scatola nera della V46 mancava la soglia Otsu. Ora vanno nell'intestazione di ogni scatola nera
# ("avvio") e si riscrivono come eventi all'inizio della run.
_eventi_avvio = []
_ultimi_inviati = {"linea": 0.0, "arena": 0.0}
_conta = {"verifica": collections.deque(maxlen=60), "linea": collections.deque(maxlen=60)}
_pi = {"cpu_temp": None, "carico": None, "v5": None, "sottotensione": False, "sottotensione_avvenuta": False,
       "batt_v": None, "batt_pct": None, "ip": None}
_ultimo_msg = [""]
_n_msg = [0]

_eventi = collections.deque(maxlen=400)   # dict(n, t, cat, testo)
# [FIX 107] per la cabina: storia di 20 s, cronometro dallo switch, fasi della gara, eventi col tempo di gara
_storia = collections.deque(maxlen=200)
_eventi_cab = collections.deque(maxlen=60)
_cab = {"crono": None, "fasi": None, "modo": None, "avvisato": False}
# [FIX 47] registro COMPLETO per la finestra: ogni print del programma (anche quelle che il terminale
# filtra come rumore) e ogni evento, nell'ordine in cui arrivano
_registro = collections.deque(maxlen=300)  # dict(t, cat, testo, imp)
_n_eventi = [0]
_campione = [{}]

# scatola nera
_scatola = {"f": None, "nome": None, "ultimo_flush": 0.0, "ultimo_campione": 0.0, "ultima_foto": 0.0}
# [FIX 108] UNA SCATOLA NERA PER RUN, con le LoP dentro. Prima ogni accensione dello switch ("NUOVA RUN") apriva un
# file nuovo e il tempo ripartiva da 0: una gara con 2 LoP finiva in 3 file. Ora, se lo switch è rimasto spento meno di
# CRONO_NUOVA_GARA_S (120 s), è una LoP: stesso file, stesso tempo, e due eventi ("STOP n" quando si spegne, con fase,
# laser e rotta; "LoP n: si riparte" quando si riaccende). File nuovo solo per una gara nuova o un programma riavviato.
_run = {"attiva": False, "sw": False, "spento_da": None, "lop": 0, "stop": 0,
        "riacceso_t": 0.0, "ultimo_spento": None, "ultimo_acceso": None}

# -------------------------------------------------------------------------------------------
#   NOMI DELLE FUNZIONI -> cosa sta facendo il robot (in italiano)
# -------------------------------------------------------------------------------------------
NOMI = {
    "InseguitoreIA": ("Seguilinea", "linea"),
    "CrosSx": ("Incrocio: giro a SINISTRA", "incrocio"),
    "CrosSxIncl": ("Incrocio: giro a SINISTRA", "incrocio"),
    "CrosDx": ("Incrocio: giro a DESTRA", "incrocio"),
    "CrosDxIncl": ("Incrocio: giro a DESTRA", "incrocio"),
    "CrosFF": ("Doppio verde: DIETROFRONT", "incrocio"),
    "CrosFFIncl": ("Doppio verde: DIETROFRONT", "incrocio"),
    "BoosterSx": ("Spinta a sinistra", "linea"),
    "BoosterDx": ("Spinta a destra", "linea"),
    "OstAutDet": ("Aggiro l'OSTACOLO", "ostacolo"),
    "LineaDavanti": ("cerco la linea", "ostacolo"),
    "ArenaAI": ("ARENA: cerco le palline", "arena"),
    "AbbassaPinza": ("abbasso la pinza", "arena"),
    "AlzaPinza": ("alzo la pinza", "arena"),
    "CaricaPalla": ("prendo la pallina", "arena"),
    "ApriPinza": ("apro la pinza", "arena"),
    "ChiudiPinza": ("chiudo la pinza", "arena"),
    "ScaricaPalla": ("porto la pallina al triangolo", "arena"),
    "SvuotaPinza": ("lascio la pallina", "arena"),
    "GiraVersoMemoria": ("mi giro verso dove l'avevo visto", "arena"),
    "TrovaUscitaIA": ("ARENA: cerco l'uscita", "arena"),
    "EsciDallaPorta": ("Uscita dalla porta", "arena"),
    "CentraSullaPorta": ("mi centro sulla porta", "arena"),
    "SpostamentoPorta": ("misuro la porta con la camera", "arena"),
    "Festeggia": ("FESTA!", "gara"),
    "AvanzaSullIncrocio": ("avanzo fino a mettere le ruote sull'incrocio", None),
    "CompletaSvolta": ("finisco la svolta: cerco la linea davanti", None),
    "PerimetroUscita": ("giro lungo i muri cercando l'uscita", "arena"),
    "ProvaApertura": ("provo un'apertura nel muro", "arena"),
    "ControllaApertura": ("controllo se l'apertura e' l'uscita", "arena"),
    "GuardaPavimento": ("guardo il pavimento (striscia nera?)", "arena"),
    "EsciSullaStriscia": ("esco sulla striscia nera", "arena"),
    "TrovaUscita": ("ARENA: cerco l'uscita", "arena"),
    "TrovaIngressoArena": ("INGRESSO ARENA: controllo la striscia argento", "arena"),
    "TrovaUscitaArena": ("ARENA: cerco l'uscita", "arena"),
    "EsciControllando": ("esco guardando il pavimento (argento? nero?)", "arena"),
    "AvvicinatiAllaPorta": ("mi avvicino alla porta guardando il pavimento", "arena"),
    "GiroDeiMuri": ("costeggio le pareti cercando l'uscita", "arena"),
    "SeguiParete": ("seguo il muro a 6-7 cm", "arena"),                       # [FIX 63]
    "RuotaVerso": ("ruoto sul posto (giroscopio, anello chiuso)", None),     # [FIX 64]
    "EsciDallaPortaDavanti": ("uscita nel muro davanti: mi stacco dal muro ed esco", "arena"),   # [FIX 69]
    "DirezioneIngresso": ("calcolo la direzione per entrare dritto nell'arena", "arena"),     # [FIX 71]
    "CentraSullIngresso": ("mi centro sulla porta d'ingresso", "arena"),                      # [FIX 71]
    "IngressoDopoArgento": ("linea finita dopo l'argento: riprovo l'ingresso", "arena"),      # [FIX 75]
    "RuotaOstacolo": ("giro intorno all'ostacolo (a squadra con le piastrelle)", "ostacolo"), # [FIX 73]
    "GiraInArena": ("rotazione grande in arena", "arena"),                                    # [FIX 74]
    "ConfermaDietrofront": ("doppio verde: lo ricontrollo da fermo", "incrocio"),            # [FIX 79]
    "SquadraSullUscita": ("mi raddrizzo e mi centro sulla striscia nera dell'uscita", "gara"), # [FIX 84]
    "ConfermaOstacolo": ("ostacolo o rampa? avanzo piano e controllo", "ostacolo"),
    "AttraversaInterruzione": ("interruzione: mi allineo e vado dritto col giroscopio", "linea"),
    "AttraversaVuoto": ("interruzione: attraverso il vuoto dritto col giroscopio", "linea"),
    "RecuperaLinea": ("linea persa: la cerco girando sul posto e tornando indietro", "linea"),
    "VedoLinea": ("guardo se vedo la linea", "linea"),
    "IncrocioDritto": ("incrocio senza verde: lo attraverso dritto", "linea"),
    "AnalizzaIncrocio": ("guardo se davanti c'è un incrocio", "linea"),
    "GiraVerso": ("giro verso una direzione (giroscopio)", "linea"),
    "ControllaAperturaMuro": ("apertura nel muro: misuro e guardo se è l'uscita", "arena"),
    "AvvicinatiAlMuro": ("vado vicino alla parete", "arena"),
    "ScegliLatoGiro": ("scelgo da che parte fare il giro", "arena"),
    "LineaFuori": ("cerco la linea fuori dall'arena", "arena"),
    "MemorizzaPosizione": ("memorizzo dove ho visto la pallina", "arena"),
    "Cattura": ("catturo la pallina", "arena"),
    "Gira": ("giro sul posto", None),
    "Dritto": ("avanzo dritto", None),
}

# -------------------------------------------------------------------------------------------
#   MESSAGGI: traduzioni, rumore e categorie
# -------------------------------------------------------------------------------------------
TRADUZIONI = [
    (r"IA\s+Incrocio\s+Sx", "Incrocio con verde a SINISTRA -> giro a sinistra", "incrocio"),
    (r"IA\s+Incrocio\s+Dx", "Incrocio con verde a DESTRA -> giro a destra", "incrocio"),
    (r"IA\s+Incrocio\s+Fr", "Doppio verde -> DIETROFRONT", "incrocio"),
    (r"IA\s*-\s*Discontinuit", "Linea interrotta -> vado dritto", "linea"),
    (r"IA\s+STOP\s+RO", "Linea ROSSA: arrivo!", "gara"),
    (r"IA\s+Arena\s+In", "Striscia argento: forse l'ingresso dell'arena", "arena"),
    (r"^POSSIBILE OSTACOLO", "Qualcosa davanti a meno di 15 cm", "ostacolo"),
    (r"^OSTACOLO$", "OSTACOLO: lo aggiro", "ostacolo"),
    (r"^FINE OSTACOLO", "Ostacolo superato", "ostacolo"),
    (r"Trovata Fine Linea", "Sono entrato nell'arena", "arena"),
    (r"^PALLINA CATTURATA", "Pallina PRESA", "arena"),
    (r"^PALLINA NON CATTURATA", "Pallina MANCATA: riprovo", "errore"),
    (r"^Scarica Argento", "Porto la pallina ARGENTO al triangolo verde", "arena"),
    (r"^Scarica Nero", "Porto la pallina NERA al triangolo rosso", "arena"),
    (r"^Scarico Palla", "Lascio la pallina nel triangolo", "arena"),
    (r"^Esco dalla porta", "Esco dall'arena", "arena"),
    (r"^Falso ARGENTO", "Falso ARGENTO: la linea continua, NON entro", "errore"),
    (r"^Striscia ARGENTO sotto il muso", "ARGENTO uscendo: era l'ingresso, torno dentro", "errore"),
    (r"^Uscita confermata", "Uscita confermata: linea ritrovata fuori", "gara"),
    (r"^Giro dell'arena: parete a", None, "arena"),        # None = testo originale, solo colore
    (r"^Apertura nel muro: la misuro", "Apertura nel muro: la misuro e vado al centro", "arena"),
    (r"^Apertura larga", None, "arena"),
    (r"^E' l'USCITA", "E' l'USCITA: esco", "gara"),
    (r"^E' l'INGRESSO", "E' l'INGRESSO: lo supero e continuo il giro", "arena"),
    (r"^Non riesco a girarmi", "Non riesco a girarmi: arretro e riprovo", "errore"),
    (r"^Accostato al triangolo", None, "arena"),
    (r"^Non avanzo", "Non avanzo (spigolo contro qualcosa): arretro", "errore"),
    (r"^Davanti è libero", "Davanti è libero: mi stacco dalla parete e riprovo", "arena"),
    (r"^Giroscopio: la rotazione è bloccata", "Giroscopio: rotazione bloccata (tocco qualcosa), arretro", "errore"),   # [FIX 65]
    (r"^Giroscopio: robot inclinato", None, "errore"),                       # [FIX 65]
    (r"^Muro: direzione corretta", None, "arena"),                          # [FIX 63]
    (r"^L'apertura arriva fino all'angolo", None, "arena"),                 # [FIX 70]
    (r"^Ingresso ANNULLATO", None, "errore"),                               # [FIX 81]
    (r"^Ingresso", None, "arena"),                                          # [FIX 71]
    (r"^Dietrofront confermato", None, "incrocio"),                         # [FIX 79]
    (r"^Dietrofront ANNULLATO", None, "errore"),                            # [FIX 79]
    (r"^Triangolo di lato", None, "arena"),                                 # [FIX 83]
    (r"^Uscita: .*(tocco lo stipite|torno indietro|non è la porta|non trovata)", None, "errore"),     # [FIX 103] [FIX 104]
    (r"^Uscendo sono ancora contro lo stipite", None, "errore"),            # [FIX 103]
    (r"^Uscito storto", None, "arena"),                                     # [FIX 103]
    (r"^PROBABILE ALTALENA", None, "linea"),                                # [FIX 102]
    (r"^Altalena: ", None, "linea"),                                        # [FIX 102]
    (r"^Uscita: ", None, "gara"),                                           # [FIX 84]
    (r"^Uscendo non avanzo", None, "errore"),                               # [FIX 84]
    (r"^Negli ultimi 2 s ho girato", None, "linea"),                        # [FIX 85]
    (r"^GIROSCOPIO BLOCCATO", None, "errore"),                              # [FIX 88]
    (r"^GIROSCOPIO DI NUOVO VIVO", None, "sistema"),                        # [FIX 88]
    (r"^Falso ostacolo", None, "ostacolo"),                                 # [FIX 87]
    (r"^Laser frontale: lettura isolata", None, "ostacolo"),                # [FIX 87]
    (r"^Non è un ostacolo", None, "ostacolo"),                              # [FIX 87]
    (r"^Parete a ", None, "ostacolo"),                                      # [FIX 90]
    (r"^Ostacolo: ", None, "ostacolo"),                                     # [FIX 90]
    (r"^Non mi avvicino", None, "ostacolo"),                                # [FIX 90]
    (r"^Centratura sull'ingresso", None, "arena"),                          # [FIX 71]
    (r"^Linea finita subito dopo l'argento", None, "arena"),                # [FIX 75]
    (r"^Rotazione in arena bloccata", None, "errore"),                      # [FIX 74]
    (r"^Giro completo senza palline", None, "arena"),                       # [FIX 76]
    (r"^Triangolo a .* un fianco tocca il muro", None, "arena"),            # [FIX 77]
    (r"^Dopo l'angolo il laser", None, "arena"),                            # [FIX 63]
    (r"^Striscia NERA davanti mentre seguo", "Striscia NERA nel muro davanti: è l'USCITA", "gara"),   # [FIX 69]
    (r"^Striscia argento ma l'arena è già fatta", None, "errore"),          # [FIX 66]
    (r"^Festa finita", "Festa finita", "gara"),
    (r"^FESTA", "ARRIVO! Festeggio", "gara"),
    (r"^NUOVA RUN", "NUOVA RUN: switch acceso, contatori azzerati", "gara"),
    (r"^Interrotto da tastiera", "Programma interrotto (Ctrl+C)", "errore"),
    (r"^ARRESTO SICURO", "Arresto sicuro: motori fermi", "gara"),
]
RUMORE = [
    r"^(alto|basso|sinistro|destro)\b", r"^distanza", r"^posizione altezza porta",
    r"^nessun", r"^leggo verde", r"^mas?chero", r"^mashero", r"^distanze", r"^tempo trascorso",
    r"^pausa", r"^imu:", r"^switch:", r"^azione$", r"^pulse:", r"^fronte (libero|occupato)",
    r"^correggo per bianco", r"^centro verso", r"^tipo:", r"^pallina (true|false)", r"^direzione",
    r"^piega a", r"^dritto inclinato", r"^uscita più vicina", r"^errore:\s*-?\d", r"^robot a (destra|sinistra)",
    r"^ia\s+bianco", r"^ia\s+discontinuit.*:\s*-?\d", r"^\(?\s*(true|false)", r"^[-\d\s.,()]+$",
    r"^maschera immagine", r"^trovato$", r"^fatto$", r"^fermo$", r"^tilt in azione", r"^cerco elemento",
    r"^porta vista", r"^distanza targhet", r"^inizio lato", r"^passo vuoto", r"^inizio ostacolo",
    r"^mi allontano", r"^sinistro-", r"^destro-", r"^vado dritto poi", r"^indietro dritto",
    r"^giro (orario|antiorario)", r"^non e' l'uscita", r"^simo davanti",
]
CATEGORIE = [
    (r"controllo verde", "verde"),
    (r"errore|error|traceback|non risponde|timeout|warn|impossibile", "errore"),
    (r"ostacolo", "ostacolo"),
    (r"incrocio|dietrofront|verde|cross", "incrocio"),
    (r"pallin|palla|triangol|scarico|pinza|sfera|correggo di", "arena"),
    (r"porta|uscita|ingresso|arena|centratura", "arena"),
    (r"festa|nuova run|arrivo|rosso", "gara"),
    (r"foto|camera|cam |esposizione|yolo|modelli", "sistema"),
    (r"arduino|bluetooth|pca9685|robot|i2c", "sistema"),
]
_TRAD = [(re.compile(a, re.I), b, c) for a, b, c in TRADUZIONI]
_RUM = [re.compile(a, re.I) for a in RUMORE]
_CAT = [(re.compile(a, re.I), c) for a, c in CATEGORIE]

COLORI = {"incrocio": "33", "arena": "36", "ostacolo": "35", "errore": "31;1", "verde": "32;1",
          "gara": "1;37;44", "linea": "37", "sistema": "37", "info": "37"}


def _classifica(testo):
    """-> (testo da mostrare, categoria) oppure (None, None) se è rumore."""
    pulito = testo.strip()
    if not pulito:
        return None, None
    for rx, nuovo, cat in _TRAD:
        if rx.search(pulito):
            if nuovo is None:                       # [FIX 53] testo originale, solo la categoria (colore)
                return pulito, cat
            num = re.findall(r"0\.\d+", pulito)
            return (nuovo + (f"  (sicurezza {float(num[-1]):.2f})" if num and "IA" in pulito else "")), cat
    for rx in _RUM:
        if rx.search(pulito):
            return None, None
    for rx, cat in _CAT:
        if rx.search(pulito):
            return pulito, cat
    return pulito, "info"


# -------------------------------------------------------------------------------------------
#   TEMPO E PILA DELLE FUNZIONI
# -------------------------------------------------------------------------------------------
def _ora():
    return time.time()


def _t_rel(t=None):
    t = _ora() if t is None else t
    base = _t_run if _t_run is not None else _t_avvio
    return t - base


def _pila(frame):
    nomi = []
    while frame is not None:
        n = frame.f_code.co_name
        if n in NOMI:
            nomi.append(n)
        frame = frame.f_back
    nomi.reverse()
    return nomi


def _pila_principale():
    try:
        if SIM or threading.current_thread() is threading.main_thread():
            return _pila(sys._getframe(1))
        fr = sys._current_frames().get(threading.main_thread().ident)
        return _pila(fr)
    except Exception:
        return []


def _descrivi(pila):
    if not pila:
        sw = _switch()
        return ("In attesa: switch SPENTO" if not sw else "Tra una fase e l'altra"), "info"
    parti = []
    cat = "info"
    for n in pila:
        lab, c = NOMI[n]
        if not parti or parti[-1] != lab:
            parti.append(lab)
        if c:
            cat = c
    return " > ".join(parti), cat


def _switch():
    try:
        return bool(_rwd.GetSensori()["switch"][1])
    except Exception:
        return False


# -------------------------------------------------------------------------------------------
#   EVENTI
# -------------------------------------------------------------------------------------------
_dedup = {"chiave": None, "t": 0.0, "volte": 0}


def evento(testo, cat="info", mostra=True):
    """Registra un evento (va nel terminale, nella scatola nera e nel cruscotto)."""
    global _t_run
    t = _ora()
    with _lock:
        _n_eventi[0] += 1
        ev = {"n": _n_eventi[0], "t": round(_t_rel(t), 2), "cat": cat, "testo": testo}
        _eventi.append(ev)
        _registro.append({"t": ev["t"], "cat": cat, "testo": testo, "imp": True})
        if _cab["crono"] is not None:           # [FIX 107] nella cabina gli eventi hanno il tempo del cronometro
            ini = _cab["crono"].inizio
            _eventi_cab.append(dict(ev, t=round(t - ini, 1) if ini is not None else ev["t"]))
            _cab["fasi"].evento(testo, t)
    _scrivi_scatola({"tipo": "evento", **ev})
    if not _run["attiva"] and cat in ("sistema", "errore", "gara") and len(_eventi_avvio) < 30:
        _eventi_avvio.append({"cat": cat, "testo": testo})      # [FIX 114]
    if mostra and not SIM:
        _mostra_evento(ev)


def _mostra_evento(ev):
    if RwdConf.TERMINALE == "tutto" or RwdConf.DEBUG:
        return                      # in modalità "tutto" la riga originale è già stata stampata
    if _cab["modo"] == "cabina":
        return                      # [FIX 107] nella cabina gli eventi sono nel loro riquadro
    m, s = divmod(max(ev["t"], 0), 60)
    col = COLORI.get(ev["cat"], "37")
    riga = f"\033[37m{int(m):02d}:{s:04.1f}\033[0m  \033[{col}m{ev['testo']}\033[0m"
    if not _tty():
        riga = f"{int(m):02d}:{s:04.1f}  [{ev['cat']}] {ev['testo']}"
    with _lock_term:
        try:
            _out.write(riga + "\n")
            _out.flush()
        except Exception:
            pass


def _print(*args, sep=" ", end="\n", file=None, flush=False):
    """Sostituisce print: filtra il rumore, traduce i messaggi importanti, registra tutto."""
    if file is not None and file not in (sys.stdout, sys.__stdout__):
        return _print_orig(*args, sep=sep, end=end, file=file, flush=flush)
    try:
        testo = sep.join(str(a) for a in args)
    except Exception:
        return _print_orig(*args, sep=sep, end=end, file=file, flush=flush)
    if SIM or RwdConf.TERMINALE == "tutto" or RwdConf.DEBUG:
        with _lock_term:
            _print_orig(*args, sep=sep, end=end, file=file, flush=flush)
    try:
        _gestisci_messaggio(testo)
    except Exception:
        pass


def _gestisci_messaggio(testo):
    global _t_run
    _ultimo_msg[0] = testo.strip()[:120]
    _n_msg[0] += 1
    grezzo = {"t": round(_t_rel(_ora()), 2), "cat": "grezzo", "testo": testo.strip()[:150], "imp": False}
    with _lock:
        _registro.append(grezzo)                # [FIX 47] anche le print "di rumore" vanno nella finestra
    if re.match(r"^\s*NUOVA RUN", testo):
        t = _ora()
        lim = getattr(RwdConf, "CRONO_NUOVA_GARA_S", 120.0)
        # quanto è rimasto spento lo switch (il monitor può aver già visto la riaccensione, o non ancora)
        if _run["spento_da"] is not None:
            spento = t - _run["spento_da"]
        elif t - _run["riacceso_t"] < 3.0:
            spento = _run["ultimo_spento"]
        else:
            spento = None
        if _run["attiva"] and spento is not None and spento <= lim:
            pass                                    # [FIX 108] ripartenza dopo una LoP: stessa scatola nera, stesso tempo
        else:
            _t_run = t
            _nuova_scatola()
            _run.update(attiva=True, lop=0, stop=0, spento_da=None, riacceso_t=0.0, ultimo_spento=None)
            for e in _eventi_avvio:                 # [FIX 114] i controlli dell'avvio anche dentro la run
                _scrivi_scatola({"tipo": "evento", "n": 0, "t": 0.0, "cat": e["cat"], "testo": "AVVIO: " + e["testo"]})
    if testo.startswith("Controllo verde"):
        _yolo.update(verde=testo.replace("Controllo verde: ", ""), verde_t=_ora())
    nuovo, cat = _classifica(testo)
    if nuovo is None:
        return
    chiave = re.sub(r"[-\d.]+", "#", nuovo.lower())
    t = _ora()
    if chiave == _dedup["chiave"] and t - _dedup["t"] < 2.0:
        _dedup["volte"] += 1
        _dedup["t"] = t
        return
    if _dedup["volte"] > 0:
        evento(f"   (ripetuto altre {_dedup['volte']} volte)", "sistema")
    _dedup.update(chiave=chiave, t=t, volte=0)
    grezzo["tradotto"] = True                  # [FIX 47] nella finestra si vede la versione tradotta
    evento(nuovo, cat)


# -------------------------------------------------------------------------------------------
#   GANCI sulle funzioni del robot e delle camere (non cambiano cosa fanno)
# -------------------------------------------------------------------------------------------
def _aggancia(oggetto, nome, prima=None, dopo=None):
    orig = getattr(oggetto, nome, None)
    if orig is None or getattr(orig, "_monitor", False):
        return

    def gancio(*a, **k):
        if prima:
            try:
                prima(*a, **k)
            except Exception:
                pass
        r = orig(*a, **k)
        if dopo:
            try:
                dopo(r, *a, **k)
            except Exception:
                pass
        return r
    gancio._monitor = True
    try:
        setattr(oggetto, nome, gancio)
    except Exception:
        pass


def _cmd_sterzo(vel, sterzo=0, *a, **k):
    _cmd.update(motore="Sterzo", vel=vel, sterzo=sterzo)


def _cmd_stop(*a, **k):
    _cmd.update(motore="Stop", vel=0, sterzo=0)


def _cmd_gira(gradi, velocita=40, *a, **k):
    try:
        h0 = _rwd.GetGyro()[2]
    except Exception:
        h0 = None
    _cmd.update(manovra=f"Gira {gradi:+.0f} gradi", gira_h0=h0, gira_gradi=gradi)


def _diff_angolo(a, b):
    return (a - b + 180) % 360 - 180


def _azione_motori(cmd, vel, sterzo):
    """[FIX 43] Cosa stanno facendo le ruote, in parole semplici."""
    if cmd == "Stop" or not vel:
        return "FERMO"
    if cmd == "Dritto":
        return f"avanti dritto col giroscopio (vel {vel:.0f})"
    if abs(sterzo) >= 100:
        return f"ruoto SUL POSTO verso {'DESTRA' if sterzo > 0 else 'SINISTRA'} (vel {abs(vel):.0f})"
    verso = "avanti" if vel > 0 else "INDIETRO"
    if abs(sterzo) < 5:
        return f"{verso} dritto (vel {abs(vel):.0f})"
    return f"{verso} curvando a {'DESTRA' if sterzo > 0 else 'SINISTRA'} (vel {abs(vel):.0f}, sterzo {sterzo:+.0f})"


def _arduino_ok():
    """[FIX 43] Arduino manda un pacchetto ogni pochi ms: se tace per 0,3 s ViennaClsRobot mette tutto a 0."""
    t = getattr(_rwd, "_last_packet_time", None)
    if SIM or t is None:
        return True, 0.0
    return time.time() - t < 0.3, time.time() - t


def _cmd_dritto(velocita=40, durata=2.0, *a, **k):
    _cmd.update(manovra=f"Dritto {durata:.1f} s", motore="Dritto", vel=velocita, sterzo=0)


def _cmd_braccio(angolo, *a, **k):
    _cmd["braccio"] = angolo


def _cmd_pinza(angolo, *a, **k):
    _cmd["pinza"] = angolo


def _dopo_sensori(r, *a, **k):
    if SIM:
        _campiona_se_serve(sys._getframe(2))


def _dopo_verifica(r, *a, **k):
    cls, conf = r[0], r[1]
    with _lock:
        _yolo.update(cls=cls, conf=float(conf or 0), t=_ora())
        _conta["verifica"].append(_ora())


def _dopo_arena(nome):
    def f(r, *a, **k):
        if r and r[0]:
            tipo = r[4]
            _arena.update(cosa=f"{nome}: classe {tipo}, centro ({r[2]}, {r[3]})", t=_ora(),
                          box=list(getattr(_webcam, "UltimoBox", None) or []))
    return f


def _dopo_cam_arena(r, *a, **k):
    _frame_arena[0] = r
    _t_arena[0] = _ora()


def _dopo_cam_linea(r, *a, **k):
    _conta["linea"].append(_ora())
    _t_linea[0] = _ora()


# -------------------------------------------------------------------------------------------
#   RASPBERRY E BATTERIA
# -------------------------------------------------------------------------------------------
def _leggi_pi():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            _pi["cpu_temp"] = int(f.read().strip()) / 1000.0
    except Exception:
        pass
    try:
        _pi["carico"] = os.getloadavg()[0]
    except Exception:
        pass
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=1).stdout
        val = int(out.strip().split("=")[1], 16)
        _pi["sottotensione"] = bool(val & 0x1)
        _pi["sottotensione_avvenuta"] = bool(val & 0x10000)
    except Exception:
        pass
    try:
        out = subprocess.run(["vcgencmd", "pmic_read_adc", "EXT5V_V"], capture_output=True, text=True, timeout=1).stdout
        m = re.search(r"=([\d.]+)V", out)
        if m:
            _pi["v5"] = float(m.group(1))
    except Exception:
        pass
    if RwdConf.BATTERIA_INA219:
        try:
            import smbus2
            with smbus2.SMBus(1) as bus:
                raw = bus.read_word_data(RwdConf.BATTERIA_INA219, 0x02)
                raw = ((raw & 0xFF) << 8) | (raw >> 8)
                v = (raw >> 3) * 0.004
            _pi["batt_v"] = round(v, 2)
            celle = RwdConf.BATTERIA_CELLE
            _pi["batt_pct"] = int(max(0, min(100, (v / celle - 3.5) / (4.2 - 3.5) * 100)))
        except Exception:
            pass


def _ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))        # nessun pacchetto inviato: serve solo a leggere l'IP
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


# -------------------------------------------------------------------------------------------
#   CAMPIONE: la fotografia dello stato in questo istante
# -------------------------------------------------------------------------------------------
def _fps(dq, finestra=2.0):
    t = _ora()
    n = sum(1 for x in dq if t - x < finestra)
    return round(n / finestra, 1)


_pend_annunciata = {"tipo": "piano", "t": None, "max_b": 0, "max_r": 0}


def _annuncia_pendenza(pend):
    # [FIX 82] un evento quando inizia e quando finisce un tratto inclinato (terminale, scatola nera, cruscotto)
    if not pend or pend["tipo"] == "sconosciuto":
        return
    a = _pend_annunciata
    if pend["tipo"] != "piano":
        a["max_b"] = max(a["max_b"], abs(pend["becc"]))
        a["max_r"] = max(a["max_r"], abs(pend["roll"]))
    if pend["tipo"] == a["tipo"]:
        return
    ora = _ora()
    if pend["tipo"] == "piano":
        durata = f" dopo {ora - a['t']:.0f} s" if a["t"] else ""
        evento(f"Tratto inclinato finito{durata} (massimo: beccheggio {a['max_b']:.0f}, rollio {a['max_r']:.0f} gradi): di nuovo IN PIANO", "info")
        a["max_b"] = a["max_r"] = 0
    else:
        evento(f"Tratto inclinato: {pend['testo'].split(' (da')[0]}", "info")
        if a["tipo"] == "piano":
            a["t"] = ora
    a["tipo"] = pend["tipo"]


def _campione_ora(pila=None):
    if pila is None:
        pila = _pila_principale()
    desc, cat = _descrivi(pila)
    try:
        s = _rwd.GetSensori()
    except Exception:
        s = {"distanze": (0, 0, 0), "imu": (0, 0, 0), "switch": (False, False), "tilt": (0, 0)}
    try:
        l1 = _rwd.linee["Luce1"].value == 0
        l2 = _rwd.linee["Luce2"].value == 0
    except Exception:
        l1 = l2 = False
    ora = _ora()
    dist = list(s.get("distanze", (0, 0, 0)))
    for i in range(3):
        if dist[i]:
            _laser_ult[i] = [dist[i], ora]
    ard, muto_da = _arduino_ok()
    imu = list(s.get("imu", (0, 0, 0)))
    try:
        pend = _rwd.Pendenza()          # [FIX 82]
    except Exception:
        pend = None
    _annuncia_pendenza(pend)
    # [FIX 87][FIX 88] laser frontale filtrato e da dove viene la rotta (giroscopio o bussola stimata)
    try:
        dfr = _rwd.FrontaleFiltrato()
        bussola = _rwd.BussolaStato()
        rotta = _rwd.GetGyro()[2]
    except Exception:
        dfr, bussola, rotta = None, "", imu[2]
    manovra = _cmd["manovra"] if pila and pila[-1] in ("Gira", "Dritto") else ""
    if pila and pila[-1] == "Gira" and _cmd["gira_h0"] is not None and (ard or bussola.startswith("stimata")):
        g = _cmd["gira_gradi"]
        fatti = abs(_diff_angolo(rotta, _cmd["gira_h0"]))
        manovra = f"giro a {'DESTRA' if g > 0 else 'SINISTRA'} di {abs(g):.0f} gr: fatti {fatti:.0f}"
    c = {
        "t": round(_t_rel(ora), 2),
        "stato": desc, "cat": cat, "pila": pila,
        "manovra": manovra,
        "azione": _azione_motori(_cmd["motore"], _cmd["vel"], _cmd["sterzo"]),
        "d": dist,
        "d_ult": [[v, round(ora - t, 1)] for v, t in _laser_ult],   # ultimo valore valido e da quanti s
        "ard": ard, "ard_muto": round(muto_da, 1),
        "imu": imu,          # (beccheggio, rollio, rotta)
        "dfr": dfr,          # [FIX 87] laser frontale filtrato (mediana), quello usato per gli ostacoli
        "bus": bussola,      # [FIX 88] "giroscopio" o "stimata: ..." (giroscopio bloccato / Arduino muto)
        "rotta": rotta,      # [FIX 88] rotta usata dal programma (uguale a imu[2] se il giroscopio funziona)
        "tilt": list(s.get("tilt", (0, 0))),
        "pend": ({"tipo": pend["tipo"], "testo": pend["testo"], "becc": pend["becc"], "roll": pend["roll"]}
                 if pend else None),    # [FIX 82] tratto inclinato capito dal giroscopio
        "sw": bool(s.get("switch", (False, False))[1]),
        "mot": [_cmd["motore"], _cmd["vel"], _cmd["sterzo"]],
        "br": _cmd["braccio"], "pz": _cmd["pinza"], "led": [l1, l2],
        "yolo": [_yolo["cls"], round(_yolo["conf"], 2)] if ora - _yolo["t"] < 1.5 else [None, 0],
        "verde": _yolo["verde"] if ora - _yolo["verde_t"] < 5 else "",
        "arena": _arena["cosa"] if ora - _arena["t"] < 1.5 else "",
        "dec_s": _fps(_conta["verifica"]), "fps": _fps(_conta["linea"]),
        "pal": [_G.get("Arg", 0), _G.get("Nera", 0)],
        "msg": _ultimo_msg[0],
        "pi": dict(_pi),
        "lux": [_cam_meta["linea"]["lux"], _cam_meta["arena"]["lux"]],
        "cam_meta": {"linea": dict(_cam_meta["linea"]), "arena": dict(_cam_meta["arena"])},
        "vista": dict(_vista),
    }
    with _lock:
        _campione[0] = c
    return c


def _miniatura(img, w=176, h=104):
    if img is None:
        return None
    try:
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        small = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return base64.b64encode(buf.tobytes()).decode() if ok else None
    except Exception:
        return None


def _stop_e_lop(c, t):
    """[FIX 108] Switch spento durante la run: evento STOP con dove era il robot. Riacceso entro CRONO_NUOVA_GARA_S: LoP."""
    sw = bool(c.get("sw"))
    if sw:
        _run["ultimo_acceso"] = c
    if _run["attiva"] and _run["sw"] and not sw:
        _run["stop"] += 1
        _run["spento_da"] = t
        c = _run["ultimo_acceso"] or c             # com'era il robot l'ultimo istante con lo switch acceso
        m, s = divmod(max(c["t"], 0), 60)
        d = c.get("d") or [0, 0, 0]
        b, ro, rt = (list(c.get("imu") or []) + [0, 0, 0])[:3]
        evento(f"STOP {_run['stop']}: switch spento a {int(m)}:{s:04.1f} durante \"{c.get('stato', '')}\" "
               f"(laser Sx {d[0] or 'fuori'} Fr {d[1] or 'fuori'} Dx {d[2] or 'fuori'} cm, rotta {c.get('rotta', rt)}, "
               f"beccheggio {b:+.0f}, YOLO {(c.get('yolo') or ['-'])[0] or '-'})", "gara")
    elif _run["attiva"] and sw and not _run["sw"] and _run["spento_da"] is not None:
        spento = t - _run["spento_da"]
        _run.update(riacceso_t=t, ultimo_spento=spento)
        if spento <= getattr(RwdConf, "CRONO_NUOVA_GARA_S", 120.0):
            _run["lop"] += 1
            evento(f"LoP {_run['lop']}: si riparte dopo {spento:.0f} s di switch spento (STOP {_run['stop']})", "gara")
        _run["spento_da"] = None
    _run["sw"] = sw


def _leggi_metadati_camere():
    """Legge Lux, ExposureTime e AnalogueGain dalle due Picamera2."""
    for nome, cam in (("linea", getattr(_webcam, "CamSL", None)),
                      ("arena", getattr(_webcam, "CamAr", None))):
        if cam is None: continue
        try:
            md = cam.capture_metadata() or {}
            for chiave, campo in (("Lux", "lux"), ("ExposureTime", "exposure_us"), ("AnalogueGain", "gain")):
                valore = md.get(chiave)
                _cam_meta[nome][campo] = round(float(valore), 3) if valore is not None else None
            _cam_meta[nome]["t"] = _ora()
        except Exception:
            pass


def _blocca_esposizione_arena():
    if not getattr(RwdConf, "CAM_ARENA_AUTOESPOSIZIONE", True) or not getattr(RwdConf, "CAM_ARENA_BLOCCA_ESPOSIZIONE", True):
        return
    cam = getattr(_webcam, "CamAr", None)
    dati = _cam_meta["arena"]
    if cam is None: return
    try:
        cmd = {"AeEnable": False}
        if dati.get("exposure_us") is not None: cmd["ExposureTime"] = int(dati["exposure_us"])
        if dati.get("gain") is not None: cmd["AnalogueGain"] = float(dati["gain"])
        cam.set_controls(cmd)
        evento("Camera arena: autoesposizione bloccata dopo assestamento", "sistema")
    except Exception as e:
        evento("Camera arena: blocco esposizione non riuscito: " + str(e), "errore")


def controlli_avvio():
    """[FIX 114] Controlli dell'avvio della V47 (FIX 113), chiamati da RwdFoto.py dopo la taratura della camera
    linea: blocco dell'esposizione della camera arena e controllo VISTA OK/ATTENZIONE (solo informativo)."""
    if SIM or not getattr(RwdConf, "CAM_VISTA_ABILITATA", True):
        return
    try:
        time.sleep(float(getattr(RwdConf, "CAM_AVVIO_ATTESA_S", 1.5)))
        _leggi_metadati_camere()
        _blocca_esposizione_arena()
        _controlla_vista_avvio()
    except Exception as e:
        evento("Controlli dell'avvio non riusciti: " + str(e), "errore")


def _controlla_vista_avvio():
    """Controllo informativo: segnala problemi, non impedisce la partenza."""
    if not getattr(RwdConf, "CAM_VISTA_ABILITATA", True) or SIM: return
    problemi = []
    lo, hi = float(getattr(RwdConf, "CAM_LUX_MIN", 10)), float(getattr(RwdConf, "CAM_LUX_MAX", 10000))
    for nome, cam in (("linea", getattr(_webcam, "CamSL", None)), ("arena", getattr(_webcam, "CamAr", None))):
        if cam is None:
            problemi.append(nome + ": camera non disponibile")
            continue
        try:
            frame = cam.capture_array()
            if frame is None or frame.size == 0:
                problemi.append(nome + ": nessun fotogramma")
                continue
            if nome == "linea": _t_linea[0] = _ora()
            else: _frame_arena[0] = frame; _t_arena[0] = _ora()
            bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR) if frame.ndim == 3 and frame.shape[2] == 4 else frame
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            media = float(np.mean(gray))
            if media < 3 or float(np.mean(gray < 5)) > .98: problemi.append(nome + ": immagine quasi tutta nera")
            elif media > 252 or float(np.mean(gray > 250)) > .98: problemi.append(nome + ": immagine quasi tutta bianca")
            if nome == "linea":
                hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
                soglia = int(getattr(_webcam, "SOGLIA_NERO", getattr(RwdConf, "SOGLIA_NERO", 80)))
                mask = cv2.inRange(hsv, np.array([0,0,0]), np.array([180,150,soglia]))
                quota = float(np.mean(mask > 0))
                if quota < float(getattr(RwdConf, "CAM_NERO_MIN", .005)):
                    problemi.append("linea: linea nera non rilevata (posizionare il robot sulla linea)")
                elif quota > float(getattr(RwdConf, "CAM_NERO_MAX", .65)):
                    problemi.append("linea: immagine troppo scura o linea non distinguibile")
        except Exception as e:
            problemi.append(nome + ": lettura fallita (" + type(e).__name__ + ")")
    _leggi_metadati_camere()
    for nome in ("linea", "arena"):
        lux = _cam_meta[nome].get("lux")
        if lux is None: problemi.append(nome + ": Lux non disponibile")
        elif lux < lo: problemi.append(nome + ": poca luce (" + str(lux) + " lux)")
        elif lux > hi: problemi.append(nome + ": troppa luce (" + str(lux) + " lux)")
    _vista.update(ok=not problemi, testo="VISTA OK" if not problemi else "ATTENZIONE: " + "; ".join(problemi),
                  dettagli=problemi, t=_ora())
    evento(_vista["testo"], "sistema" if not problemi else "errore")


def _campiona_se_serve(frame=None):
    t = _ora()
    if t - _scatola["ultimo_campione"] < 0.1:
        return
    _scatola["ultimo_campione"] = t
    pila = _pila(frame) if frame is not None else None
    c = _campione_ora(pila)
    try:
        _stop_e_lop(c, t)                       # [FIX 108]
    except Exception:
        pass
    c["lop"] = _run["lop"]
    if _cab["crono"] is not None:               # [FIX 107] cronometro, fasi e storia per la cabina
        try:
            cr = _cab["crono"]
            prima = cr.inizio
            cr.aggiorna(c["sw"], t)
            if cr.inizio != prima:              # gara nuova: le fasi ripartono
                _cab["fasi"].azzera(t)
                _eventi_cab.clear()
            _cab["fasi"].aggiorna(c, t)
            with _lock:
                _storia.append(c)
        except Exception:
            pass
    rec = {"tipo": "c", **c}
    if c["sw"]:
        _scatola["ha_run"] = True
    if RwdConf.SCATOLA_FOTO and t - _scatola["ultima_foto"] >= 0.5:
        _scatola["ultima_foto"] = t
        rec["img_l"] = _miniatura(_G.get("Immagine"))
        if c["cat"] == "arena" or (c["pila"] and c["pila"][0] in ("ArenaAI", "TrovaUscitaIA")):
            rec["img_a"] = _miniatura(_frame_arena[0])
    _scrivi_scatola(rec)


# -------------------------------------------------------------------------------------------
#   SCATOLA NERA (file JSONL: una riga per campione o evento)
# -------------------------------------------------------------------------------------------
_impronta = {}               # [FIX 86] impronta del codice, calcolata una volta sola


def _impronta_codice():
    # [FIX 86] IMPRONTA DEL CODICE: un "codice fiscale" dei file .py della cartella da cui gira il robot.
    # Stesso calcolo di Shuri (batteria.py): sha256 di nome e contenuto di ogni .py, in ordine di nome, prime
    # 16 cifre. Se un ragazzo cambia un parametro senza cambiare VERSIONE, o se nella cartella restano file di
    # versioni diverse, il numero di versione è uguale ma l'impronta no: Shuri se ne accorge.
    if not _impronta:
        import glob, hashlib
        cart = os.path.dirname(os.path.abspath(__file__))
        h, nomi = hashlib.sha256(), []
        try:
            for f in sorted(glob.glob(os.path.join(cart, "*.py"))):
                n = os.path.basename(f)
                nomi.append(n)
                h.update(n.encode())
                with open(f, "rb") as fh:
                    h.update(fh.read())
            _impronta.update(impronta=h.hexdigest()[:16], file=nomi, cartella=cart)
        except Exception as e:
            _impronta.update(impronta="non calcolata", file=nomi, cartella=cart, errore=str(e))
    return _impronta


def _sigla_versione():
    # [FIX 86] "ClaudeRob V29" -> "V29" (per il nome del file della scatola nera)
    m = re.search(r"V\d+", str(RwdConf.VERSIONE))
    return m.group(0) if m else re.sub(r"[^A-Za-z0-9]+", "", str(RwdConf.VERSIONE))[:12] or "V"


def _nuova_scatola():
    if not RwdConf.SCATOLA_NERA:
        return
    try:
        if _scatola["f"]:
            _scatola["f"].close()
            if not _scatola.get("ha_run") and _scatola["nome"]:
                try:
                    os.remove(_scatola["nome"])     # solo attesa a switch spento: non serve
                except Exception:
                    pass
        _scatola["ha_run"] = False
        cart = RwdConf.CARTELLA_SCATOLA
        os.makedirs(cart, exist_ok=True)
        if shutil.disk_usage(cart).free < 500e6:
            _scatola["f"] = None
            evento("Scatola nera sospesa: meno di 500 MB liberi", "errore")
            return
        # [FIX 86] nel nome anche la versione del codice: run_2026-11-02_10-15-30_V29.jsonl (prima la data, così i
        # file restano in ordine di tempo anche mescolando versioni diverse)
        base = os.path.join(cart, "run_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + _sigla_versione())
        nome, k = base + ".jsonl", 2
        while os.path.exists(nome):
            nome, k = f"{base}_{k}.jsonl", k + 1
        _scatola["f"] = open(nome, "w", encoding="utf-8")
        _scatola["nome"] = nome
        imp = _impronta_codice()
        intest = {"tipo": "intestazione", "versione": RwdConf.VERSIONE,
                  "impronta": imp.get("impronta"), "file": imp.get("file"),     # [FIX 86]
                  "cartella_codice": imp.get("cartella"),
                  "inizio": datetime.now().isoformat(timespec="seconds"),
                  "camera_linea": {"altezza_cm": 8.3, "inclinazione_dalla_verticale": 15, "vista_cm": [0, 7.7]},
                  "avvio": list(_eventi_avvio)}                                  # [FIX 114]
        _scatola["f"].write(json.dumps(intest) + "\n")
    except Exception as e:
        _scatola["f"] = None
        _print_orig("[MONITOR] scatola nera non disponibile:", e)


def _scrivi_scatola(rec):
    f = _scatola["f"]
    if f is None:
        return
    try:
        with _lock:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")
            if _ora() - _scatola["ultimo_flush"] > 1.0:
                f.flush()
                _scatola["ultimo_flush"] = _ora()
    except Exception:
        pass


# -------------------------------------------------------------------------------------------
#   PANNELLO DEL TERMINALE
# -------------------------------------------------------------------------------------------
ALTEZZA_PANNELLO = 8
_term = {"righe": 0, "colonne": 0}


def _tty():
    try:
        return _out.isatty() and RwdConf.TERMINALE in ("pannello", "cabina") and not RwdConf.DEBUG
    except Exception:
        return False


def _barra(val, maxv=100, larg=10):
    if not val or val <= 0:
        return "·" * larg
    pieni = int(round(min(val, maxv) / maxv * larg))
    return "█" * pieni + "·" * (larg - pieni)


def _imposta_terminale():
    c, r = shutil.get_terminal_size((100, 30))     # (colonne, righe)
    if (r, c) == (_term["righe"], _term["colonne"]):
        return r, c
    _term.update(righe=r, colonne=c)
    alto = max(3, r - ALTEZZA_PANNELLO)
    _out.write("\033[?25l")                      # nasconde il cursore lampeggiante
    _out.write(f"\033[1;{alto}r")                # gli eventi scorrono solo nella parte alta
    _out.write(f"\033[{alto};1H")
    _out.flush()
    return r, c


def _disegna_pannello():
    c = _campione[0]
    if not c:
        return
    with _lock_term:
        r, col = _imposta_terminale()
        d = c["d"]
        b, ro, rt = (c["imu"] + [0, 0, 0])[:3]
        m, s = divmod(max(c["t"], 0), 60)
        pi = c["pi"]
        y = c["yolo"]
        def tronca(x):
            return x[:col - 1]
        # colore dello stato
        colst = {"linea": "42;30", "incrocio": "43;30", "ostacolo": "45;37", "arena": "46;30",
                 "gara": "44;37", "info": "47;30"}.get(c["cat"], "47;30")
        sw = "\033[32mSWITCH ON\033[0m" if c["sw"] else "\033[31mSWITCH OFF\033[0m"
        stato = c["stato"]
        fr_col = "31;1" if 0 < d[1] < 15 else "0"
        du = c.get("d_ult") or [[0, 0]] * 3
        def dist(i):
            v = d[i]
            if v:
                return f"{v:3d} cm"
            uv, ue = du[i]
            return f"\033[37mfuori portata{f' (era {uv} cm {ue:.1f}s fa)' if uv and ue < 5 else ''}\033[0m"
        alim = ("\033[41;37m SOTTOTENSIONE ADESSO \033[0m" if pi.get("sottotensione")
                else "\033[33mfulmine visto dall'avvio\033[0m" if pi.get("sottotensione_avvenuta") else "\033[32mOK\033[0m")
        batt = (f"{pi['batt_v']:.2f} V {pi['batt_pct']}%" if pi.get("batt_v") else "non misurata")
        verde = f"   \033[32m{c['verde'][:60]}\033[0m" if c["verde"] else ""
        righe = [
            f"\033[1;37;40m {RwdConf.VERSIONE} \033[0m \033[37m{int(m):02d}:{s:04.1f}\033[0m  {sw}  \033[{colst}m {stato} \033[0m",
            (f"\033[1mLASER \033[0m Sx {_barra(d[0], 60)} {dist(0)}   \033[{fr_col}mFronte {_barra(d[1], 60)} {dist(1)}\033[0m   Dx {_barra(d[2], 60)} {dist(2)}"
             if c.get("ard", True) else
             f"\033[1mLASER \033[0m \033[41;37;1m ARDUINO ZITTO da {c.get('ard_muto', 0):.1f} s (switch spento?): laser e giroscopio NON validi \033[0m"),
            f"\033[1mASSETTO\033[0m rotta {rt:4.0f}°   beccheggio {b:+4.0f}°   rollio {ro:+4.0f}°   tilt {c['tilt']}   "
            + _testo_pendenza(c),         # [FIX 82]
            f"\033[1mYOLO  \033[0m linea {y[0] or '-':>3} {y[1]:.2f}   decisioni {c['dec_s']:4.1f}/s   camera {c['fps']:4.1f} fps   {('arena: ' + c['arena']) if c['arena'] else ''}{verde}",
            f"\033[1mORA   \033[0m \033[1;33m{c.get('manovra') or c.get('azione', '')}\033[0m"
            + (f"   \033[37m(ruote: {c.get('azione', '')})\033[0m" if c.get('manovra') else ""),
            f"\033[1mMOTORI\033[0m {c['mot'][0]} vel {c['mot'][1]} sterzo {c['mot'][2]}   braccio {c['br'] if c['br'] is not None else '-'}°  pinza {c['pz'] if c['pz'] is not None else '-'}°   LED {'●' if c['led'][0] else '○'}{'●' if c['led'][1] else '○'}   palline arg {c['pal'][0]} nera {c['pal'][1]}",
            f"\033[1mPI    \033[0m CPU {_f(pi.get('cpu_temp'), '.0f', '°C')}  carico {_f(pi.get('carico'), '.1f')}   5V {_f(pi.get('v5'), '.2f', ' V')}  alimentazione {alim}   batteria {batt}"
            + (f"   cruscotto http://{pi['ip']}:{RwdConf.PORTA_CRUSCOTTO}" if RwdConf.CRUSCOTTO and pi.get("ip") else ""),
            f"\033[37mUltima print: {c['msg']}\033[0m",
        ]
        try:
            _out.write("\0337")                               # salva il cursore (zona eventi)
            for i, riga in enumerate(righe):
                _out.write(f"\033[{r - ALTEZZA_PANNELLO + 1 + i};1H\033[2K" + _taglia_ansi(riga, col - 1))
            _out.write("\0338")                               # torna nella zona eventi
            _out.flush()
        except Exception:
            pass


def _modo_terminale():
    """[FIX 107] "cabina" se è stata scelta e la finestra è abbastanza grande, altrimenti "pannello"."""
    if RwdConf.TERMINALE != "cabina" or _cab["crono"] is None:
        return "pannello"
    import ViennaCabina as VC
    col, righe = shutil.get_terminal_size((80, 24))
    if col >= VC.COLONNE_MIN and righe >= VC.RIGHE_MIN:
        return "cabina"
    if not _cab["avvisato"]:
        _cab["avvisato"] = True
        evento(f"Terminale piccolo ({col} x {righe}): per la CABINA ingranditelo ad almeno "
               f"{VC.COLONNE_MIN} x {VC.RIGHE_MIN}. Intanto uso il pannello di prima", "sistema")
    return "pannello"


def _disegna_cabina():
    """[FIX 107] Ridisegna tutta la cabina di pilotaggio (ViennaCabina.py)."""
    c = _campione[0]
    if not c:
        return
    import ViennaCabina as VC
    col, righe = shutil.get_terminal_size((100, 40))
    ora = _ora()
    with _lock:
        storia = list(_storia)
        evs = list(_eventi_cab)
    tm = _cab["crono"].tempi(ora)
    eta_l = (ora - _t_linea[0]) if _t_linea[0] else None
    eta_a = (ora - _t_arena[0]) if _t_arena[0] else None
    fasi = _cab["fasi"]
    out = VC.schermo(c, storia, evs, fasi.adesso(), fasi.durate(), RwdConf.VERSIONE, tm,
                     _G.get("Immagine"), _frame_arena[0], eta_l, eta_a, min(col - 1, 140), righe - 1)
    with _lock_term:
        try:
            _out.write(VC.disegna(out))
            _out.flush()
        except Exception:
            pass


def _testo_pendenza(c):
    # [FIX 82] "IN PIANO" in verde, il tratto inclinato in giallo
    p = c.get("pend")
    if not p:
        return ""
    if p["tipo"] == "piano":
        return f"\033[32m{p['testo'].upper()}\033[0m"
    if p["tipo"] == "sconosciuto":
        return f"\033[37m{p['testo']}\033[0m"
    return f"\033[43;30m {p['testo']} \033[0m"


def _f(v, fmt, unita=""):
    return "-" if v is None else format(v, fmt) + unita


def _taglia_ansi(s, n):
    """Taglia una stringa con codici colore a n caratteri visibili."""
    out, vis, i = [], 0, 0
    while i < len(s) and vis < n:
        if s[i] == "\033":
            j = s.find("m", i)
            if j < 0:
                break
            out.append(s[i:j + 1])
            i = j + 1
            continue
        out.append(s[i])
        vis += 1
        i += 1
    return "".join(out) + "\033[0m"


def _riga_semplice():
    c = _campione[0]
    if not c:
        return
    d = c["d"]
    y = c["yolo"]
    with _lock_term:
        b, ro, rt = (c["imu"] + [0, 0, 0])[:3]
        pi = c["pi"]
        _print_orig(f"[{c['t']:6.1f}s] {'ON ' if c['sw'] else 'OFF'} | {c['stato']}"
                    + f" | ORA: {c.get('manovra') or c.get('azione', '')}"
                    + (f" | laser Sx {d[0] or 'fuori'} Fr {d[1] or 'fuori'} Dx {d[2] or 'fuori'} cm" if c.get("ard", True)
                       else f" | ARDUINO ZITTO da {c.get('ard_muto', 0):.1f}s (switch spento?)")
                    + f" | rotta {rt} becc {b:+} roll {ro:+}"
                    + (f" ({c['pend']['testo']})" if c.get("pend") else "")    # [FIX 82]
                    + f" | YOLO {y[0] or '-'} {y[1]:.2f} | {c['mot'][0]} vel {c['mot'][1]} sterzo {c['mot'][2]}"
                    f" | braccio {c['br']} pinza {c['pz']} | CPU {_f(pi.get('cpu_temp'), '.0f', 'C')}"
                    + (" | SOTTOTENSIONE" if pi.get('sottotensione') else ""))


# -------------------------------------------------------------------------------------------
#   THREAD DI SFONDO (solo sul robot vero)
# -------------------------------------------------------------------------------------------
_pannello = {"proc": None}


def _avvia_pannello():
    # [FIX 42] apre la finestra "ClaudeRob - STATO" in un processo separato (serve uno schermo, es. VNC)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        evento("Finestra di stato non aperta: nessuno schermo (DISPLAY)", "sistema")
        return
    try:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ViennaPannello.py")
        _pannello["proc"] = subprocess.Popen([sys.executable, script], stdin=subprocess.PIPE,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        evento("Finestra di stato aperta: ClaudeRob - STATO", "sistema")
    except Exception as e:
        evento(f"Finestra di stato non aperta: {e}", "errore")


def _jpeg_camera(img, w=320, h=189):
    """[FIX 51] Fotogramma rimpicciolito in JPEG (base64) per la finestra di stato."""
    if img is None:
        return None
    try:
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        small = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(buf.tobytes()).decode() if ok else None
    except Exception:
        return None


def _manda_al_pannello():
    pr = _pannello["proc"]
    if pr is None or pr.poll() is not None:
        return
    try:
        with _lock:
            c = dict(_campione[0])
            evs = list(_eventi)[-8:]
            reg = [r for r in list(_registro)[-80:] if not r.get("tradotto")][-40:]   # [FIX 47]
        # [FIX 51] le due camere: si manda un fotogramma solo se è nuovo; la finestra mostra da quanto
        # tempo non ne arrivano (la camera arena il programma la usa solo nell'arena)
        ora = _ora()
        cam = {"linea_eta": round(ora - _t_linea[0], 1) if _t_linea[0] else None,
               "arena_eta": round(ora - _t_arena[0], 1) if _t_arena[0] else None,
               "soglia": int(getattr(_webcam, "SOGLIA_NERO", 110) or 110)}
        if _t_linea[0] > _ultimi_inviati["linea"]:
            _ultimi_inviati["linea"] = _t_linea[0]
            cam["linea"] = _jpeg_camera(_G.get("Immagine"))
        if _t_arena[0] > _ultimi_inviati["arena"]:
            _ultimi_inviati["arena"] = _t_arena[0]
            cam["arena"] = _jpeg_camera(_frame_arena[0])
        pr.stdin.write(json.dumps({"c": c, "eventi": evs, "registro": reg, "cam": cam},
                                  separators=(",", ":")) + "\n")
        pr.stdin.flush()
    except Exception:
        _pannello["proc"] = None


def _ciclo():
    ultimo_pi = 0.0
    ultimo_pannello_win = 0.0
    ultimo_pannello = 0.0
    ultima_semplice = 0.0
    while _attivo:
        try:
            t = _ora()
            if t - ultimo_pi > 2.0:
                ultimo_pi = t
                _leggi_pi()
            _campiona_se_serve()
            if t - getattr(_leggi_metadati_camere, "_ultimo", 0.0) >= float(getattr(RwdConf, "CAM_METADATI_INTERVALLO_S", 1.0)):
                _leggi_metadati_camere._ultimo = t
                _leggi_metadati_camere()
            ok, muto = _arduino_ok()
            if not ok and _arduino["ok"]:
                _arduino.update(ok=False, da=t)
                # [FIX 104] quasi sempre è lo switch spento (05/11: il prof spegne lo switch e l'Arduino tace)
                evento("Arduino zitto: switch spento? (se lo switch è acceso: cavo USB, batteria, motori)", "errore")
            elif ok and not _arduino["ok"]:
                _arduino["ok"] = True
                evento(f"Arduino di nuovo OK dopo {t - _arduino['da']:.1f} s di silenzio", "errore")
            if t - ultimo_pannello_win > 0.2:
                ultimo_pannello_win = t
                _manda_al_pannello()
            modo = _modo_terminale() if _tty() else None          # [FIX 107]
            if modo != _cab["modo"] and _tty():
                with _lock_term:
                    _out.write("\033[r\033[2J\033[H")              # si cambia schermata: si ricomincia pulito
                    _out.flush()
                _term.update(righe=0, colonne=0)
                _cab["modo"] = modo
            if modo == "cabina" and t - ultimo_pannello > 0.2:
                ultimo_pannello = t
                _disegna_cabina()
            elif RwdConf.TERMINALE in ("pannello", "cabina") and _tty() and t - ultimo_pannello > 0.2:
                ultimo_pannello = t
                _disegna_pannello()
            elif RwdConf.TERMINALE in ("pannello", "cabina", "semplice") and not _tty() and not RwdConf.DEBUG \
                    and t - ultima_semplice > RwdConf.RIGA_OGNI:
                ultima_semplice = t
                _riga_semplice()
        except Exception:
            pass
        time.sleep(0.1)


# -------------------------------------------------------------------------------------------
#   CRUSCOTTO WEB (solo laboratorio)
# -------------------------------------------------------------------------------------------
def _avvia_cruscotto():
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    cart = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cruscotto")

    class Gestore(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _manda(self, dati, tipo, codice=200):
            self.send_response(codice)
            self.send_header("Content-Type", tipo)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(dati)))
            self.end_headers()
            self.wfile.write(dati)

        def do_GET(self):
            try:
                u = urlparse(self.path)
                p = u.path
                if p in ("/", "/index.html", "/cruscotto.html"):
                    with open(os.path.join(cart, "cruscotto.html"), "rb") as f:
                        return self._manda(f.read(), "text/html; charset=utf-8")
                if p.endswith(".js") and "/" not in p[1:]:
                    with open(os.path.join(cart, p[1:]), "rb") as f:
                        return self._manda(f.read(), "application/javascript")
                if p == "/robot.stl":                         # [FIX 37] il modello 3D del robot (dai file STL)
                    with open(os.path.join(cart, "robot.stl"), "rb") as f:
                        return self._manda(f.read(), "model/stl")
                if p == "/stato":
                    da = int(parse_qs(u.query).get("da", ["0"])[0])
                    with _lock:
                        evs = [e for e in _eventi if e["n"] > da]
                        c = dict(_campione[0])
                    return self._manda(json.dumps({"c": c, "eventi": evs, "versione": RwdConf.VERSIONE,
                                                   "scatola": os.path.basename(_scatola["nome"] or "")}).encode(),
                                       "application/json")
                if p in ("/linea.jpg", "/arena.jpg"):
                    img = _G.get("Immagine") if p == "/linea.jpg" else _frame_arena[0]
                    if img is None:
                        return self._manda(b"", "image/jpeg", 204)
                    if img.ndim == 3 and img.shape[2] == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    return self._manda(buf.tobytes(), "image/jpeg")
                if p == "/scatole":
                    cartella = RwdConf.CARTELLA_SCATOLA
                    nomi = sorted((n for n in os.listdir(cartella) if n.endswith(".jsonl")), reverse=True) \
                        if os.path.isdir(cartella) else []
                    return self._manda(json.dumps(nomi[:50]).encode(), "application/json")
                if p.startswith("/scatola/"):
                    nome = os.path.basename(p[len("/scatola/"):])
                    with open(os.path.join(RwdConf.CARTELLA_SCATOLA, nome), "rb") as f:
                        return self._manda(f.read(), "application/x-ndjson")
                self._manda(b"non trovato", "text/plain", 404)
            except Exception as e:
                try:
                    self._manda(str(e).encode(), "text/plain", 500)
                except Exception:
                    pass

    try:
        srv = ThreadingHTTPServer(("0.0.0.0", RwdConf.PORTA_CRUSCOTTO), Gestore)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True, name="cruscotto").start()
        _pi["ip"] = _ip()
        evento(f"Cruscotto 3D attivo: dal PC aprite http://{_pi['ip']}:{RwdConf.PORTA_CRUSCOTTO}", "sistema")
    except Exception as e:
        evento(f"Cruscotto non avviato: {e}", "errore")


# -------------------------------------------------------------------------------------------
#   AVVIO E CHIUSURA
# -------------------------------------------------------------------------------------------
def avvia(robot, webcam, globali):
    """Da chiamare in RwdFoto.py subito dopo  Rwd = Robot()."""
    global _rwd, _webcam, _G, _attivo, _out
    try:
        _rwd, _webcam, _G = robot, webcam, globali
        _out = sys.stdout
        builtins.print = _print
        _aggancia(robot, "Sterzo", prima=_cmd_sterzo)
        _aggancia(robot, "Stop", prima=_cmd_stop)
        _aggancia(robot, "Gira", prima=_cmd_gira)
        _aggancia(robot, "Dritto", prima=_cmd_dritto)
        _aggancia(robot, "Braccio", prima=_cmd_braccio)
        _aggancia(robot, "Pinza", prima=_cmd_pinza)
        _aggancia(robot, "GetSensori", dopo=_dopo_sensori)
        if SIM:     # nel simulatore non c'è il thread di sfondo: si campiona quando il codice legge i sensori
            _aggancia(robot, "GetGyro", dopo=_dopo_sensori)
            _aggancia(robot, "Distanze", dopo=_dopo_sensori)
        _aggancia(webcam, "VerificaVerde", dopo=_dopo_verifica)
        _aggancia(webcam, "CercaPortaTri", dopo=_dopo_arena("triangolo/porta"))
        _aggancia(webcam, "PallinaNuova", dopo=_dopo_arena("pallina"))
        if getattr(webcam, "CamAr", None) is not None:
            _aggancia(webcam.CamAr, "capture_array", dopo=_dopo_cam_arena)
        if getattr(webcam, "CamSL", None) is not None:
            _aggancia(webcam.CamSL, "capture_array", dopo=_dopo_cam_linea)
        if RwdConf.SCATOLA_NERA:
            _nuova_scatola()
        if SIM:
            return
        _attivo = True
        if RwdConf.TERMINALE == "cabina":       # [FIX 107]
            import ViennaCabina as VC
            _cab["crono"] = VC.Cronometro(getattr(RwdConf, "CRONO_DURATA_S", 480.0),
                                          getattr(RwdConf, "CRONO_NUOVA_GARA_S", 120.0))
            _cab["fasi"] = VC.Fasi()
        if _tty():
            _out.write("\033[2J\033[H")
            _cab["modo"] = _modo_terminale()
            if _cab["modo"] == "pannello":
                _imposta_terminale()
        evento(f"{RwdConf.VERSIONE} avviato", "gara")
        # [FIX 114] il controllo VISTA (FIX 113) è passato in controlli_avvio(), chiamata da RwdFoto.py
        # DOPO la taratura della camera linea (FIX 112).
        if RwdConf.SCATOLA_NERA and _scatola["nome"]:
            evento(f"Scatola nera: {_scatola['nome']}", "sistema")
        if RwdConf.CRUSCOTTO:
            _avvia_cruscotto()
        if getattr(RwdConf, "PANNELLO", False):
            _avvia_pannello()
            if _pannello["proc"] is not None and not getattr(RwdConf, "FINESTRE_CAMERE", False):
                # [FIX 51] le camere sono nella finestra di stato: le vecchie finestre di OpenCV non si aprono più
                # (si bloccavano durante le manovre perché le aggiorna il programma del robot quando può)
                cv2.imshow = lambda *a, **k: None
                evento("Camere nella finestra di stato (vecchie finestre OpenCV spente)", "sistema")
        elif RwdConf.TERMINALE == "cabina" and not getattr(RwdConf, "FINESTRE_CAMERE", False):
            # [FIX 109] finestra di stato spenta: le camere sono nella cabina del terminale; le vecchie finestre OpenCV
            # restano spente lo stesso
            cv2.imshow = lambda *a, **k: None
            evento("Camere nella cabina del terminale (finestra di stato e vecchie finestre OpenCV spente)", "sistema")
        threading.Thread(target=_ciclo, daemon=True, name="monitor").start()
    except Exception as e:
        builtins.print = _print_orig
        _print_orig("[MONITOR] non avviato (il robot funziona lo stesso):", e)


def chiudi():
    """Da chiamare nel blocco finally di RwdFoto.py."""
    global _attivo
    _attivo = False
    try:
        if _pannello["proc"] is not None:
            _pannello["proc"].stdin.close()        # il pannello si chiude da solo
    except Exception:
        pass
    try:
        if _scatola["f"]:
            _scatola["f"].flush()
            _scatola["f"].close()
            _scatola["f"] = None
    except Exception:
        pass
    if not SIM and _tty():
        try:
            r = _term["righe"] or shutil.get_terminal_size((100, 30))[1]
            _out.write(f"\033[r\033[?25h\033[{r};1H\n")
            _out.flush()
        except Exception:
            pass
    builtins.print = _print_orig
