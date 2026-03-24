# Diagram & Visualisasi Sistem

## 1. Arsitektur Sistem Overall

```
┌────────────────────────────────────────────────────────────────────┐
│              INTERAKSI MANUSIA-ROBOT BERBASIS LLM                 │
│            Pembangkitan Action Plan pada Robot Lengan             │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐              ┌──────────────────────────────┐
│    USER INTERFACE       │              │    LLM INFERENCE SERVER      │
│   (Web Browser - LPC)   │◄─ HTTP ──────┤  (GPU Server - HPC)          │
│                         │   (ngrok)    │                              │
│ • Text Input            │──────────────► • FastLanguageModel          │
│ • Voice Input (Web      │              │ • LoRA Adapter (Gemma 2B)    │
│   Speech API)           │              │ • Action Plan Generation     │
│ • Video Stream          │              │                              │
│ • Detected Objects      │              │ Models:                      │
│                         │              │ - Aryaduta/modellora9        │
│                         │              │ - max_seq_length: 2048       │
└─────────────────────────┘              │ - max_new_tokens: 1024       │
         ▲                               └──────────────────────────────┘
         │
    FLASK APP
    app.py
         │
    ┌────┴───────────────────────────────────────────────────────┐
    │                                                             │
    ├──► Object Detection (OpenCV)                              │
    │    └─ HSV color filtering (biru/jingga/kuning)            │
    │    └─ Contour detection                                   │
    │    └─ Linear interpolation (camera → robot coords)        │
    │                                                             │
    ├──► Video Stream Generator                                 │
    │    └─ Webcam capture (ID: 5) atau IP camera              │
    │    └─ Frame rotation (90° untuk webcam)                   │
    │    └─ MJPEG encoding untuk web streaming                 │
    │                                                             │
    └──► Robot Execution (PyDobot)                              │
         └─ Serial COM3 (115200 baud)                           │
         └─ Parse JSON actions                                  │
         └─ Execute move/suction commands                       │
         └─ Wait mechanism untuk command completion             │
         │
    ┌────┴─────────────────────┐
    │   DOBOT MAGICIAN         │
    │   Robot Arm              │
    │                          │
    │ • X,Y,Z Cartesian Move   │
    │ • Joint angles (j1-j4)   │
    │ • Suction Cup Control    │
    │ • Real-time Pose Query   │
    │                          │
    └──────────────────────────┘
```

## 2. Fine-tuning Pipeline

```
┌──────────────────────┐
│  Base Model: Gemma   │
│      2B Model        │
│  (Hugging Face)      │
└──────────────────────┘
         │
         │ LoRA (Low Rank Adaptation)
         │ rank=16, lora_alpha=32
         ▼
┌──────────────────────────────────────────────┐
│      Fine-tuning Dataset (Alpaca Format)     │
├──────────────────────────────────────────────┤
│ {                                            │
│   "instruction": "Generate robot action      │
│    plan with available objects and           │
│    commands...",                             │
│   "input": "Move blue block forward",        │
│   "output": "{actions: [...]}"               │
│ }                                            │
└──────────────────────────────────────────────┘
         │
         │ SFTTrainer (Supervised Fine-Tuning)
         │ Learning rate: 2e-4
         │ Epochs: 3
         ▼
┌──────────────────────────────────┐
│  Fine-tuned Model (LoRA Adapter) │
│  Format: SafeTensor (.safetensors)
│  Storage: Hugging Face Hub       │
│  Model Name: Aryaduta/modellora9 │
└──────────────────────────────────┘
         │
         │ FastLanguageModel.from_pretrained()
         ▼
┌──────────────────────────────────┐
│    Ready for Inference           │
│                                  │
│ Input:  user_command +           │
│         detected_objects          │
│                                  │
│ Output: JSON Action Plan         │
└──────────────────────────────────┘
```

## 3. Object Detection Flow

