## Versione e issue

<!-- Esempio: V41 – FIX 106-107 – issue #12 -->
Versione: V__ · FIX: ___ · Issue: #__ · Parte dalla: V__ (l'ultima unita in `main`)

## Le tre domande (rispondi con parole tue)

**1. Che problema risolve?**
<!-- Quale scatola nera, quale secondo, cosa faceva il robot. -->


**2. Cosa farà di diverso il robot adesso?**
<!-- Spiegato a parole, come a un compagno. Niente codice. -->


**3. Come sappiamo che funziona e che non rompe il resto?**
<!-- Le prove nel simulatore: tabella prima / dopo. -->

| Prova | Versione prima | Questa versione |
|---|---|---|
| (la tabella del controllo automatico: Details → Summary) | | |
| scuola, semi 1-6 | | |
| rcj2026 / lunga / contorto | | |
| la prova del problema | | |

## Controlli

- [ ] Parte dall'**ultima versione unita** in `main` (contiene tutti i FIX di prima)
- [ ] Il **controllo automatico** in fondo alla pull request è verde ✅
- [ ] Una funzione nuova ha il suo **interruttore** in `ViennaDataConf.py` (si spegne senza fare una versione nuova)
- [ ] Cartella nuova `ClaudeRob_V__` (le versioni consegnate non sono state toccate)
- [ ] Ogni modifica ha il suo `# [FIX n]` con il motivo
- [ ] `VERSIONE` aggiornata in `ViennaDataConf.py`
- [ ] `CHANGELOG.md` e `LEGGIMI_MODIFICHE.md` aggiornati (fine riga CRLF)
- [ ] `CLAUDE.md` aggiornato ("ultima" versione, "ultimo FIX", storia)
- [ ] Se un'altra versione è stata unita nel frattempo: rifatta partendo da quella, prove rifatte
- [ ] So spiegare questa modifica a voce, senza leggere il codice
