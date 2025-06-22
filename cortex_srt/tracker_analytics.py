# tracker_analytics.py
import time
import numpy as np
from collections import deque

class TrackerAnalytics:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.fps_history = deque(maxlen=window_size)
        self.accuracy_history = deque(maxlen=window_size)
        self.tracking_time = {}
        self.algorithm_stats = {}
        
    def update_fps(self, fps):
        self.fps_history.append(fps)
        
    def update_accuracy(self, ground_truth_bbox, predicted_bbox):
        """Calculate IoU (Intersection over Union) for accuracy"""
        if ground_truth_bbox is None or predicted_bbox is None:
            return
            
        iou = self.calculate_iou(ground_truth_bbox, predicted_bbox)
        self.accuracy_history.append(iou)
        
    def calculate_iou(self, bbox1, bbox2):
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
            
        intersection_area = (xi2 - xi1) * (yi2 - yi1)
        
        # Calculate union
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
                    'total_time': 0,
                    'count': 0,
                    'avg_fps': 0,
                    'avg_accuracy': 0
                }
            
            stats = self.algorithm_stats[algorithm]
            stats['total_time'] += duration
            stats['count'] += 1
            stats['avg_fps'] = np.mean(self.fps_history) if self.fps_history else 0
            stats['avg_accuracy'] = np.mean(self.accuracy_history) if self.accuracy_history else 0
            
    def get_report(self):
        report = "=== Tracking Algorithm Performance Report ===\n"
        for algorithm, stats in self.algorithm_stats.items():
            report += f"\nAlgorithm: {algorithm}\n"
            report += f"  Average FPS: {stats['avg_fps']:.2f}\n"
            report += f"  Average Accuracy (IoU): {stats['avg_accuracy']:.2%}\n"
            report += f"  Total Tracking Time: {stats['total_time']:.2f}s\n"
            report += f"  Number of Sessions: {stats['count']}\n"
            
        return report