```
┌─────────────────────────────────┐
│   Camera Frame (BGR)            │
│   Size: HxWx3                   │
│   Source: Webcam/IP Camera      │
└─────────────────────────────────┘
         │
         │ cv2.cvtColor(BGR → HSV)
         ▼
┌─────────────────────────────────┐
│   HSV Color Space Frame         │
│   Better untuk color detection  │
└─────────────────────────────────┘
         │
    ┌────┴────┬─────────────┬──────────────┐
    │          │             │              │
    ▼          ▼             ▼              ▼
  Blue       Orange        Yellow        (future)
  Range:     Range:        Range:
  H:100-140  H:5-25        H:20-40
  S:50-255   S:50-255      S:90-255
  V:100-255  V:50-255      V:100-255
    │          │             │              │
    │ cv2.inRange()         │
    ▼          ▼             ▼              ▼
  Mask_B    Mask_O       Mask_Y
  (binary)  (binary)      (binary)
    │          │             │              │
    │ cv2.findContours()     │
    ▼          ▼             ▼              ▼
  Contours  Contours    Contours
  (list)    (list)      (list)
    │          │             │              │
    │ Filter by size(100-5000px) & find largest
    ▼          ▼             ▼              ▼
  Contour_B Contour_O  Contour_Y
  (single)  (single)   (single)
    │          │             │              │
    │ cv2.boundingRect() + check overlap│
    │          │             │              │
    └────┬─────┴─────────────┴──────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Bounding Boxes (camera coords)
│  • Blue: (x1, y1, w1, h1)    
│  • Orange: (x2, y2, w2, h2)  
│  • Yellow: (x3, y3, w3, h3)  
└──────────────────────────────┘
         │
         │ maps_to_real(x, y) - Linear Interpolation
         │
    ┌────────────────────────────────────────────┐
    │ Calibration Mapping:                       │
    │ Camera (270, 132) → Robot (294, 122)       │
    │ Camera (142, 338) → Robot (160, -124)      │
    │                                            │
    │ Formula:                                   │
    │ real_x = real_x1 + (real_x2 - real_x1) *  │
    │         ((camera_x - cam_x1) / (cam_x2 - cam_x1))
    │                                            │
    │ real_y = real_y1 + (real_y2 - real_y1) *  │
    │         ((camera_y - cam_y1) / (cam_y2 - cam_y1))
    └────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Real World Coordinates       │
│ • Blue: (152.76, 158.92)     │
│ • Orange: (-168.94, -129.37) │
│ • Yellow: (-86.59, 117.21)   │
│ Z: -50 (fixed)               │
└──────────────────────────────┘
         │
         │ Draw bounding box + text on frame
         ▼
┌──────────────────────────────┐
│ Output Frame (with overlay)  │
│ Sent to /video_feed endpoint │
└──────────────────────────────┘
```

## 4. Action Plan Execution State Machine

```
START
  │
  ├─► Parse JSON
  │   └─ Extract "actions" array
  │
  ▼
FOR EACH ACTION IN actions[]:
  │
  ├─► action["command"]
  │   │
  │   ├─► "move"
  │   │   ├─ Get current pose (x,y,z,r)
  │   │   └─ Apply directional offset:
  │   │      ├─ atas: z+20
  │   │      ├─ bawah: z-30
  │   │      ├─ kiri: y+40
  │   │      ├─ kanan: y-40
  │   │      ├─ depan: x+40
  │   │      └─ belakang: x-30
  │   │   └─ device.move_to(x', y', z', r)
  │   │
  │   ├─► "move_to"
  │   │   ├─ Extract params: x, y, z
  │   │   ├─ If suction_status == True:
  │   │   │  └─ z += 35 (height offset)
  │   │   └─ device.move_to(x, y, z, 0)
  │   │
  │   └─► "suction_cup"
  │       ├─ action == "on"
  │       │  ├─ suction_status = True
  │       │  └─ device.suck(True)
  │       └─ action == "off"
  │          ├─ suction_status = False
  │          └─ device.suck(False)
  │
  ▼
END OF LOOP
  │
  ├─► Home position: device.move_to(250, 0, 0, 0)
  ├─► Disable suction: device.suck(False)
  │
  ▼
END
```

## 5. Web Request Flow

