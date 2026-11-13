# Come lavorare su RoboCassano (per Battista, Gioele e chi entra nella squadra)

Questa repository contiene il software del robot **RoboCassano** (RoboCup Junior Rescue Line). Ci lavorano il prof
(Giovanni Vaccaro), gli studenti **Battista** e **Gioele**, e Claude (un'intelligenza artificiale che propone correzioni e
le prova nel simulatore).
**Nessuna modifica entra nella versione ufficiale senza che il prof la approvi.**

Prima di cominciare leggi anche `CLAUDE.md`: ci sono le regole fisse, la storia delle versioni e cosa resta da fare.

---

## 0. Prima il robot, poi il codice

La cosa più preziosa in questo progetto **non è saper scrivere Python**: è **capire il robot**. Perché un servo a
rotazione continua non gira sotto una certa soglia, cosa vede un laser contro uno stipite, cosa succede quando lo switch
si spegne in gara. Le correzioni migliori sono sempre nate dalla scatola nera e dalla fisica, non dal codice. Il Python
viene dopo, e lì vi aiuta Claude.

Per questo **ogni pull request deve saper rispondere a tre domande**, a voce, senza leggere il codice:

1. **Che problema risolve?** Quale scatola nera, quale secondo, cosa faceva il robot.
2. **Cosa farà di diverso il robot adesso?** Spiegato a parole, come lo spieghereste a un compagno.
3. **Come sappiamo che funziona e che non rompe il resto?** Le prove nel simulatore, prima e dopo.

Se non sapete rispondere, la pull request non è pronta, anche se il codice "funziona". Alla RoboCup i giudici fanno
proprio queste domande.

Il Python si impara **un pezzo alla volta, sul nostro robot**: si comincia da `ViennaDataConf.py` (solo parametri:
velocità, distanze, soglie; cambiare un numero si vede subito sul robot), poi una funzione alla volta tra quelle che
conoscete già dal comportamento del robot. Quando non capite qualcosa chiedete a Claude: *"spiegami questa funzione in
italiano semplice"*, *"cosa fa questa riga?"*. E spiegatevelo a vicenda: insegnare è il modo più veloce per imparare.

---

## 1. Le parole da sapere

| Parola | Cosa vuol dire |
|---|---|
| **repository** | la cartella del progetto su GitHub, con tutta la sua storia |
| **`main`** | il ramo **ufficiale**: quello che va sul robot. È protetto, non si modifica direttamente |
| **ramo** (*branch*) | la tua copia di lavoro: ci fai tutte le prove che vuoi senza toccare `main` |
| **commit** | un salvataggio con una frase che dice cosa hai cambiato |
| **push** | mandi i tuoi commit su GitHub |
| **pull request** (PR) | la proposta "porta le mie modifiche in `main`": il prof la legge e decide |
| **issue** | un problema o un compito scritto su GitHub (scheda *Issues*), con chi se ne occupa |

## 2. Preparare il computer (una volta sola)

1. Crea un account su **github.com** e manda il nome utente al prof. Ti arriva un invito per email: **accettalo**.
2. Installa **GitHub Desktop** (desktop.github.com) e fai l'accesso con il tuo account.
3. In GitHub Desktop: **File → Clone repository** → `Giooooonni93/Robocassano27` → scegli dove metterla.
4. Per il simulatore serve Python 3 con due librerie. Nel Terminale (Mac) o nel Prompt dei comandi (Windows):
   ```
   pip3 install numpy opencv-python
   ```
5. Un editor per il codice: va bene **Visual Studio Code** (code.visualstudio.com) oppure Notepad++.

## 3. Le regole del progetto (sempre)

1. **Ogni modifica al codice del robot è una versione nuova**, in una cartella nuova: si copia l'ultima
   (`ClaudeRob_V40`) in `ClaudeRob_V41` e si lavora **solo** sulla copia.
