from roboflow import Roboflow
import os

print("[*] Initializing Roboflow...")
rf = Roboflow(api_key="u7tAiOq8xQRURfZKtU6X")
print("[*] Connecting to project...")
project = rf.workspace("yolo-emergency-recognition").project("ambulance-detection-wdbvs")
print("[*] Downloading version 1 (YOLOv8 format)...")
version = project.version(1)
dataset = version.download("yolov8")

print(f"[+] Dataset downloaded to: {dataset.location}")
