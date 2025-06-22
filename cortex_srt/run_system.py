# run_system.py
#!/usr/bin/env python3
"""
Military-Grade Tracking System
Usage: python run_system.py [--port COM3] [--camera 0]
"""

import argparse
import sys
from main import TrackingSystem
import traceback


def main():
    parser = argparse.ArgumentParser(description="Military-Grade Tracking System")
    parser.add_argument("--port", default="COM3", help="Arduino serial port")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--no-arduino", action="store_true", help="Run without Arduino")

    args = parser.parse_args()

    print("===========================================")
    print("   MILITARY TRACKING SYSTEM v1.0")
    print("===========================================")
    print(f"Camera: {args.camera}")
    print(f"Arduino Port: {args.port if not args.no_arduino else 'DISABLED'}")
    print("\nControls:")
    print("  - Left Click: Start tracking at cursor position")
    print("  - T: Switch tracking algorithm")
    print("  - R: Reset tracking")
    print("  - Q: Quit")
    print("\nAvailable Tracking Algorithms:")
    print("  1. CSRT - Accurate but slower")
    print("  2. KCF - Fast, works well with translation")
    print("  3. MIL - Good for partial occlusions")
    print("  4. MOSSE - Very fast, lower accuracy")
    print("  5. MedianFlow - Good for predictable motion")
    print("===========================================\n")

    try:
        system = TrackingSystem()
        system.run()
    except KeyboardInterrupt:
        print("\nSystem shutdown requested")
    except Exception as e:
        print("An unexpected error occurred:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
