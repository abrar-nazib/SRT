# run_system.py (updated with rotation option)
#!/usr/bin/env python3
"""
Military-Grade Tracking System
Usage: python run_system.py [--port COM3] [--camera 0] [--rotate 90]
"""

import argparse
import sys
from main import TrackingSystem


def main():
    parser = argparse.ArgumentParser(description="Military-Grade Tracking System")
    parser.add_argument("--port", default="COM8", help="Arduino serial port")
    parser.add_argument("--camera", type=int, default=1, help="Camera index")
    parser.add_argument(
        "--rotate",
        type=int,
        default=90,
        choices=[-90, 0, 90, 180],
        help="Camera rotation angle (default: 90 for vertical)",
    )
    parser.add_argument("--no-arduino", action="store_true", help="Run without Arduino")

    args = parser.parse_args()

    print("===========================================")
    print("   MILITARY TRACKING SYSTEM v1.0")
    print("   VERTICAL CAMERA MODE")
    print("===========================================")
    print(f"Camera: {args.camera}")
    print(f"Rotation: {args.rotate}°")
    print(f"Arduino Port: {args.port if not args.no_arduino else 'DISABLED'}")
    print("\nControls:")
    print("  - Left Click: Start tracking at cursor position")
    print("  - Drag: Select target area")
    print("  - T: Switch tracking algorithm")
    print("  - R: Reset tracking")
    print("  - F: Manual fire (when in fire zone)")
    print("  - Space: Stop tracking")
    print("  - Q: Quit")
    print("\nFire Zone:")
    print("  - Target must be within 30 pixels of center")
    print("  - Hold for 0.5 seconds to activate laser")
    print("\nAvailable Tracking Algorithms:")
    print("  1. CSRT - Accurate but slower")
    print("  2. KCF - Fast, works well with translation")
    print("  3. MIL - Good for partial occlusions")
    print("  4. MOSSE - Very fast, lower accuracy")
    print("  5. MedianFlow - Good for predictable motion")
    print("===========================================\n")

    try:
        system = TrackingSystem(camera_index=args.camera, camera_rotate=args.rotate, arduino_port=args.port)
        system.run()
    except KeyboardInterrupt:
        print("\nSystem shutdown requested")
    except Exception as e:
        print(f"Error: {e}")
        # Print the stack trace for debugging
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
