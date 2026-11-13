#!/usr/bin/env python3
"""PROVA NEL SIMULATORE della versione nuova contro la precedente (lo fa GitHub a ogni pull request).

  python3 Strumenti_prove_Claude/confronta_simulatore.py ClaudeRob_V48            (contro la versione prima)
  python3 Strumenti_prove_Claude/confronta_simulatore.py ClaudeRob_V48 ClaudeRob_V47

Fa girare le due versioni sulle stesse piste con lo stesso seme (ogni gara in un processo a parte) e scrive una
tabella: come finisce, quanto dura, quante LoP, se le due gare sono identiche campione per campione.
Esce con 1 solo se la versione nuova va in ERRORE PYTHON. Una gara diversa non è un errore: si guarda la tabella
(se la versione cambia il seguilinea deve essere diversa; se cambia solo la cabina deve essere identica).
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

RADICE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROVE = [("scuola_nuova", 1), ("scuola_nuova", 2), ("scuola", 1), ("rcj2026", 1)]

ESEGUI = r'''
import sys, json, hashlib
sys.path.insert(0, sys.argv[1])
import esegui
r = esegui.esegui(sys.argv[2], sys.argv[3], 480, cfg={"seme": int(sys.argv[5])}, scenario=sys.argv[4])
p = r.get("punteggio") if isinstance(r.get("punteggio"), dict) else {}
print("RISULTATO " + json.dumps({"fine": r["fine"], "durata": r["durata"], "errore": r["errore"], "lop": p.get("lop"),
      "firma": hashlib.sha256(json.dumps([r["campioni"], r["eventi"]]).encode()).hexdigest()[:12]}))
'''


def numero(c):
    m = re.search(r"ClaudeRob_V(\d+)$", c.rstrip("/"))
    return int(m.group(1)) if m else -1


def simulatore():
    s = [c for c in glob.glob(os.path.join(RADICE, "ClaudeRob_Simulatore_V*")) if os.path.exists(os.path.join(c, "esegui.py"))]
    return max(s, key=lambda c: int(re.search(r"_V(\d+)$", c).group(1)))


def gara(sim, cartella, scen, seme, cartella_tmp):
    nome = f"ci_{os.path.basename(cartella)}_{scen}_{seme}"
    out = subprocess.run([sys.executable, "-c", ESEGUI, sim, cartella, nome, scen, str(seme)],
                         capture_output=True, text=True, cwd=cartella_tmp, timeout=900)
    for f in glob.glob(os.path.join(sim, f"replay_{nome}.json")):
        os.remove(f)                                  # il replay non serve (ed è escluso da .gitignore)
    righe = [r for r in out.stdout.splitlines() if r.startswith("RISULTATO ")]
    if not righe:
        return {"fine": "il simulatore non è partito", "durata": 0, "errore": (out.stderr or out.stdout)[-1500:],
                "lop": None, "firma": "-"}
    return json.loads(righe[-1][len("RISULTATO "):])


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("-")]
    tutte = sorted([c for c in glob.glob(os.path.join(RADICE, "ClaudeRob_V*")) if numero(c) >= 0], key=numero)
    nuova = os.path.join(RADICE, os.path.basename(a[0].rstrip("/"))) if a else tutte[-1]
    if len(a) > 1:
        vecchia = os.path.join(RADICE, os.path.basename(a[1].rstrip("/")))
    else:
        prima = [c for c in tutte if numero(c) < numero(nuova)]
        vecchia = prima[-1] if prima else None
    sim = simulatore()
    nn, nv = os.path.basename(nuova), os.path.basename(vecchia) if vecchia else "-"
    print(f"== Simulatore {os.path.basename(sim)}: {nn} contro {nv}")
    tab = [f"### Simulatore: {nn} contro {nv}", "",
           f"| Pista (seme) | {nv} | {nn} | Uguali? |", "|---|---|---|---|"]
    errori = []
    with tempfile.TemporaryDirectory() as tmp:
        for scen, seme in PROVE:
            rn = gara(sim, nuova, scen, seme, tmp)
            rv = gara(sim, vecchia, scen, seme, tmp) if vecchia else None

            def cella(r):
                if r is None:
                    return "-"
                if r["errore"]:
                    return "❌ ERRORE PYTHON"
                return f"{r['fine']}, {r['durata']:.0f} s" + (f", {r['lop']} LoP" if r.get("lop") is not None else "")
            uguali = "-" if rv is None else ("✅ identiche" if rv["firma"] == rn["firma"] else "diverse")
            riga = f"| {scen} ({seme}) | {cella(rv)} | {cella(rn)} | {uguali} |"
            tab.append(riga)
            print("  ", riga)
            if rn["errore"]:
                errori.append(f"{scen} seme {seme}:\n{rn['errore']}")
    testo = "\n".join(tab) + "\n"
    if errori:
        testo += "\n**ERRORI della versione nuova:**\n\n```\n" + "\n".join(errori)[-3000:] + "\n```\n"
        print("\n".join(errori))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(testo + "\n")
    print("== RISULTATO:", "OK" if not errori else "ERRORE PYTHON nella versione nuova")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
