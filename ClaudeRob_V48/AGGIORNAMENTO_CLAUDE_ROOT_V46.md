# Aggiornamento da riportare nel CLAUDE.md della cartella progetto

Il file `CLAUDE.md` di progetto non era presente nello ZIP V45 ricevuto. Per non sostituire alla cieca il documento originale, queste sono le modifiche da riportare nella copia di progetto:

1. Nella regola 1, indicare `ClaudeRob_V46` come versione di lavoro di Battista; specificare che V45 resta la base di confronto e che V46 non è ancora validata sul robot.
2. Nella regola 4, aggiornare l'ultimo FIX da 111 a 112.
3. Nella regola 5, mantenere l'obbligo di CRLF per `CHANGELOG.md` e `LEGGIMI_MODIFICHE.md`.
4. Nella sezione GitHub, annotare issue #28 = Battista / V46 / FIX112 e PR #30 = Gioele / V47 / FIX113 ancora aperta al momento della preparazione. Se la PR #30 viene unita prima della PR V46, Battista deve rifare la V46 partendo dalla versione appena unita, riportare le proprie modifiche e rinumerare il FIX dopo il FIX113, come prescrive la guida.
5. Nella storia delle versioni, aggiungere: `V46 (issue #28, Battista) – FIX112: fuoco manuale della camera linea (se supportato), prova a 20 FPS, blocco dell'esposizione con LED accesi, autotaratura Otsu all'avvio e registrazione della soglia nella scatola nera.`
6. Nella sezione “Aperto / da fare”, aggiungere che la V46 deve ancora essere verificata sul robot in almeno tre condizioni di luce e confrontata con V45 nel simulatore V32 prima della consegna.

La V46 inclusa in questo ZIP è un ramo di lavoro locale basato sulla V45 caricata dall'utente, non una versione pubblicata o unita su GitHub.
