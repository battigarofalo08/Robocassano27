from picamera2 import Picamera2, Preview
from libcamera import controls, Transform
from threading import Thread
import cv2
import numpy as np
import time
import warnings
from ultralytics import YOLO
import torch
from ultralytics.utils import LOGGER
from datetime import datetime
import ViennaDataConf as RwdConf
import os
import queue
import shutil

LOGGER.handlers.clear()

torch.set_num_threads(4)
torch.set_num_interop_threads(1)



warnings.simplefilter("ignore")

# =========================================================
# [FIX 1] MODELLI YOLO CARICATI UNA SOLA VOLTA
# Prima ogni funzione eseguiva YOLO(...) a ogni chiamata, cioè a ogni
# fotogramma: il modello veniva riletto dal disco ogni volta.
# Ora vengono caricati qui, all'avvio, e le funzioni li riusano.
# =========================================================
print("Caricamento modelli YOLO...")
MOD_CROSS  = YOLO("best_ncnn_model_Cross3", task="detect")      # incroci / linea
MOD_PALLE  = YOLO("best_ncnn_model_PalCol3", task="detect")     # palline
MOD_TRIAN  = YOLO("best_ncnn_model_TrianFull3", task="detect")  # triangoli / porta
MOD_EXIT   = YOLO("best_ncnn_model_Exit3", task="detect")       # uscita / ingresso
print("Modelli YOLO caricati")


# =========================================================
# [FIX 31] FOTO DEL PERCORSO PER IL RIADDESTRAMENTO
# - Le foto si salvano in CARTELLA_FOTO (/home/pi/OneDrive/Incroci/) con il nome
#   <classe>Cross<data_ora>.jpg, come prima: es. SxCross20261008_153012_123456.jpg
# - Il nome NON contiene ":" né spazi. Il codice originale usava datetime.now() nel nome
#   ("...Cross2026-05-12 10:15:33.123456.jpg"): OneDrive non accetta ":" nei nomi dei file,
#   quindi quelle foto possono restare sul Raspberry senza mai arrivare su OneDrive.
# - La scrittura su SD la fa un thread separato: il ciclo del robot non aspetta mai il disco.
# - Si salva al massimo una foto ogni FOTO_INTERVALLO secondi per classe, ma subito quando
#   la classe cambia (gli incroci, i verdi, le interruzioni sono le foto più preziose).
# =========================================================
_coda_foto = queue.Queue(maxsize=40)    # se la SD è lenta le foto in più si scartano
_ultima_foto = {}                       # classe -> istante dell'ultima foto salvata
_ultima_classe = [None]
_foto_salvate = [0]


def _scrittore_foto():
    while True:
        nome, img = _coda_foto.get()
        try:
            if _foto_salvate[0] % 50 == 0:      # ogni 50 foto controlla lo spazio libero
                libero_mb = shutil.disk_usage(RwdConf.CARTELLA_FOTO).free / 1e6
                if libero_mb < RwdConf.FOTO_SPAZIO_MINIMO_MB:
                    print(f"[FOTO] SD quasi piena ({libero_mb:.0f} MB liberi): salvataggio sospeso")
                    RwdConf.SALVA_FOTO = False
                    continue
            if cv2.imwrite(nome, img):
                _foto_salvate[0] += 1
            else:
                print("[FOTO] Impossibile scrivere", nome)
        except Exception as e:
            print("[FOTO] Errore salvataggio:", e)


if RwdConf.SALVA_FOTO:
    try:
        os.makedirs(RwdConf.CARTELLA_FOTO, exist_ok=True)
        Thread(target=_scrittore_foto, daemon=True).start()
        print("[FOTO] Salvataggio attivo in", RwdConf.CARTELLA_FOTO)
    except Exception as e:
        print("[FOTO] Cartella non disponibile, salvataggio disattivato:", e)
        RwdConf.SALVA_FOTO = False


def SalvaFoto(etichetta, img):
    if not RwdConf.SALVA_FOTO or img is None:
        return
    adesso = time.time()
    cambiata = etichetta != _ultima_classe[0]
    if not cambiata and adesso - _ultima_foto.get(etichetta, 0) < RwdConf.FOTO_INTERVALLO:
        return
    _ultima_foto[etichetta] = adesso
    _ultima_classe[0] = etichetta
    if img.ndim == 3 and img.shape[2] == 4:            # la camera dà BGRA: il jpg vuole BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    ora = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    try:
        _coda_foto.put_nowait((f"{RwdConf.CARTELLA_FOTO}{etichetta}Cross{ora}.jpg", img.copy()))
    except queue.Full:
        pass

IdCamAr =1
IdCamSL =0
    
Immagine=None

RisX=440 #320    #320
RisY=260 #240    #240
CentroX = int(RisX/2)
CentroY = int(RisY/2)

ErrPre=0


NumFoto=0

# Range verde
lower_green = np.array([40, 55, 55])
upper_green = np.array([80, 255, 255])

# Range giallo
lower_yellow = np.array([26, 120, 120])
upper_yellow = np.array([32, 255, 255]) 

# Range blu
lower_blu = np.array([105, 150, 50])
upper_blu = np.array([125, 255, 255])

# Range rosso
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

border_thickness = 30

# Range Nero
# [FIX 45] la soglia di luminosità del nero (prima fissa a 80) si regola in ViennaDataConf.SOGLIA_NERO
# oppure con TaraNero.py, che la salva in taratura_nero.json (questo file vale più di ViennaDataConf).
SOGLIA_NERO = RwdConf.SOGLIA_NERO
# [FIX 112] Ripiego immutabile: se Otsu non è affidabile si torna sempre al
# valore scritto in ViennaDataConf.py, non a una soglia Otsu precedente.
SOGLIA_NERO_RISERVA = int(getattr(RwdConf, "SOGLIA_NERO", 110))
try:
    import json as _json
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "taratura_nero.json")) as _f:
        _tara = _json.load(_f)
    SOGLIA_NERO = int(_tara["soglia_nero"])
    print(f"Soglia del nero da taratura_nero.json: {SOGLIA_NERO} (tarata il {_tara.get('data', '?')})")
except FileNotFoundError:
    print(f"Soglia del nero da ViennaDataConf: {SOGLIA_NERO}")
except Exception as _e:
    print("taratura_nero.json non leggibile, uso ViennaDataConf:", _e)
lower_black = np.array([0, 0, 0])
upper_black = np.array([180, 150, SOGLIA_NERO])   # prima: [180, 150, 80]

#175, 120

AreaSigBkVe=10
AreaSigBk=600 #1500
AreaSigVerde=4000
AreaSigRed=15000

# [FIX 112] Fuoco fisso della camera linea. LensPosition è espresso in diottrie
# (1 / distanza in metri). Si usa il range che dichiara la camera: se il fuoco
# richiesto non è raggiungibile, si imposta il limite più vicino e lo si segnala.
def _imposta_fuoco_linea(Cam):
    if not bool(getattr(RwdConf, "CAM_LINEA_FUOCO_MANUALE", True)):
        try:
            Cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except Exception:
            pass
        return {"modo": "continuo", "avviso": "fuoco manuale disattivato"}
    try:
        distanza_cm = float(getattr(RwdConf, "CAM_LINEA_FUOCO_CM", 8.3))
        if distanza_cm <= 0:
            raise ValueError("CAM_LINEA_FUOCO_CM deve essere positivo")
        richiesto = 100.0 / distanza_cm
        impostato = richiesto
        limiti = getattr(Cam, "camera_controls", {}).get("LensPosition")
        if limiti and len(limiti) >= 2:
            minimo, massimo = float(limiti[0]), float(limiti[1])
            impostato = max(minimo, min(massimo, richiesto))
        Cam.set_controls({"AfMode": controls.AfModeEnum.Manual,
                          "LensPosition": float(impostato)})
        avviso = None
        if abs(impostato - richiesto) > 0.01:
            avviso = (f"fuoco richiesto {richiesto:.2f} D non disponibile; "
                      f"impostato {impostato:.2f} D")
        return {"modo": "manuale", "richiesto_D": round(richiesto, 2),
                "impostato_D": round(impostato, 2), "avviso": avviso}
    except Exception as e:
        # Se il modulo non espone LensPosition, non si blocca l'avvio del robot.
        try:
            Cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except Exception:
            pass
        return {"modo": "continuo (ripiego)", "avviso": str(e)}

