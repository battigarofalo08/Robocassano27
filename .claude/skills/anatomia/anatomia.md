# Anatomia di RoboCassano

Scritta il 10/11/2026 sulla **ClaudeRob V41** (impronta `7fa6d06745b2776b`). I nomi delle funzioni e i valori dei parametri
vanno sempre ricontrollati nell'ultima cartella `ClaudeRob_V<n>`: il robot cambia a ogni versione.

Legenda: **[codice]** letto nel codice · **[STL]** letto nei file 3D · **[scatola nera]** misurato sul robot vero ·
**[simulatore]** valore del simulatore · **[da confermare]** dedotto (per esempio dal nome di un file), da verificare con la squadra.

---

## 0. La mappa: chi parla con chi

```
                       ┌──────────────────────── RASPBERRY PI 5 ("cervello") ────────────────────────┐
  camera LINEA ──CSI──▶│ ViennaClsWebCam.py  → Immagine (linea)  → YOLO Cross3                        │
  camera ARENA ──CSI──▶│                     → Arena  (arena)    → YOLO PalCol3 / TrianFull3 / Exit3 │
                       │                                                                              │
  ARDUINO NANO ──USB──▶│ ViennaClsRobot.py  (filo di lettura _arduino_reader, 230400 baud)            │
   3 laser VL53L1X     │      Distanze() GetGyro() GetSwitch() FrontaleFiltrato() Pendenza() ...      │
   giroscopio BNO055   │                                                                              │
   switch              │ RwdFoto.py  = il PROGRAMMA DI GARA: decide cosa fare                          │
                       │      seguilinea → ingresso → vittime → uscita → altalena → linea rossa       │
                       │ ViennaDataConf.py = TUTTI i parametri    ViennaMonitor.py = scatola nera      │
                       │                                                                              │
                       │ ViennaClsRobot.py → Sterzo(vel, sterzo) / Braccio() / Pinza()                │
                       └───────────────┬───────────────────────────────┬─────────────────────────────┘
                                   I2C │                               │ GPIO 22, 23
                      PCA9685 0x41 (ruote)   PCA9685 0x40 (braccio, pinza)      2 LUCI (relè)
                          4 servo a rotazione continua      2 servo di posizione
```

Un ciclo, in parole: l'Arduino manda ~30 volte al secondo le misure (laser, giroscopio, switch) su USB; un filo del programma
le tiene aggiornate; le camere scattano di continuo; `RwdFoto.py` guarda immagini e misure, decide, e chiama `Sterzo()` che
scrive gli impulsi sulla scheda PCA9685 delle ruote. La scatola nera registra tutto 10 volte al secondo.

---

## 1. Il corpo: i 5 pezzi stampati in 3D  [STL]

