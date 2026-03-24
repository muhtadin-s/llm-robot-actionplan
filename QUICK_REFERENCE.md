# Quick Reference Guide - Analisis Proyek

## 📋 Project Overview

**Nama**: Interaksi Manusia-Robot Berbasis LLM untuk Pembangkitan Action Plan pada Robot Lengan  
**Author**: Atyaduta Putra Perkasa (5024201077)  
**Type**: Tugas Akhir / Skripsi  
**Status**: Active Development  
**Last Updated**: March 2026

---

## 🎯 Project Goals

1. **Fine-tune LLM** (Gemma 2B) untuk generate JSON Action Plan robot-specific
2. **Build Web Interface** untuk user input natural language commands
3. **Real-time Object Detection** menggunakan OpenCV dan camera calibration
4. **Execute Actions** pada robot arm (Dobot Magician) secara real-time

---

## 🏗️ Architecture at a Glance

```
User → Web UI → LLM Inference → Action Plan → Robot Execution → Physical Movement
        ↓            ↓              ↓              ↓
       LPC          HPC            JSON          Serial COM3
   (Web Server)  (GPU Server)    (Actions)    (Robot ARM)
```

---

## 📁 File Structure

| File | Purpose | Lines | Language |
|------|---------|-------|----------|
| `app.py` | Flask web server + robot control | 276 | Python |
| `dobot.py` | Robot communication driver | 370 | Python |
| `tes_koneksi.py` | Robot connectivity test | 20 | Python |
| `inference.ipynb` | Full LLM inference notebook | 142 | Jupyter |
| `simple-inf.ipynb` | Simple inference notebook | 106 | Jupyter |
| `train.ipynb` | Model fine-tuning notebook | 7 cells | Jupyter |
| `index.html` | Main web interface | 167 | HTML/CSS/JS |
| `index2.html` | Alternative web UI | 220 | HTML/CSS/JS |

---

## 🔧 Technology Stack

### Backend
- **Framework**: Flask (Python web framework)
- **Robot Control**: pydobot (serial communication)
- **Computer Vision**: OpenCV (image processing)
- **API Client**: requests (HTTP)
- **Data**: JSON

### Frontend
- **Template**: HTML5
- **Styling**: Tailwind CSS v3
- **Scripts**: Vanilla JavaScript
- **Voice**: Web Speech API (Indonesian)

### ML/AI
- **Base Model**: Google Gemma 2B
- **Training**: Unsloth + TRL (SFTTrainer)
- **Fine-tuning Method**: LoRA (Low Rank Adaptation)
- **Inference**: FastLanguageModel (Unsloth)

### Hardware
- **Robot**: Dobot Magician
- **Connection**: Serial (COM3, 115200 baud)
- **Camera**: Webcam/IP Camera
- **HPC**: GPU Server (14GB VRAM for inference)

---

## 🚀 Quick Start

### Setup
1. **Install dependencies**
   ```bash
   pip install flask opencv-python numpy requests pydobot torch transformers unsloth
   ```

2. **Configure robot connection**
   - Edit `app.py`: Change `port="COM3"` if needed
   - Test with: `python tes_koneksi.py`

3. **Configure camera**
   - Edit `app.py`: Change `cv2.VideoCapture(5)` to your camera (0 for default)
   - Adjust rotation if needed

4. **Calibrate coordinates**
   - Run calibration using `tes_koneksi.py`
   - Update `maps_to_real()` values in `app.py`

### Running
1. **Option A: Two Computer Setup (Recommended)**
   - HPC: Run `inference.ipynb` to start LLM API server
   - LPC: Run `python app.py`
   - Browser: Visit `http://localhost:5000`

2. **Option B: Single Computer Setup**
   - Run `python app.py`
   - Update ngrok URL if needed

---

## 🎮 How to Use

### Step 1: Input Command
- Type natural language command: "pindahkan balok biru ke depan"
- Or use voice button (Indonesian language)

### Step 2: Run Inference
- Click "Jalankan Inference" button
- LLM processes command + detected objects
- Returns JSON action plan

### Step 3: Execute Robot
- Review action plan in results panel
- Click "Jalankan robot" button
- Robot executes movement sequence

---

## 📊 Data Flow

```
INPUT: "pindahkan balok biru ke depan"
       + Detected: [("biru", (152.76, 158.92)), ...]

    ↓ (Prompt + Context)

LLM GENERATION:
{
  "actions": [
    {"command": "move_to", "parameters": {"x": 152.76, "y": 158.92, "z": 6}},
    {"command": "suction_cup", "parameters": {"action": "on"}},
    {"command": "move", "parameters": {"direction": "depan"}},
    {"command": "suction_cup", "parameters": {"action": "off"}}
  ]
}

    ↓ (Execution)

ROBOT MOVEMENT:
1. Move to blue block location
2. Activate suction cup
3. Move forward (depan = x+40)
4. Deactivate suction cup
5. Return to home position
```

---

## 🔑 Key Components Explained

### 1. Object Detection (`detect_blocks()`)
- **Input**: Video frame
- **Process**: HSV color filtering → contour detection → coordinate conversion
- **Output**: List of detected objects with real-world coordinates
- **Performance**: ~5-10ms per frame

### 2. Coordinate Calibration (`maps_to_real()`)
- **Problem**: Camera coordinates ≠ robot coordinates
- **Solution**: Linear interpolation using 2 calibration points
- **Formula**: Simple linear transformation (affine)

