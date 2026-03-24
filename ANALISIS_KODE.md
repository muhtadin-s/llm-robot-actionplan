# Analisis Kode - Interaksi Manusia-Robot Berbasis LLM

## 1. Ringkasan Proyek

Proyek ini adalah **Tugas Akhir (TA)** yang mengintegrasikan **Large Language Model (LLM)** dengan **Robot Lengan (Dobot Magician)** untuk menghasilkan **Action Plan** dari input bahasa alami. Sistem ini terdiri dari dua komponen utama:

### Arsitektur Sistem
- **HPC (High Performance Computer)**: Menjalankan inferensi LLM dan API server
- **LPC (Low Performance Computer)**: Menjalankan web interface, deteksi objek, dan kontrol robot

---

## 2. Struktur Folder dan File

```
ta_duta_lengkap-main/
├── README.md                          # Dokumentasi proyek utama
├── finetuning/                        # Fase 1: Fine-tuning LLM
│   ├── README.md                      # Penjelasan metodologi finetuning
│   └── train.ipynb                    # Notebook untuk training model
├── implementasi/                      # Fase 2: Implementasi Robot
│   ├── README.md                      # Panduan implementasi
│   ├── app.py                         # Web server Flask utama
│   ├── dobot.py                       # Driver komunikasi dengan robot
│   ├── tes_koneksi.py                 # Script testing koneksi robot
│   ├── inference.ipynb                # Notebook inference lengkap
│   ├── simple-inf.ipynb               # Notebook inference sederhana
│   └── images/                        # Dokumentasi gambar
└── templates/                         # Web Interface
    ├── index.html                     # Interface utama (full-width)
    └── index2.html                    # Interface alternatif (2-column)
```

---

## 3. Fase 1: Fine-tuning Model LLM

### 3.1 File: `finetuning/README.md`

**Tujuan**: Menyesuaikan base model LLM untuk menghasilkan action plan robot

**Komponen Utama**:

| Aspek | Detail |
|-------|--------|
| **Model Base** | Gemma 2B (Google) |
| **Metode Finetuning** | LoRA (Low Rank Adaptation) |
| **Library** | Unsloth (inference + finetuning) |
| **Format Dataset** | Alpaca Format |
| **Perangkat** | Google Colab (14GB VRAM) |

**Format Dataset Alpaca**:
```json
{
  "instruction": "[Instruksi lengkap tentang perintah robot, format JSON, objek tersedia]",
  "input": "pindahkan balok biru ke depan",
  "output": "{\"actions\": [{\"command\": \"move_to\", ...}]}"
}
```

**Perintah Robot yang Didukung**:
1. `move`: Gerak lateral (atas, bawah, depan, belakang, kiri, kanan)
2. `move_to`: Gerak ke koordinat XYZ tertentu
3. `suction_cup`: Aktifkan/nonaktifkan penyedot
4. `err_msg`: Return error message jika task tidak bisa dicapai

**Dataset Sample**:
- **Input**: "pindahkan posisi balok biru ke posisi kiri"
- **Output**: 
```json
{
  "actions": [
    {"command": "move_to", "parameters": {"x": 152.76, "y": 158.92, "z": 6}},
    {"command": "suction_cup", "parameters": {"action": "on"}},
    {"command": "move", "parameters": {"direction": "kiri"}},
    {"command": "suction_cup", "parameters": {"action": "off"}}
  ]
}
```

**Model Output**: LoRA adapter disimpan di Hugging Face (format safetensor)

---

### 3.2 File: `finetuning/train.ipynb`

**Statusnya**: Notebook dengan 7 cells untuk training

**Alur Training**:
1. Setup Unsloth dan libraries
2. Load model Gemma 2B dengan LoRA
3. Load dataset dari Hugging Face
4. Konfigurasi training parameters
5. Inisialisasi dan jalankan SFTTrainer
6. Simpan model ke Hugging Face Hub

**Teknologi**:
- `FastLanguageModel`: Untuk fast inference dan training
- `SFTTrainer`: Supervised Fine-Tuning dari TRL
- `max_seq_length`: 2048 tokens

---

## 4. Fase 2: Implementasi Robot

### 4.1 File: `implementasi/dobot.py` (370 baris)

