# [FIX 110] UN SOLO PROGRAMMA DEL ROBOT ALLA VOLTA. Se ne partono due (due avvii automatici, o un avvio a mano mentre
# l'altro gira) comandano gli stessi motori e leggono la stessa seriale dell'Arduino. Il primo prende un "lucchetto"
# (file LUCCHETTO in ViennaDataConf.py, bloccato con flock: si libera da solo quando il programma finisce, anche se
# si pianta); il secondo lo trova chiuso, lo dice ed esce PRIMA di aprire camere, seriale e motori.
# Nel simulatore non serve (lì le gare girano anche in parallelo).
import sys as _sys
import ViennaDataConf as RwdConf
if "finto_hw" not in _sys.modules and getattr(RwdConf, "UN_SOLO_PROGRAMMA", True):
    import fcntl as _fcntl
    import os as _os
    import time as _time
    try:
        _lucchetto = open(getattr(RwdConf, "LUCCHETTO", "/tmp/clauderob_robot.lock"), "a+")
        _fcntl.flock(_lucchetto, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        _lucchetto.seek(0)
        _lucchetto.truncate()
        _lucchetto.write(str(_os.getpid()))
        _lucchetto.flush()
    except BlockingIOError:
        try:
            _lucchetto.seek(0)
            _chi = _lucchetto.read().strip()
        except Exception:
            _chi = "?"
        print("\n*** ATTENZIONE: il programma del robot sta GIA' girando (processo " + _chi + "). ***")
        print("*** Questo secondo programma NON parte: due programmi comanderebbero gli stessi motori. ***")
        print("*** Per fermare quello che gira: chiudete la sua finestra, oppure  kill " + _chi + "  ***\n")
        _time.sleep(getattr(RwdConf, "LUCCHETTO_ATTESA_S", 20))     # così si fa in tempo a leggere
        _sys.exit(1)
    except Exception as _e:                                      # niente lucchetto: si parte lo stesso, come prima
        print("[FIX 110] lucchetto non disponibile:", _e)

from ViennaClsRobot import Robot, angle_difference
import ViennaClsWebCam as WebCam
import ViennaDataConf as RwdConf
import ViennaMonitor as Monitor   # [FIX 37] terminale chiaro, scatola nera, cruscotto 3D
import threading
from datetime import datetime
import time
import cv2
import math

PrAng=0
ArenaCompleta=False

Rwd=Robot()
Monitor.avvia(Rwd, WebCam, globals())   # [FIX 37]
VelCross=0
print("avviato robot") 
Arg=0
Nera=0
Immagine = None
# [FIX 21] Memoria degli angoli in arena: un dizionario {classe YOLO: heading}.
# Prima c'erano PosVerde/PosRosso/PosPorta, ma i numeri delle classi usati per
# salvare e per riusare non coincidevano (es. salvato con tipo==2, riusato
# con TipoAzione==3), quindi la memoria non veniva mai usata correttamente.
PosMem = {}


def log(*args):
    # [FIX 10] stampa solo se DEBUG = True in ViennaDataConf
    if RwdConf.DEBUG:
        print(*args)


def MascheraAlta(img):
    # [FIX 9] Copia il fotogramma e copre le prime SogMask righe ripetendo la
    # riga SogMask (usato in salita). Prima si modificava direttamente il
    # fotogramma condiviso con il thread della camera e, in alcuni casi, si
    # analizzava un fotogramma VECCHIO (catturato prima della manovra).
    c = img.copy()
    c[0:RwdConf.SogMask, :] = c[RwdConf.SogMask:RwdConf.SogMask+1, :]
    return c


def NuovaRun():
    # [FIX 7] Azzera lo stato della gara (palline salvate, memoria angoli).
    global Arg, Nera, ArenaCompleta, PosMem, FestaFatta, RottaArena, RiferimentoGriglia, UscitaArenaFatta
    Arg = 0
    Nera = 0
    ArenaCompleta = False
    PosMem = {}
    FestaFatta = False      # [FIX 32]
    RiferimentoGriglia = None   # [FIX 62] direzione delle piastrelle, si rimisura alla partenza
    RottaArena = None       # [FIX 34]
    PorteScartate.clear()   # [FIX 38]
    UscitaArenaFatta = False    # [FIX 66]
    print("NUOVA RUN: contatori azzerati")


RiferimentoGriglia = None   # [FIX 62] direzione delle piastrelle (gradi del giroscopio alla partenza)
UscitaArenaFatta = False    # [FIX 66] True quando il robot è uscito dall'arena (non deve più rientrarci)
StoricoRotta = []           # [FIX 62] (istante, direzione) degli ultimi 2 s di seguilinea
FestaFatta = False
RottaArena = None       # [FIX 34] direzione con cui il robot è entrato nell'arena (le pareti sono
                        # perpendicolari a questa direzione: serve per uscire dritti dalla porta)


def SpostamentoPorta(classe, rotta, rotta_porta):
    # [FIX 35] Quanti cm è spostato il centro del robot rispetto al centro della porta
    # (positivo = porta a destra). Si guardano i due stipiti nell'immagine: dall'angolo di
    # ciascuno e dalla larghezza vera della porta si ricava sia la distanza dal muro sia lo
    # spostamento laterale. Non serve sapere quanto è lontana la porta.
    # Se uno stipite esce dall'immagine il robot ruota di 20 gradi da quel lato e riguarda;
    # se la porta non si vede ruota verso dove l'aveva vista arrivando, poi arretra un po'.
    # Restituisce (spostamento in cm oppure None, secondi di retromarcia in più)
    indietro = 0.0
    girato_verso_porta = False
    ultimo_giro = 0
    k = math.tan(math.radians(112 * RwdConf.GradiPerPixelArena)) / 112    # pixel -> tangente
    for tentativo in range(6):
        time.sleep(0.15)
        ImmArena = WebCam.CamAr.capture_array()
        array = cv2.resize(ImmArena, (224, 224), interpolation=cv2.INTER_AREA)
        trovato, _, cx, _, _, _ = WebCam.CercaPortaTri(array, classe)
        _, _, hd = Rwd.GetGyro()
        psi = angle_difference(hd, rotta)              # quanto sono ruotato rispetto alla perpendicolare
        if trovato and WebCam.UltimoBox is not None:
            x1, _, x2, _ = WebCam.UltimoBox
            print(f"Porta vista da x={x1} a x={x2}, robot ruotato di {psi:.0f} gradi")
            if x1 > 3 and x2 < 220 and x2 - x1 > 10:   # entrambi gli stipiti dentro l'immagine
                t1 = math.tan(math.radians(psi) + math.atan((x1 - 112) * k))
                t2 = math.tan(math.radians(psi) + math.atan((x2 - 112) * k))
                if t2 - t1 > 0.05:
                    dist = RwdConf.LarghezzaPorta / (t2 - t1)      # distanza camera-muro
                    spost = dist * (t1 + t2) / 2 + RwdConf.DistanzaCameraArena * math.sin(math.radians(psi))
                    return spost, indietro
            elif abs(psi) < 45 and not (x1 <= 3 and x2 >= 220):   # tagliato da un lato solo
                giro = 20 if x2 >= 220 else -20                     # guardo verso lo stipite tagliato
                if ultimo_giro == -giro:
                    # ho appena guardato dall'altra parte: la porta è più larga dell'inquadratura,
                    # sono troppo vicino. Torno perpendicolare e arretro.
                    Rwd.Gira(angle_difference(rotta, hd), VelArena)
                    Rwd.Stop()
                    ultimo_giro = 0
                else:
                    Rwd.Gira(giro, VelArena)
                    Rwd.Stop()
                    ultimo_giro = giro
                    continue
        else:
            print("Porta non trovata dalla camera")
            if not girato_verso_porta:
                girato_verso_porta = True
                scarto = max(-40, min(40, angle_difference(rotta_porta, rotta)))   # dove l'avevo vista
                if abs(scarto) > 10:
                    Rwd.Gira(angle_difference((rotta + scarto) % 360, hd), VelArena)
                    Rwd.Stop()
                    continue
        if tentativo < 5:
            Rwd.Sterzo(-VelArena, 0)
            time.sleep(0.3)
            Rwd.Stop()
            indietro += 0.3
    return None, indietro


def CentraSullaPorta(rotta, classe, rotta_porta):
    # [FIX 35] Prima il robot arrivava alla porta spostato di lato di 8-10 cm (anche 30 se
    # arrivava in diagonale) e lo spigolo dell'apertura gli prendeva la fiancata.
    # Ora: misura lo spostamento con la camera, trasla di lato (gira di 90 gradi, avanza,
    # torna perpendicolare) e RIMISURA, fino a 3 volte, finché è centrato entro TolleranzaPorta.
    # Per traslare usa il laser frontale (che dopo la svolta guarda la parete laterale) se la
    # lettura è credibile, altrimenti il tempo con VelocitaArenaCmS: la rimisura corregge l'errore.
    # Restituisce i secondi di retromarcia in più fatti per vedere la porta.
    indietro = 0.0
    for giro in range(3):
        spost, indietro_mis = SpostamentoPorta(classe, rotta, rotta_porta)
        indietro += indietro_mis
        if spost is None or abs(spost) <= RwdConf.TolleranzaPorta:
            print("Centratura porta:", "porta non misurabile, salto la correzione" if spost is None else f"centrato ({spost:.1f} cm)")
            break
        print(f"Centratura porta: spostato di {spost:.1f} cm, mi sposto di lato")
        lato = 1 if spost > 0 else -1
        rotta_lato = (rotta + 90 * lato) % 360
        _, _, hd = Rwd.GetGyro()
        Rwd.Gira(angle_difference(rotta_lato, hd), VelArena)
        Rwd.Stop()
        time.sleep(0.2)
        _, f0, _ = Rwd.Distanze()
        if abs(spost) + 15 < f0 < RwdConf.LaserMaxAffidabile:     # davanti c'è la parete, lontana il giusto
            for _ in range(RwdConf.PassiMaxPorta):
                _, f, _ = Rwd.Distanze()
                if f <= f0 - abs(spost) or 0 < f < 12:
                    break
                Rwd.Dritto(int(VelArena * 0.7), 0.1, heading_ref=rotta_lato)
        else:                                       # lettura non credibile (palline, triangolo, troppo lontano)
            Rwd.Dritto(int(VelArena * 0.7), abs(spost) / RwdConf.VelocitaArenaCmS, heading_ref=rotta_lato)
        Rwd.Stop()
        _, _, hd = Rwd.GetGyro()
        Rwd.Gira(angle_difference(rotta, hd), VelArena)
        Rwd.Stop()
        time.sleep(0.2)
    _, _, hd = Rwd.GetGyro()
    Rwd.Gira(angle_difference(rotta, hd), VelArena)    # di nuovo perpendicolare (potrei aver ruotato per guardare)
    Rwd.Stop()
    return indietro


def LaserVeri():
    # [FIX 48] Come Rwd.Distanze(), ma uno 0 (laser fuori portata: non vede niente entro 1,2 m) diventa
    # LASER_LONTANO. Prima, guardando fuori dalla porta d'uscita, il laser frontale mandava 0 e il codice
    # lo prendeva per "muro a meno di 35 cm": partiva la ricerca della porta lungo la parete (video del 15/10).
    # Se Arduino non risponde da più di 0,3 s gli 0 sono finti e restano 0.
    d = Rwd.Distanze()
    if time.time() - getattr(Rwd, "_last_packet_time", 0) > 0.3:
        return d
    return tuple(RwdConf.LASER_LONTANO if v == 0 else v for v in d)


def AvvicinatiAllaPorta(rotta_porta):
    # [FIX 48] PRIMA IL PAVIMENTO, POI I LASER. Arrivato alla porta il robot avanza piano verso di essa
    # (al massimo AvvicinamentoPorta cm) guardando sotto il muso con la camera linea:
    #   striscia NERA    -> è l'uscita: torna dove era partito e restituisce "uscita"
    #   striscia ARGENTO -> è l'ingresso: torna dove era partito e restituisce "ingresso"
    #   muro davanti o nessuna striscia -> torna dove era partito, restituisce None
    # Torna sempre indietro perché poi EsciDallaPorta si CENTRA sulla porta prima di uscire: uscendo
    # subito appena vista la striscia, se il robot non era centrato prendeva lo stipite (simulatore).
    # Prima il robot, arrivato davanti alla porta, tornava subito indietro di 1 s allontanandosi
    # proprio dalla striscia nera, e si affidava ai laser.
    _, _, hd = Rwd.GetGyro()
    Rwd.Gira(angle_difference(rotta_porta, hd), VelArena)
    Rwd.Stop()
    VelP = int(VelArena * 0.7)                       # VelocitaArenaCmS è misurata a questa velocità
    durata = RwdConf.AvvicinamentoPorta / RwdConf.VelocitaArenaCmS
    print("Avanzo verso la porta guardando il pavimento")
    t0 = time.time()
    while time.time() - t0 < durata:
        cosa, angolo = GuardaPavimento(apertura_davanti=True)
        if cosa == "nero":
            fatto = time.time() - t0
            Rwd.Stop()
            print("Striscia NERA: questa porta è l'USCITA. Torno indietro e mi centro prima di uscire")
            Rwd.Dritto(-VelP, fatto, heading_ref=rotta_porta)
            Rwd.Stop()
            return "uscita"
        if cosa == "argento":
            fatto = time.time() - t0
            Rwd.Stop()
            print("Striscia ARGENTO sotto il muso: questa è l'INGRESSO, torno indietro")
            PorteScartate.append(rotta_porta)
            Rwd.Dritto(-VelP, fatto + 0.2, heading_ref=rotta_porta)
            Rwd.Stop()
            return "ingresso"
        _, dFr, _ = LaserVeri()
        if dFr < 8:
            print("Davanti c'è il muro: non sono dentro l'apertura")
            break
        Rwd.Dritto(VelP, 0.1, heading_ref=rotta_porta)
    fatto = time.time() - t0
    Rwd.Stop()
    print("Nessuna striscia sotto il muso: torno indietro e uso i laser")
    Rwd.Dritto(-VelP, fatto, heading_ref=rotta_porta)
    Rwd.Stop()
    return None


def EsciDallaPorta(rotta_porta, classe=0):
    # [FIX 34] USCITA DALLA PORTA con giroscopio e laser, senza manovre a tempo.
    # Prima, arrivato davanti alla porta, il robot faceva archi a tempo (indietro, Gira(7),
    # Sterzo(±60) per 1,3 s): se arrivava in diagonale o spostato di lato, finiva contro la parete.
    # 1) direzione perpendicolare al muro della porta (multiplo di 90° rispetto all'ingresso)
    if RottaArena is not None:
        k = round(angle_difference(rotta_porta, RottaArena) / 90.0)
        rotta = (RottaArena + 90 * k) % 360
    else:
        rotta = rotta_porta
    print(f"Uscita: porta verso {rotta_porta:.0f} gradi, esco perpendicolare a {rotta:.0f} gradi")
    # [FIX 48] 0) prima guardo il pavimento avvicinandomi alla porta: se c'è la striscia nera esco subito
    esito = AvvicinatiAllaPorta(rotta_porta)
    if esito == "ingresso":
        return "ingresso"
    confermata = esito == "uscita"     # striscia nera vista: la porta è davanti, i laser non servono
    Rwd.Sterzo(-VelArena, 0)            # [FIX 35] mi allontano: spazio per girare e porta tutta nell'immagine
    time.sleep(RwdConf.TempoIndietroPorta)
    Rwd.Stop()
    _, _, hd = Rwd.GetGyro()
    Rwd.Gira(angle_difference(rotta, hd), VelArena)
    Rwd.Stop()
    time.sleep(0.2)
    indietro = CentraSullaPorta(rotta, classe, rotta_porta)  # [FIX 35]
    dSx, dFr, dDx = LaserVeri()     # [FIX 48] prima Rwd.Distanze(): lo 0 "fuori portata" sembrava un muro
    # 2) se davanti c'è il muro la porta è di lato: scorro lungo la parete
    #    [FIX 48] solo se la striscia nera non ha già confermato che l'uscita è proprio davanti
    if not confermata and dFr < RwdConf.DistanzaLiberoPorta:
        lato = 1 if angle_difference(rotta_porta, rotta) > 0 else -1
        print("Muro davanti: scorro lungo la parete verso", "destra" if lato > 0 else "sinistra")
        Rwd.Gira(90 * lato, VelArena)
        Rwd.Stop()
        rotta_lungo = (rotta + 90 * lato) % 360
        trovata = False
        for _ in range(RwdConf.PassiMaxPorta):
            Rwd.Dritto(int(VelArena * 0.7), 0.1, heading_ref=rotta_lungo)
            cosa, angolo = GuardaPavimento(apertura_davanti=False)   # [FIX 48] anche qui guardo il pavimento
            if cosa == "nero":
                EsciSullaStriscia(angolo)
                return True
            dSx, dFr2, dDx = LaserVeri()             # [FIX 48] laterale a 0 = guarda dentro l'apertura
            laterale = dSx if lato > 0 else dDx      # la parete ora è dal lato opposto alla svolta
            if laterale > RwdConf.DistanzaLiberoPorta:
                trovata = True                       # il laser laterale guarda dentro l'apertura
                break
            if 0 < dFr2 < 12:
                break                                # angolo della stanza: la porta non è di qua
        if not trovata:
            Rwd.Stop()
            return False
        Rwd.Dritto(int(VelArena * 0.7), RwdConf.TempoCentroPorta, heading_ref=rotta_lungo)   # mi centro
        Rwd.Stop()
        _, _, hd = Rwd.GetGyro()
        Rwd.Gira(angle_difference(rotta, hd), VelArena)
        Rwd.Stop()
    # 3) esco dritto
    print("Esco dalla porta")
    # [FIX 46] esco guardando il pavimento: se passo sull'argento era l'ingresso e torno dentro
    esito_u = EsciControllando(rotta, RwdConf.TempoUscitaPorta + RwdConf.TempoIndietroPorta + indietro)
    if esito_u == "ingresso":
        return "ingresso"
    return esito_u != "bloccato"                       # [FIX 84] bloccato contro lo stipite: non sono uscito


PorteScartate = []      # [FIX 38] rotte (gradi) in cui il robot ha riconosciuto l'INGRESSO


def ControllaApertura():
    # [FIX 38] Con il muso dentro un'apertura del muro guarda il pavimento con la camera linea:
    # striscia ARGENTO = ingresso, striscia NERA = uscita, altrimenti None.
    img = Immagine
    if img is None:
        return None
    img = img.copy()
    cls, conf, _, _ = WebCam.VerificaVerde(img)
    if cls == "In":
        return "ingresso"
    if WebCam.StrisciaNera(img) is not None:
        return "uscita"
    return None


def ProvaApertura(rotta):
    # [FIX 38] Il robot è girato verso un'apertura: avanza piano finché la camera linea vede una striscia.
    # Restituisce (esito, passi fatti): esito = "uscita", "ingresso", "muro" o None.
    esito, passi = None, 0
    for passi in range(1, RwdConf.PassiAperturaMax + 1):
        esito = ControllaApertura()
        if esito:
            break
        _, dFr, _ = Rwd.Distanze()
        if 0 < dFr < 8:
            esito = "muro"
            break
        Rwd.Dritto(int(VelArena * 0.5), 0.1, heading_ref=rotta)
    Rwd.Stop()
    return esito, passi


def GuardaPavimento(apertura_davanti=True):
    # [FIX 39] Cosa c'è sotto il muso? "nero" (uscita, restituisce anche l'inclinazione), "argento" (ingresso) o None.
    # La striscia nera si controlla sempre (costa poco); l'argento con YOLO solo se davanti c'è un'apertura.
    img = Immagine
    if img is None:
        return None, None
    img = img.copy()
    angolo = WebCam.StrisciaNera(img)
    if angolo is not None or apertura_davanti:
        if WebCam.VerificaVerde(img)[0] == "In":
            return "argento", None
    if angolo is not None:
        return "nero", angolo
    return None, None


NeroScartatoFino = 0.0      # [FIX 104] fino a quando non considerare la striscia nera (era davanti a un muro)


def ScartaNero(motivo):
    # [FIX 104] la striscia nera appena vista non porta a una porta: per USCITA_NERO_PAUSA_S non la si guarda più,
    # altrimenti il giro dei muri la ritroverebbe subito e ci riproverebbe all'infinito
    global NeroScartatoFino
    NeroScartatoFino = time.time() + getattr(RwdConf, "USCITA_NERO_PAUSA_S", 6.0)
    print("Uscita: " + motivo)


def EsciSullaStriscia(angolo):
    # [FIX 39] Il muso è sulla striscia nera: mi metto perpendicolare alla striscia ed esco dritto.
    print(f"Striscia NERA sotto il muso (inclinata di {angolo:.0f} gradi): è l'USCITA")
    Rwd.Stop()
    Rwd.Gira(max(-80, min(80, angolo)), VelArena)
    Rwd.Stop()
    print("Esco dalla porta")
    _, _, hd = Rwd.GetGyro()
    return EsciControllando(hd, RwdConf.TempoUscitaPorta, nero_gia_visto=True) not in ("ingresso", "bloccato")   # [FIX 46] [FIX 104]


def PerimetroUscita(lato=1, davanti_al_muro=True):
    # [FIX 38] CERCA L'USCITA SEGUENDO I MURI con il laser laterale.
    # Serve quando la camera non distingue l'uscita dall'ingresso, come nell'arena della scuola dove
    # sono sullo stesso muro, separati da un pezzo di parete (video dell'8/10).
    # Il robot tiene il muro a DistanzaMuro cm; agli angoli (o davanti a un triangolo) gira di 90 gradi;
    # quando il laser laterale vede un'apertura si ferma a metà, si gira e controlla la striscia:
    # NERA = esce, ARGENTO = è l'ingresso, torna sul muro e prosegue.
    VelP = int(VelArena * 0.7)
    print("Giro dei muri: lato", "sinistro" if lato > 0 else "destro", "verso il muro")
    # 1) mi metto perpendicolare al muro più vicino a dove guardo (le pareti sono a multipli di 90 gradi
    #    rispetto alla direzione con cui sono entrato nell'arena) e ci vado vicino
    _, _, hd = Rwd.GetGyro()
    if RottaArena is not None:
        rotta = (RottaArena + 90 * round(angle_difference(hd, RottaArena) / 90.0)) % 360
    else:
        rotta = hd
    Rwd.Sterzo(-VelArena, 0)                         # un po' di spazio per girare
    time.sleep(0.4)
    Rwd.Stop()
    _, _, hd = Rwd.GetGyro()
    Rwd.Gira(angle_difference(rotta, hd), VelArena)
    Rwd.Stop()
    for _ in range(80):                              # avanti fino al muro (max 8 s)
        _, dFr, _ = LaserVeri()                      # [FIX 48]
        if 0 < dFr < RwdConf.DistanzaMuro + 8:
            break
        cosa, angolo = GuardaPavimento(apertura_davanti=dFr > RwdConf.DistanzaLiberoPorta)   # [FIX 39]
        if cosa == "nero":
            EsciSullaStriscia(angolo)
            return True
        if cosa == "argento":
            print("Davanti c'è l'ingresso: non ci passo")
            Rwd.Sterzo(-VelArena, 0)
            time.sleep(0.6)
            Rwd.Stop()
            break
        Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
    Rwd.Stop()
    # 2) giro di 90 gradi: il muro resta di fianco
    _, _, hd = Rwd.GetGyro()
    rotta = (rotta + 90 * lato) % 360                # lato=+1: giro a destra e il muro resta a SINISTRA
    Rwd.Gira(angle_difference(rotta, hd), VelArena)
    Rwd.Stop()
    passi_fuori = 0
    passo = 0
    passi_meta = max(1, int(round(RwdConf.LarghezzaPorta / 2 / (RwdConf.VelocitaArenaCmS * 0.1))))
    t0 = time.time()
    while time.time() - t0 < RwdConf.TempoMaxPerimetro:
        sensori = Rwd.GetSensori()
        _, SwSf = sensori['switch']
        if not SwSf:
            Rwd.Stop()
            return False
        dSx, dFr, dDx = LaserVeri()       # [FIX 48] prima sensori['distanze']: un'apertura (laser a 0) non veniva vista
        muro = dSx if lato > 0 else dDx
        # la camera linea guarda il pavimento sotto il muso: se passo sopra la striscia NERA sono all'uscita
        # (succede quando l'uscita è proprio in fondo al muro che sto seguendo)
        passo += 1
        cosa, angolo = GuardaPavimento(apertura_davanti=(passo % 2 == 0 and dFr > RwdConf.DistanzaLiberoPorta))
        if cosa == "nero":
            EsciSullaStriscia(angolo)
            return True
        argento = cosa == "argento"
        if argento:
            print("Striscia ARGENTO davanti: è l'ingresso, non ci passo")
            PorteScartate.append(rotta)
            Rwd.Sterzo(-VelP, 0)
            time.sleep(0.6)
            Rwd.Stop()
        if argento or 0 < dFr < RwdConf.DistanzaAngolo:   # angolo, triangolo o ingresso davanti: giro dalla parte opposta al muro
            Rwd.Stop()
            rotta = (rotta + 90 * lato) % 360
            _, _, hd = Rwd.GetGyro()
            Rwd.Gira(angle_difference(rotta, hd), VelArena)
            Rwd.Stop()
            passi_fuori = 0
            continue
        if muro > RwdConf.DistanzaLiberoPorta:        # il laser laterale guarda dentro un'apertura
            passi_fuori += 1
            if passi_fuori < passi_meta:
                Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
                continue
            Rwd.Stop()
            verso_muro = (rotta - 90 * lato) % 360
            _, _, hd = Rwd.GetGyro()
            Rwd.Gira(angle_difference(verso_muro, hd), VelArena)
            Rwd.Stop()
            time.sleep(0.2)
            esito, passi = ProvaApertura(verso_muro)
            print("Apertura nel muro:", {"uscita": "striscia NERA, è l'USCITA", "ingresso": "striscia ARGENTO, è l'ingresso",
                                         "muro": "era un ostacolo"}.get(esito, "nessuna striscia"))
            if esito == "uscita":
                print("Esco dalla porta")
                EsciControllando(verso_muro, RwdConf.TempoUscitaPorta, nero_gia_visto=True)   # [FIX 46]
                return True
            if esito == "ingresso":
                PorteScartate.append(verso_muro)
            Rwd.Sterzo(-VelP, 0)                      # torno sul percorso lungo il muro
            time.sleep(passi * 0.1 + 0.2)
            Rwd.Stop()
            _, _, hd = Rwd.GetGyro()
            Rwd.Gira(angle_difference(rotta, hd), VelArena)
            Rwd.Stop()
            for _ in range(30):                       # supero l'apertura finché il laser rivede il muro
                Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
                d = LaserVeri()                       # [FIX 48]
                m = d[0] if lato > 0 else d[2]
                if 0 < m < RwdConf.DistanzaLiberoPorta or 0 < d[1] < RwdConf.DistanzaAngolo:
                    break
            passi_fuori = 0
            continue
        passi_fuori = 0
        if muro == 0:                                 # lettura non valida (Arduino muto): vado dritto
            Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
            continue
        corr = max(-15.0, min(15.0, (muro - RwdConf.DistanzaMuro) * 1.5))
        Rwd.Dritto(VelP, 0.1, heading_ref=(rotta - lato * corr) % 360)   # mi avvicino o mi allontano dal muro
    Rwd.Stop()
    return False


def Festeggia():
    # [FIX 32] FESTEGGIAMENTO ALL'ARRIVO: gioco di luci, braccio che si alza, pinza 3 volte.
    # Le ruote restano ferme: il robot non si muove dalla linea rossa.
    print("FESTA! Percorso completato")
    Rwd.Stop()
    L1 = Rwd.linee['Luce1']
    L2 = Rwd.linee['Luce2']        # relè attivi bassi: value = 0 -> LED acceso
    # 1) i due LED si alternano
    for _ in range(RwdConf.FESTA_LAMPEGGI):
        L1.value, L2.value = 0, 1
        time.sleep(RwdConf.FESTA_TEMPO_LED)
        L1.value, L2.value = 1, 0
        time.sleep(RwdConf.FESTA_TEMPO_LED)
    # 2) il braccio si alza piano, con entrambi i LED accesi
    L1.value, L2.value = 0, 0
    Rwd.Braccio(RwdConf.FESTA_BRACCIO_BASSO)
    time.sleep(0.4)
    passo = -2 if RwdConf.FESTA_BRACCIO_ALTO < RwdConf.FESTA_BRACCIO_BASSO else 2
    for angolo in range(RwdConf.FESTA_BRACCIO_BASSO, RwdConf.FESTA_BRACCIO_ALTO + passo, passo):
        Rwd.Braccio(angolo)
        time.sleep(0.02)
    # 3) la pinza si apre e si chiude, i LED lampeggiano a tempo
    for _ in range(RwdConf.FESTA_PINZA_VOLTE):
        Rwd.Pinza(RwdConf.FESTA_PINZA_APERTA)
        L1.value, L2.value = 0, 1
        time.sleep(0.35)
        Rwd.Pinza(RwdConf.FESTA_PINZA_CHIUSA)
        L1.value, L2.value = 1, 0
        time.sleep(0.35)
    # 4) fine: LED accesi un secondo, poi spenti
    L1.value, L2.value = 0, 0
    time.sleep(1.0)
    L1.value, L2.value = 1, 1
    print("Festa finita")


def GiraVersoMemoria(TipoAzione):
    # [FIX 21] Se abbiamo già visto questo elemento, giriamo verso l'angolo
    # memorizzato. angle_difference evita giri inutili (es. 350° invece di -10°).
    if TipoAzione in PosMem:
        _, _, AngCor = Rwd.GetSensori()['imu']
        Rwd.Gira(angle_difference(PosMem[TipoAzione], AngCor), VelArena)


def MemorizzaPosizione(tipo):
    # [FIX 21] Salva l'angolo della prima volta che vediamo questa classe
    if tipo is not None and tipo not in PosMem:
        _, _, AngCor = Rwd.GetSensori()['imu']
        PosMem[tipo] = AngCor
        log("Memorizzata classe", tipo, "a", AngCor, "gradi")


def Cattura():
    global Immagine
    while True:
        Immagine = WebCam.CamSL.capture_array()   
        Imma=Immagine
        time.sleep(0.04)
        '''
        array = cv2.resize(Imma, (224, 224), interpolation=cv2.INTER_AREA)
        ora = datetime.now()
        if True:
            if array is not None:
                #i+=1
                #cv2.imshow("Foto Scattata", array)
                cv2.imwrite(f"/home/pi/OneDrive/FotoAzione/FotoA{datetime.now()}.jpg", array)
                #print(f"foto{datetime.now()}.jpg salvata")
                time.sleep(0.15)
        '''
def FotogrammaNuovo(n=2, tmax=0.5):
    # [FIX 44] Aspetta n fotogrammi NUOVI della camera linea (scattati dopo questo momento).
    # Dopo una rotazione il fotogramma in memoria può essere stato scattato mentre il robot girava ancora.
    vecchio = Immagine
    visti = 0
    t0 = time.time()
    while visti < n and time.time() - t0 < tmax:
        if Immagine is not vecchio:
            visti += 1
            vecchio = Immagine
        time.sleep(0.01)
    return Immagine


VideoThred = threading.Thread(target=Cattura, daemon=True)
VideoThred.start()

print("Avviata CAM Seguilinea")

############## SEGUILINEA   ###############
Kp=RwdConf.Kp
Ki=RwdConf.Ki
Kd=RwdConf.Kd

Vel=RwdConf.Vel
VelCross=RwdConf.VelCrs
Alfa = RwdConf.Alfa
VelArena=RwdConf.VelArena
VelSl=Vel
def compute_tilt(pitch, roll):
    return math.sqrt(pitch*pitch + roll*roll)


def AbbassaPinza():
    VelAz=0.03       # Per rallentare  AUMENTA per accellerare diminuisci
    pas=2
    Start=40    #20
    End=178
    for i in range(Start,End+pas,pas):
        Rwd.Braccio(i)
        time.sleep(VelAz)
  
def AlzaPinza():
    VelAz=0.03      # Per rallentare  AUMENTA per accellerare diminuisci
    pas=-2
    Start=178
    End=40  #20
    for i in range(Start,End+pas,pas):
        Rwd.Braccio(i)
        time.sleep(VelAz)
  
        
def CaricaPalla():
    VelAz=0.05      # Per rallentare  AUMENTA per accellerare diminuisci
    pas=-5
    Start=170
    End=40  #20
    for i in range(Start,End+pas,pas):
        if i== 60:
            Rwd.Pinza(120)
            time.sleep(0.1)
            Rwd.Pinza(98)
            time.sleep(0.1)
            Rwd.Pinza(120)
            time.sleep(0.1)
            Rwd.Pinza(98)            
        Rwd.Braccio(i)
        time.sleep(VelAz)


def ApriPinza():
    VelAz=0.05      # Per rallentare  AUMENTA per accellerare diminuisci
    pas=2
    Start=98 #95
    End=160
    for i in range(Start,End+pas,pas):
        Rwd.Pinza(i)
        time.sleep(VelAz)

    
def ChiudiPinza():
    VelAz=0.05      # Per rallentare  AUMENTA per accellerare diminuisci
    pas=-2
    Start=160
    End=98 #95 
    
    for i in range(Start,End+pas,pas):
        Rwd.Pinza(i)
        time.sleep(VelAz)

def SvuotaPinza():
    VelAz=0.03       # Per rallentare  AUMENTA per accellerare diminuisci
    pas=2
    Start=40
    End=116
    for i in range(Start,End+pas,pas):
        Rwd.Braccio(i)
        time.sleep(VelAz)  
    ApriPinza()
    time.sleep(2)
    Rwd.Braccio(120)
    time.sleep(0.05)
    Rwd.Braccio(116)
    time.sleep(0.05)
    Rwd.Braccio(120)
    time.sleep(0.05)    
    Rwd.Braccio(116)
    time.sleep(0.05)    
    pas2=-2
    Start2=116
    End2=40  
    for i in range(Start2,End2+pas,pas2):
        Rwd.Braccio(i)
        time.sleep(VelAz)    
    Rwd.Braccio(End2)


def AvanzaSullIncrocio(tempo_riserva):
    # [FIX 41] PORTA IL CENTRO DELLE RUOTE SOPRA L'INCROCIO prima di girare.
    # Il robot gira attorno al centro delle ruote, che è 11,5 cm dietro il muso. Prima avanzava per un
    # tempo fisso e nel video del 12/10 iniziava a girare circa 11 cm prima dell'incrocio: dopo la
    # svolta la linea nuova restava di lato e il seguilinea lo riportava sulla linea vecchia.
    # Ora guarda la linea trasversale scorrere nell'immagine: da come si sposta calcola la velocità vera
    # e, quando la linea passa sotto il muso, avanza ancora di DistanzaMusoRuote cm.
    # Se la linea trasversale non si vede, avanza per il tempo di prima (tempo_riserva).
    _, _, h0 = Rwd.GetGyro()
    t0 = time.time()
    Rwd.Sterzo(VelCross, 0)
    oss = []
    while time.time() - t0 < 1.5:
        cm = WebCam.DistanzaLineaTrasversale(Immagine)
        if cm is None:
            break
        if not oss or oss[-1][1] != cm:
            oss.append((time.time(), cm))
        time.sleep(0.03)
    v = None
    if len(oss) >= 2 and oss[-1][0] - oss[0][0] > 0.1 and oss[0][1] - oss[-1][1] > 1.0:
        v = (oss[0][1] - oss[-1][1]) / (oss[-1][0] - oss[0][0])          # cm/s
    if v and 3 < v < 60:
        resto = (RwdConf.DistanzaMusoRuote + max(0.0, oss[-1][1])) / v - (time.time() - oss[-1][0])
        time.sleep(max(0.0, min(1.5, resto)))
        print(f"Incrocio: velocità {v:.0f} cm/s, ruote sopra l'incrocio")
    else:
        time.sleep(max(0.0, tempo_riserva - (time.time() - t0)))
    return h0


def CompletaSvolta(verso, h0=None):
    # [FIX 41] FINISCE LA SVOLTA: dopo la svolta di base (SVOLTA_BASE gradi) il robot continua a ruotare
    # PIANO sul posto finché la linea nuova è davanti al muso. Non usa tanti Gira(10): con angoli così
    # piccoli Gira supera il bersaglio (nel simulatore 25-30 gradi per ogni "10").
    # Non gira mai oltre SVOLTA_MAX gradi dalla direzione di partenza; se non trova la linea si mette
    # a 90 gradi esatti col giroscopio e lascia fare al seguilinea.
    t0 = time.time()
    while time.time() - t0 < 3.0:
        if WebCam.LineaAlCentro(Immagine):
            Rwd.Stop()
            if h0 is not None:
                _, _, hd = Rwd.GetGyro()
                print(f"Svolta completata: linea davanti dopo {abs(angle_difference(hd, h0)):.0f} gradi")
            return True
        if h0 is not None:
            _, _, hd = Rwd.GetGyro()
            if abs(angle_difference(hd, h0)) >= RwdConf.SVOLTA_MAX:
                break
        Rwd.Sterzo(RwdConf.VelCrs, 100 * verso)    # rotazione lenta sul posto
        time.sleep(0.04)
    Rwd.Stop()
    if h0 is not None:
        _, _, hd = Rwd.GetGyro()
        Rwd.Gira(angle_difference((h0 + 90 * verso) % 360, hd), VelCross)
        Rwd.Stop()
    print("Svolta: linea non trovata davanti, mi metto a 90 gradi e continua il seguilinea")
    return False


FineSvoltaVerde = 0.0       # [FIX 92] quando è finita l'ultima svolta al verde (destra o sinistra)
SvoltaAttesa = None         # [FIX 71] (istante, direzione attesa dopo l'ultima svolta a 90 gradi a un incrocio)
                            # [FIX 101] + verso della svolta (+1 destra, -1 sinistra)
IngressoLato = 0            # [FIX 101] da che parte spostarsi davanti alla porta: +1 destra, -1 sinistra, 0 non si sa
UltimaAltalena = 0.0        # [FIX 102] istante dell'ultima altalena riconosciuta


def AvviaPausaVerdi():
    # [FIX 80] Svolta al verde finita: finché l'incrocio della svolta è ancora nella camera (al massimo
    # VERDE_PAUSA_S secondi) lo stesso incrocio non si rivaluta (scatola nera 29/10: finendo la curva il robot
    # lo ha rivisto di traverso e ha fatto un dietrofront sbagliato). Vedi VerificaVerde in ViennaClsWebCam.
    global FineSvoltaVerde
    WebCam.PausaVerdi[0] = time.time() + getattr(RwdConf, "VERDE_PAUSA_S", 0.0)
    WebCam.PausaSenzaVerde[0] = 0
    FineSvoltaVerde = time.time()                   # [FIX 92]


def ConfermaDietrofront():
    # [FIX 79] DIETROFRONT SOLO SE SICURO. Un dietrofront sbagliato fa ripercorrere la pista al contrario (e
    # spesso costa la LoP). Prima di farlo il robot si ferma, prende un fotogramma NUOVO e lo ricontrolla:
    # YOLO deve dire di nuovo "Fr" e i colori non devono dire il contrario. Se no, niente dietrofront: il
    # seguilinea continua e il prossimo fotogramma decide (se è un verde solo, gira da quella parte).
    if not getattr(RwdConf, "DIETRO_CONFERMA", False):
        return True
    Rwd.Stop()
    time.sleep(0.25)
    img = FotogrammaNuovo()
    if img is None:
        return True
    roll_ora = Rwd.GetGyro()[0]
    cls, conf, _, _ = WebCam.VerificaVerde(MascheraAlta(img) if roll_ora > 15 else img)
    geo, perche = WebCam.UltimoControlloVerde[0]
    if cls == "Fr":
        print(f"Dietrofront confermato da fermo (YOLO {conf:.2f}; colori: {geo or 'non giudicano'}, {perche})")
        return True
    print(f"Dietrofront ANNULLATO: da fermo non è un doppio verde (ora: {cls}; colori: {geo or 'non giudicano'}, {perche})")
    return False


def MemorizzaSvolta(verso):
    # [FIX 71] All'incrocio con verde il robot gira solo di 42 gradi (svolte "vecchie") e il seguilinea finisce
    # la curva. Se subito dopo c'è l'ingresso dell'arena, la striscia argento arriva a metà curva: per sapere
    # in che direzione entrare ci si ricorda la direzione PRIMA della svolta + 90 gradi.
    global SvoltaAttesa
    _, _, hd = Rwd.GetGyro()
    SvoltaAttesa = (time.time(), (hd + 90 * verso) % 360, verso)    # [FIX 101] anche il verso della svolta


def CrosDx():           #Esegue incrocio a Destra
    #Funzione incrocio Destro
    #Rwd.Sterzo(Vel,65)
    
    MemorizzaSvolta(1)   # [FIX 71] per entrare dritti se subito dopo c'è l'arena
    if RwdConf.SVOLTE == "vecchie":
        # [FIX 52] svolta del codice originale della squadra: avanti a tempo, poi Gira(42); il seguilinea
        # finisce la curva
        Rwd.Sterzo(VelCross,0)
        time.sleep(0.45)
        time.sleep(0.1)
        Rwd.Gira(42,VelCross)
    else:
        h0 = AvanzaSullIncrocio(0.55)   # [FIX 41] svolta "nuova"
        Rwd.Gira(RwdConf.SVOLTA_BASE * (1), VelCross)
        CompletaSvolta(1, h0)
    #Rwd.Sterzo(VelCross,100)
    #time.sleep(0.9)
    #Rwd.Stop()
    Rwd.Sterzo(-VelCross,0)
    time.sleep(0.15)
    #Rwd.Stop()
    AvviaPausaVerdi()      # [FIX 80]

def CrosSx():           #Esegue incrocio a Sinistra
    #Funzione Incrocio Sinistro
    #Rwd.Sterzo(Vel,-65)
    
    MemorizzaSvolta(-1)   # [FIX 71] per entrare dritti se subito dopo c'è l'arena
    if RwdConf.SVOLTE == "vecchie":
        # [FIX 52] svolta del codice originale della squadra: avanti a tempo, poi Gira(-35); il seguilinea
        # finisce la curva
        Rwd.Sterzo(VelCross,0)
        time.sleep(0.45)
        time.sleep(0.1)
        Rwd.Gira(-35,VelCross)
    else:
        h0 = AvanzaSullIncrocio(0.55)   # [FIX 41] svolta "nuova"
        Rwd.Gira(RwdConf.SVOLTA_BASE * (-1), VelCross)
        CompletaSvolta(-1, h0)
    #Rwd.Sterzo(VelCross,0)
    #time.sleep(0.9)
    #Rwd.Stop()
    Rwd.Sterzo(-VelCross,0)
    time.sleep(0.15)
    #Rwd.Stop()
    AvviaPausaVerdi()      # [FIX 80]

def CrosDxIncl():           #Esegue incrocio a Destra
    #Funzione incrocio Destro
    #Rwd.Sterzo(Vel,65)
    
    MemorizzaSvolta(1)   # [FIX 71] per entrare dritti se subito dopo c'è l'arena
    if RwdConf.SVOLTE == "vecchie":
        # [FIX 52] svolta del codice originale della squadra: avanti a tempo, poi Gira(42); il seguilinea
        # finisce la curva
        Rwd.Sterzo(VelCross,0)
        time.sleep(0.40)
        time.sleep(0.1)
        Rwd.Gira(42,VelCross)
    else:
        h0 = AvanzaSullIncrocio(0.5)   # [FIX 41] svolta "nuova"
        Rwd.Gira(RwdConf.SVOLTA_BASE * (1), VelCross)
        CompletaSvolta(1, h0)
    #Rwd.Sterzo(VelCross,100)
    #time.sleep(0.9)
    #Rwd.Stop()
    #Rwd.Sterzo(-VelCross,0)
    #time.sleep(0.15)
    #Rwd.Stop()
    AvviaPausaVerdi()      # [FIX 80]
    


def CrosSxIncl():           #Esegue incrocio a Sinistra
    #Funzione Incrocio Sinistro
    #Rwd.Sterzo(Vel,-65)
    
    MemorizzaSvolta(-1)   # [FIX 71] per entrare dritti se subito dopo c'è l'arena
    if RwdConf.SVOLTE == "vecchie":
        # [FIX 52] svolta del codice originale della squadra: avanti a tempo, poi Gira(-37); il seguilinea
        # finisce la curva
        Rwd.Sterzo(VelCross,0)
        time.sleep(0.40)
        time.sleep(0.1)
        Rwd.Gira(-37,VelCross)
    else:
        h0 = AvanzaSullIncrocio(0.5)   # [FIX 41] svolta "nuova"
        Rwd.Gira(RwdConf.SVOLTA_BASE * (-1), VelCross)
        CompletaSvolta(-1, h0)
    #Rwd.Sterzo(VelCross,0)
    #time.sleep(0.9)
    #Rwd.Stop()
    #Rwd.Sterzo(-VelCross,0)
    #time.sleep(0.15)
    #Rwd.Stop()
    AvviaPausaVerdi()      # [FIX 80]

def CrosFF():           #Esegue Dietrofront
    #Funzione Dietro Front
    #Rwd.Stop()    
    time.sleep(0.1)
    Rwd.Sterzo(VelCross,0) 
    time.sleep(0.6)
    Rwd.Gira(170,VelCross)
    # [FIX 80] dopo il dietrofront NIENTE pausa dei verdi: il robot può arrivare subito all'incrocio di prima
    #time.sleep(0.5)
    #Rwd.Sterzo(-VelCross,0)
    #time.sleep(0.2) 
    #Rwd.Stop() 

def CrosFFIncl(Verso=1):           #Esegue Dietrofront
    #Funzione Dietro Front
    #Rwd.Stop()    
    #time.sleep(0.1)
    Rwd.Sterzo(VelCross,0) 
    time.sleep(0.6)
    # [FIX 44] prima Gira(±100) + 0,5 s di rotazione "nascosta" (Gira non fermava i motori): circa 140 gradi.
    # Ora Gira si ferma da sola: dietrofront vero come in CrosFF.
    if Verso==1:
        Rwd.Gira(170,VelCross)
    else:
        Rwd.Gira(-170,VelCross)
    # [FIX 80] dopo il dietrofront NIENTE pausa dei verdi (vedi CrosFF)
    #Rwd.Sterzo(-VelCross,0)
    #time.sleep(0.2) 
    #Rwd.Stop() 


def BoosterDx():
    print('BOOOOOSter DX')
    Rwd.Sterzo(VelCross,100)
    #Rwd.Sterzo(-VelCross,0)
    #time.sleep(0.1)
    #Rwd.Gira(35,VelCross)
    #Rwd.Sterzo(Vel,100)
    #time.sleep(0.3)

def BoosterSx():
    print('BOOOOOSter SX')
    Rwd.Sterzo(VelCross,-100)
    #Rwd.Sterzo(-VelCross,0)
    #time.sleep(0.1)
    #Rwd.Gira(-35,VelCross)
    #Rwd.Sterzo(Vel,-100)
    #time.sleep(0.3)


def LineaDavanti(Verso, PixMask=120):
    # [FIX 28] La camera vede la linea? Usata DURANTE gli spostamenti attorno all'ostacolo.
    # Prima la linea veniva cercata solo a fine rotazione: se era più lontana di quanto
    # inquadra la camera, il robot ci passava sopra senza accorgersene.
    Crop = Immagine.copy()
    if Verso == 1:
        Crop[:, 0:PixMask] = 255
    else:
        Crop[:, WebCam.RisX-PixMask:] = 255
    Incr_Ril, _, _, _ = WebCam.VerificaVerde(Crop)
    return Incr_Ril == "Ln"


UltimaRotazioneOk = True    # [FIX 90] l'ultima RuotaOstacolo è arrivata (più o meno) alla direzione voluta?
UltimoStaccoParete = -99.0  # [FIX 90] quando il robot si è staccato l'ultima volta da una parete
StacchiDiFila = 0           # [FIX 90] stacchi dalla parete uno dopo l'altro (ognuno gira di più)


def RuotaOstacolo(rotta, gradi):
    # [FIX 73] Giro intorno all'ostacolo: dalla direzione VOLUTA del lato precedente (non da quella letta adesso)
    # alla nuova, ad anello chiuso col giroscopio. Restituisce la nuova direzione da tenere.
    # [FIX 90] e si ricorda se ci è arrivato: se resta a più di OST_ROTAZIONE_TOLL gradi la rotazione era bloccata
    # (scatola nera 03/11 V30, secondo 81: girando verso la parete a destra fa 25 gradi in 4 s invece di 90)
    global UltimaRotazioneOk
    nuova = (rotta + gradi) % 360
    Rwd.Stop()
    esito = Rwd.RuotaVerso(nuova, VelCross, tolleranza=3, timeout=4.0)
    Rwd.Stop()
    _, _, hd = Rwd.GetGyro()
    UltimaRotazioneOk = esito is True or abs(angle_difference(nuova, hd)) <= RwdConf.OST_ROTAZIONE_TOLL
    return nuova


def Spinge():
    # [FIX 90] il robot ha qualcosa a pochi cm davanti (laser frontale filtrato, FIX 87): se avanza, spinge
    d = Rwd.FrontaleFiltrato()
    return 0 < d <= RwdConf.OST_SPINTA_CM


def AvantiOst(durata, rotta):
    # [FIX 90] Come Rwd.Dritto(VelSl, durata) ma a passi di 0,1 s: se davanti c'è qualcosa a pochi cm si ferma,
    # arretra un poco e risponde False. Scatola nera 03/11 (V30), secondi 90-95: aggirando l'"ostacolo" il robot
    # ha spinto contro la parete per 5 s con il laser frontale a 4 cm e il muso che saliva (beccheggio 7).
    t0 = time.time()
    while time.time() - t0 < durata - 1e-3:
        if not Rwd.GetSwitch()['sw_sof']:          # switch spento: Dritto esce subito, qui girerebbe a vuoto
            Rwd.Stop()
            return False
        if Spinge():
            Rwd.Stop()
            print(f"Ostacolo: spingo contro qualcosa davanti ({Rwd.FrontaleFiltrato()} cm): mi fermo e arretro")
            Rwd.Sterzo(-VelCross, 0)
            time.sleep(RwdConf.OST_SPINTA_ARRETRA_S)
            Rwd.Stop()
            return False
        t_passo = time.time()
        Rwd.Dritto(VelSl, min(0.1, durata - (time.time() - t0)), heading_ref=rotta)
        # Dritto si raddrizza ruotando sul posto (FIX 64): se un passo da 0,1 s è durato più di 0,6 s e il robot è
        # ancora storto, la rotazione è bloccata (un fianco contro la parete). Prima ci riprovava per 40 s.
        _, _, hd = Rwd.GetGyro()
        if time.time() - t_passo > 0.6 and abs(angle_difference(rotta, hd)) > 20:
            Rwd.Stop()
            print(f"Ostacolo: non riesco a raddrizzarmi (storto di {abs(angle_difference(rotta, hd)):.0f} gradi, tocco qualcosa): arretro")
            Rwd.Sterzo(-VelCross, 0)
            time.sleep(RwdConf.OST_SPINTA_ARRETRA_S)
            Rwd.Stop()
            return False
    return True


def TornaIndietroOst(rotta0):
    # [FIX 90] da questo lato non si passa: arretro, torno nella direzione di partenza e lo dico a chi mi ha chiamato
    Rwd.Stop()
    Rwd.Sterzo(-VelCross, 0)
    time.sleep(RwdConf.OST_SPINTA_ARRETRA_S)
    Rwd.Stop()
    Rwd.RuotaVerso(rotta0, VelCross, tolleranza=3, timeout=4.0)
    Rwd.Stop()
    return "bloccato"


def StaccaDallaParete(sx, dx):
    # [FIX 90] arretra e si gira dalla parte opposta alla parete. Se si ritrova contro la parete entro
    # OST_STACCO_RIPROVA_S secondi, la volta dopo gira di più (20, 40, 60 gradi): prima, sulla linea che finisce
    # contro la parete, il robot ci tornava contro e spingeva per un minuto (simulatore V30, pista della scuola).
    global UltimoStaccoParete, StacchiDiFila
    if time.time() - UltimoStaccoParete > 2 * RwdConf.OST_STACCO_RIPROVA_S:
        StacchiDiFila = 0
    StacchiDiFila += 1
    gradi = min(60, RwdConf.OST_STACCO_GRADI * StacchiDiFila)
    UltimoStaccoParete = time.time()
    lato = "DESTRA" if dx <= sx else "SINISTRA"
    print(f"Mi stacco dalla parete a {lato}: arretro e giro di {gradi} gradi verso {'sinistra' if lato == 'DESTRA' else 'destra'}")
    Rwd.Stop()
    Rwd.Sterzo(-VelCross, 0)
    time.sleep(RwdConf.OST_SPINTA_ARRETRA_S)
    Rwd.Stop()
    Rwd.Gira(-gradi if lato == "DESTRA" else gradi, VelCross)
    Rwd.Stop()


def ScegliLatoOstacolo():
    # [FIX 90] OSTACOLO PIÙ FURBO. Prima il robot girava SEMPRE intorno all'ostacolo passando a destra, anche con
    # una parete proprio lì (la pista della scuola ha le pareti ai bordi). Scatola nera 03/11 (V30), secondi 81-129:
    # sul semicerchio vicino al bordo il robot tocca la parete a destra, la prende per un ostacolo, prova a girare
    # a destra (bloccato), spinge per 5 s, e ci mette 48 s a ripartire.
    # Ora guarda i laser laterali:
    #  - se una parete è a meno di OST_PARETE_CM di lato, il "qualcosa davanti" è quasi sempre la parete stessa:
    #    il robot arretra, si gira di OST_STACCO_GRADI dalla parte libera e torna a seguire la linea (None);
    #    se entro OST_STACCO_RIPROVA_S secondi è di nuovo lì, è un ostacolo vero e lo aggira;
    #  - lo aggira passando dal lato più libero (a destra come prima, a sinistra se a destra c'è poco spazio).
    # Restituisce il Verso per OstAutDet (-1 = passa a destra, 1 = passa a sinistra) oppure None.
    global UltimoStaccoParete
    sx, _, dx = LaserVeri()
    vicino = min(sx, dx)
    if 0 < vicino < RwdConf.OST_PARETE_CM and time.time() - UltimoStaccoParete > RwdConf.OST_STACCO_RIPROVA_S:
        lato = "DESTRA" if dx <= sx else "SINISTRA"
        print(f"Parete a {lato} a {vicino} cm e qualcosa davanti: è la parete, non un ostacolo")
        StaccaDallaParete(sx, dx)
        return None
    if dx < RwdConf.OST_LATO_LIBERO_CM and sx > dx:
        print(f"Ostacolo: a destra poco spazio ({dx} cm, a sinistra {sx} cm): lo aggiro a SINISTRA")
        return 1
    return -1


def AggiraOstacolo():
    # [FIX 90] sceglie il lato; se da quel lato non passa (non riesce a girarsi o spinge contro qualcosa) prova
    # dall'altro; se non passa da nessuno dei due torna a seguire la linea invece di spingere
    global UltimoStaccoParete
    verso = ScegliLatoOstacolo()
    if verso is None:
        return
    if OstAutDet(verso) != "bloccato":
        return
    print(f"Ostacolo: passando a {'sinistra' if verso == 1 else 'destra'} non passo, provo dall'altro lato")
    if OstAutDet(-verso) != "bloccato":
        return
    print("Ostacolo: non riesco ad aggirarlo da nessun lato, torno a seguire la linea")
    UltimoStaccoParete = time.time()


def OstAutDet(Verso=1): # Verso assume valori -1 e 1 e definisce il lato di agiramento dell'ostacolo
    global Immagine
    global VelCross
    global VelSl
    PixMask=120
    PASSI_MAX = 40      # [FIX 27] 40 passi da 0,1-0,2 s: un ciclo non può durare più di 4-8 s
                        # (prima, se il laser non vedeva mai l'ostacolo, il robot spingeva per sempre)
    DisTarg=10         # distanza desiderata dall'oggetto (cm)
    TrovLinea=False
    Rwd.Stop()
    Rwd.Sterzo(VelCross,0)
    time.sleep(0.1)
    Rwd.Stop()
    ##########################INIZIO OSTACOLO PRIMO GIRO
    # [FIX 73] LATI DELL'OSTACOLO A SQUADRA CON LE PIASTRELLE. Prima ogni giro era "Gira di 87/85/80 gradi da
    # dove sono": se il robot arrivava all'ostacolo un po' storto (uscendo da una curva) tutto il giro era
    # storto e il lato lungo finiva addosso all'ostacolo (simulatore V27: laser laterale a 3 cm, poi il robot
    # incastrato girandosi per rientrare). Ora la direzione di partenza si aggancia al lato delle piastrelle
    # più vicino (RiferimentoGriglia, entro 25 gradi) e ogni giro va a una direzione ASSOLUTA, con la
    # rotazione ad anello chiuso (FIX 72).
    _, _, rotta = Rwd.GetGyro()
    if RiferimentoGriglia is not None:
        dg = angle_difference(rotta, RiferimentoGriglia)
        griglia = (RiferimentoGriglia + 90 * round(dg / 90.0)) % 360
        if abs(angle_difference(rotta, griglia)) <= 25:
            rotta = griglia
    rotta0 = rotta                                  # [FIX 90] direzione di partenza (per tornare indietro)
    rotta = RuotaOstacolo(rotta, -90 * Verso)
    if not UltimaRotazioneOk:                       # [FIX 90] da questo lato non riesco nemmeno a girarmi
        print("Ostacolo: non riesco a girarmi da questo lato (tocco qualcosa)")
        return TornaIndietroOst(rotta0)
    sensori = Rwd.GetSensori()
    _,SwSf=sensori['switch']
    if Verso==1:
        _,_,DisTarg=LaserVeri()   # [FIX 54] 0 = lontano, non vicino
    else: 
       DisTarg,_,_=LaserVeri()   # [FIX 54]
    if DisTarg < 10:
        DisTarg=10
    if DisTarg > 25:                # [FIX 54] il laser non vedeva bene l'ostacolo: valore normale
        DisTarg=15
    Dis=DisTarg
    print("Distanza Targhet", Dis)
    Passi=0
    PassiCiclo = 0   # [FIX 27] ogni ciclo dura al massimo PASSI_MAX passi
    while Dis < DisTarg+10 and not TrovLinea and SwSf and PassiCiclo < PASSI_MAX:
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']        
        Passi+=1
        if Spinge():                                # [FIX 90] il primo lato è chiuso davanti: provo dall'altro
            print(f"Ostacolo: spingo contro qualcosa davanti ({Rwd.FrontaleFiltrato()} cm) sul primo lato")
            return TornaIndietroOst(rotta0)
        Rwd.Dritto(VelSl,0.2,heading_ref=rotta)
        PassiCiclo += 1
        # --- 1. Lettura laser lato ostacolo 
        sensori = Rwd.GetSensori()
        if Verso==1:
            _,_,Dis=LaserVeri()   # [FIX 54] 
        else: 
            Dis,_,_=LaserVeri()   # [FIX 54]

    # Passato primo lato vado poco avanti e giro 90 gradi 
    # [FIX 27] 0,9 s invece di 0,5 s: quando il laser laterale supera il bordo dell'ostacolo
    # metà robot è ancora accanto al blocco. Con 0,5 s lo spigolo anteriore lo toccava
    # (margine di 0-5 cm, provato nel simulatore). Regolate questo tempo sul robot vero.
    AvantiOst(0.9, rotta)                           # [FIX 90] si ferma se spinge
    Rwd.Stop()
    ##########################INIZIO OSTACOLO SECONDO GIRO
    rotta = RuotaOstacolo(rotta, 90 * Verso)          # [FIX 73]
    print("INIZIO LATO LUNGO")
    if Verso==1:
        Crop = Immagine.copy()
        Crop[:, 0:PixMask] = 255
    else: 
        Crop = Immagine.copy()
        Crop[:, WebCam.RisX-PixMask:] = 255 
    Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
    #TrovLinea=Incr_Ril=="Ln"        
    cv2.imshow('Linea', Crop)
    key = cv2.waitKey(1) & 0xFF
    time.sleep(0.2)
    # Vado avanti fino ad incontrare con il laser l'ostacolo
    if not TrovLinea and SwSf:
        PassiCiclo = 0   # [FIX 27] ogni ciclo dura al massimo PASSI_MAX passi
        Dis = 999   # [FIX 54] prima Dis=25 (o il valore del ciclo prima): se DisTarg era 15 la condizione
                    # 25 > 25 era falsa, il ciclo non partiva e il robot girava contro l'ostacolo
        while Dis > DisTarg+10 and not TrovLinea and SwSf and PassiCiclo < PASSI_MAX:
            sensori = Rwd.GetSensori()
            _,SwSf=sensori['switch'] 
            if not AvantiOst(0.1, rotta): break   # [FIX 90] spinge: fine di questo lato
            PassiCiclo += 1
            # --- 1. Lettura laser lato ostacolo 
            sensori = Rwd.GetSensori()
            if Verso==1:
                _,_,Dis=LaserVeri()   # [FIX 54] 
            else: 
                Dis,_,_=LaserVeri()   # [FIX 54]
            
        # Vai fino a superare l'ostacolo con il laser    
        AvantiOst(0.3, rotta)   # [FIX 90]
        Rwd.Stop()
        print("Inizio Ostacolo Dritto")
        time.sleep(0.2)
        PassiCiclo = 0   # [FIX 27] ogni ciclo dura al massimo PASSI_MAX passi
        while Dis < DisTarg+10 and not TrovLinea and SwSf and PassiCiclo < PASSI_MAX:
            sensori = Rwd.GetSensori()
            _,SwSf=sensori['switch'] 
            if not AvantiOst(0.1, rotta): break   # [FIX 90] spinge: fine di questo lato
            PassiCiclo += 1
            # --- 1. Lettura laser lato ostacolo 
            sensori = Rwd.GetSensori()
            if Verso==1:
                _,_,Dis=LaserVeri()   # [FIX 54]
            else: 
                Dis,_,_=LaserVeri()   # [FIX 54]
            # [FIX 54] con LaserVeri qui arriva 0 solo se Arduino non risponde
            if Dis ==0:
                Dis=13

            print("Distanza", Dis) 
            
        # Passato primo lato vado poco avanti e giro 90 gradi 
        AvantiOst(0.6, rotta)   # [FIX 90]
        Rwd.Stop()
        print("Passo Vuoto Giro e Inizio Ostacolo Rientro")
        time.sleep(0.2)
        ##########################INIZIO OSTACOLO TERZO GIRO
        rotta = RuotaOstacolo(rotta, 80 * Verso)      # [FIX 73]
        if Verso==1:
            Crop = Immagine.copy()
            Crop[:, 0:PixMask] = 255
        else: 
            Crop = Immagine.copy()
            Crop[:, WebCam.RisX-PixMask:] = 255 
        Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
        TrovLinea=Incr_Ril=="Ln"        
        cv2.imshow('Linea', Crop)
        key = cv2.waitKey(1) & 0xFF
        time.sleep(0.2)
        if not TrovLinea:
            PassiCiclo = 0   # [FIX 27] ogni ciclo dura al massimo PASSI_MAX passi
            Dis = 999   # [FIX 54] prima Dis=25 (o il valore del ciclo prima): se DisTarg era 15 la condizione
                        # 25 > 25 era falsa, il ciclo non partiva e il robot girava contro l'ostacolo
            while Dis > DisTarg+10 and not TrovLinea and SwSf and PassiCiclo < PASSI_MAX:
                sensori = Rwd.GetSensori()
                _,SwSf=sensori['switch'] 
                if not AvantiOst(0.1, rotta): break   # [FIX 90] spinge: fine di questo lato
                PassiCiclo += 1
                TrovLinea = LineaDavanti(Verso)   # [FIX 28] controllo continuo della linea
                # --- 1. Lettura laser lato ostacolo 
                sensori = Rwd.GetSensori()
                if Verso==1:
                    _,_,Dis=LaserVeri()   # [FIX 54] 
                else: 
                    Dis,_,_=LaserVeri()   # [FIX 54]
                
                # [FIX 54] con LaserVeri qui arriva 0 solo se Arduino non risponde
                
                if Dis ==0:
                    Dis=13
                print("Distanza", Dis)
            # Vai fino a superare l'ostacolo con il laser    
            AvantiOst(0.3, rotta)   # [FIX 90]
            Rwd.Stop()
            print("Inizio Ostacolo Dritto")
            time.sleep(0.2)
            PassiCiclo = 0   # [FIX 27] ogni ciclo dura al massimo PASSI_MAX passi
            while Dis < DisTarg+10 and not TrovLinea and SwSf and PassiCiclo < PASSI_MAX:
                sensori = Rwd.GetSensori()
                _,SwSf=sensori['switch'] 
                if not AvantiOst(0.1, rotta): break   # [FIX 90] spinge: fine di questo lato
                PassiCiclo += 1
                TrovLinea = LineaDavanti(Verso)   # [FIX 28] controllo continuo della linea
                # --- 1. Lettura laser lato ostacolo 
                sensori = Rwd.GetSensori()
                if Verso==1:
                    _,_,Dis=LaserVeri()   # [FIX 54]
                else: 
                    Dis,_,_=LaserVeri()   # [FIX 54]
                # [FIX 54] con LaserVeri qui arriva 0 solo se Arduino non risponde
                if Dis ==0:
                    Dis=13
                print("Distanza", Dis) 
            # Passato primo lato vado poco avanti e giro 90 gradi 
            AvantiOst(0.6, rotta)   # [FIX 90]
            Rwd.Stop()
            print("Passo Vuoto Giro e Inizio Ostacolo Rientro")
            time.sleep(0.2)
            ##########################INIZIO OSTACOLO TERZO GIRO
            if not TrovLinea:
                rotta = RuotaOstacolo(rotta, 80 * Verso)      # [FIX 73]
            Rwd.Stop()
            if Verso==1:
                Crop = Immagine.copy()
                Crop[:, 0:PixMask] = 255
            else: 
                Crop = Immagine.copy()
                Crop[:, WebCam.RisX-PixMask:] = 255 
            Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
            TrovLinea=Incr_Ril=="Ln"        
            cv2.imshow('Linea', Crop)
            key = cv2.waitKey(1) & 0xFF
            time.sleep(0.2)
    print("Trovata Linea e mi posiziono")
    
    AvantiOst(0.5, rotta)                           # [FIX 90]
    if Verso==1:
        Rwd.Gira(-40,VelCross)
    else:
        Rwd.Gira(40,VelCross)
    #time.sleep(0.5)
    print("FINE OSTACOLO")

# ===========================================================================================
#   [FIX 46] INGRESSO E USCITA DELL'ARENA
# ===========================================================================================
ArgentoIgnoraFino = 0.0     # [FIX 81] fino a quando l'argento non si ricontrolla (dopo un falso argento)


def InPianoPerArena():
    # [FIX 81] L'ingresso dell'arena è in piano. Scatola nera 29/10, secondo 93,6: il robot iniziava una rampa
    # (beccheggio 15), YOLO ha visto "argento" dove c'era una curva, il controllo "non sono in piano" guardava
    # solo il beccheggio di QUEL momento con soglia 15 (15 non è > 15) ed è passato: il robot è "entrato" e ha
    # avviato l'arena sulla rampa. Ora il robot deve essere IN PIANO (Pendenza(), mediana di mezzo secondo,
    # beccheggio e rollio sotto ARENA_PIANO_GRADI) da almeno ARENA_PIANO_S secondi.
    try:
        p = Rwd.Pendenza()
    except Exception:
        return True, "pendenza non disponibile"
    if p["tipo"] == "sconosciuto":
        return True, p["testo"]
    g = getattr(RwdConf, "ARENA_PIANO_GRADI", 8)
    if p["tipo"] != "piano":
        return False, f"sono su un tratto inclinato: {p['testo']}"
    if abs(p["becc"]) >= g or abs(p["roll"]) >= g:
        return False, f"sta iniziando un tratto inclinato (beccheggio {p['becc']:+.0f}, rollio {p['roll']:+.0f} gradi)"
    if p["piano_da_s"] < getattr(RwdConf, "ARENA_PIANO_S", 1.0):
        return False, f"sono in piano solo da {p['piano_da_s']:.1f} s (inizio o fine di una rampa)"
    return True, p["testo"]


def ScartaArgento(motivo):
    # [FIX 81] falso argento: per ARENA_IGNORA_S secondi il seguilinea non si ferma più a ricontrollarlo
    # (sulla rampa YOLO può continuare a vedere "argento" e il robot si fermerebbe ogni mezzo secondo)
    global ArgentoIgnoraFino, UltimoArgento
    ArgentoIgnoraFino = time.time() + getattr(RwdConf, "ARENA_IGNORA_S", 0.0)
    UltimoArgento = 0.0
    print(f"Ingresso ANNULLATO: {motivo}. Continuo a seguire la linea")


def ArenaDavanti():
    # [FIX 111] FALSO ARGENTO IN MEZZO ALLA PISTA. Scatola nera 12/11 ore 10:09 (V43), secondi 93-103: il robot perde la
    # linea dopo una svolta, YOLO scambia un bordo scuro per la striscia argento, i controlli dell'ingresso passano
    # (centratura: "striscia non vista") e il robot "entra" a velocità 68: scende da una discesa di 28 gradi, LoP 2.
    # In quel momento il laser davanti misurava 155-166 cm. Nelle 18 scatole nere, in TUTTI i 15 ingressi veri, al
    # momento di entrare il laser davanti misurava al massimo 105 cm: dietro la porta c'è l'arena (90 cm di fondo).
    # Quindi: se davanti è libero oltre ARGENTO_FRONTE_MAX_CM (150: l'arena del regolamento è profonda al massimo
    # 120 cm, se si entra dal lato corto), lì non c'è l'arena e l'ingresso si annulla.
    # In più, se ARGENTO_DOPO_S > 0, niente ingresso nei primi ARGENTO_DOPO_S secondi dalla partenza della run (il
    # cronometro della V43, che non si azzera con le LoP). Spento di base: nelle prove che partono vicino all'arena
    # l'ingresso vero è arrivato anche a 6, 13 e 17 s.
    # Si decide solo con letture VERE del laser (non 0 = "fuori portata"): se il laser non vede niente non si sa cosa c'è
    # davanti e si lascia entrare come prima (nel simulatore il laser arriva solo a 120 cm).
    lim = getattr(RwdConf, "ARGENTO_FRONTE_MAX_CM", 150)
    try:
        Rwd.FrontaleFiltrato()                        # aggiorna la storia del laser davanti
        adesso = time.time()
        finestra = getattr(RwdConf, "ARGENTO_FRONTE_FINESTRA_S", 0.5)
        valide = sorted(d for (t, d) in list(getattr(Rwd, "_storia_fr", [])) if adesso - t <= finestra and d > 0)
    except Exception:
        valide = []
    if lim and len(valide) >= 3:
        fr = valide[len(valide) // 2]
        if fr > lim:
            return False, (f"il laser davanti vede libero fino a {fr:.0f} cm, ma dietro una porta vera c'è l'arena "
                           f"(al massimo {lim} cm)")
    t_min = getattr(RwdConf, "ARGENTO_DOPO_S", 0)
    t0 = getattr(Monitor, "_t_run", None)
    if t_min and t0 is not None and time.time() - t0 < t_min:
        return False, f"sono passati solo {time.time() - t0:.0f} s dalla partenza (l'argento vero non arriva prima di {t_min} s)"
    return True, ""


def TrovaIngressoArena(roll=0, entra=True):
    # Chiamata dal seguilinea quando YOLO vede la striscia ARGENTO ("In").
    # Prima di entrare fa 3 controlli, poi entra dritto col giroscopio. Restituisce True se è entrato.
    #   1) da FERMO, con un fotogramma nuovo, YOLO deve vedere di nuovo l'argento (come FIX 33)
    #   2) oltre la striscia la linea nera NON deve continuare (all'ingresso la linea finisce)
    #   3) il robot deve essere in piano (sulle rampe la camera vede male)
    global RottaArena
    Rwd.Stop()
    time.sleep(0.3)                                   # fotogramma nuovo a robot fermo
    Crop = MascheraAlta(Immagine) if roll > 15 else Immagine
    cv2.imshow('Linea', Crop)
    Incr_Ril, confid, _, _ = WebCam.VerificaVerde(Crop)
    if Incr_Ril != "In":
        print("Ingresso non confermato (striscia argento non rivista da fermo): continuo a seguire la linea")
        return False
    if abs(roll) > 15:
        print("Ingresso non confermato: non sono in piano")
        return False
    in_piano, perche = InPianoPerArena()               # [FIX 81]
    if not in_piano:
        ScartaArgento(perche)
        return False
    oltre = WebCam.LineaOltreStriscia(Crop)
    if oltre:
        print("Falso ARGENTO: oltre la striscia la linea nera continua, non è l'ingresso")
        Rwd.Sterzo(VelSl, 0)                          # supero il punto per non rivederlo subito
        time.sleep(0.3)
        return False
    print('IA     Arena                In In In In In: ', confid,
          "(oltre la striscia niente linea)" if oltre is False else "")
    if not entra:
        return True                                   # [FIX 66] solo il controllo, senza entrare
    # [FIX 71] ENTRARE PERPENDICOLARI ALLA STRISCIA. Scatola nera 26/10: subito prima dell'ingresso c'è un
    # incrocio con verde; il robot ha visto l'argento mentre stava ancora girando (direzione 41 invece di 83)
    # ed è entrato di sbieco di 40 gradi. E la direzione d'ingresso diventa RottaArena, cioè la direzione dei
    # muri per tutto il giro dei muri: anche quello partiva storto.
    rotta_ingresso = DirezioneIngresso(Crop)
    _, _, hd_ora = Rwd.GetGyro()
    if abs(angle_difference(rotta_ingresso, hd_ora)) > 3:
        Rwd.Sterzo(-RwdConf.VelCrs, 0)               # un passo indietro per avere spazio per girarsi
        time.sleep(0.3)
        Rwd.Stop()
        Rwd.RuotaVerso(rotta_ingresso, tolleranza=2, timeout=4.0)
        Rwd.Stop()
    if CentraSullIngresso(rotta_ingresso) == "linea":   # [FIX 71] anche di lato, non solo di direzione
        # [FIX 81] scatola nera 29/10: avanzando piano YOLO vedeva solo la linea ("Ln" 1.00) e niente argento,
        # ma il robot entrava lo stesso. Se la striscia non si rivede e la linea continua, non è l'ingresso.
        ScartaArgento("avanzando non rivedo la striscia argento, vedo solo la linea")
        return False
    arena, perche = ArenaDavanti()                    # [FIX 111] davanti deve esserci l'arena, non la pista
    if not arena:
        ScartaArgento(perche)
        return False
    RottaArena = rotta_ingresso                       # [FIX 34] riferimento per uscire dritti
    print(" Verificata entrata: entro dritto")
    EntraDallaPorta(rotta_ingresso)                 # [FIX 93]
    print("Trovata Fine Linea")
    time.sleep(1)
    Rwd.GetOffLed1()
    return True


def EntraDallaPorta(rotta_ingresso):
    # [FIX 93] PASSARE LA PORTA SENZA TOCCARE GLI STIPITI. Scatola nera 05/11 (V33), secondi 17,8-22: entrando il
    # robot si storce di 8 gradi a sinistra (1 -> 353); Dritto lo raddrizzava RUOTANDO SUL POSTO mentre era ancora
    # dentro la porta: il robot gira attorno al centro delle ruote, il retro sinistro (dove c'è il LED) va verso
    # lo stipite (laser sinistro 22 -> 16 cm) e lo tocca: per 1,5 s la rotazione resta bloccata a 351-353 gradi.
    # Ora nella porta si avanza SENZA ruotare sul posto e si raddrizza solo quando tutto il robot è dentro l'arena.
    # [FIX 96] LA LARGHEZZA DEL ROBOT. Scatola nera 05/11 ore 15:12 (V34), secondi 171,7-174: il laser davanti
    # vedeva libero (102 cm, il fondo dell'arena) ma a 172,6 s il robot ha smesso di avanzare (frontale fermo a
    # 93-97 cm per 1,3 s con i motori a 68) e si è girato di 18 gradi a sinistra (146 -> 128) mentre lo sterzo
    # correggeva a destra: il fianco SINISTRO era agganciato allo stipite. Il robot è largo ROBOT_LARGHEZZA_CM
    # e la porta circa 28 cm: restano pochi cm per lato, e un po' di spostamento o di storto bastano a toccare.
    # Ora, mentre attraversa, il robot controlla due cose:
    #  - si gira da solo di più di ENTRATA_STORTO_GRADI (un fianco è trattenuto: girarsi a sinistra vuol dire
    #    fianco sinistro agganciato);
    #  - il laser davanti non si accorcia più (non avanza: è fermo contro lo stipite).
    # Se succede: arretra fuori dalla porta, si rimette dritto, si sposta di ENTRATA_SPOSTA_CM dalla parte
    # opposta al fianco agganciato e riprova (al massimo ENTRATA_TENTATIVI volte).
    arretrato = CercaAperturaDavanti(rotta_ingresso)  # [FIX 101] cm arretrati per avere spazio: si recuperano entrando
    durata = RwdConf.TempoEntrataArena + arretrato / RwdConf.VelocitaArenaCmS
    PassaLaPorta(rotta_ingresso, durata, IngressoLato if IngressoLato else 1, "Ingresso",
                 getattr(RwdConf, "ENTRATA_TENTATIVI", 5), ultimo_spinge=True)        # [FIX 103] stesso giro di prima
    _, _, hd = Rwd.GetGyro()
    if abs(angle_difference(rotta_ingresso, hd)) > 3:
        print(f"Entrato storto di {angle_difference(hd, rotta_ingresso):+.0f} gradi: mi raddrizzo ora che sono dentro")
        Rwd.RuotaVerso(rotta_ingresso, tolleranza=2, timeout=3.0)
        Rwd.Stop()


def PassaLaPorta(rotta, durata, lato0, nome, tentativi, ultimo_spinge=True, extra_ritento=0.0):
    # [FIX 103] I TENTATIVI PER PASSARE UNA PORTA, uguali per l'INGRESSO (FIX 96, 101) e per l'USCITA.
    # Attraversa con AttraversaPorta; se un fianco resta agganciato allo stipite arretra dritto (senza ruotare),
    # si raddrizza e si sposta di lato, poi riprova:
    #  - "mi sono girato da solo": il fianco agganciato è sicuro (girato a sinistra = fianco sinistro): ci si sposta
    #    di ENTRATA_SPOSTA_CM dall'altra parte;
    #  - "non avanzo": non si sa da che parte è lo stipite: si prova a +4, +8 cm dalla parte prevista (lato0: +1 destra,
    #    -1 sinistra), poi a -4, -8 dall'altra.
    # ultimo_spinge=True: l'ultimo tentativo è senza controlli (l'ingresso, come prima). Con False, se nemmeno l'ultimo
    # riesce si torna indietro e si restituisce False (l'uscita: chi chiama riprende il giro dei muri, FIX 84).
    # extra_ritento: secondi in più per ogni nuovo tentativo (arretrando si perde strada; l'ingresso non lo usa).
    # Restituisce True se è passato.
    cm = getattr(RwdConf, "ENTRATA_SPOSTA_CM", 4.0)
    posti = [lato0 * cm, lato0 * 2 * cm, -lato0 * cm, -lato0 * 2 * cm]
    k_posto = 0
    posizione = 0.0                                   # cm a destra rispetto al primo tentativo
    for tentativo in range(1, tentativi + 1):
        ultimo = tentativo == tentativi
        esito, fatto, lato = AttraversaPorta(rotta, durata + (extra_ritento if tentativo > 1 else 0.0),
                                             controlla=not (ultimo and ultimo_spinge),
                                             camera=(nome == "Uscita"))
        Rwd.Stop()
        if esito == "ok":
            return True
        if ultimo:
            print(f"{nome}: {esito} anche al tentativo {tentativo} di {tentativi}: torno indietro")
            Rwd.Sterzo(-RwdConf.VelCrs, 0)
            time.sleep(min(1.5, fatto * 1.3 + 0.3))
            Rwd.Stop()
            return False
        if esito == "mi sono girato da solo":
            meta = posizione + cm * lato              # prova fisica: il fianco agganciato è quello
        else:
            # [FIX 104] scatola nera 06/11 10:48, 65 s: "mi sposto di 0 cm" (il posto era già quello del tentativo
            # prima): si salta ai posti non ancora provati
            while k_posto < len(posti) and abs(posti[k_posto] - posizione) < 1.0:
                k_posto += 1
            if k_posto < len(posti):
                meta = posti[k_posto]
                k_posto += 1
            else:
                meta = posizione + cm * lato
        sposta = meta - posizione
        posizione = meta
        print(f"{nome}: {esito} dopo {fatto:.1f} s (tocco lo stipite): arretro, mi raddrizzo e mi sposto di "
              f"{abs(sposta):.0f} cm a {'destra' if sposta > 0 else 'sinistra'} (tentativo {tentativo} di {tentativi})")
        Rwd.Sterzo(-RwdConf.VelCrs, 0)               # fuori dalla porta, dritto indietro (senza ruotare)
        time.sleep(min(1.5, fatto * 1.3 + 0.3))
        Rwd.Stop()
        Rwd.RuotaVerso(rotta, tolleranza=2, timeout=3.0)
        Rwd.Stop()
        SpostaDiLato(rotta, sposta)
    return True


def AttraversaPorta(rotta, durata, controlla=True, camera=False):
    # [FIX 96] Avanza per "durata" secondi verso "rotta" senza ruotare sul posto. Lo sterzo corregge almeno con
    # ENTRATA_STERZO_MIN (sotto circa 40 i servo a rotazione continua non girano: FIX 64).
    # Restituisce (esito, secondi fatti, lato): esito "ok", "mi sono girato da solo" o "non avanzo";
    # lato = +1 se il fianco agganciato è il SINISTRO (bisogna spostarsi a destra), -1 se è il destro.
    # [FIX 103] camera=True (uscita): anche la striscia NERA ferma nell'immagine vuol dire "non avanzo" (FIX 84)
    t0 = time.time()
    fronte = []                                         # (istante, laser davanti)
    storia_striscia = []
    segno_prec, t_segno = 0, t0                         # [FIX 104] quando lo sterzo ha cambiato verso l'ultima volta
    s_min = getattr(RwdConf, "ENTRATA_STERZO_MIN", 45)
    storto = getattr(RwdConf, "ENTRATA_STORTO_GRADI", 8)
    while True:
        adesso = time.time()
        fatto = adesso - t0
        if fatto >= durata or not Rwd.GetSwitch()['sw_sof']:
            return "ok", fatto, 0
        _, _, hd = Rwd.GetGyro()
        err = angle_difference(rotta, hd)
        corr = max(-100.0, min(100.0, 3.0 * err))
        if abs(err) >= 3:
            corr = math.copysign(max(abs(corr), s_min), err)
        segno = (corr > 0) - (corr < 0)
        if segno and segno != segno_prec:
            segno_prec, t_segno = segno, adesso
        Rwd.Sterzo(VelArena, corr)
        sx, fr, dx = LaserVeri()
        fronte.append((adesso, fr))
        if controlla and fatto > 0.5:
            # [FIX 104] scatola nera 06/11 10:48, 54-55 s: lo sterzo minimo (45) ha portato il robot da 355 a 0 gradi,
            # poi per il ritardo dei servo ha continuato fino a 7 anche sterzando al contrario: "mi sono girato da
            # solo" senza nessuno stipite, e il robot si è spostato dalla parte sbagliata. Ora conta solo se lo sterzo
            # spinge già da ENTRATA_RITARDO_STERZO_S nel verso giusto e il robot si allontana lo stesso.
            if abs(err) > storto and adesso - t_segno >= getattr(RwdConf, "ENTRATA_RITARDO_STERZO_S", 0.5):
                return "mi sono girato da solo", fatto, (1 if err > 0 else -1)
            # [FIX 106] FALSI "NON AVANZO" CON LA PORTA APERTA. Scatola nera 09/11 (V40), secondi 136, 143, 149, 158: robot
            # dritto e centrato, laser davanti 101-103 cm (il fondo dell'arena attraverso la porta); dopo 0,6 s "non
            # avanzo (tocco lo stipite)" e retromarcia, 4 volte di fila: 48 s persi. Ma il robot stava entrando: il laser
            # sinistro passava lo stipite (48 -> 64 -> 85 -> 101 cm) e la rotta restava dritta. A circa 1 m il laser
            # davanti balla di +-2 cm da fermo (deviazione standard 2,1 cm, letture da 96 a 106) e in 0,6 s, partendo
            # da fermo, il robot fa solo 3-5 cm: il confronto con 1,5 cm scattava a caso. Nel simulatore non si vedeva
            # (rumore 0,7 cm). Ora, se davanti è lontano (almeno ENTRATA_LONTANO_CM), il controllo comincia dopo
            # ENTRATA_LONTANO_ATTESA_S, confronta con le letture di 1,2-1,5 s prima e vuole almeno ENTRATA_LONTANO_AVANZO_CM:
            # se il robot avanza davvero, in 1,2 s il laser si accorcia di circa 10 cm. Da vicino resta tutto come prima
            # (lì il laser è preciso), e "mi sono girato da solo" (il caso vero del 5/11 alle 15:12) non cambia.
            vicino = [f for (t, f) in fronte if adesso - t <= 0.3]
            lontano = bool(vicino) and sorted(vicino)[len(vicino) // 2] >= getattr(RwdConf, "ENTRATA_LONTANO_CM", 60)
            if lontano:
                if fatto < getattr(RwdConf, "ENTRATA_LONTANO_ATTESA_S", 1.5):
                    prima = []                          # troppo presto: a questa distanza non si capisce ancora
                else:
                    prima = [f for (t, f) in fronte if 1.2 <= adesso - t <= 1.5]
                soglia = getattr(RwdConf, "ENTRATA_LONTANO_AVANZO_CM", 5.0)
            else:
                prima = [f for (t, f) in fronte if 0.6 <= adesso - t <= 0.9]
                soglia = getattr(RwdConf, "ENTRATA_AVANZO_MIN_CM", 1.5)
            ora = vicino
            # [FIX 101] anche con il laser davanti cortissimo (prima solo sopra 3 cm): nel simulatore, contro lo spigolo
            # dello stipite il laser segnava 1 cm e il robot spingeva fino alla fine del tempo senza accorgersene
            if len(prima) >= 2 and len(ora) >= 2:
                f_prima, f_ora = sorted(prima)[len(prima) // 2], sorted(ora)[len(ora) // 2]
                if f_ora < 150 and f_prima - f_ora < soglia:
                    if IngressoLato:
                        lato = IngressoLato             # [FIX 101] dalla parte opposta all'ultima svolta
                    elif abs(err) >= 2:
                        lato = 1 if err > 0 else -1
                    else:
                        lato = 1 if sx < dx else -1     # il fianco più vicino a qualcosa è quello agganciato
                    return "non avanzo", fatto, lato
            if camera:
                FotogrammaNuovo()
                if StrisciaFerma(storia_striscia):
                    return "non avanzo", fatto, (1 if sx < dx else -1)
        time.sleep(0.03)


def SpostaDiLato(rotta, cm, indietro=False):
    # [FIX 96] Spostamento laterale di "cm" (positivi = a destra) restando rivolto verso "rotta": ruota di 40 gradi,
    # avanza, si raddrizza (come la centratura sull'ingresso, FIX 71). Avanza anche di circa 1,2 x cm.
    # [FIX 101] indietro=True: alla fine arretra di quei 1,2 x cm, così resta alla stessa distanza dal muro.
    if abs(cm) < 0.5:
        return
    lato = 1 if cm > 0 else -1
    via = (rotta + 40 * lato) % 360
    Rwd.RuotaVerso(via, tolleranza=2, timeout=3.0)
    Rwd.Dritto(RwdConf.VelCrs, abs(cm) / math.sin(math.radians(40)) / RwdConf.VelocitaArenaCmS, heading_ref=via)
    Rwd.Stop()
    Rwd.RuotaVerso(rotta, tolleranza=2, timeout=3.0)
    Rwd.Stop()
    if indietro:
        Rwd.Sterzo(-RwdConf.VelCrs, 0)
        time.sleep(abs(cm) / math.tan(math.radians(40)) / RwdConf.VelocitaArenaCmS)
        Rwd.Stop()


def FrontaleDaFermo():
    # [FIX 101] laser davanti a robot fermo: mediana di 5 letture in un quarto di secondo
    letture = []
    for _ in range(5):
        letture.append(LaserVeri()[1])
        time.sleep(0.05)
    return sorted(letture)[2]


def CercaAperturaDavanti(rotta):
    # [FIX 101] PRIMA DI ENTRARE: DAVANTI C'E' LA PORTA O IL MURO? Scatola nera 05/11 ore 16:12: girato verso la porta,
    # il laser davanti misurava 18-20 cm (il muro accanto alla porta: attraverso la porta si vedrebbe il fondo
    # dell'arena, 90 cm e più) e il robot è andato a sbattere 2 volte. Se davanti c'è il muro, il robot si sposta di lato
    # a passi di ENTRATA_CERCA_PASSO_CM, restando alla stessa distanza dal muro, finché il laser vede lontano; poi si
    # sposta ancora di ENTRATA_OLTRE_CM per mettersi verso il centro della porta (il laser "vede lontano" appena il suo
    # fascio supera lo stipite, quando il robot è ancora vicino al bordo). Si cerca prima dalla parte opposta all'ultima
    # svolta (FIX 101), poi dall'altra. Restituisce i cm di cui ha arretrato (da recuperare entrando).
    # [FIX 104] la ricerca vera e propria è in CercaApertura, usata anche per l'uscita.
    global IngressoLato
    arretrato, trovata, verso = CercaApertura(rotta, IngressoLato if IngressoLato else -1,
                                              getattr(RwdConf, "INGRESSO_LIBERO_CM", 40), "Ingresso",
                                              " (dalla parte opposta all'ultima svolta)" if IngressoLato else "")
    if trovata and verso:
        IngressoLato = verso
    return arretrato


def CercaApertura(rotta, lato, libero, nome, perche="", un_lato=False):
    # [FIX 101] [FIX 104] Davanti c'è l'apertura (laser davanti >= libero)? Se no, la cerca spostandosi di lato a passi,
    # prima verso "lato" (+1 destra, -1 sinistra), poi (se un_lato=False) dall'altra parte.
    # Restituisce (cm arretrati, trovata, verso in cui l'ha trovata: 0 se c'era già).
    f = FrontaleDaFermo()
    if f >= libero:
        return 0.0, True, 0
    passo = getattr(RwdConf, "ENTRATA_CERCA_PASSO_CM", 4.0)
    n = getattr(RwdConf, "ENTRATA_CERCA_PASSI", 5)
    print(f"{nome}: davanti c'è muro a {f} cm, non la porta: la cerco spostandomi a {'destra' if lato > 0 else 'sinistra'}"
          + perche)
    arretrato = 0.0
    spazio = getattr(RwdConf, "CERCA_SPAZIO_CM", 22)  # [FIX 104] prima 16: troppo poco, nel simulatore lo spigolo
    if f < spazio:                                     # toccava il muro e il robot restava girato di 35 gradi
        arretrato = spazio - f
        Rwd.Sterzo(-RwdConf.VelCrs, 0)
        time.sleep(arretrato / RwdConf.VelocitaArenaCmS)
        Rwd.Stop()
    posizione = 0.0                                    # cm a destra rispetto a dove ha cominciato
    giri = ((lato, n),) if un_lato else ((lato, n), (-lato, 2 * n))   # dall'altra parte: prima torna indietro, poi cerca
    for verso, passi in giri:
        if verso != lato:
            print(f"{nome}: a {'destra' if lato > 0 else 'sinistra'} niente apertura dopo {n * passo:.0f} cm: "
                  f"torno indietro e provo dall'altra parte")
        for k in range(1, passi + 1):
            if not Rwd.GetSwitch()['sw_sof']:
                return arretrato, False, 0
            SpostaDiLato(rotta, passo * verso, indietro=True)   # a piccoli passi: un passo lungo andrebbe contro il muro
            posizione += passo * verso
            # [FIX 104] il laser vale solo se il robot guarda davvero dritto: girato di 35 gradi (rotazione bloccata
            # contro il muro) vedeva 58 cm in diagonale e credeva di aver trovato l'apertura
            _, _, hd = Rwd.GetGyro()
            if abs(angle_difference(rotta, hd)) > 4:
                Rwd.Sterzo(-RwdConf.VelCrs, 0)
                time.sleep(0.3)
                Rwd.Stop()
                arretrato += 0.3 * RwdConf.VelocitaArenaCmS
                Rwd.RuotaVerso(rotta, tolleranza=2, timeout=3.0)
                Rwd.Stop()
                _, _, hd = Rwd.GetGyro()
                if abs(angle_difference(rotta, hd)) > 4:
                    continue
            f = FrontaleDaFermo()
            if f >= libero:
                oltre = getattr(RwdConf, "ENTRATA_OLTRE_CM", 6.0)
                print(f"{nome}: apertura trovata a {abs(posizione):.0f} cm a {'destra' if posizione > 0 else 'sinistra'} "
                      f"(laser davanti {f} cm): mi sposto ancora di {oltre:.0f} cm verso il centro della porta")
                SpostaDiLato(rotta, oltre * verso, indietro=True)
                return arretrato, True, verso
    if un_lato and posizione:
        for _ in range(int(round(abs(posizione) / passo))):      # torno dove ero, a piccoli passi
            SpostaDiLato(rotta, -passo * lato, indietro=True)
    print(f"{nome}: apertura non trovata col laser" + (", entro come prima" if nome == "Ingresso" else ""))
    return arretrato, False, 0


def TerrenoDaPixel(u, v, W, H):
    # [FIX 71] Punto del pavimento (cm avanti dal centro del robot, cm a destra) visto dal pixel (u, v) della
    # camera linea, con le misure della camera (altezza, inclinazione, campo visivo) in ViennaDataConf.
    tau = math.radians(RwdConf.CAM_LINEA_INCLINAZIONE)
    f = (W / 2) / math.tan(math.radians(RwdConf.CAM_LINEA_HFOV / 2))
    xc, yc = (u - W / 2) / f, (v - H / 2) / f
    giu = math.cos(tau) + yc * math.sin(tau)
    t = RwdConf.CAM_LINEA_ALTEZZA / max(0.05, giu)
    return RwdConf.CAM_LINEA_AVANTI + t * (math.sin(tau) - yc * math.cos(tau)), t * xc


UltimoArgento = 0.0         # [FIX 75] istante in cui YOLO ha visto l'ultima volta la striscia argento
UltimoDietrofront = 0.0     # [FIX 98] istante dell'ultimo dietrofront per un argento dopo l'arena


def IngressoDopoArgento():
    # [FIX 75] Riprova dell'ingresso: mi giro nella direzione giusta (FIX 71), avanzo piano finché rivedo la
    # striscia (CentraSullIngresso) ed entro. Restituisce True se è entrato.
    global RottaArena, UltimoArgento
    UltimoArgento = 0.0
    Rwd.Stop()
    rotta = DirezioneIngresso(None)
    print(f"Linea finita subito dopo l'argento: riprovo l'ingresso verso {rotta:.0f}")
    Rwd.Sterzo(-RwdConf.VelCrs, 0)
    time.sleep(0.3)
    Rwd.Stop()
    Rwd.RuotaVerso(rotta, tolleranza=2, timeout=4.0)
    Rwd.Stop()
    if not InPianoPerArena()[0]:                      # [FIX 81]
        print("Striscia argento non ritrovata: cerco la linea (non sono in piano)")
        return False
    if CentraSullIngresso(rotta) is not True:
        print("Striscia argento non ritrovata: cerco la linea")
        return False
    arena, perche = ArenaDavanti()                    # [FIX 111]
    if not arena:
        ScartaArgento(perche)
        return False
    RottaArena = rotta
    print(" Verificata entrata: entro dritto")
    EntraDallaPorta(rotta)                          # [FIX 93]
    print("Trovata Fine Linea")
    time.sleep(1)
    Rwd.GetOffLed1()
    return True


def CentraSullIngresso(rotta):
    # [FIX 71] Già girato verso l'arena, il robot può essere spostato di lato rispetto alla porta (ha visto
    # l'argento a metà curva): nel simulatore era 11 cm fuori centro e lo stipite lo fermava. La striscia è
    # lunga INGRESSO_STRISCIA_CM e la camera ne vede circa 14 cm: se un'estremità della striscia è dentro
    # l'immagine, il centro della porta è a mezza striscia da quell'estremità. Se serve, il robot si sposta di
    # lato (arretra, ruota di 40 gradi, avanza, si raddrizza).
    # avanzo piano finché la camera rivede la striscia (dopo il passo indietro può essere fuori vista)
    t0 = time.time()
    Incr, box, img = None, None, None
    viste = []                                        # [FIX 81] cosa ha visto YOLO avanzando
    while time.time() - t0 < 1.5:
        img = FotogrammaNuovo()
        if img is None:
            return
        Incr, _, _, _ = WebCam.VerificaVerde(img)
        viste.append(Incr)
        box = WebCam.UltimoBoxLinea[0]
        if Incr == "In" and box is not None:
            break
        Rwd.Dritto(int(RwdConf.VelCrs * 0.7), 0.15, heading_ref=rotta)
        Rwd.Stop()
    if Incr != "In" or box is None:
        if viste and viste.count("Ln") >= max(2, len(viste) - 1):
            print(f"Centratura sull'ingresso: striscia non vista, YOLO vede la linea ({viste.count('Ln')} volte su {len(viste)})")
            return "linea"                            # [FIX 81] la linea continua: non è l'ingresso
        print("Centratura sull'ingresso: striscia non vista")
        return False
    H, W = img.shape[:2]
    u0, u1 = box[0] * W / 224.0, box[2] * W / 224.0
    v = (box[1] + box[3]) / 2 * H / 224.0
    meta = RwdConf.INGRESSO_STRISCIA_CM / 2
    spost = 0.0
    if u0 > 6 and u1 >= W - 6:            # si vede l'estremità SINISTRA: la porta è più a destra
        spost = TerrenoDaPixel(u0, v, W, H)[1] + meta
    elif u1 < W - 6 and u0 <= 6:          # si vede l'estremità DESTRA: la porta è più a sinistra
        spost = TerrenoDaPixel(u1, v, W, H)[1] - meta
    if abs(spost) < RwdConf.INGRESSO_TOLLERANZA_CM:
        print(f"Centratura sull'ingresso: centrato ({spost:+.1f} cm)")
        return True
    print(f"Centratura sull'ingresso: porta {abs(spost):.0f} cm a {'destra' if spost > 0 else 'sinistra'}, mi sposto")
    lato = 1 if spost > 0 else -1
    via = (rotta + 40 * lato) % 360
    Rwd.Dritto(-RwdConf.VelCrs, 0.6, heading_ref=rotta)
    Rwd.Stop()
    Rwd.RuotaVerso(via, tolleranza=2, timeout=3.0)
    Rwd.Dritto(RwdConf.VelCrs, abs(spost) / math.sin(math.radians(40)) / RwdConf.VelocitaArenaCmS, heading_ref=via)
    Rwd.Stop()
    Rwd.RuotaVerso(rotta, tolleranza=2, timeout=3.0)
    Rwd.Stop()
    return True


def DirezioneIngresso(Crop):
    # [FIX 71] In che direzione entrare nell'arena? Perpendicolare alla striscia argento, cioè lungo la linea
    # nera che arriva alla striscia.
    #  1) LINEA: retta sui pixel neri tra il robot e la striscia (sotto il riquadro "In" di YOLO); il suo
    #     angolo rispetto alla verticale dell'immagine si somma alla direzione del robot;
    #  2) GRIGLIA: le piastrelle (e i muri dell'arena) sono a 90 gradi da RiferimentoGriglia, misurato alla
    #     partenza. Se la linea dice quasi la stessa cosa (entro 10 gradi) si fa la media; se la linea non si
    #     vede si usa il lato delle piastrelle più vicino (entro 20 gradi) oppure, se il robot stava girando,
    #     il lato successivo nel verso della svolta (come FIX 62);
    #  3) se non si sa niente: la direzione attuale (come prima).
    import numpy as np
    global IngressoLato
    IngressoLato = 0
    _, _, hd = Rwd.GetGyro()
    # 0) SVOLTA APPENA FATTA: se negli ultimi SVOLTA_INGRESSO_S secondi il robot ha girato a un incrocio,
    #    la direzione giusta è quella prima della svolta + 90 gradi (scatola nera 26/10: prima 353, poi
    #    l'argento visto a 41 gradi a metà curva; giusto era 83)
    if SvoltaAttesa is not None and time.time() - SvoltaAttesa[0] <= RwdConf.SVOLTA_INGRESSO_S:
        attesa = SvoltaAttesa[1]
        if abs(angle_difference(attesa, hd)) <= 70:
            if RiferimentoGriglia is not None:
                # la direzione prima della svolta non è sempre precisa (il robot può arrivare all'incrocio
                # uscendo da una curva): ci si aggancia al lato delle piastrelle più vicino
                dg = angle_difference(attesa, RiferimentoGriglia)
                g = (RiferimentoGriglia + 90 * round(dg / 90.0)) % 360
                # [FIX 96] prima solo entro 25 gradi: nel simulatore (pista della scuola, seme 3) la direzione
                # prima della svolta era sbagliata di 26 gradi, il robot è entrato verso 116 invece di 90, ha
                # preso lo spigolo della porta ed è rimasto incastrato. La porta è in un muro parallelo alle
                # piastrelle: ci si aggancia al lato più vicino fino a INGRESSO_AGGANCIO_GRADI.
                if abs(angle_difference(attesa, g)) <= getattr(RwdConf, "INGRESSO_AGGANCIO_GRADI", 25):
                    attesa = g
            # [FIX 101] DA CHE PARTE E' ARRIVATO IL ROBOT. Scatole nere 05/11: alle 15:52 (svolta a SINISTRA prima
            # dell'argento) il fianco sinistro toccava lo stipite; alle 16:12 (svolta a DESTRA) il robot era spostato a
            # destra della porta (laser davanti a 20 cm: muro, non la porta) ma si spostava a destra lo stesso, perché
            # il lato si deduceva da un errore di direzione di 4 gradi. Il prof: "il sistema si deve regolare in base
            # alla direzione dell'ultima svolta prima dell'argento". Il robot gira quando la camera (12 cm davanti alle
            # ruote) è sull'incrocio: il centro del robot resta indietro, cioè dalla parte da cui arriva. Dopo una
            # svolta a destra è spostato a DESTRA della porta e deve andare a SINISTRA, e viceversa.
            verso = SvoltaAttesa[2] if len(SvoltaAttesa) > 2 else 0
            IngressoLato = -verso
            if verso:
                print(f"Ingresso subito dopo una svolta a {'DESTRA' if verso > 0 else 'SINISTRA'}: entro verso {attesa:.0f} "
                      f"(robot a {hd}); se serve mi sposto a {'sinistra' if verso > 0 else 'destra'}")
            else:
                print(f"Ingresso subito dopo una svolta: entro verso {attesa:.0f} (robot a {hd})")
            return attesa
    linea = None
    box = WebCam.UltimoBoxLinea[0]
    # la retta si cerca sotto la striscia: solo se il riquadro di YOLO è stretto (striscia di traverso);
    # con la striscia di sbieco il riquadro copre quasi tutta l'immagine
    if box is not None and (box[3] - box[1]) > 0.6 * 224:
        box = None
    if box is not None and Crop is not None:
        H = Crop.shape[0]
        y0 = int(min(H - 1, max(0, box[3] * H / 224.0)))
        if H - y0 >= 0.15 * H:
            g = cv2.cvtColor(Crop[y0:, :, :3], cv2.COLOR_BGR2GRAY)
            ys, xs = np.nonzero(g < RwdConf.SOGLIA_NERO)
            if len(xs) >= 150:
                vx, vy, _, _ = cv2.fitLine(np.column_stack([xs, ys]).astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).flatten()
                if vy > 0:
                    vx, vy = -vx, -vy
                ang = math.degrees(math.atan2(vx, -vy))
                if abs(ang) <= 70:
                    linea = (hd + ang) % 360
    griglia = None
    if RiferimentoGriglia is not None:
        base = linea if linea is not None else hd
        dg = angle_difference(base, RiferimentoGriglia)
        griglia = (RiferimentoGriglia + 90 * round(dg / 90.0)) % 360
    if linea is not None:
        if griglia is not None and abs(angle_difference(linea, griglia)) <= 10:
            rotta = (linea + angle_difference(griglia, linea) / 2) % 360
            print(f"Ingresso: linea verso {linea:.0f}, piastrelle verso {griglia:.0f}: entro verso {rotta:.0f} (robot a {hd})")
        elif griglia is not None and abs(angle_difference(linea, griglia)) <= getattr(RwdConf, "INGRESSO_AGGANCIO_GRADI", 0):
            # [FIX 96] la retta sui pixel neri può prendere un pezzo di curva: la porta è comunque parallela
            # alle piastrelle, quindi vale il lato delle piastrelle
            rotta = griglia
            print(f"Ingresso: linea verso {linea:.0f} ma piastrelle verso {griglia:.0f}: entro verso {rotta:.0f} (robot a {hd})")
        else:
            rotta = linea
            print(f"Ingresso: la linea va verso {linea:.0f} (robot a {hd}): entro così")
        return rotta
    if griglia is not None:
        giro = 0.0
        if StoricoRotta:
            giro = angle_difference(hd, StoricoRotta[0][1])        # quanto ho girato negli ultimi secondi
        if abs(angle_difference(hd, griglia)) <= 25:
            print(f"Ingresso: linea non misurabile, lato delle piastrelle verso {griglia:.0f} (robot a {hd})")
            return griglia
        if abs(giro) > 20:
            dg = angle_difference(hd, RiferimentoGriglia)
            passo = math.ceil(dg / 90.0) if giro > 0 else math.floor(dg / 90.0)
            avanti = (RiferimentoGriglia + 90 * passo) % 360
            if abs(angle_difference(hd, avanti)) <= 60:
                print(f"Ingresso: stavo girando ({giro:+.0f} gradi): entro verso {avanti:.0f} (robot a {hd})")
                return avanti
    print(f"Ingresso: direzione non misurabile, entro dritto verso {hd}")
    return hd


# ===========================================================================================
#   [FIX 53] USCITA COSTEGGIANDO LE PARETI (metodo della squadra, 22/10)
# ===========================================================================================
# lato = +1: parete a SINISTRA del robot (agli angoli gira a destra); lato = -1: parete a DESTRA.
def RottaParete(hd):
    # Le pareti dell'arena sono a multipli di 90 gradi rispetto alla direzione con cui il robot è entrato.
    base = RottaArena if RottaArena is not None else 0
    return (base + 90 * round(angle_difference(hd, base) / 90.0)) % 360


def GiraA(rotta):
    # Ruota fino alla direzione assoluta "rotta". Se non ci arriva (per esempio uno spigolo del robot
    # tocca un triangolo o la parete) arretra un po' e riprova una volta.
    for tentativo in range(2):
        if getattr(RwdConf, "DRITTO_RUOTA_GRADI", 0):
            # [FIX 64] rotazione ad anello chiuso: arriva entro 3 gradi (prima Gira si fermava a 3 gradi ma
            # il robot continuava a ruotare e nella scatola nera finiva 8-14 gradi oltre, ad ogni angolo).
            # [FIX 65] se la rotazione è bloccata il giroscopio se ne accorge in 0,6 s (prima 4 s di timeout)
            esito = Rwd.RuotaVerso(rotta, VelArena, tolleranza=3, timeout=6.0)
            if esito is True:
                return True
            if esito == "bloccato":
                print("Giroscopio: la rotazione è bloccata, uno spigolo tocca qualcosa. Arretro e riprovo")
            else:
                print("Non riesco a girarmi: arretro e riprovo")
        else:
            _, _, hd = Rwd.GetGyro()
            Rwd.Gira(angle_difference(rotta, hd), VelArena, timeout=4.0)
            Rwd.Stop()
            _, _, hd = Rwd.GetGyro()
            if abs(angle_difference(rotta, hd)) < 15:
                return True
            print("Non riesco a girarmi: arretro e riprovo")
        Rwd.Sterzo(-VelArena, 0)
        time.sleep(0.4)
        Rwd.Stop()
    return False


def ArduinoVivo():
    # Se Arduino non manda dati da più di 0,3 s, laser e giroscopio sono a 0: il robot si ferma e aspetta
    # fino a 3 s invece di guidare alla cieca (scatola nera del 21/10, secondo 443).
    if time.time() - getattr(Rwd, "_last_packet_time", time.time()) < 0.3:
        return True
    Rwd.Stop()
    print("Arduino non risponde: mi fermo e aspetto")
    t0 = time.time()
    while time.time() - t0 < 3.0:
        time.sleep(0.1)
        if time.time() - getattr(Rwd, "_last_packet_time", 0) < 0.3:
            return True
    return False


def ScegliLatoGiro():
    # "Capire che giro fare": si costeggia la parete laterale più vicina.
    dSx, _, dDx = LaserVeri()
    lato = 1 if dSx <= dDx else -1
    print(f"Giro dell'arena: parete a {'SINISTRA' if lato > 0 else 'DESTRA'} (sx {dSx} cm, dx {dDx} cm)")
    return lato


def AvvicinatiAlMuro(lato):
    # Si mette parallelo alle pareti e, se la parete scelta è lontana, ci va vicino e si rigira.
    # Mentre va verso la parete guarda il pavimento: davanti potrebbe esserci proprio un'apertura
    # (nel simulatore il robot puntava dritto sull'uscita, non trovava il muro e usciva dall'arena alla cieca).
    # Restituisce (rotta, uscito).
    _, _, hd = Rwd.GetGyro()
    rotta = RottaParete(hd)
    GiraA(rotta)
    dSx, _, dDx = LaserVeri()
    muro = dSx if lato > 0 else dDx
    if muro > RwdConf.APERTURA_CM:
        verso_muro = (rotta - 90 * lato) % 360
        GiraA(verso_muro)
        t0 = time.time()
        while time.time() - t0 < 8.0:
            cosa, angolo = GuardaPavimento(apertura_davanti=True)
            if cosa == "nero":                # andando verso la parete ho trovato l'uscita
                EsciSullaStriscia(angolo)
                return rotta, True
            if cosa == "argento":             # davanti c'è l'ingresso: mi fermo e torno un po' indietro
                Rwd.Stop()
                print("Andando verso la parete ho trovato l'INGRESSO: torno indietro")
                Rwd.Dritto(-int(VelArena * 0.7), 0.6, heading_ref=verso_muro)
                break
            _, dFr, _ = LaserVeri()
            if dFr <= 10:                     # muso a 10 cm: spazio per girarsi senza toccare (anche i triangoli)
                break
            Rwd.Dritto(int(VelArena * 0.7), 0.1, heading_ref=verso_muro)
        Rwd.Stop()
        GiraA(rotta)
    return rotta, False


def SwitchSpento(dove):
    # [FIX 105] Lo switch è stato spento (LoP o fine prova)? Allora fermo i motori, lo scrivo e rispondo True:
    # chi mi chiama deve uscire subito. Con lo switch spento Rwd.Dritto esce senza muovere il robot (FIX 88),
    # quindi un ciclo "a tempo" fatto solo di Dritto e LaserVeri girerebbe a vuoto.
    if Rwd.GetSwitch()['sw_sof']:
        return False
    Rwd.Stop()
    print(f"Switch spento: interrompo {dove}")
    return True


def ControllaAperturaMuro(rotta, lato):
    # Il laser laterale è appena "caduto" in un'apertura.
    # 1) Continuo finché lo stesso laser rivede la parete: così so quanto è larga l'apertura.
    # 2) Torno indietro di metà del tempo: il robot è davanti al centro dell'apertura (non serve sapere
    #    la velocità, avanti e indietro vanno alla stessa velocità).
    # 3) Mi giro verso l'apertura e guardo: camera LINEA sul pavimento (striscia nera = uscita, argento =
    #    ingresso) e camera ARENA con il modello delle porte. Se non è chiaro, avanzo piano guardando il pavimento.
    # Restituisce "uscita" (ed è già uscito), "ingresso" o None (non era una porta).
    VelP = int(VelArena * 0.7)
    print("Apertura nel muro: la misuro")
    t0 = time.time()
    nell_angolo = False
    while time.time() - t0 < 3.0:
        # [FIX 105] PROGRAMMA PIANTATO CON LO SWITCH SPENTO. Rapporto di Shuri del 5/11 (V37, prova
        # stress_guasti_reali) e simulatore V31 con la V39: LoP a 417,9 s mentre il robot misurava un'apertura
        # nel giro dei muri. Con lo switch spento Dritto esce subito, nessuno aspetta: nel simulatore il tempo
        # non avanzava più e la gara restava ferma per sempre; sul robot vero il ciclo girava a vuoto per 3 s
        # e poi il robot continuava il controllo della porta (rotazioni, foto) come se avesse misurato davvero.
        # Ora con lo switch spento si esce subito, come fa già GiroDeiMuri a ogni passo.
        if SwitchSpento("la misura dell'apertura"):
            return None
        Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
        dSx, dFr, dDx = LaserVeri()
        muro = dSx if lato > 0 else dDx
        if muro <= RwdConf.APERTURA_CM:
            break
        if dFr < RwdConf.ANGOLO_CM:
            nell_angolo = True                         # [FIX 70] l'apertura arriva fino all'angolo
            break
    durata = time.time() - t0
    Rwd.Stop()
    larga = durata * RwdConf.VelocitaArenaCmS        # solo per il messaggio
    if nell_angolo:
        # [FIX 70] PORTA NELL'ANGOLO. Il muro davanti ha fermato la misura: la porta finisce nell'angolo e la
        # misura è più corta del vero. Prima il robot tornava indietro di metà del tempo, si fermava troppo
        # vicino allo stipite e girandosi verso la porta ci restava incastrato (simulatore, pista lunga).
        # Ora avanza fino a PORTA_ANGOLO_CM dal muro davanti: il centro del robot è a circa 15 cm dall'angolo,
        # cioè in mezzo a una porta da 27-30 cm, e c'è ancora spazio per girarsi.
        print(f"L'apertura arriva fino all'angolo: mi metto a {RwdConf.PORTA_ANGOLO_CM} cm dal muro davanti")
        t1 = time.time()
        while time.time() - t1 < 2.0:
            if SwitchSpento("la misura dell'apertura"):      # [FIX 105]
                return None
            _, dFr, _ = LaserVeri()
            if dFr <= RwdConf.PORTA_ANGOLO_CM:
                break
            Rwd.Dritto(int(VelArena * 0.5), 0.1, heading_ref=rotta)
        Rwd.Stop()
    else:
        if durata < 0.5:
            print(f"Apertura troppo stretta (circa {larga:.0f} cm): non è una porta")
            return None
        Rwd.Dritto(-VelP, durata / 2, heading_ref=rotta)   # "torno un po' indietro": centro dell'apertura
        Rwd.Stop()
    verso_porta = (rotta - 90 * lato) % 360
    if SwitchSpento("il controllo dell'apertura"):          # [FIX 105]
        return None
    GiraA(verso_porta)
    # camera arena: attaccata alla porta la vede troppo da vicino, quindi prima mi allontano un po'
    # dalla parete (come proposto dalla squadra), faccio 3 foto (vince la maggioranza) e torno
    Rwd.Dritto(-VelP, RwdConf.INDIETRO_CAMERA_S, heading_ref=verso_porta)
    Rwd.Stop()
    time.sleep(0.3)                                    # immagini nuove a robot fermo
    voti = []
    for _ in range(3):
        tipo, conf = WebCam.TipoPorta(WebCam.CamAr.capture_array())
        if tipo:
            voti.append(tipo)
    tipo_cam = max(set(voti), key=voti.count) if voti else None
    Rwd.Dritto(VelP, RwdConf.INDIETRO_CAMERA_S, heading_ref=verso_porta)
    Rwd.Stop()
    time.sleep(0.3)
    # camera linea: la striscia è proprio davanti al muso, dove la camera arena non arriva
    cosa, angolo = GuardaPavimento(apertura_davanti=True)
    print(f"Apertura larga circa {larga:.0f} cm: camera arena dice {tipo_cam}, pavimento {cosa}")
    if cosa == "nero":
        esito = "uscita"
    elif cosa == "argento":
        esito = "ingresso"
    else:
        esito = tipo_cam
    avanzato = 0.0
    if esito is None:
        # nessuno dei due è sicuro: avanzo piano guardando il pavimento.
        # [FIX 63] max 2,5 s (prima 1 s): a ~7 cm/s in 1 s il robot faceva 7 cm e, se era lontano dal muro,
        # la striscia restava fuori dalla camera (scatola nera 23/10, secondo 356: "pavimento None")
        t1 = time.time()
        while time.time() - t1 < 2.5:
            if SwitchSpento("il controllo dell'apertura"):  # [FIX 105]
                return None
            cosa, angolo = GuardaPavimento(apertura_davanti=True)
            _, dFr, _ = LaserVeri()
            if cosa in ("nero", "argento") or dFr < 6:
                break
            Rwd.Dritto(int(VelArena * 0.5), 0.1, heading_ref=verso_porta)
        avanzato = time.time() - t1
        Rwd.Stop()
        esito = "uscita" if cosa == "nero" else "ingresso" if cosa == "argento" else None
    if esito == "uscita":
        print("E' l'USCITA: esco")
        esito_u = EsciControllando(verso_porta, RwdConf.TempoUscitaPorta, nero_gia_visto=(cosa == "nero"))
        if esito_u in ("uscita", "incerto"):
            return "uscita"
        # "ingresso": uscendo ha visto l'argento (già rientrato); [FIX 84] "bloccato": tornato dentro dallo stipite
        esito = "ingresso" if esito_u == "ingresso" else None
        avanzato = 0.0
    if avanzato > 0:
        Rwd.Dritto(-int(VelArena * 0.5), avanzato, heading_ref=verso_porta)
        Rwd.Stop()
    if esito == "ingresso":
        print("E' l'INGRESSO: riprendo il giro")
        PorteScartate.append(verso_porta)
    else:
        print("Non era una porta: riprendo il giro")
    # mi rigiro nel verso di marcia e supero l'apertura finché il laser rivede la parete
    GiraA(rotta)
    t2 = time.time()
    while time.time() - t2 < 2.5:
        if SwitchSpento("il giro dei muri"):                # [FIX 105]
            return None
        Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
        dSx, dFr, dDx = LaserVeri()
        muro = dSx if lato > 0 else dDx
        if muro <= RwdConf.APERTURA_CM or dFr < RwdConf.ANGOLO_CM:
            break
    Rwd.Stop()
    return esito


_storico_moto = []          # [FIX 55] (istante, immagine arena piccola in grigi, rotta)


def RobotFermo():
    # [FIX 55] Il robot sta davvero avanzando? Con i soli 3 laser non sempre si capisce: se uno spigolo tocca
    # uno stipite che i laser non vedono, le letture restano uguali e il robot spinge per sempre (simulatore,
    # uscita vicino a un angolo). Si confronta l'immagine della camera arena con quella di 1,5 s prima:
    # se è quasi uguale e la rotta non è cambiata, il robot è fermo.
    import numpy as np                     # RwdFoto.py non lo importava in cima
    try:
        img = WebCam.CamAr.capture_array()
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (32, 24), interpolation=cv2.INTER_AREA).astype(np.int16)
    except Exception:
        return False
    _, _, hd = Rwd.GetGyro()
    _, dFr, _ = LaserVeri()
    t = time.time()
    _storico_moto.append((t, g, hd, dFr))
    while _storico_moto and t - _storico_moto[0][0] > 2.0:
        _storico_moto.pop(0)
    vecchi = [s for s in _storico_moto if t - s[0] >= 1.5]
    if not vecchi:
        return False
    if abs(angle_difference(hd, vecchi[-1][2])) >= 3:
        return False                                   # sto girando: non sono fermo
    # [FIX 63] col nuovo giro dei muri il robot ruota a destra e a sinistra di qualche grado: se negli
    # ultimi 2 s la direzione è cambiata di 3 gradi o più non è incastrato (prima: falso "Non avanzo" e il
    # robot si staccava dal muro passando davanti all'uscita senza vederla, simulatore pista lunga)
    if max(abs(angle_difference(hd, s[2])) for s in _storico_moto) >= 3:
        return False
    recenti = [s[3] for s in _storico_moto]
    if max(recenti) < 120:
        # il laser frontale vede qualcosa: se avanzo la distanza deve diminuire
        return max(recenti) - min(recenti) < 1.5
    # davanti è tutto libero (per esempio una porta): decide l'immagine della camera arena
    diff = float(np.mean(np.abs(g - vecchi[-1][1])))
    return diff < RwdConf.FERMO_SOGLIA


# ===========================================================================================
#   [FIX 63] SEGUIRE IL MURO A DISTANZA COSTANTE
# ===========================================================================================
# Scatola nera del 23/10: nel giro dei muri il robot doveva stare a 5 cm, invece stava a 10-30 cm e si
# allontanava sempre di più lungo ogni parete. Due motivi:
#  1) la correzione era "piega la rotta di al massimo 20 gradi" e poi Dritto(0,1 s): con i servo a rotazione
#     continua una correzione di sterzo sotto ~40 NON fa girare il robot (misurato sui dati: a velocità 47
#     con sterzo tra -50 e +50 il robot gira di 0-5 gradi al secondo). Girava solo grazie a un errore della
#     derivata in Dritto (vedi FIX 64), un colpetto ogni 0,1 s: troppo poco;
#  2) la direzione dei muri veniva solo dalla direzione d'ingresso (RottaArena): se è sbagliata di qualche
#     grado il robot va "parallelo" a un muro che non c'è.
# Ora, a ogni passo:
#  - distanza vera dal muro = lettura del laser laterale x coseno dell'angolo col muro;
#  - errore = distanza - LATO_MURO_CM; angolo voluto verso il muro = PARETE_KP x errore (max 25 gradi);
#  - se il robot è storto più di PARETE_ERR_RUOTA gradi si raddrizza RUOTANDO SUL POSTO (RuotaVerso),
#    poi avanza dritto PARETE_PASSO_S secondi;
#  - [PARETE_STIMA] mentre avanza confronta come cambia davvero la distanza con come dovrebbe cambiare se il
#    muro fosse nella direzione stimata: la differenza dice di quanti gradi è sbagliata la direzione del muro
#    e la corregge un po' alla volta (la correzione vale anche per i muri successivi).

def NuovaParete(rotta, prima=None):
    # Stato del controllo per un tratto di parete. "corr" = correzione (gradi) della direzione dei muri
    # imparata finora: si porta dietro da un muro all'altro.
    return {"rotta": rotta % 360, "corr": prima["corr"] if prima else 0.0,
            "s": 0.0, "t": None, "prec": None, "res": 0.0, "ds": 0.0, "letture": [], "voluta": None}


def AsseParete(st):
    # direzione stimata del muro che sto seguendo
    return (st["rotta"] + st["corr"]) % 360


def SeguiParete(lato, muro, st, davanti=None):
    # Un passo del giro dei muri (circa PARETE_PASSO_S secondi). lato = +1 muro a sinistra, -1 a destra.
    # [FIX 94] davanti = laser frontale filtrato: serve ad anticipare gli angoli e i triangoli
    VelP = int(VelArena * 0.7)
    _, _, hd = Rwd.GetGyro()
    asse = AsseParete(st)
    alfa = -lato * angle_difference(hd, asse)          # gradi: + = muso verso il muro, - = via dal muro
    # mediana delle ultime 3 letture: un riflesso o una lettura storta non fanno sterzare il robot
    st["letture"] = (st["letture"] + [muro])[-3:]
    muro = sorted(st["letture"])[len(st["letture"]) // 2]
    adesso = time.time()
    if st["t"] is not None:
        st["s"] += RwdConf.VelocitaArenaCmS * min(0.5, adesso - st["t"])   # cm percorsi (stima)
    st["t"] = adesso
    dist = muro * math.cos(math.radians(alfa))          # distanza perpendicolare dal muro
    # --- stima della direzione vera del muro
    if getattr(RwdConf, "PARETE_STIMA", False):
        # si usa solo quando il robot sta già seguendo bene il muro (entro 5 cm dalla distanza voluta) e dopo
        # i primi 10 cm del tratto: vicino agli angoli il laser vede spesso il triangolo, non il muro
        vicino = abs(dist - RwdConf.LATO_MURO_CM) < 5 and st["s"] > 10
        # [FIX 94] mentre anticipa un angolo il robot si allontana apposta dal muro e il laser laterale vede spesso il
        # triangolo: niente stima (nel simulatore la "correzione" arrivava a +20 gradi e il robot si incastrava)
        if davanti is not None and 0 < davanti < RwdConf.PARETE_ANTICIPO_CM:
            vicino = False
        if st["prec"] is not None and vicino:
            s0, d0, a0 = st["prec"]
            ds, dd = st["s"] - s0, dist - d0
            if 0 < ds < 5 and abs(dd) < 3:              # niente salti (pallina, apertura)
                # se il muro fosse proprio in direzione "asse", avanzando di ds la distanza cambierebbe
                # di -sin(alfa) x ds. Quello che avanza è l'errore di direzione.
                st["res"] += dd + math.sin(math.radians(a0)) * ds
                st["ds"] += ds
        st["prec"] = (st["s"], dist, alfa) if vicino else None
        if st["ds"] >= 15:
            eps = -math.degrees(st["res"] / st["ds"])   # gradi in più verso il muro, rispetto alla stima
            passo = max(-5.0, min(5.0, 0.5 * lato * eps))   # al massimo 5 gradi alla volta
            lim = RwdConf.PARETE_STIMA_MAX
            st["corr"] = max(-lim, min(lim, st["corr"] + passo))
            if abs(passo) >= 2:
                print(f"Muro: direzione corretta di {passo:+.0f} gradi (totale {st['corr']:+.0f})")
            st["res"], st["ds"] = 0.0, 0.0
            asse = AsseParete(st)
            alfa = -lato * angle_difference(hd, asse)
    # [FIX 94] ANTICIPO DELLE SVOLTE. Quando il laser frontale comincia a leggere poco (angolo, triangolo nell'angolo,
    # pallina contro il muro) il robot comincia ad ALLONTANARSI dal muro mentre avanza: la distanza voluta passa
    # da LATO_MURO_CM a LATO_MURO_CM + PARETE_ANTICIPO_LATO tra PARETE_ANTICIPO_CM e ANGOLO_CM. Così quando gira
    # di 90 gradi all'angolo ha spazio: ruotando sul posto il retro del robot va verso il muro (scatola nera 05/11:
    # "Non avanzo" a 215 e 235 s, rotazioni bloccate a 247 e 250 s). Non serve sapere dove sono i triangoli: il
    # laser frontale vede sia il muro sia il lato lungo del triangolo.
    lato_voluto = RwdConf.LATO_MURO_CM
    if davanti is not None and 0 < davanti < RwdConf.PARETE_ANTICIPO_CM:
        f = min(1.0, (RwdConf.PARETE_ANTICIPO_CM - davanti) / float(RwdConf.PARETE_ANTICIPO_CM - RwdConf.ANGOLO_CM))
        lato_voluto += RwdConf.PARETE_ANTICIPO_LATO * f
        if f >= 0.3 and not st.get("anticipo_detto"):
            print(f"Muro davanti a {davanti} cm: anticipo la svolta, mi stacco dalla parete fino a {lato_voluto:.0f} cm")
            st["anticipo_detto"] = True
    # --- angolo voluto rispetto al muro
    if muro > 60:
        alfa_voluto = 0.0                               # il laser non vede il muro: tengo la direzione
    else:
        errore = dist - lato_voluto
        amax = RwdConf.PARETE_ANGOLO_MAX
        alfa_voluto = max(-amax, min(amax, RwdConf.PARETE_KP * errore))
    voluta = (asse - lato * alfa_voluto) % 360
    # la direzione voluta cambia al massimo di PARETE_VOLUTA_PASSO gradi per passo (prima 8): vicino a superfici
    # storte (il lato lungo di un triangolo) il laser cambia molto appena il robot ruota e il robot "ballava" a
    # destra e a sinistra senza avanzare (simulatore)
    lim = RwdConf.PARETE_VOLUTA_PASSO
    if st["voluta"] is not None:
        voluta = (st["voluta"] + max(-lim, min(lim, angle_difference(voluta, st["voluta"])))) % 360
    st["voluta"] = voluta
    passo = RwdConf.PARETE_PASSO_S
    if abs(angle_difference(voluta, hd)) > RwdConf.PARETE_ERR_RUOTA:
        # [FIX 94] tolleranza più larga e meno tempo: nella scatola nera del 05/11 il robot passava più tempo a
        # ruotare di 2-3 gradi che ad avanzare (46 cm in 15 s lungo una parete)
        esito = Rwd.RuotaVerso(voluta, tolleranza=RwdConf.PARETE_TOLL_RUOTA, timeout=1.0)
        if esito == "bloccato":
            # [FIX 94] uno spigolo tocca (di solito il retro contro il muro): prima riprovava a ruotare per 40 s
            # (simulatore). Arretro un poco senza ruotare e al prossimo passo riprovo.
            print("Muro: rotazione bloccata, arretro un poco")
            Rwd.Dritto(-VelP, 0.4, heading_ref=hd, ruota=False)
            Rwd.Stop()
        st["t"] = time.time()                           # mentre ruota non avanza
        st["prec"] = None                               # e il laser laterale cambia per la rotazione
        passo = max(passo, 0.3)                         # dopo una rotazione avanzo un po' di più
    Rwd.Sterzo(VelP, 0)
    time.sleep(passo)


def GiroDeiMuri(lato, rotta):
    # Costeggia le pareti tenendo il fianco a LATO_MURO_CM. Agli angoli (o davanti a un triangolo) gira di
    # 90 gradi. Quando il laser laterale salta da "parete vicina" a "lontano" controlla l'apertura.
    # Restituisce True se è uscito.
    VelP = int(VelArena * 0.7)
    letture = []               # ultime distanze laterali (per riconoscere il SALTO di un'apertura)
    agganciato = 0             # da quanti passi sto seguendo la parete
    _storico_moto.clear()
    nuovo = getattr(RwdConf, "PARETE_KP", 0) > 0        # [FIX 63] controllo nuovo della distanza
    st = NuovaParete(rotta)
    appena_girato = False      # [FIX 63] subito dopo un angolo: l'apertura potrebbe essere proprio lì
    fermi = 0                  # [FIX 63] quante volte di fila "Non avanzo" sullo stesso muro
    t0 = time.time()
    while time.time() - t0 < RwdConf.TEMPO_MAX_MURI:
        if not Rwd.GetSensori()['switch'][1]:
            Rwd.Stop()
            return False
        if not ArduinoVivo():
            return False
        dSx, dFr, dDx = LaserVeri()
        muro = dSx if lato > 0 else dDx
        # la striscia nera sotto il muso vale sempre come uscita
        cosa, angolo = GuardaPavimento(apertura_davanti=False)
        if cosa == "nero" and time.time() < NeroScartatoFino:
            cosa = None                                 # [FIX 104] appena scartata (muro davanti)
        if cosa == "nero":
            if nuovo and abs(angolo) < 30:
                lett = st["letture"] or [muro]
                muro_medio = sorted(lett)[len(lett) // 2]
                if EsciDallaPortaDavanti(lato, AsseParete(st), muro_medio):     # [FIX 69]
                    return True
                letture, agganciato = [], 0
                st["prec"], st["t"] = None, None
                continue
            if EsciSullaStriscia(angolo):               # [FIX 104] prima "uscito" anche quando non era uscito
                return True
            letture, agganciato = [], 0
            st["prec"], st["t"] = None, None
            continue
        # angolo o triangolo davanti: giro di 90 gradi dalla parte opposta alla parete
        if dFr < RwdConf.ANGOLO_CM:
            Rwd.Stop()
            rotta = (rotta + 90 * lato) % 360
            st = NuovaParete(rotta, st)                 # [FIX 63] la correzione imparata resta
            GiraA(AsseParete(st) if nuovo else rotta)
            letture, agganciato = [], 0
            _storico_moto.clear()
            appena_girato = nuovo
            fermi = 0
            continue
        # [FIX 63] PORTA SUBITO DOPO L'ANGOLO. Nell'arena della scuola l'uscita comincia a pochi cm
        # dall'angolo: dopo la svolta il laser laterale guarda già dentro la porta, non c'è nessun "salto"
        # da vicino a lontano e il robot ci passava davanti senza controllarla (simulatore, arena_parete).
        if appena_girato:
            if muro > 50:
                print("Dopo l'angolo il laser laterale vede lontano: forse una porta proprio qui")
                appena_girato = False
                esito = ControllaAperturaMuro(AsseParete(st), lato)
                if esito == "uscita":
                    return True
                letture, agganciato = [], 5
                st["prec"], st["t"] = None, None
                continue
            if muro <= RwdConf.APERTURA_CM:
                appena_girato = False
        # [FIX 65] il pavimento dell'arena è piano: se il giroscopio vede il robot inclinato, sta salendo su
        # qualcosa (una pallina rimasta, il bordo di un triangolo). Arretro un po'.
        pitch, roll, _ = Rwd.GetGyro()
        if nuovo and max(abs(pitch), abs(roll)) > getattr(RwdConf, "PARETE_MAX_INCLINAZIONE", 99):
            Rwd.Stop()
            print(f"Giroscopio: robot inclinato (pitch {pitch}, roll {roll}), sto salendo su qualcosa. Arretro")
            Rwd.Dritto(-VelP, 0.6, heading_ref=AsseParete(st))
            Rwd.Stop()
            letture = []
            continue
        # [FIX 55] non avanzo: uno spigolo tocca qualcosa che i laser non vedono
        if nuovo and dFr < 20 and RobotFermo():
            # [FIX 70] non avanzo e il muro (o un triangolo) è vicino davanti: è un angolo, anche se il laser
            # frontale legge ancora più di ANGOLO_CM (lo spigolo del robot tocca il lato lungo del triangolo
            # prima che il laser lo veda vicino: simulatore, pista lunga). Arretro e giro come in un angolo.
            print("Non avanzo e davanti è vicino: è un angolo, arretro e giro")
            Rwd.Stop()
            Rwd.Dritto(-VelP, 0.5, heading_ref=AsseParete(st))
            Rwd.Stop()
            rotta = (rotta + 90 * lato) % 360
            st = NuovaParete(rotta, st)
            GiraA(AsseParete(st))
            letture, agganciato, fermi = [], 0, 0
            _storico_moto.clear()
            appena_girato = True
            continue
        if RobotFermo() and nuovo and fermi < 2:
            # [FIX 63] prime volte: arretro, mi giro di 20 gradi via dal muro, avanzo un po' e continuo a
            # seguire il muro (prima si staccava e andava dritto fino al muro davanti senza seguire la parete:
            # se l'uscita era lì in mezzo non la vedeva)
            fermi += 1
            Rwd.Stop()
            print("Non avanzo: forse uno spigolo contro uno stipite. Arretro e riprovo un po' più staccato")
            asse = AsseParete(st)
            Rwd.Dritto(-VelP, 0.5, heading_ref=asse)
            Rwd.RuotaVerso((asse + lato * 20) % 360, tolleranza=3, timeout=1.5)
            Rwd.Dritto(VelP, 0.5, heading_ref=(asse + lato * 20) % 360)
            Rwd.Stop()
            _storico_moto.clear()
            st["prec"], st["t"], st["voluta"] = None, None, None
            continue
        if RobotFermo():
            fermi = 0
            Rwd.Stop()
            print("Non avanzo: forse uno spigolo contro uno stipite. Arretro")
            if nuovo:
                rotta_n = rotta                         # [FIX 63] da qui uso la direzione corretta del muro
                rotta = AsseParete(st)
            Rwd.Dritto(-VelP, 0.5, heading_ref=rotta)
            Rwd.Stop()
            _, dFr, _ = LaserVeri()
            if dFr >= 60:
                # davanti è libero: probabilmente c'è un'apertura vicino all'angolo. Mi stacco dalla parete
                # di qualche centimetro e riprovo guardando il pavimento.
                print("Davanti è libero: mi stacco dalla parete e riprovo guardando il pavimento")
                fuori = (rotta + 90 * lato) % 360
                GiraA(fuori)
                Rwd.Dritto(VelP, 0.5, heading_ref=fuori)
                GiraA(rotta)
                t1 = time.time()
                ingresso = False
                while time.time() - t1 < 8.0:              # fino al muro davanti (o alla striscia)
                    cosa, angolo = GuardaPavimento(apertura_davanti=True)
                    if cosa == "nero":
                        EsciSullaStriscia(angolo)
                        return True
                    if cosa == "argento":
                        ingresso = True
                        break
                    _, dFr, _ = LaserVeri()
                    if dFr < RwdConf.ANGOLO_CM:
                        break
                    Rwd.Dritto(VelP, 0.1, heading_ref=rotta)
                Rwd.Stop()
                if ingresso:
                    print("Era l'INGRESSO: torno indietro e continuo il giro")
                    Rwd.Dritto(-VelP, 0.8, heading_ref=rotta)
                    Rwd.Stop()
            # in ogni caso proseguo come dopo un angolo
            if nuovo:
                rotta = (rotta_n + 90 * lato) % 360
                st = NuovaParete(rotta, st)
                GiraA(AsseParete(st))
            else:
                rotta = (rotta + 90 * lato) % 360
                GiraA(rotta)
            letture, agganciato = [], 0
            _storico_moto.clear()
            continue
        # apertura: il laser laterale SALTA da vicino a lontano mentre seguivo la parete
        # [FIX 55] basta che poco prima la parete fosse entro 20 cm (prima servivano 5 passi "agganciato":
        # avvicinandosi in diagonale il robot passava davanti all'uscita senza considerarla)
        if muro > RwdConf.APERTURA_CM and letture and min(letture[-3:]) <= 20 and muro - min(letture[-3:]) > 8:
            esito = ControllaAperturaMuro(AsseParete(st) if nuovo else rotta, lato)
            if esito == "uscita":
                return True
            letture, agganciato = [], 5
            st["prec"], st["t"] = None, None
            continue
        if muro <= RwdConf.APERTURA_CM:
            agganciato += 1
        letture = (letture + [muro])[-5:]
        if nuovo:
            SeguiParete(lato, muro, st, Rwd.FrontaleFiltrato())   # [FIX 63] [FIX 94]
            continue
        # (V24) seguo la parete: se sono lontano correggo verso di lei (al massimo 20 gradi), se troppo vicino mi allontano
        corr = max(-20.0, min(20.0, (muro - RwdConf.LATO_MURO_CM) * 2.0))
        Rwd.Dritto(VelP, 0.1, heading_ref=(rotta - lato * corr) % 360)
    Rwd.Stop()
    print("Giro delle pareti: uscita non trovata nel tempo massimo")
    return False


def EsciDallaPortaDavanti(lato, asse, muro):
    # [FIX 69] Seguendo il muro il robot trova la striscia NERA sotto il muso: l'uscita è nel muro DAVANTI.
    # Nell'arena della scuola l'uscita comincia a pochi cm dall'angolo: tenendo il fianco a 6,5 cm dal muro
    # il robot sfiorava lo spigolo della porta e si incastrava (simulatore, arena_parete). Se invece la porta
    # comincia proprio nell'angolo, staccarsi troppo fa toccare l'altro stipite (simulatore, pista lunga).
    # Prima di uscire mi porto con il fianco a PORTA_LATO_CM dal muro che seguivo (laser laterale "muro"):
    # così il robot (largo 15,6 cm) passa in una porta da 27 cm che comincia tra 0 e circa 8 cm dall'angolo.
    # Se serve mi sposto di lato (arretro, ruoto di 35 gradi, avanzo, mi raddrizzo), poi esco dritto lungo la
    # direzione del muro, non lungo la striscia vista storta dalla camera.
    # Restituisce True se è uscito, False se uscendo ha visto l'argento (era l'ingresso, già rientrato).
    VelP = int(VelArena * 0.7)
    stacco = max(-3.0, min(6.0, getattr(RwdConf, "PORTA_LATO_CM", 9.5) - muro))
    print(f"Striscia NERA davanti mentre seguo il muro: è l'USCITA. Fianco a {muro:.0f} cm dal muro, "
          f"mi sposto di {stacco:+.0f} cm ed esco dritto")
    Rwd.Stop()
    if abs(stacco) >= 1.5:
        Rwd.Dritto(-VelP, 0.6, heading_ref=asse)
        verso = 1 if stacco > 0 else -1               # +1 = verso l'interno dell'arena
        via = (asse + lato * verso * 35) % 360
        Rwd.RuotaVerso(via, tolleranza=2, timeout=2.0)
        Rwd.Dritto(VelP, abs(stacco) / math.sin(math.radians(35)) / RwdConf.VelocitaArenaCmS, heading_ref=via)
    Rwd.RuotaVerso(asse, tolleranza=2, timeout=2.0)
    Rwd.Stop()
    # [FIX 104] LA PORTA COMINCIA PIU' IN LA'. Scatola nera 06/11 ore 10:48 (V38), 238 s: striscia nera davanti mentre
    # seguiva il muro, ma il laser davanti misurava 13-14 cm: era il muro accanto alla porta (la porta comincia a
    # qualche cm dall'angolo). Il robot ha spinto contro il muro per 5 tentativi (laser a 4 cm), poi ha rifatto tutto il
    # giro: uscito solo a 349 s, quasi 2 minuti dopo. Ora, se davanti c'è muro, cerca l'apertura spostandosi a piccoli
    # passi verso l'INTERNO dell'arena (dall'altra parte c'è il muro che seguiva).
    arretrato, trovata, _ = CercaApertura(asse, lato, getattr(RwdConf, "USCITA_LIBERO_CM", 30), "Uscita",
                                          " (verso l'interno dell'arena)", un_lato=True)
    if not trovata:
        ScartaNero("striscia nera ma davanti c'è muro: non è la porta, continuo il giro dei muri")
        return False
    print("Esco dalla porta")
    return EsciControllando(asse, RwdConf.TempoUscitaPorta + 0.6 + arretrato / RwdConf.VelocitaArenaCmS,
                            nero_gia_visto=True) not in ("ingresso", "bloccato")   # [FIX 84]


def TrovaUscitaArena():
    # Chiamata dal programma principale dopo le palline. Cerca l'uscita con TrovaUscitaIA (camera
    # dell'arena, poi giro dei muri). In ogni modo in cui esce, ora esce con EsciControllando, che guarda
    # il pavimento a ogni passo: striscia ARGENTO = è l'ingresso, torna dentro e la ricerca continua;
    # striscia NERA = uscita confermata. Fuori controlla di ritrovare la linea nera.
    if getattr(RwdConf, "USCITA_MODO", "camera") == "muri":
        # [FIX 53] metodo della squadra: costeggiare le pareti; se non trova l'uscita, metodo di prima
        Rwd.GetOnLed1()
        Rwd.GetOnLed2()
        lato = ScegliLatoGiro()
        rotta, uscito = AvvicinatiAlMuro(lato)
        if not uscito:
            uscito = GiroDeiMuri(lato, rotta)
        if not uscito and Rwd.GetSensori()['switch'][1]:
            print("Passo alla ricerca dell'uscita con la camera")
            TrovaUscitaIA(0)
        Rwd.GetOffLed1()
        Rwd.GetOffLed2()
    else:
        TrovaUscitaIA(0)
    if not Rwd.GetSensori()['switch'][1]:
        return False
    global UscitaArenaFatta
    UscitaArenaFatta = True                           # [FIX 66]
    if LineaFuori():
        print("Uscita confermata: ritrovata la linea nera fuori dall'arena")
    else:
        print("Uscito, ma la linea non si vede ancora: la cerca il seguilinea")
    return True


def LineaFuori():
    # [FIX 46] Fuori dall'arena c'è la linea nera: una macchia nera grande che NON sia la striscia d'uscita.
    for _ in range(5):
        img = Immagine
        if img is not None:
            if WebCam.StrisciaNera(img) is None:
                trovata, _, _, _ = WebCam.CercaBlocchiCol(img, "nero", WebCam.AreaSigBk)
                if trovata:
                    return True
        time.sleep(0.1)
    return False


def SquadraSullUscita(rotta):
    # [FIX 84] DRITTI E IN MEZZO ALLA PORTA D'USCITA, USANDO LA STRISCIA NERA (non il giroscopio).
    # Shuri, prova "giroscopio disturbato di 15 gradi", secondo 345: girandosi verso la porta il robot si fidava
    # del giroscopio, è arrivato storto di 4-5 gradi e spostato di 9 cm, lo spigolo ha preso lo stipite e per
    # 100 s ha spinto contro la porta ("Alto" ripetuto): LoP nella zona. La striscia nera dell'uscita è lunga
    # quanto la porta e sta proprio sulla soglia: la sua INCLINAZIONE nell'immagine dice di quanto il robot è
    # storto, la sua ESTREMITÀ (se si vede) dice dov'è lo stipite. Come il FIX 71 per l'ingresso.
    # Restituisce la nuova rotta (quella da tenere uscendo).
    img = FotogrammaNuovo()
    geo = WebCam.GeometriaStrisciaNera(img)
    if geo is None:
        return rotta
    angolo = geo[0]
    if angolo is not None and RwdConf.USCITA_SQUADRA_GRADI <= abs(angolo) <= 30:
        print(f"Uscita: la striscia nera è inclinata di {angolo:+.0f} gradi, mi raddrizzo")
        _, _, hd = Rwd.GetGyro()
        Rwd.RuotaVerso((hd + angolo) % 360, tolleranza=1.5, timeout=3.0)
        Rwd.Stop()
        _, _, rotta = Rwd.GetGyro()
        img = FotogrammaNuovo()
        geo = WebCam.GeometriaStrisciaNera(img)
        if geo is None:
            return rotta
    _, (u0, v0), (u1, v1), W, H = geo
    meta = RwdConf.INGRESSO_STRISCIA_CM / 2           # la striscia d'uscita è lunga come quella d'ingresso
    sx_vista = u0 > 0.03 * W
    dx_vista = u1 < 0.97 * W
    if sx_vista and dx_vista:
        spost = (TerrenoDaPixel(u0, v0, W, H)[1] + TerrenoDaPixel(u1, v1, W, H)[1]) / 2
    elif sx_vista:
        spost = TerrenoDaPixel(u0, v0, W, H)[1] + meta  # vedo la fine SINISTRA: la porta è più a destra
    elif dx_vista:
        spost = TerrenoDaPixel(u1, v1, W, H)[1] - meta  # vedo la fine DESTRA: la porta è più a sinistra
    else:
        return rotta                                  # la striscia esce dai due lati: sono in mezzo
    if abs(spost) < RwdConf.USCITA_TOLLERANZA_CM:
        print(f"Uscita: centrato sulla porta ({spost:+.1f} cm)")
        return rotta
    print(f"Uscita: porta {abs(spost):.0f} cm a {'destra' if spost > 0 else 'sinistra'}, mi sposto prima di uscire")
    lato = 1 if spost > 0 else -1
    via = (rotta + 40 * lato) % 360
    Rwd.Dritto(-int(VelArena * 0.7), 0.6, heading_ref=rotta)
    Rwd.Stop()
    Rwd.RuotaVerso(via, tolleranza=2, timeout=3.0)
    Rwd.Dritto(int(VelArena * 0.7), abs(spost) / math.sin(math.radians(40)) / RwdConf.VelocitaArenaCmS, heading_ref=via)
    Rwd.Stop()
    Rwd.RuotaVerso(rotta, tolleranza=1.5, timeout=3.0)
    Rwd.Stop()
    return rotta


def Protetto(fase):
    # [FIX 100] UN ERRORE NEL CODICE NON DEVE FINIRE LA GARA. Scatola nera 05/11 ore 15:52 (V35): un errore
    # (FIX 99) durante l'uscita dall'arena ha fermato tutto il programma e la gara era finita. Ora, se una fase
    # (seguilinea, arena, uscita) va in errore, l'errore si stampa per intero (finisce nella scatola nera), i motori
    # si fermano e il programma passa alla fase successiva invece di chiudersi.
    try:
        return fase()
    except Exception:
        import traceback
        Rwd.Stop()
        print(f"ERRORE NEL CODICE in {fase.__name__}: passo alla fase successiva")
        for riga in traceback.format_exc().rstrip().splitlines():
            print("   " + riga)
        return None


def StrisciaFerma(storia):
    # [FIX 84] Uscendo dalla porta, il robot è incastrato contro lo stipite? Si guarda la striscia NERA dell'uscita
    # con la camera linea: se il robot avanza, in un secondo la striscia scorre verso il basso e sparisce; se resta
    # nello stesso punto dell'immagine per USCITA_FERMO_S secondi, le ruote spingono ma il robot non si muove.
    # (RobotFermo, con la camera arena, dava falsi allarmi appena fuori dalla porta: vede solo bianco.)
    geo = WebCam.GeometriaStrisciaNera(Immagine)
    t = time.time()
    v = None if geo is None else (geo[1][1] + geo[2][1]) / 2
    storia.append((t, v))
    while storia and t - storia[0][0] > RwdConf.USCITA_FERMO_S + 1.0:
        storia.pop(0)
    # [FIX 99] solo i campioni vecchi in cui la striscia si vedeva. Scatola nera 05/11 ore 15:52 (V35), 284 s:
    # uscendo, dopo "tocco lo stipite, riprovo", il campione vecchio era senza striscia (None) e il programma si è
    # fermato con "TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'".
    vecchi = [s for s in storia if t - s[0] >= RwdConf.USCITA_FERMO_S and s[1] is not None]
    if v is None or not vecchi:
        return False
    if any(s[1] is None for s in storia if t - s[0] <= RwdConf.USCITA_FERMO_S):
        return False
    return abs(v - vecchi[-1][1]) < RwdConf.USCITA_FERMO_PX


def EsciDallaPorta(rotta, durata):
    # [FIX 103] USCIRE DALLA PORTA COME SI ENTRA. Scatola nera 06/11 ore 10:15 (V37), secondi 259-267: uscendo verso 91
    # gradi, laser sinistro a 12-13 cm (lo stipite sinistro), il robot si gira da solo a sinistra (91 -> 80: fianco
    # sinistro agganciato) e Dritto lo raddrizza RUOTANDO SUL POSTO dentro la porta (lo stesso errore del FIX 93
    # all'ingresso). Poi "Uscito", ma il seguilinea gira a sinistra e trova "un ostacolo a 8 cm": era il muro.
    # Il controllo del FIX 84 (striscia nera ferma nell'immagine) funziona solo finché la camera vede la striscia: lo
    # stipite lo tocca il fianco, quando la camera (12 cm più avanti) è già oltre.
    # Ora la porta d'uscita si passa con lo stesso sistema dell'ingresso (PassaLaPorta): avanti senza ruotare sul
    # posto, controllo "mi sono girato da solo" / "non avanzo" (laser davanti e striscia nera), arretra, si raddrizza,
    # si sposta di lato e riprova. Da che parte provare prima: lontano dal laser laterale più vicino (lo stipite).
    # Restituisce "uscita", oppure "bloccato" se non è riuscito (si torna al giro dei muri, come nel FIX 84).
    sx, _, dx = LaserVeri()
    lato0 = 1 if sx < dx else -1
    # [FIX 104] prima di spingere: davanti c'è davvero l'apertura? (tutte le uscite vere del 5 e 6/11: laser davanti
    # 44-91 cm; il muro accanto alla porta: 13-14 cm). Se no la cerca di lato, prima dalla parte più libera.
    arretrato, trovata, _ = CercaApertura(rotta, lato0, getattr(RwdConf, "USCITA_LIBERO_CM", 30), "Uscita")
    if not trovata:
        Rwd.Dritto(-int(VelArena * 0.7), 0.6, heading_ref=rotta, ruota=False)
        Rwd.Stop()
        ScartaNero("davanti c'è muro: non è la porta, riprendo il giro dei muri")
        return "bloccato"
    durata += arretrato / RwdConf.VelocitaArenaCmS
    if PassaLaPorta(rotta, durata, lato0, "Uscita", getattr(RwdConf, "USCITA_TENTATIVI", 5), ultimo_spinge=False,
                    extra_ritento=getattr(RwdConf, "USCITA_EXTRA_RITENTO_S", 0.6)):
        _, _, hd = Rwd.GetGyro()
        if abs(angle_difference(rotta, hd)) > 8:
            print(f"Uscito storto di {angle_difference(hd, rotta):+.0f} gradi: mi raddrizzo ora che sono fuori")
            Rwd.RuotaVerso(rotta, tolleranza=3, timeout=3.0)
            Rwd.Stop()
        return "uscita"
    print("Uscendo sono ancora contro lo stipite: torno dentro e riprendo il giro dei muri")
    Rwd.Dritto(-int(VelArena * 0.7), 1.0, heading_ref=rotta, ruota=False)
    Rwd.Stop()
    return "bloccato"


def EsciControllando(rotta, durata, nero_gia_visto=False):
    # [FIX 46] Esce dritto (col giroscopio) a passi di 0,1 s guardando il pavimento con la camera linea.
    #  - striscia ARGENTO: questa porta è l'INGRESSO. Torna indietro di quanto ha fatto e restituisce "ingresso".
    #  - striscia NERA: è l'uscita, continua. Restituisce "uscita" (o "incerto" se non ha visto nessuna striscia).
    # Il tempo si conta dall'inizio (anche mentre YOLO guarda il pavimento le ruote vanno avanti),
    # così la distanza percorsa è la stessa di prima con un solo Dritto(durata).
    nero = nero_gia_visto
    argento_di_fila = 0
    squadrato = False
    if nero_gia_visto:
        rotta = SquadraSullUscita(rotta)              # [FIX 84] dritto e in mezzo alla porta prima di uscire
        return EsciDallaPorta(rotta, durata)          # [FIX 103]
    sblocchi = 0                                      # [FIX 84] quante volte mi sono già staccato dallo stipite
    storia_striscia = []                              # [FIX 84] dove si vede la striscia nera, istante per istante
    t0 = time.time()
    while time.time() - t0 < durata:
        fermo = StrisciaFerma(storia_striscia)
        if fermo and sblocchi >= 2:
            # [FIX 84] ancora contro lo stipite dopo 2 tentativi: questa uscita non riesce da qui. Prima il robot
            # credeva di essere uscito e il seguilinea spingeva contro la porta fino alla LoP. Ora torna dentro
            # e lo dice: chi lo ha chiamato riprende il giro dei muri e ritenta la porta da un'altra posizione.
            Rwd.Stop()
            print("Uscendo sono ancora contro lo stipite: torno dentro e riprendo il giro dei muri")
            Rwd.Dritto(-int(VelArena * 0.7), 1.0, heading_ref=rotta)
            Rwd.Stop()
            return "bloccato"
        if fermo:
            # [FIX 84] le ruote spingono ma il robot non avanza: uno spigolo è contro lo stipite della porta.
            # Prima il robot restava lì (100 s nella prova di Shuri). Ora arretro, mi rimetto dritto e in mezzo
            # guardando la striscia nera e riprovo (al massimo 2 volte).
            sblocchi += 1
            Rwd.Stop()
            print("Uscendo non avanzo: tocco lo stipite. Arretro, mi rimetto in mezzo alla porta e riprovo")
            Rwd.Dritto(-int(VelArena * 0.7), 0.8, heading_ref=rotta)
            Rwd.Stop()
            rotta = SquadraSullUscita(rotta)
            storia_striscia.clear()
            t0 = time.time()
            continue
        cosa, _ = GuardaPavimento(apertura_davanti=True)
        # [FIX 53] il NERO vince sull'argento: se la striscia nera è già stata vista, un "argento" dopo è un
        # riflesso (scatola nera del 21/10, secondi 448 e 453: luce riflessa sul pavimento presa per argento).
        # E l'argento deve essere visto in 2 fotogrammi di fila.
        argento_di_fila = argento_di_fila + 1 if (cosa == "argento" and not nero) else 0
        if argento_di_fila >= 2:
            fatto = time.time() - t0
            Rwd.Stop()
            print("Striscia ARGENTO sotto il muso: questa è l'INGRESSO, torno dentro")
            PorteScartate.append(rotta)
            Rwd.Dritto(-VelArena, fatto + 0.3, heading_ref=rotta)
            Rwd.Stop()
            return "ingresso"
        if cosa == "nero" and not nero:
            nero = True
            print("Striscia NERA sotto il muso: è l'USCITA")
        if nero and not squadrato:
            # [FIX 84] appena vedo la striscia nera mi raddrizzo e mi centro, PRIMA di arrivare agli stipiti
            squadrato = True
            Rwd.Stop()
            rotta = SquadraSullUscita(rotta)
            return EsciDallaPorta(rotta, durata)      # [FIX 103] la porta si passa come all'ingresso
        Rwd.Dritto(VelArena, 0.1, heading_ref=rotta)
    Rwd.Stop()
    if not nero:
        print("Uscito senza vedere la striscia nera")
    return "uscita" if nero else "incerto"


def AnalizzaIncrocio(img, soglia_nero=110, run_min=18, bordo=5):
    # [FIX 59] Incrocio (o ramo laterale) SENZA verde: da regolamento si va dritti.
    # Si guardano i punti in cui la linea nera tocca il BORDO dell'immagine ("bracci"): una linea,
    # una curva o un angolo ne hanno 2 (da dove arriva e dove va), un incrocio 3 o 4.
    # Braccio d'arrivo = quello sul bordo basso più vicino al centro; braccio dritto = quello opposto.
    # Controlli contro i falsi incroci (angolo acuto con la punta sul bordo, due linee vicine):
    #  - tutti i bracci attaccati allo stesso pezzo di linea;
    #  - il tratto arrivo->dritto è nero quasi tutto (è davvero una linea dritta);
    #  - ogni braccio laterale parte da quel tratto ed è nero fino al bordo, quasi perpendicolare.
    # Risponde (True, angolo in gradi del braccio dritto rispetto alla verticale dell'immagine,
    # y dell'incrocio) oppure (False, 0, 0).
    import numpy as np, math
    import cv2
    g = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    m = g < soglia_nero
    H, W = m.shape
    if m.sum() < 800:
        return False, 0.0, 0
    alto = m[:bordo, :].any(axis=0)
    destra = m[:, W - bordo:].any(axis=1)
    basso = m[H - bordo:, :].any(axis=0)[::-1]
    sinistra = m[:, :bordo].any(axis=1)[::-1]
    perim = np.concatenate([alto, destra, basso, sinistra])
    coord = ([(x, 0) for x in range(W)] + [(W - 1, y) for y in range(H)] +
             [(x, H - 1) for x in range(W - 1, -1, -1)] + [(0, y) for y in range(H - 1, -1, -1)])
    n = len(perim)
    if perim.all() or not perim.any():
        return False, 0.0, 0
    inizio = int(np.argmin(perim))
    bracci, run = [], []
    for k in range(1, n + 1):
        i = (inizio + k) % n
        if perim[i]:
            run.append(i)
        elif run:
            if len(run) >= run_min:
                bracci.append(coord[run[len(run) // 2]])
            run = []
    if len(bracci) < 3:
        return False, 0.0, 0
    _, etich = cv2.connectedComponents(m.astype(np.uint8))
    def pezzo(b):
        x0, y0 = b
        f = etich[max(0, y0 - bordo):y0 + bordo + 1, max(0, x0 - bordo):x0 + bordo + 1]
        v = f[f > 0]
        return int(np.bincount(v).argmax()) if len(v) else -1
    mg = cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0     # tolleranza di qualche pixel
    def nero(a, b):
        return float(np.mean([mg[int(round(a[1] + (b[1] - a[1]) * t)), int(round(a[0] + (b[0] - a[0]) * t))]
                              for t in np.linspace(0.05, 0.95, 30)]))
    sotto = [i for i, (bx, by) in enumerate(bracci) if by >= H - 1]
    i_in = min(sotto, key=lambda i: abs(bracci[i][0] - W / 2)) if sotto else max(range(len(bracci)), key=lambda i: bracci[i][1])
    P = bracci[i_in]
    dif = lambda a, b: (a - b + 540) % 360 - 180
    ang_da = lambda a, b: math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1])))
    # braccio dritto: quello che con il braccio d'arrivo forma la linea più nera e più dritta
    migliore = None
    for i_out in range(len(bracci)):
        if i_out == i_in or pezzo(bracci[i_out]) != pezzo(P):
            continue
        Q = bracci[i_out]
        f = nero(P, Q)
        if f < 0.85:
            continue
        lat = []
        for j in range(len(bracci)):
            if j in (i_in, i_out) or pezzo(bracci[j]) != pezzo(P):
                continue
            S = bracci[j]
            vx, vy = Q[0] - P[0], Q[1] - P[1]
            t = ((S[0] - P[0]) * vx + (S[1] - P[1]) * vy) / float(vx * vx + vy * vy)
            if not 0.15 < t < 0.85:
                continue
            J = (P[0] + t * vx, P[1] + t * vy)
            if 55 <= abs(dif(ang_da(J, S), ang_da(P, Q))) <= 125 and nero(J, S) >= 0.85:
                lat.append(J)
        if lat and (migliore is None or f > migliore[0]):
            migliore = (f, i_out, lat)
    if migliore is None:
        return False, 0.0, 0
    _, i_out, lat = migliore
    J = (np.mean([p[0] for p in lat]), np.mean([p[1] for p in lat]))
    return True, dif(ang_da(J, bracci[i_out]), 0), int(J[1])


UltimoIncrocio = 0.0


def IncrocioDritto(img):
    # [FIX 59] Se davanti c'è un incrocio senza verde (YOLO ha detto solo "linea"), il seguilinea a
    # PID seguiva il baricentro del nero: arrivando un po' storti (per esempio dopo un anello o una
    # curva stretta) prendeva il braccio laterale e finiva su una linea fuori sequenza (nel
    # simulatore fino a 3 LoP a gara). Ora il robot si gira verso il braccio OPPOSTO a quello da cui
    # arriva e attraversa l'incrocio dritto col giroscopio. Risponde True se ha attraversato.
    global UltimoIncrocio
    if time.time() - UltimoIncrocio < RwdConf.INCROCIO_PAUSA_S:
        return False
    # [FIX 92] SUBITO DOPO UNA SVOLTA AL VERDE NON SI "RADDRIZZA". Scatola nera 05/11 (V30): con le svolte
    # "vecchie" il robot gira solo di 42 gradi e il seguilinea finisce la curva; mentre è ancora sopra
    # l'incrocio, questa funzione lo prendeva per un incrocio SENZA verde e lo rigirava verso il braccio
    # "dritto", cioè annullava la svolta: 10,7 s (dopo la destra: correzione -31, il robot torna sulla linea
    # lunga invece di scendere), 16,3 s (dopo la sinistra: +28), 23,9 s (+68), 39,9 s (+24), 56,9 s alla
    # rotonda (+73). Per INCROCIO_DOPO_SVOLTA_S secondi dopo una svolta al verde si lascia fare al seguilinea.
    if time.time() - FineSvoltaVerde < getattr(RwdConf, "INCROCIO_DOPO_SVOLTA_S", 0.0):
        return False
    trovato, ang, y_inc = AnalizzaIncrocio(img, RwdConf.SOGLIA_NERO)
    if not trovato or y_inc < 0.35 * img.shape[0]:
        return False
    UltimoIncrocio = time.time()
    print(f"Incrocio senza verde: lo attraverso dritto (correzione {ang:.0f} gradi)")
    Rwd.Stop()
    if abs(ang) > 4:
        Rwd.Gira(ang, VelCross)
        Rwd.Stop()
    _, _, rotta = Rwd.GetGyro()
    Rwd.Dritto(RwdConf.VelCrs, RwdConf.INCROCIO_DRITTO_S, heading_ref=rotta)
    return True


def VedoLinea():
    # [FIX 58] Foto scattata a robot fermo: True se YOLO vede la linea (o un suo elemento: verdi,
    # interruzione, striscia argento o rossa), False se vede solo bianco.
    FotogrammaNuovo()
    Incr, _, _, _ = WebCam.VerificaVerde(Immagine)
    if Incr == "In" and UscitaArenaFatta:
        # [FIX 98] Scatola nera 05/11 ore 15:12, secondo 470: dopo l'altalena il robot ha perso la linea e il
        # ventaglio si è fermato su una striscia ARGENTO ("linea ritrovata girando di -30"), girandosi verso
        # l'arena già fatta. Uscito dall'arena, l'argento non è la linea da seguire.
        return False
    return Incr not in ("No", "Bi")


def GiraVerso(rotta):
    _, _, hd = Rwd.GetGyro()
    d = angle_difference(rotta, hd)
    if abs(d) > 3:
        Rwd.Gira(d, VelCross)
    Rwd.Stop()


def RecuperaLinea():
    # [FIX 58] Ricerca della linea persa senza mai andare avanti alla cieca.
    # 1) ventaglio sul posto: RECUPERO_ANGOLI rispetto alla direzione di quando l'ha persa;
    # 2) se non la vede: torna dritto, arretra a piccoli passi (al massimo RECUPERO_RETRO_S secondi)
    #    guardando dopo ogni passo: la linea c'era, sulla strada appena fatta la ritrova;
    # 3) se ancora niente, rifà il ventaglio da lì. Risponde True se l'ha ritrovata.
    Rwd.Stop()
    _, _, h0 = Rwd.GetGyro()
    for giro in range(2):
        for a in RwdConf.RECUPERO_ANGOLI:
            GiraVerso((h0 + a) % 360)
            if VedoLinea():
                print(f"Linea ritrovata girando di {a} gradi")
                return True
        GiraVerso(h0)
        if giro == 1:
            break
        t0 = time.time()
        while time.time() - t0 < RwdConf.RECUPERO_RETRO_S:
            Rwd.Sterzo(-VelCross, 0)
            time.sleep(0.15)
            Rwd.Stop()
            if VedoLinea():
                print("Linea ritrovata tornando indietro")
                return True
    print("Linea NON ritrovata")
    return False


def AltalenaNellaStoria(storia, salto, salita_min):
    # [FIX 102] Cerca nello storico (istante, beccheggio, rotta) un muso in SU (almeno salita_min gradi) seguito da un
    # muso in GIU' di almeno "salto" gradi in meno. Restituisce (campione col muso più in alto, campione più in basso)
    # oppure None.
    i_max = None
    for i, c in enumerate(storia):
        if i_max is None or c[1] > storia[i_max][1]:
            i_max = i
            continue
        alto = storia[i_max]
        if alto[1] >= salita_min and alto[1] - c[1] >= salto:
            j = min(range(i, len(storia)), key=lambda k: storia[k][1])      # il punto più basso
            return alto, storia[j]
    return None


def AspettaGiroscopioFermo():
    # [FIX 102] dopo un colpo forte il BNO055 per un attimo dà rotte sballate (scatola nera 05/11 16:12, 423 s:
    # 154 -> 111 -> 74 -> 29 gradi in 0,3 s con il robot inclinato): si aspetta che beccheggio e rotta restino
    # fermi per ALTALENA_STABILE_S (al massimo ALTALENA_ATTESA_MAX_S)
    t0 = time.time()
    stabile = getattr(RwdConf, "ALTALENA_STABILE_S", 0.5)
    letture = []                                      # (istante, beccheggio, rotta) lette qui, ogni 0,05 s
    while time.time() - t0 < getattr(RwdConf, "ALTALENA_ATTESA_MAX_S", 2.5):
        time.sleep(0.05)
        b, _, h = Rwd.GetGyro()
        adesso = time.time()
        letture.append((adesso, b, h))
        if adesso - t0 < stabile:
            continue
        st = [c for c in letture if adesso - c[0] <= stabile]
        if len(st) < 3:
            continue
        hs = [c[2] for c in st]
        giro = max(abs(angle_difference(h, hs[0])) for h in hs)
        bs = [c[1] for c in st]
        # [FIX 104] scatola nera 06/11 10:48, 369-371 s: dopo la caduta il robot resta FERMO sulla tavola abbassata, a
        # -18 gradi: prima si aspettava di tornare in piano (sotto 8 gradi) e si perdevano sempre 2,5 s. Conta che il
        # beccheggio non cambi più (entro 3 gradi), anche se il robot è inclinato.
        if max(bs) - min(bs) <= 3 and giro < 3:
            media = sum(bs) / len(bs)
            print(f"Altalena: giroscopio fermo dopo {time.time() - t0:.1f} s"
                  + (f" (robot inclinato di {media:+.0f} gradi: sono ancora sulla tavola)" if abs(media) >= 8 else ""))
            return True
    print("Altalena: il giroscopio non si è calmato del tutto, vado avanti lo stesso")
    return False


def ControllaAltalena():
    # [FIX 102] L'ALTALENA. Scatole nere 05/11 (15:12 e 16:12): sull'altalena il robot sale con il muso in alto (+21 gradi
    # per 2 s), poi la tavola cade e in 0,7 s il beccheggio passa da +21 a -49 ("stoppie" sulle ruote davanti); il robot
    # perde la linea, YOLO vede una "discontinuità" e il giroscopio per un attimo dà rotte sballate: alle 16:12 il robot
    # ha attraversato un vuoto che non c'era verso 89 gradi (veniva da 240). Idea del prof: se il beccheggio cambia di
    # colpo di molti gradi, il robot capisce di aver appena superato un'altalena, lo scrive sullo schermo, aspetta che
    # il giroscopio si stabilizzi e ricontrolla la linea. Si riconosce: muso su di almeno ALTALENA_SALITA_MIN gradi
    # seguito, entro ALTALENA_FINESTRA_S, da un calo di almeno ALTALENA_SALTO_GRADI. Poi:
    #  1) fermo, "PROBABILE ALTALENA SUPERATA";
    #  2) attesa del giroscopio fermo; lo storico della rotta (con i valori sballati) si cancella;
    #  3) se la rotta è cambiata di più di 10 gradi rispetto a prima della caduta, si rimette nella direzione di prima
    #     (l'altalena è dritta: la linea continua da quella parte);
    #  4) ricontrolla la linea; se non la vede avanza un poco e riguarda; se ancora niente, la ricerca sicura.
    global UltimaAltalena
    if not getattr(RwdConf, "ALTALENA_ATTIVA", True):
        return False
    if time.time() - UltimaAltalena < getattr(RwdConf, "ALTALENA_PAUSA_S", 4.0):
        return False
    st = Rwd.StoriaBeccheggio(getattr(RwdConf, "ALTALENA_FINESTRA_S", 1.2))
    r = AltalenaNellaStoria(st, getattr(RwdConf, "ALTALENA_SALTO_GRADI", 30), getattr(RwdConf, "ALTALENA_SALITA_MIN", 10))
    if r is None:
        return False
    UltimaAltalena = time.time()
    (t1, b_alto, h_prima), (t2, b_basso, _) = r
    Rwd.Stop()
    print(f"PROBABILE ALTALENA SUPERATA: beccheggio da {b_alto:+d} a {b_basso:+d} gradi in {t2 - t1:.1f} s. "
          f"Mi fermo, aspetto il giroscopio e ricontrollo la linea")
    AspettaGiroscopioFermo()
    UltimaAltalena = time.time()
    StoricoRotta.clear()
    _, _, hd = Rwd.GetGyro()
    if abs(angle_difference(h_prima, hd)) > 10:
        print(f"Altalena: sono girato di {angle_difference(hd, h_prima):+.0f} gradi rispetto a prima della caduta: "
              f"torno verso {h_prima}")
        GiraVerso(h_prima)
    if VedoLinea():
        print("Altalena: la linea c'è, riparto")
        return True
    Rwd.Dritto(RwdConf.VelCrs, getattr(RwdConf, "ALTALENA_AVANZA_S", 0.4), heading_ref=h_prima)
    Rwd.Stop()
    if VedoLinea():
        print("Altalena: linea ritrovata un poco più avanti, riparto")
        return True
    print("Altalena: linea non vista, la cerco")
    RecuperaLinea()
    return True


def SeguiFinoAlVuoto():
    # [FIX 62] Segue piano il nastro nero fino alla sua fine: sterza verso la parte più LONTANA del nero
    # visibile (la fine del pezzo dritto prima del vuoto: come guardare lontano guidando, il robot si mette
    # in direzione del pezzo dritto) e si ferma quando il nero è quasi sparito, cioè quando la fine del
    # nastro è arrivata sotto il muso. Così arriva al vuoto sopra la linea e allineato.
    # Se il nero sparisce da un LATO dell'immagine il robot è ancora in curva (per esempio a metà di una
    # curva a U): non è la fine del nastro, quindi gira sul posto da quella parte finché lo rivede.
    import numpy as np
    t0 = time.time()
    ultimo_err = 0.0
    rotazioni = 0
    while time.time() - t0 < RwdConf.GAP_AVVICINA_S + 2.0 * rotazioni:
        g = cv2.cvtColor(Immagine[:, :, :3], cv2.COLOR_BGR2GRAY)
        ys, xs = np.nonzero(g < RwdConf.SOGLIA_NERO)
        if len(xs) < RwdConf.GAP_NERO_MIN:
            if abs(ultimo_err) > 0.35 and rotazioni < 6:
                rotazioni += 1
                Rwd.Gira(15 if ultimo_err > 0 else -15, VelCross)
                Rwd.Stop()
                FotogrammaNuovo()
                continue
            break
        lontano = ys <= np.percentile(ys, 30)
        ultimo_err = (xs[lontano].mean() - g.shape[1] / 2) / (g.shape[1] / 2)    # -1 sinistra .. +1 destra
        Rwd.Sterzo(int(RwdConf.VelCrs * 0.6), max(-70, min(70, 70 * ultimo_err)))
        time.sleep(0.08)
    Rwd.Stop()


def AttraversaVuoto():
    # [FIX 62] Il robot ha seguito la linea fino alla fine del nastro e ora vede solo bianco: va dritto con
    # la direzione che ha adesso (il PID l'ha appena allineato al pezzo dritto che da regolamento precede
    # ogni interruzione), tenendola col giroscopio, finché ricompare la linea (al massimo GAP_TEMPO_MAX).
    # Risponde True se l'ha ritrovata; se no RecuperaLinea farà la ricerca sicura.
    _, _, rotta = Rwd.GetGyro()
    # Da regolamento prima di un vuoto c'è un pezzo di linea DRITTO, e le piastrelle sono a 90 gradi
    # l'una dall'altra: se la direzione del robot è entro GAP_SCATTO_GRADI da un lato delle piastrelle
    # (dopo una curva a U il PID non fa in tempo ad allinearsi del tutto), si usa quella esatta.
    # Se il robot stava CURVANDO (per esempio a metà di una curva a U) il lato giusto è il prossimo nel
    # verso in cui gira, anche se è più lontano: dopo una U che va verso nord-ovest il pezzo dritto va a
    # ovest, non a nord.
    if RiferimentoGriglia is not None:
        dg = angle_difference(rotta, RiferimentoGriglia)
        griglia = (RiferimentoGriglia + 90 * round(dg / 90.0)) % 360
        velocita_giro = 0.0          # gradi/s nell'ultimo secondo di seguilinea prima dell'interruzione
        giro_totale = 0.0            # [FIX 85] gradi girati negli ultimi ~2 s di seguilinea
        if StoricoRotta:
            t_fine, h_fine = StoricoRotta[-1]
            prima = [s for s in StoricoRotta if t_fine - s[0] >= 0.8]
            if prima:
                velocita_giro = angle_difference(h_fine, prima[-1][1]) / max(0.1, t_fine - prima[-1][0])
            if t_fine - StoricoRotta[0][0] >= 1.5:
                giro_totale = angle_difference(h_fine, StoricoRotta[0][1])
        # [FIX 85] Shuri, campo contorto seme 1, secondo 29 (LoP che c'era dalla V25): interruzione subito dopo una
        # curva a U. Il robot aveva girato di 50 gradi negli ultimi 2 s, ma nell'ultimo 0,8 s solo a 19,6 gradi/s
        # (sotto i 25 della soglia): "non sto curvando", lato più vicino = nord, e ha attraversato verso la fila
        # vicina invece che verso ovest. Ora conta anche la rotazione TOTALE degli ultimi 2 s.
        if abs(velocita_giro) <= RwdConf.GAP_CURVA_GRADI_S and abs(giro_totale) > RwdConf.GAP_CURVA_TOT_GRADI:
            # segno della curva, e un valore sopra la soglia: per tutto il resto vale "sto curvando"
            velocita_giro = math.copysign(max(abs(giro_totale) / 2.0, RwdConf.GAP_CURVA_GRADI_S + 1), giro_totale)
            print(f"Negli ultimi 2 s ho girato di {giro_totale:.0f} gradi: ero in curva")
        if abs(velocita_giro) > RwdConf.GAP_CURVA_GRADI_S:
            passo = math.ceil(dg / 90.0 - 0.05) if velocita_giro > 0 else math.floor(dg / 90.0 + 0.05)
            avanti = (RiferimentoGriglia + 90 * passo) % 360
            if abs(angle_difference(rotta, avanti)) <= 60:
                griglia = avanti
                print(f"Stavo curvando ({velocita_giro:.0f} gradi/s): il pezzo dritto va verso {griglia:.0f}")
        if abs(angle_difference(rotta, griglia)) <= max(RwdConf.GAP_SCATTO_GRADI, 60 if abs(velocita_giro) > RwdConf.GAP_CURVA_GRADI_S else 0):
            rotta = griglia
            GiraVerso(rotta)
    print(f"Interruzione: attraverso il vuoto dritto verso {rotta} gradi")
    t0 = time.time()
    while time.time() - t0 < RwdConf.GAP_TEMPO_MAX:
        Rwd.Dritto(RwdConf.VelCrs, 0.15, heading_ref=rotta)
        Incr, _, _, _ = WebCam.VerificaVerde(Immagine)
        if Incr not in ("Bi", "Di", "No"):
            Rwd.Stop()
            print("Linea ritrovata dopo l'interruzione")
            return True
    Rwd.Stop()
    return False


def AttraversaInterruzione():
    # [FIX 57] Interruzione della linea (YOLO "Di", fino a 20 cm di vuoto).
    # 1) arretra di poco: così la camera vede tutto il pezzo dritto prima del vuoto (da regolamento
    #    almeno 5 cm di linea dritta);
    # 2) si allinea a quel pezzo: retta sui pixel neri della parte ALTA dell'immagine (la più lontana,
    #    cioè la linea che entra nel vuoto) e rotazioni di 0,7 x l'angolo finché è sotto 4 gradi.
    #    La prospettiva della camera esagera un po' l'angolo, per questo si gira a piccoli passi;
    # 3) va dritto tenendo la direzione col giroscopio finché ritrova la linea (al massimo
    #    GAP_TEMPO_MAX secondi, circa 25-30 cm), poi torna al seguilinea.
    import numpy as np
    Rwd.Stop()
    Rwd.Sterzo(-RwdConf.VelCrs, 0)
    time.sleep(RwdConf.GAP_RETRO_S)
    Rwd.Stop()
    for _ in range(4):
        FotogrammaNuovo()
        g = cv2.cvtColor(Immagine[:, :, :3], cv2.COLOR_BGR2GRAY)
        ys, xs = np.nonzero(g < RwdConf.SOGLIA_NERO)
        if len(xs) < 150:
            break
        alto = ys <= ys.min() + 0.4 * (ys.max() - ys.min())
        vx, vy, _, _ = cv2.fitLine(np.column_stack([xs[alto], ys[alto]]).astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        if vy > 0:
            vx, vy = -vx, -vy
        ang = math.degrees(math.atan2(vx, -vy))
        if abs(ang) < 4 or abs(ang) > 70:
            break
        Rwd.Gira(0.7 * ang, RwdConf.VelCrs)
        Rwd.Stop()
    _, _, rotta = Rwd.GetGyro()
    print(f"Interruzione: vado dritto verso {rotta} gradi")
    t0 = time.time()
    while time.time() - t0 < RwdConf.GAP_TEMPO_MAX:
        Rwd.Dritto(RwdConf.VelCrs, 0.15, heading_ref=rotta)
        Incr, _, _, _ = WebCam.VerificaVerde(Immagine)
        if time.time() - t0 > 0.4 and Incr not in ("Bi", "Di", "No"):
            print("Linea ritrovata dopo l'interruzione")
            break
    Rwd.Stop()


def ConfermaOstacolo():
    # [FIX 56] Distingue un ostacolo vero da una rampa. Il robot avanza piano (OST_VEL_CONFERMA) per al
    # massimo OST_TEMPO_CONFERMA secondi guardando laser frontale e beccheggio:
    #  - un ostacolo (alto almeno 15 cm) si lascia avvicinare: il laser scende fino a OST_CONFERMA_CM
    #    -> il robot si ferma, arretra un poco e la funzione risponde True (parte OstAutDet);
    #  - una rampa no: prima che il laser scenda così in basso le ruote davanti salgono e il robot si
    #    inclina oltre OST_RAMPA_GRADI -> risponde False e il seguilinea continua.
    # Se allo scadere del tempo non è successa nessuna delle due cose, per sicurezza è un ostacolo.
    # [FIX 87] Il laser è quello FILTRATO (mediana): prima bastava UNA lettura sbagliata a 5 cm per
    # "confermare" l'ostacolo (scatola nera 03/11, secondo 85: 5 cm e subito dopo 54, 74, 134 cm).
    # E se allo scadere del tempo il laser in mediana vede lontano (15 cm o più) non è un ostacolo ma una
    # lettura disturbata: prima "per sicurezza" diventava sempre un ostacolo (03/11, secondo 110).
    t0 = time.time()
    letture = []
    while time.time() - t0 < RwdConf.OST_TEMPO_CONFERMA:
        Rwd.Sterzo(RwdConf.OST_VEL_CONFERMA, 0)
        time.sleep(0.05)
        s = Rwd.GetSensori()
        dFr = Rwd.FrontaleFiltrato()      # [FIX 87]
        if dFr > 0:
            letture.append(dFr)
        beccheggio = s['imu'][0]          # [FIX 23] imu = (pitch, roll, heading)
        if abs(beccheggio) > RwdConf.OST_RAMPA_GRADI and not getattr(Rwd, "giroscopio_bloccato", False):
            Rwd.Stop()
            print(f"Non è un ostacolo: il robot si inclina di {beccheggio} gradi, è una RAMPA")
            return False
        if 0 < dFr <= RwdConf.OST_CONFERMA_CM:
            Rwd.Stop()
            print(f"Ostacolo confermato a {dFr} cm")
            Rwd.Sterzo(-RwdConf.OST_VEL_CONFERMA, 0)
            time.sleep(0.3)
            Rwd.Stop()
            return True
    Rwd.Stop()
    if letture:                                       # [FIX 87]
        mediana = sorted(letture)[len(letture) // 2]
        if mediana >= getattr(RwdConf, "OST_FALSO_CM", 15):
            print(f"Falso ostacolo: in {RwdConf.OST_TEMPO_CONFERMA} s il laser frontale ha letto in mediana {mediana} cm "
                  f"(lettura disturbata): continuo a seguire la linea")
            return False
        # [FIX 90] avanzando verso un ostacolo vero la distanza scende. Se non scende e di lato c'è una parete, il
        # robot sta strisciando lungo la parete (scatola nera 03/11 V30, secondo 101: 12 -> 16 cm, parete a 12 cm)
        sx, _, dx = LaserVeri()
        if letture[-1] >= letture[0] - 1 and 0 < min(sx, dx) < RwdConf.OST_PARETE_CM:
            print(f"Non mi avvicino ({letture[0]} -> {letture[-1]} cm) e c'è una parete di lato a {min(sx, dx)} cm: "
                  f"è la parete, non un ostacolo")
            StaccaDallaParete(sx, dx)               # altrimenti il seguilinea ci torna contro e spinge
            return False
    print("Né ostacolo vicino né rampa: per sicurezza lo tratto come ostacolo")
    return True


def InseguitoreIA():
    global Immagine
    global FestaFatta
    global RottaArena
    global PosMem
    global VelCross
    global VelSl
    Centro_x=112
    center_x=112
    ErrPID=0
    ErrDeriv=0
    ErrIntegr=0
    Err_Last=0
    Direzione=''
    ContDisc = 0
    Disco=False
    UscitaLinea=False
    err_filtr=0
    MargImm=0 
    start_timeSx = 0
    start_timeDx = 0
    i=0
    Incr_Ril=""
    LineePerse = 0         # [FIX 58] ricerche della linea fallite di fila
    pid_reset = True       # [FIX 4] azzera il PID alla prima lettura della linea
    t_pid_prec = time.time()
    # [FIX 22] aspetta il primo fotogramma della camera (evita crash con Immagine = None)
    while Immagine is None:
        time.sleep(0.05)
    Rwd.GetOnLed1()
    Rwd.GetOnLed2()
    PosMem = {}            # [FIX 21] (prima: PosVerde = PosRosso = PosPorta = None)
    global RiferimentoGriglia
    if RiferimentoGriglia is None:
        # [FIX 62] alla partenza il robot è appoggiato dritto sulla piastrella: la sua direzione dice
        # come sono orientate tutte le piastrelle del campo (a multipli di 90 gradi da questa)
        _, _, RiferimentoGriglia = Rwd.GetGyro()
    for i in range(2):
        sensori = Rwd.GetSensori()
        print('distanze', sensori['distanze'], "Posizione", sensori['imu'],"SW", sensori['switch'], "TILT", sensori['tilt'])
        time.sleep(0.2)

    while True:
        start_timeCiclo = time.time()
        #Immagine = WebCam.CamSL.capture_array()
        #cv2.imshow('Linea', Immagine)
        key = cv2.waitKey(1) & 0xFF
        time.sleep(0.01)
        ramo_linea = False     # [FIX 4] diventa True solo se in questo ciclo lavora il PID
        sensori = Rwd.GetSensori()
        log('distanze', sensori['distanze'], "Posizione", sensori['imu'],"SW", sensori['switch'], "TILT", sensori['tilt'])
        _,dFr,_= sensori['distanze']
        # [FIX 62] storico della direzione (ultimi 2 s): dice se il robot sta curvando e da che parte
        StoricoRotta.append((time.time(), sensori['imu'][2]))
        while StoricoRotta and time.time() - StoricoRotta[0][0] > 2.0:
            StoricoRotta.pop(0)
        # [FIX 23] ATTENZIONE AI NOMI: GetSensori()['imu'] restituisce (pitch, roll, heading).
        # Qui la variabile "roll" contiene quindi il BECCHEGGIO (salita/discesa)
        # e "pitch" il ROLLIO (inclinazione laterale). Il codice funziona, ma i nomi sono scambiati.
        roll, pitch,_ = sensori['imu']
        if ControllaAltalena():                       # [FIX 102]
            pid_reset = True
            continue
        ContDisc=0
        if roll > 15:
            print("Dritto Inclinato0000000000000000")
            #Rwd.Dritto(VelSl,0.4)
            #Trasforma immagine tagliando la parte alta
            Crop = MascheraAlta(Immagine)   # [FIX 9]
        else:    
            Crop=Immagine
        cv2.imshow('Linea', Crop)
        '''
        _,tilt = Rwd.GetTilt()
        if tilt== 1 and not (roll >-10 and roll <10 and pitch > -10 and pitch < 10):
            print("tilt in azione")
            Rwd.Sterzo(-VelSl,0)
            time.sleep(0.6)
            Rwd.Stop()
        '''
        if roll >-10 and roll <10 and pitch > -10 and pitch < 10 :
            VelSl = Vel
            VelCross=RwdConf.VelCrs
        # [FIX 3] Prima: VelCross = int(VelCross*Alfa) -> VelCross moltiplicava SE STESSA
        # a ogni ciclo e in salita scendeva a zero (47 -> 14 -> 4 -> 1 -> 0).
        # Ora si parte sempre dal valore di configurazione RwdConf.VelCrs.
        elif roll >10:
            VelSl = int(Vel*RwdConf.AlfaVelSal)
            VelCross = int(RwdConf.VelCrs*RwdConf.AlfaCrosSal)
        elif roll < -10:
            VelSl = int(Vel*RwdConf.AlfaVelDis)
            VelCross = int(RwdConf.VelCrs*RwdConf.AlfaCrosDis)
        else:
            VelSl = int(Vel*RwdConf.AlfaVelDis)
            VelCross = int(RwdConf.VelCrs*RwdConf.AlfaVelDis)
        sensori = Rwd.GetSensori()
        _,dFrGrezzo,_= sensori['distanze']
        # [FIX 87] mediana delle ultime letture: una lettura isolata sotto 15 cm non ferma più il robot
        dFr = Rwd.FrontaleFiltrato()
        if 0 < dFrGrezzo < 15 and not (0 < dFr < 15):
            print(f"Laser frontale: lettura isolata {dFrGrezzo} cm ignorata (mediana {dFr} cm)")
        # [FIX 24] 0 = lettura non valida (sensore che non risponde o dati Arduino
        # persi), NON un ostacolo a 0 cm
        if 0 < dFr < 15:  #Ostacolo presente
            print("POSSIBILE OSTACOLO") 
            roll, _,_ = sensori['imu'] 
            # [FIX 56] prima: laser < 15 cm e robot in piano = ostacolo, sempre. Ma davanti a una rampa il
            # laser frontale (a circa 6 cm da terra) colpisce la salita a 14-15 cm mentre il robot è ancora
            # in piano: il robot faceva il giro dell'ostacolo intorno alla RAMPA. Ora ConfermaOstacolo()
            # avanza piano e decide: si avvicina fino a 8 cm = ostacolo, il robot si inclina = rampa.
            if roll >-9 and roll <9 and ConfermaOstacolo():
                print("OSTACOLO")  
                AggiraOstacolo()                    # [FIX 90] prima OstAutDet(-1): sempre a destra, anche contro una parete
                                  
            else:
                print("Non è un ostacolo (non sono in piano, rampa o laser disturbato): continuo")   # [FIX 87]
                Rwd.Sterzo(VelSl,0)
        else:
            Start_Decisione=time.time()
            if roll > 15: 
                print("Dritto Inclinato0000000000000000")
                #Rwd.Dritto(VelSl,0.4)
                #Trasforma immagine tagliando la parte alta
                Crop = MascheraAlta(Immagine)   # [FIX 9]
            else:    
                Crop=Immagine
            cv2.imshow('Linea', Crop)            
            Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
            #cv2.imshow('Linea', Crop)
            tempo_trascorsoCiclo = time.time()-Start_Decisione
            log("Tempo trascorso decisione: ",tempo_trascorsoCiclo)
            if Incr_Ril=="Sx":
                print ('IA           Incrocio          Sx Sx Sx Sx Sx: ', confid)
                roll, pitch,_ = sensori['imu']
                if roll >-10 and roll <10 and pitch > -10 and pitch < 10 :
                    CrosSx()
                    Crop=Immagine
                    Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
                    if Incr_Ril=="Bi":
                        Rwd.Gira(25,VelCross)      # [FIX 44] prima Gira(10) + 0,2 s che girava ancora: circa 29 gradi
                        print("Correggo per bianco")
                elif roll >10:
                    print("VADO DRITTO POI GIRO")
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(1.3)
                    #Rwd.Stop()
                    CrosSxIncl()
                elif roll < -10:
                    print("INDIETRO DRITTO POI GIRO")
                    Rwd.Sterzo(-VelSl,0)      #Sposta leggermente il robot
                    time.sleep(0.6)
                    #Rwd.Stop()
                    CrosSxIncl()
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(0.3)
                    #Rwd.Stop()
                else: 
                    print("VADO DRITTO POI GIRO")
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(1)
                    #Rwd.Stop()
                    CrosSxIncl()
                    
            elif Incr_Ril=="Di":
                print ('IA-          Discontinuità      Di Di Di Di Di: ', confid) 
                # Verifica se siamo in salita, applico maschera alle prime SogMask righe dell'immagine
                if roll > 15:
                    print("MASCHERA IMMAGINE ALTA")
                    #Rwd.Dritto(VelSl,0.4)
                    #Trasforma immagine tagliando la parte alta
                    Crop = MascheraAlta(Immagine)   # [FIX 9]
                else:    
                    Crop=Immagine
                if roll > 15:
                    print("Non sono in piano, Probabile non sia Ingresso") 
                    Rwd.Sterzo(VelSl,0)    
                else:    
                    cv2.imshow('Linea', Crop)                
                    # [FIX 62] YOLO vede "Di" appena la fine della linea entra nell'immagine, quando il robot può
                    # essere ancora in curva (interruzione subito dopo una curva o una curva a U). La V23 si
                    # fermava lì, si allineava e partiva: dopo una U attraversava storta o di lato e finiva sulla
                    # fila vicina (campo contorto: LoP in tutte le gare). Ora prima segue il nastro piano fino
                    # alla sua fine (SeguiFinoAlVuoto), poi attraversa il vuoto dritto (AttraversaVuoto).
                    if RwdConf.GAP_SEGUI_FINO_AL_VUOTO:
                        SeguiFinoAlVuoto()
                        if not AttraversaVuoto():
                            RecuperaLinea()
                    else:
                        AttraversaInterruzione()
                    # [FIX 57] Prima: una sterzata secca di 0,25 s e poi 0,9 s dritto ALLA CIECA, nella
                    # direzione in cui il robot si trovava. Se l'interruzione viene subito dopo una curva
                    # il robot è ancora storto: attraversava il vuoto di sbieco e sull'altopiano cadeva dal
                    # bordo (nel simulatore 14 cadute in 6 gare). Ora si allinea alla linea e poi va dritto
                    # tenendo la direzione col giroscopio finché ritrova la linea.
            elif Incr_Ril=="Dx":
                print ('IA            Incrocio         Dx Dx Dx Dx Dx:  ', confid)
                roll, _,_ = sensori['imu']
                if roll >-10 and roll <10 and pitch > -10 and pitch < 10 :
                    CrosDx()
                    Crop=Immagine
                    Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
                    if Incr_Ril=="Bi":
                        Rwd.Gira(-25,VelCross)      # [FIX 44] prima Gira(-10) + 0,2 s che girava ancora: circa 29 gradi
                        print("Correggo per bianco")
                elif roll >10:
                    print("VADO DRITTO POI GIRO")
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(1.3)
                    #Rwd.Stop()
                    CrosDxIncl()
                elif roll < -10:
                    print("INDIETRO DRITTO POI GIRO")
                    Rwd.Sterzo(-VelSl,0)      #Sposta leggermente il robot
                    time.sleep(0.7)
                    #Rwd.Stop()
                    CrosDxIncl()
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(0.4)
                    #Rwd.Stop()

                else:
                    print("VADO DRITTO POI GIRO")
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(1)
                    #Rwd.Stop()
                    CrosDxIncl()

            elif Incr_Ril=="Fr" and ConfermaDietrofront():    # [FIX 79] se non è confermato: seguilinea (else)
                print ('IA        Incrocio             Fr Fr Fr Fr Fr : ', confid)
                roll, pitch,_ = sensori['imu']
                if roll >-10 and roll <10 and pitch > -10 and pitch < 10 :
                    CrosFF() 
                elif roll >10:
                    print("VADO DRITTO POI GIRO")
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(1.6)
                    #Rwd.Stop()
                    CrosFF()
                elif roll < -10:
                    print("INDIETRO DRITTO POI GIRO")
                    Rwd.Sterzo(-VelSl,0)      #Sposta leggermente il robot
                    time.sleep(0.7)
                    #Rwd.Stop()
                    CrosFF()
                elif pitch >10:
                    print("GIRO Orario")
                    CrosFFIncl(Verso=1)                
                elif pitch < -10:
                    print("GIRO Antiorario")
                    CrosFFIncl(Verso=-1)
                else:
                    print("VADO DRITTO POI GIRO")
                    Rwd.Sterzo(VelSl,0)      #Sposta leggermente il robot
                    time.sleep(1)
                    #Rwd.Stop()
                    CrosFF() 
            elif Incr_Ril=="In" and time.time() >= ArgentoIgnoraFino:   # [FIX 81] se no: seguilinea (else)
                global UltimoArgento
                UltimoArgento = time.time()                 # [FIX 75]
                # [FIX 33] INGRESSO NELL'ARENA: prima si CONFERMA la striscia argento da fermi,
                # poi si entra dritti tenendo la direzione con il giroscopio.
                # Prima: il robot avanzava 0,5 s e SOLO DOPO ricontrollava la striscia. La camera
                # della linea (alta 8,3 cm) vede pochi centimetri davanti: dopo l'avanzamento la
                # striscia era già sotto il robot, la conferma falliva ("Inclinazione Arena"),
                # il robot riprendeva a seguire il bianco ed entrava storto contro la barriera.
                # Inoltre le correzioni Sterzo(±35) per 0,05 s erano troppo brevi per fare effetto.
                # [FIX 46] tutti i controlli e l'ingresso sono ora nella funzione TrovaIngressoArena
                if UscitaArenaFatta and getattr(RwdConf, "ARENA_UNA_VOLTA", False):
                    # [FIX 66] SCATOLA NERA 23/10, secondo 596: uscito dall'arena, dopo un'interruzione il
                    # robot ha ritrovato la linea girando di 60 gradi, è tornato indietro ed è RIENTRATO
                    # nell'arena. L'arena c'è una volta sola: se la striscia argento è confermata vuol dire
                    # che sto tornando indietro sulla linea, quindi faccio dietrofront.
                    if TrovaIngressoArena(roll, entra=False):
                        global UltimoDietrofront
                        # [FIX 98] Scatola nera 05/11 ore 15:12, secondi 470-493: qui il robot restava fermo 23 s
                        # perché Gira(180) non girava (FIX 97). Ora il dietrofront si fa una volta; se entro
                        # DIETROFRONT_PAUSA_S rivede l'argento, la striscia non va presa sul serio: la scarta e
                        # continua (dopo l'arena il robot non entra comunque più: ARENA_UNA_VOLTA).
                        if time.time() - UltimoDietrofront > getattr(RwdConf, "DIETROFRONT_PAUSA_S", 30):
                            UltimoDietrofront = time.time()
                            print("Striscia argento ma l'arena è già fatta: sto tornando indietro, faccio dietrofront")
                            Rwd.Gira(180, VelArena)
                            Rwd.Stop()
                        else:
                            ScartaArgento("argento di nuovo dopo il dietrofront: lo ignoro")
                            Rwd.Sterzo(VelSl, 0)
                            time.sleep(0.3)
                        pid_reset = True
                        continue
                    Rwd.Sterzo(VelSl,0)
                    continue
                if TrovaIngressoArena(roll):
                    UscitaLinea=True
                    break
                Rwd.Sterzo(VelSl,0)
            elif Incr_Ril=="Ro":
                Rwd.Stop()
                time.sleep(0.5)
                Rwd.Sterzo(VelSl,0)
                time.sleep(0.1)
                Rwd.Stop()
                time.sleep(0.1)
                #Immagine = WebCam.CamSL.capture_array()

                if roll > 15:
                    print("Maschero immagine")
                    #Rwd.Dritto(VelSl,0.4)
                    #Trasforma immagine tagliando la parte alta
                    Crop = MascheraAlta(Immagine)   # [FIX 9]
                else:    
                    Crop=Immagine
                cv2.imshow('Linea', Crop)

                Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
                if Incr_Ril=="Ro":
                    print ('IA     STOP                 RO RO RO RO RO: ', confid)
                    if roll >-10 and roll <10 and pitch > -10 and pitch < 10 :
                        time.sleep(0.5)
                        Rwd.Stop() 
                    else:
                        Rwd.Sterzo(VelSl,60)
                        time.sleep(0.5)
                        Rwd.Stop()
                    if RwdConf.FESTA and not FestaFatta:   # [FIX 32] una sola festa per run
                        Festeggia()
                        FestaFatta = True
                    if UscitaArenaFatta and getattr(RwdConf, "FERMO_DOPO_ARRIVO", True):
                        # [FIX 95] GARA FINITA: arena fatta e linea rossa, il robot resta fermo finché si spegne lo switch.
                        # Scatola nera 05/11 (V33): dopo la festa (286,7 s) ripartiva, scendeva di nuovo la rampa e
                        # rivedeva l'ingresso dell'arena 16 volte ("faccio dietrofront").
                        # prima avanzo ancora un poco: il robot si fermava a pochi cm PRIMA della linea rossa (Shuri, batteria
                        # del 03/11: "si ferma 1 cm prima della piastrella d'arrivo") e così la supera con le ruote
                        Rwd.Dritto(VelSl, getattr(RwdConf, "AVANZA_ARRIVO_S", 1.0), ruota=False)
                        Rwd.Stop()
                        print("GARA FINITA: resto fermo sulla linea rossa (spegnete lo switch)")
                        while Rwd.GetSwitch()['sw_sof']:
                            Rwd.Stop()
                            time.sleep(0.2)
                    time.sleep(10)
                    #Rwd.Gira(180, VelCross)#
                    #time.sleep(0.6)#
                    

            elif Incr_Ril=="Bi" and RwdConf.RECUPERO_SICURO:
                # [FIX 58] LINEA PERSA, ricerca SICURA. Prima: girava di 25° da una parte e di 50°
                # dall'altra e, appena vedeva del nero, andava avanti alla cieca; se non vedeva niente
                # arretrava 0,7 s e ripartiva. Vicino a un bordo rialzato andare avanti senza linea
                # vuol dire cadere. Ora il robot cerca la linea SENZA andare mai avanti: prima ruota sul
                # posto (ventaglio di angoli col giroscopio), poi torna indietro sulla strada già fatta.
                print ('IA         BIANCO               Bi Bi Bi Bi Bi: ')
                # [FIX 75] Linea finita poco dopo aver visto l'argento: quasi sicuramente sono all'ingresso
                # dell'arena e la conferma da fermo non è riuscita (a metà curva la striscia era sul bordo
                # dell'immagine). Prima il robot cercava la linea, tornava indietro e prendeva una linea
                # fuori sequenza (simulatore V27, pista lunga). Ora riprova l'ingresso.
                if (UltimoArgento and time.time() - UltimoArgento < RwdConf.ARGENTO_RECENTE_S
                        and not UscitaArenaFatta and IngressoDopoArgento()):
                    UscitaLinea = True
                    break
                if RecuperaLinea():
                    LineePerse = 0
                else:
                    LineePerse += 1
                    if LineePerse >= 2:
                        print("Linea non ritrovata: resto fermo, il capitano può chiamare la LoP")
                        Rwd.Stop()
                        time.sleep(1.0)
            elif Incr_Ril=="Bi":
                print ('IA         BIANCO               Bi Bi Bi Bi Bi: ') 
                # Cerchiamo la linea a destra
                Rwd.Gira(-25,VelCross) 
                FotogrammaNuovo()          # [FIX 44] immagine scattata a robot fermo
                #time.sleep(0.45)
                #Rwd.Stop()
                #Immagine = WebCam.CamSL.capture_array()

                if roll > 15:
                    print("Mashero immagine")
                    #Rwd.Dritto(VelSl,0.4)
                    #Trasforma immagine tagliando la parte alta
                    Crop = MascheraAlta(Immagine)   # [FIX 9]
                else:    
                    Crop=Immagine
                cv2.imshow('Linea', Crop)

                Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
                
                if Incr_Ril != "No" and Incr_Ril != "Bi":  # Trovata linea a Destra
                    Rwd.Sterzo(VelSl,0)
                    time.sleep(0.1)
                else:                       # Non trovata a destra Guarda a sinistra
                    Rwd.Gira(50,VelCross)
                    FotogrammaNuovo()      # [FIX 44] immagine scattata a robot fermo
                    #time.sleep(0.85)
                    #Rwd.Stop()
                    #Immagine = WebCam.CamSL.capture_array()
                    # Carico immagine per cercare riga a sinistra
                    if roll > 15:
                        print("Maschero immagine")
                        #Rwd.Dritto(VelSl,0.4)
                        #Trasforma immagine tagliando la parte alta
                        Crop = MascheraAlta(Immagine)   # [FIX 9]
                    else:    
                        Crop=Immagine
                    cv2.imshow('Linea', Crop)

                    Incr_Ril, confid, Centro_x, Img= WebCam.VerificaVerde(Crop)
                    
                    if Incr_Ril != "No" and Incr_Ril != "Bi":  # Riga trovata a sinistra
                        Rwd.Sterzo(VelSl,0)
                        time.sleep(0.2)
                    else:                       # Non trovata mi riposiziono centralmente
                        Rwd.Gira(-25,VelCross)
                        #time.sleep(0.50)
                        #Rwd.Stop()
                        #time.sleep(0.2)
                        Rwd.Sterzo(-VelSl,0)    # Torno indietro per ripartire
                        time.sleep(0.7)
                        #Rwd.Stop() 

            else:       #elif Incr_Ril=="Ln":  # Non abbiamo casi particolari ma la linea
                if roll > 15:
                    print("Maschero immagine")
                    Crop = MascheraAlta(Immagine)   # [FIX 9]
                else:    
                    Crop=Immagine
                cv2.imshow('Linea', Crop)
                # [FIX 59] incrocio senza verde: attraversarlo dritto invece di seguire il baricentro
                if RwdConf.INCROCI_DRITTI and IncrocioDritto(Crop):
                    pid_reset = True
                    continue
                # Determino l'errore di posizionamento rispetto alla linea ideale
                Disco,err_Corr=WebCam.CalcolaErrore(Crop)
                if Disco == "BusterDx":
                    BoosterDx()
                elif Disco == "BusterSx":
                    BoosterSx()
                else:
                    # ===== PID SEGUILINEA =====  [FIX 4]
                    ramo_linea = True
                    adesso = time.time()
                    if pid_reset:
                        # Dopo un incrocio, un ostacolo o all'avvio si riparte da zero:
                        # niente integrale "vecchio" e niente derivata falsata
                        ErrIntegr = 0
                        Err_Last = err_Corr
                        t_pid_prec = adesso
                        pid_reset = False
                    DeltaT = max(adesso - t_pid_prec, 0.01)   # tempo VERO tra due calcoli del PID
                    t_pid_prec = adesso
                    ErrIntegr += err_Corr*DeltaT
                    # anti-windup: l'integrale non può crescere all'infinito
                    ErrIntegr = max(-RwdConf.IntegrMax, min(RwdConf.IntegrMax, ErrIntegr))
                    # derivata = (errore ATTUALE - errore PRECEDENTE) / dt
                    # (prima era al contrario e il termine D amplificava le oscillazioni)
                    ErrDeriv = (err_Corr - Err_Last) / DeltaT
                    err_PID = (Kp * err_Corr) + (Ki * ErrIntegr) + (Kd * ErrDeriv)
                    Err_Last=err_Corr
                    log('IA         Seguilinea           Ln Ln Ln Ln Ln: ', err_PID)
                    # Kp NON va moltiplicato di nuovo qui (prima: err_PID*Kp)
                    if roll >-10 and roll <10 and pitch > -10 and pitch < 10 :
                        Rwd.Sterzo(VelSl,err_PID)
                    elif roll >10:
                        Rwd.Sterzo(VelSl,err_PID*RwdConf.AlfaCorSal)
                    elif roll < -10:
                        Rwd.Sterzo(VelSl,err_PID*RwdConf.AlfaCorDis)
                    else:
                        Rwd.Sterzo(VelSl,err_PID*RwdConf.AlfaCorDis)

        if not ramo_linea:
            pid_reset = True   # [FIX 4] in questo ciclo c'è stata una manovra: al prossimo tratto di linea il PID riparte pulito
        tempo_trascorsoCiclo = time.time()-start_timeCiclo
        log("Oggi: ", datetime.now(),"Tempo Ciclo: ", tempo_trascorsoCiclo)
        sensori = Rwd.GetSensori()
        _,SwSf = sensori['switch'] 
        if (cv2.waitKey(1) & 0xFF == ord('q')) or not SwSf or UscitaLinea:
            Rwd.GetOffLed1()
            break
        time.sleep(0.01)
    Rwd.GetOffLed1()
    Rwd.GetOffLed2()  
  
def AccostaTriangolo():
    # [FIX 54] Si avvicina PIANO al bordo del triangolo tenendo la direzione col giroscopio, finché il laser
    # frontale legge SCARICO_CM oppure finché il robot non avanza più (sta già toccando il bordo).
    # Così la pallina, aprendo la pinza, cade DENTRO il triangolo.
    _, _, rotta = Rwd.GetGyro()
    for tentativo in range(3):
        t0 = time.time()
        storico = []
        fermo = False
        while time.time() - t0 < 2.5:
            _, dFr, _ = LaserVeri()
            if dFr <= RwdConf.SCARICO_CM:
                break
            storico = (storico + [dFr])[-6:]
            if len(storico) == 6 and dFr < 12 and max(storico) - min(storico) < 1:
                fermo = True                           # da 0,6 s non mi avvicino: sono contro qualcosa
                break
            Rwd.Dritto(int(VelArena * 0.5), 0.1, heading_ref=rotta)
        Rwd.Stop()
        # [FIX 77] Fermo ancora lontano dal triangolo con un fianco attaccato al muro: è lo spigolo del robot
        # contro il muro, non il triangolo (simulatore V27: muso a 10 cm, pallina caduta 4 cm fuori). Arretro,
        # mi stacco di qualche cm dal muro e riprovo.
        dSx, dFr, dDx = LaserVeri()
        if dFr <= RwdConf.SCARICO_CM + 3 or min(dSx, dDx) > 8 or tentativo == 2:
            break
        via = 1 if dSx < dDx else -1                   # muro a sinistra: mi stacco verso destra
        print(f"Triangolo a {dFr} cm ma un fianco tocca il muro: mi stacco e riprovo")
        Rwd.Dritto(-int(VelArena * 0.5), 0.6, heading_ref=rotta)
        Rwd.RuotaVerso((rotta + via * 25) % 360, tolleranza=3, timeout=2.0)
        Rwd.Dritto(int(VelArena * 0.5), 0.5, heading_ref=(rotta + via * 25) % 360)
        Rwd.RuotaVerso(rotta, tolleranza=3, timeout=2.0)
        Rwd.Stop()
    _, dFr, _ = LaserVeri()
    print(f"Accostato al triangolo: muso a {dFr} cm dal bordo")
    if RwdConf.RETRO_SCARICO_S > 0:
        Rwd.Sterzo(-VelArena, 0)
        time.sleep(RwdConf.RETRO_SCARICO_S)
        Rwd.Stop()


def ScaricaPalla(TipoAzione): #Tipo Azione corrisponde a triVerde(1) TriRosso(2) Uscita(3)
    global PosMem
    max_area = 0
    center_x = 112
    center_y = 112
    tipo = "" 
    frame = None
    ContaGiro = 0
    i=0
    print("Cerco Elemento", TipoAzione)
    GiraVersoMemoria(TipoAzione)   # [FIX 21]
    time.sleep(0.1)    
    centrature = 0                 # [FIX 83] quante volte mi sono già girato verso un triangolo visto di lato
    while True:
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']
        if cv2.waitKey(1) == ord('q') or not SwSf:
            break
        #Rwd.Pinza(110)
        ImmArena = WebCam.CamAr.capture_array()
        array = cv2.resize(ImmArena, (224, 224), interpolation=cv2.INTER_AREA)
        cv2.imshow('Linea', array)
        cv2.waitKey(1)
        closest_box, area, centro_x, centro_y, tipo, frame = WebCam.CercaPortaTri(array, TipoAzione)
        cv2.imshow('Linea', frame)
        if (cv2.waitKey(1) & 0xFF == ord('q')): 
            break
        sensori = Rwd.GetSensori()
        _,dFr,_=sensori['distanze'] 
        if closest_box:
            MemorizzaPosizione(tipo)   # [FIX 21]
                
        if closest_box and tipo == TipoAzione: # Trovato triangolo verde o rosso    
            print("Distanza triangolo: ", dFr)
            # [FIX 83] SCARICO SOLO CON IL TRIANGOLO DAVANTI. Shuri, pista lunga seme 2, secondo 267: dopo la presa
            # il robot si è girato verso la direzione ricordata del triangolo, lo ha visto sul BORDO destro
            # dell'immagine e il laser frontale leggeva 16 cm... ma era il MURO accanto al triangolo. Sotto i 17 cm
            # il codice scaricava subito (anche nel ramo che stava ancora sterzando verso il triangolo): pallina
            # lasciata 5 cm fuori, contata come salvata, poi la nera portata prima delle due vive (-1032 punti).
            # Ora: se il muro è vicino e il triangolo non è al centro dell'immagine, arretro e mi giro verso il
            # triangolo (angolo dai pixel, come per le palline: FIX 30) prima di scaricare.
            gradi_tri = (centro_x - center_x) * RwdConf.GradiPerPixelArena
            if dFr < 17 and abs(centro_x - center_x) > RwdConf.SCARICO_CENTRO_PX and centrature < 4:
                centrature += 1
                print(f"Triangolo di lato ({gradi_tri:+.0f} gradi) e muro a {dFr} cm: arretro e mi giro verso il triangolo")
                Rwd.Stop()
                Rwd.Dritto(-int(VelArena * 0.7), RwdConf.SCARICO_ARRETRA_S)
                Rwd.Stop()
                _, _, hd_ora = Rwd.GetGyro()
                Rwd.RuotaVerso((hd_ora + gradi_tri) % 360, tolleranza=3, timeout=3.0)
                Rwd.Stop()
                continue
            if dFr > 14:
                if centro_x < (center_x-10):
                    Rwd.Sterzo(VelArena, -60)
                    #time.sleep(0.05)
                    #Rwd.Stop()
                
                elif centro_x > (center_x+10):
                    Rwd.Sterzo(VelArena, 60)
                    #time.sleep(0.05)
                    #Rwd.Stop()
                    
                else:
                    Rwd.Sterzo(VelArena, 0)
                    #time.sleep(0.5)
                    #Rwd.Stop()
                
            else:
                Rwd.Stop()
                print("Scarico Palla")
                Rwd.Sterzo(VelArena,0)
                time.sleep(1.3) 
                Rwd.Stop()
                ImmArena = WebCam.CamAr.capture_array()
                array = cv2.resize(ImmArena, (224, 224), interpolation=cv2.INTER_AREA)
                cv2.imshow('Linea', array)
                cv2.waitKey(1)
                closest_box, area, centro_x, centro_y, tipo, frame = WebCam.CercaPortaTri(array, TipoAzione)
                cv2.imshow('Linea', frame)
                dSx,dFr,dDx=Rwd.Distanze()
                if dSx < 18:                    #or centro_x: > (center_x+10):
                    Rwd.Sterzo(-VelArena,0)
                    time.sleep(0.6)
                    Rwd.Gira(20,VelArena)
                    Rwd.Sterzo(VelArena,-60)
                    time.sleep(1.5) 
                    Rwd.Stop() 
                elif dDx < 18:                  # or centro_x < (center_x-10):
                    Rwd.Sterzo(-VelArena,0)
                    time.sleep(0.6)
                    Rwd.Gira(-20,VelArena)
                    Rwd.Sterzo(VelArena,60)
                    time.sleep(1.5) 
                    Rwd.Stop() 
            sensori = Rwd.GetSensori()
            _,dFr,_=sensori['distanze']
            if dFr < 17:        
                print("Scarico Palla")
                AccostaTriangolo()             # [FIX 54] prima: avanti 1,3 s a tempo e indietro 0,4 s
                SvuotaPinza()
                time.sleep(1)
                
                
                #Rwd.Stop()
                break
        else:
            ContaGiro +=1
            i +=1
            print("Nessun Triangolo Verde.")

            if ContaGiro < 10*i:
                Rwd.Sterzo(int(VelArena), 80) 
                if i>3:
                    i=1
            else:
                sensori = Rwd.GetSensori()
                _,dFr,_=sensori['distanze']    
                if dFr > 20:
                    Rwd.Sterzo(VelArena,0)
                    time.sleep(0.5)
                    #Rwd.Stop()
                else: 
                    Rwd.Sterzo(-VelArena,0)
                    time.sleep(0.4)
                ContaGiro=0
        #cv2.imshow('Linea', frame)
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']           
        if cv2.waitKey(1) == ord('q') or not SwSf:
            break
    
    cv2.destroyAllWindows()

def TrovaUscitaIA(TipoAzione): #Tipo Azione corrisponde a triVerde(1) TriRosso(2) Uscita(3)
    global PosMem
    global Immagine
    max_area = 0
    center_x = 112
    center_y = 112
    tipo = "" 
    frame = None
    ContaGiro = 0
    CordYArrivo=110
    Rwd.GetOnLed1()
    Rwd.GetOnLed2()      
    i=0
    print("Cerco Elemento", TipoAzione)
    GiraVersoMemoria(TipoAzione)   # [FIX 21]
    time.sleep(0.1)    
    Verso=1
    storico = []    # [FIX 26] (tempo, direzione) degli ultimi 2 secondi di ricerca
    rotta_porta = None  # [FIX 34] direzione assoluta della porta (dal giroscopio + posizione nell'immagine)
    blocchi = 0                 # [FIX 38] quante volte si è incastrato
    perimetro_fatto = False     # [FIX 38] il giro dei muri si fa una volta sola (poi decide di nuovo la camera)
    t_inizio = time.time()
    while True:
        # [FIX 39] Se la camera linea vede la striscia NERA sotto il muso, siamo sull'uscita: si esce.
        # Prima il robot ci passava vicino o sopra mentre cercava la porta con la camera dell'arena
        # e non se ne accorgeva.
        cosa, angolo = GuardaPavimento(apertura_davanti=False)
        if cosa == "nero":
            EsciSullaStriscia(angolo)
            break
        # [FIX 38] se con la camera non trova l'uscita entro TempoMaxRicercaPorta, giro dei muri
        if not perimetro_fatto and time.time() - t_inizio > RwdConf.TempoMaxRicercaPorta:
            perimetro_fatto = True
            print("Uscita non trovata con la camera: cerco lungo i muri")
            if PerimetroUscita(Verso, davanti_al_muro=False):
                break
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']
        if cv2.waitKey(1) == ord('q') or not SwSf:
            break
        #Rwd.Pinza(110)
        ImmArena = WebCam.CamAr.capture_array()
        array = cv2.resize(ImmArena, (224, 224), interpolation=cv2.INTER_AREA)
        cv2.imshow('Linea', array)
        cv2.waitKey(1)
        closest_box, area, centro_x, centro_y, tipo, frame = WebCam.CercaPortaTri(array, TipoAzione)
        cv2.imshow('Linea', frame)
        if (cv2.waitKey(1) & 0xFF == ord('q')): 
            break
        sensori = Rwd.GetSensori()
        _,dFr,_=sensori['distanze'] 
        if closest_box:
            MemorizzaPosizione(tipo)   # [FIX 21]
                
        if closest_box and tipo == TipoAzione: # Trovato triangolo verde o rosso    
            print("Posizione Altezza Porta: ", centro_y)
            if centro_y < CordYArrivo:
                _, _, hd = Rwd.GetGyro()     # [FIX 34] da lontano la porta è tutta nell'immagine:
                rotta_porta = (hd + (centro_x - center_x) * RwdConf.GradiPerPixelArena) % 360   # direzione affidabile
                if centro_x < (center_x-10):
                    Rwd.Sterzo(VelArena, -45)
                    #time.sleep(0.05)
                    #Rwd.Stop()
                
                elif centro_x > (center_x+10):
                    Rwd.Sterzo(VelArena, 45)
                    #time.sleep(0.05)
                    #Rwd.Stop()
                    
                else:
                    Rwd.Sterzo(VelArena, 0)
                    #time.sleep(0.5)
                    #Rwd.Stop()
                
            else:
                # [FIX 34] ARRIVATO ALLA PORTA (sostituisce la vecchia manovra a tempo e il FIX 25)
                Rwd.Stop()
                print("Arrivato alla porta")
                # [FIX 48] TOLTO il controllo "è l'ingresso?" fatto qui con VerificaVerde sull'immagine della
                # camera ARENA: è il modello della camera LINEA, addestrato su altre immagini, e poteva dire
                # "argento" anche davanti all'uscita facendo partire il giro dei muri. Ora l'argento lo
                # controlla la camera linea, sul pavimento, mentre il robot si avvicina alla porta
                # (AvvicinatiAllaPorta) e mentre esce (EsciControllando). Se è l'ingresso, EsciDallaPorta
                # restituisce "ingresso" e il robot fa quello che faceva prima: giro dei muri.
                if True:
                    if rotta_porta is None:
                        _, _, hd = Rwd.GetGyro()
                        rotta_porta = (hd + (centro_x - center_x) * RwdConf.GradiPerPixelArena) % 360
                    esito = EsciDallaPorta(rotta_porta, TipoAzione)
                    if esito == "ingresso":
                        # [FIX 46] uscendo ha visto la striscia ARGENTO: era l'ingresso ed è già tornato dentro
                        _, _, hd = Rwd.GetGyro()
                        PorteScartate.append(hd)
                        PosMem.pop(TipoAzione, None)
                        print("Era l'INGRESSO: cerco l'uscita lungo i muri")
                        if PerimetroUscita(Verso, davanti_al_muro=True):
                            break
                        rotta_porta = None
                        continue
                    if esito:
                        break
                    print("Uscita non riuscita: riprendo la ricerca della porta")
                    rotta_porta = None
        else:    
            ContaGiro +=1
            i +=1
            print("Nessun Triangolo Verde.")

            # [FIX 26] ANTI-BLOCCO: il robot sta cercando ruotando, ma se in 1,5 s la direzione
            # cambia meno di 6 gradi vuol dire che è incastrato (per esempio contro uno stipite,
            # dove il laser frontale centrale "vede" libero attraverso l'apertura).
            _,_,hd = Rwd.GetGyro()
            adesso = time.time()
            storico.append((adesso, hd))
            storico = [s for s in storico if adesso - s[0] < 2.0]
            if adesso - storico[0][0] > 1.5 and max(abs(angle_difference(s[1], hd)) for s in storico) < 6:
                print("BLOCCATO: torno indietro e giro")
                blocchi += 1                                  # [FIX 38]
                if blocchi >= 2 and not perimetro_fatto:
                    perimetro_fatto = True
                    print("Bloccato due volte: cerco l'uscita lungo i muri")
                    if PerimetroUscita(Verso, davanti_al_muro=True):
                        break
                Rwd.Sterzo(-VelArena,0)
                time.sleep(0.8)
                Rwd.Stop()
                Rwd.Gira(Verso*70, VelArena)
                storico = []
                ContaGiro = 0
                continue

            if ContaGiro < 10*i:
                Rwd.Sterzo(int(VelArena)*0.7, Verso*70) 
                if i%3==0:
                    i=1
                    
            else:
                sensori = Rwd.GetSensori()
                _,dFr,_=LaserVeri()       # [FIX 48] laser a 0 = spazio libero, non muro
                if dFr > 20:
                    if i%2==0:
                        Rwd.Sterzo(VelArena,0)
                        time.sleep(1.3)
                        #Rwd.Stop()
                    else:
                        Rwd.Sterzo(VelArena,0)
                        time.sleep(0.7)
                        #Rwd.Stop()
                        
                else: 
                    Rwd.Sterzo(-VelArena,0)
                    time.sleep(0.7)
                ContaGiro=0
            #if i%2==0:
            #    Verso=-1*Verso                
        #cv2.imshow('Linea', frame)
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']           
        if cv2.waitKey(1) == ord('q') or not SwSf:
            break
    Rwd.GetOffLed1()
    Rwd.GetOffLed2()    
    cv2.destroyAllWindows()



def TrovaUscita(): # NON USATA dal main (sostituita da TrovaUscitaIA)
    global PosMem
    ParSX = False
    ParDX = False
    max_area = 0
    center_x = 112
    center_y = 112
    tipo = "" 
    frame = None
    ContaGiro = 0
    TipoAzione=0
    #Rwd.Sterzo(-VelArena,0)
    #time.sleep(0.4) 
    #Rwd.Gira(180,VelArena)
    #time.sleep(1)
    Rwd.Sterzo(VelArena,0)
    time.sleep(2) 
    Rwd.Stop() 
    Rwd.GetOnLed1()
    Rwd.GetOnLed2()
    print("Cerco Elemento", TipoAzione)
    trovato = False
    i=0
    Verso=1
    GiraVersoMemoria(0)   # [FIX 21]
    while True:
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']
        if cv2.waitKey(1) == ord('q') or not SwSf:
            break
        #Rwd.Pinza(110)
        Immagine = WebCam.CamAr.capture_array()
        array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
        cv2.imshow('Linea', array)
        cv2.waitKey(1)
        closest_box, area, centro_x, centro_y, tipo, frame = WebCam.CercaPortaTri(Immagine, TipoAzione)
            ######
        sensori = Rwd.GetSensori()
        _,dFr,_=sensori['distanze']    
        if closest_box and tipo== TipoAzione: # Trovato triangolo verde/TriRosso    
            if centro_y < 80:
                print("CentroY: ",centro_y)
                if centro_x < (center_x - 10): #30
                    Rwd.Sterzo(VelArena, -50)#35
                    #time.sleep(0.05)
                    #Rwd.Stop()
                    
                elif centro_x > (center_x + 10):
                    Rwd.Sterzo(VelArena, 50)
                    #time.sleep(0.15)
                    #Rwd.Stop()
                else:
                    Rwd.Sterzo(VelArena*0.7, 0)
                '''
                else:
                    cv2.imshow('YOLOv8 Detection', frame)
                    print("Area ",area, centro_x, centro_y)
                    #Rwd.Stop()
                    #time.sleep(0.2)
                    if area < 11000:
                        Rwd.Sterzo(VelArena*0.7, 0) 
                        #time.sleep()
                '''
            else:
                Rwd.Stop()
                Rwd.Sterzo(VelArena,0)      # Mi avvicino alla porta per far vedere meglio la striscia
                time.sleep(0.5)
                Rwd.Stop()
                
                print("Simo davanti alla porta VERIFICA")
                ImmArena = WebCam.CamAr.capture_array()
                array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
                cv2.imshow('Linea', array)
                cv2.waitKey(1)
                closest_box, area, centro_x, centro_y, tipo, frame = WebCam.VerificaUscita(ImmArena)
                cv2.imshow('Linea', frame)
                time.sleep(1)
                if closest_box and tipo == 0:
                    trovato = True
                    print("TROVATO")
                    Rwd.Stop()
                    time.sleep(0.5)
                    dSx,dFr,dDx=Rwd.Distanze()
                    if centro_x < (center_x - 15): 
                        print("Centro verso sinistra")
                        Rwd.Sterzo(VelArena, -100)
                        time.sleep(0.15)
                        Rwd.Stop()
                    elif centro_x > (center_x + 15):
                        print("Centro verso destra")
                        Rwd.Sterzo(VelArena, 100)
                        time.sleep(0.15)
                        Rwd.Stop()
                    Rwd.Sterzo(VelArena, 0)
                    time.sleep(0.4)    
                    '''
                    if dSx < 25:
                        print("Mi allontano da sinistra")
                        ParSX = True
                        #Rwd.Sterzo(-VelArena,0)
                        #time.sleep(0.8)
                        #Rwd.Gira(35,VelArena)
                        Rwd.Sterzo(VelArena,30)
                        time.sleep(1) 
                        Rwd.Stop() 
                        Rwd.Gira(-40,VelArena)
                        Rwd.Sterzo(VelArena,0)
                        time.sleep(0.4) 
                        Rwd.Stop() 

                    elif dDx < 25:
                        print("Mi allontano da destra")
                        ParDX = True
                        #Rwd.Sterzo(-VelArena,0)
                        #time.sleep(0.8)
                        #Rwd.Gira(-35,VelArena)
                        Rwd.Sterzo(VelArena,-30)
                        time.sleep(1) 
                        Rwd.Stop() 
                        Rwd.Gira(40,VelArena)
                        Rwd.Sterzo(VelArena,0)
                        time.sleep(0.4) 
                        Rwd.Stop() 
                    '''
                    # Ricarico l'immagine dalla nuova posizione e verifico tipo e posizione    
                    ImmArena = WebCam.CamAr.capture_array()
                    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
                    cv2.imshow('Linea', array)
                    cv2.waitKey(1)
                    closest_box, area, centro_x, centro_y, tipo, frame = WebCam.VerificaUscita(ImmArena)
                    cv2.imshow('Linea', frame)
                    time.sleep(1)
                    if closest_box and tipo == 0:
                        trovato = True
                        print("TROVATO")
                        Rwd.Stop()
                        if centro_x < (center_x - 15): 
                            print("Centro verso sinistra")
                            Rwd.Sterzo(VelArena, -100)
                            time.sleep(0.20)
                            Rwd.Stop()
                        elif centro_x > (center_x + 15):
                            print("Centro verso destra")
                            Rwd.Sterzo(VelArena, 100)
                            time.sleep(0.20)
                            Rwd.Stop()
                        '''
                        sensori = Rwd.GetSensori()
                        _,dFr,_=sensori['distanze']
                        if dFr < 20:
                            if ParDX:
                                Rwd.Gira(45, VelSl)
                                Rwd.Stop()
                            elif ParSX:
                                Rwd.Gira(-45, VelSl)
                                Rwd.Stop()
                        Rwd.Sterzo(VelArena, 0)
                        time.sleep(1.5)
                        Rwd.Stop()
                        '''
                        Rwd.Sterzo(VelArena, 0)
                        time.sleep(0.5)
                        Rwd.Stop()
                        break
                else:
                    print("NON E' L'USCITA")
                    Rwd.Sterzo(-VelArena, 0)
                    time.sleep(1.9)
                    Rwd.Gira(30,VelArena)      # [FIX 44] prima Gira(25) + 0,1 s che girava ancora
                    time.sleep(0.1) 
                    Verso=-1*Verso
                    trovato = False
        else:
            ContaGiro +=1
            i +=1
            print("Nessuna Porta Trovata.")

            if ContaGiro < 40*i:
                if Verso >0:
                    Rwd.Sterzo(int(VelArena), 75) 
                else:
                    Rwd.Sterzo(int(VelArena), -75)
                if i>5:
                    i=1
            else:
                sensori = Rwd.GetSensori()
                _,dFr,_=sensori['distanze']    
                if dFr > 24:
                    y = 0
                    while dFr > 20 and y < (0.4*i):
                        sensori = Rwd.GetSensori()
                        _,dFr,_=sensori['distanze']    
                        Rwd.Sterzo(VelArena,0)
                        time.sleep(0.1)
                        y = y + 0.1
                    #Rwd.Stop()
                else: 
                    Rwd.Sterzo(-VelArena,0) 
                    time.sleep(2.2)
                ContaGiro=0
                if i%2 ==0:
                    Verso =-1*Verso
                print("Direzione",Verso)
        cv2.imshow('Linea', frame)
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']
        if cv2.waitKey(1) == ord('q') or not SwSf:
            break
    
    cv2.destroyAllWindows()

def GiraInArena(gradi):
    # [FIX 74] Rotazione grande in arena (dopo aver lasciato la pallina, nella ricerca). Prima Rwd.Gira: se uno
    # spigolo toccava il muro o il triangolo il robot spingeva per 8 s (timeout) e poi ripartiva da lì
    # (simulatore V27: robot a 5 cm dal muro dopo lo scarico, rotazione bloccata, poi 150 s senza trovare la
    # pallina successiva). Ora: un po' indietro per avere spazio, rotazione ad anello chiuso; se il giroscopio
    # dice che è bloccata, ancora indietro e si riprova.
    _, _, hd = Rwd.GetGyro()
    obiettivo = (hd + gradi) % 360
    Rwd.Dritto(-int(VelArena * 0.7), 0.4, heading_ref=hd)
    Rwd.Stop()
    for tentativo in range(3):
        esito = Rwd.RuotaVerso(obiettivo, VelArena, tolleranza=5, timeout=6.0)
        if esito is True:
            return True
        print("Rotazione in arena bloccata (giroscopio): arretro e riprovo")
        _, _, hd = Rwd.GetGyro()
        Rwd.Dritto(-int(VelArena * 0.7), 0.6, heading_ref=hd)
        Rwd.Stop()
    return False


def ArenaAI():  
    global PrAng
    global ArenaCompleta
    global Arg
    global Nera
    max_area = 0
    center_x = 112
    center_y = 112
    tipo = "" 
    frame = None
    contatore= 0
    area=1500
    print("AVVIO ARENA")
    Rwd.Stop()
    WebCam.AutoregolaCam(WebCam.CamAr)
    time.sleep(0.5)
    Posiz=Rwd.GetGyro()
    # Visualizza i valori letti
    Rwd.GetOnLed1()
    Rwd.GetOnLed2()    
    sensori = Rwd.GetSensori()
    _,SwSf=sensori['switch']
    # Verifica la posizione d'ingresso se uno dei sensori laterali percepisce un oggetto si piega
    dSx,dFr,dDx=Rwd.Distanze()
    print(dSx,dFr,dDx)
    time.sleep(1)
    Verso=1
    if dSx < 22 :
        print("Piega a Sinistra")
        #Rwd.Sterzo(VelArena,0)             
        #time.sleep(0.6)
        Rwd.Gira(40,VelArena)      # [FIX 44] prima Gira(3) + 0,5 s che girava ancora: circa 40 gradi
        Verso=1
        Rwd.Stop()
        
    elif dDx < 22:
        print("Piega a Destra")
        #Rwd.Sterzo(VelArena,0)             
        #time.sleep(0.6)
        Rwd.Gira(-40,VelArena)     # [FIX 44] prima Gira(-3) + 0,5 s che girava ancora: circa 40 gradi
        Verso=-1
        Rwd.Stop()
    if dFr < 35:
        print("Fronte Occupato correggo")
        if dSx > dDx:
            Rwd.Gira(-45,VelArena)     # [FIX 44] prima Gira(-9) + 0,5 s che girava ancora: circa 45 gradi
            Verso=-1
            Rwd.Stop()
        else:
            Rwd.Gira(45,VelArena)      # [FIX 44] prima Gira(9) + 0,5 s che girava ancora: circa 45 gradi
            Verso=1
            Rwd.Stop()            
        Rwd.Sterzo(VelArena,0)             
        time.sleep(1.2) #1
        Rwd.Stop()
    else:
        print("Fronte Libero")
        if dSx > dDx:
            Verso=-1
            Rwd.Stop()
        else:
            Verso=1
            Rwd.Stop()
    #else:    
    #    Rwd.Sterzo(VelArena,0)             
    #    time.sleep(0.5)
    Rwd.Stop()
    Rwd.Sterzo(VelArena,0)             
    time.sleep(1.2) #1
    Rwd.Stop()
    Rwd.Sterzo(-VelArena,0)          
    time.sleep(0.4)
    Rwd.Stop()
    #Verifico posizione entrata e fisso rotazione ricerca oraria o antioraria    
    dSx,dFr,dDx=Rwd.Distanze()
    print(dSx,dFr,dDx) 
    if dSx > dDx:
        print("Robot a destra - Rotazione antioraria")
        Verso=-1
    else:
        print("Robot a destra - Rotazione oraria")
        Verso=1 
        
    Rwd.Stop()
    time.sleep(2)
    
    ContaGiro=0
    i = 0
    passi_ricerca = 0          # [FIX 76] passi della ricerca a scatti
     
    Rwd.Sterzo(VelArena,0)
    time.sleep(1.5) 
    Rwd.Stop() 
    while True:
        ImmArena = WebCam.CamAr.capture_array()
        array = cv2.resize(ImmArena, (224, 224), interpolation=cv2.INTER_AREA)
        cv2.imshow('Linea', array)
        cv2.waitKey(1)
        if Arg < 2:
            TipoPalla=0
        else:
            TipoPalla=1
        closest_box, area, centro_x, centro_y, tipo, frame = WebCam.PallinaNuova(array, TipoPalla)
        cv2.imshow('Linea', frame)
        cv2.waitKey(1)
            ######
        if closest_box and tipo == TipoPalla:
            passi_ricerca = 0                        # [FIX 76]
            if area < 5500:
                if centro_x < (center_x-10):
                    Rwd.Sterzo(VelArena, -50)
                    #time.sleep(0.05)
                    #Rwd.Stop()
                
                elif centro_x > (center_x+10):
                    Rwd.Sterzo(VelArena, 50)
                    #time.sleep(0.05)
                    #Rwd.Stop()
                    
                else:
                    Rwd.Sterzo(VelArena, 0)
                    #time.sleep(0.5)
                    #Rwd.Stop()
                
            else:
                Rwd.Stop()
                
                ImmArena = WebCam.CamAr.capture_array()
                array = cv2.resize(ImmArena, (224, 224), interpolation=cv2.INTER_AREA)
                cv2.imshow('Linea', array)
                cv2.waitKey(1)
                closest_box, area, centro_x, centro_y, tipo, frame = WebCam.PallinaNuova(array, TipoPalla)
                cv2.imshow('Linea', frame)
                cv2.waitKey(1)           
                # [FIX 30] CORREZIONE FINALE PROPORZIONALE.
                # Prima: se la pallina era a più di 15 pixel dal centro, il robot girava SEMPRE
                # per 0,3 s a piena potenza (25-39 gradi!), anche quando servivano 3-4 gradi.
                # Da vicino 15 pixel sono circa 1 cm: la correzione scattava per niente, la pallina
                # finiva 8-13 cm di lato e la pinza si chiudeva a vuoto (nel simulatore: 7 prese
                # mancate su 7 dopo questa correzione, 0 mancate senza).
                # Inoltre, se nella seconda foto la pallina non si vedeva, centro_x valeva 0 e il
                # robot girava a sinistra "alla cieca".
                # Ora: si gira solo dell'angolo che serve, misurato con il giroscopio.
                if closest_box and tipo == TipoPalla:
                    gradi = (centro_x - center_x) * RwdConf.GradiPerPixelArena
                    if abs(gradi) >= 3:
                        print(f"Correggo di {gradi:.0f} gradi verso la pallina")
                        # [FIX 72] prima Rwd.Gira: si fermava a 3 gradi dall'obiettivo ma il robot continuava a
                        # ruotare (scatola nera 26/10: "correggo di -19" -> girato di 26, "+17" -> 24, "+4" -> 8,
                        # "-4" -> 11): la pinza si chiudeva di lato alla pallina. Ora rotazione ad anello chiuso
                        # che aspetta il giroscopio e arriva entro 1,5 gradi.
                        _, _, hd_ora = Rwd.GetGyro()
                        Rwd.RuotaVerso((hd_ora + gradi) % 360, tolleranza=1.5, timeout=3.0)
                        Rwd.Stop()
                else:
                    print("Pallina non vista nella seconda foto: nessuna correzione")
                if area > 9000:
                    Rwd.Sterzo(-VelArena, 0)
                    time.sleep(0.2)
                    Rwd.Stop()
                print("Carica Pallina")
                Rwd.Sterzo(-VelArena, 0)
                time.sleep(0.5)
                Rwd.Stop()
                AbbassaPinza()
                time.sleep(0.4)
                Rwd.Sterzo(VelArena*0.7, 0)
                time.sleep(1.1) #1.85
                Rwd.Stop()
                ChiudiPinza()
                time.sleep(0.5)
                Rwd.Sterzo(-VelArena, 0)
                time.sleep(0.4)
                Rwd.Stop()
                CaricaPalla()
                time.sleep(1)
                print("TIPO: ", tipo)
                print(contatore)

                sensori = Rwd.GetSensori()
                PallaPresa,_=sensori['switch']
                
                print("Pallina", PallaPresa)

                if PallaPresa:
                    print("PALLINA CATTURATA",PallaPresa)
                    if TipoPalla == 0:
                        print("Scarica Argento")
                        Arg+=1
                        ScaricaPalla(3)
                        GiraInArena(Verso*160)         # [FIX 74] prima Rwd.Gira(Verso*160) (vedi GiraInArena)
                        print("Fermo")
                        Rwd.Stop()
                    else:
                        print("Scarica Nero")
                        Nera+=1
                        ScaricaPalla(2)
                        GiraInArena(Verso*(-160))      # [FIX 74] prima Rwd.Gira(Verso*(-160))
                        Rwd.Sterzo(-VelArena,0)
                        time.sleep(0.5) 
                        Rwd.Sterzo(VelArena,0)
                        time.sleep(1.8)
                        Rwd.Stop()
                        GiraInArena(Verso*(-120))      # [FIX 74]
                        print("Fermo")
                        Rwd.Stop()
                else:
                    print("PALLINA NON CATTURATA",PallaPresa)
                    ApriPinza()
                    time.sleep(0.5)
                if Arg >= 2 and Nera >= 1:
                    ArenaCompleta=True
                    break
                else:
                    ArenaCompleta=False
        else:
            ContaGiro +=1
            contatore = 0
            i+=1
            print("Nessuna sfera trovata.")
            if getattr(RwdConf, "RICERCA_A_SCATTI", False):
                # [FIX 76] RICERCA A SCATTI. Prima il robot ruotava di continuo per 1-3 s, poi andava avanti
                # 1,7 s e girava di 100 gradi: non faceva mai un giro completo e poteva restare in una parte
                # dell'arena (scatola nera 23/10: 100 s per trovare la seconda pallina; simulatore V27: 150 s
                # senza trovarla, LoP). Ora: scatti di RICERCA_PASSO_GRADI gradi, fermo a ogni scatto così la
                # camera arena vede un'immagine ferma; dopo un giro completo si sposta (avanti se c'è spazio,
                # altrimenti gira) e ricomincia.
                passi_ricerca += 1
                if passi_ricerca <= int(360 / RwdConf.RICERCA_PASSO_GRADI):
                    _, _, hd = Rwd.GetGyro()
                    Rwd.RuotaVerso((hd + Verso * RwdConf.RICERCA_PASSO_GRADI) % 360, VelArena, tolleranza=4, timeout=2.0)
                    Rwd.Stop()
                    time.sleep(0.15)                 # immagine ferma per la camera arena
                else:
                    passi_ricerca = 0
                    _, dFr, _ = LaserVeri()
                    if dFr > 40:
                        print("Giro completo senza palline: mi sposto più avanti")
                        _, _, hd = Rwd.GetGyro()
                        Rwd.Dritto(VelArena, min(2.5, (dFr - 25) / RwdConf.VelocitaArenaCmS), heading_ref=hd)
                        Rwd.Stop()
                    else:
                        print("Giro completo senza palline e muro vicino: mi giro")
                        GiraInArena(Verso * 120)
                    Verso = -Verso
            elif ContaGiro < 10*i:
                Rwd.Sterzo(int(VelArena*0.7), Verso*80)
                if i >3:
                    i=1
            else:
                _,dFr,_ = Rwd.Distanze()
                if dFr > 20:
                    Rwd.Sterzo(VelArena,0)
                    time.sleep(1.7)
                    Rwd.Sterzo(-VelArena,0)
                    time.sleep(0.4)
                    Rwd.Stop()
                elif dFr <15 : 
                    Rwd.Sterzo(-VelArena,0)
                    time.sleep(0.7)
                    Rwd.Stop()
                GiraInArena(Verso*(-100))      # [FIX 74]
                Verso=(-1)*Verso
                ContaGiro=0
            #time.sleep(0.2)
            #Rwd.Stop()
            
        if frame is None:
            cv2.imshow('Linea', array)
        else:
            cv2.imshow('Linea', frame)
        sensori = Rwd.GetSensori()
        _,SwSf=sensori['switch']            
        if cv2.waitKey(1) == ord('q') or not SwSf or ArenaCompleta:
            break
    Rwd.GetOffLed1()
    Rwd.GetOffLed2()
    #TrovaUscita(2)
    
    #cv2.destroyAllWindows()      

Rwd.GetOffLed1()
Rwd.GetOffLed2()

Rwd.Braccio(40)
time.sleep(1)

Rwd.Pinza(160)       
time.sleep(1)
'''
Rwd.Sterzo(30,0)
time.sleep(0.5)
Rwd.Stop()
Rwd.Sterzo(30,0)
time.sleep(0.5)
Rwd.Stop()
Rwd.Sterzo(30,0)
time.sleep(0.5)
Rwd.Stop()
'''
'''
AbbassaPinza()
time.sleep(1)
Rwd.Sterzo(25,0)
time.sleep(0.8)
Rwd.Stop()
ChiudiPinza()
time.sleep(1)
CaricaPalla()
time.sleep(2)
SvuotaPinza()
time.sleep(2)
print("FATTO")
'''

# [FIX 112] Autotaratura della camera linea UNA VOLTA all'avvio.
# Sul robot: LED accesi durante l'assestamento e il calcolo Otsu. Nel simulatore
# si usa il valore di configurazione, così le prove restano confrontabili con V45.
def _taratura_camera_linea_avvio():
    # [FIX 114] la riserva è la soglia di taratura_nero.json (TaraNero.py) se c'è, altrimenti ViennaDataConf
    soglia_riserva = int(getattr(WebCam, "SOGLIA_NERO_RISERVA", getattr(RwdConf, "SOGLIA_NERO", 110)))
    if "finto_hw" in _sys.modules:
        WebCam.ImpostaSogliaNero(soglia_riserva)
        Monitor.evento(f"SIMULATORE: autotaratura camera linea saltata; soglia {soglia_riserva} da ViennaDataConf", "sistema")
        return
    # [FIX 114] INTERRUTTORE (feature flag): con CAM_LINEA_AUTOTARATURA = False si torna alla taratura della
    # V45/V47 (AutoregolaCam, esposizione automatica, soglia da taratura_nero.json o ViennaDataConf).
    if not getattr(RwdConf, "CAM_LINEA_AUTOTARATURA", True):
        WebCam.AutoregolaCam(WebCam.CamSL)
        Monitor.evento(f"CAMERA LINEA: autotaratura spenta (CAM_LINEA_AUTOTARATURA = False); soglia {WebCam.SOGLIA_NERO}; "
                       f"fuoco {getattr(WebCam, '_INFO_FUOCO_LINEA', {}).get('modo', 'non noto')}; "
                       f"{getattr(RwdConf, 'CAM_LINEA_FPS', 20)} FPS", "sistema")
        return

    Rwd.Stop()
    try:
        Rwd.GetOnLed1()
        Rwd.GetOnLed2()
        print("[FIX 112] Camera linea: LED accesi, assesto esposizione e calcolo Otsu...")
        esito = WebCam.AutotaraturaLinea(WebCam.CamSL)
    except Exception as e:
        WebCam.ImpostaSogliaNero(soglia_riserva)
        esito = {"soglia": soglia_riserva, "fonte": "ViennaDataConf.SOGLIA_NERO",
                 "otsu_ok": False, "soglia_otsu": None, "motivo": str(e),
                 "misure": None, "esposizione": {"bloccata": False},
                 "fuoco": {}, "fps": int(getattr(RwdConf, "CAM_LINEA_FPS", 20))}
    finally:
        # I LED tornano nello stato di attesa; durante la gara vengono riaccesi
        # dalle funzioni del seguilinea come nella versione precedente.
        try:
            Rwd.GetOffLed1()
            Rwd.GetOffLed2()
        except Exception as e:
            print("[FIX 112] Avviso: non riesco a spegnere i LED dopo la taratura:", e)

    m = esito.get("misure") or {}
    exp = esito.get("esposizione") or {}
    fuoco = esito.get("fuoco") or {}
    dettagli = (f"soglia {esito.get('soglia')} ({esito.get('fonte')}); "
                f"Otsu={esito.get('soglia_otsu')}; "
                f"esposizione {'bloccata' if exp.get('bloccata') else 'NON bloccata'} "
                f"({exp.get('exposure_us')} us, gain {exp.get('gain')}); "
                f"fuoco {fuoco.get('modo', 'non noto')}; {esito.get('fps')} FPS")
    if esito.get("otsu_ok"):
        extra = (f"; nero V={m.get('nero_tipico')} (max97 {m.get('nero_max_97')}), "
                 f"bianco V={m.get('bianco_tipico')} (min3 {m.get('bianco_min_3')})")
        avvisi = []
        if not exp.get("bloccata"):
            avvisi.append("esposizione non bloccata")
        if fuoco.get("avviso"):
            avvisi.append(fuoco["avviso"])
        Monitor.evento("CAMERA LINEA: " + dettagli + extra +
                       ("; ATTENZIONE: " + "; ".join(avvisi) if avvisi else ""),
                       "errore" if avvisi else "sistema")
    else:
        Monitor.evento("ATTENZIONE CAMERA LINEA: " + dettagli +
                       f"; uso il valore di riserva. Motivo: {esito.get('motivo')}", "errore")

_taratura_camera_linea_avvio()
# [FIX 114] il controllo VISTA della V47 (FIX 113) ora parte DOPO la taratura della camera linea, così usa la
# soglia del nero vera della gara (nella V47 partiva prima, dentro Monitor.avvia).
Monitor.controlli_avvio()
# La camera arena mantiene la sua regolazione durante le fasi in arena.
#WebCam.AutoregolaCam(WebCam.CamAr)

Rwd.Stop()

SwPrec = False      # [FIX 7] stato dello switch al ciclo precedente

# [FIX 6] try/finally: QUALSIASI errore (o Ctrl+C) passa dal blocco "finally"
# che ferma i motori. Prima, se Python andava in errore, la PCA9685 continuava
# a mandare l'ultimo comando e i servo a rotazione continua NON si fermavano.
try:
    while True:
        Arena = WebCam.CamAr.capture_array()
        ImmCol=Immagine
        sensori = Rwd.GetSensori()
        log(sensori['switch'])
        _,SwSf=sensori['switch']

        # [FIX 7] Switch appena acceso (fronte di salita) = nuova run
        if SwSf and not SwPrec and RwdConf.AZZERA_CONTATORI_A_OGNI_AVVIO:
            NuovaRun()
        SwPrec = SwSf

        if SwSf:
            print("AZIONE")
            
            time.sleep(0.3)
            sensori = Rwd.GetSensori()
            _,SwSf=sensori['switch']
            
            if  not SwSf:
                time.sleep(0.1)
            else:
                Protetto(InseguitoreIA)                 # [FIX 100]
            time.sleep(0.3)    
            sensori = Rwd.GetSensori()
            _,SwSf=sensori['switch']
            
            if  not SwSf:
                time.sleep(0.1)
            else:
                Protetto(ArenaAI)                       # [FIX 100]
            time.sleep(0.3)
            sensori = Rwd.GetSensori()
            _,SwSf=sensori['switch']
            
            if  not SwSf: #or OutArena
                time.sleep(0.1)
            
            else:
                Protetto(TrovaUscitaArena)  # [FIX 46] prima TrovaUscitaIA(0). [FIX 100] protetta
            time.sleep(0.3)
            # Lo switch potrebbe essere stato spento e riacceso durante la run
            _,SwPrec = Rwd.GetSensori()['switch']


        else:
            Rwd.Stop()
            #sensori = Rwd.GetSensori()
            Posiz=Rwd.GetGyro()
            Swi=Rwd.GetSwitch()
            # Visualizza i valori letti
            print("PAUSA......")
            print("Distanze:", Rwd.Distanze())
            print("IMU:", Rwd.GetGyro())
            print("Switch:", Rwd.GetSwitch())
            time.sleep(0.5)



        cv2.imshow('Arena', Arena)
        cv2.imshow('Linea', Immagine)
        if (cv2.waitKey(1) & 0xFF == ord('q')): 
            break
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Interrotto da tastiera (Ctrl+C)")

finally:
    # [FIX 6] Arresto sicuro: viene eseguito SEMPRE, anche dopo un errore
    print("ARRESTO SICURO DEL ROBOT")
    try:
        Rwd.Stop()
        Rwd.SpegniPWM()
    except Exception as e:
        print("Errore durante lo stop motori:", e)
    try:
        WebCam.CamAr.stop()
        WebCam.CamSL.stop()
    except Exception:
        pass
    Rwd.GetOffLed1()
    Rwd.GetOffLed2()
    Rwd.StopLetture()
    Monitor.chiudi()        # [FIX 37] chiude la scatola nera e rimette a posto il terminale
    time.sleep(1)    
    cv2.destroyAllWindows()
