from ViennaClsRobot import Robot
import time

r = Robot()

while True:
    print("Distanze:", r.Distanze())
    print("IMU:", r.GetGyro())
    print("Switch:", r.GetSwitch())
    print("Tilt: ",r.GetTilt())
    print("----")
    time.sleep(0.05)
