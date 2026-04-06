from ultralytics import YOLO
import os

def train_model():
    # Load a pretrained YOLOv8n model
    model = YOLO('yolov8n.pt')

    # Path to data.yaml
    data_yaml = os.path.join(os.getcwd(), 'Ambulance-Detection-1', 'data.yaml')
    
    print(f"[*] Starting training with dataset: {data_yaml}")
    
    # Train the model
    # Using small number of epochs and image size for a quick demonstration training
    # In a real scenario, you'd use epochs=50 or 100
    results = model.train(
        data=data_yaml,
        epochs=10, 
        imgsz=640,
        batch=8,
        name='ambulance_model'
    )
    
    print("[+] Training complete!")
    
    # The best model will be in runs/detect/ambulance_model/weights/best.pt
    # We'll copy it to the root directory for easier access
    import shutil
    best_model_path = os.path.join('runs', 'detect', 'ambulance_model', 'weights', 'best.pt')
    if os.path.exists(best_model_path):
        shutil.copy(best_model_path, 'best.pt')
        print("[+] Custom model 'best.pt' created in root directory.")
    else:
        print("[!] Could not find best.pt. Check 'runs' folder.")

if __name__ == "__main__":
    train_model()
