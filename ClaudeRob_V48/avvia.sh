#!/bin/bash
# Avvia il robot dalla sua cartella (così trova i modelli YOLO e il cruscotto).
# Uso:  ./avvia.sh      (la prima volta: chmod +x avvia.sh)
cd "$(dirname "$0")"
python3 RwdFoto.py
