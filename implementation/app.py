from flask import Flask, Response, render_template, jsonify, request
import cv2
import numpy as np
import requests
import pydobot
import json

app = Flask(__name__)

# Global variable to store detected coordinates
detected_coordinates = []

# Linear interpolation to convert camera coordinate to real coordinate
# input => top left and bottom right robot coordinate (set this first before camera), camera coordinate (use calibration mat / paper), and x y camera (to be converted)
# output => real world coordinate xreal, yreal
def maps_to_real(maps_x, maps_y):
    # Define the known mappings (top-left and bottom-right corners)
    maps_coordinates = {
        'top_left': (270, 132),
        'bottom_right': (142, 338)
    }

    real_coordinates = {
        'top_left': (294, 122),
        'bottom_right': (160, -124)
    }
    
    # Extract mappings
    maps_x_top_left, maps_y_top_left = maps_coordinates['top_left']
    maps_x_bottom_right, maps_y_bottom_right = maps_coordinates['bottom_right']
    
    real_x_top_left, real_y_top_left = real_coordinates['top_left']
    real_x_bottom_right, real_y_bottom_right = real_coordinates['bottom_right']

    # Perform linear interpolation
    def interpolate(x1, x2, y1, y2, x):
        return y1 + (y2 - y1) * ((x - x1) / (x2 - x1))
    
    # Interpolate for x-coordinate
    real_x = interpolate(maps_x_top_left, maps_x_bottom_right, real_x_top_left, real_x_bottom_right, maps_x)
    
    # Interpolate for y-coordinate
    real_y = interpolate(maps_y_top_left, maps_y_bottom_right, real_y_top_left, real_y_bottom_right, maps_y)

    rounded_x = round(real_x, 2)
    rounded_y = round(real_y, 2)

    return rounded_x, rounded_y

