import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_webcam():
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to preprocess the image
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Convert the image to PIL format
        pil_image = Image.fromarray(thresh)
        
        try:
            # Use pytesseract to do OCR on the image
            text = pytesseract.image_to_string(pil_image, config='--psm 6 digits')
            
            # Clean up the detected text
            text = text.strip()
            
            if text and text.isdigit():
                print(f"Detected number: {text}")
            else:
                print("No Number")
                
        except Exception as e:
            print("Error in OCR:", str(e))
            
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
