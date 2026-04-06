# Ambulance Detection Dataset Instructions

To utilize a pre-trained YOLOv8/YOLOv11 model or run the Roboflow workflow accurately, you will need a robust dataset containing labeled ambulances.

## Option 1: Roboflow Universe (Recommended)

Roboflow Universe has thousands of open-source datasets related to emergency vehicles, traffic, and ambulances.

1. Create a free account at [Roboflow Universe](https://universe.roboflow.com/).
2. Search for "Ambulance Detection" or "Emergency Vehicles".
3. Export the dataset:
   - Click "Download Dataset".
   - Select YOLOv8 format.
   - You can either download the ZIP physically or use the provided Python snippet.

**Snippet to download programmatically:**
```python
# pip install roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")
project = rf.workspace("workspace-name").project("project-name")
version = project.version(1)
dataset = version.download("yolov8")
```

## Option 2: Kaggle Datasets

You can also search Kaggle for emergency vehicle datasets. 
Search terms: `emergency vehicle classification`, `indian traffic dataset`, or `ambulance detection yolo`.

**To download from Kaggle using CLI:**
1. Setup your `kaggle.json` API token.
2. Run:
```bash
pip install kaggle
kaggle datasets download -d <author>/<dataset-name>
unzip <dataset-name>.zip -d ./dataset
```

## Connecting to the Monitoring System

If using the YOLO model natively without the `InferenceHTTPClient`, you will need to train it on the downloaded dataset:
```python
from ultralytics import YOLO

# Load a pre-trained model
model = YOLO('yolov8n.yaml')  # build a new model from YAML

# Train the model
results = model.train(data='path/to/dataset/data.yaml', epochs=100, imgsz=640)
```
After training, integrate the `.pt` weights into your custom OpenCV loop instead of the HTTP client!
