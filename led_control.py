from gpiozero import LED
from time import sleep

led = LED(17)

try:
    led.on()
    print("LED is ON")
    sleep(5)
    led.off()
    print("LED is OFF")
finally:
    led.close()

