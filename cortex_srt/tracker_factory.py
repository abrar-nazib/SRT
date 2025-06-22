# tracker_factory.py
import cv2


class TrackerFactory:
    def create_tracker(self, algorithm: str):
        """Factory method to create different trackers"""
        if algorithm == "CSRT":
            return cv2.TrackerCSRT_create()
        elif algorithm == "KCF":
            return cv2.TrackerKCF_create()
        elif algorithm == "MIL":
            return cv2.TrackerMIL_create()
        elif algorithm == "MOSSE":
            return cv2.TrackerMOSSE_create()
        elif algorithm == "MedianFlow":
            return cv2.TrackerMedianFlow_create()
        else:
            raise ValueError(f"Unknown tracking algorithm: {algorithm}")
