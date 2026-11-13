from ViennaClsRobot import Robot
import time

robot = Robot()

print("In attesa di comandi Bluetooth...") 

while True:
    cmd = robot.ComandoBluetooth() 
    if cmd:
        print("Ricevuto:", cmd)
    time.sleep(0.1)
