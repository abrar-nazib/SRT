# pid_controller.py (continued)
import time

class PIDController:
    def __init__(self, kp=0.1, ki=0.01, kd=0.05):
        self.kp = kp  # Proportional gain
        self.ki = ki  # Integral gain
        self.kd = kd  # Derivative gain
        
        self.prev_error_x = 0
        self.prev_error_y = 0
        self.integral_x = 0
        self.integral_y = 0
        
        self.last_time = time.time()
        
        # Limits for servo movement (degrees)
        self.max_output = 10
        self.min_output = -10
        
    def update(self, error_x, error_y):
        current_time = time.time()
        dt = current_time - self.last_time
        
        if dt <= 0:
            dt = 0.001
            
        # Calculate PID for X axis
        self.integral_x += error_x * dt
        derivative_x = (error_x - self.prev_error_x) / dt
        
        output_x = (self.kp * error_x + 
                   self.ki * self.integral_x + 
                   self.kd * derivative_x)
        
        # Calculate PID for Y axis
        self.integral_y += error_y * dt
        derivative_y = (error_y - self.prev_error_y) / dt
        
        output_y = (self.kp * error_y + 
                   self.ki * self.integral_y + 
                   self.kd * derivative_y)
        
        # Apply limits
        output_x = self.constrain(output_x, self.min_output, self.max_output)
        output_y = self.constrain(output_y, self.min_output, self.max_output)
        
        # Update previous values
        self.prev_error_x = error_x
        self.prev_error_y = error_y
        self.last_time = current_time
        
        # Convert pixel error to degrees
        # Assuming 1920x1080 resolution and 60 degree FOV
        degrees_per_pixel_x = 60.0 / 1920
        degrees_per_pixel_y = 35.0 / 1080
        
        pan_degrees = output_x * degrees_per_pixel_x
        tilt_degrees = output_y * degrees_per_pixel_y
        
        return pan_degrees, tilt_degrees
        
    def constrain(self, value, min_val, max_val):
        return max(min_val, min(value, max_val))
        
    def reset(self):
        self.prev_error_x = 0
        self.prev_error_y = 0
        self.integral_x = 0
        self.integral_y = 0
        self.last_time = time.time()