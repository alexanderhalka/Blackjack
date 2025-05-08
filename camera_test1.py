import cv2
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("Please set your OpenAI API key in the .env file as OPENAI_API_KEY=your-key")

def encode_image_to_base64(image):
    # Convert PIL Image to base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_webcam():
    # Initialize OpenAI client with API key
    client = OpenAI(api_key=api_key)
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        # Convert frame to PIL Image
        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        try:
            # Encode image to base64
            base64_image = encode_image_to_base64(pil_image)
            
            # Call OpenAI Vision API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Look at this image and identify if there is a playing card visible. If there is a card, respond with the card's value (2-10, J, Q, K, A) and suit (hearts, diamonds, clubs, spades) in the format 'value of suit' (e.g., '7 of hearts' or 'King of spades'). If no card is clearly visible, respond with 'No card detected'."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=20
            )
            
            # Get the response
            text = response.choices[0].message.content.strip()
            print(f"Detected: {text}")
                
        except Exception as e:
            print("Error in OpenAI API call:", str(e))
            
        # Display the frame
        cv2.imshow('Webcam Feed', frame)
        
        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release everything when job is finished
    cap.release()
    cv2.destroyAllWindows()

# Start the webcam analysis
analyze_webcam()
