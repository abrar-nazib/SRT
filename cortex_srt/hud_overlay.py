# hud_overlay.py (updated for vertical display)
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

    def draw(
        self, frame, target_bbox, fps, algorithm, tracking_active, in_fire_zone=False
    ):
        overlay = frame.copy()
        height, width = frame.shape[:2]

        # Draw crosshair with fire zone indicator
        self.draw_crosshair(overlay, width, height, in_fire_zone)

        # Draw compass/heading indicator (adjusted for vertical)
        self.draw_compass(overlay, width, height)

        # Draw info panels on sides for vertical display
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
            pulse_radius = self.fire_zone_radius + int(
                5 * np.sin(self.fire_zone_animation)
            )
            cv2.circle(
                frame, (center_x, center_y), pulse_radius, self.color_fire_zone, 2
            )

            # Inner circle
            cv2.circle(
                frame,
                (center_x, center_y),
                self.fire_zone_radius,
                self.color_fire_zone,
                1,
            )

            # Fire ready indicator - moved to side for vertical display
            cv2.putText(
                frame,
                "FIRE",
                (center_x + 60, center_y - 10),
                self.font,
                0.6,
                self.color_fire_zone,
                2,
            )
            cv2.putText(
                frame,
                "READY",
                (center_x + 60, center_y + 10),
                self.font,
                0.6,
                self.color_fire_zone,
                2,
            )
        else:
            # Normal fire zone indicator (dimmed)
            cv2.circle(
                frame,
                (center_x, center_y),
                self.fire_zone_radius,
                self.color_secondary,
                1,
            )

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

        # Ranging marks - adjusted for vertical display
        for i in range(1, 3):
            cv2.circle(frame, (center_x, center_y), i * 50, self.color_secondary, 1)

    def draw_compass(self, frame, width, height):
        # Side compass for vertical display
        compass_x = width - 40
        compass_height = 300
        start_y = (height - compass_height) // 2

        cv2.line(
            frame,
            (compass_x, start_y),
            (compass_x, start_y + compass_height),
            self.color_primary,
            1,
        )

        # Tick marks
        for i in range(0, compass_height + 1, 30):
            tick_width = 10 if i % 60 == 0 else 5
            cv2.line(
                frame,
                (compass_x, start_y + i),
                (compass_x + tick_width, start_y + i),
                self.color_primary,
                1,
            )

        # Direction indicators
        cv2.putText(
            frame,
            "N",
            (compass_x + 15, start_y + 10),
            self.font,
            0.4,
            self.color_primary,
            1,
        )
        cv2.putText(
            frame,
            "S",
            (compass_x + 15, start_y + compass_height - 5),
            self.font,
            0.4,
            self.color_primary,
            1,
        )

    def draw_info_panel(self, frame, fps, algorithm, tracking_active, in_fire_zone):
        height, width = frame.shape[:2]

        # Top info panel for vertical display
        panel_y = 20
        panel_height = 120
        panel_width = width - 40

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (20, panel_y),
            (20 + panel_width, panel_y + panel_height),
            (0, 0, 0),
            -1,
        )
        frame[:] = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Border
        cv2.rectangle(
            frame,
            (20, panel_y),
            (20 + panel_width, panel_y + panel_height),
            self.color_primary,
            1,
        )

        # Info arranged horizontally for vertical display
        info_items = [
            ("FPS", f"{fps:.1f}"),
            ("ALG", algorithm),
            ("STATUS", "TRACKING" if tracking_active else "STANDBY"),
            ("FIRE", "READY" if in_fire_zone and tracking_active else "HOLD"),
        ]

        x_offset = 30
        for label, value in info_items:
            # Label
            cv2.putText(
                frame,
                label,
                (x_offset, panel_y + 30),
                self.font,
                0.4,
                self.color_secondary,
                1,
            )
            # Value
            color = self.color_primary
            if label == "STATUS" and tracking_active:
                color = self.color_alert
            elif label == "FIRE" and in_fire_zone and tracking_active:
                color = self.color_fire_zone

            cv2.putText(
                frame,
                value,
                (x_offset, panel_y + 55),
                self.font,
                0.5,
                color,
                1,
            )
            x_offset += (panel_width - 40) // 4

        # Time at bottom
        cv2.putText(
            frame,
            datetime.now().strftime("%H:%M:%S"),
            (width // 2 - 40, panel_y + 90),
            self.font,
            0.6,
            self.color_primary,
            1,
        )

    def draw_grid(self, frame, width, height):
        # Lighter grid for vertical display
        # Horizontal lines
        for y in range(0, height, height // 8):
            cv2.line(frame, (0, y), (width, y), self.color_secondary, 1, cv2.LINE_AA)

        # Vertical lines
        for x in range(0, width, width // 6):
            cv2.line(frame, (x, 0), (x, height), self.color_secondary, 1, cv2.LINE_AA)

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
                label = "IN ZONE"
            else:
                color = self.color_alert
                label = "LOCKED"

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
        cv2.line(
            frame,
            (x + w - corner_length, y),
            (x + w + offset, y),
            color,
            line_thickness,
        )
        cv2.line(
            frame,
            (x + w, y - offset),
            (x + w, y + corner_length),
            color,
            line_thickness,
        )

        # Bottom-left corner
        cv2.line(
            frame,
            (x, y + h - corner_length),
            (x, y + h + offset),
            color,
            line_thickness,
        )
        cv2.line(
            frame,
            (x - offset, y + h),
            (x + corner_length, y + h),
            color,
            line_thickness,
        )

        # Bottom-right corner
        cv2.line(
            frame,
            (x + w - corner_length, y + h),
            (x + w + offset, y + h),
            color,
            line_thickness,
        )
        cv2.line(
            frame,
            (x + w, y + h - corner_length),
            (x + w, y + h + offset),
            color,
            line_thickness,
        )

        # Center indicator
        center_x = x + w // 2
        center_y = y + h // 2

        # Draw line from target center to screen center when not in fire zone
        if not in_fire_zone:
            screen_center_x = frame.shape[1] // 2
            screen_center_y = frame.shape[0] // 2
            cv2.line(
                frame,
                (center_x, center_y),
                (screen_center_x, screen_center_y),
                self.color_secondary,
                1,
                cv2.LINE_AA,
            )
        cv2.drawMarker(frame, (center_x, center_y), color, cv2.MARKER_CROSS, 10, 1)

        # Target label - positioned better for vertical display
        cv2.putText(frame, label, (x, y - 10), self.font, 0.5, color, 1)

        # Distance indicator (simulated)
        distance = np.random.randint(100, 500)
        cv2.putText(
            frame,
            f"D:{distance}m",
            (x + w + 5, y + h // 2),
            self.font,
            0.4,
            color,
            1,
        )

        # Target ID
        cv2.putText(
            frame,
            f"TGT-{hash(str(bbox))%1000:03d}",
            (x, y + h + 20),
            self.font,
            0.4,
            color,
            1,
        )

        # Fire solution indicator when in fire zone
        if in_fire_zone:
            cv2.putText(
                frame,
                "FIRE SOLUTION",
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
                "LOST",
                (center_x - 20, center_y),
                self.font,
                0.6,
                self.color_warning,
                2,
            )
            cv2.rectangle(frame, (x, y), (x + w, y + h), self.color_warning, 1)

    def add_scan_lines(self, frame):
        height, width = frame.shape[:2]

        # Create scan line effect - horizontal for vertical display
        for y in range(0, height, 4):
            frame[y : y + 1, :] = frame[y : y + 1, :] * 0.85

        return frame