2. **Non si modifica mai** una cartella già consegnata (V39, V40, …): serve per i confronti.
3. **Le versioni si prenotano con le issue.** Prima di cominciare guarda la scheda **Issues** e le **Pull requests**
   aperte, poi apri una issue tipo "V41 – Battista – altalena" e assegnala a te. **Chi apre per primo l'issue prende quel
   numero** (e i FIX successivi): se la V41 è già presa, tu prendi la V42. Così nessuno fa due versioni con lo stesso numero.
4. **Ognuno il suo pezzo di robot.** Per esempio Battista l'altalena e il seguilinea, Gioele l'arena (ingresso, palline,
   uscita). Se due persone cambiano la stessa funzione nello stesso momento nascono conflitti difficili da sistemare:
   se ti serve toccare il pezzo di un altro, parlatene prima (anche con un commento nella sua issue).
5. I **nomi dei file** non cambiano mai (`RwdFoto.py`, `ViennaClsRobot.py`, `ViennaDataConf.py`, …).
6. Ogni modifica nel codice ha un commento **`# [FIX n]`** con il motivo (quale scatola nera, quale secondo, cosa si
   vede). Prendi il numero dopo l'ultimo (l'ultimo è scritto in `CLAUDE.md`).
7. In `ViennaDataConf.py` aggiorna `VERSIONE = "ClaudeRob V41"`. I parametri nuovi si mettono **solo** lì e si leggono
   con `getattr(RwdConf, "NOME", valore_di_riserva)`.
8. Aggiorna `CHANGELOG.md` (sezione nuova in cima + una riga nella tabella "In breve") e `LEGGIMI_MODIFICHE.md`
   (una riga per FIX). Questi due file hanno la **fine riga CRLF** (Windows): in Visual Studio Code lo vedi in basso a
   destra; se c'è scritto `LF`, cliccaci e scegli `CRLF`.
9. **Prima della pull request, prova nel simulatore** e confronta con la versione precedente (vedi sotto).
10. **Si parte sempre dall'ULTIMA versione unita in `main`**, mai da una vecchia. Se due versioni partono dalla stessa
    (come V46 e V47 dalla V45), la seconda non contiene la prima: il controllo automatico lo vede e la pull request
    resta rossa (sezione 3bis).

## 3bis. Lavorare come nelle aziende della Silicon Valley

Dal 12/11 lavoriamo con i metodi delle grandi aziende di software. Sono le stesse cose che troverete al lavoro.

| Metodo (nome inglese) | Cosa vuol dire da noi |
|---|---|
| **Un solo tronco** (*trunk-based development*) | `main` è la verità. Ogni versione nuova parte dall'ultima unita. Pull request piccole e frequenti, un pezzo di robot alla volta |
| **Controllo automatico** (*CI, continuous integration*) | A ogni pull request GitHub, da solo, controlla le regole e fa girare la versione nel simulatore contro quella prima (file `.github/workflows/controllo.yml`). In fondo alla pull request: ✅ verde = si può unire, ❌ rosso = c'è da sistemare. La tabella delle gare è nella pagina **Details → Summary**. Si può lanciare anche a mano: `python3 Strumenti_prove_Claude/controlla_versione.py` e `python3 Strumenti_prove_Claude/confronta_simulatore.py` |
| **Revisione del codice** (*code review*) | Nessuno unisce da solo il proprio lavoro: la pull request la legge e la unisce il prof (`CODEOWNERS`). Chi scrive spiega, chi rivede chiede. Ognuno lavora **con il suo account** GitHub |
| **Interruttori** (*feature flags*) | Una funzione nuova entra con un interruttore in `ViennaDataConf.py` (es. `CAM_LINEA_AUTOTARATURA = True/False`). Se sul robot va male si spegne in 5 secondi, senza fare una versione nuova |
| **Rilascio** (*release*) | La versione che va sul robot è sempre una versione unita e verde, mai una cartella "di prova" |
| **Analisi senza colpe** (*blameless postmortem*) | Dopo un errore (in gara o nel lavoro) si scrive cosa è successo e quale regola lo impedirà la prossima volta, non chi ha sbagliato. Le scatole nere servono a questo |
| **Lavagna** (*Kanban*, GitHub Projects) | Ogni issue è una scheda: Da fare → In corso → In revisione → Fatto. Tutti vedono chi fa cosa |
| **Riunione in piedi** (*stand-up*) | A inizio laboratorio, 10 minuti: ognuno dice cosa ha fatto, cosa farà, cosa lo blocca |

