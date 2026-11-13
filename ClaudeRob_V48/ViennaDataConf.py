
#####   PID SeguiLinea   ####
# [FIX 4] Prima Kp veniva applicato DUE volte (err_PID*Kp), quindi il guadagno
# reale era Kp*Kp = 1.1*1.1 = 1.21 e Ki reale = 0.01*1.1 = 0.011.
# Ora Kp si applica una volta sola: per mantenere la stessa "forza" di prima
# usiamo direttamente i valori equivalenti. Il termine D aveva il segno
# sbagliato ed è stato corretto: RITARARE Kd IN CAMPO (partire da 0.05).
Kp=1.21
Ki=0.011
Kd=0.05
IntegrMax=1000      # [FIX 4] anti-windup: limite dell'integrale (Ki*IntegrMax = contributo massimo 11)

####   PID rotazioni/Dritto (prima erano scritti fissi dentro ViennaClsRobot.py)
PidGiroKp=1.8
PidGiroKi=0.05
PidGiroKd=0.4

####   VELOCITA' Movimenti  ####
Vel=57
VelCrs=47
VelArena=68
Alfa=0.4

####   VELOCITA' e Precisione Girate

VelMaxGiro=35
ErrMaxGiro=5
TimeoutGira=8.0     # [FIX 8] secondi massimi per una rotazione (se il robot è incastrato non gira all'infinito).
                    # Prima era 4 s: sul robot vero un dietrofront (Gira 170) può durare di più e veniva
                    # interrotto a metà. Se nel terminale compare "[Gira] TIMEOUT" alzate ancora questo valore.

### Variazioni Velocità e Correzione

AlfaVelSal = 0.6
AlfaVelDis = 0.4
AlfaCrosSal = 0.3
AlfaCrosDis = 0.3
AlfaCorSal = 0.5
AlfaCorDis = 0.5

### Costanti Immagine
SogMask=100
# [FIX 30] gradi di rotazione per ogni pixel di scarto nell'immagine 224x224 della camera arena.
# 0,3 = campo visivo di circa 66 gradi diviso 224 pixel. Misuratelo: mettete una pallina di lato,
# leggete centro_x e l'angolo vero, e calcolate gradi / (centro_x - 112).
GradiPerPixelArena = 0.3
# [FIX 33] secondi di avanzamento dritto dopo aver confermato la striscia argento dell'ingresso:
# devono bastare a portare TUTTO il robot dentro l'arena (circa 25 cm). Regolatelo in campo.
TempoEntrataArena = 2.5     # [FIX 68] prima 1.2. Servono circa 29 cm: dal muso alla striscia (~4 cm) + robot lungo
                            # 21,5 cm + margine. 1,2 s andava bene a 24 cm/s, ma la scatola nera del 23/10 dice che
                            # il robot va a circa 11 cm/s: entrava di soli 13-14 cm e restava con il retro fuori.
# [FIX 34] uscita dalla porta dell'arena
DistanzaLiberoPorta = 35    # cm: se il laser frontale legge più di così, davanti c'è l'apertura
# [FIX 48] Il VL53L0X manda 0 quando NON vede niente entro la sua portata (circa 1,2 m): per esempio
# quando guarda fuori da una porta. Nelle funzioni dell'uscita lo 0 ora vale LASER_LONTANO (= lontano),
# non "muro attaccato". Se però Arduino non risponde (tutto a 0 per più di 0,3 s) resta 0.
LASER_LONTANO = 150         # cm
AvvicinamentoPorta = 30     # [FIX 48] cm che il robot percorre verso la porta guardando il pavimento
PassiMaxPorta = 40          # passi da 0,1 s scorrendo lungo la parete prima di rinunciare
TempoCentroPorta = 0.9      # s di avanzamento dopo che il laser laterale vede l'apertura, per centrarsi
                            # [FIX 40] il laser laterale è 10 cm dietro il muso (1,5 cm davanti al centro
                            # delle ruote): per arrivare a metà di una porta da 27 cm servono circa 15 cm
TempoUscitaPorta = 2.5      # s di avanzamento dritto per uscire del tutto dall'arena ([FIX 68] prima 1.5,
                            # stesso motivo di TempoEntrataArena: a 11 cm/s erano solo 16 cm)
# [FIX 35] centratura sulla porta prima di uscire (camera arena + laser frontale)
TempoIndietroPorta = 1.0    # s di retromarcia davanti alla porta: da lontano la camera la vede tutta
LarghezzaPorta = 27         # cm: [FIX 40] MISURATA sul vostro campo (ingresso e uscita)
                            # NB: la centratura usa anche GradiPerPixelArena: tarate quello (vedi sopra)
TolleranzaPorta = 3         # cm: se sono spostato meno di così non correggo
LaserMaxAffidabile = 120    # cm: oltre questa lettura il VL53L0X non è affidabile, uso il tempo
VelocitaArenaCmS = 10       # cm/s a VelArena*0.7. [FIX 67] prima 17: la scatola nera del 23/10 (laser frontale
                            # che si avvicina al muro) dice circa 10 cm/s, e quasi uguale a velocità 34, 47 o 68
                            # (i servo arrivano subito al massimo). Cronometrate 1 metro e correggete.