File in `Meccanica_STL/`, in **millimetri**, già nella **posizione di montaggio** (stesse coordinate per tutti: si possono
rimontare uno sull'altro). Asse verticale = **Y**; il muso (pinza e camere) è verso **X negativo**. Robot montato: circa
**202 mm** di lunghezza, **157 mm** di larghezza (le misure del codice dicono 15,6 cm), ~9 cm di altezza dei pezzi stampati.

| Pezzo | Ingombro (mm) | Dove sta | Cosa porta |
|---|---|---|---|
| `ServoRWDAmmortizzato.stl` | 202 x 8 x 151 | in basso, è la piastra più bassa (Y da -49 a -41) | i supporti dei servo delle ruote, con ammortizzazione ("RWD" = trazione) [da confermare] |
| `BaseLogica.stl` | 154 x 26 x 157 | al centro (Y da -22 a +4) | la "logica": Raspberry, Arduino, schede PCA9685 [da confermare] |
| `CoperturaAlta.stl` | 183 x 36 x 154 | in alto (Y da +5 a +41) | il coperchio che protegge l'elettronica [da confermare] |
| `SupportoPinzaWebcam_1.stl` | 61 x 67 x 157 | davanti (X da -36 a +25) | la pinza con il braccio e la camera della linea [da confermare] |
| `CupolaWebArenaLED.stl` | 8 x 52 x 148 | sul muso, sottile (X da -43 a -35) | la camera dell'arena e le luci LED [da confermare] |

Il modello del cruscotto (`ClaudeRob_V*/cruscotto/robot.stl`, 19092 triangoli, in cm) è questi 5 pezzi uniti.
**Esploso 3D**: `python3 .claude/skills/anatomia/costruisci_esploso.py` → `Meccanica_STL/esploso_robot.html`.

**Componenti in 3D semplificato** (`Meccanica_STL/componenti/`, fatti da `componenti.py` con le misure dei datasheet): i 4
servo FS5106R, il servo DM996, la LiPo, i 3 buck, l'Arduino Nano, le 2 PCA9685; nell'esploso sono montati
al loro livello (vedi "I tre livelli"); in più il Raspberry Pi 5 e la scheda a 2 relè. **Ancora senza modello 3D**: il servo della
pinza, le camere, laser, giroscopio e le strisce LED. Il braccio c'è: `Braccio.stl` (vedi la scheda 6), con le due ganasce della
pinza (`PinzaParteSxSfera.stl`, `PinzaParteDxSfera.stl`, 10/11) agganciate sotto; c'è anche il supporto degli interruttori
(`BiSwitch.stl`, sul fianco, in alto). Nell'esploso compaiono nell'elenco come "senza modello 3D".

Misure che il codice usa [codice/simulatore]: larghezza **15,6 cm** (`ROBOT_LARGHEZZA_CM`), camera linea **12 cm** davanti
alle ruote, laser davanti 11,5 cm davanti all'asse delle ruote, laser laterali 1,5 cm davanti e a ±7,5 cm di lato.

---

## 1. bis I tre livelli  [dal prof, 10/11 · STL]

| Livello | Pezzo stampato | Piano di appoggio | Cosa c'è sopra |
|---|---|---|---|
| **1** (in basso) | `ServoRWDAmmortizzato` | Y = −41 mm | **batteria LiPo** e i **3 buck DC-DC** (sotto: i 4 servo delle ruote) |
| **2** (in mezzo) | `BaseLogica` | Y = +4 mm | le **2 PCA9685** a 16 canali e l'**Arduino Nano** |
| **3** (in alto) | `CoperturaAlta` | Y = +41 mm | il **Raspberry Pi 5** e la **scheda a 2 relè** |

Tra un piano e l'altro ci sono circa 4 cm. Nell'esploso ogni componente è al suo livello e si smonta con lui; il punto preciso
dentro il livello è indicativo.

## 1a. Cosa si vede nelle foto del robot (10/11)  [foto, da confermare con la squadra]

Foto in `immagini/foto_robot/`: `sotto.jpg`, `fianco.jpg`, `fianco_elettronica.jpg`, `davanti_pinza.jpg`.

- **Sotto** (`sotto.jpg`): telaio verde oliva (`ServoRWDAmmortizzato`); **4 servo neri di formato standard**, uno per ruota,
  in culle bianche e fissati con fascette stampate verdi; al centro, tra i servo davanti e dietro, una **scatola bianca
  lunga** (probabile vano della batteria [da confermare]). Ruote stampate bianche (morbide, tassellate) con mozzi blu.
- **Di lato** (`fianco.jpg`, `fianco_elettronica.jpg`): **molle** delle sospensioni sopra le ruote; il **Raspberry Pi**
  (porte Ethernet/USB) sotto la copertura alta; un **convertitore buck** (scheda blu con bobina) nel piano basso; una scheda
  **a 2 relè** blu sul fianco (le 2 luci sono comandate dai relè: GPIO 22 e 23); un **tester della LiPo** con display (mostra
  "3", cioè 3 celle); una **maniglia** blu in alto; il servo del **braccio** (scritta "…M996…", tipo MG996R) sul davanti.
- **Davanti** (`davanti_pinza.jpg`): la **pinza** blu a due dita con **ingranaggi**, in cima al braccio; **due strisce LED
  COB a 5 V** inclinate ai lati; le **due camere** (il prof: quella che punta **verso il basso** è la camera **linea**,
  quella **inclinata** è la camera **arena**); un **piccolo sensore nero quadrato** sul muso (probabile laser davanti
  VL53L1X [da confermare]).
- Sul tavolo: la batteria LiPo con il caricatore bilanciato: la batteria si toglie per caricarla.

## 1b. L'energia: batteria e convertitori  [dal prof, 10/11]

- **Batteria LiPo Zeee 3S, 2200 mAh, 50C, 24,4 Wh** [dal prof]: 11,1 V nominali (12,6 V carica, da non scaricare sotto
  circa 9,9 V, cioè 3,3 V per cella); 11,1 V x 2,2 Ah = 24,4 Wh. Si toglie per caricarla con il caricatore bilanciato; sul
  robot c'è un tester con display che mostra le celle. Posizione: probabilmente il vano sotto il robot [da confermare].
  Durata, a spanne: con 20-25 W di consumo medio (Raspberry 5 con YOLO, 4 servo, luci) circa un'ora [stima, da misurare].
- **3 convertitori buck DC-DC** [dal prof]: abbassano gli 11,1 V della batteria per i vari circuiti. Quale tensione dà
  ciascuno e chi alimenta (Raspberry 5 V fino a 5 A, servo delle ruote, braccio e pinza, luci 5 V): [da confermare].
- **Nel codice**: `ViennaMonitor.py` legge dal Raspberry la **sottotensione** (`vcgencmd get_throttled`) e la tensione
  `EXT5V_V` (`vcgencmd pmic_read_adc`): nella scatola nera finiscono nel campo `pi`. Se il buck del Raspberry non ce la fa
  (batteria scarica, picchi dei servo), lì si vede. Shuri mette questi casi in "Hardware da controllare".
- **Simulatore**: la batteria non esiste (sempre carica, nessuna sottotensione).
- **Sicurezza**: la LiPo si carica solo con il caricatore bilanciato, sorvegliata, e non si usa se è gonfia o rovinata.

## 2. Il cervello: Raspberry Pi 5  [codice]

- **Programma di gara**: `RwdFoto.py` (~4500 righe), dalla cartella della versione (oggi `~/ClaudeRob_V41`).
- **Avvio**: all'accensione `~/.config/labwc/autostart` (e `lxsession`) lancia `~/ClaudeRob_GARA/avvia.sh`; `ClaudeRob_GARA`
  è un collegamento alla versione di gara (`ln -sfn ~/ClaudeRob_V41 ~/ClaudeRob_GARA`).
- **File**: `ViennaClsRobot.py` (corpo: motori, sensori, movimenti), `ViennaClsWebCam.py` (occhi), `ViennaDataConf.py`
  (tutti i parametri: ~200), `ViennaMonitor.py` (scatola nera, terminale, cruscotto), `ViennaPannello.py` (pannello a schermo),
  `ViennaCabina.py` (dalla V42: il terminale "cabina di pilotaggio").
- **Ciclo principale** (fondo di `RwdFoto.py`): in PAUSA finché lo switch è spento; acceso → `Protetto(InseguitoreIA)` →
  `Protetto(ArenaAI)` → `Protetto(TrovaUscitaArena)`. `Protetto` (FIX 100): un errore Python non chiude la gara, passa alla
  fase dopo. `finally` (FIX 6): qualunque cosa succeda, ferma i motori.
- **Impronta** (FIX 86): codice sha256 dei file `.py` della cartella; nella scatola nera dice se gira la versione giusta.
- **Nel simulatore**: lo stesso `RwdFoto.py` gira davvero; `finto_hw.py` sostituisce le librerie del Raspberry e il tempo
  diventa virtuale (avanza solo con `time.sleep`).

---

## 3. Gli occhi: due camere e quattro reti YOLO  [codice]

| | Camera LINEA | Camera ARENA |
|---|---|---|
| Nel codice | `CamSL = Picamera2(0)` | `CamAr = Picamera2(1)` |
| Risoluzione | 440 x 260 | 440 x 260 |
| Guarda | il pavimento davanti al muso (12 cm davanti alle ruote) | davanti, più in alto: pareti, porte, palline, triangoli |
| Reti YOLO (NCNN) | `best_ncnn_model_Cross3`: linea e incroci | `PalCol3` palline · `TrianFull3` triangoli e porta · `Exit3` uscita (0) / ingresso (1) |

- **Classi della camera linea**: `Ln` linea, `In` argento (ingresso), `Bi` bianco, `No` niente, `Di` discontinuità
  (interruzione), `Ro` rosso (arrivo), verdi `Sx`/`Dx`… I modelli YOLO **non sono su GitHub**: stanno sul robot e si copiano
  in ogni cartella di versione.
- **Funzioni** (`ViennaClsWebCam.py`): `LeggiCross`, `VerificaVerde` / `VerdiGeometria` (i verdi), `PallinaNuova`,
  `CercaPortaTri`, `TipoPorta`, `VerificaUscita`, `StrisciaNera` / `GeometriaStrisciaNera`, `LineaAlCentro`,
  `CalcolaErrore`, `CercaBlocchiCol` (colori), `AutoregolaCam`, `SalvaFoto`.
- **Scatola nera**: campi `yolo` (classe e sicurezza), `verde`, e ogni ~0,5 s le miniature `img_l` (linea) e `img_a` (arena).
- **Simulatore**: YOLO è un "oracolo" che risponde quello che c'è davvero davanti: non sbaglia mai come la rete vera (luce,
  riflessi, plastica lucida scambiata per argento: scatola nera 09/11 13:00, secondo 381).