## 4. Il lavoro, passo per passo

### Il giro completo della squadra

1. **Prova sul robot** con l'ultima versione (cartella pulita, sezione 9), sulla pista della scuola: arena **e** altalena,
   più volte. Annotate a parte cosa vedete ("dopo l'altalena ha perso la linea", "incastrato nella porta d'uscita"…).
2. **Scatola nera sul Mac** con `Laboratorio Shuri/Scarica scatole nere.command`.
   Scrivete anche le **note di laboratorio**: un file di testo con lo stesso nome della scatola nera
   (`run_..._V40.txt`) con dov'era il robot e cosa avete visto. Shuri le legge e le mette nell'analisi.
3. **Scatola nera su GitHub, una volta sola**, in `ScatoleNere/` (con un ramo e una pull request, oppure la carica il
   prof con Claude). Da lì la leggono tutti: il vostro Claude, quello del prof, Shuri. Non serve darla a ogni Claude.
4. **Una issue per ognuno**, ognuno sul suo pezzo, per esempio "V41 – Battista – altalena" e "V42 – Gioele – uscita".
5. **Ognuno lavora sulla sua versione** (passi qui sotto, o con Claude Code: sezione 7), partendo dall'ultima unita in
   `main`. Prima richiesta a Claude: *"analizza la scatola nera `run_…` nella parte dell'altalena (o dell'uscita), trova
   cosa è andato storto, riproducilo nel simulatore e proponi una correzione"*.
6. **Pull request** con la tabella prima/dopo e le risposte alle tre domande (sezione 0). Il prof controlla, chiede, unisce.
7. **Chi arriva secondo si aggiorna** (passo 8 qui sotto).
8. **La versione nuova (che contiene tutte le correzioni) va sul robot**, nuova scatola nera, e si ricomincia.

### Passo per passo (con GitHub Desktop)

