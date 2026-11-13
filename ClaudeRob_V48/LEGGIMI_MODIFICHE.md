# ClaudeRob V48 – codice del robot

Ogni modifica nel codice è segnata con un commento `# [FIX n]`.
Per trovarle tutte in Notepad++: **Cerca → Trova nei file → `[FIX`**.

## Prima di tutto: la prova in laboratorio

1. Copiare i 6 file al posto dei vecchi (fare prima un backup della cartella!).
2. I modelli YOLO (`best_ncnn_model_...`) restano dove sono: i nomi non sono cambiati.
3. Lanciare `LetturaNano.py` e controllare che sensori e switch rispondano.
4. Lanciare `RwdFoto.py`. All'avvio compare "Caricamento modelli YOLO…": dura qualche
   secondo, **una volta sola**. Il robot è pronto quando partono le stampe "PAUSA......".

## Elenco delle modifiche

| FIX | File | Cosa cambia | Perché |
|---|---|---|---|
| 1 | WebCam | I 4 modelli YOLO si caricano una volta sola, all'avvio | Prima si ricaricavano dal disco a **ogni fotogramma**: era la causa principale della lentezza |
| 2 | WebCam, DataConf | Foto salvate solo se `SALVA_FOTO = True` | Le scritture su SD a ogni ciclo rallentano e riempiono la scheda. I nomi dei file non hanno più spazi e ":" |
| 3 | RwdFoto | `VelCross` sulle rampe si calcola da `RwdConf.VelCrs` | Prima moltiplicava sé stessa a ogni ciclo e in salita arrivava a 0: gli incroci in rampa non avanzavano |
| 4 | RwdFoto, DataConf | PID seguilinea corretto | Derivata con il segno invertito, Kp applicato due volte, integrale senza limite e mai azzerato |
| 5 | WebCam, DataConf | Comandi della camera scritti con `=` invece di `:` | `ctrl.AeEnable: False` per Python è un'annotazione e **non fa nulla**: la taratura non bloccava l'esposizione |
| 6 | RwdFoto, Robot | `try/finally` con arresto sicuro + `SpegniPWM()` | Se il programma andava in errore, i servo continuavano a girare e il robot "scappava" |
| 7 | RwdFoto, DataConf | Contatori azzerati a ogni nuova accensione dello switch | Prima dopo un riavvio il robot credeva di aver già salvato le palline argentate |
| 8 | Robot, DataConf | `Gira()` con timeout (8 s; nella prima v3 era 4 s e poteva interrompere il dietrofront sul robot vero) | Se il robot si incastrava, girava all'infinito |
| 9 | RwdFoto | Funzione `MascheraAlta()` per le rampe | Lavora su una copia del fotogramma più recente. Prima in alcuni casi analizzava un fotogramma vecchio |
| 10 | tutti | Stampe per ogni ciclo solo se `DEBUG = True` | Le tante `print` via VNC rallentano il ciclo |
| 11 | WebCam | `CalcolaErrore`: caso "solo banda bassa" | Usava la coordinata della banda alta (che valeva -1), quindi l'errore era sempre -100 (sterzata massima a sinistra) |
| 12 | Robot | Tentativi I2C più brevi | Un errore I2C poteva bloccare il robot fino a 1,6 s |
| 13 | Robot, RwdFoto | `Dritto(..., heading_ref=...)` nell'ostacolo | Su ogni lato dell'ostacolo il robot tiene la stessa direzione. Prima ogni piccolo passo ripartiva da zero e gli errori si sommavano |
| 14 | Robot, DataConf | Costanti PID delle rotazioni spostate in `ViennaDataConf.py` | Tutti i parametri da tarare stanno in un solo file |
| 15 | Robot | Commenti degli indirizzi PCA corretti | Erano scambiati (0x40 = braccio, 0x41 = motori) |
| 16 | Robot | `ComandoBluetooth()` "consuma" il comando | Prima restituiva l'ultimo carattere per sempre |
| 17 | Robot | Riconnessione Arduino con `while` invece della ricorsione | Dopo circa 30 minuti senza Arduino Python andava in `RecursionError` |
| 18 | Robot | Nota: `motor_offsets.json` non viene usato | La taratura reale è in `motor_range` |
| 19 | Robot | Spegnere i LED non aspetta più 0,5 s | Tempo perso a ogni cambio di stato |
| 20 | WebCam | `np.int0` → `np.intp` | `np.int0` non esiste in NumPy 2 |
| 21 | RwdFoto | Memoria degli angoli in arena con un dizionario `PosMem` | Prima i numeri delle classi per salvare e per riusare non coincidevano e la memoria non funzionava. Inoltre si gira per l'angolo più breve |
| 22 | RwdFoto | Si aspetta il primo fotogramma prima di partire | Evita un crash se la camera è lenta ad avviarsi |
| 23 | RwdFoto | Commento sui nomi roll/pitch | Nel main "roll" contiene in realtà il beccheggio (salita/discesa) |
| 24 | RwdFoto | Distanza 0 non vale come ostacolo | 0 vuol dire lettura non valida, non "ostacolo a 0 cm" |
| 25 | RwdFoto (`TrovaUscitaIA`) | *(sostituito dal FIX 34 nella V5)* | La vecchia uscita a tempo faceva sbattere il robot contro la parete |
| 26 | RwdFoto (`TrovaUscitaIA`) | Anti-blocco: se cercando l'uscita la direzione cambia meno di 6° in 1,5 s, il robot torna indietro e gira | Incastrato contro lo stipite, il laser frontale centrale guardava attraverso l'apertura e il robot spingeva contro il muro all'infinito |
| 27 | RwdFoto (`OstAutDet`) | Dopo il primo lato 0,9 s invece di 0,5 s; ogni ciclo `while` ha un massimo di 40 passi | Lo spigolo anteriore toccava il blocco (margine 0-5 cm) e il ciclo continuava all'infinito perché il laser non vedeva mai l'ostacolo |
| 28 | RwdFoto (`OstAutDet`, nuova `LineaDavanti`) | La linea viene cercata a ogni passo mentre il robot torna verso la linea | Prima si cercava solo a fine rotazione: se la linea era oltre l'inquadratura il robot ci passava sopra |
| 29 | WebCam (`CalcolaErrore`) | Incrocio a T senza verde: in alto si guarda solo la zona attorno alla linea che prosegue dritta | Il ramo laterale spostava il centro del nero nella banda alta e il robot sterzava nel ramo invece di andare dritto |
| 30 | RwdFoto (`ArenaAI`), DataConf | Correzione finale prima della presa proporzionale allo scarto, con il giroscopio (`GradiPerPixelArena`); niente correzione se la pallina non si vede nella seconda foto | Prima il robot girava sempre 0,3 s a piena potenza (25-39°) anche per 1 cm di scarto: la pallina finiva di lato e la pinza si chiudeva a vuoto (v2: 35 prese mancate su 10 prove, v3: 0) |
| 31 | WebCam (`SalvaFoto`), DataConf | Foto del percorso salvate in `/home/pi/OneDrive/Incroci/` per riaddestrare YOLO: una ogni 0,5 s per classe, subito quando la classe cambia; scrittura in un thread separato; stop automatico se la SD ha meno di 1 GB libero | Servono foto nuove per l'addestramento senza rallentare il robot. I nomi non hanno più ":" (OneDrive non li accetta) |
| 32 | RwdFoto (`Festeggia`), DataConf | All'arrivo sulla linea rossa: LED alternati, braccio che si alza, pinza aperta e chiusa 3 volte (una sola volta per run, ruote ferme) | Festeggiamento richiesto dalla squadra. Tutti i tempi e gli angoli sono in `ViennaDataConf.py` (FESTA_...) |
| 33 | RwdFoto (`InseguitoreIA`, ramo "In"), DataConf | Ingresso in arena: quando vede la striscia argento si ferma, la ricontrolla con una seconda foto e poi entra **dritto** con il giroscopio per `TempoEntrataArena` secondi | Prima entrava con una curva a tempo, non girava abbastanza e prendeva la barriera della stanza |
| 34 | RwdFoto (nuova `EsciDallaPorta`), DataConf | Uscita dall'arena: il robot si mette **perpendicolare al muro** della porta (con il giroscopio, multiplo di 90° rispetto alla direzione di ingresso), poi esce dritto. Se il laser frontale vede il muro scorre lungo la parete finché il laser laterale trova l'apertura | Prima faceva archi a tempo: se arrivava in diagonale o spostato finiva contro la parete |
| 35 | RwdFoto (nuove `SpostamentoPorta`, `CentraSullaPorta`), WebCam, DataConf | Prima di uscire si **centra sulla porta**: arretra, guarda i due stipiti con la camera dell'arena, calcola di quanti cm è spostato, trasla di lato e rimisura (fino a 3 volte) | Nel simulatore, con le vostre misure, il robot arrivava alla porta spostato di 13 cm (fino a 35 se arrivava in diagonale) e lo stipite gli prendeva la fiancata |
| 36 | WebCam (`VerificaVerde`, nuova `VerdiGeometria`), DataConf, nuovo `ProvaVerde.py` | Secondo parere sui verdi: quando YOLO dice Sx, Dx o doppio verde, il codice trova con i colori la linea orizzontale dell'incrocio e i verdi. Vale solo un verde **sotto** la linea nell'immagine (cioè prima dell'incrocio); quelli sopra sono falsi verdi | Nel video dell'8 ottobre, scendendo dal quadrato, il robot gira a sinistra per un verde che sta dopo l'incrocio invece di andare dritto: YOLO l'aveva preso per buono |
| 37 | nuovo `ViennaMonitor.py`, nuova cartella `cruscotto/`, RwdFoto (2 righe), DataConf | Terminale chiaro (eventi tradotti in italiano + pannello fisso con tutti i valori), scatola nera di ogni run, cruscotto web con il robot in 3D per il laboratorio | Il terminale stampava centinaia di numeri al secondo e non si capiva cosa stesse facendo il robot |
| 38 | RwdFoto (`TrovaUscitaIA`, nuove `PerimetroUscita`, `ProvaApertura`, `ControllaApertura`), WebCam (nuova `StrisciaNera`), DataConf | Quando il robot riconosce l'INGRESSO (striscia argento) non torna indietro alla cieca: cerca l'uscita **seguendo i muri** con il laser laterale, controlla ogni apertura con la camera linea, salta l'ingresso ed esce sulla striscia NERA. Il giro dei muri parte anche dopo 45 s di ricerca inutile con la camera o dopo 2 blocchi | Nel video dell'8/10 (arena della scuola, ingresso e uscita sullo stesso muro) il robot tornava 3 volte contro lo stesso punto. Nel simulatore la V7 alla quarta volta usciva dall'ingresso |
| 39 | RwdFoto (`TrovaUscitaIA`, `PerimetroUscita`, nuove `GuardaPavimento`, `EsciSullaStriscia`), WebCam (`StrisciaNera`), nuovo `ProvaStriscia.py` | Mentre cerca l'uscita il robot guarda SEMPRE il pavimento con la camera linea: se passa sopra la striscia nera, anche di sbieco, si mette perpendicolare ed esce | Il robot passava vicino o sopra la striscia nera dell'uscita senza riconoscerla |
| 40 | DataConf | `LarghezzaPorta` 27 cm, `TempoCentroPorta` 0,9 s, `TempoEntrataArena` 1,2 s, `DistanzaCameraArena` 10,5 cm | Misure vere del robot (21,5 × 15 cm, muso a 11,5 cm dalle ruote, laser laterali 10 cm dietro il muso) e delle porte (27 cm) prese dalla squadra il 12/10 |
| 41 | RwdFoto (`CrosDx`, `CrosSx`, `CrosDxIncl`, `CrosSxIncl`, nuove `AvanzaSullIncrocio`, `CompletaSvolta`), WebCam (nuove `DistanzaLineaTrasversale`, `LineaAlCentro`; memoria del falso verde), DataConf | Prima di girare il robot porta il centro delle ruote sopra l'incrocio (velocità misurata dalla camera), gira di 75° e completa finché la linea nuova è davanti al muso | Video del 12/10: all'incrocio prima dell'ingresso dell'arena girava solo di 42°, partendo 11 cm prima dell'incrocio, e tornava sulla linea dritta contro la parete |
| 42 | nuovo `ViennaPannello.py`, Monitor, DataConf | Finestra "ClaudeRob - STATO" in un processo separato con operazione in corso, tutti i sensori ed eventi, aggiornata 5 volte al secondo; da Thonny una riga completa ogni secondo | La squadra voleva tutti i dati sempre visibili e sapere cosa sta facendo il robot |
| 43 | Monitor, `ViennaPannello.py` | Laser fuori portata (valore 0) mostrati come `fuori portata` con l'ultimo valore buono invece di sparire; allarme `ARDUINO NON RISPONDE` se Arduino tace più di 0,3 s (laser e giroscopio a 0), con evento in scatola nera; riga ORA con l'azione delle ruote in italiano e i gradi fatti durante `Gira`; nomi per AvanzaSullIncrocio, CompletaSvolta, PerimetroUscita e le altre fasi nuove |
| 44 | `ViennaClsRobot.py` (Gira), RwdFoto | `Gira` ferma i motori a fine rotazione (prima continuavano a girare a VelCrs durante le pause); angoli che dipendevano dalla rotazione nascosta riscritti in gradi veri; `FotogrammaNuovo()` dopo le rotazioni nella ricerca della linea |
| 45 | DataConf, WebCam, nuovo `TaraNero.py`, ProvaVerde | Soglia di luminosità del nero `SOGLIA_NERO` (prima 80 fisso, ora 110) e taratura sul campo con `TaraNero.py` → `taratura_nero.json` |
| 46 | RwdFoto, WebCam, Monitor | `TrovaIngressoArena` (argento rivisto da fermo, robot in piano, linea che non continua oltre la striscia: `LineaOltreStriscia`), `TrovaUscitaArena`, `EsciControllando` (argento in uscita = ingresso, torna dentro; nero = uscita confermata), `LineaFuori` |
| 47 | Monitor, `ViennaPannello.py` | Riquadro eventi della finestra: tutte le print in tempo reale (grigie) più gli eventi tradotti (a colori), circa 20 righe; tasti `t` (tutti/solo importanti) e spazio (pausa) |
| 48 | RwdFoto, DataConf, Monitor, simulatore | Uscita: `LaserVeri()` (0 = fuori portata = `LASER_LONTANO`, se Arduino risponde) in EsciDallaPorta, PerimetroUscita, TrovaUscitaIA; `AvvicinatiAllaPorta()` guarda il pavimento prima della manovra con i laser (nero = uscita confermata, poi centratura e uscita); tolto VerificaVerde sull'immagine della camera arena; pavimento controllato anche scorrendo lungo la parete; simulatore con laser fuori portata = 0 |
| 49 | `ViennaClsRobot.py` | `_scegli_chip_gpio()`: all'avvio cerca tra tutti i `/dev/gpiochip*` quello con etichetta `pinctrl-rp1` e lo passa a gpiozero (`LGPIOFactory(chip=N)`); necessario dopo l'aggiornamento del 18/10 che ha rinumerato i chip (11–15) |
| 50 | `ViennaClsRobot.py`, `ScattaCalibrazione.py`, nuovo `ProvaGPIO.py` | `CreaLuci()`: luci GPIO22/23 comandate direttamente con lgpio sul chip `pinctrl-rp1` tenuto aperto (gpiozero falliva riaprendolo); ripiego su gpiozero.LED; se niente funziona luci finte con avviso e il robot parte lo stesso |
| 51 | `ViennaPannello.py`, Monitor, DataConf | Camere linea e arena dentro la finestra di stato (JPEG dal monitor 5 volte al secondo, età dell'ultimo fotogramma), `cv2.imshow` delle vecchie finestre disattivato (`FINESTRE_CAMERE`); testi con DejaVu Sans via Pillow (minimo 14 px, grigi più chiari); tasto `m` maschera del nero; terminale senza grigio scuro |
| 52 | RwdFoto, DataConf | `SVOLTE = "vecchie"`: CrosDx/CrosSx/CrosDxIncl/CrosSxIncl come nel codice originale (avanti a tempo + Gira(42)/(-35)/(-37)); "nuove" = FIX 41 |
| 53 | RwdFoto, WebCam, DataConf, Monitor | Uscita costeggiando le pareti: `ScegliLatoGiro`, `AvvicinatiAlMuro`, `GiroDeiMuri` (fianco a LATO_MURO_CM, apertura = salto del laser laterale), `ControllaAperturaMuro` (misura, centro, camera arena con `WebCam.TipoPorta` + pavimento con la camera linea), `GiraA` con nuovo tentativo, `ArduinoVivo`; nel EsciControllando il nero vince sull'argento e l'argento va visto 2 volte |
| 54 | RwdFoto, DataConf | `AccostaTriangolo()` al posto di avanti 1,3 s + indietro 0,4 s prima di SvuotaPinza (`SCARICO_CM`, `RETRO_SCARICO_S`); OstAutDet: `Dis = 999` prima dei cicli "fino a vedere l'ostacolo" (prima `Dis=25` saltava il ciclo con DisTarg=15) e letture con `LaserVeri()` |
| 55 | RwdFoto, DataConf, Monitor | `RobotFermo()`: blocco riconosciuto dal laser frontale che non diminuisce o, con il fronte libero, dall'immagine della camera arena ferma (`FERMO_SOGLIA`); nel giro delle pareti arretra, si stacca dalla parete e riprova guardando il pavimento; apertura riconosciuta anche arrivando in diagonale (parete entro 20 cm poco prima) |
| 56 | RwdFoto, DataConf, Monitor | `ConfermaOstacolo()`: con il laser frontale sotto 15 cm il robot avanza piano (max `OST_TEMPO_CONFERMA` s): laser fino a `OST_CONFERMA_CM` = ostacolo (arretra e `OstAutDet`), beccheggio oltre `OST_RAMPA_GRADI` = rampa (il seguilinea continua). Prima la rampa veniva aggirata come un ostacolo |
| 57 | RwdFoto, DataConf, Monitor | `AttraversaInterruzione()` al posto di sterzata + 0,9 s dritto alla cieca: arretra `GAP_RETRO_S`, si allinea al pezzo dritto prima del vuoto (fitLine sulla parte alta dei pixel neri, rotazioni di 0,7 × l'angolo), poi `Rwd.Dritto` col giroscopio finché rivede la linea (max `GAP_TEMPO_MAX`) |
| 58 | RwdFoto, DataConf, Monitor | `RecuperaLinea()` per il caso "Bi": ventaglio sul posto (`RECUPERO_ANGOLI`) con `GiraVerso` e `VedoLinea`, poi retromarcia a passi (`RECUPERO_RETRO_S`) e secondo ventaglio; mai avanti senza linea. Dopo 2 ricerche fallite resta fermo. `RECUPERO_SICURO = False` = vecchia ricerca |
| 59 | RwdFoto, DataConf, Monitor | `AnalizzaIncrocio()` (bracci della linea sul bordo dell'immagine, pezzi collegati, tratto dritto nero, braccio laterale perpendicolare) e `IncrocioDritto()`: incrocio senza verde attraversato dritto verso il braccio opposto a quello d'arrivo (`INCROCI_DRITTI`, `INCROCIO_DRITTO_S`, `INCROCIO_PAUSA_S`) |
| 62 | RwdFoto, DataConf, Monitor | Con "Di": `SeguiFinoAlVuoto()` (segue il nastro verso la sua parte più lontana fino alla fine; se esce di lato ruota di 15° da quella parte) e `AttraversaVuoto()` (dritto col giroscopio, direzione agganciata ai lati delle piastrelle: `RiferimentoGriglia` misurato alla partenza, `GAP_SCATTO_GRADI`, lato successivo nel verso della curva se `StoricoRotta` dice più di `GAP_CURVA_GRADI_S`). `GAP_SEGUI_FINO_AL_VUOTO = False` = V23 |
| 63 | RwdFoto, DataConf, Monitor | `SeguiParete()` nel giro dei muri: distanza perpendicolare (laser × coseno), angolo verso il muro `PARETE_KP` × errore (max `PARETE_ANGOLO_MAX`), raddrizzamento ruotando sul posto oltre `PARETE_ERR_RUOTA`, stima della direzione vera del muro (`PARETE_STIMA`, max `PARETE_STIMA_MAX`), mediana di 3 letture, max 8°/passo. `LATO_MURO_CM` 5 → 6,5. Porta subito dopo l'angolo. Avanzamento verso un'apertura dubbia fino a 2,5 s | Scatola nera 23/10: muro a 10-30 cm invece di 5; le correzioni di sterzo piccole non fanno girare i servo |
| 64 | Robot, RwdFoto, DataConf | `RuotaVerso()` (rotazione ad anello chiuso col giroscopio, a colpi vicino all'obiettivo) usata da `GiraA`; in `Dritto` niente colpo della derivata al primo giro e raddrizzamento sul posto oltre `DRITTO_RUOTA_GRADI` | A velocità 47 uno sterzo tra -50 e +50 gira di 0-5 °/s; `Gira` finiva 8-14° oltre |
| 65 | Robot, RwdFoto, DataConf, Monitor | Giroscopio come sensore di tocco: rotazione comandata ma direzione ferma per `BLOCCO_S` = "bloccato" (arretra e riprova); nel giro dei muri pitch/roll oltre `PARETE_MAX_INCLINAZIONE` = sta salendo su qualcosa | Prima un robot incastrato aspettava 4 s di timeout |
| 66 | RwdFoto, DataConf, Monitor | `UscitaArenaFatta`: dopo l'uscita una striscia argento confermata (`TrovaIngressoArena(entra=False)`) fa fare dietrofront invece di rientrare (`ARENA_UNA_VOLTA`) | Scatola nera, secondo 596: rientrato nell'arena |
| 67 | DataConf | `VelocitaArenaCmS` 17 → 10 | Velocità misurata sulla scatola nera |
| 68 | DataConf | `TempoEntrataArena` 1,2 → 2,5 s, `TempoUscitaPorta` 1,5 → 2,5 s | A ~11 cm/s il robot entrava di 13-14 cm |
| 69 | RwdFoto, DataConf, Monitor | `EsciDallaPortaDavanti()`: striscia nera davanti durante il giro dei muri → fianco a `PORTA_LATO_CM` dal muro seguito (spostamento laterale se serve), uscita lungo la direzione del muro | Uscita a 8 cm dall'angolo (arena della scuola): il robot sfiorava lo spigolo |
| 70 | RwdFoto, Robot, DataConf | Porta che arriva all'angolo: avanti fino a `PORTA_ANGOLO_CM` dal muro davanti invece di tornare indietro di metà; "Non avanzo" con muro davanti < 20 cm = angolo; "Non avanzo" lontano dagli angoli = arretra, 20° via dal muro e continua a seguirlo; `RobotFermo` non scatta se negli ultimi 2 s la direzione è cambiata di 3° o più; `RuotaVerso` riconosce il blocco anche a colpi | Pista lunga del simulatore: robot incastrato sullo stipite e contro il triangolo, uscita saltata |
| 71 | RwdFoto, DataConf, Monitor | `MemorizzaSvolta()` negli incroci, `DirezioneIngresso()` (svolta appena fatta → linea sotto la striscia → lato delle piastrelle), rotazione verso l'ingresso e `CentraSullIngresso()` (estremità della striscia vista dalla camera linea, `TerrenoDaPixel` con `CAM_LINEA_*`) | Scatola nera 26/10: argento visto a metà curva dopo un incrocio, ingresso storto di 40° |
| 72 | Robot, RwdFoto, DataConf | `RuotaVerso`: continua fino a `RUOTA_ANTICIPO`, assestamento, colpi brevi con pausa; `Gira` si ferma in anticipo (`GIRA_ANTICIPO_S`); `Dritto` non conta il tempo delle rotazioni; correzione verso la pallina con `RuotaVerso` | Giroscopio in ritardo di 0,2 s e 5-7° di rotazione dopo lo stop: correzioni verso la pallina sempre oltre |
| 73 | RwdFoto, Monitor | `OstAutDet`: partenza agganciata alle piastrelle, giri a direzioni assolute con `RuotaOstacolo()` | Arrivando storto da una curva il lato lungo toccava l'ostacolo |
| 74 | RwdFoto, Monitor | `GiraInArena()`: passo indietro, rotazione ad anello chiuso, se bloccata indietro e riprova | Dopo lo scarico il robot spingeva 8 s contro il muro |
| 75 | RwdFoto, DataConf, Monitor | `UltimoArgento` + `IngressoDopoArgento()`: linea finita entro `ARGENTO_RECENTE_S` dall'argento → riprova dell'ingresso | Conferma da fermo fallita: il robot tornava indietro sulla linea |
| 76 | RwdFoto, DataConf, Monitor | Ricerca palline a scatti di `RICERCA_PASSO_GRADI`, giro completo, poi spostamento (`RICERCA_A_SCATTI`) | Ricerca che non copriva tutta l'arena (100 s per la seconda pallina il 23/10) |
| 77 | RwdFoto, Monitor | `AccostaTriangolo`: lontano dal triangolo con un fianco contro il muro → arretra, si stacca, riprova | Pallina caduta 4 cm fuori dal triangolo |
| 78 | WebCam, DataConf, ProvaVerde | `VerdiGeometria`: misura l'INCLINAZIONE della linea dell'incrocio e giudica i verdi lungo quella; oltre `VERDE_ANGOLO_MAX` non giudica; ignora le macchie verdi sottili o sfilacciate (`VERDE_LATO_MIN`, `VERDE_RIEMPIMENTO`) | Scatola nera 29/10: a metà svolta il robot ha rivisto lo stesso incrocio di traverso e i colori hanno contato due verdi "prima della linea"; il bordo scuro del nastro veniva preso per un verde |
| 79 | WebCam, RwdFoto, DataConf, Monitor | I colori non trasformano mai un verde solo in doppio verde; doppio verde visto da lontano → aspetta; `ConfermaDietrofront()` da fermo prima di girare (`DIETRO_CONFERMA`) | Dietrofront sbagliato sulla piastrella con i verdi in diagonale |
| 80 | WebCam, RwdFoto, DataConf | `AvviaPausaVerdi()` alla fine di ogni svolta al verde: per `VERDE_PAUSA_S` lo stesso incrocio non si rivaluta | Il dietrofront del 29/10 è partito 0,2 s dopo la svolta a sinistra, sullo stesso incrocio |
| 81 | RwdFoto, DataConf, Monitor | Ingresso arena solo in piano da `ARENA_PIANO_S` (`InPianoPerArena()`); se avanzando YOLO vede solo la linea l'ingresso si annulla; dopo un falso argento per `ARENA_IGNORA_S` non si ricontrolla (`ScartaArgento()`) | Scatola nera 29/10, secondo 93,6: "ingresso" all'inizio di una rampa e arena avviata sulla rampa |
| 82 | Robot, Monitor, Pannello, cruscotto, DataConf | `Pendenza()`: piano / salita / discesa / inclinato di lato dal giroscopio (mediana di 0,5 s, due soglie); si vede nel terminale, nella finestra di stato, nel cruscotto, nella scatola nera (campo `pend`) e come evento | Richiesta del 29/10: il robot deve capire da solo che è su un tratto inclinato e scriverlo nei dati in tempo reale |
| 83 | RwdFoto, DataConf, Monitor | `ScaricaPalla`: si scarica solo con il triangolo entro `SCARICO_CENTRO_PX` dal centro dell'immagine; se il muro è vicino e il triangolo è di lato, arretra (`SCARICO_ARRETRA_S`) e ruota verso il triangolo | Shuri (pista lunga seme 2): il laser leggeva il MURO accanto al triangolo, pallina lasciata 5 cm fuori, contata come salvata, nera portata prima delle due vive (-1032 punti) |
| 84 | RwdFoto, WebCam, DataConf, Monitor | `SquadraSullUscita()` + `GeometriaStrisciaNera()`: prima di uscire il robot si raddrizza con l'inclinazione della striscia nera e si centra con la sua estremità; in `EsciControllando` se non avanza (`RobotFermo`) arretra, si ricentra e riprova (max 2) | Shuri (giroscopio disturbato 15°): arrivato storto e spostato di 9 cm, lo spigolo contro lo stipite per 100 s, LoP nella zona |
| 85 | RwdFoto, DataConf, Monitor | `AttraversaVuoto`: "sto curvando" anche se negli ultimi 2 s ha girato in tutto più di `GAP_CURVA_TOT_GRADI` | Shuri (contorto seme 1, LoP dalla V25): interruzione dopo una curva a U, rotazione rallentata a 19,6 gradi/s, il robot ha attraversato verso nord sulla fila vicina invece che verso ovest |
| 86 | Monitor | Scatola nera: la versione nel nome del file (`run_AAAA-MM-GG_hh-mm-ss_V29.jsonl`) e nell'intestazione l'impronta del codice (`impronta`, stesso calcolo di Shuri), l'elenco dei file `.py` e la cartella da cui gira | Richiesta del 2/11: riconoscere subito la versione di ogni gara vera e accorgersi se sul robot ci sono file modificati o di versioni diverse |
| 87 | Robot, RwdFoto, DataConf, Monitor | `FrontaleFiltrato()`: laser frontale come mediana pesata sul tempo degli ultimi `LASER_FR_FINESTRA_S`; usata nel seguilinea e in `ConfermaOstacolo`, che a fine controllo con mediana da `OST_FALSO_CM` in su dice "Falso ostacolo" e continua. Scatola nera: campo `dfr` | Scatola nera 03/11: laser frontale che salta (15% di letture con salti oltre 50 cm), due ostacoli finti: una lettura a 5 cm "confermava" l'ostacolo, e senza conferma il robot lo aggirava "per sicurezza" |
| 88 | Robot, DataConf, Monitor | Bussola di riserva: rotta stimata dai comandi dei motori (`GRADI_S_PER_VEL`) quando il giroscopio non cambia mentre il robot ruota (`GIRO_BLOCCATO_GRADI`) o l'Arduino tace; messaggi "GIROSCOPIO BLOCCATO" / "DI NUOVO VIVO"; scatola nera: `bus` e `rotta`; `Dritto` esce con lo switch spento | Scatola nera 03/11: giroscopio fermo a (-2, -2, 0) per tutta la gara, 12 rotazioni finite in TIMEOUT dopo 8 s |
| 89 | Robot | `Pendenza()`: "sconosciuta" con il giroscopio bloccato; si riazzera se l'orologio salta di giorni | Scatola nera 03/11: "in piano" per tutta la gara col giroscopio fermo, "in piano (da 425990 s)" per l'ora corretta da internet dopo l'avvio |
| 90 | RwdFoto, DataConf, Monitor | Ostacolo più furbo: `ScegliLatoOstacolo()` (parete di lato sotto `OST_PARETE_CM`: arretra e si stacca; altrimenti aggira dal lato più libero), `AggiraOstacolo()` (se un lato è chiuso prova l'altro, poi rinuncia), `AvantiOst()`/`Spinge()` (si ferma e arretra se il laser frontale è a `OST_SPINTA_CM`), `RuotaOstacolo` si accorge della rotazione bloccata; `ConfermaOstacolo`: niente ostacolo se la distanza non scende e c'è una parete di lato | Scatola nera 03/11 V30, secondi 81-129: parete a destra presa per ostacolo, giro sempre a destra contro la parete, 5 s di spinta col laser a 4 cm, 48 s persi |
| 91 | DataConf | `VERDE_PAUSA_S` da 3,0 a 1,0 s: la pausa dei verdi dopo una svolta (FIX 80) dura al massimo 1 s | Scatola nera 05/11 (V30), secondi 55-57: alla rotonda il verde dell'uscita (sempre in vista) veniva ignorato per la pausa e il robot andava dritto; nel simulatore la pista della scuola ora si completa |
| 92 | RwdFoto, DataConf | `IncrocioDritto` non interviene per `INCROCIO_DOPO_SVOLTA_S` (2 s) dopo la fine di una svolta al verde (`FineSvoltaVerde`, impostato da `AvviaPausaVerdi`) | Scatola nera 05/11 (V30): mentre il seguilinea finiva la curva "vecchia" da 42 gradi, il robot prendeva lo stesso incrocio per un incrocio senza verde e annullava la svolta (10,7 s: -31 gradi, torna sulla linea lunga invece di scendere; anche 16,3 / 23,9 / 39,9 / 56,9 s) |
| 93 | RwdFoto, Robot | `EntraDallaPorta`: nella porta dell'arena `Dritto(..., ruota=False)` (nuovo parametro di `Dritto`: niente raddrizzamenti sul posto), poi `RuotaVerso` quando il robot è tutto dentro | Scatola nera 05/11 (V33): entrando storto di 8 gradi, il raddrizzamento sul posto dentro la porta portava il retro sinistro (LED) contro lo stipite |
| 94 | RwdFoto, DataConf | Giro dei muri: anticipo degli angoli staccandosi dal muro (`PARETE_ANTICIPO_CM`, `PARETE_ANTICIPO_LATO`) con il laser frontale filtrato; meno soste (`PARETE_ERR_RUOTA` 7, `PARETE_TOLL_RUOTA` 3, `PARETE_PASSO_S` 0,2, `PARETE_VOLUTA_PASSO` 10); rotazione bloccata = arretra; stima del muro sospesa mentre anticipa | Scatola nera 05/11 (V33): 96 s per uscire, 72% del tempo a ruotare sul posto, "Non avanzo" e rotazioni bloccate vicino agli angoli; richiesta del prof di anticipare le girate |
| 95 | RwdFoto, DataConf | Dopo l'arena, alla linea rossa: avanza `AVANZA_ARRIVO_S` e resta fermo finché si spegne lo switch (`FERMO_DOPO_ARRIVO`) | Scatola nera 05/11 (V33): dopo la festa ripartiva e rivedeva l'ingresso 16 volte; Shuri: si fermava prima della piastrella d'arrivo (nel simulatore lunga e contorto ora arrivano: 1893 e 1989) |
| 96 | RwdFoto, DataConf | `EntraDallaPorta` con `AttraversaPorta`: nella porta controlla se il robot si gira da solo (> `ENTRATA_STORTO_GRADI`) o se il laser davanti non si accorcia (< `ENTRATA_AVANZO_MIN_CM` in 0,6 s); se succede arretra, si raddrizza, si sposta di `ENTRATA_SPOSTA_CM` dalla parte opposta al fianco agganciato (`SpostaDiLato`) e riprova (`ENTRATA_TENTATIVI`); sterzo minimo `ENTRATA_STERZO_MIN`; direzione d'ingresso agganciata alle piastrelle fino a `INGRESSO_AGGANCIO_GRADI` (40) | Scatola nera 05/11 15:12 (V34): laser davanti libero ma fianco sinistro agganciato allo stipite (frontale fermo a 93-97 cm, robot girato da solo di 18 gradi); simulatore V31 seme 3: direzione sbagliata di 26 gradi non agganciata (limite 25) |
| 97 | Robot | `Gira` conta quanto ha girato dall'inizio invece di confrontare obiettivo e direzione attuale | `Gira(180)` finiva subito (errore -180 = "già arrivato"): dietrofront mai fatto, robot fermo 23 s (scatola nera 05/11 15:12, 470-493 s) |
| 98 | RwdFoto, DataConf | Dopo l'arena: `VedoLinea` non conta l'argento come linea; un solo dietrofront per l'argento, poi entro `DIETROFRONT_PAUSA_S` lo ignora | Scatola nera 05/11 15:12: dopo l'altalena il ventaglio si è fermato su una striscia argento e il robot è rimasto bloccato davanti |
| 99 | RwdFoto | `StrisciaFerma`: per il confronto solo i campioni vecchi con la striscia nera vista | Scatola nera 05/11 15:52 (V35), 284 s: uscendo dopo un tocco dello stipite il campione vecchio era None → `TypeError` e programma fermo |
| 100 | RwdFoto | `Protetto(fase)` attorno a `InseguitoreIA`, `ArenaAI`, `TrovaUscitaArena` nel ciclo principale: un errore si stampa (scatola nera) e si passa alla fase successiva | Un errore nel codice chiudeva il programma e la gara finiva |
| 101 | RwdFoto, DataConf | `SvoltaAttesa` salva anche il verso della svolta; `IngressoLato` = parte opposta all'ultima svolta; `CercaAperturaDavanti` (laser davanti < `INGRESSO_LIBERO_CM` = muro: cerca l'apertura di lato a passi, prima dalla parte prevista, poi ancora `ENTRATA_OLTRE_CM`); `SpostaDiLato(..., indietro=True)`; nella porta tentativi a +4, +8, -4, -8 cm; "non avanzo" anche col laser cortissimo | Scatola nera 05/11 16:12 (V36): dopo una svolta a destra il robot era a destra della porta (laser davanti 18-20 cm) ma si spostava a destra per un errore di direzione di 4 gradi |
| 102 | Robot, RwdFoto, DataConf | `Rwd.StoriaBeccheggio` (storico del beccheggio dall'Arduino); `ControllaAltalena` nel seguilinea: salto del beccheggio (su di 10, giù di 30 in 1,2 s) = "PROBABILE ALTALENA SUPERATA": fermo, giroscopio stabile, storico rotta cancellato, direzione di prima, ricontrollo linea | Scatole nere 05/11 15:12 e 16:12: dopo l'altalena (da +21 a -49 gradi in 0,7 s) linea persa, rotta sballata, vuoto attraversato verso 89 gradi venendo da 240 |
| 103 | RwdFoto, DataConf, Monitor | `PassaLaPorta` (i tentativi dell'ingresso, ora in comune); `EsciDallaPorta` per l'uscita: avanti senza ruotare, "girato da solo" / "non avanzo" (laser davanti o striscia nera ferma), arretra, si raddrizza, si sposta di lato (+4, +8, -4, -8 cm, prima lontano dal laser laterale più vicino) e riprova (`USCITA_TENTATIVI` 5, `USCITA_EXTRA_RITENTO_S`); se non riesce "bloccato" e giro dei muri | Scatola nera 06/11 10:15 (V37): uscendo il fianco sinistro resta agganciato (91 -> 80 gradi), Dritto ruota sul posto nella porta, poi il seguilinea prende il muro per un ostacolo |
| 104 | RwdFoto, DataConf, Monitor, Pannello | Uscita: `CercaApertura` (ricerca dell'apertura in comune con l'ingresso) in `EsciDallaPortaDavanti` (verso l'interno) e `EsciDallaPorta`, soglia `USCITA_LIBERO_CM` 30, `ScartaNero` + `USCITA_NERO_PAUSA_S`, laser valido solo da dritto, `CERCA_SPAZIO_CM` 22; `EsciSullaStriscia` restituisce l'esito. Ingresso: niente spostamenti da 0 cm, "girato da solo" solo dopo `ENTRATA_RITARDO_STERZO_S`. Altalena: giroscopio "fermo" anche se inclinato. Messaggio "Arduino zitto: switch spento?" | Scatola nera 06/11 10:48 (V38): uscita cercata contro il muro accanto alla porta (laser 13 cm), 2 minuti persi; tentativo d'ingresso da 0 cm; falso "girato da solo" per il ritardo dello sterzo; 2,5 s fermi dopo l'altalena |
| 105 | RwdFoto, Robot, DataConf | `SwitchSpento(dove)`: in tutti i cicli di `ControllaAperturaMuro` e prima di girarsi verso la porta, con lo switch spento ferma i motori ed esce (risposta None); `Rwd.Dritto` con lo switch spento ferma i motori e aspetta al massimo 0,1 s prima di uscire; `VERSIONE` V40 | Rapporto di Shuri 05/11 (V37, `stress_guasti_reali`), riprodotto con la V39 nel simulatore V31: LoP a 417,9 s durante la misura di un'apertura nel giro dei muri, `Dritto` usciva subito e il ciclo girava a vuoto senza mai aspettare: programma piantato. V40: 0 blocchi su 74 prove con lo switch spento, gare normali identiche alla V39 |
| 106 | RwdFoto, DataConf | `AttraversaPorta`: se il laser davanti è lontano (>= `ENTRATA_LONTANO_CM` 60) il controllo "non avanzo" comincia dopo `ENTRATA_LONTANO_ATTESA_S` (1,5 s), confronta con 1,2-1,5 s prima e vuole almeno `ENTRATA_LONTANO_AVANZO_CM` (5 cm); da vicino come prima; `VERSIONE` V41 | Scatola nera 09/11 10:46 (V40), secondi 136-158: 4 falsi "non avanzo" con la porta aperta (laser davanti 101-103 cm, laser sinistro che passa lo stipite), 48 s persi. A 1 m il laser balla di +-2 cm e il cono vede gli stipiti. Nelle 17 scatole nere: 10 "non avanzo" all'ingresso tutti con laser lontano. Simulatore: tutte le prove identiche alla V40 |
| 107 | Monitor, Cabina (nuovo), DataConf | `TERMINALE = "cabina"`: `ViennaCabina.py` disegna la cabina di pilotaggio (laser dall'alto, assetto con storia di 20 s, `Cronometro` dallo switch che conta le LoP e non si azzera fino a `CRONO_NUOVA_GARA_S` 120 s di switch spento, `CRONO_DURATA_S` 480, camere linea e arena a mezzi blocchi a 256 colori, motori e pinza, `Fasi` della gara che vanno solo avanti e contano dopo 3 s, eventi col tempo del cronometro); `ViennaMonitor` la ridisegna ogni 0,2 s, non stampa più gli eventi che scorrono quando è attiva e torna a `"pannello"` se la finestra è sotto 100 x 38 | Il prof (10/11, issue #19): il terminale "non convince"; vuole le camere in piccolo e un cronometro dallo switch. Prova: simulatore identico alla V41; monitor vero con robot finto: cabina 5/s, 1 LoP contata; terminale 80 x 24: torna il pannello |
| 108 | Monitor, Cabina | Una scatola nera per run: a "NUOVA RUN" il file nuovo (e il tempo da 0) solo se lo switch è rimasto spento più di `CRONO_NUOVA_GARA_S` (120 s) o la run non era cominciata; altrimenti è una LoP: stesso file e stesso tempo. `_stop_e_lop`: evento "STOP n" allo spegnimento con l'ultimo campione acceso (stato, laser, rotta, beccheggio, YOLO) ed evento "LoP n: si riparte" alla riaccensione; campo `lop` in ogni campione. Nome dei file invariato. Cabina: camere alte da 8 a 20 righe secondo la finestra | Il prof (10/11): ogni LoP creava una scatola nera nuova; vuole un file per run con le LoP dentro, per capire dove sbaglia il robot. Prova con robot finto: 2 gare = 2 file, la prima con STOP 1, LoP 1, STOP 2 e tempo continuo; simulatore identico alla V41/V42 |
| 109 | DataConf, Monitor | `PANNELLO = False`: la finestra "ClaudeRob - STATO" non si apre più da sola; con `TERMINALE = "cabina"` e `FINESTRE_CAMERE = False` `cv2.imshow` resta spento anche senza la finestra di stato | 12/11, prima accensione della V43: si aprivano cabina e finestra STATO insieme ("partono entrambe"); la cabina ha già tutto |
| 110 | RwdFoto, DataConf | In cima a `RwdFoto.py`, prima di aprire camere, seriale e motori: lucchetto `flock` su `LUCCHETTO` (/tmp/clauderob_robot.lock); se è già preso da un altro programma, avviso con il numero del processo, attesa `LUCCHETTO_ATTESA_S` (20 s) e uscita; `UN_SOLO_PROGRAMMA` per spegnerlo; non nel simulatore | 12/11: sul Raspberry c'erano due avvii automatici (labwc e lxsession con `sleep 30`): due programmi comanderebbero gli stessi motori e la stessa seriale. Prova: il secondo programma esce con l'avviso, il primo continua |
| 111 | RwdFoto, DataConf | `ArenaDavanti()` prima di "Verificata entrata" (in `TrovaIngressoArena` e `IngressoDopoArgento`): mediana delle letture vere (non 0) del laser davanti negli ultimi `ARGENTO_FRONTE_FINESTRA_S` (0,5 s); oltre `ARGENTO_FRONTE_MAX_CM` (150) l'ingresso si annulla con `ScartaArgento`; con il laser fuori portata non blocca. `ARGENTO_DOPO_S` (0 = spento): niente ingresso nei primi N s della run (`Monitor._t_run`, non si azzera con le LoP) | Scatola nera 12/11 10:09 (V43), 93-103 s: falso argento dopo una linea persa, "ingresso" a velocità 68 in mezzo alla pista, discesa di 28 gradi, LoP 2; laser davanti 155-166 cm. Nei 15 ingressi veri delle 18 scatole nere: al massimo 105 cm. Prova sui dati veri: 15 veri entrano, il falso è annullato; simulatore identico alla V44 |
| 112 | `ViennaClsWebCam.py`, `RwdFoto.py`, `ViennaDataConf.py`, `TaraNero.py` | Camera linea a fuoco manuale fisso (se supportato), 20 FPS; all'avvio con LED accesi blocca esposizione/guadagno, scarta 3 fotogrammi, calcola Otsu su 7 fotogrammi e aggiorna `SOGLIA_NERO`; se Otsu è fuori 60-170 usa il valore di riserva di `ViennaDataConf.py`; evento scritto in terminale e scatola nera | La camera linea lavorava a 10 FPS con autofocus continuo; la soglia era tarata a mano e l'esposizione non veniva bloccata con i LED accesi |
| 113 | WebCam, Monitor, Cabina, DataConf | Metadati Lux/ExposureTime/AnalogueGain ogni secondo; controllo vista all'avvio; autoesposizione iniziale e tentativo di blocco per la camera arena | Mancavano una misura della luce e un controllo preliminare delle camere; soglie ed esposizione restano da tarare sul robot |
| 114 | RwdFoto, WebCam, Monitor, TaraNero, DataConf | Unione di V46 (FIX 112) e V47 (FIX 113) in una versione sola. Interruttore `CAM_LINEA_AUTOTARATURA` (True = autotaratura della V46, False = taratura della V45/V47). Il controllo VISTA della V47 parte DOPO la taratura della camera linea (`Monitor.controlli_avvio()`), così usa la soglia vera. Gli eventi dell'avvio (versione, CAMERA LINEA, VISTA, esposizione arena) vanno nell'intestazione di ogni scatola nera (`avvio`) e come eventi "AVVIO: ..." all'inizio della run. Se Otsu non va bene la riserva è la soglia di `taratura_nero.json`, se c'è. `TaraNero.py` usa fuoco fisso e FPS della gara (senza la grafica DOS) | V46 e V47 partivano tutte e due dalla V45: la V47 non aveva il FIX 112. Nella scatola nera V46 del 12/11 17:52 mancava la soglia Otsu: l'evento era nel file dell'avvio, cancellato alla partenza della gara |

## FIX 113 – Lux, controllo vista e camera arena

La V47 aggiunge una verifica delle due camere prima della partenza e registra la luce durante la gara.

- **Metadati:** una volta al secondo legge `Lux`, `ExposureTime` (microsecondi) e `AnalogueGain` sia dalla camera linea sia dalla camera arena.
- **Scatola nera:** aggiunge `lux: [linea, arena]`, `cam_meta` (con i tre valori e il timestamp) e `vista` (esito, testo e dettagli).
- **Cabina:** mostra Lux, esposizione e gain per entrambe le camere. La moviola usa automaticamente la `ViennaCabina.py` dell'ultima versione disponibile.
- **Controllo all'avvio:** attende `CAM_AVVIO_ATTESA_S`, controlla che arrivi un fotogramma da ciascuna camera e segnala immagini quasi completamente nere o bianche. Per la camera linea verifica anche la quota di pixel neri: per questa prova il robot deve essere posizionato sulla linea.
- **Partenza:** il risultato è solo informativo ("VISTA OK" oppure "ATTENZIONE: ..."). Non blocca il robot.
- **Camera arena:** l'autoesposizione può restare attiva durante l'assestamento; poi il programma prova a fissare i valori correnti di esposizione e gain.

**Parametri provvisori in `ViennaDataConf.py`:** `CAM_LUX_MIN`, `CAM_LUX_MAX`, `CAM_NERO_MIN`, `CAM_NERO_MAX`, `CAM_AVVIO_ATTESA_S`, `CAM_ARENA_AUTOESPOSIZIONE`, `CAM_ARENA_BLOCCA_ESPOSIZIONE`, `CAM_VISTA_ABILITATA`. Le soglie attuali sono iniziali, non una taratura definitiva.

### Prove da fare sul robot

1. Con illuminazione normale, registrare i Lux di entrambe le camere.
2. Ripetere con luci spente e con una torcia: annotare Lux, ExposureTime e AnalogueGain.
3. Coprire una camera alla volta all'avvio: deve comparire ATTENZIONE con il nome della camera.
4. Con il robot sulla linea, verificare il controllo del nero; ripetere fuori dalla linea per capire quanto è sensibile la soglia.
5. Aprire la scatola nera con `Strumenti_prove_Claude/terminale_nuovo.py` e verificare che i valori e lo stato siano visibili.
6. Eseguire il confronto nel simulatore con la V45: le gare devono restare identiche.

**Esposizione arena:** non fissare ancora un valore manuale definitivo. Prima raccogliere i metadati con luci normali, spente e torcia; poi scegliere insieme se lasciare l'autoesposizione, bloccarla dopo l'assestamento o usare un'esposizione fissa.

## Novità della V9: l'uscita si riconosce dalla striscia nera

Una sola modifica. Mentre cerca l'uscita, a ogni passo il robot guarda il pavimento sotto il muso con la camera linea.
Se vede la striscia nera, anche presa di sbieco, si gira perpendicolare alla striscia ed esce dritto.
Se la striscia sembra nera ma YOLO dice che è argento, non esce: è l'ingresso.

**Prova da fare subito (2 minuti):** con `RwdFoto.py` spento lanciate `python3 ProvaStriscia.py` e mettete il muso sulla
striscia nera dell'uscita, dritto e di sbieco: deve scrivere `STRISCIA NERA`. Sul bianco e sull'argento deve scrivere `niente`.
Se non la vede, abbassate `STRISCIA_AREA_MIN` in `ViennaDataConf.py` (ora 2500).

## Novità della V8: uscita dall'arena seguendo i muri

**Il problema (video dell'8 ottobre, girava la V5).** Nell'arena della scuola ingresso e uscita sono sullo stesso muro,
separati da un pezzo di parete. Il robot puntava sempre l'ingresso: arrivato lì riconosceva la striscia argento, tornava
indietro, girava e... ritrovava lo stesso ingresso, anche perché si ricordava l'angolo in cui aveva visto la "porta".
Nel simulatore, con lo stesso campo, la V7 fa 3 tentativi contro l'ingresso e al quarto esce proprio dall'ingresso.

**Cosa fa la V8.**
1. Quando riconosce l'ingresso lo segna come scartato e dimentica l'angolo memorizzato della porta.
2. Si mette perpendicolare al muro con il giroscopio, si avvicina, gira di 90° e **segue il muro** a 10 cm con il laser laterale.
3. Agli angoli (o davanti a un triangolo) il laser frontale lo fa girare di 90°.
4. Quando il laser laterale vede un'apertura si ferma a metà, si gira ed entra piano guardando il pavimento con la camera linea:
   striscia **argento** = ingresso, torna indietro e prosegue; striscia **nera** = uscita, esce.
5. Se l'uscita è in fondo al muro che sta seguendo, la riconosce passando sopra la striscia nera.

Il giro dei muri parte anche se con la camera non trova l'uscita entro 45 s (`TempoMaxRicercaPorta`) o se si incastra due volte.

**Da regolare in campo** (`ViennaDataConf.py`, sezione FIX 38):
- `DistanzaMuro` (10 cm): quanto stare lontano dal muro. Se il robot struscia, alzatelo.
- `DistanzaAngolo` (15 cm): quando girare all'angolo. Se tocca il triangolo, alzatelo.
- la striscia nera ora si controlla con `ProvaStriscia.py` (vedi V9).
- `LarghezzaPorta` e `VelocitaArenaCmS`, già presenti, servono a fermarsi a metà dell'apertura.

**Una domanda per voi.** Il controllo "è l'ingresso?" all'arrivo alla porta usa il modello degli incroci (`Cross3`) sulla
foto della camera ARENA. Il modello è stato allenato sulla camera della linea: se all'ingresso il robot a volte non lo
riconosce, la scatola nera lo dirà (evento "Questa è l'INGRESSO" mancante) e conviene usare la camera linea anche lì.

## Novità della V7: terminale, scatola nera e cruscotto 3D

**Come si lancia.** Sempre `RwdFoto.py`, dalla cartella `ClaudeRob_V7` (oppure `./avvia.sh`, che fa la stessa cosa).
Nella cartella devono esserci anche le 4 cartelle dei modelli YOLO (`best_ncnn_model_...`): copiatele dalla versione precedente.

**1. Terminale.** Lanciato da un terminale (LXTerminal, anche via VNC) si divide in due:
- in alto scorrono solo gli **eventi**, in italiano, con orario e colore (giallo incroci, azzurro arena, viola ostacolo,
  rosso errori, verde controllo verde). Esempio: `01:13.2  Incrocio con verde a DESTRA -> giro a destra (sicurezza 0.91)`;
- in basso c'è un **pannello fisso** che si aggiorna 5 volte al secondo: cosa sta facendo il robot (es. `Seguilinea > Aggiro
  l'OSTACOLO > avanzo dritto`), i 3 laser con le barre, rotta/beccheggio/rollio, la classe di YOLO e quante decisioni al
  secondo prende, i fotogrammi al secondo della camera, motori, braccio, pinza, LED, palline salvate, temperatura del
  Raspberry, tensione a 5 V e il **fulmine** (sottotensione) letto direttamente dal Pi 5.

Le stampe ripetute (`Alto`, `Basso`, `Nessun Triangolo`...) non compaiono più: l'ultima resta visibile in fondo al pannello.
Da Thonny (che non è un vero terminale) il pannello diventa una riga riassuntiva ogni 2 secondi.
`TERMINALE = "tutto"` (o `DEBUG = True`) torna a stampare tutto come prima.

**2. Scatola nera.** Ogni run (da quando accendete lo switch) viene registrata in `/home/pi/OneDrive/ScatolaNera/run_<data>.jsonl`:
10 campioni al secondo con stato e sensori, tutti gli eventi, e 2 miniature al secondo delle camere. Una run di 3 minuti
occupa circa 1 MB. Non comunica con niente, quindi **si può tenere accesa anche in gara**: dopo una run sbagliata aprite il
file nel cruscotto e rivedete, secondo per secondo, cosa vedeva e cosa ha deciso il robot.

**3. Cruscotto 3D (solo laboratorio).** Con il robot acceso e collegato alla rete della scuola, dal PC o dal telefono aprite
l'indirizzo che compare nel terminale, tipo `http://192.168.1.23:8000`. Vedete:
- il robot in 3D che ruota e si inclina come dice il giroscopio, con il braccio, la pinza, i LED, i raggi dei 3 laser
  (verdi, gialli sotto 30 cm, rossi sotto 15 cm) e l'area di pavimento che vede la camera linea;
- tutti i valori, le due camere dal vivo, il grafico degli ultimi 30 secondi e gli eventi;
- il menu **Run salvate sul robot** per riaprire una scatola nera, con la linea del tempo (spazio = play, frecce = passo).

La pagina `cruscotto/cruscotto.html` si apre anche da sola sul PC (doppio clic) per rivedere un file della scatola nera
copiato da OneDrive.

**In gara: `CRUSCOTTO = False` e WiFi spento** (`sudo nmcli radio wifi off`). Il regolamento RCJ Rescue (3.2.4) vieta
qualsiasi comunicazione wireless tra robot e dispositivi esterni, VNC compreso.

**Batteria.** Oggi la LiPo non è misurata. Se montate un INA219 sull'I2C (indirizzo 0x44 o 0x45, non 0x40/0x41 che sono
le PCA9685), scrivete l'indirizzo in `BATTERIA_INA219` e compariranno tensione e percentuale.

Il monitor non può fermare il robot: ogni sua parte è protetta e, se qualcosa non va, il robot continua senza.

## Novità della V6

Cambiano `ViennaClsWebCam.py` (FIX 36) e `ViennaDataConf.py` (parametri `CONTROLLO_VERDE` e `VERDE_...`). Nuovo file `ProvaVerde.py`.

**Come funziona il controllo.** Nell'immagine della camera linea il basso è vicino al robot. Il codice cerca la riga
con tanto nero (la linea orizzontale dell'incrocio) e le macchie verdi: un verde sotto quella riga è prima
dell'incrocio e vale, uno sopra è dopo e si ignora. Poi decide: verde valido a sinistra → Sx, a destra → Dx,
tutti e due → doppio verde, nessuno → dritto. Se l'incrocio è troppo in alto o in basso nell'immagine, o non trova
il verde, decide YOLO come prima. Quando cambia la decisione di YOLO stampa una riga che inizia con
`Controllo verde:`.

**Prima della gara, provatelo sulle foto che il robot ha già salvato:**

    python3 ProvaVerde.py

Prende le foto di incroci in `/home/pi/OneDrive/Incroci/`, ricalcola la decisione e scrive le foto disegnate
in `Incroci_ControlloVerde/` (riga blu = linea dell'incrocio, riquadro verde = verde valido, rosso = falso).
Non apre le camere e non muove il robot. Guardate le foto `DIVERSO_...`: se in qualcuna ha torto il controllo,
mandatemele. Se qualcosa non va in gara, `CONTROLLO_VERDE = False` torna al comportamento di prima.

Nel simulatore, facendo sbagliare apposta YOLO sui falsi verdi, la V5 girava all'incrocio 1; la V6 va dritta.
Con YOLO che non sbaglia il controllo non cambia nessuna decisione.

**Per il modello.** Conviene comunque riaddestrare `Cross3` con foto di falsi verdi etichettate come linea normale:
il controllo con i colori è una rete di sicurezza, non sostituisce un modello che sbaglia meno.

## Novità della V5

Cambiano `RwdFoto.py` (FIX 33-35), `ViennaClsWebCam.py` (FIX 35, una riga) e `ViennaDataConf.py` (nuovi parametri).
Il simulatore ora usa **le misure prese dalle vostre foto di calibrazione** (vedi sotto): con queste, sul percorso
completo il robot fa dietrofront, svolta al ritorno, entra in arena, esce dalla porta giusta e arriva alla linea rossa.

Parametri nuovi in `ViennaDataConf.py`, da regolare in campo:

| Parametro | Valore | A cosa serve |
|---|---|---|
| `TempoEntrataArena` | 1.0 s | avanzamento dritto dopo la striscia argento: deve portare **tutto** il robot dentro |
| `DistanzaLiberoPorta` | 35 cm | sopra questa lettura del laser frontale davanti c'è l'apertura |
| `PassiMaxPorta` | 40 | passi da 0,1 s scorrendo lungo la parete prima di rinunciare |
| `TempoCentroPorta` | 1.1 s | avanzamento dopo che il laser laterale vede l'apertura |
| `TempoUscitaPorta` | 1.5 s | avanzamento finale per uscire dall'arena |
| `TempoIndietroPorta` | 1.0 s | retromarcia davanti alla porta, così la camera la vede tutta |
| `LarghezzaPorta` | 30 cm | **misuratela** sul vostro campo: serve per calcolare lo spostamento |
| `TolleranzaPorta` | 3 cm | sotto questo spostamento non si corregge |
| `VelocitaArenaCmS` | 17 cm/s | velocità a `VelArena*0.7`: cronometrate 1 metro (serve solo se il laser non è utilizzabile) |
| `DistanzaCameraArena` | 10 cm | distanza tra il centro di rotazione e la camera dell'arena |

La centratura (FIX 35) usa anche `GradiPerPixelArena`. Dalle vostre foto vale circa **0,30** (va bene il valore attuale).

## Misure ricavate dalle foto di calibrazione (8 ottobre 2026)

- **Camera seguilinea**: alta 83 mm, inclinata **15° in avanti rispetto alla verticale** (quasi a piombo), campo
  orizzontale circa 80°. Inquadra il pavimento da sotto il muso fino a **circa 7,7 cm davanti**, largo circa 14 cm.
  Controllo: il marcatore verde da 2,5 cm risulta di 2,44 cm.
- **Camera arena**: alta 98 mm, inclinata **26° verso il basso**, campo orizzontale circa 68°, circa 1 cm dietro il muso.
  Controllo: con questi valori le palline a 10, 20 e 40 cm cadono nella posizione giusta dell'immagine (scarto sotto 1°).

Le foto sono a 440 x 260 pixel (non a piena risoluzione), ma per la taratura bastano.

## Novità della V3

Cambiano `RwdFoto.py` (FIX 25-28, 30, 32), `ViennaClsWebCam.py` (FIX 29, 31) e `ViennaDataConf.py` (FIX 30-32). Nel simulatore, sul percorso da
15 x 9 piastrelle con falsi verdi, doppio verde, ostacolo e arena, la v3 arriva fino alla linea rossa.
Da provare in campo:
- *(FIX 25: sostituito dal FIX 34 nella V5)*;
- 0,9 s dopo il primo lato dell'ostacolo (FIX 27): deve bastare perché lo spigolo non tocchi il blocco;
- finestra di ±80 pixel attorno alla linea agli incroci a T (FIX 29): controllate che le curve strette
  vengano ancora seguite bene;
- `GradiPerPixelArena` (FIX 30): misuratelo sulla vostra camera dell'arena. Mettete una pallina di lato,
  leggete `centro_x` e l'angolo vero, e calcolate gradi / (centro_x - 112).

## Foto di calibrazione per il simulatore

`ScattaCalibrazione.py` scatta foto a piena risoluzione dalle due camere, con i LED accesi, in
`/home/pi/OneDrive/Calibrazione/`, guidando passo passo su come posizionare il robot.
Servono a tarare il simulatore sul punto di vista vero delle camere.

## ⚠️ Da provare in campo

**PID seguilinea (FIX 4).** Kp e Ki sono stati convertiti nei valori equivalenti
(`Kp=1.21`, `Ki=0.011`), quindi la "forza" della correzione è la stessa di prima.
Il termine **D adesso funziona davvero** (prima peggiorava le oscillazioni), quindi
il robot si comporterà un po' diversamente. Procedura consigliata:
1. Provare con `Kd = 0`, poi `0.05`, poi `0.1`, su un tratto con curve strette.
2. Se oscilla sui rettilinei → abbassare Kp. Se "taglia" le curve → alzare Kp.

**Foto per l'addestramento (FIX 31).** Ora `SALVA_FOTO = True`: ogni gara produce qualche centinaio di foto
in `/home/pi/OneDrive/Incroci/`. Il nome inizia con la classe vista da YOLO (es. `SxCross...jpg`): è
una proposta di etichetta, da controllare prima di usarla per l'addestramento.

**Festeggiamento (FIX 32).** Provatelo prima a robot sollevato: controllate che con il braccio a 100°
e poi a 40° non tocchi la camera o la struttura. Se serve, cambiate `FESTA_BRACCIO_BASSO` e
`FESTA_BRACCIO_ALTO` in `ViennaDataConf.py`; con `FESTA = False` il festeggiamento si disattiva.

**Esposizione della camera (FIX 5).** `BLOCCA_ESPOSIZIONE = False` lascia tutto come
funzionava in gara. Per provare `True`, la taratura (`AutoregolaCam`) va fatta **con i LED
già accesi**. Nel main oggi viene chiamata con i LED spenti: con `True` le immagini
uscirebbero sovraesposte. Se lo provate, spostate la chiamata dopo `GetOnLed1/2`.

**Ostacolo (FIX 13).** Controllare che il robot giri intorno al blocco come prima: ora
mantiene la direzione su ogni lato, quindi dovrebbe essere più preciso.

**Contatori (FIX 7).** Con `AZZERA_CONTATORI_A_OGNI_AVVIO = True` si azzerano a ogni
accensione dello switch. Attenzione al *lack of progress* **dentro l'arena**: se il
robot aveva già portato 1 pallina argentata e viene riacceso, la conterà da capo e
cercherà un'argentata che non c'è più. Decidete voi quale comportamento preferite.

## Domanda aperta per la squadra

Nel modello `best_ncnn_model_TrianFull3`, che numero ha ogni classe? Il codice cerca
la classe **3** per le palline argentate e la **2** per quella nera, ma i vecchi
commenti dicevano "2 = verde, 1 = rosso". Con il FIX 21 la memoria degli angoli
funziona comunque, qualunque sia il numero. Conviene però verificare che
`ScaricaPalla(3)` e `ScaricaPalla(2)` cerchino davvero il triangolo giusto.

## Suggerimenti non applicati (cambiano l'hardware o la taratura)

- Camera della linea: messa a fuoco **manuale** (la distanza dal pavimento è fissa) e 20–30 fps invece di 10.
- Gli spostamenti in avanti sono ancora **a tempo** (`time.sleep`): cambiano con la carica della batteria.
  Dove possibile, usare il laser frontale o la camera come riferimento.
- Codice mai usato che si può spostare in un file a parte: `LeggiCross`, `TrovaUscita`, `GiraPID`, `compute_tilt`.