- **Punti deboli**: luce e riflessi; i verdi in diagonale (29/10); la plastica trasparente vicino alle porte vista come
  argento (09/11).
- **Regolazione della camera linea (V48)**: fuoco fisso a 8,3 cm (`CAM_LINEA_FUOCO_CM`), 20 FPS (`CAM_LINEA_FPS`); all'avvio del
  programma LED accesi, esposizione bloccata e soglia del nero con Otsu (FIX 112, V46). Interruttore `CAM_LINEA_AUTOTARATURA`
  (False = come la V47). **Lux** di tutte e due le camere ogni secondo, controllo **VISTA OK/ATTENZIONE** all'avvio, esposizione
  della camera arena bloccata dopo l'assestamento (FIX 113, V47). Gli eventi dell'avvio sono nell'intestazione della scatola
  nera (`avvio`) e come "AVVIO: ..." al secondo 0 (FIX 114). Campi nuovi della scatola nera: `lux`, `cam_meta`, `vista`.

---

## 4. I sensi: Arduino Nano, 3 laser, giroscopio, switch  [codice]

- **Arduino Nano** (`InoSensor.ino`, non su GitHub; posizione sul robot [da confermare]) su USB (`/dev/ttyUSB*`), **230400 baud**. Una riga di **10 numeri** separati
  da virgole: `d1,d2,d3,hd,rl,pt,sw1,sw2,t0,t1`.
  - `d1,d2,d3` = laser **sinistro, davanti, destro** in cm; `hd,rl,pt` = rotta, rollio, beccheggio; `sw1,sw2` = switch;
    `t0,t1` = inclinazione.
  - Letta dal filo `_arduino_reader` in `ViennaClsRobot.py`. Righe senza 10 campi: scartate.
  - **Con lo switch spento l'Arduino smette di mandare dati**: non è un guasto (verificato su 4 scatole nere il 5/11).
    Dopo 0,3 s senza dati il programma mette tutto a 0 e scrive "Arduino zitto: switch spento?".