1. In GitHub Desktop: **Fetch origin** (scarichi le novità), poi controlla di essere su `main`.
2. **Branch → New branch**, con un nome chiaro: `battista/altalena`, `gioele/uscita`, …
3. Copia la cartella dell'ultima versione (es. `ClaudeRob_V40` → `ClaudeRob_V41`) e lavora lì.
4. Prova nel simulatore (sezione 5).
5. In GitHub Desktop scrivi una frase nel riquadro in basso a sinistra (es. "V41: FIX 106 altalena, ritrova la
   linea") e premi **Commit**.
6. **Push origin**, poi **Create Pull Request**. Nella pull request scrivi:
   - **da dove viene** il problema (scatola nera, secondo, cosa si vede);
   - **cosa hai cambiato**;
   - **le prove**: una tabella "prima / dopo" con i risultati del simulatore.
7. Il prof legge, commenta, e se va bene fa **Merge**. Se chiede modifiche: correggi sullo stesso ramo, Commit,
   Push. La pull request si aggiorna da sola.
8. **Chi arriva secondo si aggiorna.** Se nel frattempo è stata unita la versione di un altro (es. la V41 di Battista),
   la tua V42 è partita dalla V40 e **non contiene** la sua correzione. Prima del Merge:
   - premi **Update branch** nella pull request (o in GitHub Desktop: **Branch → Update from main**);
   - rifai la tua cartella partendo dalla versione appena unita: copia `ClaudeRob_V41` in `ClaudeRob_V42` e rimetti
     dentro le tue modifiche (con Claude: *"la V41 è stata unita: rifai la V42 partendo dalla V41 con le mie modifiche
     e riprova nel simulatore"*);
   - in `CHANGELOG.md` la tua sezione va **sopra** quella della V41; in `CLAUDE.md` aggiorna "ultima" e "ultimo FIX";
   - riprova nel simulatore, aggiorna la tabella prima/dopo (confronto con la V41) e scrivilo nella pull request.
   Così ogni versione nuova contiene tutte quelle prima.
9. Dopo il Merge: in GitHub Desktop torna su `main` e fai **Fetch origin** / **Pull origin**. Chiudi l'issue.

## 5. Provare nel simulatore

Dalla cartella `Strumenti_prove_Claude`:

```
python3 gira.py ../ClaudeRob_V45 prova scuola 480 seme=1
```

Risultato atteso (V39 e V40): **arrivo** in 255-259 s con i semi da 1 a 6. Prova anche le altre piste
(`rcj2026`, `lunga`, `contorto`, `arena_parete`, `gara`) e confronta con la versione precedente:

```
python3 gira.py ../ClaudeRob_V44 prima rcj2026 480 seme=1
python3 gira.py ../ClaudeRob_V45 dopo  rcj2026 480 seme=1
```

I risultati di riferimento sono in `CLAUDE.md` (sezione "Il simulatore"). Altre prove (porte, altalena) sono descritte
in `Strumenti_prove_Claude/LEGGIMI.md`. Per vedere la gara nel browser:

```
cd ../ClaudeRob_Simulatore_V32
python3 crea_replay.py confronto.html replay_prima.json:"V44" replay_dopo.json:"V45"
```

La batteria completa di Shuri (circa 16 gare): da `Laboratorio Shuri`, `python3 batteria.py ../ClaudeRob_V45`.

## 6. Le scatole nere

Dopo ogni prova sul robot vero, la scatola nera (`run_AAAA-MM-GG_hh-mm-ss_V<n>.jsonl`) va in `ScatoleNere/`.
Per guardarla velocemente:

```
python3 -I Strumenti_prove_Claude/analizza_scatola_nera.py ScatoleNere/<nome del file>.jsonl
```

Il metodo che funziona: trovare il momento in cui succede il problema, guardare i dati secondo per secondo (laser,
rotta, motori, YOLO), capire la causa fisica, riprodurla nel simulatore, correggere, dimostrare la correzione con una
prova prima/dopo.

## 7. Lavorare con Claude Code

> Usi ChatGPT o Claude sul sito? Incolla `ISTRUZIONI_PER_LA_IA.md` nelle istruzioni del tuo progetto: così la tua IA
> conosce il robot e le regole della squadra.

1. Ognuno ha il **suo account Claude** (piano Pro, che comprende Claude Code): mai l'account di un altro.
2. Su claude.ai **collega il tuo account GitHub** (lo stesso con cui sei collaboratore).
3. Apri **Claude Code**, scegli la repository `Giooooonni93/Robocassano27`. Claude legge da solo `CLAUDE.md` e conosce
   le regole. Il ramo lo crea Claude; se vuoi un nome chiaro, chiediglielo: *"lavora sul ramo `battista/altalena`"*.
4. Prima richiesta di ogni lavoro: *"guarda le issue e le pull request aperte e dimmi che versione posso usare"*.
5. Un compito = una sessione nuova = un ramo = una pull request.
6. Prima di aprire la pull request, chiedi a Claude di spiegarti la modifica finché sai rispondere da solo alle tre
   domande della sezione 0. **La pull request la firmi tu**: il prof la approva solo se sai spiegarla.

### La skill "anatomia": smontare il robot

Nella repository c'è una **skill** (`.claude/skills/anatomia/`) che il vostro Claude usa da solo quando gli chiedete di
spiegare un pezzo del robot. Provate per esempio:
- *"smontami il sistema dei laser"*, *"come parla l'Arduino con il Raspberry?"*, *"dove sono i motori nel codice?"*;
- *"smontami il comportamento dell'uscita dall'arena: dai sensori ai motori"*;
- *"quali FIX hanno cambiato l'ingresso, e perché?"*.

Per ogni sistema vi dice: cos'è, dove sta sul robot, come parla con il resto, dove è nel codice, i parametri, come si vede
nella scatola nera e nel simulatore, la sua storia (FIX) e un esercizio. È il modo migliore per **studiare il robot prima
di cambiarlo**. E c'è l'esploso 3D: `Meccanica_STL/esploso_robot.html` (doppio clic).

### Shuri, il collaudatore

Oltre a Claude c'è un secondo agente, **Shuri**, che gira sul Mac del prof: **prova** ogni versione nel simulatore
(circa 16 gare, comprese le prove con i guasti), **analizza** le scatole nere vere con le foto delle camere e scrive un
**rapporto** con i problemi (DOVE / COSA / VERIFICATO o IPOTESI). **Non modifica mai il codice.** Prima di cominciare
un lavoro leggete il suo ultimo rapporto (`Laboratorio Shuri/SHURI_rapporto.md`) e la sua scheda sulle scatole nere
(`ScatoleNere/SHURI_scheda_reale.md`, quando c'è). Chi è, cosa fa e come usarlo: **`Laboratorio Shuri/CHI_E_SHURI.md`**.

## 8. Cosa NON fare

- Non lavorare direttamente su `main` (è protetto: GitHub non te lo lascia fare).
- Non unire (Merge) una pull request, nemmeno la tua: la unisce il prof dopo la revisione, con il controllo verde.
- Non usare l'account GitHub di un altro: ognuno lavora con il suo (così la storia dice chi ha fatto cosa).
- Non modificare le cartelle delle versioni già consegnate né i simulatori già consegnati (`ClaudeRob_Simulatore_V31`, `V32`)
  (il simulatore ha la sua numerazione: se serve cambiarlo, si fa `ClaudeRob_Simulatore_V32`).
- Non caricare foto o video con persone riconoscibili, password o dati personali.
- Non caricare file enormi (sopra 50 MB): zip, video, cartelle dei modelli YOLO restano fuori.

## 9. Sul robot

Sul Raspberry ogni versione ha la sua **cartella pulita** (`~/ClaudeRob_V40`, `~/ClaudeRob_V41`…) e **`~/ClaudeRob_GARA`** è un
collegamento alla versione da usare in gara: all'accensione il robot lancia da solo `~/ClaudeRob_GARA/avvia.sh`.

Portare una versione nuova sul robot (esempio V41):

1. dal Mac copiare la **cartella** intera (non i file sciolti in `/home/pi`):
   `scp -r ~/Documents/Claude/02_Robotica/ClaudeRob_V41 pi@192.168.2.221:~/` (oppure FileZilla, trascinando la cartella);
2. sul robot copiarci dentro i 4 modelli YOLO, che non sono su GitHub:
   `cp -r ~/best_ncnn_model_Cross3 ~/best_ncnn_model_PalCol3 ~/best_ncnn_model_TrianFull3 ~/best_ncnn_model_Exit3 ~/ClaudeRob_V41/`
3. controllare l'**impronta** (deve essere uguale a quella della versione su GitHub):
   `cd ~/ClaudeRob_V41 && for f in $(LC_ALL=C ls *.py); do echo -n $f; cat $f; done | sha256sum | cut -c1-16`
4. renderla la versione di gara: `ln -sfn ~/ClaudeRob_V41 ~/ClaudeRob_GARA`
   (se va male, si torna indietro in un secondo: `ln -sfn ~/ClaudeRob_V40 ~/ClaudeRob_GARA`).

Per lanciarla a mano: `cd ~/ClaudeRob_GARA && ./avvia.sh`, **dallo schermo del robot o da VNC**, non da SSH (il programma
apre le finestre delle camere).
