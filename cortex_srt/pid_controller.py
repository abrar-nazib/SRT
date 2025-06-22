import time
from collections import deque


class PIDController:
    def __init__(self, kp=0.085, ki=0.00001, kd=0.04, integral_window=100):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.prev_error_x = 0
        self.prev_error_y = 0

        self.integral_window = integral_window
        self.integral_x = deque(maxlen=integral_window)
        self.integral_y = deque(maxlen=integral_window)

        self.last_time = time.time()

        self.max_output = 5
        self.min_output = -5

    def update(self, error_x, error_y):
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0:
            dt = 0.001

        # Append current errors
        self.integral_x.append(error_x)
        self.integral_y.append(error_y)

        # Integral is the sum of the error queue
        integral_sum_x = sum(self.integral_x)
        integral_sum_y = sum(self.integral_y)

        # Derivative is change in error
        derivative_x = error_x - self.prev_error_x
        derivative_y = error_y - self.prev_error_y

        # PID output
        output_x = self.kp * error_x + self.ki * integral_sum_x + self.kd * derivative_x
        output_y = self.kp * error_y + self.ki * integral_sum_y + self.kd * derivative_y

        self.prev_error_x = error_x
        self.prev_error_y = error_y
        self.last_time = current_time

        degrees_per_pixel_x = 70.0 / 720
        degrees_per_pixel_y = 120.0 / 1280

        pan_degrees = self.constrain(
            output_x * degrees_per_pixel_x, self.min_output, self.max_output
        )
        tilt_degrees = self.constrain(
            output_y * degrees_per_pixel_y, self.min_output, self.max_output
        )
        print(
            f"PID Output: Pan={pan_degrees:.2f}°, Tilt={tilt_degrees:.2f}° Output X={output_x:.2f}, Output Y={output_y:.2f}"
        )
        return pan_degrees, tilt_degrees

    def constrain(self, value, min_val, max_val):
        return max(min_val, min(value, max_val))

    def reset(self):
        self.prev_error_x = 0
        self.prev_error_y = 0
        self.integral_x.clear()
        self.integral_y.clear()
        self.last_time = time.time()
