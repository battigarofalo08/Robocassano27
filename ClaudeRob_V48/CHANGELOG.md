# ClaudeRob – Changelog

Robot RoboCup Junior Rescue Line – IISS "Erodoto di Thurii", Cassano allo Ionio
Versione di lavoro: **ClaudeRob V46** (12 novembre 2026; in verifica)

Questo file riassume, versione per versione, cosa è cambiato e perché. Il dettaglio tecnico di ogni
modifica è in `LEGGIMI_MODIFICHE.md`: ogni correzione è numerata (FIX 1 … FIX 112) e nel codice è
segnata con un commento `# [FIX n]`, così si ritrova subito con "Cerca" in Notepad++.

Il programma da lanciare è sempre `RwdFoto.py` dalla cartella `ClaudeRob_V46` (oppure `./avvia.sh`).
Nella cartella vanno copiate anche le 4 cartelle dei modelli YOLO (`best_ncnn_model_...`), che non
sono nello zip.

---

## In breve

| Versione | Cosa risolve |
|---|---|
| V1 | Codice originale della squadra |
| V2 | Robot più veloce e più sicuro: YOLO caricato una volta sola, PID corretto, motori che si fermano sempre |
| V3–V4 | Uscita dall'arena, ostacolo, incroci a T, presa delle palline, foto per l'addestramento, festeggiamento |
| V5 | Dietrofront completo, ingresso in arena dritto, uscita perpendicolare alla porta, camere misurate |
| V6 | Controllo dei falsi verdi con i colori |
| V7 | Terminale leggibile, scatola nera, cruscotto 3D per il laboratorio |
| V8 | Uscita dall'arena seguendo i muri (arena della scuola) |
| V9 | Uscita riconosciuta dalla striscia nera sotto il muso, anche presa di sbieco |
| V10 | Misure vere del robot e delle porte nei calcoli di ingresso e uscita |
| V11 | Svolte agli incroci complete: il robot gira sopra l'incrocio e finisce la curva |
| V12 | Finestra di stato con tutti i sensori e l'operazione in corso, sempre aggiornata |
| V13 | Laser che non spariscono più durante le svolte, riga ORA con l'azione delle ruote, allarme Arduino |
| V14 | Gira si ferma davvero, soglia del nero tarabile, ingresso e uscita dell'arena con controllo delle strisce |
| V15 | Nella finestra di stato tutti gli eventi in tempo reale |
| V16 | Uscita dall'arena: prima il pavimento (striscia nera), poi i laser; laser a 0 = lontano |
| V17 | Il robot riparte dopo l'aggiornamento del Raspberry: trova da solo il chip dei GPIO |
| V18 | Luci comandate direttamente con lgpio (gpiozero non apriva il chip); il robot non si blocca mai per le luci |
| V19 | Finestra di stato più leggibile e con le due camere dentro, sempre aggiornate |
| V20 | Svolte agli incroci come nel codice originale; uscita dall'arena costeggiando le pareti (metodo della squadra) |
| V21 | Palline dentro i triangoli, ostacolo corretto, robot che si accorge di essere incastrato |
| V22 | La rampa non viene più scambiata per un ostacolo |
| V23 | Seguilinea che non cade e non sbaglia: interruzioni, linea persa, incroci senza verde |
| V24 | Interruzioni subito dopo una curva o una curva a U |
| V25 | Arena: giro dei muri a 6-7 cm, rotazioni precise, ingresso completo, uscita vicino all'angolo, niente secondo ingresso |
| V26 | Ingresso in arena dritto e centrato anche subito dopo un incrocio, palline prese dritte, ricerca palline a scatti, ostacolo a squadra |
| V27 | Niente dietrofront sbagliati con i verdi in diagonale, niente ingresso in arena su una rampa, pendenza dal giroscopio nei dati in tempo reale |
| V28 | Correzioni dalla prima batteria di Shuri: pallina sempre dentro il triangolo, uscita dritta e centrata anche con il giroscopio disturbato, interruzione dopo una curva a U |
| V29 | Scatola nera con la versione nel nome del file e l'impronta del codice (per gli strumenti di Shuri) |
| V30 | Niente ostacoli finti con il laser frontale disturbato; bussola di riserva quando il giroscopio si blocca o l'Arduino tace |
| V31 | Ostacolo più furbo: si stacca dalle pareti, aggira dal lato libero, non spinge più contro i muri |
| V32 | Alla rotonda gira all'uscita: la pausa dei verdi dopo una svolta dura 1 s invece di 3 |
| V33 | Le svolte al verde non vengono più annullate da "Incrocio senza verde: lo attraverso dritto" |
| V34 | Entra dalla porta senza toccare gli stipiti, giro dei muri più svelto che anticipa gli angoli, si ferma sulla linea rossa |
| V35 | Nella porta dell'arena si accorge del fianco agganciato e riprova spostato; dietrofront (Gira 180) che gira davvero; dopo l'arena l'argento non blocca più |
| V36 | Uscendo dall'arena niente più errore TypeError; un errore nel codice non chiude più il programma a metà gara |
| V37 | Davanti alla porta si sposta dalla parte giusta (opposta all'ultima svolta) e cerca l'apertura col laser; riconosce l'altalena |
| V38 | La porta d'uscita si passa con lo stesso sistema dell'ingresso: fianco agganciato, arretra, si sposta e riprova |
| V39 | Uscita: col laser capisce se davanti c'è il muro e cerca la porta di lato; ingresso senza tentativi sprecati; altalena più svelta |
| V40 | Con lo switch spento (LoP) il programma non si pianta più nel giro dei muri |
| V41 | Ingresso: niente più retromarce inutili quando il robot sta entrando dalla porta aperta |
| V42 | Terminale "cabina di pilotaggio": laser, assetto, cronometro dallo switch, le due camere in piccolo, fasi della gara |
| V43 | Una scatola nera per ogni run, con le LoP dentro; camere della cabina più grandi con la finestra grande |
| V44 | Solo la cabina nel terminale (finestra STATO spenta); un secondo programma del robot non parte se uno sta già girando |
| V45 | Niente "ingresso" in mezzo alla pista: davanti alla porta vera il laser deve vedere l'arena |
| V46 | Camera linea: fuoco manuale fisso (se supportato), 20 FPS, esposizione bloccata con LED accesi e soglia del nero calcolata da Otsu all'avvio |

---

## V45 – 12 novembre 2026

**Da dove viene:** scatola nera del 12/11 ore 10:09 (`run_2026-11-12_10-09-51_V43.jsonl`), secondi 93-103 (LoP 2). Dopo
una svolta al verde il robot perde la linea; YOLO scambia un bordo scuro per la striscia argento ("In"); i controlli
dell'ingresso passano (la centratura dice "striscia non vista", ma va avanti lo stesso) e il robot "entra" a velocità 68
in mezzo alla pista: scende da una discesa di 28 gradi. In quel momento il laser davanti misurava **155-166 cm**.

Il prof proponeva di non accettare l'argento troppo presto dopo la partenza. Nelle 18 scatole nere però l'ingresso vero è
arrivato anche a 6, 13, 17, 24 s (prove partite vicino all'arena) e i falsi argenti cadono negli stessi tempi: una soglia
sul tempo, da sola, bloccherebbe ingressi veri. Il segnale buono è il **laser davanti**: nei 15 ingressi veri, quando il
robot decide di entrare, misura **al massimo 105 cm** (dietro la porta c'è l'arena, 90 cm di fondo).

**FIX 111 – davanti alla porta ci deve essere l'arena** (`ArenaDavanti` in `RwdFoto.py`, chiamata prima di "Verificata
entrata" in `TrovaIngressoArena` e in `IngressoDopoArgento`). Mediana delle letture **vere** (non 0) del laser davanti
nell'ultimo mezzo secondo: se è oltre `ARGENTO_FRONTE_MAX_CM` (150: l'arena del regolamento è profonda al massimo 120 cm)
lì non c'è l'arena e l'ingresso si annulla ("Ingresso ANNULLATO: il laser davanti vede libero fino a ... cm"); il robot
continua a seguire la linea. Se il laser è "fuori portata" il controllo non blocca (non si sa cosa c'è). In più
`ARGENTO_DOPO_S` (spento di base, 0): niente ingresso nei primi N secondi della run, contati dal cronometro della V43 che
non si azzera con le LoP. In gara, partendo lontano dall'arena, si può accendere (per esempio 30).

### Prove

| Prova | V44 | V45 |
|---|---|---|
| Le letture vere del laser davanti nei 17 ingressi delle scatole nere | – | **15 veri su 15: entra**; falso del 12/11 a 99,9 s: **annullato** (166 cm) |
| Simulatore V32: scuola semi 1-2, rcj2026, lunga, contorto, arena_parete, gara, scuola_nuova semi 1-2 | arrivo | **identiche campione per campione** |
| Simulatore con falso argento (`yolo_argento_falso`) su scuola_nuova e rcj2026 | arrivo | identiche (nel simulatore il laser arriva a 120 cm: il controllo non blocca) |

Limite del simulatore: il suo laser arriva solo a 120 cm, quindi il caso del 12/11 (166 cm) si prova solo con i dati veri.

Impronta del codice V45: `c6bb6bcc58a393e3`.

---

## V46 – 12 novembre 2026 (issue #28, Battista)

**Obiettivo:** rendere più stabile la visione della linea quando cambia l'illuminazione, senza tarare a mano la soglia a ogni avvio.

**FIX 112 – camera linea e autotaratura.** `ViennaClsWebCam.py` prova a impostare il fuoco manuale alla distanza configurata (8,3 cm, cioè circa 12 diottrie), limitandolo al range dichiarato dalla camera; se il controllo non è disponibile, conserva un ripiego e lo segnala. La camera linea viene impostata a 20 FPS. All'avvio del robot, `RwdFoto.py` accende i due LED, lascia assestare l'esposizione automatica, blocca esposizione e guadagno, quindi raccoglie 7 fotogrammi e calcola Otsu sul canale V dei pixel poco saturi (stessa impostazione di `TaraNero.py`). Se la soglia non è calcolabile o non rientra tra 60 e 170, usa `SOGLIA_NERO` da `ViennaDataConf.py`. Il valore scelto aggiorna sia `ViennaClsWebCam` sia `ViennaDataConf`, ed è registrato come evento nel terminale e nella scatola nera. Nel simulatore l'autotaratura viene saltata e resta il valore di configurazione, per non rendere casuale il confronto con V45.

**Parametri nuovi:** `CAM_LINEA_FUOCO_MANUALE`, `CAM_LINEA_FUOCO_CM`, `CAM_LINEA_FPS`, `CAM_LINEA_BLOCCA_ESPOSIZIONE`, `CAM_LINEA_ASSESTAMENTO_S`, `CAM_LINEA_FOTOGRAMMI_OTSU`, `CAM_LINEA_SOGLIA_MIN`, `CAM_LINEA_SOGLIA_MAX`, `CAM_LINEA_PIXEL_MIN_OTSU` (tutti in `ViennaDataConf.py`, letti con `getattr`).

Impronta dei file Python V46 (stesso calcolo della scatola nera): `30a9184c711f80b0`.

### Verifiche disponibili in questa consegna

- [x] Controllo sintattico dei file Python modificati.
- [x] Prova dell'algoritmo Otsu su immagini sintetiche con separazione nero/bianco e prova del ripiego fuori intervallo.
- [ ] Sul robot vero: almeno 3 condizioni di luce (luci accese, luci spente con finestra, torcia laterale); annotare soglia, esposizione e fuoco effettivi.
- [ ] Verificare che il fotogramma della camera linea sia nitido alla distanza reale; il valore di fuoco è limitato ai controlli disponibili sul modulo.
- [ ] Simulatore V32: scuola semi 1-2, `rcj2026`, `scuola_nuova` seme 1, confronto con V45.
- [ ] Verificare nella scatola nera l'evento `CAMERA LINEA` con la soglia scelta.

**Limite della consegna:** lo ZIP ricevuto non contiene il simulatore V32 e non è stato possibile provare il robot fisico; i controlli segnati [ ] restano da completare prima dell'uso in gara.

### Interfaccia Windows 95 / MS-DOS Prompt (solo presentazione)

La cabina ora richiama una finestra Windows 95: barra del titolo blu “MS-DOS Prompt”, menu e area di lavoro grigia. Le anteprime pixelate delle camere linea e arena non vengono mostrate; restano visibili i dati di YOLO, gli FPS e lo stato delle due camere. Fuoco, frequenza, esposizione e autotaratura della V46 restano invariati.

**Solo presentazione:** non cambia il comportamento del robot né il calcolo Otsu. La modifica grafica non introduce un nuovo FIX.


## V44 – 12 novembre 2026

**Da dove viene:** prima accensione della V43 sul robot, 12/11 in laboratorio. All'avvio, insieme alla cabina del
terminale, si apriva anche la finestra "ClaudeRob - STATO" (FIX 42): "partono entrambe le versioni del terminale". E
cercando la causa sono saltati fuori due avvii automatici (`~/.config/labwc/autostart` e
`~/.config/lxsession/LXDE-pi/autostart`, quest'ultimo con `sleep 30`): se partissero tutti e due, ci sarebbero due programmi
che comandano gli stessi motori e la stessa seriale.

**FIX 109 – solo la cabina** (`ViennaDataConf.py`, `ViennaMonitor.py`). `PANNELLO = False`: la finestra STATO non si apre
più da sola (la cabina ha già camere, cronometro e tutti i dati). Con la cabina restano spente anche le vecchie finestre
OpenCV delle camere ("Linea", "Arena"), come quando c'era la finestra STATO. `PANNELLO = True` la riaccende.

**FIX 110 – un solo programma del robot alla volta** (`RwdFoto.py`, in cima, prima di aprire camere, seriale e motori).
Il primo programma prende un lucchetto (`LUCCHETTO = "/tmp/clauderob_robot.lock"`, `flock`: si libera da solo quando il
programma finisce, anche se si pianta). Un secondo programma lo trova chiuso, scrive "il programma del robot sta GIA'
girando (processo n)", aspetta `LUCCHETTO_ATTESA_S` (20 s) per farlo leggere ed esce. Nel simulatore non c'è.
`UN_SOLO_PROGRAMMA = False` lo spegne.

**Sul robot (12/11, non è codice):** `avvia.sh` non era eseguibile (su GitHub ora sì, PR #23); il terminale dell'avvio
automatico usava `it_IT@euro` (non UTF-8: `°` diventava `Â°`, la cabina sarebbe illeggibile) → `~/.config/labwc/autostart`:
`env LANG=C.UTF-8 LC_ALL=C.UTF-8 lxterminal --geometry=120x40 -e /home/pi/ClaudeRob_GARA/avvia.sh &`; avvio in
`lxsession` spento (copie `.prima_del_12nov`).

**Cosa NON cambia:** la gara.

### Prove

| Prova | V43 | V44 |
|---|---|---|
| Simulatore V32: scuola seme 1, rcj2026, scuola_nuova semi 1-2 | arrivo (255, 392, 262, 311 s) | **identiche campione per campione** |
| Due programmi lanciati insieme (blocco iniziale di `RwdFoto.py`) | partono tutti e due | il secondo scrive l'avviso ed esce (codice 1); finito il primo, si riparte normalmente |

Impronta del codice V44: `a0669f32449f6c26`.

---

## V43 – 10 novembre 2026

**Da dove viene:** il prof (10/11): "ogni volta che interrompo la run spegnendo lo switch il sistema mi crea una scatola
nera. Vorrei una scatola nera per ogni run con all'interno i vari LoP, così da capire meglio dove sbaglia il robot".
E le camere nella cabina della V42 si vedono "in bassissima risoluzione". La V42 era già stata unita: questa è la V43.

**FIX 108 – una scatola nera per ogni run, con le LoP dentro** (`ViennaMonitor.py`). Prima ogni "NUOVA RUN" (switch
acceso) apriva un file nuovo e il tempo ripartiva da 0: una gara con 2 LoP finiva in 3 file. Ora:
- se lo switch è rimasto spento meno di `CRONO_NUOVA_GARA_S` (120 s, lo stesso limite del cronometro) è una **LoP**: stesso
  file e **stesso tempo** (non riparte da 0); ogni campione ha il campo `lop` (quante LoP finora);
- quando si spegne lo switch c'è l'evento **"STOP n: switch spento a m:ss durante ..."** con com'era il robot l'ultimo
  istante acceso (fase, laser, rotta, beccheggio, YOLO); quando si riaccende, **"LoP n: si riparte dopo x s"**;
- file nuovo solo per una gara nuova (switch spento più di 120 s) o con il programma riavviato. Il nome resta
  `run_AAAA-MM-GG_hh-mm-ss_V<n>.jsonl` (gli strumenti di Shuri trovano tutto come prima).

Anche le **camere della cabina crescono con la finestra** (`ViennaCabina.py`): 8 righe con 100 x 38, fino a 20 con un
terminale grande (a 160 x 52 sono circa il doppio). Il terminale mette 2 pixel in ogni carattere: le camere restano
"miniature"; le immagini vere sono nella finestra STATO e nel cruscotto.

**Cosa NON cambia:** la gara.

### Prove

| Prova | V42 | V43 |
|---|---|---|
| Simulatore V32: scuola semi 1-2, rcj2026, lunga, scuola_nuova semi 1-2 | arrivo (255, 258, 392, 462, 262, 311 s) | **identiche campione per campione** (anche alla V41) |
| Scatola nera con robot finto: acceso, spento 0,5 s, riacceso, spento a lungo, riacceso (limite 1 s per la prova) | un file per ogni accensione | **2 file**: la prima gara con STOP 1, LoP 1, STOP 2 e tempo continuo; poi la gara nuova |
| Cabina in un terminale 160 x 52 | camere di 8 righe | camere di 17 righe |

Impronta del codice V43: `166f805b56cee80a`.

---

## V42 – 10 novembre 2026

**Da dove viene:** il prof (10/11): il terminale del robot con i dati dal vivo "ancora non mi convince", e vuole le due
camere in piccolo nel terminale e un cronometro che parte appena si accende lo switch (issue #19). Il terminale di prima
(FIX 37/42) erano 8 righe di testo sotto gli eventi che scorrono: si leggeva male mentre il robot si muove.

**FIX 107 – la "cabina di pilotaggio"** (`ViennaCabina.py`, file nuovo, e `ViennaMonitor.py`). Con
`TERMINALE = "cabina"` (adesso è quello di base) il terminale è una schermata fissa a riquadri che si ridisegna 5 volte
al secondo:
- testata (versione, switch, CPU, alimentazione), una fascia colorata con la **fase** della gara e la riga **ORA**;
- **LASER**: il robot visto dall'alto con i tre raggi lunghi quanto la distanza (verde, giallo sotto 30 cm, rosso sotto
  15); se l'Arduino tace il riquadro diventa un allarme rosso;
- **ASSETTO**: bussola, beccheggio e rollio con lo zero al centro, pendenza, storia degli ultimi 20 s;
- **CRONOMETRO** a cifre grandi: parte quando si accende lo switch, **non si azzera con le LoP** (le conta e mostra il
  tempo dall'ultima partenza), dice quanto manca agli 8 minuti (giallo nell'ultimo minuto, rosso alla fine). Se lo
  switch resta spento più di `CRONO_NUOVA_GARA_S` (120 s) la prossima accensione è una gara nuova;
- **CAMERA LINEA** e **CAMERA ARENA** in piccolo (mezzi blocchi colorati), con quello che vede YOLO e "ferma da n s" se
  il fotogramma è vecchio;
- **MOTORI E PINZA**, **LA GARA** (le fasi in fila con il tempo speso in ognuna: seguilinea, ingresso, vittime, uscita,
  altalena, arrivo) ed **EVENTI** (il più recente in alto, con il tempo del cronometro).
Serve una finestra di almeno 100 x 38 caratteri (in VNC: ingrandire il terminale). Se è più piccola il monitor lo dice
con un evento e usa il pannello di prima. `TERMINALE = "pannello"` rimette il terminale della V41.
La stessa schermata serve alla moviola delle scatole nere: `Strumenti_prove_Claude/terminale_nuovo.py`.

**Cosa NON cambia:** la gara. La cabina è solo nel monitor (thread a parte, tutto dentro try/except) e nel simulatore
non c'è il terminale.

### Prove

| Prova | V41 | V42 |
|---|---|---|
| Simulatore V32: scuola semi 1-2, rcj2026, lunga, scuola_nuova semi 1-2 | arrivo (255, 258, 392, 462, 262, 311 s) | **identiche campione per campione** |
| Monitor vero con robot finto, terminale 110 x 42, switch acceso / spento / riacceso | – | cabina 5 volte al secondo, cronometro dallo switch, **1 LoP contata** |
| Terminale piccolo 80 x 24 | – | avviso e pannello di prima |
| Moviola della scatola nera del 9/11 (V40) | – | fasi con i tempi veri (uscita 65 s), camere e cronometro |

Impronta del codice V42: `ebaf44adfcfb2e81`.

---

## V41 – 9 novembre 2026

**Da dove viene:** prima gara della V40 sul robot vero, 9/11 alle 10:46 (`run_2026-11-09_10-46-10_V40.jsonl`), dalla cartella
pulita `~/ClaudeRob_V40` (impronta giusta). Percorso completo, arrivo alla linea rossa a 388 s, 3 vittime su 3, uscita in
64 s (6/11 con la V38: 187 s), altalena superata. Il prof: "non mi è piaciuto solo l'ingresso: ero centrato bene, avanza,
entra in arena e poi usciva in retromarcia".

- **FIX 106 – Ingresso: falsi "non avanzo" con la porta aperta.**
  - Secondi 136, 143, 149 e 158: robot dritto (rotta 87-92) davanti alla porta, laser davanti 101-103 cm (il fondo
    dell'arena). Dopo 0,6-0,7 s "non avanzo (tocco lo stipite)" e retromarcia, 4 volte di fila: entrato solo a 171 s,
    48 s persi. Ma il robot stava entrando: il laser sinistro passava lo stipite (48 -> 64 -> 85 -> 101 cm) e la rotta
    restava dritta.
  - Causa: il controllo confrontava il laser davanti dopo 0,5-0,9 s con una soglia di 1,5 cm. A circa 1 m il laser
    balla di +-2 cm da fermo (deviazione standard 2,1 cm, letture da 96 a 106) e il cono del VL53L1X (largo circa 45 cm
    a 1 m, più della porta) vede anche gli stipiti: nei primi 0,6 s la lettura non si accorcia quasi per niente, anche
    se il robot avanza. Nel simulatore non si vedeva (raggio sottile, rumore 0,7 cm).
  - Nelle 17 scatole nere vere il controllo "non avanzo" è scattato 15 volte: **tutte le 10 dell'ingresso con il laser
    davanti lontano (62-111 cm)**, 4 dell'uscita con il muso contro il muro (4-9 cm: blocchi veri, giusti) e 1 a 45-55 cm.
  - Ora (`AttraversaPorta`), se il laser davanti è lontano (almeno `ENTRATA_LONTANO_CM`, 60 cm) il controllo comincia
    dopo `ENTRATA_LONTANO_ATTESA_S` (1,5 s), confronta con le letture di 1,2-1,5 s prima e vuole che il laser si sia
    accorciato almeno di `ENTRATA_LONTANO_AVANZO_CM` (5 cm): se il robot avanza davvero, in 1,2 s fa circa 10 cm. Da
    vicino resta tutto come prima (lì il laser è preciso) e "mi sono girato da solo" non cambia (il blocco vero del
    5/11 alle 15:12, robot girato di 18 gradi, è ancora riconosciuto). Un robot bloccato davvero con la porta davanti
    viene riconosciuto lo stesso, meno di un secondo dopo.

**Prove nel simulatore V31:**

| Prova | V40 | V41 |
|---|---|---|
| Pista della scuola dall'inizio, semi 1-6 | arrivo (255-259 s) | identico |
| rcj2026 / lunga / contorto | 1468 / 1893 / 1989 | identico |
| arena_parete / gara | arrivo (227 s / 362 s) | identico |
| `stress_guasti_reali` | 8 minuti, 984 punti | identico |
| Scuola e arena_parete con rumore del laser 2 cm (come il robot vero) | arrivo (254 s / 238 s) | identico |
| Ingresso: robot spostato da y 55 a 95, lato giusto e sbagliato (18 prove, anche contro lo stipite) | 18 su 18 entrato | identico (stessi tempi e urti) |
| Uscita spostata da -12 a +12 cm / uscita all'angolo (x 222-234) | 9 su 9 / 4 su 4 | identico |
| Altalena | riconosciuta, riparte | identico |

Il simulatore non può riprodurre il problema (laser a raggio sottile): la prova vera è sul robot. Da guardare nella
prossima scatola nera: l'ingresso senza "non avanzo" quando il laser davanti vede la porta aperta.

## V40 – 8 novembre 2026

**Da dove viene:** rapporto di Shuri del 5/11 sulla V37 (punto 3 delle cose aperte): nella prova `stress_guasti_reali`
(campo rcj2026, giroscopio bloccato, laser che saltano) il programma **si pianta**. Riprodotto nel simulatore V31 con la V39:
a 417,9 s il capitano chiama una LoP (switch spento) mentre il robot, nel giro dei muri, sta misurando un'apertura in
`ControllaAperturaMuro`. Da quel momento il tempo simulato non avanza più: la gara resta ferma per sempre.

- **FIX 105 – Switch spento durante il controllo di un'apertura.**
  - Causa: con lo switch spento `Rwd.Dritto` esce subito senza muovere il robot (FIX 88). Il ciclo di misura
    dell'apertura (`while ... < 3.0: Dritto(0,1 s); LaserVeri()`) non controllava lo switch e non aspettava mai: girava a
    vuoto. Nel simulatore il tempo avanza solo quando il programma aspetta, quindi la gara si piantava. Sul robot vero il
    ciclo durava 3 s a vuoto e poi il robot continuava il controllo della porta (rotazioni, foto) a switch spento.
  - Ora `ControllaAperturaMuro` controlla lo switch in tutti i suoi cicli e prima di girarsi verso la porta (funzione nuova
    `SwitchSpento`): se è spento ferma i motori, scrive "Switch spento: interrompo ..." ed esce subito. Poi `GiroDeiMuri`,
    che controlla già lo switch a ogni passo, esce anche lui e il programma va in PAUSA come al solito.
  - Rete di sicurezza in `Dritto` (`ViennaClsRobot.py`): con lo switch spento ferma i motori e aspetta 0,1 s prima di
    uscire. Così nessun altro ciclo fatto solo di `Dritto` e laser può più girare a vuoto.
  - Con lo switch acceso non cambia niente: il robot si comporta esattamente come la V39.

**Prove nel simulatore V31:**

| Prova | V39 | V40 |
|---|---|---|
| `stress_guasti_reali` (rcj2026, giroscopio bloccato, laser che saltano) | **piantato** a 417,9 s | finisce gli 8 minuti, 984 punti, riparte dopo la LoP |
| Switch spento per 4 s in 50 istanti della pista della scuola (5-250 s) e LoP in 24 istanti di rcj2026 (10-470 s) | 1 piantato (scuola, 205 s) | **0 piantati su 74** |
| Pista della scuola dall'inizio, semi 1-6 | arrivo (255-259 s) | identico |
| rcj2026 / lunga / contorto | 1468 / 1893 / 1989 | identico |
| arena_parete / gara | arrivo (227 s / 362 s) | identico |
| scuola_rampa / scuola_basso / scuola_parete | non arrivano | identico (come V39) |
| Prove porte: uscita +10 cm, uscita all'angolo x 230, ingresso y 95 lato sbagliato, altalena | uscito / uscito / entrato / riparte | identico |

## V39 – 6 novembre 2026

**Da dove viene:** gara del 6/11 alle 10:48 con la V38 (`run_2026-11-06_10-48-52_V38.jsonl`): percorso completo, arrivo alla
linea rossa a 376 s, 3 palline su 3, altalena riconosciuta e superata. Il prof: "bel lavoro sull'arena, dimmi se noti cose che
si possono migliorare" e poi "aggiusta le cose che reputi necessarie". Tempi: seguilinea 49 s, ingresso 33 s, palline 91 s,
**uscita 187 s**, altalena e arrivo 14 s.

- **FIX 104 – Uscita: prima di uscire, il laser davanti.**
  - A 238 s, seguendo il muro, il robot vede la striscia nera davanti ma il laser davanti misura 13-14 cm: è il muro accanto
    alla porta (la porta comincia a qualche cm dall'angolo). La V38 ha spinto contro il muro per 5 tentativi (laser a 4 cm),
    poi ha rifatto tutto il giro ed è uscita solo a 349 s: quasi 2 minuti persi. In tutte le uscite vere del 5 e 6/11 il
    laser davanti misurava tra 44 e 91 cm.
  - Ora (`EsciDallaPortaDavanti`, `EsciDallaPorta`): se il laser davanti vede meno di `USCITA_LIBERO_CM` (30) è il muro. Il
    robot cerca l'apertura spostandosi a passi di 4 cm (`CercaApertura`, la stessa ricerca dell'ingresso): seguendo il muro
    solo verso l'interno dell'arena, altrimenti prima dalla parte più libera; trovata, si sposta ancora di 9 cm ed esce. Se
    non la trova, scarta quella striscia nera per `USCITA_NERO_PAUSA_S` (6 s) e continua il giro dei muri (prima la
    ritrovava subito e ci riprovava).
  - La ricerca accetta il laser solo se il robot guarda davvero dritto (girato di 35 gradi vedeva 58 cm in diagonale) e
    prima arretra fino a `CERCA_SPAZIO_CM` (22, prima 16) per poter ruotare senza toccare il muro.
  - `EsciSullaStriscia` ora dice se è uscito davvero (prima "uscito" sempre).
- **FIX 104 – Ingresso: niente tentativi sprecati.**
  - A 65 s: "mi sposto di 0 cm" (il posto da provare era già quello del tentativo prima): ora si salta ai posti non provati.
  - A 54-55 s: lo sterzo minimo (45) ha portato il robot da 355 a 0 gradi e per il ritardo dei servo ha continuato fino a
    7: "mi sono girato da solo" senza nessuno stipite, e il robot si è spostato dalla parte sbagliata (è entrato al quinto
    tentativo spostato dall'altra parte). Ora "girato da solo" conta solo se lo sterzo spinge nel verso giusto da almeno
    `ENTRATA_RITARDO_STERZO_S` (0,5 s) e il robot si allontana lo stesso.
- **FIX 104 – Altalena.** Dopo la caduta il robot resta fermo sulla tavola abbassata a -18 gradi: si aspettava il ritorno in
  piano (sotto 8 gradi) e si perdevano sempre 2,5 s con "il giroscopio non si è calmato". Ora basta che il beccheggio non
  cambi più (entro 3 gradi); lo dice ("sono ancora sulla tavola"). Sulla scatola nera delle 10:48: fermo dopo 2,1 s.
- **FIX 104 – Messaggio dell'Arduino.** "ARDUINO NON RISPONDE (cavo USB? batteria?)" diventa "Arduino zitto: switch spento?
  (se lo switch è acceso: cavo USB, batteria, motori)", anche nel pannello: quasi sempre è lo switch spento.

**Prove nel simulatore V31:**

| Prova | V38 | V39 |
|---|---|---|
| Uscita all'angolo: striscia nera vista seguendo il muro, robot a 222, 226, 230, 234 (porta da 239,5) | esce 2 su 4 (spingendo) | **esce 4 su 4**, centrato |
| Uscita: robot sulla striscia spostato da -12 a +12 cm | 9 su 9 | 9 su 9 |
| Ingresso: 8 posizioni, lato previsto giusto / sbagliato | 8 su 8 / – | 8 su 8 / 6 su 8 (come la V37) |
| Pista della scuola dall'inizio, semi 1-6 | arrivo | arrivo (255-259 s) |
| rcj2026 / lunga / contorto | 1468 / 1893 / 1989 | 1468 / 1893 / 1989 |
| arena_parete / gara | arrivo | arrivo |

## V38 – 6 novembre 2026

**Da dove viene:** gara del 6/11 alle 10:15 con la V37 (`run_2026-11-06_10-15-28_V37.jsonl`). Il prof: "l'ingresso ok alla
grande, funziona sempre"; "vorrei sistemare l'uscita dall'arena proprio come abbiamo fatto per l'ingresso: ogni tanto resta
agganciato uno dei due lati del robot quando la punta".

Cosa dice la scatola nera:
- Ingresso: dopo una svolta a SINISTRA, "non avanzo" al primo tentativo, spostato di 4 cm a destra, entrato (FIX 101 giusto).
- Palline: 3 su 3 (due mancate e riprese).
- **Uscita (259-267 s):** striscia nera trovata, esce verso 91 gradi con il laser sinistro a 12-13 cm (lo stipite sinistro).
  Il robot si gira da solo a sinistra (91 -> 80 gradi: fianco sinistro agganciato) e `Dritto` lo raddrizza **ruotando sul
  posto dentro la porta** (lo stesso errore che all'ingresso era stato tolto con il FIX 93). Poi "Uscito, ma la linea non si
  vede ancora": il seguilinea gira a sinistra e trova "un ostacolo a 8 cm", che era il muro.
- Il controllo del FIX 84 (striscia nera ferma nell'immagine) vale solo finché la camera vede la striscia: lo stipite lo
  tocca il fianco, quando la camera (12 cm più avanti) è già oltre.

- **FIX 103 – Uscita come l'ingresso.** I tentativi dell'ingresso sono diventati una funzione sola, `PassaLaPorta`, usata
  per l'ingresso (identica a prima) e ora anche per l'uscita (`EsciDallaPorta`, chiamata da `EsciControllando` appena il
  robot è squadrato sulla striscia nera):
  - avanti senza ruotare sul posto, sterzo minimo 45;
  - "mi sono girato da solo" (più di 8 gradi: il fianco agganciato è quello verso cui gira) o "non avanzo" (laser davanti
    che non si accorcia, oppure striscia nera ferma nella camera come nel FIX 84);
  - arretra dritto, si raddrizza dentro l'arena, si sposta di lato e riprova: girato da solo = dall'altra parte del
    fianco agganciato; non avanzo = +4, +8 cm lontano dal laser laterale più vicino, poi -4, -8 dall'altra parte;
  - `USCITA_TENTATIVI` (5); dopo un ritento avanza `USCITA_EXTRA_RITENTO_S` (0,6 s) in più; se non esce torna dentro e
    riprende il giro dei muri ("bloccato", come nel FIX 84);
  - uscito, se è storto di più di 8 gradi si raddrizza (ora che è fuori).
  - Nella scatola nera: nuove voci "Uscita: ... tocco lo stipite" (errore), "Uscito storto", "PROBABILE ALTALENA", "Altalena:".

**Prove nel simulatore V31:**

| Prova | V37 | V38 |
|---|---|---|
| Uscita: robot squadrato sulla striscia nera ma spostato di -12, -10, -7, -4, 0, +4, +7, +10, +12 cm (centratura cieca) | esce 5 su 9 | **esce 9 su 9** |
| Ingresso: 8 posizioni davanti alla porta, lato previsto giusto | 8 su 8 | 8 su 8 (stessi tempi: ingresso invariato) |
| Pista della scuola dall'inizio, semi 1-6 | arrivo (255-258 s) | arrivo (255-258 s) |
| rcj2026 / lunga / contorto | 1468 / 1893 / 1989 | 1468 / 1893 / 1989 |
| arena_parete / gara | arrivo | arrivo |

Nel simulatore il robot che tocca lo stipite si ferma e non ruota: scatta solo il "non avanzo". Sul robot vero, come alle
10:15, scatterà spesso prima il "mi sono girato da solo", che dice subito da che parte spostarsi.

## V37 – 5 novembre 2026

**Da dove viene:** gara delle 16:12 con la V36 (`run_2026-11-05_16-12-52_V36.jsonl`): percorso completo fino alla linea rossa
(arrivo a 429 s), 3 palline su 3. Il prof: "l'ingresso non ci siamo: il robot è arrivato da destra ma correggeva come se
fosse arrivato da sinistra; il sistema si deve regolare in base alla direzione dell'ultima svolta prima dell'argento. Dopo
l'altalena fa uno stoppie sulle ruote anteriori e perde la linea: quando il giroscopio vede un cambio repentino e
importante del beccheggio deve capire che ha appena superato un'altalena, scriverlo sullo schermo, stabilizzare il
giroscopio e ricontrollare la linea".

Cosa dice la scatola nera:
- **Ingresso (107-142 s):** svolta a DESTRA al verde (da 65 a 179 gradi), argento visto a metà svolta. Girato verso la porta,
  il laser davanti misura **18-20 cm**: è il muro accanto alla porta (attraverso la porta si vede il fondo dell'arena, 90-100
  cm). La V36 ha deciso "fianco SINISTRO" da un errore di direzione di 4 gradi e si è spostata a destra, due volte:
  dalla parte sbagliata. È entrata al terzo tentativo, strisciando (laser sinistro 96-106 cm: la porta era a sinistra).
  Alle 15:52 (V35) la svolta era a SINISTRA e lo spostamento a destra era giusto.
- **Altalena (416-426 s):** muso in su a +21 gradi per 2 s, poi in 0,7 s da +21 a **-49** (lo "stoppie"); YOLO vede una
  "discontinuità" e il robot attraversa un vuoto che non c'è **verso 89 gradi** (veniva da 240), con la rotta che salta
  154 -> 111 -> 74 -> 29 gradi in 0,3 s (giroscopio disturbato col robot inclinato). La linea rossa era vicina e l'ha
  trovata lo stesso.

- **FIX 101 – Ingresso dalla parte giusta.**
  - Il robot gira quando la camera (12 cm davanti alle ruote) è sull'incrocio: il centro del robot resta dalla parte da
    cui arriva. Dopo una svolta a DESTRA è spostato a destra della porta e va corretto a SINISTRA, e viceversa
    (`IngressoLato`, dal verso salvato in `SvoltaAttesa`). Lo scrive: "Ingresso subito dopo una svolta a DESTRA ... se serve
    mi sposto a sinistra".
  - `CercaAperturaDavanti`: prima di entrare, se il laser davanti vede meno di `INGRESSO_LIBERO_CM` (40) è il muro, non la
    porta: il robot si sposta di lato a passi di `ENTRATA_CERCA_PASSO_CM` (4) restando alla stessa distanza dal muro
    (`SpostaDiLato(..., indietro=True)`), prima dalla parte opposta all'ultima svolta (fino a 5 passi), poi dall'altra;
    trovata l'apertura si sposta ancora di `ENTRATA_OLTRE_CM` (9) verso il centro della porta.
  - Se nella porta "non avanzo": tentativi a +4, +8 cm dalla parte prevista, poi -4, -8 dall'altra (`ENTRATA_TENTATIVI` 5,
    `ENTRATA_SPOSTA_CM` 4). "Mi sono girato da solo" resta guidato dal verso della rotazione (prova fisica).
  - Il controllo "non avanzo" vale anche col laser davanti cortissimo (prima solo sopra 3 cm).
- **FIX 102 – Altalena.** `ControllaAltalena` (a ogni giro del seguilinea) guarda lo storico del beccheggio pacchetto per
  pacchetto (`Rwd.StoriaBeccheggio`): muso in su di almeno `ALTALENA_SALITA_MIN` (10) seguito, entro `ALTALENA_FINESTRA_S`
  (1,2 s), da un calo di almeno `ALTALENA_SALTO_GRADI` (30). Allora: si ferma e scrive **"PROBABILE ALTALENA SUPERATA"**,
  aspetta che giroscopio e rotta stiano fermi (`ALTALENA_STABILE_S`, al massimo 2,5 s), cancella lo storico della rotta
  (con i valori sballati), se è girato di più di 10 gradi torna nella direzione di prima della caduta, ricontrolla la linea;
  se non la vede avanza 0,4 s e riguarda; poi la ricerca sicura. Sulle scatole nere del 5/11 scatta sulle altalene
  (16:12 a 418,6 s; 15:12 a 461,7 s) e su due tratti all'inizio della gara delle 15:12 con lo stesso salto (+21 -> -36 e
  +24 -> -29 gradi); mai nelle gare delle 11:47, 12:20 e 15:52.

**Prove nel simulatore V31:**

| Prova | V36 | V37 |
|---|---|---|
| Porta: robot fermo davanti alla porta, spostato di -20, -9, +9, +20 cm, lato previsto giusto | entra 1 su 4 | **entra 4 su 4** |
| 8 posizioni (-20, -12, -9, -5, +5, +9, +12, +20 cm), lato previsto giusto / sbagliato / non noto | 3 su 8 (il lato non lo usa) | **8 su 8** / 6 su 8 / 7 su 8 |
| Pista della scuola dall'inizio, semi 1-6 | arrivo (253-404 s) | arrivo, tutti tra 255 e 258 s |
| rcj2026 / lunga / contorto | 1468 / 1893 / 1989 | 1468 / 1893 / 1989 |
| arena_parete / gara | arrivo | arrivo |
| Altalena (storico finto +21 -> -49 gradi) | – | "PROBABILE ALTALENA SUPERATA", giroscopio fermo in 0,5 s, linea vista, riparte |

Nel simulatore il laser è un raggio sottile: vede "libero" appena il centro del robot passa lo stipite. Il VL53L1X vero ha
un cono largo e vede libero un po' più tardi: per questo dopo l'apertura ci si sposta ancora di 9 cm.

## V36 – 5 novembre 2026

**Da dove viene:** gara delle 15:52 con la V35 (`run_2026-11-05_15-52-24_V35.jsonl`): ingresso riuscito dopo due tocchi
dello stipite (la V35 se n'è accorta: "non avanzo, fianco SINISTRO contro lo stipite", si è spostata di 3 cm a destra e al
terzo tentativo è entrata), 3 palline su 3, uscita trovata; poi, a 284 s, il programma si è fermato con
`TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'` in `StrisciaFerma`.

- **FIX 99 – StrisciaFerma.** Uscendo, dopo "Uscendo non avanzo: tocco lo stipite. Arretro ... e riprovo", il campione
  di un secondo prima era senza striscia nera (None) e il confronto andava in errore. Ora si usano solo i campioni in
  cui la striscia si vedeva. L'errore c'era dalla V26 (FIX 84): saltava fuori solo se il robot toccava lo stipite uscendo.
- **FIX 100 – Un errore non finisce la gara.** Seguilinea, arena e uscita sono chiamati con `Protetto(...)`: se una fase va
  in errore, l'errore si stampa per intero (resta nella scatola nera come "ERRORE NEL CODICE in ..."), i motori si
  fermano e il programma passa alla fase successiva invece di chiudersi.

**Prove nel simulatore V31:** pista della scuola semi 1/3/5 arrivo (254/256/404 s, come la V35), rcj2026 1468 con arrivo,
arena_parete arrivo, porta spostata di 9 cm entra.

## V35 – 5 novembre 2026

**Da dove viene:** scatola nera del 5/11 alle 15:12 con la V34 (`run_2026-11-05_15-12-32_V34.jsonl`) e il messaggio del prof:
"l'ingresso ancora non ci siamo: non tieni in considerazione la larghezza del robot, spesso il laser anteriore è libero ma
uno dei due lati resta agganciato all'ingresso. Raccolta palline e deposito tutto ok. Dopo l'uscita ha superato
un'altalena e quando si è inclinato dopo lo sbalzo ha visto una striscia argento e il robot si è bloccato".

Cosa dice la scatola nera:
- **Ingresso (167-177 s):** direzione d'ingresso 142, centratura "striscia non vista", poi `entro dritto`. Il laser
  davanti vede libero (102 cm, il fondo dell'arena), ma da 172,6 s **non si accorcia più** (93-97 cm per 1,3 s con i
  motori a 68) e il robot **si gira da solo di 18 gradi a sinistra** (146 -> 128) mentre lo sterzo corregge a destra:
  il fianco sinistro è agganciato allo stipite. Il robot è largo 15,6 cm, la porta circa 28: restano 6 cm per lato.
- **Primo tentativo (122 s):** l'argento visto a metà di una svolta; direzione calcolata 152 con il robot a 221.
  Annullato correttamente.
- **Palline:** 3 su 3 (argento, argento, nera) nei triangoli giusti.
- **Uscita (320-456 s):** trovata dopo due aperture scartate; uscita confermata a 456 s.
- **Altalena (459-464 s):** salita di 21 gradi, poi caduta in avanti (beccheggio -69), linea persa. Il ventaglio di
  ricerca si ferma due volte: a -60 gradi sulla linea e a -30 gradi su una **striscia argento** (direzione 129, quasi
  la stessa con cui era entrato nell'arena). Da lì, in piano, YOLO vede argento con sicurezza 0,92-1,00 per 23 s.
- **Il blocco (470-493 s):** "Striscia argento ma l'arena è già fatta: faccio dietrofront" ripetuto 45 volte, ma il
  robot **non gira mai**: `Gira(180)` non funzionava (vedi FIX 97). A 493 s lo switch viene spento.

- **FIX 96 – Porta: la larghezza del robot.** `EntraDallaPorta` ora attraversa la porta con `AttraversaPorta`, che
  controlla due segnali di "fianco agganciato":
  - il robot si gira da solo di più di `ENTRATA_STORTO_GRADI` (8): girarsi a sinistra = fianco sinistro trattenuto;
  - il laser davanti non si accorcia (meno di `ENTRATA_AVANZO_MIN_CM` in 0,6 s): il robot non avanza.
  Se succede: arretra dritto fuori dalla porta, si raddrizza, si sposta di lato di `ENTRATA_SPOSTA_CM` (3 cm) dalla
  parte opposta al fianco agganciato (`SpostaDiLato`) e riprova, fino a `ENTRATA_TENTATIVI` (3) volte.
  Nella porta lo sterzo corregge almeno con `ENTRATA_STERZO_MIN` (45): sotto circa 40 i servo non girano (FIX 64).
  Inoltre la direzione d'ingresso si aggancia al lato delle piastrelle più vicino fino a `INGRESSO_AGGANCIO_GRADI` (40,
  prima 25), anche quando la retta sulla linea nera dice altro: la porta è sempre parallela alle piastrelle.
- **FIX 97 – Gira(180) gira davvero.** `Gira` calcolava l'errore come differenza tra obiettivo e direzione attuale,
  che sta tra -180 e +180: con un obiettivo esattamente opposto valeva -180 ("già arrivato") e il robot non girava.
  Ora conta quanto ha girato dall'inizio, passo per passo: funziona con qualsiasi angolo.
- **FIX 98 – Dopo l'arena l'argento non blocca.** Uscito dall'arena: il ventaglio di ricerca della linea non si ferma
  più su una striscia argento (`VedoLinea`); il dietrofront per l'argento si fa una volta sola; se il robot rivede
  l'argento entro `DIETROFRONT_PAUSA_S` (30 s) la striscia viene ignorata e il robot continua.

**Prove nel simulatore V31** (con l'arena vera della scuola, 120 x 90, uscita sul lato corto):

| Prova | V34 | V35 |
|---|---|---|
| pista della scuola dall'inizio, semi 1-6 | semi 1-2 arrivo; seme 3 entra storto (116) e resta incastrato | **6 su 6 arrivo** (253-404 s), seme 3 entra a 90 |
| porta spostata di 9 cm rispetto alla linea (striscia corta: centratura cieca) | bloccato (4 urti, 60 s fermo) | **entra** al 2° tentativo ("non avanzo, fianco ... contro lo stipite") |
| porta spostata di 3-5 cm, dritto o storto di 8 gradi | entra | entra |
| rcj2026 / lunga / contorto | 1468 / 1893 / 1989 | 1468 / 1893 / 1989 |
| arena_parete / gara | arrivo | arrivo |

Nel simulatore il robot che tocca lo stipite si ferma (non ruota attorno allo spigolo come quello vero): il controllo
"non avanzo" è quello che scatta; sul robot vero scatterà più spesso il "mi sono girato da solo".

## V34 – 5 novembre 2026

**Da dove viene:** scatola nera del 5/11 alle 12:20 con la V33 (`run_2026-11-05_12-20-26_V33.jsonl`), foto dell'arena dall'alto
e richieste del prof: "entra in maniera storta in arena e tocca lo spigolo del LED sinistro"; "più reattività nel seguire
le pareti, anticipare le girate quando il laser anteriore misura una distanza inferiore; i triangoli non sono sempre negli
stessi angoli".

Cosa dice la scatola nera:
- **Ingresso (17,8-22 s):** il robot è centrato sulla porta e parte dritto (direzione 1). Passando la porta si storce di
  8 gradi a sinistra (353) e `Dritto` lo raddrizza **ruotando sul posto** mentre è ancora nella porta: il robot gira
  attorno al centro delle ruote, il retro sinistro (il LED) va verso lo stipite (laser sinistro 22 -> 16 cm) e la
  rotazione resta bloccata per 1,5 s.
- **Giro dei muri (170-266 s):** 96 s per trovare l'uscita; il **72% del tempo** il robot era fermo a ruotare sul posto di
  2-5 gradi (per esempio 46 cm in 15 s lungo una parete), poi "Non avanzo" a 215 e 235 s e rotazioni bloccate a 247 e
  250 s vicino agli angoli.
- **Dopo l'arrivo (286,7 s):** finita la festa il robot ripartiva, scendeva la rampa e rivedeva l'ingresso 16 volte.
- L'**Arduino** si è zittito a 302,6 s.

- **FIX 93 – Porta senza toccare.** `EntraDallaPorta`: nella porta si avanza senza raddrizzamenti sul posto
  (`Dritto(..., ruota=False)`, nuovo parametro); ci si raddrizza solo quando tutto il robot è dentro l'arena.
- **FIX 94 – Giro dei muri più svelto che anticipa gli angoli.**
  - Quando il laser frontale (filtrato) scende sotto `PARETE_ANTICIPO_CM` (25 cm) il robot comincia ad allontanarsi dal
    muro mentre avanza, fino a `LATO_MURO_CM + PARETE_ANTICIPO_LATO` (6,5 + 6 cm) quando arriva a `ANGOLO_CM`: così ha
    spazio per girare di 90 gradi senza che il retro tocchi. Vale per gli angoli, per i triangoli dovunque siano e per
    le palline contro il muro (il laser li vede tutti).
  - Meno soste: si raddrizza sul posto solo oltre `PARETE_ERR_RUOTA` = 7 gradi (prima 4), con tolleranza 3 (prima 1,5),
    e avanza `PARETE_PASSO_S` = 0,2 s tra un controllo e l'altro (prima 0,12).
  - Se una rotazione lungo il muro resta bloccata il robot arretra un poco invece di insistere; mentre anticipa un angolo
    la stima della direzione del muro (`PARETE_STIMA`) è sospesa.
  - Nel simulatore il tempo passato a ruotare sul posto nel giro dei muri scende dal 28-37% al 17-24%. Prima prova del
    simulatore con l'anticipo fatto *ruotando*: il retro finiva contro il muro e il robot si incastrava; per questo
    l'anticipo è fatto staccandosi dal muro.
- **FIX 95 – Fermo sulla linea rossa.** Dopo l'arena, vista la linea rossa e fatta la festa, il robot avanza ancora
  `AVANZA_ARRIVO_S` (1 s, circa 10 cm: prima si fermava pochi cm prima della linea) e resta fermo finché si spegne lo
  switch (`FERMO_DOPO_ARRIVO`).

**Prove nel simulatore V30:**

| Prova | V33 | V34 |
|---|---|---|
| rcj2026 seme 1 / seme 3 | 1468, arrivo a 392 / 403 s | 1468, arrivo a 381 / 383 s |
| lunga seme 1 / seme 2 | 1688 / 1893 | **1893 / 1893**, sempre arrivo |
| contorto | 1742 | **1989**, arrivo |
| arena_parete | arrivo | arrivo |
| arena seme 1 / seme 2 (giro dei muri) | 76 / 85 s | 73 / 73 s |
| pista della scuola | completa (non contata come arrivo) | completa con arrivo a 289 s |

## V33 – 5 novembre 2026

**Da dove viene:** la foto della prima piastrella mandata da Battista (incrocio con il verde, vicino alla striscia nera
dell'uscita) e di nuovo la scatola nera del 5/11 (`run_2026-11-05_11-47-50_V30.jsonl`).

Guardando i tempi si capisce cosa succede dopo le svolte. Con le svolte "vecchie" il robot gira solo di 42 gradi e il
seguilinea finisce la curva. Ma mentre il robot è ancora sopra l'incrocio, `IncrocioDritto` (FIX 59) lo prende per un
incrocio SENZA verde e lo rigira verso il braccio "dritto": la svolta viene annullata.
- 8,6 s: verde a destra al secondo incrocio (giusto: deve scendere). A 10,7 s "Incrocio senza verde: lo attraverso
  dritto (correzione -31 gradi)": il robot torna sulla linea lunga invece di scendere. È il "giro a destra" che sembrava
  non visto nella prima piastrella.
- Lo stesso dopo le svolte di 14,7 s (+28), 20,3 s (+68), 38,1 s (+24) e alla rotonda (56,9 s, +73).

- **FIX 92 – Niente "dritto" subito dopo una svolta al verde.** Per `INCROCIO_DOPO_SVOLTA_S` (2 s) dopo la fine di una
  svolta al verde `IncrocioDritto` non interviene: la curva la finisce il seguilinea. Il verde dell'uscita della rotonda
  intanto lo vede YOLO (pausa di 1 s del FIX 91).

**Prove nel simulatore V30:** identiche alla V32 (pista della scuola completa con ingresso, arena, uscita e linea rossa;
rcj2026 1468; lunga 1688 e 1893; contorto 1742; arena_parete arrivo). Il simulatore fa svolte più pulite del robot vero
e questo errore quasi non lo produce: la prova vera è in pista.

## V32 – 5 novembre 2026

**Da dove viene:** scatola nera del 5/11 alle 11:47 (`run_2026-11-05_11-47-50_V30.jsonl`, fatta con la **V30**) e
segnalazione di Battista: "alla rotonda non ha girato a sinistra e ha proseguito dritto"; "non ha visto il giro a
destra nella prima piastrella".

Cosa dice la scatola nera:
- **Rotonda (secondi 53,8-57):** entra girando a sinistra (verde Sx, sicurezza 0,83). Già 0,2 s dopo YOLO vede il
  verde dell'uscita (Sx, 0,84-0,87), ma il robot lo ignora ("YOLO dice Sx, ma ho appena girato a questo incrocio")
  per la pausa del FIX 80. La pausa finiva solo dopo 4 fotogrammi senza verde o dopo 3 s: alla rotonda il verde
  dell'uscita resta sempre in vista, quindi a 56,9 s l'uscita viene presa come "Incrocio senza verde: dritto".
- **Prima piastrella (secondi 4,7-10,7):** gira a destra al verde, ma la rotazione si ferma a 37 gradi. Da 7,2 a
  8,5 s YOLO rivede un verde a destra e il robot lo ignora per la stessa pausa, poi gira di nuovo a 8,6 s.
- L'**Arduino si zittisce a 84,6 s** e il robot resta fermo fino alla fine (190 s): ancora l'alimentazione.

- **FIX 91 – Pausa dei verdi più corta.** `VERDE_PAUSA_S` da 3,0 a 1,0 s: dopo una svolta al verde lo stesso
  incrocio non si rivaluta per al massimo 1 s (basta per finire la curva, che era il problema del FIX 80), poi il
  verde successivo conta di nuovo.

**Prove nel simulatore V30:**

| Prova | V31 | V32 |
|---|---|---|
| pista della scuola (`scuola`) | non entra mai in arena, fermo a 377 s | gira al quadrato arrotondato, entra in arena (30 s), esce dalla porta giusta (259 s), festa alla linea rossa |
| rcj2026 | 1468, arrivo | 1468, arrivo |
| lunga seme 1 / seme 2 | 1688 / 1688 | 1688 / 1893 con arrivo |
| contorto | 1742 | 1742 |
| arena_parete | arrivo | arrivo |

Nessun dietrofront sbagliato sui verdi in diagonale della pista lunga (il caso per cui era nata la pausa).

## V31 – 3 novembre 2026

**Da dove viene:** scatola nera del robot vero con la V30 (`run_2026-11-03_10-50-09_V30.jsonl`, 3/11 alle 10:50) e
richiesta di Giovanni: "quando il robot sbatte contro l'ostacolo non deve continuare a spingere". Sulla pista della
scuola c'è una parete lungo il bordo destro (da regolamento non ci sarebbe).

Cosa dice la scatola nera (secondi 81-129): sul semicerchio vicino al bordo il robot tocca la parete a destra
(laser frontale 4 cm) e la prende per un ostacolo. Il giro dell'ostacolo partiva **sempre a destra**: girando verso
la parete fa 25 gradi in 4 s invece di 90, poi avanza e **spinge contro la parete per 5 s** (laser frontale fermo a
4 cm, muso che sale di 7 gradi). Appena finito, un secondo "ostacolo" (la parete di traverso, 12 -> 16 cm) "per
sicurezza" e un altro giro: 48 s persi in tutto.

- **FIX 90 – Ostacolo più furbo.**
  - *Parete accanto:* se un laser laterale vede una parete a meno di `OST_PARETE_CM` (18 cm), il "qualcosa davanti"
    è quasi sempre la parete: il robot arretra, si gira di `OST_STACCO_GRADI` (20) dalla parte libera e torna a seguire
    la linea ("Parete a DESTRA a 15 cm e qualcosa davanti: è la parete, arretro e mi stacco"). Se entro
    `OST_STACCO_RIPROVA_S` (8 s) è di nuovo lì, è un ostacolo vero.
  - *Lato libero:* lo aggira passando a destra come prima, ma a **sinistra** se a destra c'è meno di
    `OST_LATO_LIBERO_CM` (30 cm) e a sinistra di più.
  - *Niente spinte:* durante il giro, se il laser frontale (filtrato, FIX 87) è a `OST_SPINTA_CM` (5 cm) o meno, il
    robot si ferma e arretra di `OST_SPINTA_ARRETRA_S` (0,5 s). Se succede sul primo lato, o se la prima rotazione
    resta bloccata a più di `OST_ROTAZIONE_TOLL` gradi, torna nella direzione di partenza e **prova dall'altro lato**;
    se non passa da nessuno dei due torna a seguire la linea.
  - *Parete di traverso:* in `ConfermaOstacolo`, se avanzando la distanza non scende e di lato c'è una parete, non è un
    ostacolo ("Non mi avvicino (12 -> 16 cm) e c'è una parete di lato"): il robot si stacca dalla parete
    (`StaccaDallaParete`: arretra e gira di 20 gradi, poi 40 e 60 se ci ricade entro 16 s) e torna a seguire la linea.
  - *Rotazione contro la parete:* durante il giro, se raddrizzarsi richiede più di 0,6 s e il robot resta storto di
    più di 20 gradi, un fianco tocca qualcosa: si ferma e arretra (prima ci riprovava per 40 s).

**Prove nel simulatore V30:**

| Prova | V30 | V31 |
|---|---|---|
| ostacolo di rcj2026 con una parete a 17 cm sulla destra | 988 punti, 21 urti, 3 LoP, niente arrivo | 1416 punti, 3 urti, 1 LoP, arrivo |
| pista della scuola: linea che finisce contro la parete destra | schiacciato contro la parete per 60 s | si stacca (arretra e gira) e riparte |
| rcj2026 (normale) | 1468, arrivo a 458 s | 1468, arrivo a 392 s |
| lunga / contorto (normali) | 1688 / 1742 | 1688 / 1742 |
| arena_parete | arrivo | arrivo |
| rcj2026 / lunga con giroscopio bloccato e laser disturbati | 1103 / 1087 | 1125 / 1142 |

**Altre cose dalla scatola nera V30 (hardware):** il giroscopio questa volta funziona; "Falso ostacolo" a 148 s ha
fatto il suo lavoro. Ma l'**Arduino si zittisce a 292,7 s**, proprio quando il braccio si è appena abbassato e i
motori ripartono: da lì il robot resta fermo nell'arena fino alla fine (250 s). È successo in tutte le gare: IPOTESI
calo di tensione dell'Arduino quando servo del braccio e motori assorbono insieme. Controllate come è alimentato
l'Arduino (meglio solo dalla USB del Raspberry, massa in comune, un condensatore grosso sull'alimentazione dei servo).
Nota: sul Raspberry la cartella del robot contiene anche molti altri file `.py` (Bovalino26.py, Catania01.py...):
il robot funziona lo stesso, ma l'impronta nella scatola nera non è quella della V31 pulita.

## V30 – 3 novembre 2026

**Da dove viene:** scatola nera del robot vero del 3/11 alle 9:23 (`run_2026-11-03_09-23-08.jsonl`). Nota: quella gara
è stata fatta con la **V27** (lo dice l'intestazione, e nel nome del file manca `_V29`): sul Raspberry va copiata la
cartella nuova.

Cosa dice la scatola nera:
- **il giroscopio è rimasto fermo per tutta la gara** a beccheggio -2, rollio -2, rotta 0 (laser e Arduino vivi; a
  ottobre funzionava). Ogni `Gira` è finita in TIMEOUT dopo 8 s (12 volte): a ogni incrocio il robot girava su se
  stesso per 8 secondi, quasi un giro intero, e poi si perdeva;
- **il laser frontale salta**: 5, 54, 74, 134 cm; 15, 91, 11, 461 cm. Il 15% delle letture cambia di più di 50 cm da
  una all'altra (a ottobre meno del 2%, il 29/10 già il 31%; anche il sinistro salta, 10%). Due ostacoli finti:
  a 85 s una sola lettura a 5 cm ha "confermato" l'ostacolo; a 109 s una lettura a 11 cm, poi il controllo non ha
  visto né ostacolo né rampa e "per sicurezza" lo ha trattato come ostacolo;
- l'Arduino ha smesso di rispondere a 163 s (come in tutte le gare di ottobre).

**Prima di tutto controllate l'hardware:** cavi e alimentazione del BNO055 (con `LetturaNano.py`, girando il robot
a mano la rotta deve cambiare), il laser frontale (fisso, lente pulita, niente sole diretto, cavi) e l'alimentazione
dell'Arduino. Il codice nuovo regge questi guasti, ma non li ripara.

- **FIX 87 – Laser frontale filtrato.** Per l'ostacolo si usa `Rwd.FrontaleFiltrato()`: la mediana delle letture
  dell'ultimo `LASER_FR_FINESTRA_S` (0,3 s), **pesata sul tempo** (ogni valore conta per quanto è durato; una lettura
  sbagliata dura un pacchetto e non può diventare la mediana; lo 0 = "niente davanti" conta come lontano).
  `ConfermaOstacolo` usa lo stesso valore e, se allo scadere del tempo il laser in mediana vede da `OST_FALSO_CM`
  (15 cm) in su, dice "Falso ostacolo" e il robot continua a seguire la linea. Nel terminale e nella scatola nera:
  "Laser frontale: lettura isolata X cm ignorata", "Falso ostacolo", e il nuovo campo `dfr` (laser filtrato).
- **FIX 88 – Bussola di riserva.** Se i motori fanno girare il robot di più di `GIRO_BLOCCATO_GRADI` (60) e il
  giroscopio non cambia neanche di un grado, il robot scrive "GIROSCOPIO BLOCCATO" e da lì la rotta è **stimata dai
  comandi dei motori** (`GRADI_S_PER_VEL` = 0,74 gradi/s per punto di velocità, misurato sulle scatole nere di ottobre:
  35 gradi/s a velocità 47, 50 a 68). Lo stesso quando l'Arduino tace. Appena il giroscopio torna a muoversi: "GIROSCOPIO
  DI NUOVO VIVO". È meno precisa del giroscopio (soprattutto nell'arena), ma le rotazioni finiscono quasi dove devono
  invece di durare 8 s. Nella scatola nera: campi `bus` ("giroscopio" / "stimata: ...") e `rotta`. Con
  `BUSSOLA_STIMATA = False` si torna a prima. Corretto anche `Dritto`, che con lo switch spento girava a vuoto.
- **FIX 89 – Pendenza.** Con il giroscopio bloccato la pendenza è "sconosciuta" (prima diceva "in piano" per sempre).
  Corretto "in piano (da 425990 s)": il Raspberry corregge l'ora da internet dopo l'avvio e l'orologio salta avanti.

**Prove nel simulatore V29** (nuovo: guasti `imu_bloccato`, `tof_fr_spurie`, `tof_lat_spurie`, `arduino_muto_da`):

| Prova | V30 |
|---|---|
| rcj2026 (normale) | 1468, arrivo, 0 LoP (come V29) |
| pista lunga (normale) | 1688, 0 LoP (come V29) |
| contorto (normale) | 1742, 0 LoP (come V29) |
| arena_parete | arrivo in 228 s |
| rcj2026 con giroscopio bloccato + laser al 15% di letture sbagliate | 1103, tutte le palline salvate, 2 LoP, nessun TIMEOUT, nessun ostacolo finto |
| pista lunga con gli stessi guasti | 1087, 1 LoP |

Con gli stessi guasti la V29 nel simulatore non arriva in fondo alla gara (rotazioni da 8 s, ostacoli finti).

## V29 – 2 novembre 2026

**Da dove viene:** richiesta del 2/11. Le scatole nere del robot vero devono arrivare a Shuri e dire subito con quale
codice sono state registrate.

- **FIX 86 – Versione e impronta nella scatola nera.** Il file ora si chiama `run_2026-11-02_10-15-30_V29.jsonl`
  (prima la data, così i file restano in ordine di tempo; poi la versione). Nella prima riga, oltre a `versione`, ci
  sono `impronta` (le prime 16 cifre dello sha256 di nome e contenuto dei file `.py` della cartella, lo stesso calcolo
  di Shuri), l'elenco dei file e la cartella da cui gira il robot. Se un ragazzo cambia un parametro senza cambiare
  `VERSIONE`, o se sul Raspberry restano file di versioni diverse, il numero di versione è uguale ma l'impronta no:
  `analizza_scatola.py` di Shuri lo segnala ("IMPRONTA DIVERSA").
- Nessun'altra modifica al comportamento del robot: stessa guida della V28 (FIX 83-85).
- Verifica nel simulatore V28: nome del file e impronta giusti (l'impronta della scatola nera è uguale a quella
  calcolata da Shuri sulla cartella); campo 2026 e arena della scuola come la V28.

**Strumenti nuovi per Shuri** (nella cartella "Laboratorio Shuri", non nel codice del robot):
- `scarica_scatole.sh`: copia le scatole nere dal robot in rete (rsync, serve la chiave SSH una volta sola) o da una
  cartella (chiavetta USB), in `02_Robotica/ScatoleNere/`. Non cancella mai niente.
- `analizza_scatola.py`: per ogni scatola nera nuova scrive `analisi.md` (problemi con secondo, contesto, stampe,
  riga del codice e foto delle camere; ritardo del giroscopio, rotazioni, tratti inclinati, Arduino muto, controllo
  di versione e impronta, note dei ragazzi) e la scheda per Claude `SHURI_scheda_reale.md`. Provato sulle quattro
  scatole nere vere (21, 23, 26 e 29 ottobre): ritrova da solo i problemi analizzati a mano in queste settimane.

---

## V28 – 2 novembre 2026

**Da dove viene:** la prima batteria di **Shuri** sulla V27 (`Laboratorio Shuri/Prove/2026-11-02_1607_ClaudeRob_V27/`,
scheda `SHURI_scheda_correzioni.md`): 11 gare nel simulatore V28, 4 problemi. Ogni problema è stato riprodotto con il
comando della scheda e la causa è stata cercata nei dati del replay (posizione del robot, triangoli, porte), non solo
nelle stampe.

**Cosa dicono i dati (e cosa no)**
- **P2/P3 – pallina fuori dal triangolo e nera prima delle vive (pista lunga, seme 2).** L'ipotesi di Shuri era "l'urto
  sposta il robot". Nei dati: dopo la presa il robot si gira verso la direzione ricordata del triangolo e lo vede sul
  bordo destro dell'immagine; il laser frontale legge 16 cm, ma è il MURO a sinistra del triangolo (il centro del
  triangolo era 68 gradi più a destra). In `ScaricaPalla` sotto i 17 cm si scaricava subito, anche nel ramo che stava
  ancora sterzando verso il triangolo. L'urto è l'accostamento al muro, non la causa. La regola "la nera solo dopo
  due argento" c'era già (`if Arg < 2`): il problema era che la pallina fuori veniva contata come salvata.
- **P4 – nessuna uscita con il giroscopio disturbato.** Il robot NON seguiva una linea dentro la zona come ipotizzava
  Shuri: era fermo nello stesso punto per 100 s, con lo spigolo contro lo stipite della porta d'uscita. Con il
  giroscopio sbagliato il "giro di 90 gradi" verso la porta non era di 90 gradi veri: arrivato storto di 4-5 gradi e
  spostato di 9 cm. "Alto" era il seguilinea che spingeva contro lo stipite.
- **P1 – LoP al secondo 32 nel campo contorto (c'era dalla V25).** Interruzione subito dopo una curva a U. Il robot
  aveva girato di 50 gradi negli ultimi 2 s ma, nell'ultimo 0,8 s, solo a 19,6 gradi al secondo (soglia 25): per il
  FIX 62 "non stava curvando", ha scelto il lato più vicino (nord) e ha attraversato verso la fila vicina.

**Correzioni**
- **FIX 83 – Scarico solo con il triangolo davanti.** Se il muro è vicino e il triangolo non è al centro
  dell'immagine (più di 40 pixel, circa 12 gradi), il robot arretra di mezzo secondo e ruota verso il triangolo
  (angolo dai pixel, come per le palline), poi si avvicina e scarica.
- **FIX 84 – Uscita dritta e centrata con la striscia nera.** Appena la camera linea vede la striscia nera
  dell'uscita, il robot si raddrizza con la sua inclinazione e si mette in mezzo alla porta con la sua estremità
  (come il FIX 71 per l'ingresso): niente giroscopio. Se uscendo le ruote spingono ma il robot non avanza
  (`RobotFermo`, FIX 55), arretra, si ricentra e riprova (al massimo 2 volte).
- **FIX 85 – Interruzione dopo una curva a U.** "Sto curvando" anche se negli ultimi 2 s il robot ha girato in tutto
  più di 45 gradi: allora il pezzo dritto è il lato successivo nel verso della curva.

**Risultati nel simulatore V28** (stesse 11 prove della batteria di Shuri, più altri semi):

| Prova | V27 | V28 |
|---|---|---|
| Campo RCJ 2026, semi 1-4 | 1.468 su 1.468 | 1.468 su 1.468 |
| Pista lunga seme 1 | 1.729 | 1.729 |
| Pista lunga seme 2 | **861** (pallina fuori, nera prima delle vive) | **1.688**, 3 vittime, 0 urti |
| Pista lunga seme 3 | 882 | 1.688 |
| Contorto seme 1 | **1.504** (LoP al secondo 32) | **1.742**, 0 LoP |
| Contorto seme 2 | 1.825 | 1.825 |
| Contorto seme 3 | – | 1.742, 0 LoP |
| Stress falso argento in rampa | 1.893, arrivo | 1.893, arrivo |
| Stress giroscopio disturbato 15° | **984** (LoP nella zona) | **1.468**, arrivo |
| Arena della scuola (2 semi), stress porta, arena (3), gara vecchia (2) | arrivo | arrivo, 3 vittime, 0 palline fuori |

Media sulle 9 prove di Shuri con punteggio: dall'85,7% al 95,5%. In tutte le 20 gare: nessuna LoP, nessuna pallina
fuori dal triangolo. Lo scarico "girandosi verso il triangolo" e la squadratura sull'uscita costano qualche secondo:
sulla pista lunga il robot esce dalla zona ma non arriva in fondo negli 8 minuti (come la V27).

**Da controllare sul robot vero**
- Lo scarico: con il triangolo di lato il robot ora arretra e ruota prima di scaricare. L'angolo usa
  `GradiPerPixelArena` (0,3): se la camera arena non è tarata il robot ruota troppo o troppo poco.
- L'uscita: appena vede la striscia nera, il robot si ferma, si raddrizza e si sposta di lato se serve. La misura usa
  il bordo basso della striscia e la taratura della camera linea (`CAM_LINEA_*`, come il FIX 71).
- Le soglie `USCITA_FERMO_S` / `USCITA_FERMO_PX`: se il robot vero vibra molto contro lo stipite, alzare i pixel.

---

## V27 – 29 ottobre 2026

**Da dove viene:** scatola nera `run_2026-10-29_09-33-01.jsonl` (V26) e la foto della piastrella con i due verdi in
diagonale. Tre richieste: il robot ogni tanto fa dietrofront su quella piastrella; è partito un ingresso in arena
mentre seguiva la linea; il robot deve capire dal giroscopio quando è su un tratto inclinato e scriverlo.

**Cosa dicono i dati**
- Dietrofront (secondo 61,8): all'incrocio YOLO ha detto "Sx", giusto, e il robot ha girato a sinistra. Finita la
  rotazione di 35 gradi, il seguilinea ha rivisto lo STESSO incrocio, ormai di traverso (linea inclinata di circa 40
  gradi). YOLO ha detto di nuovo "Sx", ma il controllo dei colori (FIX 36) cercava la linea dell'incrocio solo per
  righe orizzontali: ha messo il "confine" a metà immagine, ha contato tutti e due i verdi come validi e ha
  cambiato "Sx" in "Fr". Provato sulle miniature della scatola nera: la V26 dice "Fr" su quel fotogramma.
- Altri errori dello stesso controllo nelle scatole nere: al secondo 56,4 (29/10) e al 32,4 (21/10) il bordo scuro del
  nastro nero, visto un po' verde dalla camera, contava come un terzo verde ("Fr" invece di "Sx" e "Dx").
- Ingresso (secondo 93,6): il robot iniziava una rampa (beccheggio 15). YOLO ha visto "argento" dove c'era una curva,
  anche da fermo. Il controllo "non sono in piano" era `abs(roll) > 15`: 15 non è maggiore di 15, è passato. La
  striscia copriva tutta l'immagine, quindi non si poteva controllare se la linea continuava. Avanzando piano YOLO
  vedeva solo la linea ("Ln" 1,00) ma il robot è entrato lo stesso e ha avviato l'arena sulla rampa.
- Tratto inclinato: dal secondo 1 al 19 il rollio è -23 gradi fisso (il robot è inclinato di lato), poi ci sono
  rampe di 15-22 gradi, anche inclinate di lato.
- Al secondo 107 l'Arduino ha smesso di rispondere (laser e giroscopio a 0): controllare cavo USB e batteria.

**Correzioni**
- **FIX 78 – Controllo dei verdi con la linea inclinata.** Il controllo misura l'inclinazione della linea
  dell'incrocio e giudica i verdi lungo quella. Se la linea è più storta di `VERDE_ANGOLO_MAX` (20 gradi
  nell'immagine schiacciata, circa 12 veri) non giudica e decide YOLO. Le macchie verdi sottili o sfilacciate (il
  bordo del nastro) non contano. Su tutte le 79 miniature di incroci delle scatole nere: i 4 "Fr" sbagliati della V26
  spariscono, il vicolo cieco vero del 23/10 resta un dietrofront, nessun giudizio nuovo sbagliato.
- **FIX 79 – Dietrofront solo se sicuro.** I colori possono togliere un verde (falso verde) ma non aggiungerlo: se
  YOLO vede un verde solo, i colori non lo trasformano in un doppio verde. Un doppio verde visto da lontano aspetta il
  fotogramma successivo. Prima di girare, il robot si ferma e ricontrolla con un fotogramma nuovo.
- **FIX 80 – Lo stesso incrocio non si giudica due volte.** Dopo una svolta al verde, finché quell'incrocio è nella
  camera (al massimo 3 s), i verdi non si rivalutano. Dopo un dietrofront niente pausa.
- **FIX 81 – Ingresso in arena solo in piano.** Il robot deve essere in piano da almeno 1 s (giroscopio, FIX 82). Se
  avanzando verso la striscia YOLO vede solo la linea, l'ingresso si annulla. Dopo un falso argento il seguilinea
  non si ferma più a ricontrollarlo per 3 s.
- **FIX 82 – Pendenza dal giroscopio.** `Pendenza()` dice se il robot è in piano, in salita, in discesa o inclinato di
  lato, con i gradi: mediana dell'ultimo mezzo secondo (i dossi non contano), due soglie (8 gradi per iniziare, 5
  per finire). Si vede nel terminale (riga ASSETTO), nella finestra di stato (riquadro Giroscopio), nel cruscotto
  (sotto la rotta) e nella scatola nera (campo `pend`); quando inizia e finisce un tratto inclinato c'è un evento.
  Sui dati del 29/10: "INCLINATO 23 gradi" al secondo 1,1, poi le rampe, e "SALITA 15" al secondo 93,8, proprio dove
  è partito il falso ingresso. Da controllare: inclinate il robot a mano verso destra; se il cruscotto scrive
  "verso sinistra", cambiate `ROLLIO_POSITIVO_A_DESTRA` in ViennaDataConf.

**Simulatore V28.** Nuova piastrella con i verdi in diagonale (sulla pista lunga ce ne sono due) e un YOLO che può
vedere un falso argento all'inizio delle rampe, grande quanto l'immagine, come nella scatola nera. Con questo simulatore:
- falso argento sulla rampa: la V26 "entra nell'arena" sulla rampa e prende 8 LoP; la V27 annulla l'ingresso e arriva
  in fondo con le 3 vittime;
- campo RCJ 2026: V27 1.468 su 1.468 in 4 gare su 4 (come la V26);
- arena (3 semi), arena della scuola (2), gara vecchia (2): 3 vittime, uscita e arrivo in 7 prove su 7 (come la V26);
- pista lunga: nessuna LoP, i verdi in diagonale sempre giusti; in 8 minuti esce dalla zona ma non arriva in fondo;
- campo contorto: resta solo la LoP al secondo 32 che c'era già; sul seme 2 la V27 fa 1.825 punti (V26 1.564). Il
  dietrofront ricontrollato da fermo costa circa mezzo secondo per ogni vicolo cieco.
- I verdi in diagonale li superano sia la V26 sia la V27: nel simulatore YOLO non sbaglia come quello vero a metà
  svolta. L'errore della V26 si vede invece sui fotogrammi veri della scatola nera e sulla foto della piastrella
  girata di 20 gradi (V26: "Fr"; V27: non giudica, decide YOLO).
- Ancora da fare (già nella V26): sulla pista lunga a volte una pallina finisce 5 cm fuori dal triangolo verde.

---

## V26 – 26 ottobre 2026

**Da dove viene:** scatola nera `run_2026-10-26_12-43-25.jsonl` (V25). Il robot entra storto in arena e prende le
palline storte.

**Cosa dicono i dati**
- Ingresso: subito prima dell'arena c'è un incrocio con verde a destra. Il robot arrivava a 353 gradi, girava di
  42 (svolte "vecchie": il resto della curva lo fa il seguilinea) e vedeva l'argento a 41 gradi, a metà curva. È
  entrato così, 40 gradi storto (giusto era circa 83). E 41 è diventato RottaArena, la direzione dei muri per tutto
  il giro dei muri.
- Palline: ogni "correggo di X gradi verso la pallina" finiva oltre: -19 → girato di 26, +17 → 24, +4 → 8, -4 → 11.
  Misurato su tutte le rotazioni delle due scatole nere: il giroscopio vede la rotazione 0,21 s dopo il comando e,
  fermati i motori, il robot gira ancora di 5-7 gradi. Tre prese a vuoto sulla prima pallina, una sulla seconda.

**Modifiche**
- **FIX 71 – Ingresso dritto e centrato.** Agli incroci con verde il robot si ricorda la direzione prima della
  svolta + 90 gradi (`MemorizzaSvolta`); se l'argento arriva entro `SVOLTA_INGRESSO_S` (6 s) entra in quella
  direzione, agganciata al lato delle piastrelle più vicino (`RiferimentoGriglia`). Altrimenti: la linea sotto la
  striscia, poi il lato delle piastrelle. Prima di entrare ruota sul posto in quella direzione e si centra sulla
  porta (`CentraSullIngresso`): la striscia è lunga 25 cm, la camera ne vede circa 14; se si vede un'estremità, il
  centro della porta è a mezza striscia da lì e il robot si sposta di lato. Usa le misure della camera linea
  (`CAM_LINEA_*`, le stesse del simulatore).
- **FIX 72 – Rotazioni che tengono conto del ritardo.** `RuotaVerso`: rotazione continua fino a `RUOTA_ANTICIPO` (12)
  gradi, poi stop e attesa `RUOTA_ASSESTA_S`, poi colpi brevi con `RUOTA_PAUSA_S` di attesa. La correzione verso la
  pallina ora usa `RuotaVerso` (arriva entro 1,5 gradi). `Gira` si ferma in anticipo di "velocità × `GIRA_ANTICIPO_S`"
  gradi. In `Dritto` il tempo passato a raddrizzarsi non conta nella durata (il robot fa sempre la stessa strada).
- **FIX 73 – Ostacolo a squadra con le piastrelle.** La direzione di partenza si aggancia al lato delle piastrelle e
  ogni giro va a una direzione assoluta (`RuotaOstacolo`). Prima, arrivando un po' storto da una curva, il lato
  lungo finiva addosso all'ostacolo.
- **FIX 74 – Rotazioni grandi in arena** (`GiraInArena`, dopo lo scarico e nella ricerca): prima un passo indietro,
  poi rotazione ad anello chiuso; se è bloccata, indietro e riprova. Prima spingeva 8 s contro il muro.
- **FIX 75 – Riprova dell'ingresso.** Se la linea finisce entro `ARGENTO_RECENTE_S` (4 s) da quando YOLO ha visto
  l'argento (conferma da fermo fallita a metà curva), il robot riprova l'ingresso invece di cercare la linea e
  tornare indietro.
- **FIX 76 – Ricerca delle palline a scatti** (`RICERCA_A_SCATTI`): scatti fermi di 30 gradi fino al giro
  completo, poi si sposta e ricomincia. Prima poteva restare in una parte dell'arena (scatola nera 23/10: 100 s per
  la seconda pallina).
- **FIX 77 – Scarico vicino al muro.** Se davanti al triangolo il robot è ancora lontano ma un fianco tocca il muro,
  arretra, si stacca di qualche cm e riprova (prima la pallina cadeva 4 cm fuori dal triangolo).

**Simulatore V27.** Aggiunto il ritardo del giroscopio (0,1 s) e servo più lenti a partire e fermarsi: come nelle
scatole nere, la rotazione si vede 0,2 s dopo il comando e il robot gira 5-7 gradi oltre. Sulla pista lunga c'è un
incrocio con verde subito prima dell'ingresso, come a scuola. Con questo simulatore:
- V25 entra storta di 37 gradi, come il robot vero; V26 entra a 90 gradi esatti e centrata sulla porta;
- pallina sotto la pinza: V25 fino a 1,7 cm di lato, V26 0,1 cm;
- campo RCJ 2026: V26 1.468 su 1.468 in 4 gare su 4 (V25: 1 su 3, nelle altre una LoP);
- arena (3 semi), arena della scuola (2 semi), gara vecchia (2 semi): V26 salva le 3 vittime, esce dalla porta
  giusta e arriva sulla linea rossa in tutte e 7 le prove;
- pista lunga: V26 senza LoP; in una gara arriva in fondo in 7 min 58 s con le 3 vittime.
- Ancora da fare: sulla pista lunga a volte la pallina viene portata davanti al muro accanto al triangolo (la
  memoria della direzione del triangolo è sbagliata); sul campo contorto resta una LoP al secondo 32 (c'è anche con
  la V25).

## V25 – 23 ottobre 2026

**Da dove viene:** scatola nera del robot vero `run_2026-10-23_10-26-28.jsonl` (V24). Problemi con l'ingresso e
l'uscita dell'arena; la squadra ha notato che costeggiando il muro il robot non tiene la distanza.

**Cosa dicono i dati**
- Nel giro dei muri il robot doveva stare a 5 cm: stava a 10-27 cm (mediana per parete) e lungo ogni parete si
  allontanava fino a 30-35 cm.
- Il motivo è nei servo a rotazione continua: arrivano quasi subito al massimo. Misurato sulla scatola nera: a
  velocità 47, con uno sterzo tra -50 e +50 il robot gira di 0-5 gradi al secondo, cioè **non sterza**. Solo la
  rotazione sul posto (sterzo 100) gira davvero, a 30-45 gradi al secondo.
- La velocità vera è circa 10-12 cm/s (quasi uguale a velocità 34, 47 o 68), non 17-24 come si pensava: i tempi
  di ingresso e uscita erano troppo corti.
- In `Dritto` la derivata del PID, al primo giro, divideva per pochi microsecondi: a ogni chiamata partiva un colpo
  di rotazione al massimo ("Sterzo 47 100" ogni 0,1 s nella scatola nera). Era l'unica cosa che faceva sterzare.
- Agli angoli `Gira` si fermava a 3 gradi dall'obiettivo ma il robot continuava a ruotare: 8-14 gradi oltre.
- Al secondo 596, già uscito, il robot ha ritrovato la linea girando di 60 gradi, è tornato indietro ed è
  **rientrato nell'arena**.
- Persi anche circa 100 s a cercare la seconda pallina (115-212 s) e 14 s di "BOOSTER" sinistra/destra su una curva
  (33-46 s): non toccati in questa versione.

**Modifiche**
- **FIX 63 – Muro a distanza costante** (`SeguiParete`). `LATO_MURO_CM` = 6,5 (prima 5: con 5 cm il robot non
  aveva spazio per girarsi negli angoli). A ogni passo: distanza vera = laser laterale × coseno dell'angolo;
  angolo voluto verso il muro = `PARETE_KP` × errore (max `PARETE_ANGOLO_MAX`); se il robot è storto più di
  `PARETE_ERR_RUOTA` gradi si raddrizza ruotando sul posto, poi avanza. Con `PARETE_STIMA` il robot capisce da come
  cambia la distanza avanzando se la direzione del muro è sbagliata e la corregge a poco a poco. Mediana di 3
  letture, direzione voluta che cambia al massimo di 8 gradi per passo (vicino ai triangoli il robot "ballava").
  Subito dopo un angolo, se il laser laterale vede lontano, controlla l'apertura (porta proprio nell'angolo).
  Avanzamento verso un'apertura dubbia fino a 2,5 s (prima 1 s: la striscia restava fuori dalla camera).
- **FIX 64 – Rotazioni e Dritto.** Nuovo `Rwd.RuotaVerso(rotta)`: rotazione sul posto ad anello chiuso col
  giroscopio, a piccoli colpi vicino all'obiettivo (non va oltre). `GiraA` la usa (tolleranza 3 gradi). In
  `Dritto`: niente più colpo della derivata; se l'errore supera `DRITTO_RUOTA_GRADI` (6) il robot si raddrizza
  ruotando sul posto. `DRITTO_RUOTA_GRADI = 0` = come prima.
- **FIX 65 – Giroscopio come sensore di tocco.** Se il robot deve ruotare ma per `BLOCCO_S` (0,6 s) la direzione
  cambia meno di `BLOCCO_GRADI` (2), sta toccando qualcosa: arretra e riprova (prima aspettava 4 s di timeout,
  nella scatola nera due volte). Nel giro dei muri, pitch o roll oltre `PARETE_MAX_INCLINAZIONE` (8) = sta salendo
  su qualcosa: arretra.
- **FIX 66 – Niente secondo ingresso.** Dopo l'uscita (`UscitaArenaFatta`), una striscia argento confermata vuol
  dire che il robot sta tornando indietro sulla linea: dietrofront. `ARENA_UNA_VOLTA = False` = come prima.
- **FIX 67 – `VelocitaArenaCmS` = 10** (prima 17), misurata sulla scatola nera. Da ricronometrare su 1 metro.
- **FIX 68 – Ingresso e uscita completi.** `TempoEntrataArena` 1,2 → 2,5 s e `TempoUscitaPorta` 1,5 → 2,5 s: a
  11 cm/s il robot entrava di soli 13-14 cm e restava con il retro fuori dall'arena.
- **FIX 69 – Uscita nel muro davanti** (`EsciDallaPortaDavanti`). Seguendo il muro il robot trova la striscia nera
  davanti: si mette con il fianco a `PORTA_LATO_CM` (9,5 cm) dal muro che seguiva (se serve si sposta di lato) ed
  esce dritto lungo la direzione del muro. Così passa sia se la porta comincia nell'angolo sia se comincia 8 cm più in
  là, come nell'arena della scuola (prima sfiorava lo spigolo).
- **FIX 70 – Porta nell'angolo e triangoli** (pista lunga del simulatore).
  - Se misurando un'apertura il robot arriva al muro davanti, la porta finisce nell'angolo: invece di tornare
    indietro di metà, avanza fino a `PORTA_ANGOLO_CM` (4 cm) dal muro davanti (centro in mezzo alla porta) e da lì
    si gira. Prima si fermava contro lo stipite e restava incastrato.
  - "Non avanzo" con il muro davanti a meno di 20 cm = angolo (lo spigolo tocca il lato lungo del triangolo prima
    che il laser frontale lo veda a 8 cm).
  - "Non avanzo" lontano dagli angoli: arretra, si gira di 20 gradi e continua a seguire il muro (prima andava
    dritto fino al muro davanti e poteva passare davanti all'uscita senza vederla). Niente più falsi "Non avanzo"
    mentre il robot si raddrizza a piccole rotazioni.
  - `RuotaVerso` si accorge del blocco anche nelle rotazioni a piccoli colpi.

**Simulatore V26.** Nuovo modello dei servo `"reale"`, tarato sulla scatola nera (velocità ~11 cm/s, rotazione sul
posto ~35 gradi/s, sterzate piccole che non fanno girare). Con questo modello il simulatore rifà gli stessi errori
del robot vero (V24: muro a 16-17 cm di mediana). Risultati V25:
- prova della sola uscita, arena con ingresso e uscita sullo stesso muro (come a scuola): uscito 4 su 4 in 61 s
  (V24: 2 su 3, in 75-182 s); arena normale: 4 su 4 in 33 s;
- sui tratti dritti il robot sta a 7-8 cm dal muro;
- campo RCJ 2026: 1.468 punti su 1.468 in 3 gare su 3 (V24: 1 su 2), senza LoP;
- gara completa: uscita dall'arena in 37-45 s dopo l'ultima pallina (V24: 150-350 s).
- pista lunga (84 piastrelle, arena 4 × 4 con ingresso e uscita sullo stesso muro): uscito dalla porta giusta 4 gare
  su 4, 0 LoP; tutta la pista in 8 min 4 s - 8 min 46 s (punteggio pieno, 1.866, quando salva le 3 vittime). In gara
  vera il limite è 8 minuti: su una pista così lunga servirebbe un robot più veloce.
- Limite: con un errore del giroscopio di ±15 gradi che cambia con la direzione (`bussola_distorsione`) il robot
  trova l'uscita ma ci passa storto e può incastrarsi sullo stipite.

## V24 – 22 ottobre 2026

**Problema visto nel nuovo campo "contorto" del simulatore** (serpentone di file a 30 cm l'una dall'altra, 15
interruzioni): quando un'interruzione viene subito dopo una curva o dopo una curva a U (due piastrelle curve di
fila), YOLO vede "Di" mentre il robot sta ancora girando. La V23 si fermava lì, si allineava e partiva: dopo una U
attraversava il vuoto verso nord invece che verso ovest e finiva sulla fila vicina. LoP in tutte le 8 gare.

- **FIX 62 – Interruzioni dopo una curva** (`SeguiFinoAlVuoto`, `AttraversaVuoto`).
  - Visto "Di", il robot segue piano il nastro fino alla sua FINE, sterzando verso la parte più lontana del
    nero (come chi guida guarda lontano). Se il nastro esce da un lato dell'immagine il robot è ancora in curva:
    gira sul posto di 15° da quella parte e continua.
  - Poi attraversa il vuoto dritto col giroscopio (`AttraversaVuoto`), al massimo `GAP_TEMPO_MAX` secondi.
  - La direzione del vuoto si aggancia ai lati delle piastrelle: alla partenza il robot misura com'è orientato
    il campo (`RiferimentoGriglia`), e da regolamento prima di ogni vuoto c'è un pezzo di linea dritto, quindi a
    90° dagli altri. Se il robot è entro `GAP_SCATTO_GRADI` (42°) da un lato, attraversa in quella direzione
    esatta. Se stava curvando (più di `GAP_CURVA_GRADI_S` = 25°/s nell'ultimo secondo) vale il lato successivo
    nel verso della curva: a metà di una U verso nord-ovest il pezzo dritto va a ovest, non a nord.
  - `GAP_SEGUI_FINO_AL_VUOTO = False` rimette il comportamento della V23.
- **Simulatore** (simulatore V25): campo contorto a punteggio pieno, 1.989, in tutte e 8 le gare (V23: media
  1.045); campo 2026 sempre 0 cadute e 0 LoP sulla linea; percorso vecchio, arena della scuola e falsi verdi come
  prima.
- **L'ostacolo del campo contorto non era un errore del robot.** Nel simulatore V24 l'arbitro chiamava la LoP
  appena il robot, girando intorno all'ostacolo, passava sopra la piastrella vicina che contiene un'altra linea.
  Il regolamento la chiama solo se il robot raggiunge e segue una linea fuori sequenza: nel simulatore V25
  intorno all'ostacolo si può passare, e `OstAutDet` rientra sempre sulla linea giusta.

## V23 – 22 ottobre 2026

**Problema visto nel simulatore:** quando perdeva la linea il robot andava avanti alla cieca. Sull'altopiano
(22 cm) cadeva dal bordo: 14 cadute in 6 gare con la V22. Agli incroci senza verde presi di traverso seguiva il
braccio sbagliato: fino a 3 LoP a gara.

- **FIX 57 – Interruzioni** (`AttraversaInterruzione`). Prima, con YOLO "Di", una sterzata secca di 0,25 s e poi
  0,9 s dritto alla cieca nella direzione in cui il robot si trovava: dopo una curva era storto e attraversava il
  vuoto di sbieco. Ora: arretra 0,35 s (la camera vede il pezzo dritto prima del vuoto), si allinea a quel pezzo
  con una retta sui pixel neri in 2–4 piccole rotazioni, poi va dritto tenendo la direzione col giroscopio finché
  rivede la linea (al massimo `GAP_TEMPO_MAX` = 2 s).
- **FIX 58 – Linea persa, ricerca sicura** (`RecuperaLinea`). Il robot non va MAI avanti senza linea: ruota sul
  posto a ventaglio (`RECUPERO_ANGOLI`: ±30, ±60, ±90, ±120 gradi col giroscopio) e guarda dopo ogni rotazione;
  se non la trova arretra a piccoli passi sulla strada già fatta (`RECUPERO_RETRO_S` = 1 s) e rifà il ventaglio.
  Se non la trova ancora resta fermo: meglio una LoP che una caduta. Il ventaglio arriva a 120° perché dopo un
  angolo acuto la linea riparte quasi all'indietro. `RECUPERO_SICURO = False` rimette la ricerca di prima.
- **FIX 59 – Incroci senza verde** (`AnalizzaIncrocio`, `IncrocioDritto`). Il PID seguiva il baricentro del nero:
  arrivando storti a un incrocio (dopo un anello, una curva stretta) prendeva il braccio laterale. Ora, se YOLO non
  vede verdi, il codice guarda dove la linea tocca i bordi dell'immagine: con 3 o 4 bracci collegati, un tratto
  dritto nero da sotto a sopra e almeno un braccio laterale quasi perpendicolare è un incrocio. Il robot si gira
  verso il braccio opposto a quello da cui arriva e attraversa dritto col giroscopio (`INCROCIO_DRITTO_S` = 0,7 s).
  Provato su curve, curve strette, zig-zag, angolo retto, angolo acuto, onde, detriti, incroci con verde: nessun
  falso incrocio. `INCROCI_DRITTI = False` rimette il comportamento di prima.
- **Simulatore** (8 gare sul campo 2026): 0 cadute e 0 LoP sulla linea in tutte e 8 (V22: 12 cadute e 30 LoP sulla
  linea in 6 gare). Tre gare a punteggio pieno, 1.468. Media da 794 a 1.166 punti. Percorso vecchio, arena della scuola e
  falsi verdi: tutto come prima.
- **Resta da fare: l'uscita dalla zona.** In 5 gare su 8 il robot trova l'uscita ma ci arriva storto o spostato:
  una fiancata tocca lo stipite e resta lì a spingere fino alla LoP. Senza uscita si perdono le ultime piastrelle e
  il bonus, circa 480 punti. È il prossimo lavoro.
- **Da provare sul robot vero**: il ventaglio e la retromarcia si vedono nel terminale ("Linea ritrovata girando di
  … gradi" / "tornando indietro"); all'incrocio "Incrocio senza verde: lo attraverso dritto". Se il robot arretra
  troppo dopo un'interruzione, abbassate `GAP_RETRO_S`; se non arriva dall'altra parte del vuoto, alzate
  `GAP_TEMPO_MAX`.

## V22 – 22 ottobre 2026

**Problema visto nel nuovo simulatore (campo RCJ 2026 con rampe):** arrivato ai piedi della rampa il robot
partiva con il giro dell'ostacolo e girava intorno alla rampa. Succedeva in tutte e 6 le gare simulate.

- **FIX 56 – Ostacolo o rampa?** (`ConfermaOstacolo`). Il laser frontale è a circa 6 cm da terra: davanti a una
  rampa di 20° colpisce la salita a 14–15 cm, quando il robot è ancora in piano. Per il codice (laser sotto 15 cm
  e robot in piano) era un ostacolo. Ora, quando il laser scende sotto 15 cm, il robot avanza piano per al
  massimo 1,5 s:
  - se il laser arriva a 8 cm (`OST_CONFERMA_CM`) è un ostacolo vero: si ferma, arretra di poco e parte `OstAutDet`;
  - se il robot si inclina più di 6° (`OST_RAMPA_GRADI`) è una rampa: le ruote davanti stanno salendo, e il
    seguilinea continua. Una rampa da 20–25° non porta mai il laser sotto 13 cm;
  - se non succede nessuna delle due cose, per sicurezza è un ostacolo.
- **Simulatore**: la rampa ora viene salita in tutte e 6 le gare (prima mai). Media del punteggio 2026 da 519 a
  794 punti su 1.468; l'ostacolo vero viene sempre confermato a 8 cm e aggirato, anche nel percorso vecchio.
- **Da provare sul robot vero**: ai piedi della vostra rampa il robot deve scrivere "Non è un ostacolo: il robot
  si inclina…"; davanti al mattone "Ostacolo confermato a 8 cm". Se con la rampa vera il laser scende sotto 8 cm
  (il VL53L1X ha un cono di 27° e può vedere la salita prima), abbassate `OST_CONFERMA_CM` a 6. Se il robot non
  si inclina abbastanza in 1,5 s, alzate `OST_TEMPO_CONFERMA` a 2.

## V21 – 22 ottobre 2026

**Problemi visti nel simulatore:** palline lasciate fuori dai triangoli, la seconda pallina argento mai presa,
l'ostacolo sbagliato al primo tentativo.

- **FIX 54 – Palline dentro il triangolo e ostacolo.**
  - *Scarico*: prima il robot arrivava al triangolo e tornava indietro di 0,4 s prima di aprire la pinza, e la
    pallina cadeva 3–8 cm prima del bordo. Nuova `AccostaTriangolo()`: si avvicina piano finché il laser
    frontale legge `SCARICO_CM` = 3 cm (o finché non avanza più) e lascia la pallina da lì. Se il braccio,
    scendendo, tocca il bordo, alzate `RETRO_SCARICO_S` (prima era 0,4).
  - *La seconda argento*: non era una presa sbagliata. Il robot lasciava la A2 fuori dal triangolo, la
    ritrovava lì davanti, la riprendeva e la contava come seconda argento: la A1 restava in arena. Con lo
    scarico corretto vengono salvate tutte e tre.
  - *Ostacolo*: sul lato lungo il codice partiva da `Dis=25` e "andava avanti finché il laser vede il blocco"
    solo se `25 > DisTarg+10`. Con `DisTarg` = 15 la condizione era falsa: il robot girava subito contro
    l'ostacolo e poi ritrovava la linea nel verso sbagliato. Ora parte da 999. In più l'ostacolo usa
    `LaserVeri()` (0 = lontano): prima lo 0 diventava "ostacolo a 13 cm".
- **FIX 55 – Il robot si accorge di essere incastrato** (`RobotFermo`). Costeggiando le pareti, se l'uscita è
  vicino a un angolo il laser frontale guarda dentro la porta e vede "libero", mentre il fianco tocca lo
  stipite: il robot spingeva per sempre. Ora, se il laser frontale vede qualcosa e la distanza non diminuisce,
  oppure se davanti è libero e l'immagine della camera arena non cambia per 1,5 s, il robot arretra, si stacca
  dalla parete e riprova guardando il pavimento (striscia nera = esce, argento = ingresso).
  Inoltre `GiroDeiMuri` riconosce un'apertura anche quando il robot ci arriva in diagonale (basta che poco
  prima la parete fosse entro 20 cm): prima al primo giro poteva passare davanti all'uscita senza vederla.
- **Simulatore**: tutte le prove arrivano al traguardo con le 3 palline nei triangoli giusti (gara completa
  con laser normali e con laser a 0 come i vostri, arena, arena della scuola anche con YOLO che non vede le
  porte). L'ostacolo è superato al primo tentativo.

## V20 – 22 ottobre 2026

- **FIX 52 – Svolte agli incroci come nel codice originale** (richiesta della squadra: sul campo vero ci
  sono incroci di forma strana). In `ViennaDataConf.py` `SVOLTE = "vecchie"`: avanti 0,45 s (0,40 in
  pendenza), poi `Gira(42)` a destra o `Gira(-35)` a sinistra (`-37` in pendenza), e il seguilinea finisce la
  curva. Con `SVOLTE = "nuove"` si torna al metodo del FIX 41. Nel simulatore con le svolte vecchie tutti gli
  incroci della gara sono superati.
- **FIX 53 – Uscita dall'arena costeggiando le pareti** (metodo proposto dalla squadra). Dopo l'ultima
  pallina (`USCITA_MODO = "muri"`):
  1. sceglie da che parte fare il giro: la parete laterale più vicina (`ScegliLatoGiro`);
  2. si mette parallelo alle pareti e va vicino a quella scelta, guardando il pavimento (`AvvicinatiAlMuro`);
  3. costeggia la parete tenendo il fianco a **`LATO_MURO_CM` = 5 cm**; agli angoli e davanti ai triangoli
     (laser frontale sotto `ANGOLO_CM` = 8 cm) gira di 90° (`GiroDeiMuri`);
  4. quando il laser laterale **salta** oltre `APERTURA_CM` = 15 cm (prima seguiva la parete a 5) c'è
     un'apertura: continua finché il laser rivede la parete per misurarla, **torna indietro** di metà fino al
     centro, si gira verso l'apertura, si allontana un po' (`INDIETRO_CAMERA_S`) e la guarda con la **camera
     arena** (modello delle porte: uscita / ingresso, 3 foto), poi torna e guarda il **pavimento** con la
     camera linea (striscia nera / argento) (`ControllaAperturaMuro`);
  5. **uscita** → esce guardando il pavimento e riparte il seguilinea; **ingresso** → si rigira nel verso
     di marcia, supera l'apertura e continua il giro.
  Se in `TEMPO_MAX_MURI` (150 s) non trova l'uscita passa al metodo di prima con la camera.
  Altre protezioni: il nero vince sull'argento uscendo (il riflesso del 21/10), l'argento va visto in 2
  fotogrammi di fila, se Arduino tace il robot si ferma invece di guidare alla cieca, se una rotazione non
  riesce (spigolo contro un triangolo) arretra e riprova.
  Nel simulatore (arena normale, arena della scuola con ingresso e uscita sullo stesso muro, anche con YOLO
  che non vede le porte) il robot esce sempre dalla porta giusta; la camera arena e il pavimento sono sempre
  d'accordo.

## V19 – 21 ottobre 2026

**Problema segnalato:** alcune scritte non si leggono bene e le immagini delle due camere spesso si bloccano.

- **FIX 51 – Finestra "ClaudeRob - STATO" rifatta.**
  - **Le camere sono dentro la finestra**, a sinistra, e si aggiornano 5 volte al secondo qualunque cosa stia
    facendo il robot. Prima erano le finestre `Linea` e `Arena` di OpenCV, che il programma del robot aggiorna
    solo quando se ne ricorda: durante svolte, retromarce e pause sembravano bloccate (le camere invece
    funzionavano). Sotto ogni camera: "dal vivo", oppure da quanto tempo non arriva un'immagine nuova
    (la camera linea diventa rossa se si ferma davvero; la camera arena il programma la usa solo nell'arena).
    Le vecchie finestre non si aprono più; per riaverle `FINESTRE_CAMERE = True` in `ViennaDataConf.py`.
  - **Testi con un carattere vero** (DejaVu Sans, già sul Raspberry, disegnato con Pillow): niente più
    scritte "a stecchini", accenti corretti, nessun testo sotto i 14 pixel, grigi più chiari.
    Se Pillow manca la finestra usa il carattere di prima.
  - Nuovo tasto **`m`**: sulla camera linea mostra la **maschera del nero**, cioè quello che il robot considera
    linea con la soglia attuale (utile con `TaraNero.py`).
  - Anche nel terminale il grigio scuro è diventato grigio chiaro.
  - La finestra ora è larga 1300 pixel: se lo schermo è più piccolo si può ridimensionare col mouse.

## V18 – 21 ottobre 2026

**Problema segnalato:** con la V17 di nuovo `can not open gpiochip`, questa volta dentro gpiozero
(`LGPIOFactory(chip=numero)`), anche se un attimo prima lo stesso chip si era aperto senza problemi.

- **FIX 50 – Le luci non usano più gpiozero** (`ViennaClsRobot.py`, funzione `CreaLuci`).
  Il robot usa gpiozero solo per i due relè delle luci (GPIO22 e GPIO23). Ora:
  1. cerca il chip `pinctrl-rp1` (qualunque numero abbia) e comanda le luci **direttamente con lgpio**,
     tenendo il chip aperto;
  2. se non lo trova (Raspberry più vecchio, simulatore) usa `gpiozero.LED` come prima;
  3. se non funziona niente, il robot **parte lo stesso senza luci** e scrive un avviso ben visibile.
  Le luci si usano come prima (`Rwd.linee['Luce1'].value = 0` accesa, `1` spenta).
- Nuovo **`ProvaGPIO.py`**: elenca i chip GPIO con il loro nome e fa lampeggiare 3 volte le luci,
  senza avviare il robot.
- `ScattaCalibrazione.py` usa le stesse luci (`CreaLuci`).

## V17 – 19 ottobre 2026

**Problema segnalato:** dopo l'aggiornamento del Raspberry del 18/10 il programma si fermava subito con
`can not open gpiochip` (prima ancora: `Cannot determine SOC peripheral base address`) su `LED(22)`.

- **FIX 49 – Scelta automatica del chip GPIO** (`ViennaClsRobot.py`, funzione `_scegli_chip_gpio`).
  Dopo l'aggiornamento i chip dei GPIO si chiamano `/dev/gpiochip11` … `gpiochip15`, mentre gpiozero cercava
  il numero 4 (o 0). All'avvio ora si provano tutti i chip e si usa quello che si chiama `pinctrl-rp1`
  (il connettore a 40 pin del Pi 5), qualunque numero abbia. All'avvio compare la riga
  `GPIO: uso /dev/gpiochipNN (pinctrl-rp1, 54 linee)`.
  Funziona anche con la numerazione vecchia e se cambierà di nuovo; su un Raspberry diverso dal Pi 5 o nel
  simulatore non fa niente e gpiozero decide come prima.

## V16 – 15 ottobre 2026

**Problema segnalato:** all'uscita il robot vede la striscia nera, ma parte la ricerca della porta con i laser.

- **FIX 48 – Uscita dall'arena.**
  - **Laser a 0 = lontano.** Il VL53L0X manda 0 quando non vede niente entro circa 1,2 m, per esempio
    guardando fuori dalla porta. `EsciDallaPorta` lo prendeva per "muro a meno di 35 cm" e partiva
    "Muro davanti: scorro lungo la parete". Nuova `LaserVeri()`: nelle funzioni dell'uscita uno 0 vale
    `LASER_LONTANO` (150 cm). Se Arduino non risponde, gli 0 restano 0.
  - **Prima il pavimento, poi i laser.** Nuova `AvvicinatiAllaPorta()`: arrivato alla porta, il robot avanza
    piano (al massimo `AvvicinamentoPorta` = 30 cm) guardando sotto il muso. Striscia **nera** = uscita
    confermata: torna indietro, si centra sulla porta ed esce, senza guardare i laser. Striscia **argento**
    = ingresso. Nessuna striscia = manovra di prima con i laser (ora corretti).
  - **Tolto** il controllo "è l'ingresso?" fatto con il modello della camera linea sull'immagine della camera
    arena: poteva sbagliare e far partire il giro dei muri.
  - Mentre scorre lungo la parete e durante il giro dei muri, un laser laterale a 0 ora vuol dire "apertura".
    Mentre scorre lungo la parete guarda anche il pavimento.
  - **Simulatore:** i laser fuori portata ora mandano 0 come sul robot vero (prima 200: per questo l'errore
    non si vedeva). Con la V15 l'errore si riproduce ("Muro davanti: scorro lungo la parete"); con la V16 le
    5 prove dell'arena arrivano al traguardo e nell'arena della scuola il robot esce in 124 s invece di 184.
  - **Da sapere:** con i laser a 0 l'aggiramento dell'**ostacolo** nel simulatore non riesce (il codice
    tratta lo 0 come "ostacolo a 13 cm"). Non è stato modificato: da verificare sul robot vero.

## V15 – 15 ottobre 2026

- **FIX 47 – Eventi in tempo reale nella finestra "ClaudeRob - STATO".** Il riquadro in basso ora è più
  grande (circa 20 righe; la finestra è alta 820 pixel e si può ridimensionare) e mostra **tutto** quello che
  il programma scrive, appena succede: ogni `print` in grigio (anche quelle che il terminale nasconde come
  rumore, per esempio `Alto`, `Basso 12`, `distanze ...`) e gli eventi importanti tradotti, a colori.
  Il più recente è in alto. Tasti, con la finestra selezionata:
  - `t` = passa da **TUTTI** a **SOLO IMPORTANTI** e viceversa;
  - `spazio` = **pausa**: la lista si ferma per leggerla con calma (i sensori sopra continuano ad aggiornarsi);
  - `q` = chiude la finestra (il robot continua).

## V14 – 15 ottobre 2026

- **FIX 44 – `Gira` ferma i motori quando ha finito.** Prima usciva lasciando le ruote a velocità `VelCrs`:
  se dopo c'era una pausa il robot continuava a ruotare (nel simulatore `Gira(90)` + 0,5 s = 132 gradi).
  Molti angoli del codice erano stati regolati contando su questa rotazione "nascosta"; ora sono scritti
  con i gradi veri, stimati col simulatore (**da verificare sul robot**):

  | Dove | Prima | Ora |
  |---|---|---|
  | Dietrofront in pendenza (`CrosFFIncl`) | `Gira(±100)` + 0,5 s | `Gira(±170)` come `CrosFF` |
  | "Correggo per bianco" dopo le svolte | `Gira(±10)` + 0,2 s | `Gira(±25)` |
  | Arena, inizio ricerca palline | `Gira(±3)` + 0,5 s | `Gira(±40)` |
  | Arena, fronte occupato | `Gira(±9)` + 0,5 s | `Gira(±45)` |
  | Arena, dopo aver scaricato l'argento | `Gira(80)` + 1 s | `Gira(160)` |
  | Arena, dopo aver scaricato la nera | `Gira(-120)` + 0,5 s | `Gira(-160)` |
  | Arena, dopo la retromarcia | `Gira(25)` + 0,1 s | `Gira(30)` |

  Nuova `FotogrammaNuovo()`: dopo una rotazione aspetta un'immagine scattata a robot fermo (ricerca della
  linea quando vede bianco).
- **FIX 45 – Soglia del nero regolabile.** Un pixel è "nero" se la luminosità V è sotto `SOGLIA_NERO`
  (prima fissa a 80, ora 110 in `ViennaDataConf.py`). Nelle foto di calibrazione il nastro nero arriva fino
  a V 105 per i riflessi, e con 80 si perdeva il 17–25% della linea. Nuovo **`TaraNero.py`** per tarare la
  soglia sul campo di gara: salva `taratura_nero.json`, che il robot legge all'avvio.
- **FIX 46 – Ingresso e uscita dell'arena in due funzioni con i controlli sulle strisce.**
  - `TrovaIngressoArena()`: quando YOLO vede l'argento, il robot si ferma e controlla che sia in piano,
    che YOLO lo riveda da fermo e che **oltre la striscia la linea nera non continui** (all'ingresso la
    linea finisce). Solo allora entra dritto col giroscopio.
  - `TrovaUscitaArena()`: cerca l'uscita come prima (camera dell'arena, poi giro dei muri), ma ogni uscita
    ora passa da `EsciControllando()`, che guarda il pavimento a ogni passo: se passa sull'**argento** era
    l'ingresso, torna dentro e la ricerca continua; se passa sul **nero** l'uscita è confermata. Fuori
    dall'arena controlla di ritrovare la linea.
  - Nel simulatore tutte e 9 le prove arrivano al traguardo, anche con un falso argento a inizio percorso.

## V13 – 12 ottobre 2026

**Problema segnalato:** i dati dei laser sparivano mentre il robot girava e non si capiva quale azione
stesse facendo il robot.

- **FIX 43** – Monitor e finestra di stato:
  - **Laser:** quando un laser è fuori portata (o il raggio colpisce il muro troppo di sbieco mentre il
    robot ruota) il sensore manda 0 e prima al suo posto compariva solo un trattino. Ora c'è scritto
    `fuori portata` e accanto l'ultimo valore buono con l'età (`era 31 cm, 0.4 s fa`), con la barra in grigio.
  - **Arduino:** se Arduino non manda dati per più di 0,3 s, `ViennaClsRobot` mette a 0 laser **e giroscopio**.
    Ora nella finestra compare un riquadro rosso `ARDUINO NON RISPONDE` e negli eventi (e nella scatola nera)
    resta scritto quando ha smesso e dopo quanti secondi è tornato. Se succede durante le svolte, il robot
    gira "alla cieca": è un problema elettrico (cavo USB, batteria, disturbi dei motori), non di codice.
  - **Riga ORA** (in giallo, sempre visibile): cosa fanno le ruote in questo istante, in italiano
    (`ruoto SUL POSTO verso DESTRA`, `avanti dritto`, `INDIETRO curvando a SINISTRA`, `FERMO`).
    Durante una `Gira` mostra anche quanti gradi ha fatto: `giro a DESTRA di 75 gr: fatti 41`.
  - Nomi in italiano anche per le fasi aggiunte nelle ultime versioni (avanzo sull'incrocio, finisco la
    svolta, giro lungo i muri, guardo il pavimento, esco sulla striscia nera...).
  - La stessa riga ORA è nel pannello del terminale (ora 8 righe) e nella riga riassuntiva.

## V12 – 12 ottobre 2026

**Richiesta della squadra:** vedere sempre i dati di tutti i sensori e quale operazione sta facendo il robot.

- **FIX 42** – Nuovo `ViennaPannello.py`: quando parte `RwdFoto.py` si apre da sola la finestra
  **"ClaudeRob - STATO"** (sul desktop del Raspberry, anche in VNC). Si aggiorna 5 volte al secondo e mostra:
  - in grande l'**operazione in corso** (es. `Incrocio: giro a DESTRA`), sotto il percorso (`Seguilinea`) e la
    manovra del momento (`ora: Gira +75 gradi`), il tempo e lo switch;
  - i 3 **laser** con le barre (gialle sotto 30 cm, rosse sotto 15), la **bussola** con rotta, beccheggio e rollio;
  - la classe di **YOLO** con la sicurezza, decisioni al secondo e fps della camera;
  - **motori** (comando, velocità, sterzo), **braccio**, **pinza**, **LED**;
  - **Raspberry** (temperatura, 5 V, fulmine), **batteria**, palline salvate;
  - gli ultimi 7 **eventi**.
- La finestra gira in un processo a parte: si aggiorna anche durante le manovre lunghe, funziona sia da
  terminale sia da Thonny, e se la chiudete il robot continua. Si spegne con `PANNELLO = False`.
- Da Thonny, oltre alla finestra, ogni secondo esce una riga con tutti i valori (`RIGA_OGNI`).

## V11 – 12 ottobre 2026

**Problema visto nel video:** all'incrocio con il verde prima dell'ingresso dell'arena il robot gira solo a
metà (circa 45°), torna sulla linea dritta e finisce contro la parete.

**Causa:** le svolte (`CrosDx`, `CrosSx` e le versioni `Incl`) avanzavano per un tempo fisso e poi giravano
di soli 35-42°, lasciando il resto al seguilinea. Il robot gira attorno al centro delle ruote, 11,5 cm dietro
il muso: nel video cominciava a girare circa 11 cm prima dell'incrocio. Dopo 42° la camera vedeva ancora
la linea vecchia e il seguilinea lo riportava indietro.

- **FIX 41** – Svolte agli incroci:
  - `AvanzaSullIncrocio`: il robot guarda la linea trasversale scorrere nell'immagine, ne ricava la sua
    velocità vera e avanza finché il **centro delle ruote è sopra l'incrocio**. Non serve misurare la velocità.
  - poi gira di 75° (`SVOLTA_BASE`) e continua a ruotare piano finché la linea nuova è **davanti al muso**
    (`CompletaSvolta`), mai oltre 115° (`SVOLTA_MAX`). Se non la trova, si mette a 90° esatti col giroscopio.
  - nel terminale compaiono `Incrocio: velocità … cm/s` e `Svolta completata …`.
- **FIX 41 (verdi)** – Se un attimo prima i colori hanno detto "falso verde", il robot va dritto anche quando
  l'incrocio è ormai troppo in basso nell'immagine per giudicarlo di nuovo.
- Simulatore: svolte riuscite con il robot lento, normale e veloce.
- **Cruscotto 3D con il robot vero:** i vostri 5 file STL (base, copertura, cupola della webcam, telaio dei servo,
  supporto pinza e webcam) sono uniti in `cruscotto/robot.stl` e il cruscotto mostra quello al posto dei blocchi.
  Ruote, braccio e pinza restano disegnati a parte perché si muovono.
- Dai file STL il robot risulta largo 15,6 cm con le alette dei paraurti: il simulatore ora usa 15,6.

## V10 – 12 ottobre 2026

**Misure prese dalla squadra:** robot 21,5 × 15 cm, muso a 11,5 cm dal centro delle ruote, laser frontale al
centro del muso (6,4 cm da terra), laser laterali 10 cm dietro il muso (5,8 cm da terra), porte da 27 cm,
muri alti 11,5 cm.

- **FIX 40** – Parametri aggiornati in `ViennaDataConf.py`:
  - `LarghezzaPorta` da 30 a **27** cm (serve per centrarsi sulla porta e fermarsi a metà apertura);
  - `TempoCentroPorta` da 1,1 a **0,9** s (il laser laterale è quasi al centro del robot: bastano circa 15 cm);
  - `TempoEntrataArena` da 1,0 a **1,2** s (circa 29 cm: dal muso alla striscia, più tutto il robot, più margine);
  - `DistanzaCameraArena` da 10 a **10,5** cm.
- Il robot ha 6 cm di margine per lato in una porta da 27 cm: la centratura (tolleranza 3 cm) basta.
- I laser stanno sopra le palline (alte 4,5 cm): non le vedono, quindi non le scambiano per muri.
- Simulatore aggiornato con le stesse misure: ingresso e uscita riusciti in tutti gli scenari.

## V9 – 9 ottobre 2026

**Problema visto a scuola:** il robot passava vicino o sopra la striscia nera dell'uscita senza riconoscerla.

- **FIX 39** – Mentre cerca l'uscita, a ogni passo il robot guarda il pavimento con la camera linea.
  Se vede la striscia nera, anche di sbieco, si mette perpendicolare ed esce. Se YOLO dice che la
  striscia è argento, non esce: è l'ingresso.
- Nuovo `ProvaStriscia.py`: con il robot fermo scrive `STRISCIA NERA` o `niente`. Serve a controllare
  che con la vostra luce e il vostro nastro la striscia venga vista.

## V8 – 8 ottobre 2026 (sera)

**Problema visto nel video:** nell'arena della scuola ingresso e uscita sono sullo stesso muro. Il robot
puntava sempre l'ingresso, tornava indietro e ci ritornava.

- **FIX 38** – Quando riconosce l'ingresso lo scarta e cerca l'uscita seguendo i muri con il laser
  laterale. Ogni apertura viene controllata con la camera linea: argento = ingresso, nero = uscita.
  Il giro dei muri parte anche dopo 45 s di ricerca inutile o dopo 2 blocchi.
- Simulatore: nuovo scenario `arena_parete`, uguale all'arena della scuola.

## V7 – 8 ottobre 2026

**Richiesta della squadra:** un terminale che faccia capire cosa sta facendo il robot.

- **FIX 37** – Nuovo `ViennaMonitor.py`:
  - **terminale**: in alto solo gli eventi importanti, in italiano e colorati; in basso un pannello
    fisso con stato del robot, laser, giroscopio, YOLO, motori, LED, temperatura e sottotensione del Pi;
  - **scatola nera**: ogni run viene registrata in `/home/pi/OneDrive/ScatolaNera/` (si può usare anche in gara);
  - **cruscotto 3D**: pagina web con il robot in 3D e i dati dal vivo, su `http://<ip-del-robot>:8000`.
    **Solo in laboratorio**: in gara `CRUSCOTTO = False` e WiFi spento (regolamento RCJ 3.2.4).
- Nuovo `avvia.sh` per lanciare il robot dalla cartella giusta.

## V6 – 8 ottobre 2026

**Problema visto nel video:** a un incrocio il robot girava per un falso verde invece di andare dritto.

- **FIX 36** – Quando YOLO dice Sx, Dx o doppio verde, il codice controlla con i colori dove sta il verde
  rispetto alla linea dell'incrocio: vale solo se è prima dell'incrocio. Si disattiva con
  `CONTROLLO_VERDE = False`.
- Nuovo `ProvaVerde.py`: ricontrolla le foto già salvate e mostra dove YOLO e i colori non sono d'accordo.

## V5 – 8 ottobre 2026

**Problemi visti sul robot:** il dietrofront non girava completamente, all'ingresso in arena il robot
prendeva la barriera, all'uscita sbatteva contro la parete.

- **FIX 8 (modificato)** – Tempo massimo di `Gira()` portato da 4 a 8 s: prima poteva interrompere il dietrofront.
- **FIX 33** – Ingresso in arena: il robot si ferma, riconferma la striscia argento ed entra dritto col giroscopio.
- **FIX 34** – Uscita: il robot si mette perpendicolare al muro della porta ed esce dritto (sostituisce il FIX 25).
- **FIX 35** – Prima di uscire si centra sulla porta guardando i due stipiti con la camera dell'arena.
- Camere misurate dalle foto di `ScattaCalibrazione.py`: camera linea a 8,3 cm, quasi a piombo
  (vede da sotto il muso a 7,7 cm davanti); camera arena a 9,8 cm, inclinata di 26°.

## V3–V4 – 7 ottobre 2026

- **FIX 25–26** – Ricerca dell'uscita: niente più giri alla cieca contro lo stipite; anti-blocco col giroscopio.
- **FIX 27–28** – Ostacolo: più margine dopo il primo lato e linea cercata a ogni passo.
- **FIX 29** – Incroci a T senza verde: il robot non sterza più nel ramo laterale.
- **FIX 30** – Presa delle palline: correzione finale proporzionale con il giroscopio (prima la pinza si chiudeva a vuoto).
- **FIX 31** – Foto del percorso salvate in `/home/pi/OneDrive/Incroci/` per riaddestrare YOLO, senza rallentare il robot.
- **FIX 32** – Festeggiamento all'arrivo: LED, braccio che si alza, pinza aperta e chiusa 3 volte.

## V2 – 6 ottobre 2026

Prima revisione completa del codice originale (FIX 1–24). Le più importanti:

- **FIX 1** – I 4 modelli YOLO si caricano una volta sola all'avvio (prima a ogni fotogramma: era la causa principale della lentezza).
- **FIX 3** – Velocità agli incroci in rampa corretta (prima scendeva a 0).
- **FIX 4** – PID del seguilinea corretto (derivata col segno sbagliato, Kp applicato due volte).
- **FIX 5** – Comandi della camera scritti con `=` invece di `:` (prima non facevano niente).
- **FIX 6** – Arresto sicuro: con qualsiasi errore o Ctrl+C i motori si fermano.
- **FIX 7** – Contatori azzerati a ogni nuova run.
- **FIX 11** – Errore del seguilinea corretto quando si vede solo la parte bassa della linea.
- **FIX 17** – Riconnessione all'Arduino senza crash dopo mezz'ora.
- **FIX 21** – Memoria degli angoli in arena che finalmente funziona.

## V1

Codice originale della squadra (`codici gommato vienna`).

---

## Strumenti nella cartella

| File | A cosa serve |
|---|---|
| `RwdFoto.py` | Il programma del robot: si lancia sempre questo |
| `ViennaDataConf.py` | Tutti i parametri da regolare, in un solo file |
| `ViennaPannello.py` | La finestra "ClaudeRob - STATO" (si apre da sola) |
| `ScattaCalibrazione.py` | Foto guidate delle due camere per tarare il simulatore |
| `ProvaVerde.py` | Ricontrolla le foto degli incroci con il controllo dei verdi |
| `ProvaStriscia.py` | Controlla che la camera linea veda la striscia nera dell'uscita |
| `TaraNero.py` | Taratura della soglia del nero (scala dei grigi) sul campo |
| `ProvaGPIO.py` | Elenca i chip GPIO e fa lampeggiare le luci, senza avviare il robot |
| `cruscotto/cruscotto.html` | Cruscotto 3D: dal robot in laboratorio, oppure aperto sul PC per rivedere una scatola nera |
| `LEGGIMI_MODIFICHE.md` | Il dettaglio di ogni FIX |

Il simulatore (`ClaudeRob_Simulatore_V22`) esegue questo stesso codice su un robot virtuale ed è utile
per provare una modifica prima di portarla sul campo.

---

## Da fare in laboratorio prima della gara

1. `TaraNero.py` sul campo di gara, con i LED accesi (vedi FIX 45).
1. Verificare i giri del FIX 44: dietrofront, ricerca palline, rotazioni dopo lo scarico.
1. `ProvaStriscia.py` sulla striscia nera dell'uscita, dritto e di sbieco. Se non la vede, abbassare `STRISCIA_AREA_MIN`.
2. Cronometrare quanti secondi impiega il robot a fare 1 metro dritto in arena e scriverlo (velocità in cm/s) in `VelocitaArenaCmS`.
3. Controllare `TempoEntrataArena` (ora 1,2 s): dopo la striscia argento tutto il robot deve essere dentro l'arena, senza arrivare al muro opposto.
4. Provare il giro dei muri: se il robot struscia, alzare `DistanzaMuro`; se tocca i triangoli, alzare `DistanzaAngolo`.
5. In gara: `CRUSCOTTO = False` e WiFi spento.
6. [V27] Inclinare il robot a mano verso destra e guardare il cruscotto o la finestra di stato: deve scrivere
   "INCLINATO verso destra". Se scrive "verso sinistra", cambiare `ROLLIO_POSITIVO_A_DESTRA` in ViennaDataConf.
7. [V27] Passare sulla piastrella con i verdi in diagonale dai quattro lati: il robot gira sempre dalla parte del verde
   valido. Poi `python3 ProvaVerde.py` sulle foto di `Incroci/`: le macchie grigie sono quelle ignorate (bordo del nastro).
8. [V27] Controllare cavo USB e alimentazione dell'Arduino: il 29/10 al secondo 107 ha smesso di rispondere.

## Ancora aperto

- **Ostacolo:** nel simulatore, con le misure vere del robot, a volte dopo l'ostacolo riprende la linea nel verso sbagliato.

- **Rilascio delle palline:** nel simulatore finiscono 3–7 cm fuori dai triangoli. Va verificato sul robot vero.
- **Conteggio delle palline:** il codice conta le prese, non le palline salvate.
- **Batteria:** non è misurata. Con un INA219 (indirizzo 0x44 o 0x45) basta scriverne l'indirizzo in `BATTERIA_INA219`.
- **Modello YOLO:** conviene riaddestrarlo con le foto nuove, compresi i falsi verdi etichettati come linea normale.
  [V27] Mettere nell'addestramento anche le foto della piastrella con i verdi in diagonale vista storta (a metà svolta)
  e quelle dell'inizio delle rampe, dove YOLO il 29/10 ha visto un falso "argento".
