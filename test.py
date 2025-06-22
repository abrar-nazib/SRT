import cv2
import numpy as np
import serial
import time


# Tracker Strategy Interface
class TrackerStrategy:
    def init(self, frame, roi):
        pass

    def update(self, frame):
        pass

    @property
    def name(self):
        return "Unknown"


# Concrete Tracker Strategies
class KCFTracker(TrackerStrategy):
    def __init__(self):
        self.tracker = cv2.legacy.TrackerKCF_create()
        self._name = "KCF"

    def init(self, frame, roi):
        self.tracker.init(frame, roi)

    def update(self, frame):
        return self.tracker.update(frame)

    @property
    def name(self):
        return self._name


class CSRTTracker(TrackerStrategy):
    def __init__(self):
        self.tracker = cv2.legacy.TrackerCSRT_create()
        self._name = "CSRT"

    def init(self, frame, roi):
        self.tracker.init(frame, roi)

    def update(self, frame):
        return self.tracker.update(frame)

    @property
    def name(self):
        return self._name


class MOSSETracker(TrackerStrategy):
    def __init__(self):
        self.tracker = cv2.legacy.TrackerMOSSE_create()
        self._name = "MOSSE"

    def init(self, frame, roi):
        self.tracker.init(frame, roi)

    def update(self, frame):
        return self.tracker.update(frame)

    @property
    def name(self):
        return self._name


class GOTURNTracker(TrackerStrategy):
    def __init__(self):
        self.tracker = cv2.legacy.TrackerGOTURN_create()
        self._name = "GOTURN"

    def init(self, frame, roi):
        self.tracker.init(frame, roi)

    def update(self, frame):
        return self.tracker.update(frame)

    @property
    def name(self):
        return self._name


class MILTracker(TrackerStrategy):
    def __init__(self):
        self.tracker = cv2.legacy.TrackerMIL_create()
        self._name = "MIL"

    def init(self, frame, roi):
        self.tracker.init(frame, roi)

    def update(self, frame):
        return self.tracker.update(frame)

    @property
    def name(self):
        return self._name


# Tracker Context
class TrackerContext:
    def __init__(self, strategy: TrackerStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: TrackerStrategy):
        self.strategy = strategy

    def init_tracker(self, frame, roi):
        self.strategy.init(frame, roi)

    def update_tracker(self, frame):
        return self.strategy.update(frame)

    @property
    def tracker_name(self):
        return self.strategy.name


# Simple Proportional Controller (can be extended to full PID)
class PController:
    def __init__(self, kp):
        self.kp = kp

    def compute(self, error):
        return self.kp * error


# Mouse callback for ROI selection
tracking = False
roi = None
success = False


def select_roi(event, x, y, flags, param):
    global tracking, roi
    if event == cv2.EVENT_LBUTTONDOWN:
        roi = (x - 25, y - 25, 50, 50)  # 50x50 ROI centered on click
        tracking = True


class Serial:
    def write(self, message):
        print(f"Serial not available. Writing to console {message}")


# Main function
def main():
    global tracking, roi

    # Video capture setup (1080p)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    # Serial setup (adjust port and baud rate as needed)
    try:
        ser = serial.Serial("COM3", 9600, timeout=1)
        time.sleep(2)  # Wait for serial connection
    except Exception as e:
        ser = Serial()

    # Tracker setup with initial strategy
    tracker_context = TrackerContext(KCFTracker())

    # P controllers for x and y axes
    p_controller_x = PController(kp=0.1)
    p_controller_y = PController(kp=0.1)

    # FPS calculation variables
    start_time = time.time()
    frame_count = 0
    fps = 0

    # Camera FOV assumptions (adjust based on your camera)
    h_fov = 60  # Horizontal FOV in degrees
    v_fov = 45  # Vertical FOV in degrees
    pixels_per_deg_x = 1920 / h_fov
    pixels_per_deg_y = 1080 / v_fov

    cv2.namedWindow("Targeting System")
    cv2.setMouseCallback("Targeting System", select_roi)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        # Convert to grayscale for IRST aesthetic
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        if tracking and roi is not None:
            if not hasattr(tracker_context, "initialized"):
                tracker_context.init_tracker(frame, roi)
                tracker_context.initialized = True
            else:
                success, bbox = tracker_context.update_tracker(frame)
                if success:
                    # Draw bounding box
                    p1 = (int(bbox[0]), int(bbox[1]))
                    p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                    cv2.rectangle(frame, p1, p2, (0, 255, 0), 2)

                    # Calculate center of tracked object
                    center_x = bbox[0] + bbox[2] / 2
                    center_y = bbox[1] + bbox[3] / 2

                    # Calculate errors in pixels
                    error_x = center_x - 960  # Center of 1920x1080 is (960, 540)
                    error_y = center_y - 540

                    # Convert to degrees
                    x_error_deg = error_x / pixels_per_deg_x
                    y_error_deg = error_y / pixels_per_deg_y

                    # Compute servo adjustments
                    x_adj = p_controller_x.compute(x_error_deg)
                    y_adj = p_controller_y.compute(y_error_deg)

                    # Laser control (on if centered within 1 degree)
                    laser = 1 if abs(x_error_deg) < 1 and abs(y_error_deg) < 1 else 0

                    # Send to Arduino
                    message = f"{x_adj:.1f}:{y_adj:.1f}:{laser}"
                    ser.write(message.encode())

                else:
                    tracking = False
                    cv2.putText(
                        frame,
                        "Tracking Lost",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                    )

        # Draw military-grade overlays
        # Crosshair
        cv2.line(frame, (960, 0), (960, 1080), (0, 255, 0), 2)
        cv2.line(frame, (0, 540), (1920, 540), (0, 255, 0), 2)
        # Tick marks
        for i in range(0, 1920, 64):  # Every 2 degrees horizontally
            cv2.line(frame, (i, 538), (i, 542), (0, 255, 0), 1)
        for i in range(0, 1080, 48):  # Every 2 degrees vertically
            cv2.line(frame, (958, i), (962, i), (0, 255, 0), 1)

        # Text overlays
        cv2.putText(
            frame,
            f"Tracker: {tracker_context.tracker_name}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"FPS: {fps:.2f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        if tracking and success:
            cv2.putText(
                frame,
                f"X Error: {x_error_deg:.2f} deg",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Y Error: {y_error_deg:.2f} deg",
                (10, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Laser: {'ON' if laser else 'OFF'}",
                (10, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        # FPS calculation
        frame_count += 1
        elapsed = time.time() - start_time
        if elapsed > 1:
            fps = frame_count / elapsed
            frame_count = 0
            start_time = time.time()

        cv2.imshow("Targeting System", frame)

        # Handle key presses to switch trackers
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("1"):
            tracker_context = TrackerContext(KCFTracker())
            tracking = False
        elif key == ord("2"):
            tracker_context = TrackerContext(CSRTTracker())
            tracking = False
        elif key == ord("3"):
            tracker_context = TrackerContext(MOSSETracker())
            tracking = False
        elif key == ord("4"):
            tracker_context = TrackerContext(GOTURNTracker())
            tracking = False
        elif key == ord("5"):
            tracker_context = TrackerContext(MILTracker())
            tracking = False

    cap.release()
    ser.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