**Tujuan**: Driver komunikasi serial dengan robot Dobot Magician

**Fungsionalitas Utama**:

| Method | Fungsi |
|--------|--------|
| `__init__(port, verbose)` | Inisialisasi koneksi serial (115200 baud) |
| `_get_pose()` | Get posisi real-time robot (x,y,z,r,j1,j2,j3,j4) |
| `move_to(x,y,z,r,mode,wait)` | Move ke koordinat Cartesian |
| `_set_cp_cmd()` | CP command untuk continuous path |
| `_set_end_effector_gripper()` | Control gripper |
| `_set_end_effector_suction_cup()` | Control penyedot |
| `_set_ptp_joint_params()` | Set joint velocity & acceleration |
| `_set_ptp_coordinate_params()` | Set Cartesian velocity & acceleration |
| `_set_ptp_jump_params()` | Set jump parameters |

**Protokol Komunikasi**:
- Serial port: COM3 (configurable)
- Baud rate: 115200
- Thread-safe dengan mutex lock
- Message-based protocol dengan struct packing

**Thread Management**:
- Lock acquisition untuk message synchronization
- Wait mechanism untuk command execution confirmation

---

### 4.2 File: `implementasi/tes_koneksi.py`

**Tujuan**: Simple test script untuk testing koneksi robot

```python
# Calibration movement pattern:
device.move_to(250, 0, 0, 0, mode=0, wait=True)      # Home
device.move_to(284, 125, -50, 0, mode=0, wait=True)  # Top-left corner
device.move_to(165, -130, -50, 0, mode=0, wait=True) # Bottom-right corner
device.move_to(250, 0, 0, 0, mode=0, wait=True)      # Back to home
```

**Fungsi**: Memverifikasi konektivitas dan kalibrasi koordinat robot

---

### 4.3 File: `implementasi/app.py` (276 baris)

**Tujuan**: Web server Flask yang mengintegrasikan semua komponen

#### **4.3.1 Komponen Utama**:

##### A. **Linear Interpolation untuk Kalibrasi Kamera** (`maps_to_real()`)

Konversi dari koordinat kamera ke koordinat dunia nyata robot:

```python
# Input: Koordinat kamera (270, 132) -> (294, 122) [top-left]
#        Koordinat kamera (142, 338) -> (160, -124) [bottom-right]
# Output: Real-world coordinates
```

**Metode**: Linear interpolation 2D pada axis X dan Y

**Penting**: Calibration coordinate harus variatif (tidak semua integer/positif)

##### B. **Deteksi Objek dengan OpenCV** (`detect_blocks()`)

**Input**: Frame video dari webcam/droidcam
**Output**: Frame dengan bounding box + coordinates

**Proses**:
1. Convert BGR → HSV color space
2. Define color ranges untuk 3 balok:
   - **Biru**: H: 100-140
   - **Jingga**: H: 5-25
   - **Kuning**: H: 20-40
3. Create masks dengan `cv2.inRange()`
4. Find contours dengan `cv2.findContours()`
5. Filter by size (100-5000 pixels)
6. Cek overlap antar bounding box
7. Convert ke real coordinates dengan `maps_to_real()`

**Output**: 
```python
detected_coordinates = [
    ("biru", (152.76, 158.92)),
    ("jingga", (-168.94, -129.37)),
    ("kuning", (-86.59, 117.21))
]
```

##### C. **Eksekusi Aksi Robot** (`RobotExecute2()`)

**Input**: JSON action plan dari LLM

```python
{
  "actions": [
    {"command": "move", "parameters": {"direction": "atas"}},
    {"command": "move_to", "parameters": {"x": -30.21, "y": 233.32, "z": -40}},
    {"command": "suction_cup", "parameters": {"action": "on"}},
    ...
  ]
}
```

**Logic Execution**:
- **move**: Increment/decrement Z (atas/bawah) atau X/Y (lateral)
  - atas: +20 Z
  - bawah: -30 Z
  - kiri: +40 Y
  - kanan: -40 Y
  - depan: +40 X
  - belakang: -30 X

- **move_to**: Move ke koordinat XYZ
  - Jika suction aktif, tambah 35 pada Z (height offset)

- **suction_cup**: on/off penyedot