_INFO_FUOCO_LINEA = {"modo": "non impostato", "avviso": None}

##### CAM VERTICALE PER ULTIMA STANZA ##############
CamSL = Picamera2(IdCamSL)
print('Carica camera Zero')
vidconfig = CamSL.create_preview_configuration(main={"format": 'XRGB8888', "size": (RisX,RisY)})
#vidconfig["transform"] = Transform(hflip=1, vflip=1) 
vidconfig["size"] = (RisX,RisY)
CamSL.configure(vidconfig)
CamSL.start()
print('avvio camera Zero')
# [FIX 112] LED accesi durante la taratura; AE resta attiva finché non viene
# bloccata da AutotaraturaLinea. Il fuoco manuale evita che la lente "pompi".
with CamSL.controls as ctrl:
    ctrl.AwbEnable = True
    ctrl.AeEnable = True
    ctrl.FrameRate = max(5, min(30, int(getattr(RwdConf, "CAM_LINEA_FPS", 20))))
_INFO_FUOCO_LINEA = _imposta_fuoco_linea(CamSL)
print(f"[FIX 112] Camera linea: {_INFO_FUOCO_LINEA['modo']}, "
      f"{getattr(RwdConf, 'CAM_LINEA_FPS', 20)} FPS" +
      (f"; ATTENZIONE: {_INFO_FUOCO_LINEA['avviso']}" if _INFO_FUOCO_LINEA.get("avviso") else ""))
#DatiCam= CamSL.capture_metadata()


##### CAM ORIZZONTALE PER ULTIMA STANZA ##############

RisXAr=440  #440
RisYAr=260

CamAr = Picamera2(IdCamAr)
vidconfig = CamAr.create_preview_configuration(main={"format": 'XRGB8888', "size": (RisXAr,RisYAr)})
vidconfig["transform"] = Transform(hflip=1, vflip=1)
vidconfig["size"] = (RisXAr,RisYAr)
CamAr.configure(vidconfig)
CamAr.start()
#CamAr.set_controls({"AfMode": controls.AfModeEnum.Continuous})
with CamAr.controls as ctrl:     # [FIX 5] vedi sopra
    ctrl.ExposureTime = 10000#1000#10000 
    #ctrl.AnalogueGain = 0.9 
    #ctrl.Brightness = 0.05 #-0.15
    #ctrl.ExposureValue = 1.5
    ctrl.Contrast = 2  
    #ctrl.AwbEnable = True
    #ctrl.AfMode = 2        # [FIX 5] prima era "AfMode: 2" e quindi non faceva nulla
    #ctrl.AeEnable = True
    #ctrl.HdrEnable = True
    ctrl.FrameRate = 10
#DatiCam= CamAr.capture_metadata() 

'''
#def VaiAlverde():
    WebCam.AutoregolaCam(WebCam.CamAr)
    TrovVer=False
    TrovVer2=False
    time.sleep(0.5)
    #Rwd.Sterzo(-Vel,0)+
    #time.sleep(0.6)
    Rwd.Stop()
    Rwd.Gira(85, Vel)
    Immagine = WebCam.CamAr.capture_array()
    cv2.imshow('Linea', Immagine)
    #Trovver, (cX1,cY1), TrovVer2, (CX2, CY2)=CercaBlocchicol (Immagine, 'verde', AreaSigCol=100)
    if TrovVer:
        Rwd.Sterzo(Vel,0)
        time.sleep(1.5) #tempo necessario per arrivare davanti alla porta d'ingresso
        Rwd.Gira(-85, Vel)
        Rwd.Sterzo(Vel,0)
        time.sleep(2.5) #tempo necessario per arrivare dentro la stanza
    else:
        Rwd.Gira(-185, Vel)
        Rwd.Sterzo (Vel,0)
        time.sleep(1.5) #tempo necessario per arrivare davanti alla porta d'ingresso
        Rwd.Gira(85, Vel)
        Rwd.Sterzo (Vel,0)
        time.sleep(2.5) #tempo necessario per arrivare dentro la stanza
    cv2.imshow('Linea', Immagine)
    sensori = Rwd.GetSensori()
    SwSf = sensori['switch']
    #if cv2.waitKey(1) == ord('q') or not SwSf or ArenaCompleta:

'''
def CercaBlocchiCol(frame, colore, AreaSigCol=100): # colore : 'verde', 'rosso', 'nero', 'giallo' , 'blu'
    '''
    Converte il frame in HSV, rileva e disegna i due blocchi più grandi di un colore specifico.

    Parametri:
        frame  : immagine BGR dalla webcam
        colore : 'verde', 'rosso', 'nero'

    Ritorna:
        (presente1, cx1, cy1, area1),
        (presente2, cx2, cy2, area2),
        frame_disegnato
    '''
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    if colore == "nero":
        mask = cv2.inRange(hsv, lower_black, upper_black)
        colore_contorno = (100, 100, 0)  # bianco per visibilità

    elif colore == "verde":
        mask = cv2.inRange(hsv, lower_green, upper_green)
        colore_contorno = (255, 255, 0) 

    elif colore == "giallo":
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        colore_contorno = (255, 255, 0) 
    
    elif colore == "blu":
        mask = cv2.inRange(hsv, lower_blu, upper_blu)
        colore_contorno = (255, 255, 0) 

    elif colore == "rosso":
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        colore_contorno = (0, 0, 255)

    else:
        raise ValueError("Colore non supportato.")

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    risultati = []

    for i in range(2):
        if i < len(contours):
            cnt = contours[i]
            area = cv2.contourArea(cnt)
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = -1, -1
            
            '''
            if area > AreaSigCol:
                # Disegno
                cv2.drawContours(frame, [cnt], -1, colore_contorno, 2)
                cv2.circle(frame, (cx, cy), 5, colore_contorno, -1)
                cv2.putText(frame, f"A:{int(area)}", (cx + 10, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colore_contorno, 2)
            '''
            risultati.append((True, cx, cy, int(area)))
        else:
            risultati.append((False, -1, -1, 0))
            
    (presente1, cX1, cY1, area1) = risultati[0]
    (presente2, cX2, cY2, area2) = risultati[1]
    Trov1 = presente1 and area1 > AreaSigCol
    Trov2 = presente2 and area2 > AreaSigCol
    
    return Trov1, (cX1,cY1), Trov2, (cX2, cY2)


