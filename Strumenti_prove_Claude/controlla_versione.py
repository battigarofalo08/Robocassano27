#!/usr/bin/env python3
"""IL CONTROLLO AUTOMATICO di una versione nuova (lo fa GitHub a ogni pull request, si può lanciare anche a mano).

Come nelle aziende: le regole della squadra le controlla la macchina, non la memoria delle persone.

  python3 Strumenti_prove_Claude/controlla_versione.py                  (controlla l'ultima ClaudeRob_V<n>)
  python3 Strumenti_prove_Claude/controlla_versione.py ClaudeRob_V48
  python3 Strumenti_prove_Claude/controlla_versione.py --base origin/main   (anche: niente versioni vecchie toccate)

Controlli (le regole di CLAUDE.md e COME_LAVORARE.md):
  1. i file .py si compilano;
  2. VERSIONE in ViennaDataConf.py = nome della cartella;
  3. la versione contiene TUTTI i [FIX n] delle altre versioni nel repository ("ogni versione nuova contiene tutte
     le precedenti": il 12/11 la V47 non aveva il FIX 112 della V46 e nessuno se n'era accorto);
  4. ci sono CHANGELOG.md e LEGGIMI_MODIFICHE.md, con fine riga CRLF, e parlano dell'ultimo FIX;
  5. con --base: la pull request non modifica le cartelle delle versioni già unite.
Stampa anche l'impronta (la stessa della scatola nera). Esce con 1 se qualcosa non va.
"""
import glob
import hashlib
import os
import re
import subprocess
import sys

RADICE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def numero(cartella):
    m = re.search(r"ClaudeRob_V(\d+)$", cartella.rstrip("/"))
    return int(m.group(1)) if m else -1


def versioni():
    c = [p for p in glob.glob(os.path.join(RADICE, "ClaudeRob_V*")) if os.path.isdir(p) and numero(p) >= 0]
    return sorted(c, key=numero)


def fix_di(cartella):
    trovati = set()
    for f in glob.glob(os.path.join(cartella, "*.py")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            trovati.update(int(n) for n in re.findall(r"\[FIX (\d+)\]", fh.read()))
    return trovati


def impronta(cartella):
    """Lo stesso calcolo di ViennaMonitor (FIX 86): nome + contenuto dei .py in ordine."""
    h = hashlib.sha256()
    for f in sorted(glob.glob(os.path.join(cartella, "*.py"))):
        h.update(os.path.basename(f).encode())
        with open(f, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def main():
    a = sys.argv[1:]
    base = a[a.index("--base") + 1] if "--base" in a else None
    nomi = [x for x in a if x.startswith("ClaudeRob_V") or "/ClaudeRob_V" in x]
    tutte = versioni()
    nuova = os.path.join(RADICE, os.path.basename(nomi[0].rstrip("/"))) if nomi else tutte[-1]
    n = numero(nuova)
    nome = os.path.basename(nuova)
    errori, avvisi = [], []
    print(f"== Controllo di {nome}")

    # 1. compilazione
    for f in sorted(glob.glob(os.path.join(nuova, "*.py"))):
        try:
            compile(open(f, encoding="utf-8").read(), f, "exec")      # solo la sintassi, senza scrivere niente
        except (SyntaxError, ValueError, UnicodeDecodeError) as e:
            errori.append(f"{os.path.basename(f)} non si compila: {str(e)[:200]}")

    # 2. VERSIONE
    try:
        conf = open(os.path.join(nuova, "ViennaDataConf.py"), encoding="utf-8").read()
        m = re.search(r'^VERSIONE\s*=\s*"ClaudeRob V(\d+)"', conf, re.M)
        if not m:
            errori.append("in ViennaDataConf.py manca VERSIONE = \"ClaudeRob V<n>\"")
        elif int(m.group(1)) != n:
            errori.append(f"VERSIONE dice V{m.group(1)} ma la cartella è {nome}")
    except FileNotFoundError:
        errori.append("manca ViennaDataConf.py")

    # 3. tutti i FIX delle altre versioni
    miei = fix_di(nuova)
    for altra in tutte:
        if altra == nuova or numero(altra) > n:
            continue
        mancano = sorted(fix_di(altra) - miei)
        if mancano:
            errori.append(f"mancano i FIX {mancano} che ci sono in {os.path.basename(altra)}: "
                          f"la versione nuova deve partire da TUTTE quelle già unite")
    ultimo = max(miei) if miei else None

    # 4. CHANGELOG e LEGGIMI_MODIFICHE
    for doc in ("CHANGELOG.md", "LEGGIMI_MODIFICHE.md"):
        p = os.path.join(nuova, doc)
        if not os.path.exists(p):
            errori.append(f"manca {doc}")
            continue
        dati = open(p, "rb").read()
        lf_soli = dati.count(b"\n") - dati.count(b"\r\n")
        if lf_soli:
            errori.append(f"{doc}: {lf_soli} righe senza CRLF (Windows): vanno salvate con fine riga CRLF")
        if ultimo is not None and f"{ultimo}".encode() not in dati:
            avvisi.append(f"{doc} non nomina il FIX {ultimo}")

    # 5. versioni vecchie non toccate
    if base:
        try:
            out = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=RADICE,
                                 capture_output=True, text=True, check=True).stdout.split()
            esistenti = subprocess.run(["git", "ls-tree", "-d", "--name-only", base], cwd=RADICE,
                                       capture_output=True, text=True, check=True).stdout.split()
            toccate = sorted({f.split("/")[0] for f in out
                              if f.startswith("ClaudeRob_V") and f.split("/")[0] in esistenti
                              and numero(f.split("/")[0]) >= 0 and "__pycache__" not in f})
            if toccate:
                errori.append(f"la pull request modifica versioni già unite: {toccate} "
                              f"(si copia l'ultima in una cartella nuova e si lavora lì)")
        except Exception as e:
            avvisi.append(f"controllo delle versioni vecchie non riuscito: {e}")

    print(f"   impronta: {impronta(nuova)}   ultimo FIX: {ultimo}   FIX trovati: {len(miei)}")
    for x in avvisi:
        print("   AVVISO:", x)
    for x in errori:
        print("   ERRORE:", x)
    print("== RISULTATO:", "OK" if not errori else f"{len(errori)} ERRORI")
    riga = (f"| {nome} | `{impronta(nuova)}` | FIX {ultimo} | " +
            ("✅ OK" if not errori else "❌ " + "<br>".join(errori)) + " |")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("### Controllo della versione\n\n| Versione | Impronta | Ultimo | Esito |\n|---|---|---|---|\n"
                    + riga + "\n\n" + "".join(f"- avviso: {x}\n" for x in avvisi))
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