DistanzaCameraArena = 10.5  # cm tra il centro delle ruote e la camera arena ([FIX 40] muso a 11,5 cm, camera 1 cm dietro)

# [FIX 38] uscita dall'arena seguendo i muri (quando la camera scambia l'ingresso per l'uscita)
TempoMaxRicercaPorta = 45   # s di ricerca con la camera prima di passare al giro dei muri
TempoMaxPerimetro = 70      # s massimi di giro dei muri

### [FIX 53] USCITA COSTEGGIANDO LE PARETI (metodo proposto dalla squadra il 22/10)
# Dopo l'ultima pallina il robot sceglie il lato con la parete più vicina, la costeggia tenendo il fianco
# a LATO_MURO_CM e, quando il laser laterale "cade" in un'apertura, la misura, torna indietro fino al centro,
# si gira e guarda con la camera arena (e con la camera linea il pavimento) se è l'uscita o l'ingresso.
USCITA_MODO = "muri"        # "muri" = questo metodo; "camera" = come prima (camera arena, poi giro dei muri)
LATO_MURO_CM = 6.5          # cm tra il fianco del robot e la parete. [FIX 63] prima 5: idea della squadra
                            # (23/10) tenerla a 6-7 cm. Con 5 cm il robot non ha spazio per girarsi negli angoli
                            # (dal centro delle ruote allo spigolo ci sono circa 14 cm, al fianco 7,8)
APERTURA_CM = 15            # il laser laterale legge più di così, tutto d'un colpo: c'è un'apertura
ANGOLO_CM = 8               # laser frontale sotto questa distanza: angolo o triangolo, giro di 90 gradi
INDIETRO_CAMERA_S = 0.8     # s di retromarcia davanti all'apertura per guardarla con la camera arena
TEMPO_MAX_MURI = 150
### [FIX 63] GIRO DEI MURI A DISTANZA COSTANTE (scatola nera del 23/10: voleva 5 cm, stava a 10-30 cm)
PARETE_KP = 3.0             # gradi di inclinazione verso il muro per ogni cm di errore sulla distanza
PARETE_ANGOLO_MAX = 25      # gradi massimi di inclinazione verso (o via da) il muro
PARETE_ERR_RUOTA = 7        # gradi: se il robot è storto più di così si raddrizza ruotando sul posto
                            # [FIX 94] prima 4: si fermava a ruotare di continuo (05/11: 46 cm in 15 s)
PARETE_TOLL_RUOTA = 3       # [FIX 94] gradi di tolleranza di quelle rotazioni (prima 1,5)
PARETE_PASSO_S = 0.2        # s di avanzamento dritto tra un controllo e l'altro ([FIX 94] prima 0,12)
PARETE_VOLUTA_PASSO = 10    # [FIX 94] gradi massimi di cambio della direzione voluta per passo (prima 8)
PARETE_ANTICIPO_CM = 25     # [FIX 94] laser frontale sotto questa distanza: comincio a staccarmi dal muro...
PARETE_ANTICIPO_LATO = 6    # ...fino a LATO_MURO_CM + tanti cm quando arriva a ANGOLO_CM (poi la svolta di 90 come prima)
FERMO_DOPO_ARRIVO = True    # [FIX 95] arena fatta + linea rossa: il robot resta fermo fino allo spegnimento dello switch
AVANZA_ARRIVO_S = 1.0       # [FIX 95] s di avanzamento dopo aver visto la linea rossa, prima di fermarsi del tutto (~10 cm)
PARETE_STIMA = True         # stima la direzione VERA del muro da come cambia il laser laterale avanzando
                            # (se il giroscopio o la direzione d'ingresso sono sbagliati di qualche grado)
PARETE_STIMA_MAX = 30       # gradi massimi di correzione della direzione dei muri
PORTA_ANGOLO_CM = 4         # [FIX 70] porta che arriva fino all'angolo: il robot si ferma a tanti cm dal muro davanti
                            # (centro a ~15 cm dall'angolo, in mezzo alla porta, con lo spazio per girarsi)
PORTA_LATO_CM = 9.5         # [FIX 69] trovata l'uscita nel muro davanti, prima di uscire si mette con il fianco a
                            # tanti cm dal muro che stava seguendo: passa sia se la porta comincia nell'angolo sia se
                            # comincia 8 cm più in là (arena della scuola)
PARETE_MAX_INCLINAZIONE = 8 # [FIX 65] gradi di pitch/roll: in arena il pavimento è piano, se il giroscopio
                            # vede di più il robot sta salendo su qualcosa (pallina, bordo del triangolo)

### [FIX 64] ROTAZIONI E DRITTO
DRITTO_RUOTA_GRADI = 6      # in Dritto, se il robot è storto più di così si raddrizza ruotando sul posto
                            # (0 = come prima). Le correzioni di sterzo piccole non fanno girare i servo.
