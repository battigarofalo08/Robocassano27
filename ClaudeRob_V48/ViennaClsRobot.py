import time
import smbus2
import threading
import serial
import glob
import ViennaDataConf as RwdConf
import json
import os


# =========================================================
#   [FIX 49 + FIX 50] LUCI (relè su GPIO22 e GPIO23) SUL RASPBERRY PI 5
# =========================================================
# Dopo l'aggiornamento del 18/10/2026 i chip dei GPIO si chiamano /dev/gpiochip11 ... gpiochip15
# (prima 4 o 0) e gpiozero non riesce più ad aprirli: LED(22) dava "can not open gpiochip".
# [FIX 49] cercava il chip giusto e lo passava a gpiozero, ma gpiozero falliva lo stesso
# riaprendolo (21/10). [FIX 50] Ora le due luci NON usano più gpiozero:
#   1) si cerca il chip che si chiama "pinctrl-rp1" (il connettore a 40 pin del Pi 5), qualunque
#      numero abbia, e lo si usa DIRETTAMENTE con lgpio, tenendolo aperto;
#   2) se non c'è (Raspberry più vecchio, simulatore) si usa gpiozero.LED come prima;
#   3) se non funziona niente il robot parte lo stesso SENZA LUCI, con un avviso ben visibile.
# Le luci si usano come prima:  self.linee['Luce1'].value = 0 (accesa, relè attivo basso) o 1.
PIN_LUCI = {'Luce1': 22, 'Luce2': 23}


class _LuceLgpio:
    """Una luce comandata direttamente con lgpio: ha .value come gpiozero.LED (0 o 1)."""
    def __init__(self, lgpio, handle, pin):
        self._lgpio, self._h, self._pin = lgpio, handle, pin
        self._valore = 0
        lgpio.gpio_claim_output(handle, pin, 0)      # come gpiozero.LED: parte a 0

    @property
    def value(self):
        return self._valore

    @value.setter
    def value(self, v):
        self._valore = 1 if v else 0
        self._lgpio.gpio_write(self._h, self._pin, self._valore)


class _LuceFinta:
    """Usata solo se i GPIO non funzionano: il robot parte lo stesso, senza luci."""
    def __init__(self):
        self.value = 1


def _apri_chip_rp1():
    """Restituisce (lgpio, handle, numero) del chip pinctrl-rp1, oppure None."""
    try:
        import lgpio
    except Exception:
        return None                                  # niente lgpio (simulatore, PC)
    candidati = []                                   # (linee, numero, handle) dei chip con "rp1" nel nome
    for percorso in sorted(glob.glob("/dev/gpiochip*")):
        try:
            numero = int(percorso.replace("/dev/gpiochip", ""))
            h = lgpio.gpiochip_open(numero)
            info = lgpio.gpio_get_chip_info(h)       # (esito, numero di linee, nome, etichetta)
        except Exception:
            continue
        etichetta = str(info[3]).strip().lower()
        if etichetta == "pinctrl-rp1" or "rp1" in etichetta:
            candidati.append((etichetta == "pinctrl-rp1", info[1], numero, h, etichetta))
        else:
            lgpio.gpiochip_close(h)
    if not candidati:
        return None
    candidati.sort(reverse=True)                     # prima il nome esatto, poi quello con più linee
    esatto, linee, numero, h, etichetta = candidati[0]
    for c in candidati[1:]:
        lgpio.gpiochip_close(c[3])                   # gli altri si chiudono, quello scelto resta aperto
    print(f"GPIO: uso /dev/gpiochip{numero} ({etichetta}, {linee} linee)")
    return lgpio, h, numero


def CreaLuci():
    """Crea le due luci. Usata da Robot e da ScattaCalibrazione.py."""
    errori = []
    chip = _apri_chip_rp1()
    if chip is not None:
        lgpio, h, numero = chip
        try:
            return {nome: _LuceLgpio(lgpio, h, pin) for nome, pin in PIN_LUCI.items()}
        except Exception as e:
            errori.append(f"lgpio su gpiochip{numero}: {e}")
    try:
        from gpiozero import LED
        return {nome: LED(pin) for nome, pin in PIN_LUCI.items()}
    except Exception as e:
        errori.append(f"gpiozero: {e}")
    print("=" * 70)
    print("ATTENZIONE: LUCI NON DISPONIBILI, il robot parte SENZA LUCI")
    for e in errori:
        print("   ", e)
    print("Lanciate  python3 ProvaGPIO.py  e mandate il risultato.")
    print("=" * 70)
    return {nome: _LuceFinta() for nome in PIN_LUCI}


OFFSET_FILE = "motor_offsets.json"


# =========================================================
#   FUNZIONI ANGOLARI
# =========================================================
def normalize_angle(angle):
    angle = angle % 360
    if angle < 0:
        angle += 360
    return angle

def angle_difference(target, current):
    return (target - current + 540) % 360 - 180


