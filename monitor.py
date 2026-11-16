import subprocess
import time

VM2_IP = "172.31.25.34"

while True:
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "2", VM2_IP],
        stdout=subprocess.DEVNULL
    )

    if result.returncode == 0:
        print("🟢 CONNECTED - VM2 is reachable")
    else:
        print("🔴 DISCONNECTED - VM2 is unreachable")

    time.sleep(3)
