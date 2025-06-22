# camera_manager.py
import cv2
import threading
import queue


class CameraManager:
    def __init__(self, camera_index=2):
        self.cap = cv2.VideoCapture(camera_index)

        # Set to proper 1080p resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

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
            if ret:
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