##### D. **Video Streaming** (`generate_frames()`)

**Input**: IP camera atau webcam (ID 5)
**Output**: MJPEG stream untuk browser

```python
# Rotate 90° untuk webcam biasa
frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

# JPEG encode
ret, buffer = cv2.imencode('.jpg', frame)

# Yield MJPEG format
yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
```

#### **4.3.2 Flask Routes**:

| Route | Method | Fungsi |
|-------|--------|--------|
| `/` | GET | Render index.html |
| `/video_feed` | GET | Stream video MJPEG |
| `/detected_objects` | GET | Return JSON detected objects |
| `/send_prompt` | POST | Send prompt ke external LLM API |
| `/run-robot` | POST | Execute action plan ke robot |

#### **4.3.3 Flow Eksekusi**:

```
User Input (Web Interface)
         ↓
Browser JS: sendPrompt()
         ↓
/send_prompt endpoint (LPC)
         ↓
HTTP GET ke HPC: https://...ngrok....app/api
         ↓
LLM Inference pada HPC
         ↓
Return JSON action plan ke LPC
         ↓
Display di web interface
         ↓
User click "Jalankan"
         ↓
/run-robot endpoint
         ↓
RobotExecute2() → Dobot serial commands
```

---

### 4.4 File: `implementasi/inference.ipynb`

**Tujuan**: Complete inference notebook dengan konteks real-time

**Struktur Cells**:

| Cell | Tujuan |
|------|--------|
| 1 | Import Unsloth, torch, transformers |
| 2 | Define Alpaca prompt template (Bahasa Indonesia) |
| 3 | Load fine-tuned model dari HuggingFace: `model_name = "Aryaduta/modellora9"` |
| 4 | Define `full_instruction` dengan format lengkap |
| 5-6 | Define `inferrence()` function |
| 7 | Helper imports |

**Fungsi `inferrence(input_context, object_context)`**:

```python
full_instruction2 = full_instruction.format(object_context=object_context)

inputs = tokenizer([alpaca_prompt.format(full_instruction2, input_context, "")],
                   return_tensors="pt").to("cuda")

outputs = model.generate(**inputs, max_new_tokens=1024, use_cache=True)

# Extract JSON dari output antara "### Response:" dan "<eos>"
json_response = extract_json(decoded_output)
return json_response
```

**Input Context**: User command dalam bahasa alami
**Object Context**: Hasil deteksi objek dengan koordinat

---

### 4.5 File: `implementasi/simple-inf.ipynb`

**Tujuan**: Simplified inference notebook untuk quick testing

**Differences**:
- Same structure as `inference.ipynb`
- Dimulai dari loading model yang sudah fine-tuned
- Focus pada testing inference saja, tanpa training

---

## 5. Web Interface

### 5.1 File: `templates/index.html` (167 baris)

**Technology Stack**: HTML + Tailwind CSS + Vanilla JavaScript

**Layout**: Single-column, mobile-responsive

**Sections**:
1. **Header**: Judul proyek
2. **Video Feed**: Stream dari `/video_feed`
3. **Detected Objects**: List objek yang terdeteksi
4. **Input Control**: 
   - Text input untuk perintah
   - Voice input button (Web Speech API)
   - Inference button
5. **Inference Result**: Display JSON output
6. **Robot Execution**: Run button + status
7. **Footer**: Credit

**JavaScript Functions**:
- `fetchDetectedObjects()`: Fetch dari `/detected_objects` setiap interval
- `sendPrompt()`: POST ke `/send_prompt` dengan object + input context
- `runRobot()`: POST ke `/run-robot` dengan action plan JSON
- `startSpeechRecognition()`: Indonesian language voice input

**Styling**: Tailwind CSS utility classes
- Container: mx-16, my-10
- Buttons: bg-gray-800, hover:bg-gray-700
- Cards: bg-gray-200, rounded-md

---

### 5.2 File: `templates/index2.html` (220 baris)

**Technology Stack**: HTML + Tailwind CSS v3.4.5 + Vanilla JavaScript

**Layout**: Two-column responsive design

**Main Differences dari index.html**:
- Left column (50% width): Video feed
- Right column (50% width): Control panels
- Compact input field dengan speech button
- Loading animation dengan pulsing dots
- Modern design dengan black buttons dan smooth transitions