VelRuota = 47               # velocità delle rotazioni sul posto brevi (RuotaVerso)
### [FIX 72] ROTAZIONI PRECISE: il giroscopio vede la rotazione 0,2 s dopo il comando e il robot, fermati i
### motori, gira ancora di 5-7 gradi (scatole nere 23 e 26/10)
GIRA_ANTICIPO_S = 0.17      # Gira si ferma quando mancano (velocità di rotazione x 0,17 s) gradi: il resto lo fa
                            # il robot da solo mentre rallenta
INGRESSO_STRISCIA_CM = 25   # [FIX 71] lunghezza della striscia argento dell'ingresso (regolamento: 25 cm)
INGRESSO_TOLLERANZA_CM = 3  # [FIX 71] fuori centro di meno di così: si entra senza spostarsi
INGRESSO_AGGANCIO_GRADI = 40   # [FIX 96] la direzione d'ingresso si aggancia al lato delle piastrelle più vicino
                            # se dista meno di così (prima 25: con 26 gradi di errore il robot entrava storto)
ROBOT_LARGHEZZA_CM = 15.6   # [FIX 96] larghezza del robot (per i commenti: porta ~28 cm, restano ~6 cm per lato)
ENTRATA_TENTATIVI = 5       # [FIX 101] prima 3. [FIX 96] quante volte riprovare la porta se un fianco resta agganciato allo stipite
ENTRATA_SPOSTA_CM = 4.0     # [FIX 101] prima 3: si prova a +4, +8, poi -4, -8 cm. [FIX 96] di quanto spostarsi di lato (lontano dallo stipite) prima di riprovare
ENTRATA_STORTO_GRADI = 8    # [FIX 96] nella porta: se il robot si gira da solo di più di così, un fianco è agganciato
ENTRATA_AVANZO_MIN_CM = 1.5 # [FIX 96] nella porta: se in 0,6 s il laser davanti si accorcia meno di così, non avanzo
ENTRATA_LONTANO_CM = 60     # [FIX 106] laser davanti da qui in su (porta aperta): a ~1 m balla di +-2 cm, controllo più lento
ENTRATA_LONTANO_ATTESA_S = 1.5  # [FIX 106] con davanti lontano, "non avanzo" si controlla solo dopo tanti secondi
ENTRATA_LONTANO_AVANZO_CM = 5.0 # [FIX 106] ... e vuole che in 1,2-1,5 s il laser si sia accorciato almeno di tanto
ENTRATA_STERZO_MIN = 45     # [FIX 96] nella porta lo sterzo corregge almeno con questo valore (sotto ~40 i servo non girano)
CAM_LINEA_AVANTI = 12.0     # [FIX 71] camera linea: cm davanti al centro delle ruote (misure del robot, come nel
CAM_LINEA_ALTEZZA = 8.3     #          simulatore): altezza dal pavimento in cm,
CAM_LINEA_INCLINAZIONE = 15.0   #      gradi in avanti rispetto alla verticale,
CAM_LINEA_HFOV = 80.0       #          gradi di campo visivo orizzontale
ARGENTO_RECENTE_S = 4       # [FIX 75] se la linea finisce entro tanti secondi da quando YOLO ha visto l'argento,
                            # si riprova l'ingresso invece di cercare la linea
RICERCA_A_SCATTI = True     # [FIX 76] ricerca delle palline a scatti fermi con giro completo (False = come prima)
RICERCA_PASSO_GRADI = 30    # [FIX 76] gradi di ogni scatto
SVOLTA_INGRESSO_S = 6       # [FIX 71] se l'argento arriva entro tanti secondi da una svolta a un incrocio, si entra
                            # nella direzione "prima della svolta + 90 gradi"
RUOTA_ANTICIPO = 12         # gradi: sotto questo errore niente più rotazione continua, ma colpi brevi
RUOTA_ASSESTA_S = 0.25      # s di attesa dopo la rotazione continua, per leggere dove è arrivato davvero
RUOTA_PAUSA_S = 0.2         # s di attesa dopo ogni colpo
RUOTA_COLPO_S_GRADO = 0.008 # durata del colpo: 0,008 s per ogni grado che manca (da 0,03 a 0,12 s)
### [FIX 65] GIROSCOPIO COME SENSORE DI TOCCO
BLOCCO_S = 0.6              # s: se il robot deve ruotare ma per tutto questo tempo la direzione cambia
BLOCCO_GRADI = 2            # meno di BLOCCO_GRADI gradi, sta toccando qualcosa (arretra e riprova)
### [FIX 66] DOPO L'USCITA DALL'ARENA
ARENA_UNA_VOLTA = True      # True = dopo essere uscito dall'arena una striscia argento NON fa rientrare:
                            # vuol dire che il robot sta tornando indietro sulla linea, quindi fa dietrofront
FERMO_SOGLIA = 2.0          # [FIX 55] se in 1,5 s l'immagine della camera arena cambia meno di così (media dei
                            # pixel, 0-255) e il giroscopio non si muove, il robot è incastrato

