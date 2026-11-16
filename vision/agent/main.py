import sys
import os
import cv2
import asyncio

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vision.camera.opencv_camera import OpenCVCamera
from vision.agent.local_bridge import LocalVisionBridge
from vision.communication.ws_client import VisionWebSocketClient
from vision.events.event_emitter import VisionEventEmitter


async def run_vision_agent():
    print("=" * 60)
    print("Starting EyeSpeak AI - Vision & Blink Engine")
    print("Press 'q' in video window to exit.")
    print("Press 'c' to clear text, 'b' for backspace.")
    print("=" * 60)

    # 1. Initialize Camera
    cam = OpenCVCamera(camera_index=0, width=640, height=480)
    if not cam.start():
        print("[Error] Failed to initialize webcam. Please verify camera connection.")
        return

    # 2. Initialize Bridge & Resilient WebSocket Client
    bridge = LocalVisionBridge()
    ws_client = VisionWebSocketClient(ws_url="ws://127.0.0.1:8000/api/v1/ws/stream")
    await ws_client.start()

    frame_count = 0
    try:
        while True:
            ret, frame = cam.read_frame()
            if not ret or frame is None:
                await asyncio.sleep(0.01)
                continue

            frame_count += 1
            telemetry = bridge.process_frame(frame)
            annotated_frame = telemetry.pop("processed_frame")

            # Stream telemetry to FastAPI WebSocket every 2 frames to optimize network
            if frame_count % 2 == 0:
                ws_client.send_event_sync(telemetry)

            # Display real-time video window
            cv2.imshow("EyeSpeak AI - Camera HUD", annotated_frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('c'):
                bridge.morse_decoder.clear()
            elif key == ord('b'):
                bridge.morse_decoder.backspace()
            elif key == ord(' '):
                bridge.morse_decoder.commit_space()

            await asyncio.sleep(0.001)

    finally:
        cam.stop()
        cv2.destroyAllWindows()
        await ws_client.stop()
        print("[EyeSpeak AI] Vision Agent terminated gracefully.")


def main():
    try:
        asyncio.run(run_vision_agent())
    except KeyboardInterrupt:
        print("\n[EyeSpeak AI] Stopped by user.")


if __name__ == "__main__":
    main()
