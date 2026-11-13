"""
ProvaGPIO.py  -  [FIX 50] prova dei GPIO e delle luci, SENZA avviare il robot.

Dalla cartella del codice:   python3 ProvaGPIO.py
1) elenca i chip GPIO del Raspberry con il loro nome (quello dei 40 pin si chiama "pinctrl-rp1");
2) accende e spegne 3 volte le due luci (GPIO22 e GPIO23) come fa il robot.
Se qualcosa non va, mandate tutto quello che scrive.
"""
import glob
import time

print("=== Chip GPIO ===")
try:
    import lgpio
    for p in sorted(glob.glob("/dev/gpiochip*"), key=lambda x: int(x.replace("/dev/gpiochip", ""))):
        n = int(p.replace("/dev/gpiochip", ""))
        try:
            h = lgpio.gpiochip_open(n)
            info = lgpio.gpio_get_chip_info(h)
            lgpio.gpiochip_close(h)
            print(f"  {p:18s} si apre    linee {info[1]:3d}   nome {info[3]}")
        except Exception as e:
            print(f"  {p:18s} NON si apre: {e}")
except Exception as e:
    print("  lgpio non disponibile:", e)

print("\n=== Luci (relè attivi bassi: 0 = accesa) ===")
from ViennaClsRobot import CreaLuci
luci = CreaLuci()
print("  tipo di luci usato:", type(luci["Luce1"]).__name__)
for i in range(3):
    for v, testo in ((0, "ACCESE"), (1, "spente")):
        luci["Luce1"].value = v
        luci["Luce2"].value = v
        print(f"  {i + 1}: luci {testo}")
        time.sleep(0.8)
print("Fatto. Se le avete viste lampeggiare 3 volte, le luci funzionano.")
