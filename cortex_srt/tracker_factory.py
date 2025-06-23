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
            # Try legacy MOSSE first, then fall back to regular
            try:
                return cv2.legacy.TrackerMOSSE_create()
            except AttributeError:
                try:
                    return cv2.TrackerMOSSE_create()
                except AttributeError:
                    raise ValueError(f"MOSSE tracker not available in this OpenCV version")
        else:
            raise ValueError(f"Unknown tracking algorithm: {algorithm}")