- **3 laser VL53L1X**: `Distanze()`, `LaserVeri()` in `RwdFoto.py` (0 = fuori portata → `LASER_LONTANO` 150 cm),
  `FrontaleFiltrato()` (FIX 87: mediana nel tempo, ignora le letture isolate).
  - Il laser vero ha un **cono largo** (~45 cm a 1 m, più di una porta) e a ~1 m balla di **±2 cm** [scatola nera 09/11];
    il simulatore usa un raggio sottile con rumore 0,7 cm (FIX 106 nasce da qui).
- **Giroscopio BNO055**: `GetGyro()` → (beccheggio, rollio, rotta). Le rotte crescono girando a **destra**. Risponde ~0,1 s in
  ritardo. Se è bloccato, `BussolaStato()` e la **bussola stimata dai motori** (FIX 88) prendono il suo posto;
  `StoriaBeccheggio()` e `Pendenza()` servono per rampe e altalena.
- **Switch**: `GetSwitch()` → `{'sw_pal', 'sw_sof'}`. `sw_sof` = avvio/pausa della gara (il capitano lo spegne per la LoP);
  `sw_pal` = switch della pallina nella pinza [da confermare].
- **Scatola nera**: `d` (laser), `dfr` (laser davanti filtrato), `imu`, `bus` (giroscopio o stimata), `rotta`, `pend`, `tilt`,
  `sw`, `ard` (Arduino vivo?).

