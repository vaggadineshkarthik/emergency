import asyncio
import json
import os
import cv2 # OpenCV for RTSP/HTTP Stream
import numpy as np
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

# Global for MJPEG streaming
lane_frames = {
    1: None, # North
    2: None, # East
    3: None, # South
    4: None  # West
}
frame_lock = asyncio.Lock()
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Local YOLO Inference
try:
    from ultralytics import YOLO
    HAS_YOLO = True
    # Load custom trained model if it exists, otherwise fallback to yolov8n.pt
    if os.path.exists("best.pt"):
        print("[+] Loading custom trained ambulance model 'best.pt'...")
        model = YOLO("best.pt")
    else:
        print("[!] Custom 'best.pt' not found. Using pre-trained yolov8n.pt...")
        model = YOLO("yolov8n.pt") 
except ImportError:
    print("[!] ultralytics not found. Running in simulation mode.")
    HAS_YOLO = False
    model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start detection task only for North Road as per user request
    asyncio.create_task(process_lane_camera(1, "North", f"http://10.2.0.215:4747/video"))
    # East, South, West are currently turned off
    yield

app = FastAPI(title="Emergency-Priority Traffic Monitoring System", lifespan=lifespan)

# Add CORS middleware to prevent potential browser blocking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directory exists
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

async def get_frame_generator(lane_id: int):
    while True:
        frame = lane_frames.get(lane_id)
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            # Show a "No Signal" placeholder if camera is not connected
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, f"LANE {lane_id} NO SIGNAL", (150, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', placeholder)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        await asyncio.sleep(0.04)

@app.get("/video_feed/{lane_id}")
async def video_feed(lane_id: int):
    return StreamingResponse(get_frame_generator(lane_id), media_type="multipart/x-mixed-replace; boundary=frame")

# --- WebSocket Manager for Real-Time UI Updates ---
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just keep connection open, client doesn't send much
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# --- Configuration ---
# Droidcam IPs provided by user
IP_1 = "10.33.143.235"
IP_2 = "10.2.0.215"
PORT = "4747"

# To test with a local file, change this to your video file path (e.g., "test.mp4")
TEST_VIDEO_PATH = None 

# SIMULATION MODE: If True, uses random images from test folder when camera fails
SIMULATION_MODE = True

# --- Background Task for Individual Lane Monitoring ---
async def process_lane_camera(lane_id: int, direction: str, url: str = None):
    """
    Reads from a specific camera URL for a specific lane.
    """
    await asyncio.sleep(1.0) # Wait for server ready
    
    # Fallback to test video if camera fails and a path is provided
    if TEST_VIDEO_PATH and not os.path.exists(url) and not url.startswith("http"):
        url = TEST_VIDEO_PATH

    if url is None:
        print(f"[!] Lane {lane_id} ({direction}): No camera URL provided.")
        return

    cap = None
    
    # Simulation variables
    test_img_dir = os.path.join("Ambulance-Detection-1", "test", "images")
    test_images = []
    if SIMULATION_MODE and os.path.exists(test_img_dir):
        test_images = [os.path.join(test_img_dir, f) for f in os.listdir(test_img_dir) if f.endswith(".jpg")]
    
    while True:
        await asyncio.sleep(0.01) # Yield
        
        # Connection handling
        if not SIMULATION_MODE and (cap is None or not cap.isOpened()):
            print(f"[*] Lane {lane_id} ({direction}) attempting connection to {url} ...")
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"[+] Lane {lane_id} ({direction}) connected.")
                else:
                    print(f"[-] Lane {lane_id} ({direction}) connected but failed to read. Retrying...")
                    cap.release()
                    cap = None
                    await asyncio.sleep(5)
                    continue
            else:
                cap.release()
                cap = None
                print(f"[!] Lane {lane_id} ({direction}) connection failed. Retrying in 5s...")
                await asyncio.sleep(5)
                continue

        # Frame retrieval
        if SIMULATION_MODE and test_images:
            import random
            img_path = random.choice(test_images)
            frame = cv2.imread(img_path)
            if frame is None:
                await asyncio.sleep(1)
                continue
            # Simulate a 1-second delay per image
            await asyncio.sleep(1.0)
        else:
            ret, frame = cap.read()
            if not ret:
                print(f"[-] Lane {lane_id} ({direction}) connection lost. Reconnecting...")
                cap.release()
                cap = None
                await asyncio.sleep(2)
                continue
            
        if HAS_YOLO and model:
            try:
                # Run YOLOv8 inference on the whole frame
                results = model(frame, verbose=False, stream=True)
                
                # Debugging counter
                obj_count = 0
                
                for r in results:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        # Robust class name check
                        cls_name = r.names[cls].lower().strip()
                        # 'storbow' is the class name in your custom dataset for ambulance/emergency
                        is_emergency = "ambulance" in cls_name or "storbow" in cls_name
                        
                        # Debug: Log EVERY detection in the terminal
                        if conf > 0.15: # Log everything above 15% confidence
                            # Send to broadcast for UI display
                            await manager.broadcast({
                                "type": "debug",
                                "lane": lane_id,
                                "message": f"Found {cls_name} ({conf:.2f})"
                            })
                            print(f"[YOLO DEBUG] Lane {lane_id}: Found {cls_name} with {conf:.2f} confidence")
                        
                        # Detect ambulances (class 0 in custom) OR standard vehicles (2,5,7 in COCO)
                        # High threshold as requested: 0.75+ for alerts
                        threshold = 0.75 if is_emergency else 0.45
                        
                        if (is_emergency or cls in [2, 5, 7]) and conf > threshold:
                            obj_count += 1
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            color = (0, 255, 0) # Default green for standard vehicles
                            
                            if is_emergency:
                                color = (0, 0, 255) # Red for ambulance
                                print(f"[!!! ALERT !!!] Lane {lane_id}: EMERGENCY DETECTED: {cls_name} ({conf:.2f})")
                            
                            # Draw bounding box and label
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(frame, f"{cls_name.capitalize()} {conf:.2f}", (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            
                            if is_emergency:
                                await trigger_emergency(lane_id, f"Ambulance Detected in {direction}")
                                break # Trigger once per frame max
                
                if obj_count > 0:
                    print(f"[DEBUG Lane {lane_id}] Frame processed, objects drawn: {obj_count}")
                            
            except Exception as e:
                print(f"[YOLO Error Lane {lane_id}] - {str(e)[:50]}")
        
        # Update global frame for this specific lane
        lane_frames[lane_id] = frame.copy()


async def trigger_emergency(lane: int, detection_method: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[!] EMERGENCY ALERT: Lane {lane} | {detection_method} at {timestamp}")
    await manager.broadcast({
        "type": "alert",
        "lane": lane,
        "timestamp": timestamp,
        "message": f"Emergency Priority: {detection_method}"
    })

# Lifespan managed instead of on_event

if __name__ == "__main__":
    import uvicorn
    # Make sure we're in the right directory to find 'static/'
    print("\n--- Emergency-Priority Traffic Monitoring System ---")
    print("Dashboard available at: http://localhost:8001")
    print("----------------------------------------------------\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)