# =========================================================
#   CLASSE ROBOT CON DUE PCA9685 + BLUETOOTH
# =========================================================
class Robot:

    def __init__(self, bus_num=1, arduino_port=None):
        self.running = True
        
        # CaricaFile OffSet motori
        self.motor_offsets = self._load_motor_offsets()

        # I2C
        self.bus = smbus2.SMBus(bus_num)

        # PCA9685 motori 360° (indirizzo 0x41)   [FIX 15] commento corretto
        self.address_motori = 0x41
        self._init_pca9685(self.address_motori)

        # PCA9685 servo 180° (indirizzo 0x40)   [FIX 15] commento corretto
        self.address_braccio = 0x40
        self._init_pca9685(self.address_braccio)

        # Motori
        self.ruota_avanti_sx = 15
        self.ruota_avanti_dx = 0
        self.ruota_dietro_dx = 11
        self.ruota_dietro_sx = 4
        self.servo_pinza = 11
        self.servo_braccio = 4

        # LED
        self.linee = CreaLuci()     # [FIX 50] prima {'Luce1': LED(22), 'Luce2': LED(23)}

        # Stato sensori (arrivano da Arduino)
        self._lock = threading.Lock()
        self._last_distances = (0, 0, 0)
        self._last_imu = (0, 0, 0)
        self._last_switch = (False, False)
        self._last_tilt = (0,0)
        self._last_packet_time = time.time()
        self._storia_becc = []          # [FIX 102] (istante, beccheggio, rotta) degli ultimi 2 s, pacchetto per pacchetto
        # [FIX 82] stato della pendenza (vedi Pendenza())
        self._pend = {"storia": [], "t_ult": 0.0, "att": ("", ""), "cand": ("", ""), "cand_t": 0.0,
                      "da": time.time(), "lock": threading.Lock()}
        # [FIX 87] storia delle letture del laser FRONTALE (per il filtro a mediana) e
        # [FIX 88] BUSSOLA STIMATA dai comandi dei motori, usata quando il giroscopio è bloccato o l'Arduino tace
        self._camp_lock = threading.RLock()     # RLock: print() passa dalla scatola nera, che rilegge i sensori
        self._storia_fr = []                 # (tempo del pacchetto, cm) delle ultime letture del laser frontale
        self._ult_campione_t = None          # tempo dell'ultimo pacchetto già messo nella storia
        self._stima_h = 0.0                  # rotazione stimata dai comandi dei motori (gradi, con segno)
        self._stima_abs = 0.0                # rotazione stimata in valore assoluto (gradi sommati)
        self._stima_vel = 0.0                # gradi/s che i motori stanno facendo girare adesso
        self._stima_t = time.time()
        self._imu_visto = None               # ultima terna (beccheggio, rollio, rotta) vista dal giroscopio
        self._imu_vero_hd = 0                # rotta dell'ultima lettura del giroscopio che è CAMBIATA
        self._stima_al_cambio = 0.0          # _stima_h in quel momento
        self._stima_abs_al_cambio = 0.0      # _stima_abs in quel momento
        self.giroscopio_bloccato = False
        
        # Avvia lettura Arduino
        self.arduino = None
        self._serial_buffer = ""
        self._init_arduino(arduino_port)

        # --- BLUETOOTH ---
        self._bt = None
        self._bt_last = None
        self._bt_buffer = ""
        self._init_bluetooth()

        # PID rotazioni   [FIX 14] costanti spostate in ViennaDataConf.py
        self.pid_kp = RwdConf.PidGiroKp
        self.pid_ki = RwdConf.PidGiroKi
        self.pid_kd = RwdConf.PidGiroKd
        self.pid_integrale = 0.0
        self.pid_errore_prec = 0.0

        self.linee['Luce1'].value = 1
        self.linee['Luce2'].value = 1

        self.motor_range = {
            self.ruota_avanti_sx:  {"min": 310, "stop": 321, "max": 333},
            self.ruota_dietro_sx:  {"min": 310, "stop": 321, "max": 333},
            self.ruota_avanti_dx:  {"min": 310, "stop": 321, "max": 332},
            self.ruota_dietro_dx:  {"min": 311, "stop": 321, "max": 333},
        }

    # ---------------------------------------------------------
    #   BLUETOOTH INIT
    # ---------------------------------------------------------
    def _init_bluetooth(self, porta="/dev/rfcomm0"):
        print("Inizializzazione Bluetooth...")

        try:
            self._bt = serial.Serial(porta, 9600, timeout=0)
            print(f"Bluetooth connesso su {porta}")
        except Exception as e:
            print(f"Errore apertura Bluetooth {porta}: {e}")
            self._bt = None
            return

        threading.Thread(target=self._bt_reader, daemon=True).start()
        print("Lettura Bluetooth avviata")

    # ---------------------------------------------------------
    #   BLUETOOTH READER
    # ---------------------------------------------------------
    def _bt_reader(self):
        print("Thread Bluetooth attivo") 

        while self.running:
            try:
                if self._bt is None:
                    # tenta riconnessione 
                    try:
                        self._bt = serial.Serial("/dev/rfcomm0", 9600, timeout=0)
                        print("Bluetooth riconnesso!")
                    except:
                        time.sleep(1)
                        continue

                n = self._bt.in_waiting
                if n > 0:
                    data = self._bt.read(n).decode(errors="ignore")
                    for c in data:
                        if c.strip():
                            self._bt_last = c
                            if RwdConf.DEBUG:          # [FIX 10] niente stampe in gara
                                print("BT:", repr(c))

                time.sleep(0.01)

            except Exception as e:
                print("Errore lettura Bluetooth:", e)
                try:
                    self._bt.close()
                except:
                    pass
                self._bt = None
                time.sleep(1)


    # ---------------------------------------------------------
    #   COMANDO PUBBLICO BLUETOOTH
    # ---------------------------------------------------------
    def ComandoBluetooth(self):
        # [FIX 16] il comando viene "consumato": prima restituiva sempre
        # l'ultimo carattere ricevuto, all'infinito
        cmd = self._bt_last
        self._bt_last = None
        return cmd

    # ---------------------------------------------------------
    #   RICERCA PORTA ARDUINO
    # ---------------------------------------------------------
    def _find_arduino_port(self):
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        if not ports:
            return None
        return ports[0]

    # ---------------------------------------------------------
    #   ARDUINO SERIAL INIT ROBUSTO
    # ---------------------------------------------------------
    def _init_arduino(self, port=None):
        # [FIX 17] ciclo while al posto della ricorsione: prima la funzione
        # richiamava sé stessa ogni 2 s e dopo ~30 minuti senza Arduino
        # Python si fermava con "RecursionError"
        porta_richiesta = port
        while True:
            print("Ricerca porta Arduino...")
            port = porta_richiesta or self._find_arduino_port()

            if port is None:
                print("Nessuna porta Arduino trovata. Riprovo tra 2 secondi...")
                time.sleep(2)
                continue

            for tentativo in range(5):
                try:
                    print(f"Tentativo {tentativo+1}: apro {port}...")
                    self.arduino = serial.Serial(port, 230400, timeout=0)
                    self.arduino.reset_input_buffer()
                    print(f"Arduino connesso su {port}")
                    break
                except Exception as e:
                    print(f"Errore apertura {port}: {e}")
                    time.sleep(1)
            else:
                print("Impossibile aprire la porta Arduino. Riprovo...")
                time.sleep(2)
                porta_richiesta = None      # al giro dopo cerca di nuovo la porta
                continue
            break

        self._serial_buffer = ""
        threading.Thread(target=self._arduino_reader, daemon=True).start()
        print("Lettura Arduino avviata")

    # ---------------------------------------------------------
    #   ARDUINO SERIAL READER ROBUSTO
    # ---------------------------------------------------------
    def _arduino_reader(self):
        while self.running:
            try:
                if self.arduino is None:
                    time.sleep(0.1)
                    continue

                n = self.arduino.in_waiting
                if n > 0:
                    data = self.arduino.read(n).decode(errors="ignore")
                    self._serial_buffer += data
                    
                    while "\n" in self._serial_buffer:
                        line, self._serial_buffer = self._serial_buffer.split("\n", 1)
                        line = line.strip()
                        
                        if not line:
                            continue

                        parts = line.split(",")
                        if len(parts) != 10:
                            continue

                        try:
                            d1, d2, d3 = map(int, parts[:3])
                            hd, rl, pt = map(int, parts[3:6])
                            sw1 = parts[6] == "0"
                            sw2 = parts[7] == "1"
                            t0,t1 = map(int, parts[8:10])
                        except ValueError:
                            continue

                        with self._lock:
                            self._last_distances = (d1, d2, d3)
                            self._last_imu = (pt, rl, hd)
                            self._last_switch = (sw2, sw1)
                            self._last_tilt = (t0,t1)
                            self._last_packet_time = time.time()
                            # [FIX 102] storico del beccheggio per riconoscere l'altalena (salto brusco)
                            self._storia_becc.append((self._last_packet_time, pt, hd))
                            while self._storia_becc and self._last_packet_time - self._storia_becc[0][0] > 2.0:
                                self._storia_becc.pop(0)
                        self._campiona()             # [FIX 87][FIX 88]
                            
                if time.time() - self._last_packet_time > 0.3:
                    with self._lock:
                        self._last_distances = (0, 0, 0)
                        self._last_imu = (0, 0, 0)
                        self._last_tilt = (0,0) 
                        self._last_switch = (False, False)

                time.sleep(0.005)

            except serial.SerialException as e:
                print("  Arduino disconnesso! Tentativo di riconnessione...", e)
                try:
                    if self.arduino:
                        self.arduino.close()
                except:
                    pass
                self.arduino = None
                time.sleep(1)
                self._init_arduino()    # riapre la porta e avvia un nuovo thread di lettura
                return

            except Exception as e:
                print("Errore lettura Arduino:", e)
                time.sleep(0.05)

    # ---------------------------------------------------------
    #   PCA9685 OFF SET MOTORI FILE
    # ---------------------------------------------------------
    # [FIX 18] NOTA: gli offset salvati in motor_offsets.json NON vengono usati
    # da _map_speed_to_pulse. La taratura reale dei motori è nel dizionario
    # self.motor_range (min/stop/max). Le funzioni sono lasciate per i test.
    def _load_motor_offsets(self):
        if not os.path.exists(OFFSET_FILE):
            return {}
        with open(OFFSET_FILE, "r") as f:
            data = json.load(f)
        return {int(k): float(v) for k, v in data.items()}

    def _save_motor_offsets(self):
        with open(OFFSET_FILE, "w") as f:
            json.dump(self.motor_offsets, f, indent=2)

    # ---------------------------------------------------------
    #   PCA9685 (MODIFICATO PER DUE SCHEDE)
    # ---------------------------------------------------------
    def _init_pca9685(self, address):
        for tentativo in range(5):
            try:
                self.bus.write_byte_data(address, 0x00, 0x20)
                self.bus.write_byte_data(address, 0x01, 0x04)
                self.set_pwm_freq(address, 50)
                print(f"PCA9685 {hex(address)} inizializzato correttamente")
                return
            except OSError as e:
                print(f"[PCA9685 {hex(address)}] Errore I2C ({e}), tentativo {tentativo+1}/5")
                time.sleep(0.2)
        print(f"PCA9685 {hex(address)} NON RISPONDE. Fermare il robot.")

    def set_pwm_freq(self, address, freq):
        prescale = int(round(25000000.0 / (4096 * freq)) - 1)
        old_mode = self.bus.read_byte_data(address, 0x00)
        self.bus.write_byte_data(address, 0x00, (old_mode & 0x7F) | 0x10)
        self.bus.write_byte_data(address, 0xFE, prescale)
        self.bus.write_byte_data(address, 0x00, old_mode)
        time.sleep(0.005)
        self.bus.write_byte_data(address, 0x00, old_mode | 0xa1)

    def _set_pwm(self, address, channel, on, off):
        data = [on & 0xFF, on >> 8, off & 0xFF, off >> 8]
        # [FIX 12] prima: 4 tentativi x 0,1 s = fino a 0,4 s di blocco per canale
        # (1,6 s per uno Sterzo su 4 ruote). Ora al massimo 30 ms.
        # Se compare spesso il WARN qui sotto, controllare l'alimentazione del Raspberry!
        for _ in range(3):
            try:
                self.bus.write_i2c_block_data(address, 0x06 + 4 * channel, data)
                return
            except OSError:
                time.sleep(0.01)
        print(f"[WARN] PCA9685 {hex(address)} non risponde (I2C Err 121) - canale:", channel)

    # ---------------------------------------------------------
    #   MOTORI 360° (PCA 0x40)
    # ---------------------------------------------------------
    def _map_speed_to_pulse(self, channel, speed_percent):
        r = self.motor_range[channel]
        STOP = r["stop"]
        MIN  = r["min"]
        MAX  = r["max"]

        speed_percent = max(-100, min(100, speed_percent))

        if speed_percent > 0:
            pulse = STOP + (MAX - STOP) + (speed_percent / 100) * (410 - MAX)
        else:
            pulse = STOP - (STOP - MIN) + (speed_percent / 100) * (MIN - 200)

        return int(pulse)

    def _set_motor(self, address, channel, speed_percent):
        pulse = self._map_speed_to_pulse(channel, speed_percent)
        self._set_pwm(address, channel, 0, pulse)

    def adjust_motor_offset(self, channel, delta):
        current = self.motor_offsets.get(channel, 0.0)
        new_offset = current + delta
        self.motor_offsets[channel] = new_offset
        self._save_motor_offsets()
        print(f"[Robot] Offset canale {channel}: {new_offset:.3f}")
        self._set_motor(self.address_motori, channel, 0)

    def calibra_min(self, channel):
        print(f"\nCalibrazione MIN per canale {channel}")
        for pulse in range(370, 240, -1):
            self._set_pwm(self.address_motori, channel, 0, pulse)
            time.sleep(0.5)
            print("Pulse:", pulse)
        self._set_motor(self.address_motori, channel, 0)

    def calibra_max(self, channel):
        print(f"\nCalibrazione MAX per canale {channel}")
        for pulse in range(290, 380):
            self._set_pwm(self.address_motori, channel, 0, pulse)
            time.sleep(0.5)
            print("Pulse:", pulse)
        self._set_motor(self.address_motori, channel, 0)

    def test_canali_reali(self):
        print("\n=== TEST CANALI REALI ===")
        canali = [15, 0, 4, 11]

        for c in canali:
            print(f"\nCanale {c} -> PWM 330 (avanti)")
            self._set_pwm(self.address_motori, c, 0, 330)
            time.sleep(1)

            print(f"Canale {c} -> PWM 290 (indietro)")
            self._set_pwm(self.address_motori, c, 0, 309)
            time.sleep(1)

            self._set_motor(self.address_motori, c, 0)

    def test_direzioni_grezzo(self):
        print("\nTEST DIREZIONE GREZZO (senza offset, senza inversioni)")
        canali = [self.ruota_avanti_sx, self.ruota_dietro_sx,
                  self.ruota_avanti_dx, self.ruota_dietro_dx]

        for c in canali:
            print(f"\nCanale {c} -> +40")
            self._set_pwm(self.address_motori, c, 0, 335)
            time.sleep(2)
            self._set_motor(self.address_motori, c, 0)

    def test_motor_stop(self, channel):
        print("\n=== TEST STOP MOTORE 360° ===")
        print(f"Canale: {channel}")
        print("Comandi:")
        print("  +  -> +0.5% offset")
        print("  -  -> -0.5% offset")
        print("  t  -> test deriva 30 secondi")
        print("  q  -> esci\n")

        self._set_motor(self.address_motori, channel, 0)

        while True:
            cmd = input(">> ").strip()

            if cmd == "+":
                self.adjust_motor_offset(channel, +10.0)

            elif cmd == "-":
                self.adjust_motor_offset(channel, -10.0)

            elif cmd == "t":
                print("\nAvvio test deriva (30s)...")
                for i in range(30):
                    self._set_motor(self.address_motori, channel, 0)
                    print(f"  Secondo {i+1}/30 - offset: {self.motor_offsets.get(channel, 0):.3f}")
                    time.sleep(1)
                print("\nTest completato.\n")

            elif cmd == "q":
                print("Uscita dal test.")
                break

            else:
                print("Comando non valido.")

    def stop_tick_from_range(self):
        for ch in [self.ruota_avanti_sx,
                   self.ruota_dietro_sx,
                   self.ruota_avanti_dx,
                   self.ruota_dietro_dx]:

            stop_tick = self.motor_range[ch]["stop"]
            self._set_pwm(self.address_motori, ch, 0, stop_tick)

    def stop_motors(self):
        self.stop_tick_from_range()

    def SpegniPWM(self):
        # [FIX 6] Spegne TUTTE le uscite della scheda motori (registro ALL_LED_OFF_H).
        # Senza segnale i servo a rotazione continua si fermano anche se lo
        # "stop" tarato si è spostato. Si usa in chiusura o dopo un errore.
        for _ in range(3):
            try:
                self.bus.write_byte_data(self.address_motori, 0xFD, 0x10)
                return
            except OSError:
                time.sleep(0.01)

    # ---------------------------------------------------------
    #   SERVO 180° (PCA 0x41)
    # ---------------------------------------------------------
    def _set_servo_angle(self, address, channel, angle):
        PulseMin = 110
        PulseMax = 530
        pulse = int((PulseMax - (angle / 180.0) * (PulseMax - PulseMin)))
        self._set_pwm(address, channel, 0, pulse)

    # ---------------------------------------------------------
    #   LETTURE PUBBLICHE (DA ARDUINO)
    # ---------------------------------------------------------
    def Distanze(self):
        with self._lock:
            return self._last_distances

    def GetGyro(self):
        # [FIX 88] BUSSOLA DI RISERVA. Scatola nera 03/11 (V27): il giroscopio è rimasto fermo a (-2, -2, 0) per
        # TUTTA la gara (laser vivi, Arduino vivo) e ogni Gira girava sul posto per 8 s fino al TIMEOUT
        # (12 volte!), con il robot che si perdeva. Anche quando l'Arduino tace (tutte le gare di ottobre, e
        # il 03/11 a 163 s) la rotta valeva 0 e le rotazioni non finivano più.
        # Ora, se il giroscopio è bloccato o l'Arduino tace, la rotta è STIMATA dai comandi dei motori:
        # ultima rotta vera + rotazione comandata da allora (GRADI_S_PER_VEL gradi/s per ogni punto di
        # velocità, misurato sulle scatole nere di ottobre: 35 gradi/s a 47, 50 gradi/s a 68).
        # È meno precisa del giroscopio, ma le rotazioni finiscono quasi dove devono.
        self._campiona()
        with self._lock:
            imu = self._last_imu
            muto = time.time() - self._last_packet_time > 0.3
        if not (muto or self.giroscopio_bloccato) or not getattr(RwdConf, "BUSSOLA_STIMATA", True):
            return imu
        hv = int(round(normalize_angle(self._imu_vero_hd + self._stima_ora() - self._stima_al_cambio))) % 360
        return (0, 0, hv) if muto else (imu[0], imu[1], hv)

    def BussolaStato(self):
        # [FIX 88] per la scatola nera e il cruscotto: "giroscopio", "stimata: giroscopio bloccato", "stimata: Arduino muto"
        with self._lock:
            muto = time.time() - self._last_packet_time > 0.3
        if muto:
            return "stimata: Arduino muto"
        if self.giroscopio_bloccato:
            return "stimata: giroscopio bloccato"
        return "giroscopio"

    def _stima_ora(self):
        # [FIX 88] rotazione stimata fino a questo istante
        return self._stima_h + self._stima_vel * (time.time() - self._stima_t)

    def _imposta_rotazione(self, gradi_s):
        # [FIX 88] chiamata a ogni comando dei motori: chiude il tratto precedente e imposta la nuova velocità di rotazione
        with self._camp_lock:
            adesso = time.time()
            dt = max(0.0, adesso - self._stima_t)
            self._stima_h += self._stima_vel * dt
            self._stima_abs += abs(self._stima_vel) * dt
            self._stima_t = adesso
            self._stima_vel = gradi_s

    def _campiona(self):
        # [FIX 87][FIX 88] Chiamata a ogni pacchetto dell'Arduino (thread di lettura) e a ogni lettura dei sensori.
        # Mette il laser frontale nella storia e controlla se il giroscopio si muove ancora.
        with self._lock:
            tp = self._last_packet_time
            d = self._last_distances
            imu = self._last_imu
        if time.time() - tp > 0.3:
            return                                   # Arduino muto: i valori sono finti (0)
        avviso = None                                # stampato FUORI dal lock
        with self._camp_lock:
            if tp == self._ult_campione_t:
                return
            self._ult_campione_t = tp
            st = self._storia_fr
            # la storia è un segnale "a gradini": (da quando, valore). Un valore ripetuto (l'Arduino rimanda l'ultima
            # misura finché il laser non ne ha una nuova) allunga il gradino invece di aggiungere un campione
            if not st or st[-1][1] != d[1]:
                st.append((tp, d[1]))
            while len(st) > 2 and tp - st[1][0] > 1.0:   # tengo i gradini dell'ultimo secondo
                st.pop(0)
            if len(st) > 300:
                del st[:-300]
            adesso = time.time()
            stima = self._stima_h + self._stima_vel * (adesso - self._stima_t)
            stima_abs = self._stima_abs + abs(self._stima_vel) * (adesso - self._stima_t)
            if imu != self._imu_visto:
                prima = self._imu_visto
                self._imu_visto = imu
                if prima is not None and self.giroscopio_bloccato:
                    self.giroscopio_bloccato = False
                    avviso = "GIROSCOPIO DI NUOVO VIVO: torno a usare la rotta vera"
                self._imu_vero_hd = imu[2]
                self._stima_al_cambio = stima
                self._stima_abs_al_cambio = stima_abs
            else:
            # il giroscopio NON è cambiato: se nel frattempo i motori hanno fatto girare il robot di molti gradi,
            # è bloccato (un BNO055 vivo cambia di almeno 1 grado appena il robot ruota)
                soglia = getattr(RwdConf, "GIRO_BLOCCATO_GRADI", 60)
                if not self.giroscopio_bloccato and stima_abs - self._stima_abs_al_cambio > soglia:
                    self.giroscopio_bloccato = True
                    avviso = (f"GIROSCOPIO BLOCCATO: i motori hanno girato il robot di circa "
                              f"{stima_abs - self._stima_abs_al_cambio:.0f} gradi ma il giroscopio legge sempre {imu}. "
                              f"Uso la bussola STIMATA dai motori (controllate il BNO055!)")
        if avviso:
            print(avviso)

    def FrontaleFiltrato(self, finestra=None):
        # [FIX 87] LASER FRONTALE FILTRATO. Scatola nera 03/11: il laser frontale salta di continuo
        # (5, 54, 74, 134 cm; 15, 91, 11, 461 cm...: il 15% delle letture cambia di più di 50 cm da una all'altra;
        # a ottobre era meno del 2%, il 29/10 già il 31%). Una sola lettura sotto 15 cm faceva partire il
        # controllo dell'ostacolo e due volte il robot ha aggirato un ostacolo che NON c'era.
        # Ora si usa la MEDIANA delle letture degli ultimi LASER_FR_FINESTRA_S secondi (gli 0, letture non
        # valide, sono scartati): una lettura isolata non sposta la mediana, un ostacolo vero sì (in 0,15 s).
        # Restituisce 0 se l'Arduino tace (come prima: 0 = non so).
        self._campiona()
        if finestra is None:
            finestra = getattr(RwdConf, "LASER_FR_FINESTRA_S", 0.3)
        with self._lock:
            muto = time.time() - self._last_packet_time > 0.3
            grezzo = self._last_distances[1]
        if muto:
            return 0
        with self._camp_lock:
            st = list(self._storia_fr)
        if not st:
            return grezzo
        # MEDIANA PESATA SUL TEMPO: ogni valore conta per quanto tempo è durato nella finestra. Una lettura
        # sbagliata dura un pacchetto (30-50 ms su 300) e non può essere la mediana; un ostacolo vero sì.
        # Con l'Arduino vivo lo 0 vuol dire "niente entro la portata" (vedi LaserVeri, FIX 48): conta come LONTANO.
        lontano = getattr(RwdConf, "LASER_LONTANO", 150)
        adesso = time.time()
        t_ini = adesso - finestra
        pesi = []
        for i, (t0, d) in enumerate(st):
            t1 = st[i + 1][0] if i + 1 < len(st) else adesso
            a, b = max(t0, t_ini), min(t1, adesso)
            if b > a:
                pesi.append((d if d > 0 else lontano, b - a))
        if not pesi:
            d = st[-1][1]
            return d if d > 0 else lontano
        pesi.sort()
        meta = sum(p for _, p in pesi) / 2
        somma = 0.0
        for d, p in pesi:
            somma += p
            if somma > meta:                         # ">" e non ">=": a parità vince il valore più lontano (prudente)
                return d
        return pesi[-1][0]

    def GetTilt(self):
        with self._lock:
            return self._last_tilt

    def GetSwitch(self):
        with self._lock:
            return {
                'sw_pal': self._last_switch[0],
                'sw_sof': self._last_switch[1]
            }

    def GetSensori(self):
        self._campiona()                             # [FIX 87][FIX 88]
        with self._lock:
            return {
                'distanze': self._last_distances,
                'imu': self._last_imu,
                'switch': self._last_switch,
                'tilt': self._last_tilt
            }

    def StoriaBeccheggio(self, secondi=1.5):
        # [FIX 102] (istante, beccheggio, rotta) degli ultimi "secondi", come arrivano dall'Arduino (non filtrati)
        adesso = time.time()
        with self._lock:
            return [x for x in self._storia_becc if adesso - x[0] <= secondi]

    def Pendenza(self):
        # [FIX 82] IL ROBOT CAPISCE SE E' SU UN TRATTO INCLINATO, dai dati del giroscopio (BNO055 sull'Arduino).
        # imu = (beccheggio, rollio, rotta): beccheggio > 0 = muso in alto (salita), rollio = inclinato di lato.
        # Un valore solo non basta (dossi, scosse quando parte o si ferma): si prende la MEDIANA degli ultimi
        # PENDENZA_FINESTRA_S secondi. Due soglie (isteresi): il tratto inclinato inizia sopra PENDENZA_INIZIO
        # gradi e finisce sotto PENDENZA_FINE, così lo stato non sfarfalla quando si è proprio vicini alla soglia.
        # Il nuovo stato deve durare PENDENZA_CONFERMA_S prima di essere preso per buono.
        # Restituisce un dizionario: tipo ("piano", "salita", "discesa", "di lato", "salita di lato", ...,
        # "sconosciuto" se l'Arduino tace), becc e roll (gradi, mediana), testo da mostrare, da_s (da quanti
        # secondi dura lo stato) e piano_da_s (da quanti secondi il robot è in piano, 0 se non lo è).
        adesso = time.time()
        with self._lock:
            becc_ora, roll_ora, _ = self._last_imu
            vivo = adesso - self._last_packet_time < 0.5
        p = self._pend
        with p["lock"]:
            if not vivo:
                return {"tipo": "sconosciuto", "becc": 0, "roll": 0, "testo": "pendenza sconosciuta (Arduino muto)",
                        "da_s": 0.0, "piano_da_s": 0.0}
            if self.giroscopio_bloccato:             # [FIX 89] il giroscopio non dice niente di vero
                return {"tipo": "sconosciuto", "becc": 0, "roll": 0, "testo": "pendenza sconosciuta (giroscopio bloccato)",
                        "da_s": 0.0, "piano_da_s": 0.0}
            # [FIX 89] Scatola nera 03/11: "in piano (da 425990 s)". Il Raspberry non ha l'ora giusta all'accensione
            # e la corregge da internet DOPO l'avvio del programma: l'orologio salta avanti di giorni.
            if adesso - p["da"] > 86400 or adesso < p["da"]:
                p["da"] = p["cand_t"] = adesso
                p["storia"] = []
            if adesso - p["t_ult"] >= 0.04 or not p["storia"]:
                p["storia"].append((adesso, becc_ora, roll_ora))
                p["t_ult"] = adesso
            finestra = getattr(RwdConf, "PENDENZA_FINESTRA_S", 0.5)
            while len(p["storia"]) > 1 and adesso - p["storia"][0][0] > finestra:
                p["storia"].pop(0)
            bs = sorted(x[1] for x in p["storia"])
            rs = sorted(x[2] for x in p["storia"])
            becc, roll = bs[len(bs) // 2], rs[len(rs) // 2]
            inizio = getattr(RwdConf, "PENDENZA_INIZIO", 8)
            fine = getattr(RwdConf, "PENDENZA_FINE", 5)
            sb = fine if p["att"][0] else inizio          # isteresi: se sono già in salita/discesa basta di meno
            sr = fine if p["att"][1] else inizio
            cb = "salita" if becc > sb else "discesa" if becc < -sb else ""
            a_destra = (roll > 0) == bool(getattr(RwdConf, "ROLLIO_POSITIVO_A_DESTRA", False))
            cr = ("destra" if a_destra else "sinistra") if abs(roll) > sr else ""
            cand = (cb, cr)
            if cand == p["att"]:
                p["cand"] = cand
            elif cand != p["cand"]:
                p["cand"], p["cand_t"] = cand, adesso
            elif adesso - p["cand_t"] >= getattr(RwdConf, "PENDENZA_CONFERMA_S", 0.4):
                p["att"], p["da"] = cand, p["cand_t"]
            cb, cr = p["att"]
            da_s = adesso - p["da"]
        if not cb and not cr:
            tipo, testo = "piano", "in piano"
        else:
            parti = []
            if cb:
                parti.append(f"{cb.upper()} {abs(becc):.0f} gradi")
            if cr:
                parti.append(f"INCLINATO verso {cr} {abs(roll):.0f} gradi")
            tipo = " ".join(x for x in (cb, "di lato" if cr else "") if x)
            testo = " e ".join(parti)
        return {"tipo": tipo, "becc": becc, "roll": roll, "testo": f"{testo} (da {da_s:.0f} s)",
                "da_s": round(da_s, 1), "piano_da_s": round(da_s, 1) if tipo == "piano" else 0.0}

    # ---------------------------------------------------------
    #   LED
    # ---------------------------------------------------------
    def GetOnLed1(self):
        self.linee['Luce1'].value = 0
        time.sleep(0.5)

    def GetOnLed2(self):
        self.linee['Luce2'].value = 0
        time.sleep(0.5)

    def GetOffLed1(self):
        self.linee['Luce1'].value = 1
        time.sleep(0.05)    # [FIX 19] spegnere non richiede attesa (prima 0,5 s)

    def GetOffLed2(self):
        self.linee['Luce2'].value = 1
        time.sleep(0.05)    # [FIX 19] spegnere non richiede attesa (prima 0,5 s)

    # ---------------------------------------------------------
    #   STERZO E MOVIMENTO
    # ---------------------------------------------------------
    def Sterzo(self, velocita, sterzo):
        OffSetLAvanti=1.17
        OffSetRAvanti=0.83
        OffSetLDietro=0.83
        OffSetRDietro=1.17
        left=0
        right=0
        v = max(-100, min(100, velocita))
        s = max(-100, min(100, sterzo))
        # [FIX 88] rotazione che questo comando produce (per la bussola stimata). Sul posto (sterzo ±100) il robot
        # gira di GRADI_S_PER_VEL x velocità gradi/s, nello stesso verso anche andando indietro (vedi sotto).
        # In curva la stima è grossolana (STIMA_CURVA): serve solo a non perdere del tutto la direzione.
        k = getattr(RwdConf, "GRADI_S_PER_VEL", 0.74)
        if s == 100:
            self._imposta_rotazione(k * abs(v))
        elif s == -100:
            self._imposta_rotazione(-k * abs(v))
        else:
            self._imposta_rotazione(k * s * getattr(RwdConf, "STIMA_CURVA", 0.5))

        if s == 0:
            if v > 0:
                left = int(v*OffSetLAvanti)
                right = int(-v*OffSetRAvanti)
            else:
                left = int(v*OffSetLDietro)
                right = int(-v*OffSetRDietro)
        elif s == 100:
            if v > 0:
                left = int(v*OffSetLAvanti)
                right = int(v*OffSetRAvanti)
            else:
                left = int(-v*OffSetLDietro)
                right = int(-v*OffSetRDietro)            
        elif s==-100:    
            if v > 0:
                left = int(-v*OffSetLAvanti)
                right = int(-v*OffSetRAvanti)
            else:
                left = int(v*OffSetLDietro)
                right = int(v*OffSetRDietro)        
        else:
            if v > 0:
                left = int((v+s)*OffSetLAvanti)
                right = int((-v+s)*OffSetRAvanti)
            else:
                left = int((v+s)*OffSetLDietro)
                right = int((-v+s)*OffSetRDietro)

        self._set_motor(self.address_motori, self.ruota_avanti_sx, left)
        self._set_motor(self.address_motori, self.ruota_dietro_sx, left)
        self._set_motor(self.address_motori, self.ruota_avanti_dx, right)
        self._set_motor(self.address_motori, self.ruota_dietro_dx, right)
        
    def Stop(self):
        self._imposta_rotazione(0.0)                 # [FIX 88]
        self.stop_motors() 

    # ---------------------------------------------------------
    #   FILTRI E MOVIMENTI AVANZATI
    # ---------------------------------------------------------
    def filtro_heading(self, heading, alpha=0.98):
        if not hasattr(self, "_heading_filtrato"):
            self._heading_filtrato = heading
        self._heading_filtrato = alpha * self._heading_filtrato + (1 - alpha) * heading
        return self._heading_filtrato

    def _rotation_speed_profile(self, errore, velocita_base):
        errore = abs(errore)
        if errore > 30:
            return velocita_base
        else:
            return max(30, int(velocita_base * 0.7))

    def Gira(self, gradi, velocita=40, timeout=None):
        if timeout is None:
            timeout = RwdConf.TimeoutGira
        _, _, start_heading = self.GetGyro()
        start_heading = normalize_angle(start_heading)
        target = normalize_angle(start_heading + gradi)
        direction = 1 if gradi > 0 else -1
        t_inizio = time.time()
        storia = []                                 # [FIX 72] ultime letture, per la velocità di rotazione
        anticipo_s = getattr(RwdConf, "GIRA_ANTICIPO_S", 0.0)
        # [FIX 97] GIRA(180) NON GIRAVA. Scatola nera 05/11 ore 15:12 (V34), secondi 470-493: dopo l'arena il robot
        # doveva fare dietrofront con Gira(180) ma restava fermo e lo ripeteva ogni 0,4 s per 23 s. Il motivo:
        # l'errore si calcolava come differenza tra obiettivo e direzione attuale, che sta tra -180 e +180; con
        # obiettivo esattamente opposto vale -180, cioè "già oltre l'obiettivo", e Gira finiva subito.
        # Ora si conta quanto il robot HA GIRATO dall'inizio, passo per passo: funziona per qualsiasi angolo.
        girato = 0.0
        precedente = start_heading

        while True:
            _, _, heading = self.GetGyro()
            heading = normalize_angle(heading)
            girato += angle_difference(heading, precedente)     # [FIX 97]
            precedente = heading

            errore = gradi - girato                             # [FIX 97] prima angle_difference(target, heading)
            if RwdConf.DEBUG:
                print(target, heading, errore)
            # [FIX 72] FERMARSI IN ANTICIPO. Il giroscopio vede la rotazione con 0,2 s di ritardo e il robot,
            # fermati i motori, gira ancora: prima Gira finiva 5-7 gradi oltre (scatole nere 23 e 26/10).
            # Ora si ferma quando mancano "velocità di rotazione x GIRA_ANTICIPO_S" gradi (da 3 a 15).
            adesso = time.time()
            storia.append((adesso, heading))
            while len(storia) > 2 and adesso - storia[0][0] > 0.15:
                storia.pop(0)
            vel_ang = 0.0
            if storia[-1][0] - storia[0][0] > 0.05:
                vel_ang = abs(angle_difference(storia[-1][1], storia[0][1])) / (storia[-1][0] - storia[0][0])
            soglia = max(3.0, min(15.0, vel_ang * anticipo_s))
            if errore * direction < soglia or not self.GetSwitch()['sw_sof']:   # [FIX 8] lettura con lock
                break
            if time.time() - t_inizio > timeout:                    # [FIX 8] timeout
                print(f"[Gira] TIMEOUT dopo {timeout}s - errore residuo {errore:.0f} gradi")
                break

            vel = max(RwdConf.VelCrs, min(velocita, abs(errore) * 1.2))
            sterzo = 100 * direction

            self.Sterzo(vel, sterzo)
            time.sleep(0.02)
        # [FIX 44] FERMA I MOTORI A FINE ROTAZIONE. Prima Gira usciva dal ciclo lasciando le ruote che
        # giravano a VelCrs: se dopo c'era una pausa (time.sleep) il robot continuava a ruotare.
        # Nel simulatore: Gira(90) + pausa di 0,5 s = 132 gradi; Gira(10) + pausa di 0,2 s = 29 gradi.
        self.Stop()

    def _pid(self, errore, dt):
        self.pid_integrale += errore * dt
        derivata = 0
        if dt > 0:
            derivata = (errore - self.pid_errore_prec) / dt
        output = (
            self.pid_kp * errore +
            self.pid_ki * self.pid_integrale +
            self.pid_kd * derivata
        )
        self.pid_errore_prec = errore
        return output

    def GiraPID(self, gradi, velocita=40):
        _, _, start_heading = self.GetGyro()
        start_heading = normalize_angle(start_heading)

        target = normalize_angle(start_heading + gradi)
        direction = 1 if gradi > 0 else -1

        full_turn = abs(gradi) == 360
        passed_half = False

        self.pid_integrale = 0
        self.pid_errore_prec = 0
        last_time = time.time()

        while True:
            _, _, heading = self.GetGyro()
            heading = normalize_angle(heading)
            errore = angle_difference(target, heading)

            if full_turn:
                if not passed_half and abs(angle_difference(start_heading, heading)) > 180:
                    passed_half = True
                if passed_half and abs(errore) < 2:
                    break
            else:
                if abs(errore) < 2:
                    break

            now = time.time()
            dt = now - last_time
            last_time = now

            pid_output = self._pid(errore, dt)
            vel = self._rotation_speed_profile(errore, velocita)
            sterzo = 100 if direction > 0 else -100
            vel = max(20, min(vel, abs(pid_output)))

            self.Sterzo(vel, sterzo)
            time.sleep(0.02)

    def Dritto(self, velocita=40, durata=2.0, heading_ref=None, ruota=True):
        # [FIX 93] ruota=False: niente raddrizzamenti RUOTANDO SUL POSTO (serve passando una porta stretta: ruotando,
        # il retro del robot si sposta di lato e lo spigolo del LED tocca lo stipite)
        # [FIX 13] heading_ref opzionale: se lo passiamo, il robot mantiene SEMPRE
        # la stessa direzione anche chiamando Dritto tante volte di seguito.
        # Prima ogni chiamata ripartiva dalla direzione attuale e gli errori si sommavano.
        if heading_ref is None:
            _, _, heading_ref = self.GetGyro()
        heading_ref = normalize_angle(heading_ref)

        start = time.time()
        self.pid_integrale = 0
        self.pid_errore_prec = None             # [FIX 64] vedi sotto
        last_time = time.time()
        soglia_ruota = getattr(RwdConf, "DRITTO_RUOTA_GRADI", 0) if ruota else 0

        rotazione = 0.0                             # [FIX 72] secondi passati a raddrizzarsi sul posto
        while time.time() - start < durata + rotazione:
            if not self.GetSwitch()['sw_sof']:      # [FIX 88] switch spento: prima girava a vuoto (RuotaVerso esce subito)
                # [FIX 105] RETE DI SICUREZZA: fermo i motori e aspetto un poco (al massimo 0,1 s) prima di uscire.
                # Prima Dritto usciva all'istante e un ciclo a tempo fatto di Dritto e laser (ControllaAperturaMuro,
                # rapporto di Shuri del 5/11) girava a vuoto senza mai aspettare: nel simulatore la gara si piantava.
                self.Stop()
                time.sleep(min(0.1, max(0.0, durata)))
                break
            _, _, heading = self.GetGyro()
            heading = normalize_angle(heading)

            errore = angle_difference(heading_ref, heading)

            # [FIX 64] SCATOLA NERA 23/10: con i servo a rotazione continua una correzione di sterzo
            # piccola (sotto circa 40 a velocità 47) NON fa girare il robot: le due ruote vanno già quasi al
            # massimo e la differenza sparisce. Il robot restava storto di 10-15 gradi per secondi interi.
            # Se l'errore supera DRITTO_RUOTA_GRADI il robot si raddrizza RUOTANDO SUL POSTO (quello sì
            # funziona sempre) e poi riparte dritto.
            if soglia_ruota and abs(errore) > soglia_ruota:
                # [FIX 72] il tempo passato a ruotare sul posto NON conta nella durata: così il robot avanza
                # sempre della stessa distanza (prima, con le rotazioni più lente, nell'ostacolo girava
                # troppo presto e lo toccava). Al massimo 2 s in più per ogni Dritto.
                t_r = time.time()
                esito_r = self.RuotaVerso(heading_ref, timeout=1.0)
                rotazione = min(2.0, rotazione + (time.time() - t_r))
                if esito_r == "bloccato":
                    soglia_ruota = 0        # non riesco a ruotare (tocco qualcosa): per ora avanzo come prima
                self.pid_integrale = 0
                self.pid_errore_prec = None
                last_time = time.time()
                continue

            now = time.time()
            dt = now - last_time
            last_time = now
            # [FIX 64] Prima, al primo giro del ciclo, dt era di pochi microsecondi e la derivata
            # (errore - 0) / dt diventava enorme: il robot faceva un colpo di rotazione al massimo a OGNI
            # chiamata di Dritto (nella scatola nera: "Sterzo 47 100" ogni 0,1 s nel giro dei muri).
            if self.pid_errore_prec is None or dt < 0.005:
                self.pid_errore_prec = errore
                dt = max(dt, 0.02)

            correzione = self._pid(errore, dt)
            correzione = max(-100, min(100, correzione))

            self.Sterzo(velocita, correzione)
            time.sleep(0.02)

    def RuotaVerso(self, rotta, velocita=None, tolleranza=1.5, timeout=1.5):
        # [FIX 64] Ruota SUL POSTO fino alla direzione assoluta "rotta", controllando il giroscopio a ogni
        # passo (anello chiuso). Lontano dall'obiettivo ruota di continuo; vicino a piccoli colpi.
        # [FIX 72] SCATOLE NERE 23 e 26/10: la rotazione si vede sul giroscopio 0,2 s DOPO il comando e,
        # fermati i motori, il robot gira ancora di 5-7 gradi (servo che rallentano + ritardo del BNO055).
        # Per questo prima le correzioni andavano sempre oltre (pallina: "correggo di 4 gradi" e il robot
        # girava di 11). Ora:
        #  - rotazione continua solo finché mancano più di RUOTA_ANTICIPO gradi;
        #  - poi stop e attesa RUOTA_ASSESTA_S: si legge dove è arrivato davvero;
        #  - poi colpi brevi (più brevi quanto meno manca), ognuno seguito da RUOTA_PAUSA_S di attesa.
        # [FIX 65] GIROSCOPIO COME SENSORE DI TOCCO: se comandiamo la rotazione ma la direzione non cambia,
        # uno spigolo del robot sta toccando qualcosa.
        # Restituisce True (arrivato), False (tempo finito) o "bloccato".
        if velocita is None:
            velocita = getattr(RwdConf, "VelRuota", 47)
        blocco_s = getattr(RwdConf, "BLOCCO_S", 0.6)
        blocco_gradi = getattr(RwdConf, "BLOCCO_GRADI", 2)
        anticipo = getattr(RwdConf, "RUOTA_ANTICIPO", 12)
        assesta = getattr(RwdConf, "RUOTA_ASSESTA_S", 0.25)
        pausa = getattr(RwdConf, "RUOTA_PAUSA_S", 0.2)
        colpo_grado = getattr(RwdConf, "RUOTA_COLPO_S_GRADO", 0.008)
        rotta = normalize_angle(rotta)
        t0 = time.time()
        storia = []
        esito = False
        continua = False                            # stavo ruotando di continuo?
        while time.time() - t0 < timeout:
            if not self.GetSwitch()['sw_sof']:
                break
            _, _, hd = self.GetGyro()
            errore = angle_difference(rotta, normalize_angle(hd))
            if abs(errore) <= tolleranza and not continua:
                esito = True
                break
            verso = 100 if errore > 0 else -100
            if abs(errore) > anticipo:
                if not continua:
                    storia = []
                continua = True
                adesso = time.time()
                storia.append((adesso, hd))
                while storia and adesso - storia[0][0] > blocco_s:
                    storia.pop(0)
                if adesso - storia[0][0] > blocco_s * 0.9 and abs(angle_difference(hd, storia[0][1])) < blocco_gradi:
                    esito = "bloccato"
                    break
                self.Sterzo(velocita, verso)
                time.sleep(0.02)
                continue
            if continua:
                # [FIX 72] mancano pochi gradi: mi fermo e aspetto che il robot (e il giroscopio) si assestino
                self.Stop()
                time.sleep(assesta)
                continua = False
                storia = []
                continue
            # [FIX 70] anche a colpi: se in 1,5 s la direzione cambia meno di 1 grado è bloccato
            adesso = time.time()
            storia.append((adesso, hd))
            while storia and adesso - storia[0][0] > 1.5:
                storia.pop(0)
            if adesso - storia[0][0] > 1.4 and abs(angle_difference(hd, storia[0][1])) < 1:
                esito = "bloccato"
                break
            self.Sterzo(velocita, verso)            # colpo breve...
            time.sleep(min(0.12, max(0.03, abs(errore) * colpo_grado)))
            self.Stop()                             # ...e attesa per leggere la direzione vera
            time.sleep(pausa)
        self.Stop()
        return esito

    # ---------------------------------------------------------
    #   BRACCIO E PINZA
    # ---------------------------------------------------------
    def Braccio(self, angolo):
        self._set_servo_angle(self.address_braccio, self.servo_braccio, angolo)

    def Pinza(self, angolo):
        self._set_servo_angle(self.address_braccio, self.servo_pinza, angolo)

    # ---------------------------------------------------------
    #   STOP PULITO
    # ---------------------------------------------------------
    def StopLetture(self):
        print("Chiusura Robot...")
        self.running = False
        time.sleep(0.2)
        try:
            if self.arduino:
                self.arduino.close()
        except:
            pass
        self.stop_motors()
        self.SpegniPWM()            # [FIX 6]
        print("Robot fermato correttamente.")