---

## 5. Le gambe: 4 servo a rotazione continua  [codice]

- **Un servo per ogni ruota**, 4 in tutto: **Feetech FS5106R** a rotazione continua [dal prof]. Dal datasheet (valori
  indicativi): circa 41 x 20 x 38 mm, 4,8-6 V, coppia circa 5-6 kg·cm, circa 100 giri al minuto senza carico. Non si dice
  "vai a 30°" ma "gira a questa velocità": per questo il codice ragiona in velocità (`Sterzo`) e non in angoli.

- Scheda **PCA9685 all'indirizzo I2C 0x41**: canali **15** (avanti sinistra), **4** (dietro sinistra), **0** (avanti destra),
  **11** (dietro destra). Impulsi da 310 a 333 (fermo a 321).
- **`Sterzo(velocita, sterzo)`**: l'unico comando delle ruote. `sterzo` 0 = dritto, ±100 = ruota sul posto, in mezzo = curva.
  Correzioni fisse dei lati (1,17 / 0,83) perché i servo non sono uguali.
- **Sopra** Sterzo: `Stop()`, `Dritto(vel, durata, heading_ref, ruota)` (va dritto tenendo la rotta col PID, FIX 13/64/72),
  `Gira(gradi)`, `RuotaVerso(rotta)` (anello chiuso: anticipa, assesta, colpi brevi, FIX 64/72; capisce se la rotazione è
  bloccata, FIX 65), `GiraA()` in `RwdFoto.py`.
- **Velocità**: `VelCrs` 47 (seguilinea), `VelArena` 68 (arena); ~10 cm/s a `VelArena*0,7` (`VelocitaArenaCmS`).
- **Fisica da ricordare**: sotto circa **40 di sterzo** (a velocità 47) i servo non girano (FIX 64); fermati, il robot gira
  ancora di 5-7 gradi (FIX 72); con lo switch spento `Dritto` ferma i motori e aspetta 0,1 s (FIX 105).
- **Scatola nera**: `mot` = ultimo comando (es. `['Sterzo', 68, 3]`), `manovra`, `azione`.
- **Simulatore**: servo "reali" con ritardo `tau_servo_reale` 0,10 s.

---

## 6. Le mani: braccio e pinza  [codice]

- Scheda **PCA9685 all'indirizzo 0x40** (la seconda scheda a 16 canali; la prima, 0x41, comanda solo le ruote):
  **canale 4 = braccio**, **canale 11 = pinza** (servo di posizione, in gradi).
- **Braccio**: servo **DM996 "all metal"** [dal prof] (ingranaggi in metallo, formato standard come l'MG996R: circa
  40 x 20 x 43 mm). Il braccio stampato è `Meccanica_STL/Braccio.stl` [STL]: un disco che si avvita alla squadretta del
  servo (il **perno**, asse = larghezza del robot), un braccio a L e una base piatta (circa 6 cm) dove si monta la pinza.
  Lo STL è disegnato **abbassato** (base vicino al pavimento, davanti al muso); alzato, il braccio ruota di circa 140°
  attorno al perno e porta la pinza sopra il muso (foto). Nell'esploso: cursore "Braccio" (posizione indicativa). **Pinza**: due dita blu mosse da ingranaggi; modello del servo [da confermare].
  Le due ganasce sono `PinzaParteSxSfera.stl` e `PinzaParteDxSfera.stl` [STL, 10/11]: coppe a mezza sfera (pallina di circa
  5 cm) con gli ingranaggi dietro, disegnate chiuse su una pallina appoggiata a terra; nell'esploso sono agganciate sotto la base
  piatta del braccio e si muovono con il cursore "Braccio" (posizione indicativa).
- `Braccio(angolo)`, `Pinza(angolo)`; in `RwdFoto.py`: `AbbassaPinza`, `AlzaPinza`, `ApriPinza`, `ChiudiPinza`,
  `CaricaPalla`, `SvuotaPinza`, `ScaricaPalla(tipo)`, `AccostaTriangolo`.