### [FIX 54] SCARICO DELLE PALLINE NEL TRIANGOLO
# Prima il robot arrivava al triangolo e poi tornava indietro di 0,4 s prima di aprire la pinza: la pallina
# cadeva 3-8 cm PRIMA del bordo (simulatore). Ora si accosta piano finché il laser frontale legge SCARICO_CM
# (o finché non avanza più perché tocca il bordo) e lascia la pallina da lì.
SCARICO_CM = 3              # cm tra muso e bordo del triangolo al momento del rilascio
RETRO_SCARICO_S = 0.0       # s di retromarcia prima di aprire la pinza (prima 0.4). Alzatelo SOLO se il
                            # braccio, scendendo, tocca il bordo del triangolo
# [FIX 83] si scarica solo con il triangolo al centro dell'immagine della camera arena (224 pixel di larghezza)
SCARICO_CENTRO_PX = 40      # pixel dal centro (circa 12 gradi): oltre, prima mi giro verso il triangolo
SCARICO_ARRETRA_S = 0.5     # s di retromarcia prima di girarsi verso il triangolo (il muro è vicino)
# [FIX 84] prima di uscire dalla porta il robot si raddrizza e si centra sulla striscia NERA dell'uscita
USCITA_SQUADRA_GRADI = 3    # se la striscia è inclinata di più, prima ruoto (senza fidarmi del giroscopio)
USCITA_TOLLERANZA_CM = 3    # se il centro della porta è più lontano di così, prima mi sposto di lato
USCITA_FERMO_S = 1.2        # uscendo, se la striscia nera resta ferma nell'immagine per questi secondi...
USCITA_FERMO_PX = 4         # ...(entro questi pixel, immagine 440x260) il robot è contro lo stipite
DistanzaMuro = 10           # cm da tenere tra il fianco del robot e il muro
DistanzaAngolo = 15         # cm: laser frontale sotto questa distanza = angolo (o triangolo), giro di 90 gradi
PassiAperturaMax = 30       # passi da 0,1 s per entrare piano in un'apertura cercando la striscia
STRISCIA_AREA_MIN = 2500    # [FIX 39] pixel neri (immagine 224x224) per dire "striscia nera dell'uscita"

# [FIX 41] fine della svolta agli incroci
# [FIX 52] COME GIRA AGLI INCROCI CON IL VERDE
#   "vecchie" = come nel codice originale della squadra: avanti a tempo (0,45 s), poi Gira(42) a destra o
#               Gira(-35) a sinistra, e il seguilinea finisce la curva. Va meglio con gli incroci di forma
#               strana del vostro campo (richiesta del 22/10).
#   "nuove"   = FIX 41: avanza finché le ruote sono sopra l'incrocio, poi ruota finché vede la linea davanti
#               (SVOLTA_BASE, SVOLTA_MAX, DistanzaMusoRuote valgono solo con "nuove").
SVOLTE = "vecchie"
SVOLTA_BASE = 75            # gradi di svolta di base (prima 42 a destra e 35-37 a sinistra)
SVOLTA_MAX = 115            # poi ruota piano finché la linea è davanti, ma mai oltre questi gradi in tutto
DistanzaMusoRuote = 11.5    # cm dal muso al centro delle ruote (MISURATA): il robot gira attorno a quel punto
# taratura della camera linea dalle foto del righello (8/10): servono per sapere a quanti cm è una linea
CAM_LINEA_ALTEZZA = 8.3     # cm da terra
CAM_LINEA_INCL = 75.3       # gradi sotto l'orizzontale (15 gradi dalla verticale)
CAM_LINEA_FY = 266.0        # pixel (immagine 440x260)
CAM_LINEA_OFFSET = -0.5     # cm: la camera è circa mezzo centimetro davanti al muso
SVOLTA_RIGHE_CENTRO = 0.6   # frazione delle righe basse dell'immagine con la linea al centro per dire "linea davanti"

# [FIX 36] secondo parere sui verdi: controlla con i colori che il verde sia PRIMA dell'incrocio
CONTROLLO_VERDE = True      # False = decide solo YOLO, come prima

### [FIX 45] SOGLIA DEL NERO (scala dei grigi)
# Un pixel è "nero" se la sua luminosità V (da 0 = nero a 255 = bianco) è <= SOGLIA_NERO.
# Prima era fissa a 80. Nelle vostre foto di calibrazione dell'8/10 il nastro nero va da V 25 a 105
# (è lucido e fa riflessi al centro dell'immagine) e il bianco da 155 a 198: con 80 si perdeva il
# 17-25% della linea. 110 sta a metà tra i due.
# La luce cambia da un campo all'altro: tarate con  python3 TaraNero.py  (scrive taratura_nero.json,
# che se esiste vale più di questo numero).
SOGLIA_NERO = 110
VERDE_NERO_RIGA = 80        # pixel neri in una riga (immagine 224x224) per dire "qui c'è la linea orizzontale"
VERDE_AREA_MIN = 250        # pixel: macchie verdi più piccole non contano
VERDE_Y_MIN = 45            # si giudica solo se l'incrocio è tra queste due righe dell'immagine:
VERDE_Y_MAX = 175           # più in basso il verde valido potrebbe essere già uscito dall'inquadratura
# [FIX 78] scatola nera 29/10: il robot, girando, ha rivisto lo stesso incrocio DI TRAVERSO e il controllo
# dei colori ha contato due verdi "prima della linea" -> dietrofront sbagliato.
VERDE_ANGOLO_MAX = 20       # gradi: se la linea dell'incrocio è più storta di così i colori non giudicano e decide
                            # YOLO da solo. Sono gradi nell'immagine 224x224, che è schiacciata (440x260 -> 224x224):
                            # 20 qui = circa 12 gradi veri. Con la piastrella della foto del 29/10 girata di 20 gradi
                            # la V26 diceva "Fr" (dietrofront), la V27 non giudica.