def LeggiCross(Img):
    Lv=80  #70
    Lt=15
    cv2.destroyAllWindows()
    TipoAzione=""
    angle=0
    print("Leggo Verde")
    Img_ruotata=Img
    cv2.imshow('Linea', Img)
    key = cv2.waitKey(1) & 0xFF
    time.sleep(0.01)
    (h, w) = Img.shape[:2]
    # Converte l'immagine nello spazio colore HSV
    hsv = cv2.cvtColor(Img, cv2.COLOR_BGR2HSV)
    # Applica la maschera per isolare il verde
    mask = cv2.inRange(hsv, lower_green, upper_green)
    #cv2.imshow("verde", mask) ####
    # Trova i contorni della maschera
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        #raise ValueError("Nessuna zona verde trovata nell'immagine.")
        TipoAzione="None"
    # Seleziona il contorno più grande
    else:
        largest_contour = max(contours, key=cv2.contourArea)
        # Calcola il rettangolo orientato (bounding box rotato)
        rect = cv2.minAreaRect(largest_contour)
        box = cv2.boxPoints(rect)
        centro , _ ,_ = rect
        box = np.intp(box)     # [FIX 20] np.int0 non esiste più in NumPy 2
        # Disegna il rettangolo sull'immagine originale (opzionale, per debug)
        Img_with_box = cv2.drawContours(Img.copy(), [box], 0, (255, 255, 255), 2)
        cv2.imshow('Linea', Img_with_box)
        key = cv2.waitKey(1) & 0xFF
        time.sleep(0.01)
        # L'inclinazione rispetto all'asse x è data dall'angolo del rettangolo
        angle=rect[-1] 
        if angle>0:
            angle = -(90-rect[-1])  
        else:
            angle = -rect[-1]    
        #print("Trovato Verde inclinato di: ", angle)
        #time.sleep(0.01)
        Img_ruotata = Img 
        TrovVer1,(cVe1X,cVe1Y),TrovVer2,(cVe2X,cVe2Y)=CercaBlocchiCol(Img_ruotata,"verde",AreaSigVerde*0.6)
        cv2.imshow('Linea', Img_ruotata)
        key = cv2.waitKey(1) & 0xFF
        time.sleep(0.01)
        if TrovVer1 and TrovVer2 and (cVe1Y > (cVe2Y-50) and cVe1Y < (cVe2Y+50)): # Doppio verde verifica solo se falso
            if (Lv+Lt+cVe1Y+10)>h: #¶Il verde è basso bisogna verificare la parte alta
                #Verifica se esiste il nero sopra
                ImmBkAlto=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,cVe1X:cVe1X+Lt]
                TrovBkAlto,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAlto,"nero",AreaSigBkVe)
                if TrovBkAlto:
                    TipoAzione="Fr"
                else:
                    TipoAzione="FF"
            else:
                #verifica se esiste il nero sotto
                ImmBkBasso=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,cVe1X:cVe1X+Lt]
                TrovBkBasso,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBasso,"nero",AreaSigBkVe)
                if TrovBkBasso:
                    TipoAzione="FF"
                else:
                    TipoAzione="Fr"
        elif TrovVer1 and TrovVer2 and not (cVe1Y > (cVe2Y-50) and cVe1Y < (cVe2Y+50)):
            if cVe2Y > cVe1Y:
                (cVe1X,cVe1Y)=(cVe2X,cVe2Y)
            if (Lv+Lt+cVe1Y+10)>h: #¶Il verde è basso bisogna verificare la parte alta
                #Verifica se esiste il nero sopra
                ImmBkAlto=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,cVe1X:cVe1X+Lt]
                TrovBkAlto,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAlto,"nero",AreaSigBkVe)
                if TrovBkAlto:
                    TipoAzione="CROSS"
                else:
                    TipoAzione="FF"
            else:
                #verifica se esiste il nero sotto
                ImmBkBasso=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,cVe1X:cVe1X+Lt]
                TrovBkBasso,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBasso,"nero",AreaSigBkVe)
                if TrovBkBasso:
                    TipoAzione="FF"
                else:
                    TipoAzione="CROSS"
        elif TrovVer1:            
            if (Lv+Lt+cVe1Y+10)>h: #¶Il verde è basso bisogna verificare la parte alta
                #Verifica se esiste il nero sopra
                if cVe1X-Lt-1 < 0:
                    ImmBkAltoSx=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,0:cVe1X+Lt-Lt-1]
                else:    
                    ImmBkAltoSx=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,cVe1X-Lt-1:cVe1X+Lt-Lt-1]
                ImmBkAltoCx=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,cVe1X:cVe1X+Lt]
                if cVe1X+Lt+Lt+1 > RisX:
                    ImmBkAltoDx=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,cVe1X+Lt+1:RisX]
                else:
                    ImmBkAltoDx=Img_ruotata[cVe1Y-Lv-Lt:cVe1Y-Lv,cVe1X+Lt+1:cVe1X+Lt+Lt+1]
                try:
                    TrovBkAltoSx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAltoSx,"nero",AreaSigBkVe)
                except:    
                    TrovBkAltoSx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAltoCx,"nero",AreaSigBkVe)
                
                TrovBkAltoCx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAltoCx,"nero",AreaSigBkVe)
                
                try:
                    TrovBkAltoDx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAltoDx,"nero",AreaSigBkVe)
                except:
                    TrovBkAltoDx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkAltoCx,"nero",AreaSigBkVe)
                if TrovBkAltoSx and TrovBkAltoCx and TrovBkAltoDx:
                    TipoAzione="CROSS"
                elif TrovBkAltoSx and TrovBkAltoCx and not TrovBkAltoDx:
                    TipoAzione="CROSS" #"FFDx"   
                elif not TrovBkAltoSx and TrovBkAltoCx and TrovBkAltoDx:
                    TipoAzione="CROSS" #"FFSx"                    
                else:
                    TipoAzione="FF"  
            else:
                #verifica se esiste il nero sotto
                if cVe1X-Lt-1 <0:
                    ImmBkBassoSx=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,0:cVe1X+Lt-Lt-1]
                else:    
                    ImmBkBassoSx=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,cVe1X-Lt-1:cVe1X+Lt-Lt-1]
                ImmBkBassoCx=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,cVe1X:cVe1X+Lt]
                if cVe1X+Lt+Lt+1 > RisX:
                    ImmBkBassoDx=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,cVe1X+Lt+1:RisX]
                else:    
                    ImmBkBassoDx=Img_ruotata[cVe1Y+Lv:cVe1Y+Lv+Lt,cVe1X+Lt+1:cVe1X+Lt+Lt+1]
                try:
                    TrovBkBassoSx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBassoSx,"nero",AreaSigBkVe)
                except:
                    TrovBkBassoSx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBassoCx,"nero",AreaSigBkVe)
                
                TrovBkBassoCx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBassoCx,"nero",AreaSigBkVe)
                try:
                    TrovBkBassoDx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBassoDx,"nero",AreaSigBkVe)
                except:
                    TrovBkBassoDx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkBassoCx,"nero",AreaSigBkVe)
                if TrovBkBassoSx and TrovBkBassoCx and TrovBkBassoDx:
                    TipoAzione="FF"
                elif TrovBkBassoSx and TrovBkBassoCx and not TrovBkBassoDx:
                    TipoAzione="CROSS" #"FFDx"
                elif not TrovBkBassoSx and TrovBkBassoCx and TrovBkBassoDx:
                    TipoAzione="CROSS" #"FFSx"
                else:
                    TipoAzione="CROSS"
        else:
                TipoAzione="None"
        if TipoAzione=="CROSS":       
            if (Lv+Lt+cVe1X+10)>w: #il verde è troppo a destra bisogna verificare a sinistra
                ImmBkSx=Img_ruotata[cVe1Y:cVe1Y+Lt,cVe1X-Lv-Lt:cVe1X-Lv]
                TrovBkSx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkSx,"nero",AreaSigBkVe)
                if TrovBkSx:
                    TipoAzione="Dx"
                else:
                    TipoAzione="Sx"
            else:
                ImmBkDx=Img_ruotata[cVe1Y:cVe1Y+Lt,cVe1X+Lv:cVe1X+Lv+Lt]
                TrovBkDx,(cBkCeXSx,cBkCeYSx),_,_ = CercaBlocchiCol(ImmBkDx,"nero",AreaSigBkVe)
                if TrovBkDx:
                    TipoAzione="Sx"
                else:
                    TipoAzione="Dx"
    if not (Img_ruotata is None):
        cv2.imshow('Linea', Img_ruotata)
        key = cv2.waitKey(1) & 0xFF
        
        time.sleep(0.01)
    print(TipoAzione, angle)
    return TipoAzione
    #time.sleep(1)
    #cv2.destroyAllWindows()