- **Scatola nera**: `br` (braccio), `pz` (pinza), `pal` (palline).
- **Come decide la presa** (`ArenaAI`): si avvicina finché il riquadro YOLO della pallina arriva a **5500 pixel**, corregge
  l'angolo, poi una manovra a tempo (indietro 0,5 s, pinza giù, avanti 1,1 s, chiude, indietro, carica). "Presa" o "mancata" lo
  dice l'interruttore della pinza (`sensori['switch']`). **Punto debole** (scatola nera V46, 12/11 17:52): due palline attaccate
  sembrano una pallina grande, i 5500 pixel arrivano troppo lontano e la pinza si chiude a vuoto (6 volte di fila).

---

## 7. Le luci  [codice]

Due luci su **GPIO 22 e 23** (`PIN_LUCI`), comandate con `lgpio` sul chip `pinctrl-rp1` del Raspberry 5 (FIX 50; se manca,
luci finte: il robot non si blocca mai per le luci). `GetOnLed1/2`, `GetOffLed1/2`. Si accendono per illuminare il pavimento e
l'arena. **Scatola nera**: `led`.

---

## 8. La memoria: scatola nera e cruscotto  [codice]

- **Scatola nera** (`ViennaMonitor.py`, FIX 37): `~/OneDrive/ScatolaNera/run_AAAA-MM-GG_hh-mm-ss_V<n>.jsonl`. Prima riga =
  intestazione (versione, impronta, cartella, file); poi un campione ~ogni 0,1 s (`tipo: "c"`) e gli eventi (`tipo: "evento"`).
  Non comunica con niente: si può usare in gara.
  Dalla V43 (FIX 108) un file per **run**: le LoP sono dentro (eventi "STOP n" con fase, laser e rotta dell'ultimo istante con lo
  switch acceso, e "LoP n: si riparte dopo x s"; campo `lop`); file nuovo solo dopo `CRONO_NUOVA_GARA_S` (120 s) di switch spento.
- **Cruscotto** (solo laboratorio, `CRUSCOTTO`): pagina web 3D su `http://<ip-del-robot>:8000` con il modello del robot.
- **Terminale "cabina di pilotaggio"** (V42, FIX 107, `ViennaCabina.py`, `TERMINALE = "cabina"`): schermata fissa a riquadri
  ridisegnata 5 volte al secondo: laser visti dall'alto, assetto con 20 s di storia, **cronometro** che parte con lo switch e
  non si azzera con le LoP (le conta; gara nuova solo dopo `CRONO_NUOVA_GARA_S` 120 s di switch spento; `CRONO_DURATA_S` 480),
  camera linea e camera arena in piccolo (mezzi blocchi a 256 colori; dalla V43 più grandi con la finestra grande), motori e pinza, fasi della gara, eventi. Serve una
  finestra di almeno 100 x 38 caratteri; più piccola → torna il pannello di prima (`"pannello"`, FIX 37/42). Riceve lo stesso
  campione della scatola nera, quindi la **moviola** `Strumenti_prove_Claude/terminale_nuovo.py` rivede una gara vera uguale.
- **Strumenti**: `Strumenti_prove_Claude/analizza_scatola_nera.py` (eventi, o campioni tra due istanti);
  `Laboratorio Shuri/analizza_scatola.py` (problemi + foto delle camere).

---

## 9. I comportamenti (gli "organi" del programma)  [codice]

Ogni comportamento: **sensori → funzioni → decisione → motori**. Le funzioni sono in `RwdFoto.py` se non è scritto altro.