VERDE_LATO_MIN = 14         # pixel: una macchia verde più stretta di così è il bordo scuro del nastro, non un verde
VERDE_RIEMPIMENTO = 0.45    # la macchia deve riempire almeno questa parte del suo rettangolo (il quadratino sì,
                            # le frange lungo il nastro no)
# [FIX 79] DIETROFRONT SOLO SE SICURO: i colori devono dire "doppio verde" e da fermo deve riconfermarlo
DIETRO_CONFERMA = True
# [FIX 80] dopo una svolta al verde (destra o sinistra) lo stesso incrocio non si rivaluta. La pausa finisce
# quando la camera ha visto VERDE_PAUSA_FOTOGRAMMI fotogrammi di fila senza verde (l'incrocio è uscito
# dall'inquadratura), e comunque dopo VERDE_PAUSA_S secondi. Dopo un dietrofront niente pausa: nel campo
# contorto il robot torna subito all'incrocio di prima e lì deve girare.
# [FIX 91] 3.0 -> 1.0 s. Scatola nera 05/11 (V30), secondi 55-57: alla ROTONDA il robot entra girando a sinistra,
# 0,2 s dopo YOLO vede già il verde dell'uscita (Sx, sicurezza 0,85) ma per la pausa lo ignora per 1,5 s e
# all'uscita va dritto. Il verde dell'uscita resta sempre in vista, quindi la pausa non finiva mai prima dei 3 s.
# Stesso schema al secondo 7 (verde a destra ignorato per 1,3 s). Nel simulatore con 1,0 s: pista della scuola
# completa (ingresso, arena, uscita, linea rossa; prima non entrava mai) e nessun peggioramento sulle altre piste.
VERDE_PAUSA_S = 1.0
VERDE_PAUSA_FOTOGRAMMI = 4

# [FIX 81] INGRESSO DELL'ARENA SOLO IN PIANO. Scatola nera 29/10, secondo 93: all'inizio di una rampa (beccheggio
# 15) YOLO ha visto l'argento, il robot è "entrato" e ha avviato l'arena sulla rampa.
ARENA_PIANO_GRADI = 8       # beccheggio e rollio sotto questi gradi...
ARENA_PIANO_S = 1.0         # ...da almeno questi secondi
ARENA_IGNORA_S = 3.0        # dopo un falso argento, per questi secondi l'argento non si ricontrolla
ARGENTO_FRONTE_MAX_CM = 150     # [FIX 111] all'ingresso il laser davanti deve vedere l'arena: oltre questi cm è pista (falso
                                #   argento: 12/11 160 cm). Ingressi veri della scuola: al massimo 105 cm (arena 90 cm di
                                #   fondo); l'arena del regolamento è profonda al massimo 120 cm. 0 = controllo spento.
                                #   Contano solo le letture vere: se il laser è "fuori portata" il controllo non blocca
ARGENTO_FRONTE_FINESTRA_S = 0.5 # [FIX 111] mediana del laser davanti su questi secondi
ARGENTO_DOPO_S = 0              # [FIX 111] niente ingresso nei primi N secondi della run (0 = spento: nelle prove vicino
                                #   all'arena l'ingresso vero arriva anche a 6 s). In gara, partendo lontano: es. 30

DIETROFRONT_PAUSA_S = 30    # [FIX 98] dopo l'arena: un solo dietrofront per un argento; se lo rivede entro tanti s lo ignora
INGRESSO_LIBERO_CM = 40     # [FIX 101] girato verso la porta, il laser davanti deve vedere almeno così (il fondo dell'arena);
                            # se vede meno è il muro accanto alla porta: il robot cerca l'apertura spostandosi di lato
ENTRATA_CERCA_PASSO_CM = 4.0    # [FIX 101] passo laterale della ricerca dell'apertura
ENTRATA_CERCA_PASSI = 5         # [FIX 101] passi per parte (prima dalla parte opposta all'ultima svolta)
ENTRATA_OLTRE_CM = 9.0          # [FIX 101] trovata l'apertura, ci si sposta ancora di tanto verso il centro della porta
USCITA_TENTATIVI = 5            # [FIX 103] tentativi per passare la porta d'uscita (poi si torna al giro dei muri)
USCITA_EXTRA_RITENTO_S = 0.6    # [FIX 103] uscita: dopo un ritento si avanza un po' di più (arretrando si perde strada)
USCITA_LIBERO_CM = 30           # [FIX 104] girato verso l'uscita, il laser davanti deve vedere almeno così (uscite vere del
                                # 5 e 6/11: 44-91 cm; il muro accanto alla porta: 13-14 cm); se no cerca l'apertura di lato