def PallinaNuova(Immagine, CLS):
    model = MOD_PALLE      # [FIX 1]

    # Se immagine con alpha → converti
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)

    # Ridimensionamento per NCNN
    img224 = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)

    # Predizione YOLO
    results = model.predict(img224, conf=0.6, verbose=False)[0]

    SalvaFoto("PALLE", img224)     # [FIX 2]

    # Nessun box rilevato
    if results.boxes is None or len(results.boxes) == 0:
        return False, 0, 0, 0, 0, img224

    max_area = 0
    best_box = None

    # Cerca solo la classe richiesta
    for box in results.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])

        if cls != CLS:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        area = (x2 - x1) * (y2 - y1)

        if area > max_area:
            max_area = area
            best_box = (x1, y1, x2, y2, conf)

    # Nessun box della classe richiesta
    if best_box is None:
        return False, 0, 0, 0, None, img224
    annotated = img224.copy()
    SalvaFoto("VIT-"+str(CLS), img224)     # [FIX 2]
 
    # Estrai box migliore
    x1, y1, x2, y2, conf = best_box
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)

    # Disegno direttamente sull'immagine 224x224
    
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.circle(annotated, (center_x, center_y), 5, (0, 0, 255), -1)
    cv2.putText(annotated, f"CLS {CLS}", (x1, y1 - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Ritorno finale
    return True, max_area, center_x, center_y, CLS, annotated



UltimoBox = None    # [FIX 35] ultimo riquadro trovato da CercaPortaTri (x1, y1, x2, y2)

def CercaPortaTri(Immagine,CLS):
    model = MOD_TRIAN      # [FIX 1]

    # Se immagine con alpha → converti
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)

    # Ridimensionamento per NCNN
    img224 = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)

    # Predizione YOLO
    results = model.predict(img224, conf=0.6, verbose=False)[0]

    SalvaFoto("ARENA", img224)     # [FIX 2]

    # Nessun box rilevato
    if results.boxes is None or len(results.boxes) == 0:
        return False, 0, 0, 0, 0, img224

    max_area = 0
    best_box = None

    # Cerca solo la classe richiesta
    for box in results.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])

        if cls != CLS:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        area = (x2 - x1) * (y2 - y1)

        if area > max_area:
            max_area = area
            best_box = (x1, y1, x2, y2, conf)

    # Nessun box della classe richiesta
    if best_box is None:
        return False, 0, 0, 0, None, img224

    # Estrai box migliore
    x1, y1, x2, y2, conf = best_box
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)

    # Disegno direttamente sull'immagine 224x224
    annotated = img224.copy()
    SalvaFoto("TRI", img224)       # [FIX 2]

    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.circle(annotated, (center_x, center_y), 5, (0, 0, 255), -1)
    cv2.putText(annotated, f"CLS {CLS}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    global UltimoBox
    UltimoBox = (x1, y1, x2, y2)    # [FIX 35] serve a EsciDallaPorta per misurare la larghezza della porta
    # Ritorno finale
    return True, max_area, center_x, center_y, CLS, annotated


      
def VerificaUscita(Immagine):
    #model = YOLO('beststriscia.pt')  #TriVerde = 1  TriRosso = 2  Uscita = 3
    #model = YOLO('bestUscita1300.pt')  #TriVerde = 1  TriRosso = 2  Uscita = 3
    
    model = MOD_EXIT       # [FIX 1]  Uscita = 0  Ingresso =1
    
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)

    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)

    # Predizione NCNN
    results = model.predict(array, conf=0.6, verbose=False)[0]

    closest_box = None
    max_area = 0
    center_x = 0
    center_y = 0 
    cls = None
    
    annotated = array
    
    SalvaFoto("EXIT", array)       # [FIX 2]


    # Controllo robusto
    if results.boxes is None or len(results.boxes) == 0:
        box = None
        best_cls = None
        max_conf = 0
        annotated = array
        closest_box=None
    else:
        box = results.boxes[0]
        cls = int(box.cls[0])
        max_conf = float(box.conf[0])
        annotated = results.plot()


        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                # Se vuoi filtrare solo sfere, ad esempio classe 0
                #if cls != 0:
                #    continue

                # Coordinate bounding box
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Calcola area del box
                area = (x2 - x1) * (y2 - y1)

                # Se questa è la più grande trovata finora ⇒ più vicina
                if area > max_area:
                    max_area = area
                    closest_box = (x1, y1, x2, y2, conf)

        if closest_box:
            x1, y1, x2, y2, conf = closest_box
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            '''
            best_cls="EXIT"
            NomeFile="/home/pi/OneDrive/Incroci/"+best_cls+f"Cross{datetime.now()}.jpg"
            array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
            if array is not None:
                #cv2.imshow("Foto Scattata", annotated_frame)
                cv2.imwrite(NomeFile, array)
                #print(f"foto{NumFoto}.jpg salvata")
            #time.sleep(0.1)   
              
            print(f"Uscita più vicina,Tipo : ({cls}), Centro: ({center_x}, {center_y}), Confidenza: {conf:.2f}, Area: {max_area}")
            '''
            
            # Disegna il box e il centro sull'immagine (opzionale)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(annotated, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.putText(annotated, "Più vicina", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
    return closest_box, max_area, center_x, center_y, cls, annotated    

def TipoPorta(Immagine):
    # [FIX 53] La camera ARENA guarda un'apertura del muro: è l'USCITA o l'INGRESSO?
    # Usa il modello best_ncnn_model_Exit3 (classe 0 = uscita, 1 = ingresso) e prende la classe del riquadro
    # PIU' GRANDE (VerificaUscita restituiva la classe dell'ultimo riquadro esaminato, non del più grande).
    # Restituisce ("uscita" | "ingresso" | None, sicurezza).
    if Immagine is None:
        return None, 0.0
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    risultati = MOD_EXIT.predict(array, conf=0.6, verbose=False)[0]
    SalvaFoto("EXIT", array)
    if risultati.boxes is None or len(risultati.boxes) == 0:
        return None, 0.0
    migliore, area_max = None, 0
    for box in risultati.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        area = (x2 - x1) * (y2 - y1)
        if area > area_max:
            area_max, migliore = area, box
    cls, conf = int(migliore.cls[0]), float(migliore.conf[0])
    return ("uscita" if cls == 0 else "ingresso" if cls == 1 else None), conf


_falso_verde_t = [0.0]    # [FIX 41] quando i colori hanno visto l'ultimo falso verde


PausaVerdi = [0.0]         # [FIX 80] fino a quando i verdi non si rivalutano (dopo una svolta al verde)
PausaSenzaVerde = [0]      # [FIX 80] fotogrammi di fila senza verde durante la pausa
UltimoControlloVerde = [(None, "")]   # [FIX 79] ultimo giudizio dei colori (per la conferma del dietrofront)