| Comportamento | Sensori | Funzioni principali | Parametri chiave | FIX importanti |
|---|---|---|---|---|
| **Seguilinea** | camera linea, YOLO Cross3 | `InseguitoreIA`, `CalcolaErrore` (WebCam), `VedoLinea`, `RecuperaLinea` | `VelCrs` 47, `SOGLIA_NERO` 110 | 11 |
| **Verdi e incroci** | camera linea, YOLO, colori | `LeggiCross`/`VerificaVerde` (WebCam), `AnalizzaIncrocio`, `CrosDx`/`CrosSx`/`CrosFF`, `AvanzaSullIncrocio`, `CompletaSvolta`, `ConfermaDietrofront`, `AvviaPausaVerdi` | svolte "vecchie"/"nuove", `VERDE_PAUSA_S` | 41, 80, 91 (rotonda), 92 |
| **Interruzione** | camera linea (`Di`) | `SeguiFinoAlVuoto`, `AttraversaVuoto`, `AttraversaInterruzione` | | 85 |
| **Ostacolo** | laser davanti filtrato, laterali | `OstAutDet`, `ConfermaOstacolo`, `AggiraOstacolo`, `ScegliLatoOstacolo`, `StaccaDallaParete`, `AvantiOst`, `Spinge` | `OST_SPINTA_CM` 5 | 13, 87, 90 |
| **Rampe e tratti inclinati** | giroscopio | `Pendenza` (Robot), `InPianoPerArena` | | 82, 89 |
| **Altalena** | giroscopio (salto del beccheggio) | `ControllaAltalena`, `AltalenaNellaStoria`, `AspettaGiroscopioFermo` | `ALTALENA_SALTO_GRADI` 30 | 102, 104 |
| **Ingresso nell'arena** | camera linea (argento), laser davanti | `TrovaIngressoArena`, `IngressoDopoArgento`, `DirezioneIngresso`, `CentraSullIngresso`, `EntraDallaPorta` → `CercaAperturaDavanti`/`CercaApertura`, `PassaLaPorta`, `AttraversaPorta`, `SpostaDiLato` | `TempoEntrataArena` 2,5, `INGRESSO_LIBERO_CM` 40, `ENTRATA_OLTRE_CM` 9, `ENTRATA_LONTANO_*` | 68, 93, 96, 101, 104, 106 |
| **Vittime (palline)** | camera arena (PalCol3, TrianFull3), switch pinza | `ArenaAI`, `ScaricaPalla`, `AccostaTriangolo`, `GiraInArena`, `MemorizzaPosizione`/`GiraVersoMemoria` | | 21, 83 |
| **Uscita dall'arena** | laser laterali e davanti, camera linea (striscia nera), camera arena (Exit3) | `TrovaUscitaArena` → `ScegliLatoGiro`, `AvvicinatiAlMuro`, `GiroDeiMuri`/`SeguiParete`, `ControllaAperturaMuro`, `EsciDallaPortaDavanti`, `EsciControllando`, `EsciDallaPorta`, `StrisciaFerma`; se fallisce `TrovaUscitaIA` (camera) | `USCITA_MODO` "muri", `LATO_MURO_CM` 6,5, `APERTURA_CM` 15, `ANGOLO_CM` 8, `USCITA_LIBERO_CM` 30, `TEMPO_MAX_MURI` 150 | 53, 55, 63, 69, 70, 84, 94, 103, 104, 105 |
| **Linea rossa e arrivo** | camera linea (`Ro`) | `InseguitoreIA`, `Festeggia` | | 95 |
| **Switch spento / LoP** | switch | ciclo principale, `SwitchSpento` | | 6, 7, 105 |

**Punti deboli noti** (vedi "Aperto / da fare" in `CLAUDE.md`): l'uscita (09/11 13:00: girato verso il pannello accanto alla
porta, plastica lucida vista come argento, 70 s persi); alcuni verdi (09/11, da analizzare); la parete di destra presa per
ostacolo in `scuola_basso`/`scuola_rampa` (simulatore).

---

## 10. Come si "smonta" davvero un sistema (esercizi)

- **Sul robot**: `LetturaNano.py` (legge l'Arduino: laser, giroscopio, switch), `ProvaGPIO.py` (luci), `ProvaVerde.py`,
  `ProvaStriscia.py`, `TaraNero.py`, `ScattaCalibrazione.py`: strumenti da laboratorio della cartella della versione.
- **Nel simulatore**: `Strumenti_prove_Claude/gira.py` (gara intera), `prova_ingresso.py`, `prova_uscita.py`,
  `prova_uscita_angolo.py`, `prova_altalena.py`; guasti nel `cfg` (`imu_bloccato`, `tof_fr_spurie`, `tof_rumore`,
  `arduino_muto_da`…).
- **Nella scatola nera**: scegli un evento, guarda i campioni secondo per secondo, e prova a dire quale sensore ha fatto
  prendere quella decisione.
