import cv2
import time
import numpy as np
from collections import deque
import pandas as pd


# --- Simplified CameraManager (for testing with video file or webcam) ---
class CameraManager:
    def __init__(self, source=0, rotate_angle=0):
        if isinstance(source, str):
            self.cap = cv2.VideoCapture(source)  # Use video file
        else:
            self.cap = cv2.VideoCapture(source)  # Use webcam index

        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

        self.rotate_angle = rotate_angle

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None

        if self.rotate_angle == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotate_angle == -90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.rotate_angle == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)

        return frame

    def release(self):
        self.cap.release()


# --- TrackerFactory (from original code) ---
class TrackerFactory:
    def create_tracker(self, algorithm: str):
        if algorithm == "CSRT":
            return cv2.TrackerCSRT_create()
        elif algorithm == "KCF":
            return cv2.TrackerKCF_create()
        elif algorithm == "MIL":
            return cv2.TrackerMIL_create()
        elif algorithm == "MOSSE":
            try:
                return cv2.legacy.TrackerMOSSE_create()
            except AttributeError:
                try:
                    return cv2.TrackerMOSSE_create()
                except AttributeError:
                    raise ValueError(
                        f"MOSSE tracker not available in this OpenCV version"
                    )
        else:
            raise ValueError(f"Unknown tracking algorithm: {algorithm}")


# --- TrackerAnalytics (from original code, with minor adjustments for direct use) ---
class TrackerAnalytics:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.fps_history = deque(maxlen=window_size)
        self.accuracy_history = deque(maxlen=window_size)
        self.tracking_time = {}
        self.algorithm_stats = {}
        self.all_frame_data = []  # To store data for CSV

    def update_fps(self, fps):
        self.fps_history.append(fps)

    def update_accuracy(self, ground_truth_bbox, predicted_bbox):
        if ground_truth_bbox is None or predicted_bbox is None:
            return

        iou = self.calculate_iou(ground_truth_bbox, predicted_bbox)
        self.accuracy_history.append(iou)

    def calculate_iou(self, bbox1, bbox2):
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0

        intersection_area = (xi2 - xi1) * (yi2 - yi1)

        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - intersection_area

        return intersection_area / union_area

    def start_tracking(self, algorithm):
        self.tracking_time[algorithm] = time.time()

    def end_tracking(self, algorithm):
        if algorithm in self.tracking_time:
            duration = time.time() - self.tracking_time[algorithm]
            if algorithm not in self.algorithm_stats:
                self.algorithm_stats[algorithm] = {
                    "total_time": 0,
                    "count": 0,
                    "avg_fps": 0,
                    "avg_accuracy": 0,
                }

            stats = self.algorithm_stats[algorithm]
            stats["total_time"] += duration
            stats["count"] += 1
            stats["avg_fps"] = np.mean(self.fps_history) if self.fps_history else 0
            stats["avg_accuracy"] = (
                np.mean(self.accuracy_history) if self.accuracy_history else 0
            )

    def record_frame_data(
        self, frame_num, algorithm, fps, ground_truth_bbox, predicted_bbox, success
    ):
        iou = (
            self.calculate_iou(ground_truth_bbox, predicted_bbox)
            if ground_truth_bbox and predicted_bbox
            else 0.0
        )
        self.all_frame_data.append(
            {
                "frame": frame_num,
                "algorithm": algorithm,
                "fps": fps,
                "ground_truth_x": ground_truth_bbox[0] if ground_truth_bbox else -1,
                "ground_truth_y": ground_truth_bbox[1] if ground_truth_bbox else -1,
                "ground_truth_w": ground_truth_bbox[2] if ground_truth_bbox else -1,
                "ground_truth_h": ground_truth_bbox[3] if ground_truth_bbox else -1,
                "predicted_x": predicted_bbox[0] if predicted_bbox else -1,
                "predicted_y": predicted_bbox[1] if predicted_bbox else -1,
                "predicted_w": predicted_bbox[2] if predicted_bbox else -1,
                "predicted_h": predicted_bbox[3] if predicted_bbox else -1,
                "iou": iou,
                "success": success,
            }
        )

    def save_to_csv(self, filename="tracker_performance_data.csv"):
        df = pd.DataFrame(self.all_frame_data)
        df.to_csv(filename, index=False)
        print(f"Performance data saved to {filename}")

    def get_report(self):
        report = "=== Tracking Algorithm Performance Report ===\n"
        for algorithm, stats in self.algorithm_stats.items():
            report += f"\nAlgorithm: {algorithm}\n"
            report += f"  Average FPS: {stats['avg_fps']:.2f}\n"
            report += f"  Average Accuracy (IoU): {stats['avg_accuracy']:.2%}\n"
            report += f"  Total Tracking Time: {stats['total_time']:.2f}s\n"
            report += f"  Number of Sessions: {stats['count']}\n"

        return report