### 3. LLM Inference
- **Model**: Gemma 2B + LoRA adapter
- **Input Format**: Alpaca (instruction, input, output)
- **Output**: JSON action plan
- **Speed**: 2-5 seconds per request

### 4. Robot Execution (`RobotExecute2()`)
- **Input**: JSON action array
- **Commands**: move, move_to, suction_cup, err_msg
- **Communication**: Serial protocol (COBS encoded)
- **Sync**: Command queueing with completion checking

---

## ⚙️ Configuration Points

### Camera Settings
```python
# app.py line ~210
cap = cv2.VideoCapture(5)  # Change to 0 for default camera
frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)  # Remove if not needed
```

### Calibration Coordinates
```python
# app.py line ~17-24
maps_coordinates = {
    'top_left': (270, 132),      # Camera coords
    'bottom_right': (142, 338)
}
real_coordinates = {
    'top_left': (294, 122),       # Robot coords
    'bottom_right': (160, -124)
}
```

### Color Detection Ranges
```python
# app.py line ~50-59
lower_blue = np.array([100, 50, 100])   # H, S, V lower bounds
upper_blue = np.array([140, 255, 255])  # H, S, V upper bounds
# Repeat for jingga (orange) and kuning (yellow)
```

### Robot Connection
```python
# app.py line ~177
device = pydobot.Dobot(port="COM3", verbose=False)
```

### API Endpoint
```python
# app.py line ~263
response = requests.get('https://412c-...ngrok-free.app/api', ...)
```

---

## 📈 Performance Metrics

| Metric | Value | Bottleneck |
|--------|-------|-----------|
| Object Detection | 5-10ms | ✓ Fast |
| LLM Inference | 2-5s | Network latency |
| Robot Execution | Variable | Physics movement |
| End-to-End | 5-10s | LLM inference |

**Optimization Tips**:
- Reduce LLM max_tokens (currently 1024)
- Cache model in memory
- Use frame skipping for detection
- Parallel processing for multiple commands

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| Camera not detected | Wrong camera ID | Change `cv2.VideoCapture()` ID |
| Robot not responding | Serial port wrong | Update `port="COM3"` |
| Objects not detected | Lighting/colors | Recalibrate HSV ranges |
| LLM timeout | Network issue | Check ngrok connection |
| Coordinates off | Calibration wrong | Re-run `tes_koneksi.py` |
| Suction not working | Parameter wrong | Check action JSON format |

---

## ✅ Quality Checklist

### Strengths ✓
- End-to-end LLM-to-robot pipeline
- Real-time object detection
- Web interface with voice input
- Modular code structure
- Good documentation

### Weaknesses ⚠
- Hardcoded configuration values
- Limited error handling
- Single threaded API calls
- No input validation
- Manual calibration needed
- Security concerns (hardcoded URLs)

### Improvement Priority
1. Move config to file (HIGH)
2. Add error handling (HIGH)
3. Add input validation (HIGH)
4. Implement tests (MEDIUM)
5. Add logging (MEDIUM)
6. Optimize performance (LOW)

---

## 📚 Dataset Format (Alpaca)

```json
{
  "instruction": "Objektif: Tugas anda adalah menghasilkan urutan respons JSON...",
  "input": "pindahkan balok biru ke depan",
  "output": "{\"actions\": [{\"command\": \"move_to\", ...}]}"
}
```

**Training**:
- Dataset: Hugging Face (Aryaduta/test-data2)
- Model: Gemma 2B
- Method: LoRA fine-tuning
- Epochs: 3
- Batch size: Customizable

---

## 🔗 External Links

- **Dobot Robot**: https://www.dobot.cc/
- **Unsloth**: https://github.com/unslothai/unsloth
- **Gemma Model**: https://huggingface.co/google/gemma-2b
- **Dataset**: https://huggingface.co/datasets/Aryaduta/test-data2
- **Fine-tuned Model**: https://huggingface.co/Aryaduta/modellora9

---

## 📝 Notes & Best Practices

### Development
- Always test on hardware before deploying
- Keep detailed logs of calibration results
- Document all hardcoded values
- Use version control for tracking changes

### Production
- Move to cloud/local network (not ngrok)
- Implement proper authentication
- Add health checks for all services
- Monitor GPU/CPU usage on HPC
- Set up automated backups

### Debugging
- Enable verbose mode on robot
- Check serial logs with Terminal/Putty
- Test object detection with cv2.imshow()
- Validate JSON output with jq/online validator

---

## 🎓 Project Outcomes

This project demonstrates:
- **NLP Integration**: Converting natural language to structured actions
- **Computer Vision**: Real-time object detection and tracking
- **Robotics Control**: Low-level hardware communication
- **Web Development**: Full-stack web application
- **ML Engineering**: Model fine-tuning and deployment
- **Systems Integration**: End-to-end pipeline architecture

---

## 📞 Contact & Support

**Author**: Atyaduta Putra Perkasa  
**ID**: 5024201077  
**Email**: [Your email]  
**GitHub**: [Your github]

---

## 📄 Documentation Files Generated

This analysis includes:
1. **ANALISIS_KODE.md** - Comprehensive code analysis
2. **DIAGRAM_VISUALISASI.md** - System diagrams and visualizations
3. **CODE_REVIEW_REKOMENDASI.md** - Technical review with recommendations
4. **QUICK_REFERENCE.md** - This document

---

## 🔄 Update Log

- **v1.0** (March 2026): Initial analysis and documentation

---

**Status**: ✅ Complete  
**Last Review**: March 24, 2026

---

*Untuk informasi lebih detail, lihat file dokumentasi lengkap di folder proyek.*