**Key Features**:
- Responsive: Mobile (full-width) → Desktop (2-column)
- Loading indicator dengan animate-pulse
- Speech-to-text terintegrasi
- Smooth hover effects

---

## 6. Summary Teknologi & Library

### **Backend (Python)**:
| Library | Fungsi |
|---------|--------|
| `Flask` | Web framework |
| `OpenCV (cv2)` | Image processing & object detection |
| `NumPy` | Array operations |
| `requests` | HTTP client untuk API calls |
| `pydobot` | Driver komunikasi robot |
| `json` | JSON parsing |

### **Frontend (JavaScript)**:
| Technology | Fungsi |
|-----------|--------|
| `Fetch API` | HTTP requests |
| `Web Speech API` | Voice input (Indonesian) |
| `WebKitSpeechRecognition` | Browser speech recognition |
| `Tailwind CSS` | Styling |

### **Machine Learning**:
| Library | Fungsi |
|---------|--------|
| `Unsloth` | Fast LLM inference & finetuning |
| `Transformers` | Hugging Face models |
| `TRL` | SFTTrainer untuk finetuning |
| `Torch` | Deep learning framework |
| `Datasets` | Load dataset dari HuggingFace |

---

## 7. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOW PERFORMANCE COMPUTER (LPC)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         Web Interface (Flask + HTML/CSS/JS)         │       │
│  │  - Input prompt dari user                           │       │
│  │  - Video stream display                             │       │
│  │  - Voice input (Web Speech API)                     │       │
│  └──────────────────────────────────────────────────────┘       │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │      Object Detection Module (OpenCV)                │       │
│  │  - Detect blocks (biru, jingga, kuning)             │       │
│  │  - Linear interpolation kamera → robot              │       │
│  │  - Real-time coordinate tracking                    │       │
│  └──────────────────────────────────────────────────────┘       │
│                              ↓ & ↑                              │
│         HTTP GET/POST ←────────────────→ Backend API            │
│                              ↓ & ↑                              │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         Robot Execution Module (PyDobot)            │       │
│  │  - Parse JSON action plan                           │       │
│  │  - Execute move, suction commands                   │       │
│  │  - Serial communication (COM3)                      │       │
│  └──────────────────────────────────────────────────────┘       │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │      Dobot Magician Robot Arm                        │       │
│  │  - Serial connection 115200 baud                    │       │
│  │  - X,Y,Z,R joint control                            │       │
│  │  - Suction cup control                              │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

                          HTTP via ngrok
                              ↓ & ↑

┌─────────────────────────────────────────────────────────────────┐
│              HIGH PERFORMANCE COMPUTER (HPC)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         LLM Inference API Endpoint                   │       │
│  │  - Receive: {object_context, input_context}         │       │
│  │  - Process dengan fine-tuned Gemma 2B + LoRA        │       │
│  │  - Return: JSON action plan                         │       │
│  └──────────────────────────────────────────────────────┘       │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Fine-tuned Model: Aryaduta/modellora9 (HuggingFace)│       │
│  │  - Base: Gemma 2B                                   │       │
│  │  - Adapter: LoRA (safetensor format)                │       │
│  │  - Max tokens: 1024 per generation                  │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Input Flow:
User Text Input → Web Interface → JSON Payload
                → LLM API (HPC) → Action Plan JSON
                → Robot Execution (LPC) → Physical Movement
