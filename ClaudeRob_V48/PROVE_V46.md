# V46 – prove da completare (issue #28)

## Prove automatiche eseguite su questa copia

- `py_compile` sui file Python modificati.
- Prova Otsu con due gruppi sintetici di pixel (nero e bianco): soglia valida nell'intervallo configurato.
- Prova del ripiego: soglia Otsu simulata fuori 60–170 → uso del valore originale di `ViennaDataConf.SOGLIA_NERO`.
- Prova logica del fuoco: impostazione manuale con limitazione al range dichiarato dalla camera e ripiego su autofocus continuo quando `LensPosition` non è disponibile.
- Controllo che `VERSIONE` sia `ClaudeRob V46`, che il FIX sia 112 e che changelog/documentazione siano aggiornati.

## Prove che richiedono il robot reale

Con il robot fermo, posizionato sulla linea e con i LED accesi, annotare in almeno tre condizioni:

| Condizione | Soglia Otsu | Soglia usata | Esposizione (us) | Gain | Fuoco (diottrie) | Linea piena? |
|---|---:|---:|---:|---:|---:|---|
| Palestra/laboratorio con luci accese | | | | | | |
| Luci spente e luce dalla finestra | | | | | | |
| Torcia laterale | | | | | | |

Verificare che nel terminale e nella scatola nera appaia l'evento `CAMERA LINEA` con la soglia effettivamente scelta. Controllare inoltre la nitidezza della linea: il fuoco richiesto (8,3 cm) può essere limitato dal range del modulo camera.

## Simulatore V32

Eseguire V45 e V46 con gli stessi semi e confrontare:

- scuola semi 1 e 2;
- `rcj2026`;
- `scuola_nuova` seme 1.

Nel simulatore l'autotaratura è volutamente saltata: la V46 usa la stessa `SOGLIA_NERO` di configurazione, così la prova confronta il comportamento di gara senza dipendere da una luce simulata casuale.
