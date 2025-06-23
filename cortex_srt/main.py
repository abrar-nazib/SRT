# main.py (corrected version)
import cv2
import numpy as np
from datetime import datetime
import threading
import queue
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import time

from camera_manager import CameraManager
from hud_overlay import HUDOverlay
from tracker_factory import TrackerFactory
from pid_controller import PIDController
from arduino_controller import ArduinoController


class TrackingSystem:
    def __init__(self, camera_index=0, camera_rotate=90, arduino_port="COM8"):
        self.camera = CameraManager(
            camera_index=camera_index, rotate_angle=camera_rotate
        )
        self.hud = HUDOverlay()
        self.tracker_factory = TrackerFactory()
        self.pid_controller = PIDController()
        self.arduino_comm = ArduinoController(port=arduino_port)

        self.current_tracker = None
        self.tracking_active = False
        self.target_bbox = None
        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()

        # Tracking algorithms
        # self.algorithms = ["CSRT", "KCF", "MIL", "MOSSE", "MedianFlow"]
        self.algorithms = ["CSRT", "KCF", "MIL", "MOSSE"]
        self.current_algorithm_idx = 0

        # Selection state
        self.selecting = False
        self.selection_start = None
        self.selection_end = None

        # Fire zone parameters
        self.fire_zone_threshold = 30  # pixels from center
        self.in_fire_zone = False
        self.fire_zone_time = 0
        self.min_fire_zone_time = 0.5  # seconds before firing

        # Debug flag
        self.debug = True

    def run(self):
        cv2.namedWindow("Military Tracking System", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Military Tracking System", 720, 1280)
        cv2.setMouseCallback("Military Tracking System", self.mouse_callback)

        while True:
            frame = self.camera.get_frame()
            if frame is None:
                continue

            # Calculate FPS
            self.calculate_fps()

            # Process tracking
            if self.tracking_active and self.current_tracker:
                success, bbox = self.current_tracker.update(frame)
                if success:
                    self.target_bbox = bbox
                    # Calculate error and send to Arduino
                    error_x, error_y = self.calculate_error(bbox, frame.shape)

                    # Check if target is in fire zone
                    distance_from_center = np.sqrt(error_x**2 + error_y**2)
                    self.in_fire_zone = distance_from_center < self.fire_zone_threshold

                    # Track time in fire zone
                    if self.in_fire_zone:
                        if self.fire_zone_time == 0:
                            self.fire_zone_time = time.time()

                        # Check if we've been in fire zone long enough
                        time_in_zone = time.time() - self.fire_zone_time
                        if time_in_zone > self.min_fire_zone_time:
                            laser = 1  # Fire!
                        else:
                            laser = 0
                    else:
                        self.fire_zone_time = 0
                        laser = 0

                    # Send PID commands
                    pan, tilt = self.pid_controller.update(error_x, error_y)

                    if (
                        self.debug and self.frame_count % 10 == 0
                    ):  # Debug every 10 frames
                        print(
                            f"Tracking - Error: ({error_x:.1f}, {error_y:.1f}), "
                            f"PID Out: ({pan:.2f}°, {tilt:.2f}°), "
                            f"Fire Zone: {self.in_fire_zone}, Laser: {laser}"
                        )

                    print(
                        f"Tracking frame {self.frame_count}: {self.algorithms[self.current_algorithm_idx]} - Success: {success} - BBox: {bbox} Error: ({error_x:.1f}, {error_y:.1f})"
                    )
                    self.arduino_comm.send_command(pan, tilt, laser)
                else:
                    if self.debug:
                        print("Tracking failed - target lost")
                    self.tracking_active = False
                    self.target_bbox = None
                    self.in_fire_zone = False
                    self.fire_zone_time = 0
                    # Send stop command when tracking fails
                    self.arduino_comm.send_command(0, 0, 0)

            # Draw selection box if selecting
            display_frame = frame.copy()
            if self.selecting and self.selection_start and self.selection_end:
                cv2.rectangle(
                    display_frame,
                    self.selection_start,
                    self.selection_end,
                    (0, 255, 0),
                    2,
                )

            # Draw HUD with fire zone status
            display_frame = self.hud.draw(
                display_frame,
                self.target_bbox,
                self.fps,
                self.algorithms[self.current_algorithm_idx],
                self.tracking_active,
                self.in_fire_zone,
            )

            cv2.imshow("Military Tracking System", display_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("t"):  # Toggle tracking algorithms
                self.switch_algorithm()
            elif key == ord("r"):  # Reset tracking
                self.reset_tracking()
            elif key == ord(" "):  # Space bar to stop tracking
                self.stop_tracking()
            elif key == ord("f"):  # Manual fire (when in fire zone)
                if self.in_fire_zone and self.tracking_active:
                    print("Manual fire command!")
                    self.arduino_comm.send_command(0, 0, 1)  # Fire laser
            elif key == ord("d"):  # Toggle debug
                self.debug = not self.debug
                print(f"Debug mode: {'ON' if self.debug else 'OFF'}")
            elif key == ord("c"):  # Center servos
                print("Centering servos...")
                self.arduino_comm.send_command(0, 0, 0)

        self.cleanup()

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.debug:
                print("\n=== NEW TARGET SELECTION ===")

            # Always allow new selection, stop current tracking first
            self.stop_tracking()

            # Small delay to ensure commands are processed
            time.sleep(0.05)

            self.selecting = True
            self.selection_start = (x, y)
            self.selection_end = (x, y)

            # Reset HUD acquisition time for new target
            self.hud.acquisition_start_time = None

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.selecting:
                self.selection_end = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.selecting:
                self.selecting = False

                # Calculate bounding box from selection
                x1 = min(self.selection_start[0], self.selection_end[0])
                y1 = min(self.selection_start[1], self.selection_end[1])
                x2 = max(self.selection_start[0], self.selection_end[0])
                y2 = max(self.selection_start[1], self.selection_end[1])

                w = x2 - x1
                h = y2 - y1

                # If it's just a click (not a drag), create a default box
                if w < 5 and h < 5:
                    bbox_size = 50
                    x1 = x - bbox_size // 2
                    y1 = y - bbox_size // 2
                    w = bbox_size
                    h = bbox_size

                # Start tracking with the new target
                self.start_tracking((x1, y1, w, h))

    def start_tracking(self, bbox):
        """Start tracking with a new target"""
        if self.debug:
            print(f"Starting new tracking with bbox: {bbox}")

        frame = self.camera.get_current_frame()
        if frame is None:
            print("ERROR: No frame available for tracking initialization")
            return

        # Ensure bbox is within frame bounds
        height, width = frame.shape[:2]
        x, y, w, h = bbox
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(10, min(w, width - x))
        h = max(10, min(h, height - y))
        bbox = (x, y, w, h)

        # Create new tracker
        algorithm = self.algorithms[self.current_algorithm_idx]
        self.current_tracker = self.tracker_factory.create_tracker(algorithm)

        try:
            # Initialize tracker
            self.current_tracker.init(frame, bbox)

            # Set tracking state
            self.target_bbox = bbox
            self.tracking_active = True
            self.in_fire_zone = False
            self.fire_zone_time = 0

            # IMPORTANT: Reset PID controller for new target
            self.pid_controller.reset()

            if self.debug:
                print(f"✓ Target locked successfully")
                print(f"✓ Using {algorithm} tracker")
                print(f"✓ PID controller reset")

        except Exception as e:
            print(f"ERROR: Failed to initialize tracker: {e}")
            self.tracking_active = False
            self.target_bbox = None
            self.current_tracker = None

    def stop_tracking(self):
        """Stop current tracking"""
        if self.debug and self.tracking_active:
            print("Stopping current tracking...")

        self.tracking_active = False
        self.target_bbox = None
        self.current_tracker = None
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        self.in_fire_zone = False
        self.fire_zone_time = 0

        # Reset PID controller
        self.pid_controller.reset()

        # Send stop command to Arduino (center servos and turn off laser)
        self.arduino_comm.send_command(0, 0, 0)

        # Clear any pending commands
        time.sleep(0.05)

        if self.debug:
            print("✓ Tracking stopped")
            print("✓ Servos centered")
            print("✓ Laser off")

    def switch_algorithm(self):
        self.current_algorithm_idx = (self.current_algorithm_idx + 1) % len(
            self.algorithms
        )
        if self.tracking_active and self.target_bbox:
            # Reinitialize with new algorithm
            algorithm = self.algorithms[self.current_algorithm_idx]
            self.current_tracker = self.tracker_factory.create_tracker(algorithm)
            frame = self.camera.get_current_frame()
            if frame is not None:
                try:
                    self.current_tracker.init(frame, self.target_bbox)
                    # Reset PID when switching algorithms
                    self.pid_controller.reset()
                    print(f"Switched to {algorithm} tracker")
                except Exception as e:
                    print(f"Failed to switch tracker: {e}")
                    self.stop_tracking()
        else:
            print(f"Algorithm set to: {self.algorithms[self.current_algorithm_idx]}")

    def reset_tracking(self):
        """Complete reset of the tracking system"""
        self.stop_tracking()
        # Additional reset for Arduino
        self.arduino_comm.send_command(0, 0, 0)
        print("Tracking system reset")

    def calculate_error(self, bbox, frame_shape):
        """Calculate pixel error from center of frame"""
        target_center_x = bbox[0] + bbox[2] / 2
        target_center_y = bbox[1] + bbox[3] / 2
        frame_center_x = frame_shape[1] / 2
        frame_center_y = frame_shape[0] / 2

        error_x = target_center_x - frame_center_x
        error_y = target_center_y - frame_center_y

        return error_x, error_y

    def calculate_fps(self):
        self.frame_count += 1
        if self.frame_count % 30 == 0:
            current_time = time.time()
            self.fps = 30 / (current_time - self.last_time)
            self.last_time = current_time

    def cleanup(self):
        print("\nShutting down system...")
        self.stop_tracking()
        time.sleep(0.1)  # Give time for final commands
        self.camera.release()
        self.arduino_comm.close()
        cv2.destroyAllWindows()
        print("System shutdown complete")


if __name__ == "__main__":
    print("Starting Military Tracking System...")
    print("Press 'D' to toggle debug mode")
    print("Press 'C' to center servos manually")
    system = TrackingSystem()
    system.run()
