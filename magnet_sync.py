import socket
import subprocess
from gpiozero import DigitalInputDevice
import time

# GPIO Pin for KE0043 Digital Output
SENSOR_PIN = 16  # GPIO 16 (BCM numbering)

# Initialize the KE0043 sensor as a digital input device with pull-up
sensor = DigitalInputDevice(SENSOR_PIN, pull_up=True)

def get_esp32_ip(last_octet=50):
    """
    Dynamically determines the ESP32's IP address based on the Raspberry Pi's subnet.
    """
    try:
        output = subprocess.check_output(["hostname", "-I"]).decode().strip()
        pi_ip = output.split()[0]  # Get the first IP address from the list
        subnet = ".".join(pi_ip.split(".")[:3])  # Extract the subnet
        esp32_ip = f"{subnet}.{last_octet}"
        print(f"Determined ESP32 IP: {esp32_ip}")
        return esp32_ip
    except Exception as e:
        raise Exception(f"Error determining ESP32 IP address: {e}")

# ESP32 details
ESP32_IP = get_esp32_ip()
ESP32_SYNC_PORT = 12346  # Port for synchronization messages

def send_sync_message(socket_connection):
    """
    Sends a synchronization ("SYNC") message to the ESP32 using an open socket connection.
    """
    try:
        socket_connection.sendall('SYNC\n'.encode('utf-8'))
        print("Sent SYNC message to ESP32")
    except Exception as e:
        print(f"Failed to send SYNC message to ESP32: {e}")
        raise

def connect_to_esp32():
    """
    Establishes a persistent connection to the ESP32.
    """
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ESP32_IP, ESP32_SYNC_PORT))
            print("Connected to ESP32")
            return sock
        except Exception as e:
            print(f"Failed to connect to ESP32: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

def magnet_detected():
    """
    Callback function triggered when the sensor detects the magnet.
    """
    global esp32_socket
    print("Magnet detected!")
    try:
        send_sync_message(esp32_socket)
    except Exception:
        # Reconnect if the connection to ESP32 is lost
        print("Reconnecting to ESP32...")
        esp32_socket = connect_to_esp32()

def magnet_no_longer_detected():
    """
    Callback function triggered when the sensor no longer detects the magnet.
    """
    print("Magnet no longer detected.")

# Establish an initial connection to the ESP32
esp32_socket = connect_to_esp32()

# Assign event handlers
sensor.when_activated = magnet_detected        # Triggered when sensor goes LOW (magnet detected)
sensor.when_deactivated = magnet_no_longer_detected  # Triggered when sensor goes HIGH (no magnet)

print("Waiting for magnet events...")
try:
    # Keep the script running to listen for events
    while True:
        time.sleep(0.1)  # Prevent CPU overutilization
except KeyboardInterrupt:
    print("\nMagnet detection stopped.")
    esp32_socket.close()
    print("Connection to ESP32 closed.")