USCITA_NERO_PAUSA_S = 6.0       # [FIX 104] striscia nera davanti a un muro: per tanti secondi non la si considera più
ENTRATA_RITARDO_STERZO_S = 0.5  # [FIX 104] "girato da solo" vale solo se lo sterzo spinge nel verso giusto da almeno tanto
CERCA_SPAZIO_CM = 22            # [FIX 104] cercando l'apertura, prima arretra fino ad avere tanto spazio davanti (prima 16)
ALTALENA_ATTIVA = True          # [FIX 102] riconoscere l'altalena dal salto del beccheggio
ALTALENA_SALITA_MIN = 10        # [FIX 102] gradi di muso in su prima della caduta
ALTALENA_SALTO_GRADI = 30       # [FIX 102] di quanti gradi deve calare il beccheggio (05/11: da +21 a -49, cioè 70)
ALTALENA_FINESTRA_S = 1.2       # [FIX 102] ...entro quanti secondi
ALTALENA_STABILE_S = 0.5        # [FIX 102] giroscopio fermo per tanto (beccheggio < 8, rotta entro 3 gradi)
ALTALENA_ATTESA_MAX_S = 2.5     # [FIX 102] attesa massima del giroscopio
ALTALENA_AVANZA_S = 0.4         # [FIX 102] se la linea non si vede, avanza tanto e riguarda
ALTALENA_PAUSA_S = 4.0          # [FIX 102] dopo un'altalena, per tanto non se ne cerca un'altra

# [FIX 82] PENDENZA DAL GIROSCOPIO (si vede nel terminale, nella finestra di stato, nel cruscotto e nella
# scatola nera). Beccheggio > 0 = salita. Il rollio: inclinate il robot a mano verso DESTRA e guardate il
# cruscotto; se scrive "verso sinistra" mettete ROLLIO_POSITIVO_A_DESTRA = not ROLLIO_POSITIVO_A_DESTRA.
PENDENZA_INIZIO = 8         # gradi: oltre questi inizia un tratto inclinato
PENDENZA_FINE = 5           # gradi: sotto questi il tratto è finito (due soglie: niente sfarfallio)
PENDENZA_FINESTRA_S = 0.5   # si usa la mediana degli ultimi 0,5 s (i dossi e le scosse non contano)
PENDENZA_CONFERMA_S = 0.4   # il nuovo stato deve durare almeno così prima di essere annunciato
ROLLIO_POSITIVO_A_DESTRA = False

# [FIX 37] Terminale, scatola nera e cruscotto 3D (ViennaMonitor.py)
VERSIONE = "ClaudeRob V48"  # [FIX 114] unione di V46 (FIX 112, camera linea) e V47 (FIX 113, lux e vista)
PANNELLO = False            # [FIX 42] finestra "ClaudeRob - STATO" con tutti i sensori e l'operazione in corso
                            # [FIX 109] dalla V44 spenta: la cabina del terminale (FIX 107) ha già tutto, camere comprese.
                            # True = si apre anche lei (per vedere le camere grandi)
FINESTRE_CAMERE = False     # [FIX 51] le due camere ora sono DENTRO la finestra di stato e non si bloccano più.
                            # True = si aprono ANCHE le vecchie finestre 'Linea' e 'Arena' di OpenCV
                            # (quelle si aggiornano solo quando il programma se ne ricorda)
RIGA_OGNI = 1.0             # [FIX 42] da Thonny: una riga con tutti i valori ogni quanti secondi
TERMINALE = "cabina"        # [FIX 107] "cabina" = CABINA DI PILOTAGGIO a riquadri (ViennaCabina.py): laser, assetto,
                            #   cronometro, le due camere in piccolo, motori, fasi della gara, eventi. Serve una finestra
                            #   di almeno 100 x 38 caratteri (in VNC ingranditela): se è più piccola si usa "pannello"
                            # "pannello" = eventi chiari in alto + pannello fisso in basso con tutti i valori
                            # "semplice" = solo eventi + una riga riassuntiva ogni 2 s (per Thonny)
                            # "tutto"    = stampa tutto come prima (lo fa anche DEBUG = True)
UN_SOLO_PROGRAMMA = True    # [FIX 110] un secondo programma del robot non parte se uno sta già girando
LUCCHETTO = "/tmp/clauderob_robot.lock"   # [FIX 110] il file del lucchetto (si libera da solo quando il programma finisce)
LUCCHETTO_ATTESA_S = 20     # [FIX 110] il secondo programma lascia il messaggio sullo schermo per tanti secondi, poi esce
CRONO_DURATA_S = 480.0      # [FIX 107] cronometro della cabina: 8 minuti di gara (dalla prima accensione dello switch)
CRONO_NUOVA_GARA_S = 120.0  # [FIX 107] switch spento più di così: la prossima accensione fa ripartire il cronometro da 0
                            #   (con spegnimenti più corti è una LoP: il cronometro va avanti e conta le LoP)
