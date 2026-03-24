<!-- ABOUT THE PROJECT -->
# Implementation

If you're at this phase, it's assumed that you've completed the fine-tuning and your new LLM model is available.

Before proceeding further, let's first test the fine-tuned model.

Here's a simple notebook to test inference (using the LoRA adapter uploaded to Hugging Face) [Notebook](./simple-inf.ipynb)

After the LLM has finished fine-tuning, there are still several tasks to complete before implementing it on the actual robot.

- [x] Fine-tune gemma-2B for LLM
- [x] Implement robot perception with webcam and opencv (object detection based on color) and calibrate camera coordinates to robot coordinates
- [x] Create a web interface for the robot
- [x] Create LLM Inference API
- [x] Connect everything together

Note: The LLM inference code and robot operation run on two separate computers. Simply put, the Low Performance Computer (LPC) will be connected to the robot and camera and also host a simple web page as a control interface for entering text. Meanwhile, the High Performance Computer (HPC) will be used for LLM inference and hosting the Inference API so that the LPC can make HTTP inference requests to the HPC. In the actual implementation, only two code files are executed (inference.ipynb and app.py). If you want to run it on a single computer (1 HPC), you can directly run both code files on one computer.

![System Diagram](./images/hpc-lpc.jpg)


For the following explanations, assume I'm only discussing the app.py code except when discussing the creation of the inference endpoint.

## Implementing Robot Perception with Webcam and OpenCV (Color-Based Object Detection)

![Object Detection](./images/opencv.jpg)

All this code will later be in app.py in the detect_blocks() function:

In this code, it only detects exactly one blue, orange, and yellow block.

For object detection, a webcam is used and processed with OpenCV for classification based on color. If you want to use a different method, you can do so. For the camera, I'm using an IPCamera with droidcam. If you want to use a different camera, don't forget to change the source.

```
# Function to detect blocks
# Input = Image frame
# Output = frame of detected object (camera with bounding box) and update detected_object global coordinate

def detect_blocks(frame, min_size=100, max_size=5000):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    ......
    ......
    detected_coordinates = detected_objects  # Update global coordinate
    return result_frame
```

Next, after obtaining the coordinates (for example, red block: (100,200)), remember that the obtained coordinates are relative to the camera frame. However, we want the coordinates of the red block relative to the robot. For this, I use linear interpolation method where I determine the boundaries of the upper-left and lower-right corner points using the maps_to_real() function. Make sure to replace the maps_coordinate with your new camera coordinates.

![Map to Real](./images/maptoreal.jpg)

![Camera vs Robot Coordinates](./images/kamvsreal.jpg)

![Calibration Method](./images/cara_kal.jpg)


## Creating a Web Interface for the Robot

The website serves as a place to input natural language command text and operate the robot. The website is hosted in Flask (app.py).

```
# FOR WEBSITE INTERFACE USING FLASK
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/detected_objects')
def get_detected_objects():
    global detected_coordinates
    return jsonify(detected_coordinates)

# Endpoint to handle running the robot
@app.route('/run-robot', methods=['POST'])
def run_robot_endpoint():
........
........


@app.route('/send_prompt', methods=['POST'])
def send_prompt():
.........
.........


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
```

Here's an example of the website display

![Web Display](./images/tampwe.jpg)

Note: To make the object detection frame visible on the web, ensure the /video_feed endpoint is accessible (reconfigure all variables for the functions related to generate_frame() and ensure the camera is connected to the computer running the web server app.py)

For instructions on how to use the website, it will be discussed at the end.

## Creating LLM Inference API

This part will later be in inference.ipynb

The LLM Inference API is created with Flask. In this research, we use NGROK reverse proxy so the API can be accessed through the internet. If you want to use local network/intranet, skip NGROK and replace the inference request link on app.py with the IP of the computer used for inference.

```
# Open a ngrok tunnel to the HTTP server
public_url = ngrok.connect(5000).public_url
print(" * ngrok tunnel \"{}\" -> \"http://127.0.0.1:{}/\"".format(public_url, 5000))

# Update any base URLs to use the public ngrok URL
app.config["BASE_URL"] = public_url

# Define Flask routes
@app.route("/")
def index():
    return "Hello from Inferrence Computer"

@app.route('/api')
def api():
    data = request.json
    input_context = data.get('input_context', None)
    object_context = data.get('object_context', None)
    
    if input_context and object_context:
        output_data = inference(input_context, object_context)
        return jsonify(output_data)
    elif input_context is None:
        return jsonify({"status": "failure", "message": "input_context are missing"}), 400
    else:
        return jsonify({"status": "failure", "message": "internal error"}), 400

# Start the Flask server in a new thread
threading.Thread(target=app.run, kwargs={"use_reloader": False}).start()
```

Note: The inference(input_context, object_context) function takes the input command (input_context) and object detection perception results (object_context) and is executed in the cell before Flask. To test, use applications like POSTMAN to make requests to the API and ensure it returns the appropriate JSON action plan.

![Example Inference](./images/postman.jpg)

## Connecting Everything Together

The setup in this research is divided into 2 parts: LLM inference setup and robot setup.

### Inference Setup

Run inference.ipynb on the HPC and ensure the /api endpoint is accessible by making a request (use applications like POSTMAN) to check whether the API can return inference results.

### Robot Setup

Next, on the LPC there are several steps

1. Try installing [dobotlab](https://www.dobot-robots.com/service/download-center). Dobotlab is a GUI to control the Dobot Magician. This application is needed to check which port the DOBOT is connected to (e.g., 'COM3') and will be useful in the future to explore the functionality of this robot.
2. Next, install the following libraries (it's recommended to use venv/conda to avoid interfering with other libraries):

```
from flask import Flask, Response, render_template, jsonify, request
import cv2
import numpy as np
import requests
import pydobot
import json
```

The main library used to control the robot is [pydobot](https://github.com/luismesas/pydobot). Read the repository first to understand its documentation.

After installing all libraries, open the folder where pydobot is installed. Next, replace the contents of dobot.py with the [dobot.py](./dobot.py) file in this repository.

Now try running the tes_koneksi.py function to see if the robot library is installed correctly. If there's an error, make sure the port (e.g., COM8) is correct, the robot is turned on and connected via USB, and try running the code after the robot beeps (because the robot will initialize when it's first turned on).

If the robot doesn't respond or there's an error message in the CLI, try homeing the robot manually using dobotlab. Next, disconnect the dobot from dobotlab (DO NOT TURN OFF / UNPLUG THE ROBOT !!!) and try running the code again.

If tes_koneksi.py runs smoothly, next connect the camera and robot to the LPC computer with the following configuration.

![Top Setup](./images/setup-atas.jpeg)

![Bottom Setup](./images/setup-bawah.jpeg)

After that, try running app.py and inference.ipynb. On the website hosted by app.py, try accessing the / endpoint or index.html. It should produce the following display:

![Example Website Display](./images/contoh-web.png)

For using the website
1. Enter a natural language command input in the text column "for example, move the yellow block forward".
2. Click run inference and wait until the action plan in JSON form appears.
3. If the inference result in JSON form appears and there are no errors, click run robot (make sure to continue monitoring the robot's condition).

Note: If the coordinates start to deviate/become inaccurate, try homeing with the tes_koneksi.py code.