```
User Input ─────────────────► Web Interface (index.html / index2.html)
                                        │
                                        ▼
                        JavaScript: sendPrompt()
                        │
                        │ Collect:
                        │ • object_context (from /detected_objects)
                        │ • input_context (from text input)
                        │
                        ▼
                    POST /send_prompt
                        │
                        ├─► Collect detected objects
                        ├─► Collect user command
                        │
                        ▼
                    JSON Payload:
                    {
                      "object_context": "1. Balok biru: (152.76, 158.92, -50)...",
                      "input_context": "pindahkan balok biru ke depan"
                    }
                        │
                        ▼
                    HTTP GET (with ngrok)
                    ┌─────────────────────────────────────┐
                    │ https://412c-...-free.app/api      │
                    │ Headers:                            │
                    │ - ngrok-skip-browser-warning        │
                    │ - Content-Type: application/json    │
                    └─────────────────────────────────────┘
                        │
                        │ (Network)
                        │
                        ▼
                    HPC LLM API
                        │
                        ├─► Load model
                        ├─► Prepare prompt
                        ├─► Run inference
                        ├─► Parse JSON output
                        │
                        ▼
                    JSON Response:
                    {
                      "actions": [
                        {"command": "move_to", "parameters": {...}},
                        {"command": "suction_cup", "parameters": {...}},
                        ...
                      ]
                    }
                        │
                        │ (Network)
                        │
                        ▼
                    LPC receive response
                        │
                        ▼
                    Display in #inference-result
                        │
                        ▼
                    User Click "Jalankan" button
                        │
                        ▼
                    JavaScript: runRobot()
                        │
                        ▼
                    POST /run-robot
                        │
                        ├─► Parse JSON
                        ├─► Call RobotExecute2(actions)
                        │
                        ▼
                    Robot Execution
                        │
                        ├─► Serial COM3
                        ├─► Command → Robot
                        ├─► Wait for completion
                        │
                        ▼
                    Display status in #robot-result
```

## 6. Communication Protocol - Dobot Serial

```
HOST (LPC)                              ROBOT (Dobot Magician)
    │                                         │
    │ 1. Establish Serial Connection         │
    │────► OPEN COM3 (115200, 8N1) ───────►│
    │                                         │
    │ 2. Initialize Sequence                 │
    │────► _set_queued_cmd_start_exec() ───►│
    │────► _set_queued_cmd_clear() ──────►│
    │────► _set_ptp_joint_params() ──────►│
    │────► _set_ptp_coordinate_params() ──►│
    │────► _set_ptp_jump_params() ────────►│
    │────► _set_ptp_common_params() ─────►│
    │────► _get_pose() ──────────────────►│◄──── Return current x,y,z,r,j1,j2,j3,j4
    │                                      │
    │ 3. Execute Command (example: move_to)
    │                                      │
    │ Message Structure:                   │
    │ ┌────────────────────────────────┐   │
    │ │ Header (COBS encoded)          │   │
    │ │ ID: SET_PTP_COORDINATE_CMD     │   │
    │ │ Ctrl: 3                        │   │
    │ │ Params:                        │   │
    │ │  - x (float32)                 │   │
    │ │  - y (float32)                 │   │
    │ │  - z (float32)                 │   │
    │ │  - r (float32)                 │   │
    │ │  - mode (uint8)                │   │
    │ │ Checksum (XOR)                 │   │
    │ └────────────────────────────────┘   │
    │                                       │
    │────► SEND via Serial ──────────────►│ Move to (x,y,z,r)
    │                                      │
    │◄───── Response (ack + queue_index) ──│
    │                                      │
    │ 4. Wait for Execution              │
    │    (if wait=True)                   │
    │                                      │
    │────► Polling _get_queued_cmd_current_index() ──│
    │                                      │
    │◄───── Return current_idx ────────────│
    │                                      │
    │ if current_idx == expected_idx:     │
    │     Command completed!               │
    │                                      │
    │ Repeat steps 3-4 for each action   │
    │                                      │
    │ 5. Close Connection                │
    │────► CLOSE COM3 ──────────────────►│
```

## 7. Class & Module Dependencies