SCATOLA_NERA = True         # registra ogni run in CARTELLA_SCATOLA (permesso in gara: non comunica con niente)
CARTELLA_SCATOLA = "/home/pi/OneDrive/ScatolaNera/"
SCATOLA_FOTO = True         # nella scatola nera anche le miniature delle camere (2 al secondo)
CRUSCOTTO = True            # SOLO LABORATORIO: pagina web 3D su http://<ip-del-robot>:8000
                            # IN GARA: CRUSCOTTO = False e WiFi spento (regolamento RCJ Rescue 3.2.4)
PORTA_CRUSCOTTO = 8000
BATTERIA_INA219 = None      # indirizzo I2C dell'INA219 se lo montate (es. 0x45; NON 0x40/0x41: sono le PCA9685)
BATTERIA_CELLE = 3          # LiPo 3S = 11,1 V

# [FIX 113]- metadati e controllo vista (soglie provvisorie da tarare sul robot)
CAM_METADATI_INTERVALLO_S = 1.0
CAM_LUX_MIN = 10.0
CAM_LUX_MAX = 10000.0
CAM_NERO_MIN = 0.005
CAM_NERO_MAX = 0.65
CAM_AVVIO_ATTESA_S = 1.5
CAM_ARENA_AUTOESPOSIZIONE = True
CAM_ARENA_BLOCCA_ESPOSIZIONE = True
CAM_VISTA_ABILITATA = True

### [FIX 2/10] Interruttori per gara e debug
DEBUG = False               # True = stampa a ogni ciclo (utile in laboratorio, lento in gara)
### [FIX 31] Foto del percorso per riaddestrare la rete neurale (YOLO)
SALVA_FOTO = True           # True = salva le foto del percorso (le scrive un thread separato: il robot non rallenta)
CARTELLA_FOTO = "/home/pi/OneDrive/Incroci/"   # la stessa cartella usata prima per l'addestramento
FOTO_INTERVALLO = 0.5       # secondi minimi tra due foto della STESSA classe (Ln, Sx, Fr, PALLE...).
                            # Quando la classe cambia (es. da Ln a Sx) la foto si salva subito: sono le più utili.
FOTO_SPAZIO_MINIMO_MB = 1000   # se sulla SD restano meno di 1 GB liberi il salvataggio si ferma da solo

### [FIX 32] Festeggiamento all'arrivo sulla linea rossa
FESTA = True
FESTA_LAMPEGGI = 6          # quante volte i due LED si alternano all'inizio
FESTA_TEMPO_LED = 0.2       # secondi (i LED sono su relè: non scendere sotto 0,1 s)
FESTA_BRACCIO_BASSO = 100   # il braccio parte da qui...
FESTA_BRACCIO_ALTO = 40     # ...e si alza fino a qui (40 = braccio alzato, come in AlzaPinza)
FESTA_PINZA_APERTA = 160    # stessi valori di ApriPinza / ChiudiPinza
FESTA_PINZA_CHIUSA = 98
FESTA_PINZA_VOLTE = 3       # apri-chiudi della pinza

### [FIX 5] Taratura generica delle altre camere
# Per la camera linea V46 si usano i parametri dedicati qui sotto:
# l'esposizione viene bloccata dopo l'assestamento automatico con i LED accesi.
BLOCCA_ESPOSIZIONE = False

### [FIX 112] CAMERA LINEA: fuoco, frequenza e autotaratura all'avvio
# La camera è a circa 8,3 cm dal pavimento: 1/distanza = circa 12 diottrie.
# Picamera2 usa LensPosition in diottrie; il codice limita il valore al range
# realmente dichiarato dalla camera (alcuni moduli non arrivano a 8,3 cm).
# [FIX 114] INTERRUTTORE dell'autotaratura (feature flag): True = V46 (LED accesi, esposizione bloccata, soglia Otsu
# all'avvio del programma); False = come V45/V47 (esposizione automatica, soglia da taratura_nero.json o SOGLIA_NERO).
# Per tornare del tutto alla camera della V47: CAM_LINEA_AUTOTARATURA = False, CAM_LINEA_FUOCO_MANUALE = False, CAM_LINEA_FPS = 10.
CAM_LINEA_AUTOTARATURA = True
CAM_LINEA_FUOCO_MANUALE = True
CAM_LINEA_FUOCO_CM = 8.3
CAM_LINEA_FPS = 20
# Prima si accendono i LED, si lascia assestare l'esposizione automatica,
# poi si blocca esposizione e guadagno prima di misurare la soglia Otsu.
CAM_LINEA_BLOCCA_ESPOSIZIONE = True
CAM_LINEA_ASSESTAMENTO_S = 1.5
CAM_LINEA_FOTOGRAMMI_OTSU = 7
CAM_LINEA_SOGLIA_MIN = 60
CAM_LINEA_SOGLIA_MAX = 170
CAM_LINEA_PIXEL_MIN_OTSU = 200