```

---

## 8. Analisis Kekuatan & Kelemahan

### **Kekuatan**:
✓ **Integrasi End-to-End**: Dari NLP ke physical robot control  
✓ **Fine-tuning Specific**: Model dioptimalkan untuk task spesifik  
✓ **Real-time Object Detection**: OpenCV untuk dynamic object tracking  
✓ **Web Interface User-Friendly**: Dual templates dengan voice support  
✓ **Modular Design**: Komponen terpisah (detection, inference, execution)  
✓ **Coordinate Calibration**: Linear interpolation untuk camera-to-robot mapping

### **Kelemahan & Improvement Opportunities**:
⚠ **Hardcoded Calibration**: `maps_to_real()` menggunakan fixed calibration points
   - Solusi: Implement dynamic calibration system

⚠ **Limited Color Detection**: Hanya 3 warna (biru, jingga, kuning)
   - Solusi: Implement more sophisticated object detection (YOLO, etc.)

⚠ **No Error Handling untuk Collision**: Robot tidak obstacle-aware
   - Solusi: Add depth sensor atau collision detection

⚠ **Single Model Instance**: API endpoint tidak load-balanced untuk concurrent requests
   - Solusi: Implement queue system atau model batching

⚠ **Fixed Camera Source**: URL camera di-hardcode
   - Solusi: Dynamic camera configuration via UI settings

⚠ **No Logging/Monitoring**: Minimal error logging untuk production use
   - Solusi: Add comprehensive logging system

⚠ **Prompt Injection Risk**: User input langsung ke LLM tanpa validation
   - Solusi: Input sanitization dan validation

⚠ **Network Dependency**: Membutuhkan ngrok untuk HPC-LPC communication
   - Solusi: Local network configuration atau VPN for production

---

## 9. Requirements & Dependencies

### **Hardware**:
- **Robot**: Dobot Magician ARM
- **LPC**: Desktop/Laptop dengan 4GB+ RAM
- **HPC**: GPU-equipped machine (NVIDIA) dengan 14GB+ VRAM
- **Camera**: Webcam atau IP camera (droidcam compatible)
- **Network**: LAN connectivity antara LPC-HPC

### **Software Dependencies**:

```
# Python Packages (via requirements.txt)
flask==2.x.x
opencv-python>=4.5.0
numpy>=1.19.0
requests>=2.25.0
pydobot>=1.2.0
unsloth>=2.x.x  # Linux/WSL only
transformers>=4.30.0
torch>=2.0.0
trl>=0.7.0
datasets>=2.10.0

# System Requirements
Python 3.8+
CUDA 11.8+ (untuk GPU inference)
```

---

## 10. Cara Penggunaan Sistem

### **Setup Awal**:
1. Fine-tune model Gemma dengan dataset menggunakan `finetuning/train.ipynb`
2. Upload LoRA adapter ke HuggingFace Hub
3. Update model name di `inference.ipynb` dan `simple-inf.ipynb`
4. Configure camera source di `app.py` (IP camera atau webcam ID)
5. Calibrate koordinat dengan `tes_koneksi.py`

### **Menjalankan Sistem**:
1. **HPC**: Jalankan inference API dengan notebook atau standalone server
2. **LPC**: Jalankan `python app.py`
3. **Browser**: Akses `http://localhost:5000` atau IP LPC
4. **User**: Masukkan prompt → Click "Jalankan Inference" → Click "Jalankan Robot"

### **Testing**:
- `tes_koneksi.py`: Test robot connectivity
- `simple-inf.ipynb`: Test model inference tanpa API
- `inference.ipynb`: Full inference testing dengan context

---

## 11. Next Steps & Recommendations

### **Immediate Improvements**:
1. Implement proper error handling dan logging
2. Add input validation untuk safety constraints
3. Create configuration file untuk tunable parameters
4. Add testing suite (unit tests)
5. Implement queue system untuk concurrent requests

### **Future Enhancements**:
1. **Advanced Object Detection**: YOLO/RCNN untuk lebih banyak objek
2. **3D Vision**: Stereo camera untuk depth estimation
3. **Path Planning**: RRT atau collision-free trajectory generation
4. **Reinforcement Learning**: Learn dari robot feedback
5. **Multi-robot Support**: Extend untuk multiple robot arms
6. **Cloud Deployment**: Containerization (Docker) + Kubernetes orchestration

---

## 12. File Structure Summary

```
Total Files: 13
├── Python Code: 3 files (app.py, dobot.py, tes_koneksi.py)
├── Notebooks: 3 files (train.ipynb, inference.ipynb, simple-inf.ipynb)
├── HTML Templates: 2 files (index.html, index2.html)
├── Documentation: 3 files (3 x README.md)
├── Images: N files (detailed flow diagrams)
└── Supporting: Configuration & settings

Total Lines of Code: ~1000 lines (excluding notebooks & templates)
```

---

**Author**: Atyaduta Putra Perkasa (5024201077)  
**Last Updated**: March 2026  
**Status**: Active Development