def VerdiGeometria(array, dettagli=None):
    # [FIX 36] Decide l'incrocio guardando DOVE sono i verdi, senza YOLO.
    # Nell'immagine della camera linea il basso è vicino al robot e l'alto è lontano.
    # Regola RoboCup: un verde vale solo se è PRIMA dell'incrocio, cioè SOTTO la linea di traverso
    # nell'immagine. Un verde sopra la linea è dopo l'incrocio: è falso.
    # Restituisce ("Sx" / "Dx" / "Fr" / "Ln", spiegazione) oppure (None, motivo) se non si può dire.
    #
    # [FIX 78] SCATOLA NERA 29/10, secondo 61,8. Piastrella con i due verdi in DIAGONALE (uno prima e uno dopo
    # l'incrocio). Il robot ha girato a sinistra giusto, ma a metà svolta ha rivisto lo STESSO incrocio di
    # traverso (linea inclinata di 40 gradi). La versione vecchia cercava la linea dell'incrocio solo per RIGHE
    # orizzontali dell'immagine: con la linea storta ha messo il "confine" a metà immagine, ha contato tutti e
    # due i verdi come "prima dell'incrocio" e ha cambiato il giusto "Sx" di YOLO in "Fr": DIETROFRONT.
    # Ora:
    #   1) si cerca la DIREZIONE della linea dell'incrocio (da -40 a +40 gradi) e si misura tutto lungo quella;
    #   2) se la linea è più storta di VERDE_ANGOLO_MAX gradi i colori NON giudicano (None);
    #   3) le macchie verdi strette o "sfilacciate" non contano: sono il bordo scuro del nastro nero, che la
    #      camera vede un po' verde (nella foto del secondo 56 c'era una "macchia" di 15x94 pixel lungo la linea).
    # dettagli: dizionario facoltativo che viene riempito con angolo, linea e macchie (lo usa ProvaVerde.py).
    if dettagli is None:
        dettagli = {}
    hsv = cv2.cvtColor(array, cv2.COLOR_BGR2HSV)
    verde = cv2.inRange(hsv, lower_green, upper_green)
    verde = cv2.morphologyEx(verde, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))     # [FIX 78] via le frange
    nero = cv2.inRange(hsv, lower_black, upper_black)
    nero[verde > 0] = 0
    H, W = nero.shape
    ys, xs = np.nonzero(nero)
    if len(xs) < 200:
        return None, "nessuna linea orizzontale"
    # 1) direzione della linea di traverso: per ogni inclinazione si contano i pixel neri lungo "righe
    #    inclinate"; quando l'inclinazione è giusta la linea dell'incrocio riempie poche righe tutte piene.
    #    Si sceglie l'inclinazione con la somma dei quadrati più grande (righe piene contano molto di più)
    migliore = None
    for a in range(-40, 41, 2):
        t = np.radians(a)
        d = np.round(ys * np.cos(t) - xs * np.sin(t)).astype(int)
        d0 = int(d.min())
        conta = np.bincount(d - d0)
        energia = float((conta.astype(np.float64) ** 2).sum())
        if migliore is None or energia > migliore[0]:
            migliore = (energia, a, conta, d0, d)
    _, a, conta, d0, d = migliore
    soglia = 0.9 * RwdConf.VERDE_NERO_RIGA
    if conta.max() < soglia:
        return None, "nessuna linea orizzontale"
    if abs(a) > RwdConf.VERDE_ANGOLO_MAX:
        return None, f"incrocio storto di {a} gradi: i colori non giudicano"
    dettagli["angolo"] = a
    t = np.radians(a)
    righe = np.where(conta > max(soglia, 0.5 * conta.max()))[0]
    gruppi = np.split(righe, np.where(np.diff(righe) > 3)[0] + 1)
    banda = max(gruppi, key=lambda g: conta[g].sum())
    forti = banda[conta[banda] >= 0.7 * conta[banda].max()]
    d_banda = float(forti.mean()) + d0      # le righe più piene: l'ombra ai bordi non sposta il centro
    y_banda = (d_banda + (W / 2) * np.sin(t)) / np.cos(t)        # la stessa riga, al centro dell'immagine
    dettagli["y_banda"] = y_banda
    if y_banda < RwdConf.VERDE_Y_MIN:
        return None, f"incrocio troppo in alto (y={y_banda:.0f})"
    if y_banda > RwdConf.VERDE_Y_MAX:
        return None, f"incrocio troppo in basso (y={y_banda:.0f})"
    # 2) la linea "verticale": posizione (lungo la linea di traverso) del nero fuori dalla banda
    s = xs * np.cos(t) + ys * np.sin(t)
    fuori = (d < banda[0] + d0 - 3) | (d > banda[-1] + d0 + 3)
    if fuori.sum() < 50:
        return None, "linea verticale non trovata"
    s_linea = float(np.median(s[fuori]))
    # 3) i verdi: prima (sotto la linea di traverso, misurata con la sua inclinazione) o dopo (sopra)
    n, _, st, cen = cv2.connectedComponentsWithStats(verde)
    sx = dx = falsi = 0
    dettagli["macchie"] = macchie = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < RwdConf.VERDE_AREA_MIN:
            continue
        if min(w, h) < RwdConf.VERDE_LATO_MIN or area < RwdConf.VERDE_RIEMPIMENTO * w * h:
            macchie.append((x, y, w, h, "ignorata"))
            continue                                    # [FIX 78] striscia sottile o sfilacciata: non è un verde
        cx, cy = cen[i]
        if cy * np.cos(t) - cx * np.sin(t) > d_banda:   # sotto la linea di traverso: PRIMA dell'incrocio
            if cx * np.cos(t) + cy * np.sin(t) < s_linea:
                sx += 1
            else:
                dx += 1
            macchie.append((x, y, w, h, "valido"))
        else:
            falsi += 1
            macchie.append((x, y, w, h, "falso"))
    if sx == 0 and dx == 0 and falsi == 0:
        return None, "nessun verde"
    cls = "Fr" if (sx and dx) else "Sx" if sx else "Dx" if dx else "Ln"
    return cls, f"incrocio a y={y_banda:.0f} inclinato {a:+d} gradi, verdi validi sx={sx} dx={dx}, falsi={falsi}"


def DistanzaLineaTrasversale(Immagine):
    # [FIX 41] Se nell'immagine della camera linea c'è una linea di traverso (incrocio), a quanti cm
    # davanti al muso si trova? None se non c'è. Usa la taratura della camera fatta con le foto del righello.
    if Immagine is None:
        return None
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(array, cv2.COLOR_BGR2HSV)
    nero = cv2.inRange(hsv, lower_black, upper_black) > 0
    righe = np.where(nero.sum(axis=1) > 0.4 * 224)[0]          # anche un T con il ramo da una parte sola
    if len(righe) == 0:
        return None
    gruppi = np.split(righe, np.where(np.diff(righe) > 3)[0] + 1)
    banda = max(gruppi, key=len)
    y = (banda[0] + banda[-1]) / 2 * 260.0 / 224.0                 # riga nell'immagine vera 440x260
    ang = np.arctan((y - 130) / RwdConf.CAM_LINEA_FY) + np.radians(RwdConf.CAM_LINEA_INCL)
    return float(RwdConf.CAM_LINEA_ALTEZZA / np.tan(ang) - RwdConf.CAM_LINEA_OFFSET)


def LineaAlCentro(Immagine):
    # [FIX 41] La linea nera passa al centro della parte bassa dell'immagine (davanti al muso, dritta)?
    # Serve a finire le svolte agli incroci: il robot gira finché la linea nuova è davanti a lui.
    if Immagine is None:
        return False
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(array[112:, :], cv2.COLOR_BGR2HSV)          # metà bassa: vicino al muso
    nero = cv2.inRange(hsv, lower_black, upper_black) > 0
    centro = nero[:, 92:132]                                        # striscia centrale larga 40 pixel
    righe_con_linea = (centro.sum(axis=1) >= 8).mean()              # quante righe hanno nero al centro
    return righe_con_linea >= RwdConf.SVOLTA_RIGHE_CENTRO