### [FIX 56] Ostacolo o rampa?
# Quando il laser frontale legge meno di 15 cm il robot avanza piano e decide:
OST_CONFERMA_CM = 8         # il laser scende fino a qui = ostacolo vero (una rampa da 20-25° non ci arriva mai)
OST_RAMPA_GRADI = 6         # il robot si inclina più di così = rampa (le ruote davanti stanno salendo)
OST_VEL_CONFERMA = 30       # velocità con cui avanza mentre controlla
OST_TEMPO_CONFERMA = 1.5    # secondi massimi di controllo (poi, per sicurezza, è un ostacolo)
### [FIX 87] Laser frontale filtrato (scatola nera 03/11: letture che saltano, ostacoli finti)
LASER_FR_FINESTRA_S = 0.3   # s: mediana delle letture del laser frontale in questo tempo
OST_FALSO_CM = 15           # finito il controllo, se la mediana del laser è da qui in su NON è un ostacolo
### [FIX 88] Bussola stimata quando il giroscopio è bloccato o l'Arduino tace (scatola nera 03/11)
BUSSOLA_STIMATA = True      # False = come prima (rotta 0 se il giroscopio non risponde)
GRADI_S_PER_VEL = 0.74      # gradi/s di rotazione sul posto per ogni punto di velocità (35 a vel 47, 50 a vel 68)
STIMA_CURVA = 0.5           # in curva (sterzo non ±100) la rotazione stimata è sterzo x GRADI_S_PER_VEL x questo
GIRO_BLOCCATO_GRADI = 60    # i motori girano il robot di tanti gradi e il giroscopio non cambia = bloccato
### [FIX 90] Ostacolo più furbo: pareti ai lati, niente spinte (scatola nera 03/11 V30)
OST_PARETE_CM = 18          # laser laterale sotto questa distanza = parete accanto al robot
OST_STACCO_GRADI = 20       # con una parete di lato: arretra e si gira di tanto verso la parte libera (poi 40, 60 se ci ricade)
OST_STACCO_RIPROVA_S = 8    # se entro questo tempo è di nuovo davanti a qualcosa, è un ostacolo vero
OST_LATO_LIBERO_CM = 30     # se a destra c'è meno spazio di così (e a sinistra di più) aggira a sinistra
OST_SPINTA_CM = 5           # laser frontale (filtrato) fino a qui mentre avanza = sta spingendo contro qualcosa
OST_SPINTA_ARRETRA_S = 0.5  # quanto arretra quando si accorge che spinge
OST_ROTAZIONE_TOLL = 25     # rotazione dell'ostacolo rimasta a più di tanti gradi dall'obiettivo = bloccata

### [FIX 57] Interruzioni della linea
GAP_RETRO_S = 0.35          # s di retromarcia prima di allinearsi (la camera vede il pezzo dritto prima del vuoto)
GAP_TEMPO_MAX = 2.0         # s massimi di dritto col giroscopio sopra il vuoto (circa 25-30 cm)

GAP_SEGUI_FINO_AL_VUOTO = True   # [FIX 62] True = segue il nastro fino al vuoto e poi lo attraversa (AttraversaVuoto)
                                 # False = si ferma appena YOLO vede "Di" (AttraversaInterruzione, V23)
GAP_AVVICINA_S = 2.0        # [FIX 62] s massimi per seguire il nastro fino alla sua fine
GAP_NERO_MIN = 300          # [FIX 62] pixel neri sotto i quali il nastro è finito (il vuoto è sotto il muso)
GAP_CURVA_GRADI_S = 25      # [FIX 62] sopra questa velocità di rotazione il robot "sta curvando": vale il lato successivo nel verso della curva
GAP_CURVA_TOT_GRADI = 45    # [FIX 85] ...oppure se negli ultimi 2 s ha girato in tutto più di così (curva a U che rallenta)
GAP_SCATTO_GRADI = 42       # [FIX 62] entro questi gradi da un lato delle piastrelle attraversa il vuoto in quella direzione esatta (sotto 45: la direzione più vicina è quella giusta)

### [FIX 58] Linea persa: ricerca sicura (mai avanti alla cieca)
RECUPERO_SICURO = True      # False = vecchia ricerca (gira 25° e 50° e poi va avanti)
RECUPERO_ANGOLI = (-30, 30, -60, 60, -90, 90, -120, 120)   # gradi del ventaglio, rispetto a dove l'ha persa
                            # (fino a 120°: dopo un angolo acuto la linea riparte quasi all'indietro)
RECUPERO_RETRO_S = 1.0      # s massimi di retromarcia a piccoli passi sulla strada già fatta

### [FIX 59] Incroci senza verde: si attraversano dritti
INCROCI_DRITTI = True       # False = come prima (il PID segue il baricentro del nero)
INCROCIO_DRITTO_S = 0.7     # s di dritto col giroscopio per superare l'incrocio
INCROCIO_PAUSA_S = 2.0      # s dopo un incrocio in cui non se ne cerca un altro
INCROCIO_DOPO_SVOLTA_S = 2.0  # [FIX 92] dopo una svolta al verde, per tanti secondi niente "incrocio senza verde: dritto"

### [FIX 7] Contatori della gara
# True  = a ogni nuova accensione dello switch si azzerano palline salvate e posizioni.
# False = i contatori restano (utile se dopo un "lack of progress" in arena
#         il robot deve ricordarsi quante palline ha già portato).
AZZERA_CONTATORI_A_OGNI_AVVIO = True