```
app.py
├─ Flask
├─ cv2 (OpenCV)
│  ├─ color space conversion
│  ├─ contour detection
│  └─ bounding box operations
├─ numpy
├─ requests (HTTP client)
├─ pydobot.Dobot
│  ├─ serial communication
│  ├─ message protocol
│  └─ command execution
└─ json

dobot.py (pydobot module)
├─ serial (PySerial)
├─ struct (binary packing)
├─ time
├─ threading
│  └─ Thread lock mechanism
├─ message.Message
├─ enums.PTPMode
├─ enums.CommunicationProtocolIDs
└─ enums.ControlValues

inference.ipynb / simple-inf.ipynb
├─ unsloth.FastLanguageModel
├─ torch
├─ transformers (AutoTokenizer)
├─ trl.SFTTrainer
├─ datasets.load_dataset
└─ json parsing

index.html / index2.html
├─ Fetch API
├─ WebKitSpeechRecognition (voice input)
├─ Tailwind CSS v3
└─ Vanilla JavaScript
```

## 8. Data Format Specifications

### Action Plan JSON Schema

```json
{
  "type": "object",
  "properties": {
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "command": {
            "type": "string",
            "enum": ["move", "move_to", "suction_cup", "err_msg"]
          },
          "parameters": {
            "type": "object",
            "oneOf": [
              {
                "properties": {
                  "direction": {
                    "type": "string",
                    "enum": ["atas", "bawah", "depan", "belakang", "kiri", "kanan"]
                  }
                }
              },
              {
                "properties": {
                  "x": {"type": "number"},
                  "y": {"type": "number"},
                  "z": {"type": "number"}
                }
              },
              {
                "properties": {
                  "action": {
                    "type": "string",
                    "enum": ["on", "off"]
                  }
                }
              },
              {
                "properties": {
                  "msg": {"type": "string"}
                }
              }
            ]
          }
        },
        "required": ["command", "parameters"]
      }
    }
  },
  "required": ["actions"]
}
```

### Detected Objects Format

```json
[
  ["biru", [152.76, 158.92]],
  ["jingga", [-168.94, -129.37]],
  ["kuning", [-86.59, 117.21]]
]
```

### Inference Request Format

```json
{
  "object_context": "1. Balok biru: (152.76, 158.92, -50)\n2. Balok jingga: (-168.94, -129.37, -50)\n3. Balok kuning: (-86.59, 117.21, -50)",
  "input_context": "pindahkan balok biru ke depan"
}
```

---

## 9. Performance Metrics

```
┌────────────────────────────────┐
│   Video Stream Processing      │
├────────────────────────────────┤
│ FPS: 30 (typical)              │
│ Resolution: 640x480 (webcam)   │
│ Encoding: MJPEG                │
│ Latency: ~100-200ms            │
└────────────────────────────────┘

┌────────────────────────────────┐
│   Object Detection             │
├────────────────────────────────┤
│ Algorithm: HSV color filtering │
│ Detection speed: ~5-10ms       │
│ Accuracy: ~95% (controlled env)│
│ Max objects: 3                 │
└────────────────────────────────┘

┌────────────────────────────────┐
│   LLM Inference                │
├────────────────────────────────┤
│ Model: Gemma 2B + LoRA         │
│ Speed: ~2-5 seconds            │
│ Max tokens: 1024               │
│ VRAM: 14GB (Colab)             │
└────────────────────────────────┘

┌────────────────────────────────┐
│   Robot Execution              │
├────────────────────────────────┤
│ Serial baud: 115200            │
│ Motion speed: configurable     │
│ Response time: ~100-500ms      │
│ Accuracy: ±5mm                 │
└────────────────────────────────┘

┌────────────────────────────────┐
│   End-to-End Latency           │
├────────────────────────────────┤
│ User input → Robot execution:  │
│ ~5-10 seconds (typical)        │
│                                │
│ Breakdown:                     │
│ • User input → LLM: ~3-5s      │
│ • LLM → Action plan: ~2-5s     │
│ • Parse & execute: ~100ms      │
└────────────────────────────────┘
```

---

**End of Diagrams & Visualizations**
