import cv2
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("Please set your OpenAI API key in the .env file as OPENAI_API_KEY=your-key")

# Card counting values (Hi-Lo system)
CARD_VALUES = {
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
    '7': 0, '8': 0, '9': 0,
    '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
}

class CardCounter:
    def __init__(self):
        self.running_count = 0
        self.decks_remaining = 6  # Assuming 6-deck shoe
        self.last_card = None
        self.last_count_update = 0
    
    def update_count(self, card_value):
        if card_value in CARD_VALUES:
            self.running_count += CARD_VALUES[card_value]
            self.last_card = card_value
            self.last_count_update = time.time()
    
    def get_true_count(self):
        return self.running_count / self.decks_remaining
    
    def reset_count(self):
        self.running_count = 0
        self.last_card = None

def encode_image_to_base64(image):
    # Convert PIL Image to base64 with JPEG compression (quality 80)
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=80)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_webcam():
    # Initialize OpenAI client with API key
    client = OpenAI(api_key=api_key)
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    # Initialize FPS calculation variables
    fps = 0
    frame_count = 0
    start_time = time.time()
    
    # Initialize card counter
    counter = CardCounter()
    
    # Timer for sending frames every 2 seconds
    last_sent_time = 0
    send_interval = 2.0  # seconds
    
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        # Calculate FPS
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:  # Update FPS every second
            fps = frame_count / elapsed_time
            frame_count = 0
            start_time = time.time()
            
        # Resize frame to 480x360 for better detail
        small_frame = cv2.resize(frame, (480, 360))
        pil_image = Image.fromarray(cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB))
        
        # Send frame every 2 seconds
        current_time = time.time()
        if current_time - last_sent_time >= send_interval:
            try:
                # Encode image to base64 (JPEG)
                base64_image = encode_image_to_base64(pil_image)
                
                # Call OpenAI Vision API
                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": "Look at this image and identify if there is a playing card visible. If there is a card, respond with ONLY the card's value (2-10, J, Q, K, A) and suit (hearts, diamonds, clubs, spades) in the format 'value of suit' (e.g., '7 of hearts' or 'King of spades'). If no card is clearly visible, respond with 'No card detected'."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=20
                )
                
                # Get the response and update count
                text = response.choices[0].message.content.strip()
                if text != 'No card detected':
                    # Extract just the value from the response
                    value = text.split()[0]
                    counter.update_count(value)
                print(f"Detected: {text}")
                last_sent_time = current_time
                    
            except Exception as e:
                print("Error in OpenAI API call:", str(e))
        
        # Add information to the frame
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Running Count: {counter.running_count}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"True Count: {counter.get_true_count():.1f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if counter.last_card:
            cv2.putText(frame, f"Last Card: {counter.last_card}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
        # Display the frame
        cv2.imshow('Blackjack Card Counter', frame)
        
        # Break the loop on 'q' or 'ESC' key press, reset count on 'r'
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # 27 is the ESC key
            break
        elif key == ord('r'):  # Reset count
            counter.reset_count()
    
    # Release everything when job is finished
    cap.release()
    cv2.destroyAllWindows()

# Start the webcam analysis
analyze_webcam()