# --- Main Benchmarking Logic ---
class TrackerBenchmark:
    def __init__(
        self,
        video_source=0,
        rotate_angle=0,
        haar_cascade_path="haarcascade_frontalface_default.xml",
    ):
        self.camera = CameraManager(source=video_source, rotate_angle=rotate_angle)
        self.tracker_factory = TrackerFactory()
        self.analytics = TrackerAnalytics()
        self.algorithms = ["CSRT", "KCF", "MIL", "MOSSE"]
        self.current_algorithm_idx = 0
        self.current_tracker = None
        self.target_bbox = None  # Predicted bbox from the tracker
        self.ground_truth_bbox = None  # Bbox from Haar Cascade
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0

        # Haar Cascade Face Detector
        self.face_detector = cv2.CascadeClassifier(haar_cascade_path)
        if self.face_detector.empty():
            raise IOError(
                f"Could not load Haar Cascade classifier from {haar_cascade_path}"
            )

    def detect_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) > 0:
            # Return the largest face found
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            return tuple(largest_face)
        return None

    def start_tracking(self):
        if self.current_tracker:
            self.analytics.end_tracking(self.algorithms[self.current_algorithm_idx])

        algorithm = self.algorithms[self.current_algorithm_idx]
        self.current_tracker = self.tracker_factory.create_tracker(algorithm)
        frame = self.camera.get_frame()
        if frame is not None and self.ground_truth_bbox is not None:
            try:
                self.current_tracker.init(frame, self.ground_truth_bbox)
                self.analytics.start_tracking(algorithm)
                print(f"Started tracking with {algorithm}")
            except Exception as e:
                print(f"Error initializing {algorithm} tracker: {e}")
                self.current_tracker = None
                self.target_bbox = None
                self.ground_truth_bbox = None

    def stop_tracking(self):
        if self.current_tracker:
            self.analytics.end_tracking(self.algorithms[self.current_algorithm_idx])
            self.current_tracker = None
            self.target_bbox = None
            self.ground_truth_bbox = None
            print("Tracking stopped.")

    def switch_algorithm(self):
        self.stop_tracking()
        self.current_algorithm_idx = (self.current_algorithm_idx + 1) % len(
            self.algorithms
        )
        print(f"Switched to algorithm: {self.algorithms[self.current_algorithm_idx]}")

    def calculate_fps(self):
        self.frame_count += 1
        if self.frame_count % 30 == 0:
            current_time = time.time()
            self.fps = 30 / (current_time - self.last_time)
            self.last_time = current_time
            self.analytics.update_fps(self.fps)

    def run(self):
        cv2.namedWindow("Tracker Benchmark", cv2.WINDOW_NORMAL)

        print("\n--- Tracker Benchmarking Tool (Automated Ground Truth) ---")
        print("Instructions:")
        print("  - Face detection will automatically provide ground truth.")
        print("  - Press 'T' to switch to the next tracking algorithm.")
        print("  - Press 'R' to reset/stop current tracking.")
        print("  - Press 'Q' to quit and see the report.")
        print("----------------------------------------------------------")

        while True:
            frame = self.camera.get_frame()
            if frame is None:
                print("End of video or camera disconnected.")
                break

            self.calculate_fps()

            display_frame = frame.copy()

            # Detect face for ground truth
            self.ground_truth_bbox = self.detect_face(frame)

            if self.ground_truth_bbox:
                # Draw ground truth bbox
                x, y, w, h = [int(v) for v in self.ground_truth_bbox]
                cv2.rectangle(
                    display_frame, (x, y), (x + w, y + h), (0, 255, 255), 2
                )  # Yellow for ground truth
                cv2.putText(
                    display_frame,
                    "GT",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

                # If no tracker is active, or tracking was lost, start new tracking with detected face
                if not self.current_tracker or not self.target_bbox:
                    self.start_tracking()

            success = False
            if self.current_tracker and self.target_bbox:
                success, bbox = self.current_tracker.update(frame)
                if success:
                    self.target_bbox = bbox
                    if self.ground_truth_bbox:
                        self.analytics.update_accuracy(self.ground_truth_bbox, bbox)
                    p1 = (int(bbox[0]), int(bbox[1]))
                    p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                    cv2.rectangle(
                        display_frame, p1, p2, (255, 0, 0), 2
                    )  # Blue for tracked bbox
                    cv2.putText(
                        display_frame,
                        self.algorithms[self.current_algorithm_idx],
                        (p1[0], p1[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 0, 0),
                        2,
                    )
                else:
                    cv2.putText(
                        display_frame,
                        "Tracking Lost!",
                        (50, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        3,
                    )
                    self.stop_tracking()

            # Record data for the current frame
            self.analytics.record_frame_data(
                self.frame_count,
                self.algorithms[self.current_algorithm_idx],
                self.fps,
                self.ground_truth_bbox,
                self.target_bbox,
                success,
            )

            cv2.putText(
                display_frame,
                f"FPS: {self.fps:.2f}",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.imshow("Tracker Benchmark", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("t"):
                self.switch_algorithm()
            elif key == ord("r"):
                self.stop_tracking()

        self.stop_tracking()  # Ensure tracking is ended before report
        self.camera.release()
        cv2.destroyAllWindows()
        self.analytics.save_to_csv()
        print(self.analytics.get_report())


if __name__ == "__main__":
    # To use a video file, replace 0 with the path to your video file, e.g., 'video.mp4'
    # Make sure 'haarcascade_frontalface_default.xml' is in the same directory as this script
    benchmark = TrackerBenchmark(video_source=0, rotate_angle=0)  # Use webcam (index 0)
    benchmark.run()
