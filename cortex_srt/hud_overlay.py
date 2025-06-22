# hud_overlay.py (updated version with fire zone indicator)
import cv2
import numpy as np
from datetime import datetime
import time


class HUDOverlay:
    def __init__(self):
        self.color_primary = (0, 255, 0)  # Green
        self.color_secondary = (0, 200, 0)  # Darker green
        self.color_alert = (0, 0, 255)  # Red
        self.color_warning = (0, 255, 255)  # Yellow
        self.color_acquiring = (255, 255, 0)  # Cyan
        self.color_fire_zone = (0, 0, 255)  # Red for fire zone
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        # Animation states
        self.lock_animation_frame = 0
        self.acquisition_start_time = None
        self.fire_zone_animation = 0
        
        # Fire zone parameters
        self.fire_zone_radius = 30  # pixels from center

    def draw(self, frame, target_bbox, fps, algorithm, tracking_active, in_fire_zone=False):
        overlay = frame.copy()
        height, width = frame.shape[:2]

        # Draw crosshair with fire zone indicator
        self.draw_crosshair(overlay, width, height, in_fire_zone)

        # Draw compass/heading indicator
        self.draw_compass(overlay, width, height)

        # Draw info panel
        self.draw_info_panel(overlay, fps, algorithm, tracking_active, in_fire_zone)

        # Draw grid overlay
        self.draw_grid(overlay, width, height)

        # Draw target if tracking
        if target_bbox and tracking_active:
            self.draw_target(overlay, target_bbox, in_fire_zone)
        elif target_bbox and not tracking_active:
            # Draw lost target indicator
            self.draw_lost_target(overlay, target_bbox)

        # Add scan lines effect
        overlay = self.add_scan_lines(overlay)

        # Blend with original
        return cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)

    def draw_crosshair(self, frame, width, height, in_fire_zone):
        center_x, center_y = width // 2, height // 2
        
        # Animate fire zone
        self.fire_zone_animation += 0.2
        
        # Draw fire zone circle
        if in_fire_zone:
            # Pulsing effect
            pulse_radius = self.fire_zone_radius + int(5 * np.sin(self.fire_zone_animation))
            cv2.circle(frame, (center_x, center_y), pulse_radius, self.color_fire_zone, 2)
            
            # Inner circle
            cv2.circle(frame, (center_x, center_y), self.fire_zone_radius, self.color_fire_zone, 1)
            
            # Fire ready indicator
            cv2.putText(frame, "FIRE READY", (center_x - 40, center_y - 50), 
                       self.font, 0.6, self.color_fire_zone, 2)
        else:
            # Normal fire zone indicator (dimmed)
            cv2.circle(frame, (center_x, center_y), self.fire_zone_radius, self.color_secondary, 1)

        # Main crosshair - changes color when in fire zone
        crosshair_color = self.color_fire_zone if in_fire_zone else self.color_primary
        line_thickness = 3 if in_fire_zone else 2
        
        cv2.line(
            frame,
            (center_x - 40, center_y),
            (center_x - 20, center_y),
            crosshair_color,
            line_thickness,
        )
        cv2.line(
            frame,
            (center_x + 20, center_y),
            (center_x + 40, center_y),
            crosshair_color,
            line_thickness,
        )
        cv2.line(
            frame,
            (center_x, center_y - 40),
            (center_x, center_y - 20),
            crosshair_color,
            line_thickness,
        )
        cv2.line(
            frame,
            (center_x, center_y + 20),
            (center_x, center_y + 40),
            crosshair_color,
            line_thickness,
        )

        # Center dot - pulsing when in fire zone
        dot_size = 5 if in_fire_zone else 3
        cv2.circle(frame, (center_x, center_y), dot_size, crosshair_color, -1)

        # Ranging marks
        for i in range(1, 4):
            cv2.circle(frame, (center_x, center_y), i * 60, self.color_secondary, 1)

    def draw_info_panel(self, frame, fps, algorithm, tracking_active, in_fire_zone):
        height, width = frame.shape[:2]
        panel_x = 20
        panel_y = height - 180  # Increased height for fire status

        # Background
        cv2.rectangle(
            frame, (panel_x, panel_y), (panel_x + 250, height - 20), (0, 0, 0), -1
        )
        cv2.rectangle(
            frame,
            (panel_x, panel_y),
            (panel_x + 250, height - 20),
            self.color_primary,
            1,
        )

        # Info text
        info_lines = [
            f"FPS: {fps:.1f}",
            f"ALG: {algorithm}",
            f"STATUS: {'TRACKING' if tracking_active else 'STANDBY'}",
            f"FIRE: {'READY' if in_fire_zone and tracking_active else 'HOLD'}",
            f"TIME: {datetime.now().strftime('%H:%M:%S')}",
        ]

        for i, line in enumerate(info_lines):
            if i == 2 and tracking_active:
                color = self.color_alert
            elif i == 3 and in_fire_zone and tracking_active:
                color = self.color_fire_zone
            else:
                color = self.color_primary
                
            cv2.putText(
                frame,
                line,
                (panel_x + 10, panel_y + 25 + i * 25),
                self.font,
                0.5,
                color,
                1,
            )

    def draw_target(self, frame, bbox, in_fire_zone):
        x, y, w, h = [int(v) for v in bbox]

        # Animate lock acquisition
        if self.acquisition_start_time is None:
            self.acquisition_start_time = time.time()

        acquisition_time = time.time() - self.acquisition_start_time

        if acquisition_time < 0.5:  # Acquisition phase
            color = self.color_acquiring
            label = "ACQUIRING..."
            # Pulsing effect
            pulse = int(abs(np.sin(acquisition_time * 10)) * 255)
            color = (pulse, pulse, 0)
        else:  # Locked phase
            if in_fire_zone:
                color = self.color_fire_zone
                label = "TARGET IN FIRE ZONE"
            else:
                color = self.color_alert
                label = "TARGET LOCKED"

        # Target box with animated corners
        corner_length = 20
        self.lock_animation_frame += 1

        # More aggressive animation when in fire zone
        if in_fire_zone:
            offset = int(8 * np.sin(self.lock_animation_frame * 0.2))
        else:
            offset = int(5 * np.sin(self.lock_animation_frame * 0.1))

        # Draw corner brackets
        line_thickness = 3 if in_fire_zone else 2
        
        # Top-left corner
        cv2.line(frame, (x - offset, y), (x + corner_length, y), color, line_thickness)
        cv2.line(frame, (x, y - offset), (x, y + corner_length), color, line_thickness)

        # Top-right corner
        cv2.line(frame, (x + w - corner_length, y), (x + w + offset, y), color, line_thickness)
        cv2.line(frame, (x + w, y - offset), (x + w, y + corner_length), color, line_thickness)

        # Bottom-left corner
        cv2.line(frame, (x, y + h - corner_length), (x, y + h + offset), color, line_thickness)
        cv2.line(frame, (x - offset, y + h), (x + corner_length, y + h), color, line_thickness)

        # Bottom-right corner
        cv2.line(frame, (x + w - corner_length, y + h), (x + w + offset, y + h), color, line_thickness)
        cv2.line(frame, (x + w, y + h - corner_length), (x + w, y + h + offset), color, line_thickness)

        # Center indicator
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Draw line from target center to screen center when not in fire zone
        if not in_fire_zone:
            screen_center_x = frame.shape[1] // 2
            screen_center_y = frame.shape[0] // 2
            cv2.line(frame, (center_x, center_y), (screen_center_x, screen_center_y), 
                    self.color_secondary, 1, cv2.LINE_AA)

        cv2.drawMarker(frame, (center_x, center_y), color, cv2.MARKER_CROSS, 10, 1)

        # Target label
        cv2.putText(frame, label, (x, y - 10), self.font, 0.5, color, 1)

        # Distance indicator (simulated)
        distance = np.random.randint(100, 500)
        cv2.putText(
            frame,
            f"DIST: {distance}m",
            (center_x - 40, y + h + 20),
            self.font,
            0.4,
            color,
            1,
        )

        # Target ID
        cv2.putText(
            frame,
            f"TGT-{hash(str(bbox))%1000:03d}",
            (x + w - 50, y - 10),
            self.font,
            0.4,
            color,
            1,
        )
        
        # Fire solution indicator when in fire zone
        if in_fire_zone:
            cv2.putText(
                frame,
                "FIRE SOLUTION VALID",
                (x, y - 30),
                self.font,
                0.4,
                self.color_fire_zone,
                1,
            )

    def draw_lost_target(self, frame, bbox):
        """Draw indicator for lost target"""
        x, y, w, h = [int(v) for v in bbox]
        center_x = x + w // 2
        center_y = y + h // 2

        # Blinking effect
        if int(time.time() * 2) % 2:
            cv2.putText(
                frame,
                "TARGET LOST",
                (center_x - 50, center_y),
                self.font,
                0.6,
                self.color_warning,
                2,
            )
            cv2.rectangle(frame, (x, y), (x + w, y + h), self.color_warning, 1)

    def draw_compass(self, frame, width, height):
        # Top center compass
        compass_y = 50
        compass_width = 300
        start_x = (width - compass_width) // 2

        cv2.line(
            frame,
            (start_x, compass_y),
            (start_x + compass_width, compass_y),
            self.color_primary,
            1,
        )

        # Tick marks
        for i in range(0, compass_width + 1, 30):
            tick_height = 10 if i % 60 == 0 else 5
            cv2.line(
                frame,
                (start_x + i, compass_y),
                (start_x + i, compass_y - tick_height),
                self.color_primary,
                1,
            )

        # Center indicator
        cv2.putText(
            frame,
            "N",
            (width // 2 - 5, compass_y - 15),
            self.font,
            0.5,
            self.color_primary,
            1,
        )

    def draw_grid(self, frame, width, height):
        # Horizontal lines
        for y in range(0, height, height // 10):
            cv2.line(frame, (0, y), (width, y), self.color_secondary, 1, cv2.LINE_AA)

        # Vertical lines
        for x in range(0, width, width // 10):
            cv2.line(frame, (x, 0), (x, height), self.color_secondary, 1, cv2.LINE_AA)

    def add_scan_lines(self, frame):
        height, width = frame.shape[:2]

        # Create scan line effect
        for y in range(0, height, 3):
            frame[y : y + 1, :] = frame[y : y + 1, :] * 0.8

        return frame