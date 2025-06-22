# camera_manager.py (updated for vertical camera)
import cv2
import threading
import queue
import numpy as np
import imutils


class CameraManager:
    def __init__(self, camera_index=2, rotate_angle=90):
        self.cap = cv2.VideoCapture(camera_index)
        self.frame_width = 1280
        self.frame_height = 720

        print(
            "[INFO] Resolution in OpenCV:",
            self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
            "x",
            self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
        )

        self.rotate_angle = rotate_angle  # 90 for clockwise, -90 for counter-clockwise

        # Set to proper 1080p resolution (will be rotated)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Check if the camera frame has been resized correctly
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera with index {camera_index}")

        # Use threading for better performance
        self.frame_queue = queue.Queue(maxsize=2)
        self.current_frame = None
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.capture_thread.daemon = True
        self.running = True
        self.capture_thread.start()

    def _capture_frames(self):
        while self.running:
            ret, frame = self.cap.read()
            frame = imutils.resize(
                frame, width=self.frame_width, height=self.frame_height
            )
            if ret:
                # Rotate the frame
                if self.rotate_angle == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif self.rotate_angle == -90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif self.rotate_angle == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)

                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
                self.current_frame = frame

    def get_frame(self):
        if not self.frame_queue.empty():
            return self.frame_queue.get()
        return self.current_frame

    def get_current_frame(self):
        return self.current_frame

    def release(self):
        self.running = False
        self.capture_thread.join()
        self.cap.release()
