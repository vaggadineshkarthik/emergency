import cv2
import os
from ultralytics import YOLO

def test_inference():
    model_path = "best.pt"
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        return

    print(f"Loading model: {model_path}")
    model = YOLO(model_path)
    
    # Path to test images
    test_img_dir = os.path.join("Ambulance-Detection-1", "test", "images")
    if not os.path.exists(test_img_dir):
        print(f"Error: {test_img_dir} not found.")
        return
        
    test_images = [f for f in os.listdir(test_img_dir) if f.endswith(".jpg")]
    if not test_images:
        print("No test images found.")
        return
        
    # Test on the first 3 images
    for img_name in test_images[:3]:
        img_path = os.path.join(test_img_dir, img_name)
        print(f"\nProcessing {img_name}...")
        results = model(img_path)
        
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                name = r.names[cls]
                print(f" - Found: {name} (Confidence: {conf:.2f})")

if __name__ == "__main__":
    test_inference()