# Function to detect blocks
# Input = Image frame
# Output = frame of detected object (camera with bounding box ) and update detected_object global coordinate
def detect_blocks(frame, min_size=100, max_size=5000):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    lower_blue = np.array([100, 50, 100])
    upper_blue = np.array([140, 255, 255])
    
    lower_orange = np.array([5, 50, 50])
    upper_orange = np.array([25, 255, 255])
    
    lower_yellow = np.array([20, 90, 100])
    upper_yellow = np.array([40, 255, 255])
    
    mask_blue = cv2.inRange(hsv_frame, lower_blue, upper_blue)
    mask_orange = cv2.inRange(hsv_frame, lower_orange, upper_orange)
    mask_yellow = cv2.inRange(hsv_frame, lower_yellow, upper_yellow)
    
    contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_orange, _ = cv2.findContours(mask_orange, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_yellow, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    def filter_contours(contours, min_size, max_size):
        filtered_contours = [cnt for cnt in contours if min_size < cv2.contourArea(cnt) < max_size]
        return filtered_contours
    
    def find_largest_contour(contours):
        if contours:
            return max(contours, key=cv2.contourArea)
        else:
            return None
    
    def check_overlap(rect1, rect2):
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        if (x1 < x2 + w2 and x1 + w1 > x2 and
            y1 < y2 + h2 and y1 + h1 > y2):
            return True
        return False
    
    def draw_bounding_box(frame, contour, color_name):
        if contour is not None:
            x, y, w, h = cv2.boundingRect(contour)
            overlap = False
            for (box, name) in drawn_boxes:
                if check_overlap((x, y, w, h), box):
                    overlap = True
                    break
            if not overlap:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{color_name}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"Coordinates: ({x}, {y})", (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                drawn_boxes.append(((x, y, w, h), color_name))
                detected_objects.append((color_name, (maps_to_real(x,y))))
    
    global detected_coordinates
    detected_objects = []
    result_frame = frame.copy()
    drawn_boxes = []
    
    draw_bounding_box(result_frame, find_largest_contour(filter_contours(contours_blue, min_size, max_size)), "biru")
    draw_bounding_box(result_frame, find_largest_contour(filter_contours(contours_orange, min_size, max_size)), "jingga")
    draw_bounding_box(result_frame, find_largest_contour(filter_contours(contours_yellow, min_size, max_size)), "kuning")
    
    detected_coordinates = detected_objects  # Update global coordinates
    
    return result_frame

# Function to connect to robot and execute command
# Input = JSON action plan
# Output = Real world robotic action
def RobotExecute2(data):
    device = pydobot.Dobot(port="COM3", verbose=False)
    suction_status = False
    for action in data:
        command = action.get('command', '')
        if command == 'move':
            (x, y, z, r, j1, j2, j3, j4) = device.pose()
            direction = action.get('parameters', '').get('direction', '')
            if direction == 'up':
                suction_status = False
                device.move_to(x, y, z+20, 0, mode=0,  wait=True) 
                print("up")
            elif direction == 'down':
                device.move_to(x, y, z-30, 0, mode=0,  wait=True) 
                print("down")
            elif direction == 'left':
                device.move_to(x, y+40, z, 0, mode=0, wait=True) 
                print("left")
            elif direction == 'right':
                device.move_to(x, y-40, z, 0, mode=0,  wait=True) 
                print("right")
            elif direction == 'forward':
                device.move_to(x+40, y, z, 0, mode=0, wait=True) 
                print("forward")
            elif direction == 'backward':
                device.move_to(x-30, y, z, 0, mode=0, wait=True) 
                print("belakang")
            else:
                print(f"arah {direction} tidak valid")
        elif command == 'move_to':
            parameters = action.get('parameters', '')
            x = parameters.get('x', '')
            y = parameters.get('y', '')
            z = parameters.get('z', '')
            print(f"pergi ke koordinat x={x}, y={y}, z={z}")
            if suction_status == False:
                device.move_to(x, y, z, 0,mode=0, wait=True)
            else:
                device.move_to(x, y, z+35, 0, mode=0, wait=True)
        elif command == 'suction_cup':
            action_status = action.get('parameters', '').get('action', '')
            if action_status == 'on':
                suction_status = True
                print(f"status penyedot {action_status}")
                device.suck(True)
            elif action_status == 'off':
                suction_status = False
                print(f"status penyedot {action_status}")
                device.suck(False)   
            else:
                print("Invalid action status for suction cup command.")
                print(f"status penyedot {action_status} tidak valid")
        else:
            print(f"command : {command} tidak valid")
    device.move_to(250, 0, 0, 0, mode=0, wait=True)
    device.suck(False)


# fuction to generate frame of detected object (for website). In website it display camera image with opencv processing
# Input = camera frame (from droidcam IP)
# Output = frame of camera processed with openccv
def generate_frames():
    global detected_coordinates
    #cap = cv2.VideoCapture("http://10.4.66.158:4747/video")
    
    #IF USING WEBCAM, ROTATE 90 DEGREE (the robot arm should be to the left frame)
    cap = cv2.VideoCapture(5)

    while True:
        success, frame = cap.read()
        if not success:
            break
        else:

            #USE FRAME BELOW IF USE WEBCAM, if use droidcam, comment code below
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            #regular code, do not comment
            frame = detect_blocks(frame)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


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
    try:
        # Get the JSON data from the request
        data = request.json
        data_json = json.loads(data)['actions']

        #actions = data.get('actions', [])
        RobotExecute2(data_json)
        print(data)
        return jsonify({'status': "Menjalankan perintah robot. Awasi kondisi robot."}), 200
    
    except Exception as e:
        app.logger.error(f"Error running robot: {str(e)}")
        return jsonify({'error': 'Failed to run robot'}), 500


@app.route('/send_prompt', methods=['POST'])
def send_prompt():
    try:
        data = request.json  # Assuming the data sent is JSON
        
        # Extract json_object_context and input_context from data
        object_context = data.get('object_context', {})
        input_context = data.get('input_context', '')

        # Prepare headers for the POST request
        headers = {
            'ngrok-skip-browser-warning': '1',
            'Content-Type': 'application/json'
        }

        # Prepare data to send to external API
        payload = {
            'object_context': object_context,
            'input_context': input_context
        }

        # Send POST request to external API
        response = requests.get('https://412c-103-159-199-164.ngrok-free.app/api', headers=headers, json=payload)

        # Check if request was successful
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({'error': 'Failed to send data to external API'}), response.status_code

    except Exception as e:
        app.logger.error(f"Error in send_prompt: {str(e)}")
        print(f"Error in send_prompt: {str(e)}")  # Print the error to the terminal
        return jsonify({'error': 'Internal server error'}), 500
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
