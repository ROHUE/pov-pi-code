import cv2
from flask import Flask, render_template, Response
from collections import deque
import socket
import subprocess
import tensorflow as tf
import numpy as np
import time
from threading import Thread
from queue import Queue

app = Flask(__name__)

# Initialize the camera and set resolution
camera = cv2.VideoCapture(0)  # Replace with '/dev/video0' if needed for Linux
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 160)  # Lower resolution to reduce processing
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
camera.set(cv2.CAP_PROP_FPS, 10)  # Limit FPS to 10

# Load the pretrained model
MODEL_PATH = './models/fer2013_mini_XCEPTION.119-0.65.hdf5'
model = tf.keras.models.load_model(MODEL_PATH, compile=False)

# TensorFlow optimization for minimal resource usage
tf.config.optimizer.set_jit(True)  # Enable XLA for faster inference
physical_devices = tf.config.experimental.list_physical_devices('GPU')
if physical_devices:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

# Emotion labels
emotion_labels = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

# Buffer for smoothing emotions
emotion_buffer = deque(maxlen=5)  # Store the last 5 detected emotions

# Frame queue for threading
frame_queue = Queue(maxsize=10)

# Function to preprocess frames for the model
def preprocess_frame(frame):
    """
    Preprocess the frame for the model.
    """
    face = cv2.resize(frame, (48, 48))  # Resize to 48x48 as required by the model
    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    face = np.expand_dims(face, axis=-1)  # Add channel dimension
    face = np.expand_dims(face, axis=0)  # Add batch dimension
    face = face / 255.0  # Normalize pixel values
    return face

# Function to determine ESP32's IP programmatically
def get_esp32_ip(last_octet=50):
    """
    Get the ESP32 IP address based on the Raspberry Pi's subnet.
    """
    try:
        output = subprocess.check_output(["hostname", "-I"]).decode().strip()
        pi_ip = output.split()[0]
        subnet = ".".join(pi_ip.split(".")[:3])
        return f"{subnet}.{last_octet}"
    except Exception as e:
        raise Exception(f"Error determining ESP32 IP address: {e}")

ESP32_IP = get_esp32_ip()
ESP32_PORT = 12345

# Function to send emotion to ESP32 with persistent connection
def send_emotion_to_esp32(emotion):
    """
    Sends the detected emotion to the ESP32 over a persistent TCP connection.
    """
    try:
        if not hasattr(send_emotion_to_esp32, 'socket'):
            send_emotion_to_esp32.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_emotion_to_esp32.socket.connect((ESP32_IP, ESP32_PORT))
        
        send_emotion_to_esp32.socket.sendall((emotion + '\n').encode('utf-8'))
        print(f"Sent emotion to ESP32: {emotion}")
    except Exception as e:
        print(f"Failed to send emotion to ESP32: {e}")
        if hasattr(send_emotion_to_esp32, 'socket'):
            send_emotion_to_esp32.socket.close()
            delattr(send_emotion_to_esp32, 'socket')

# Worker thread for emotion detection
def emotion_detection_worker():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            try:
                preprocessed_face = preprocess_frame(frame)
                predictions = model.predict(preprocessed_face)
                dominant_emotion_idx = np.argmax(predictions[0])
                dominant_emotion = emotion_labels[dominant_emotion_idx]
                emotion_buffer.append(dominant_emotion)

                # Calculate smoothed emotion
                smoothed_emotion = max(set(emotion_buffer), key=emotion_buffer.count)
                print(f"Smoothed detected emotion: {smoothed_emotion}")

                # Send emotion to ESP32
                send_emotion_to_esp32(smoothed_emotion)

            except Exception as e:
                print(f"Error detecting emotions: {e}")

Thread(target=emotion_detection_worker, daemon=True).start()

# Frame generator for video feed
def gen_frames():
    frame_skip = 30  # Skip every 30 frames
    frame_counter = 0
    
    while True:
        success, frame = camera.read()
        if not success:
            print("Failed to read frame from camera.")
            break

        frame_counter += 1

        # Only process every 30th frame
        if frame_counter % frame_skip == 0 and not frame_queue.full():
            frame_queue.put(frame)  # Add frame to the queue for emotion detection

        # Encode the frame for streaming
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])  # Lower quality to 50
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)