def StrisciaNera(Immagine):
    # [FIX 39] La camera linea vede la striscia NERA dell'uscita (nastro 2,5 x 25 cm)?
    # Prima (FIX 38) si cercavano righe dell'immagine tutte nere: funzionava solo se il robot passava
    # sopra la striscia DRITTO. Passando di sbieco la striscia è una banda obliqua e non veniva vista.
    # Ora basta una macchia nera grande che attraversi l'immagine da sinistra a destra, con qualsiasi
    # inclinazione (la linea normale invece va dall'alto in basso, la pallina nera è piccola).
    # Restituisce l'inclinazione della striscia in gradi (0 = di traverso davanti al robot) oppure None.
    if Immagine is None:
        return None
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(array, cv2.COLOR_BGR2HSV)
    nero = cv2.inRange(hsv, lower_black, upper_black)
    n, etich, st, _ = cv2.connectedComponentsWithStats(nero)
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < RwdConf.STRISCIA_AREA_MIN:
            continue
        da_lato_a_lato = x <= 4 and x + w >= 220                  # attraversa da sinistra a destra
        obliqua = y <= 4 and y + h >= 220 and w >= 0.35 * 224      # molto inclinata: dall'alto in basso ma larga
        if da_lato_a_lato or obliqua:
            ys, xs = np.nonzero(etich == i)
            # l'immagine 224x224 è schiacciata (l'originale è 440x260): torno alle proporzioni vere
            xs = xs * (Immagine.shape[1] / 224.0)
            ys = ys * (Immagine.shape[0] / 224.0)
            vx, vy, _, _ = cv2.fitLine(np.column_stack([xs, ys]).astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).ravel()
            if vx < 0:
                vx, vy = -vx, -vy
            return float(np.degrees(np.arctan2(vy, vx)))
    return None


def GeometriaStrisciaNera(Immagine):
    # [FIX 84] Come StrisciaNera, ma restituisce anche DOVE finisce la striscia nera dell'uscita:
    # (inclinazione in gradi, (u, v) estremità sinistra, (u, v) estremità destra, larghezza, altezza)
    # in pixel dell'immagine vera (440x260), oppure None se la striscia non si vede.
    # L'inclinazione è None se la striscia è tagliata dal bordo basso dell'immagine (non si può misurare).
    # Serve per mettersi dritti e in mezzo alla porta d'uscita SENZA fidarsi del giroscopio.
    if Immagine is None:
        return None
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    H, W = Immagine.shape[:2]
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    nero = cv2.inRange(cv2.cvtColor(array, cv2.COLOR_BGR2HSV), lower_black, upper_black)
    n, etich, st, _ = cv2.connectedComponentsWithStats(nero)
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < RwdConf.STRISCIA_AREA_MIN:
            continue
        # la striscia è larga (la linea da sola è stretta); può essere unita alla linea che esce dalla porta
        if w < 0.55 * 224:
            continue
        # Si misura il BORDO BASSO della striscia (il più vicino al robot), colonna per colonna: fuori
        # dall'uscita la linea nera parte dal lato lontano della striscia e, presa insieme alla striscia,
        # ne storceva l'inclinazione (simulatore: -4 gradi con il robot perfettamente dritto).
        comp = etich == i
        colonne = np.nonzero(comp.any(axis=0))[0]
        if len(colonne) < 40:
            continue
        basso = np.array([np.nonzero(comp[:, c])[0].max() for c in colonne], dtype=np.float64)
        x_min, x_max = colonne.min() * (W / 224.0), colonne.max() * (W / 224.0)
        tagliate = basso >= 221                        # colonne dove la striscia esce dal bordo basso
        if (~tagliate).sum() < 40:
            # striscia tagliata dal bordo basso: inclinazione non misurabile, ma la posizione sì
            return None, (float(x_min), float(H - 1)), (float(x_max), float(H - 1)), W, H
        colonne, basso = colonne[~tagliate], basso[~tagliate]
        xs = colonne * (W / 224.0)
        ys = basso * (H / 224.0)
        buoni = np.ones(len(xs), bool)
        for _ in range(3):                             # via i punti lontani dalla retta (bordi sporchi, angoli)
            m, q = np.polyfit(xs[buoni], ys[buoni], 1)
            res = np.abs(ys - (m * xs + q))
            nuovi = res < max(3.0, 2.5 * np.median(res[buoni]))
            if nuovi.sum() < 20 or (nuovi == buoni).all():
                break
            buoni = nuovi
        m, q = np.polyfit(xs[buoni], ys[buoni], 1)
        x_sx, x_dx = float(x_min), float(x_max)
        return float(np.degrees(np.arctan(m))), (x_sx, m * x_sx + q), (x_dx, m * x_dx + q), W, H
    return None


UltimoBoxLinea = [None]    # [FIX 46] ultimo riquadro trovato da VerificaVerde (immagine 224x224)


def LineaOltreStriscia(Immagine, box=None):
    # [FIX 46] CONTROLLO DELL'INGRESSO: la linea nera FINISCE alla striscia argento (dopo c'è l'arena).
    # Se oltre la striscia (nella parte alta dell'immagine, più lontana dal robot) la linea nera continua,
    # quella che YOLO ha chiamato "argento" non è l'ingresso: un riflesso, un pezzo di nastro, una giuntura.
    # Restituisce True (la linea continua: NON è l'ingresso), False (oltre la striscia niente linea)
    # oppure None (la striscia è troppo in alto nell'immagine per guardare oltre).
    if Immagine is None:
        return None
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    if box is None:
        box = UltimoBoxLinea[0]
    if box is None:
        return None
    y_striscia = int(box[1]) - 6                     # bordo lontano della striscia, con margine
    if y_striscia < 30:
        return None
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(array[:y_striscia], cv2.COLOR_BGR2HSV)
    nero = cv2.inRange(hsv, lower_black, upper_black)
    n, _, st, _ = cv2.connectedComponentsWithStats(nero)
    for i in range(1, n):
        x, y, w, h, area = st[i]
        # un pezzo di linea che parte dal bordo alto e scende per buona parte della zona oltre la striscia
        if y <= 3 and h >= 0.6 * y_striscia and area >= 250:
            return True
    return False


