# arduino_controller.py
import serial
import threading
import queue
import time

class ArduinoController:
    def __init__(self, port='COM3', baudrate=115200):
        try:
            self.serial = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
            print(f"Connected to Arduino on {port}")
        except:
            print(f"Failed to connect to Arduino on {port}")
            self.serial = None
            
        self.command_queue = queue.Queue()
        self.running = True
        
        # Start communication thread
        self.comm_thread = threading.Thread(target=self._communication_loop)
        self.comm_thread.daemon = True
        self.comm_thread.start()
        
    def _communication_loop(self):
        while self.running:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                if self.serial and self.serial.is_open:
                    try:
                        self.serial.write(command.encode())
                        self.serial.flush()
                    except:
                        print("Error sending command to Arduino")
            time.sleep(0.01)  # 100Hz update rate
            
    def send_command(self, pan_degrees, tilt_degrees, laser):
        """Send command in format: '+2.5:-3.5:0'"""
        command = f"{pan_degrees:+.1f}:{tilt_degrees:+.1f}:{laser}\n"
        self.command_queue.put(command)
        
    def close(self):
        self.running = False
        self.comm_thread.join()
        if self.serial and self.serial.is_open:
            self.serial.close()