# Blackjack Card Counter

A Python application that helps players count cards in Blackjack using the Hi-Lo counting system. The application includes both a GUI interface and a webcam-based card detection system.

## Features

- Interactive GUI for manual card counting
- Real-time running count and true count calculation
- Basic strategy recommendations
- Webcam-based card detection (experimental)
- Support for multiple deck configurations

## Requirements

- Python 3.x
- Pygame
- OpenCV
- NumPy
- Pytesseract
- Pillow
- OpenAI API key (for webcam detection)

## Installation

1. Clone the repository:
```bash
git clone [your-repo-url]
cd CardCounter
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### GUI Card Counter
Run the GUI version:
```bash
python CardCounter1.py
```

### Webcam Card Detection
Run the webcam detection version:
```bash
python camera_test1.py
```

### Integrated Card Counter with Camera 
Run the integrated version with camera detection:
```bash
python CardCounterCam.py
```

## Controls

- Use mouse to select cards and actions in the GUI
- Press 'q' to quit the webcam detection
- Use arrow keys to adjust deck count in GUI
- Click "New Hand" to reset the current hand
- Click "Reset Count" to reset the running count

### Additional Controls for Integrated Version
- Press 'C' to toggle camera on/off
- Press 'P' to add the detected card to player hand
- Press 'D' to set the detected card as dealer card
- Click "Toggle Camera" to enable/disable the webcam

## License

MIT License 