def VerificaVerde(Immagine):

    #model = YOLO('beststriscia.pt')  #TriVerde = 1  TriRosso = 2  Uscita = 3
    #model = YOLO('bestLine2.pt')  #Dx = 0  FDx = 1  FFr = 2  Fr = 3  FSx = 4  Sx = 5
    model = MOD_CROSS      # [FIX 1]
    
    if Immagine.shape[2] == 4:
        Immagine = cv2.cvtColor(Immagine, cv2.COLOR_BGRA2BGR)
    
    array = cv2.resize(Immagine, (224, 224), interpolation=cv2.INTER_AREA)
    #array = Immagine
    if PausaVerdi[0] and time.time() < PausaVerdi[0]:
        # [FIX 80] la pausa dopo la svolta finisce appena l'incrocio della svolta esce dalla camera
        verde = cv2.inRange(cv2.cvtColor(array, cv2.COLOR_BGR2HSV), lower_green, upper_green)
        PausaSenzaVerde[0] = PausaSenzaVerde[0] + 1 if cv2.countNonZero(verde) < RwdConf.VERDE_AREA_MIN else 0
        if PausaSenzaVerde[0] >= getattr(RwdConf, "VERDE_PAUSA_FOTOGRAMMI", 4):
            PausaVerdi[0] = 0.0
    
    #predict = model.predict(source=array, imgsz=224)

    # Predizione YOLO    
    #results = model.predict(source=array, imgsz=224)

    # Predizione NCNN
    results = model.predict(array, conf=0.7, verbose=False)[0]

    # Controllo robusto
    if results.boxes is None or len(results.boxes) == 0:
        box = None
        best_cls = None
        max_conf = 0
        annotated_frame = None
        center_x = 112
    else:
        box = results.boxes[0]
        cls = int(box.cls[0])
        max_conf = float(box.conf[0])
        annotated_frame = results.plot()

        if cls==1:
            best_cls="Di"
        elif cls==2:
            best_cls="Dx"
        elif cls==3:
            best_cls="Fr"
        elif cls==0:
            best_cls="Bi" 
        elif cls==4:
            best_cls="In" 
        elif cls==5:
            best_cls="Ln" 
        elif cls==6:
            best_cls="Ro" 
        elif cls==7:
            best_cls="Sx" 
        else:
            best_cls="No"   

        x1, y1, x2, y2 = box.xyxy[0]
        center_x = int((x1 + x2) / 2)
        UltimoBoxLinea[0] = (float(x1), float(y1), float(x2), float(y2))   # [FIX 46] serve a LineaOltreStriscia
        #x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        # Calcola area del box
        #area = (x2 - x1) * (y2 - y1)

        if y1 < 80 and y2 < 80 and ((best_cls=="Dx") or  (best_cls=="Fr") or ( best_cls=="Sx")or ( best_cls=="Di")):
            best_cls="Ln"

        # [FIX 36] SECONDO PARERE SUI VERDI: YOLO a volte prende per buono un verde che sta DOPO
        # l'incrocio (falso verde) e il robot gira invece di andare dritto. Qui si controlla con i
        # colori dove stanno i verdi rispetto alla linea orizzontale dell'incrocio.
        if RwdConf.CONTROLLO_VERDE and best_cls in ("Sx", "Dx", "Fr") and time.time() < PausaVerdi[0]:
            # [FIX 80] SCATOLA NERA 29/10: subito dopo la svolta a sinistra il robot ha rivisto lo STESSO incrocio
            # (di traverso, mentre finiva la curva) e lo ha giudicato di nuovo. Dopo una svolta al verde, finché
            # quell'incrocio è nella camera, i verdi non si rivalutano: si segue la linea.
            print(f"Controllo verde: YOLO dice {best_cls}, ma ho appena girato a questo incrocio: seguo la linea")
            best_cls = "Ln"
        if RwdConf.CONTROLLO_VERDE and best_cls in ("Sx", "Dx", "Fr"):
            geo, perche = VerdiGeometria(array)
            UltimoControlloVerde[0] = (geo, perche)
            if geo == "Fr" and best_cls != "Fr":
                # [FIX 79] i colori possono TOGLIERE un verde (falso verde) ma non AGGIUNGERLO: se YOLO vede un
                # verde solo, i colori non lo trasformano in un doppio verde (dietrofront).
                print(f"Controllo verde: YOLO dice {best_cls}, i colori dicono Fr ({perche}): tengo {best_cls}")
            elif (geo is None and best_cls == "Fr" and getattr(RwdConf, "DIETRO_CONFERMA", False)
                  and perche.startswith("incrocio troppo in alto")):
                # [FIX 79] doppio verde visto da lontano: i colori non possono ancora controllare. Il dietrofront
                # costa caro se è sbagliato: continuo a seguire la linea e decido col prossimo fotogramma.
                print(f"Controllo verde: YOLO dice Fr ma l'incrocio è ancora lontano ({perche}): aspetto")
                best_cls = "Ln"
            elif geo is not None and geo != best_cls:
                print(f"Controllo verde: YOLO dice {best_cls}, i colori dicono {geo} ({perche})")
                best_cls = geo
                if geo == "Ln":
                    _falso_verde_t[0] = time.time()
            elif geo is None and time.time() - _falso_verde_t[0] < 1.0:
                # [FIX 41] l'incrocio è ormai troppo in basso per giudicare, ma un attimo fa i colori
                # hanno detto "falso verde": vale ancora quel giudizio, si va dritto
                print(f"Controllo verde: YOLO dice {best_cls}, ma un attimo fa era un falso verde: dritto")
                best_cls = "Ln"

            
        SalvaFoto(best_cls, array)     # [FIX 2]

    return best_cls, max_conf, center_x, annotated_frame   


def AutoregolaCam(Cam, blocca_esposizione=None):
    ####  AUTO REGOLAZIONE - TARATURA CAM   #####
    # [FIX 112] Per la camera linea il chiamante forza il blocco dopo aver
    # acceso i LED e atteso l'assestamento. Le altre camere mantengono il
    # comportamento configurato da BLOCCA_ESPOSIZIONE.
    print("Taratura CAM")
    try:
        metadata = Cam.capture_metadata()
        exposure = metadata.get("ExposureTime")
        gain = metadata.get("AnalogueGain")
    except Exception as e:
        print("[CAM] Metadati esposizione non disponibili:", e)
        exposure, gain = None, None

    blocca = (bool(getattr(RwdConf, "BLOCCA_ESPOSIZIONE", False))
              if blocca_esposizione is None else bool(blocca_esposizione))
    bloccata = False
    try:
        with Cam.controls as ctrl:
            if blocca and exposure is not None and gain is not None:
                ctrl.AeEnable = False
                ctrl.ExposureTime = int(exposure)
                ctrl.AnalogueGain = float(gain)
                bloccata = True
                print(f"Esposizione bloccata: {exposure} us, gain {gain:.2f}")
            ctrl.Brightness = -0.05 #-0.15
            ctrl.Contrast = 1
    except Exception as e:
        print("[CAM] Non riesco ad applicare i controlli di esposizione:", e)
    return {"bloccata": bloccata, "exposure_us": exposure, "gain": gain}


def ImpostaSogliaNero(soglia):
    """[FIX 112] Aggiorna insieme la soglia della camera e quella usata da RwdFoto."""
    global SOGLIA_NERO, upper_black
    valore = max(0, min(255, int(round(float(soglia)))))
    SOGLIA_NERO = valore
    RwdConf.SOGLIA_NERO = valore
    upper_black = np.array([180, 150, valore])
    return valore


