from gpiozero import Motor, PWMOutputDevice
from time import sleep

# Set up the Motor with GPIO 17 (forward) and GPIO 18 (backward)
motor = Motor(forward=17, backward=18)
speed_control = PWMOutputDevice(22)  # Connect ENA to GPIO 22 for speed control (PWM)

def run_motor_indefinitely():
    print("Enter motor power as a percentage (0-100). Enter 'q' to quit.")

    # Start the motor forward initially
    motor.forward()

    while True:
        try:
            # Prompt the user for the motor speed percentage
            user_input = input("Set motor power (%): ")

            # Allow the user to quit by entering 'q'
            if user_input.lower() == 'q':
                print("Exiting program.")
                break

            # Convert input to a floating-point number for speed percentage
            speed_percent = float(user_input)
            
            # Ensure the value is within 0-100 range
            if 0 <= speed_percent <= 100:
                # Convert percentage to 0.0 - 1.0 range for PWM
                speed = speed_percent / 100.0
                speed_control.value = speed
                print(f"Motor power set to {speed_percent}%")
            else:
                print("Please enter a valid percentage between 0 and 100.")

        except ValueError:
            print("Invalid input. Please enter a number between 0 and 100 or 'q' to quit.")

    # Stop the motor after exiting the loop
    motor.stop()
    print("Motor stopped.")

try:
    # Run the motor control loop
    run_motor_indefinitely()

finally:
    # Clean up resources on exit
    motor.close()
    speed_control.close()