def _misura_otsu_linea(Cam, numero_fotogrammi):
    """Otsu sul canale V dei pixel poco saturi, come TaraNero.py (nero + pavimento)."""
    valori = []
    for _ in range(numero_fotogrammi):
        img = Cam.capture_array()
        if img is None:
            continue
        if img.ndim == 2:
            bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3 and img.shape[2] == 4:
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif img.ndim == 3 and img.shape[2] == 3:
            bgr = img
        else:
            continue
        piccolo = cv2.resize(bgr, (224, 224), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(piccolo, cv2.COLOR_BGR2HSV)
        v = hsv[..., 2][hsv[..., 1] <= 150]
        if v.size:
            valori.append(v.reshape(-1))
        time.sleep(0.02)
    if not valori:
        return None, "nessun pixel valido dai fotogrammi"
    campione = np.concatenate(valori).astype(np.uint8, copy=False)
    otsu, _ = cv2.threshold(campione.reshape(-1, 1), 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    nero = campione[campione <= otsu]
    bianco = campione[campione > otsu]
    min_pixel = int(getattr(RwdConf, "CAM_LINEA_PIXEL_MIN_OTSU", 200))
    if len(nero) < min_pixel or len(bianco) < min_pixel:
        return None, (f"campioni insufficienti: nero {len(nero)}, bianco {len(bianco)} "
                      f"(minimo {min_pixel} per gruppo)")
    misure = {"soglia_otsu": int(round(float(otsu))),
              "nero_tipico": int(np.median(nero)),
              "nero_max_97": int(np.percentile(nero, 97)),
              "bianco_tipico": int(np.median(bianco)),
              "bianco_min_3": int(np.percentile(bianco, 3)),
              "pixel_nero": int(len(nero)), "pixel_bianco": int(len(bianco))}
    return misure, None


def AutotaraturaLinea(Cam):
    """[FIX 112] Blocca l'esposizione con LED accesi e calcola la soglia Otsu."""
    riserva = int(SOGLIA_NERO_RISERVA)
    minimo = int(getattr(RwdConf, "CAM_LINEA_SOGLIA_MIN", 60))
    massimo = int(getattr(RwdConf, "CAM_LINEA_SOGLIA_MAX", 170))
    attesa = max(0.0, float(getattr(RwdConf, "CAM_LINEA_ASSESTAMENTO_S", 1.5)))
    n = max(3, min(30, int(getattr(RwdConf, "CAM_LINEA_FOTOGRAMMI_OTSU", 7))))
    fps = max(5, min(30, int(getattr(RwdConf, "CAM_LINEA_FPS", 20))))
    try:
        # L'autoesposizione deve prima vedere i LED già accesi e la scena reale.
        time.sleep(attesa)
        esposizione = AutoregolaCam(
            Cam, blocca_esposizione=bool(getattr(RwdConf, "CAM_LINEA_BLOCCA_ESPOSIZIONE", True)))
        # [FIX 112] Scarto tre fotogrammi: i controlli camera possono arrivare
        # al sensore con alcuni frame di ritardo dopo il blocco dell'esposizione.
        for _ in range(3):
            Cam.capture_array()
        misure, motivo = _misura_otsu_linea(Cam, n)
        otsu = misure.get("soglia_otsu") if misure else None
        valida = otsu is not None and minimo <= otsu <= massimo
        if valida:
            scelta = int(otsu)
            fonte = "Otsu"
            motivo = None
        else:
            scelta = riserva
            fonte = "ViennaDataConf.SOGLIA_NERO"
            if otsu is not None:
                motivo = f"Otsu {otsu} fuori dall'intervallo {minimo}-{massimo}"
            elif not motivo:
                motivo = "Otsu non calcolabile"
        ImpostaSogliaNero(scelta)
        return {"soglia": scelta, "fonte": fonte, "otsu_ok": bool(valida),
                "soglia_otsu": otsu, "motivo": motivo, "misure": misure,
                "esposizione": esposizione, "fuoco": dict(_INFO_FUOCO_LINEA), "fps": fps}
    except Exception as e:
        ImpostaSogliaNero(riserva)
        return {"soglia": riserva, "fonte": "ViennaDataConf.SOGLIA_NERO", "otsu_ok": False,
                "soglia_otsu": None, "motivo": str(e), "misure": None,
                "esposizione": {"bloccata": False}, "fuoco": dict(_INFO_FUOCO_LINEA), "fps": fps}
    
def CalcolaErrore(frame):
    global ErrPre
    LBanda=30 #50
    Errore=0
    Azione=None
    Xa=CentroX
    Alto = frame[0:LBanda,:]
    Basso = frame[(RisY-LBanda):RisY,LBanda+1:RisX-LBanda-1] 
    Destro = frame[(LBanda+1):(RisY),(RisX-LBanda):RisX]
    Sinistro = frame[(LBanda+1):(RisY),0:LBanda]
    TrovAlto,(cBkAlX,cBkAlY),_,_ = CercaBlocchiCol(Alto,"nero",AreaSigBk)
    TrovBasso,(cBkBaX,cBkBaY),_,_ = CercaBlocchiCol(Basso,"nero",AreaSigBk)
    TrovDestro,(cBkDeX,cBkDeY),_,_ = CercaBlocchiCol(Destro,"nero",AreaSigBk)
    TrovSinistro,(cBkSiX,cBkSiY),_,_ = CercaBlocchiCol(Sinistro,"nero",AreaSigBk)
    # [FIX 29] INCROCIO A T SENZA VERDE: da regolamento si va DRITTI.
    # Se la linea c'è in alto e in basso e un ramo esce da un solo lato, il ramo laterale è
    # attaccato alla linea nella banda alta e il suo centro si sposta verso il ramo: il robot
    # sterzava nel ramo (provato nel simulatore). Ora in alto si guarda solo una finestra
    # attorno alla posizione della linea in basso, cioè la linea che prosegue dritta.
    if TrovAlto and TrovBasso and not (TrovDestro and TrovSinistro):
        xb = cBkBaX + LBanda + 1                 # linea in basso, in coordinate dell'immagine intera
        x0, x1 = max(0, xb - 80), min(RisX, xb + 80)
        TrovFin,(cFinX,cFinY),_,_ = CercaBlocchiCol(Alto[:, x0:x1],"nero",AreaSigBk*0.5)
        if TrovFin and abs((cFinX + x0) - xb) < 70:
            cBkAlX = cFinX + x0
            TrovDestro = TrovSinistro = False    # come un rettilineo: segue la linea dritta
    #Calcolo Errore
    if RwdConf.DEBUG:      # [FIX 10] 6 stampe a ogni fotogramma solo in debug
        print("      ", TrovAlto, "      ")
        print("      ", cBkAlX, "      ")
        print(TrovSinistro,"      ", TrovDestro)
        print(cBkSiX,cBkSiY,"      ", cBkDeX+RisX-LBanda, cBkDeY)
        print("      ", TrovBasso, "      ")
        print("      ", cBkBaX+LBanda, "      ")

    if TrovAlto: #Trovata la linea in alto
        Azione="ALTO"
        if TrovDestro and TrovSinistro:
            if abs(CentroX-cBkAlX) > 80:
                print("Alto Destro Sinistro", (CentroX-cBkAlX) )
                Errore=-1.2*(CentroX-cBkAlX)
                
            else:
                if cBkDeY< cBkSiY and not TrovBasso:
                    print("Sinistro-Destro")
                    #Azione="BusterDx"
                    #Errore=1.4*CentroX
                    Errore=-1.4*(CentroX-cBkAlX)
                elif cBkDeY > cBkSiY and not TrovBasso:
                    print("Destro-Sinistro")
                    #Azione="BusterSx"
                    #Errore=-1.4*CentroX
                    Errore=-1.4*(CentroX-cBkAlX)                    
                else:
                    print("Alto -Sinistro-Destro Basso")
                    Errore=-1.4*(CentroX-cBkAlX)
        else:    
            print("Alto")
            Errore=-(CentroX-cBkAlX)
    elif TrovSinistro or TrovDestro :
        if TrovBasso:                           
            if TrovSinistro and TrovDestro:
                if cBkBaX > CentroX:
                    print("Basso Destro Sinistro -Sinistro")
                    Azione="BusterSx"
                    Errore=-1.4*CentroX
                else:
                    print("Basso Destro Sinistro -Destro")
                    Azione="BusterDx"
                    Errore=1.4*CentroX
            elif TrovSinistro:
                print("Sinistro-Basso")
                Errore=-1.4*CentroX
            else:
                print("Destro-Basso") 
                Errore=1.4*CentroX
        
        else:    
            if TrovSinistro and TrovDestro:
                if cBkDeY< cBkSiY:
                    print("Sinistro-Destro")
                    Errore=1.2*CentroX
                else:
                    print("Destro-Sinistro")
                    Errore=-1.2*CentroX
            elif TrovSinistro:
                print("Sinistro")
                Errore=-CentroX
            else:
                print("Destro")
                Errore=CentroX
    elif TrovBasso: #Alto non trovato   
            print("Basso", ErrPre)
            #Azione="AngoloCeco"
            # [FIX 11] Prima si usava cBkAlX (banda ALTA), che qui vale -1 perché
            # in alto la linea non c'è: l'errore diventava sempre -100 (sterzata
            # massima a sinistra). Ora si usa la banda BASSA, riportata alle
            # coordinate dell'immagine intera (la banda parte da x = LBanda+1).
            Errore=-(CentroX-(cBkBaX+LBanda+1))
    else:
        Azione="Discontinuo"
    Errore=int(Errore/CentroX*100)  # Errore Parametrizzato Maasimo negativo -100 e massimo positivo + 100
    ErrPre=Errore
    #print("Errore: ", Errore)
    return Azione,Errore    

####### ESEMPIO USO FUNZIONI  ########
