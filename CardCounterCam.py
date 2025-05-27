import pygame
import sys
import cv2
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
import time
import threading
import re

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("Please set your OpenAI API key in the .env file as OPENAI_API_KEY=your-key")

def encode_image_to_base64(image):
    # Convert PIL Image to base64 with JPEG compression (quality 80)
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=80)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

class CardCounterCam:
    def __init__(self):
        # Initialize pygame for GUI
        pygame.init()
        self.WINDOW_WIDTH = 1000  # Increased width to accommodate camera feed
        self.WINDOW_HEIGHT = 700  # Increased height to accommodate camera feed
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("Blackjack Card Counter with Camera")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Colors
        self.colors = {
            "WHITE": (255, 255, 255),
            "BLACK": (0, 0, 0),
            "GREEN": (0, 128, 0),
            "RED": (255, 0, 0),
            "YELLOW": (255, 255, 0),
            "GRAY": (200, 200, 200),
            "LIGHT_BLUE": (173, 216, 230)
        }
        
        # Fonts
        self.title_font = pygame.font.Font(None, 48)
        self.normal_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        
        # Game state
        self.player_cards = []
        self.dealer_up_card = None
        self.running_count = 0
        self.true_count = 0
        self.num_decks = 6  # Standard shoe size
        self.decks_remaining = 6.0
        
        # Card values for Hi-Lo counting system
        self.count_values = {
            '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
            '7': 0, '8': 0, '9': 0,
            '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
        }
        
        # Button definitions
        self.card_buttons = []
        cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        button_width = 50
        button_height = 50
        button_gap = 10
        start_x = (self.WINDOW_WIDTH - (button_width * len(cards) + button_gap * (len(cards) - 1))) // 2
        
        for i, card in enumerate(cards):
            x = start_x + i * (button_width + button_gap)
            y = 400
            self.card_buttons.append({
                'rect': pygame.Rect(x, y, button_width, button_height),
                'value': card
            })
        
        # Action buttons
        button_width = 150
        button_height = 40
        self.action_buttons = [
            {
                'rect': pygame.Rect(150, 480, button_width, button_height),
                'text': 'Add Player Card',
                'action': 'player'
            },
            {
                'rect': pygame.Rect(325, 480, button_width, button_height),
                'text': 'Set Dealer Card',
                'action': 'dealer'
            },
            {
                'rect': pygame.Rect(500, 480, button_width, button_height),
                'text': 'New Hand',
                'action': 'reset'
            }
        ]
        
        # Control buttons
        button_width = 120
        button_height = 30
        self.control_buttons = [
            {
                'rect': pygame.Rect(50, 530, button_width, button_height),
                'text': 'Adjust Decks',
                'action': 'adjust_decks'
            },
            {
                'rect': pygame.Rect(180, 530, button_width, button_height),
                'text': 'Reset Count',
                'action': 'reset_count'
            },
            {
                'rect': pygame.Rect(310, 530, button_width, button_height),
                'text': 'Toggle Camera',
                'action': 'toggle_camera'
            }
        ]
        
        self.selected_card = None
        self.selected_action = None
        self.input_mode = None
        self.message = ""
        self.message_timer = 0
        
        # Camera-related attributes
        self.camera_enabled = False
        self.camera_thread = None
        self.camera_running = False
        self.camera_surface = None
        self.detected_card = None
        self.last_detected_card = None
        self.detection_confidence = "No detection"
        self.detection_confirmed = False  # Flag to track if detection is confirmed
        self.detection_stability_count = 0  # Counter for stable detections
        self.last_detection_time = 0  # Time of last detection
        self.detection_cooldown = 1.0  # Cooldown period in seconds
        self.fps = 0  # Store FPS for display
        self.api_processing = False  # Flag to prevent multiple API calls at once
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)

    def calculate_hand_value(self, cards):
        value = 0
        aces = 0
        
        for card in cards:
            if card in ['J', 'Q', 'K']:
                value += 10
            elif card == 'A':
                aces += 1
            else:
                value += int(card)
        
        # Add aces
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
                
        return value

    def get_recommendation(self):
        if not self.player_cards or not self.dealer_up_card:
            return "Need player and dealer cards"
            
        player_value = self.calculate_hand_value(self.player_cards)
        
        if self.dealer_up_card in ['J', 'Q', 'K']:
            dealer_value = 10
        elif self.dealer_up_card == 'A':
            dealer_value = 11
        else:
            dealer_value = int(self.dealer_up_card)
        
        # Basic strategy with count considerations
        if player_value <= 8:
            return "Hit"
        elif player_value == 9:
            if dealer_value in [3,4,5,6] and self.true_count >= 1:
                return "Double Down"
            return "Hit"
        elif player_value == 10:
            if dealer_value <= 9:
                return "Double Down"
            return "Hit"
        elif player_value == 11:
            return "Double Down"
        elif player_value == 12:
            if dealer_value in [4,5,6]:
                return "Stand"
            return "Hit"
        elif 13 <= player_value <= 16:
            if dealer_value <= 6:
                return "Stand"
            return "Hit"
        else:  # 17 or higher
            return "Stand"

    def update_count(self, card):
        if card in self.count_values:
            self.running_count += self.count_values[card]
            self.true_count = self.running_count / self.decks_remaining

    def parse_card_from_response(self, response_text):
        """Extract card value from the API response"""
        if "no card" in response_text.lower():
            return None, "No card detected"
            
        try:
            # Try to match standard patterns like "7 of hearts" or "King of spades"
            match = re.search(r'(\d+|[JQKA])[^\w]+(of)[^\w]+(hearts|diamonds|clubs|spades)', response_text.lower())
            if match:
                value = match.group(1)
                suit = match.group(3)
                if value.lower() == 'j':
                    value = 'J'
                elif value.lower() == 'q':
                    value = 'Q'
                elif value.lower() == 'k':
                    value = 'K'
                elif value.lower() == 'a':
                    value = 'A'
                return value, f"{value} of {suit}"
            else:
                # If we don't find a perfect match but the response contains a valid card value
                for value in ['10', 'J', 'Q', 'K', 'A', '2', '3', '4', '5', '6', '7', '8', '9']:  # Check 10 first to avoid matching in "10" in other numbers
                    if value.lower() in response_text.lower():
                        return value, f"Detected: {response_text}"
                
                return None, f"Unrecognized: {response_text}"
        except Exception as e:
            return None, f"Error: {str(e)}"

    def camera_function(self):
        """Process camera feed and detect cards"""
        # Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.message = "Failed to open camera"
            self.message_timer = 180
            self.camera_running = False
            return
            
        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for real-time processing
            
        # Initialize variables
        frame_count = 0
        start_time = time.time()
        last_sent_time = 0
        send_interval = 1.0  # Seconds between API calls
        last_detection = None
        detection_count = 0
        
        # Start API processing thread
        api_thread = None
        
        self.camera_running = True
        while self.camera_running:
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                break
                
            # Calculate FPS
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time >= 1.0:
                self.fps = frame_count / elapsed_time
                frame_count = 0
                start_time = time.time()
                
            # Resize frame for display (smaller for better performance)
            resized_frame = cv2.resize(frame, (320, 240))
            
            # Convert frame for pygame display
            pygame_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            # Rotate 90 degrees clockwise to match display orientation
            pygame_frame = np.rot90(pygame_frame, k=1)
            self.camera_surface = pygame.surfarray.make_surface(pygame_frame)
            
            # Process for card detection in a separate thread to avoid blocking the main loop
            current_time = time.time()
            if current_time - last_sent_time >= send_interval and not self.api_processing:
                self.api_processing = True
                last_sent_time = current_time
                
                # Make a copy of the frame for the API thread
                api_frame = frame.copy()
                
                # Process in a separate thread
                def process_frame(frame):
                    try:
                        # Prepare image for API - use lower resolution for faster processing
                        small_frame = cv2.resize(frame, (320, 240))
                        pil_image = Image.fromarray(cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB))
                        base64_image = encode_image_to_base64(pil_image)
                        
                        # Call OpenAI Vision API
                        response = self.client.chat.completions.create(
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
                                                "url": f"data:image/jpeg;base64,{base64_image}"
                                            }
                                        }
                                    ]
                                }
                            ],
                            max_tokens=20
                        )
                        
                        # Parse response
                        text = response.choices[0].message.content.strip()
                        card_value, confidence_text = self.parse_card_from_response(text)
                        
                        # Implement detection stability check
                        nonlocal last_detection, detection_count
                        if card_value == last_detection:
                            detection_count += 1
                        else:
                            detection_count = 1
                            last_detection = card_value
                        
                        # Only update detection if we have consistent readings or clear "no card"
                        if detection_count >= 2 or card_value is None:
                            self.detected_card = card_value
                            self.detection_confidence = confidence_text
                            
                            # Set detection confirmed flag if we have a valid card
                            if card_value is not None:
                                self.detection_confirmed = True
                                self.last_detection_time = time.time()
                    
                    except Exception as e:
                        self.detection_confidence = f"Error: {str(e)}"
                    
                    finally:
                        self.api_processing = False
                
                # Start the processing thread
                api_thread = threading.Thread(target=process_frame, args=(api_frame,))
                api_thread.daemon = True
                api_thread.start()
            
            # Brief sleep to yield CPU time and improve responsiveness
            time.sleep(0.001)
                    
        # Release camera
        cap.release()
        
        # Wait for API thread to complete if it's running
        if api_thread and api_thread.is_alive():
            api_thread.join(timeout=0.5)

    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.camera_enabled:
            # Turn off camera
            self.camera_enabled = False
            self.camera_running = False
            if self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=1.0)
            self.message = "Camera disabled"
            self.message_timer = 90
        else:
            # Turn on camera
            self.camera_enabled = True
            self.camera_thread = threading.Thread(target=self.camera_function)
            self.camera_thread.daemon = True  # Thread will close when main program exits
            self.camera_thread.start()
            self.message = "Camera enabled"
            self.message_timer = 90

    def handle_detected_card(self):
        """Process detected card from camera if available"""
        # Skip if no detection or same as last processed card
        if not self.detected_card or not self.detection_confirmed:
            return
            
        # Reset confirmation flag
        self.detection_confirmed = False
        
        # Store the card we're about to process
        current_card = self.detected_card
        self.last_detected_card = current_card
        
        # Add card based on selected action
        if self.input_mode == 'player':
            self.player_cards.append(current_card)
            self.update_count(current_card)
            self.message = f"Added {current_card} to player hand"
            self.message_timer = 90
        elif self.input_mode == 'dealer':
            # For dealer, replace the current card
            self.dealer_up_card = current_card
            self.update_count(current_card)
            self.message = f"Set dealer up card to {current_card}"
            self.message_timer = 90
        else:
            # Default to adding to player hand if no mode selected
            self.message = f"Detected {current_card}. Select 'Add Player Card' or 'Set Dealer Card'"
            self.message_timer = 120

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.running = False
                elif event.key == pygame.K_UP:
                    self.decks_remaining = min(8, self.decks_remaining + 0.5)
                    self.true_count = self.running_count / self.decks_remaining
                elif event.key == pygame.K_DOWN:
                    self.decks_remaining = max(0.5, self.decks_remaining - 0.5)
                    self.true_count = self.running_count / self.decks_remaining
                elif event.key == pygame.K_c:
                    self.toggle_camera()
                elif event.key == pygame.K_p and self.detected_card and self.detection_confirmed:
                    # Shortcut to add detected card to player hand
                    self.input_mode = 'player'
                    self.handle_detected_card()
                elif event.key == pygame.K_d and self.detected_card and self.detection_confirmed:
                    # Shortcut to set detected card as dealer card
                    self.input_mode = 'dealer'
                    self.handle_detected_card()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check card buttons
                for button in self.card_buttons:
                    if button['rect'].collidepoint(event.pos):
                        self.selected_card = button['value']
                        break
                
                # Check action buttons
                for button in self.action_buttons:
                    if button['rect'].collidepoint(event.pos):
                        if button['action'] == 'player':
                            if self.selected_card:
                                self.player_cards.append(self.selected_card)
                                self.update_count(self.selected_card)
                                self.message = f"Added {self.selected_card} to player hand"
                                self.message_timer = 90
                                self.selected_card = None
                            else:
                                self.input_mode = 'player'
                                self.message = "Using camera to add player card"
                                self.message_timer = 90
                        
                        elif button['action'] == 'dealer':
                            if self.selected_card:
                                self.dealer_up_card = self.selected_card
                                self.update_count(self.selected_card)
                                self.message = f"Set dealer up card to {self.selected_card}"
                                self.message_timer = 90
                                self.selected_card = None
                            else:
                                self.input_mode = 'dealer'
                                self.message = "Using camera to set dealer card"
                                self.message_timer = 90
                        
                        elif button['action'] == 'reset':
                            self.player_cards = []
                            self.dealer_up_card = None
                            self.message = "Started new hand"
                            self.message_timer = 90
                        break
                
                # Check control buttons
                for button in self.control_buttons:
                    if button['rect'].collidepoint(event.pos):
                        if button['action'] == 'adjust_decks':
                            self.decks_remaining = max(0.5, min(8, self.decks_remaining - 0.5))
                            if self.decks_remaining == 0.5:
                                self.decks_remaining = 8.0  # Cycle back to 8
                            self.true_count = self.running_count / self.decks_remaining
                            self.message = f"Decks remaining: {self.decks_remaining}"
                            self.message_timer = 90
                        
                        elif button['action'] == 'reset_count':
                            self.running_count = 0
                            self.true_count = 0
                            self.decks_remaining = 6.0
                            self.message = "Reset count to 0"
                            self.message_timer = 90
                            
                        elif button['action'] == 'toggle_camera':
                            self.toggle_camera()
                        break
        
        # Process detected card with cooldown to prevent accidental additions
        current_time = time.time()
        if self.camera_enabled and self.detected_card and self.detection_confirmed and \
           (current_time - self.last_detection_time) > self.detection_cooldown:
            self.handle_detected_card()

    def draw_button(self, rect, text, color=None, text_color=None, highlight=False):
        if color is None:
            color = self.colors["GRAY"]
        
        if text_color is None:
            text_color = self.colors["BLACK"]
        
        if highlight:
            pygame.draw.rect(self.screen, self.colors["YELLOW"], rect)
        else:
            pygame.draw.rect(self.screen, color, rect)
        
        pygame.draw.rect(self.screen, self.colors["BLACK"], rect, 2)  # Border
        
        text_surf = self.small_font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def draw(self):
        self.screen.fill(self.colors["GREEN"])
        
        # Draw title
        title = self.title_font.render("Blackjack Card Counter with Camera", True, self.colors["WHITE"])
        self.screen.blit(title, title.get_rect(center=(self.WINDOW_WIDTH/2, 50)))
        
        # Draw counts
        running_count_text = self.normal_font.render(f"Running Count: {self.running_count}", True, self.colors["WHITE"])
        true_count_text = self.normal_font.render(f"True Count: {self.true_count:.1f}", True, self.colors["WHITE"])
        decks_text = self.normal_font.render(f"Decks Remaining: {self.decks_remaining:.1f}", True, self.colors["WHITE"])
        self.screen.blit(running_count_text, (50, 100))
        self.screen.blit(true_count_text, (50, 140))
        self.screen.blit(decks_text, (50, 180))
        
        # Draw player and dealer cards
        player_text = self.normal_font.render("Player Cards:", True, self.colors["WHITE"])
        self.screen.blit(player_text, (50, 230))
        
        if self.player_cards:
            player_cards_text = self.normal_font.render(", ".join(self.player_cards), True, self.colors["LIGHT_BLUE"])
            self.screen.blit(player_cards_text, (250, 230))
            player_value = self.calculate_hand_value(self.player_cards)
            player_value_text = self.normal_font.render(f"Value: {player_value}", True, self.colors["LIGHT_BLUE"])
            self.screen.blit(player_value_text, (500, 230))
        
        dealer_text = self.normal_font.render("Dealer Up Card:", True, self.colors["WHITE"])
        self.screen.blit(dealer_text, (50, 270))
        
        if self.dealer_up_card:
            dealer_card_text = self.normal_font.render(self.dealer_up_card, True, self.colors["LIGHT_BLUE"])
            self.screen.blit(dealer_card_text, (250, 270))
        
        # Draw recommendation
        recommendation = self.get_recommendation()
        rec_color = self.colors["RED"] if recommendation != "Need player and dealer cards" else self.colors["WHITE"]
        rec_text = self.title_font.render(f"Recommendation: {recommendation}", True, rec_color)
        self.screen.blit(rec_text, rec_text.get_rect(center=(self.WINDOW_WIDTH/2, 330)))
        
        # Draw camera feed and status
        if self.camera_enabled and self.camera_surface:
            # Draw camera feed on the right side (no flip, already rotated correctly)
            self.screen.blit(self.camera_surface, (650, 100))
            
            # Draw FPS text using Pygame (top-left of camera feed)
            fps_text = self.small_font.render(f"FPS: {self.fps:.1f}", True, self.colors["GREEN"])
            self.screen.blit(fps_text, (650 + 10, 100 + 10))
            
            # Draw a border around the camera feed
            pygame.draw.rect(self.screen, self.colors["WHITE"], (650, 100, 320, 240), 2)
            
            # Display detected card
            card_text = self.normal_font.render("Card Detection:", True, self.colors["WHITE"])
            self.screen.blit(card_text, (650, 350))
            
            detection_text = self.normal_font.render(self.detection_confidence, True, self.colors["YELLOW"])
            self.screen.blit(detection_text, (650, 390))
            
            # Show input mode, confirmation status and FPS
            mode_text = self.small_font.render(
                f"Mode: {'Player Card' if self.input_mode == 'player' else 'Dealer Card' if self.input_mode == 'dealer' else 'None'} | " +
                f"Confirmed: {'Yes' if self.detection_confirmed else 'No'}", 
                True, self.colors["LIGHT_BLUE"]
            )
            self.screen.blit(mode_text, (650, 430))
        else:
            # Display camera status
            camera_status = self.normal_font.render("Camera: Disabled", True, self.colors["WHITE"])
            self.screen.blit(camera_status, (650, 150))
            camera_help = self.small_font.render("Press 'C' or click 'Toggle Camera'", True, self.colors["LIGHT_BLUE"])
            self.screen.blit(camera_help, (650, 190))
            
        # Draw card buttons
        for button in self.card_buttons:
            highlight = button['value'] == self.selected_card
            self.draw_button(button['rect'], button['value'], highlight=highlight)
        
        # Draw action buttons
        for button in self.action_buttons:
            highlight = (button['action'] == 'player' and self.input_mode == 'player') or \
                        (button['action'] == 'dealer' and self.input_mode == 'dealer')
            self.draw_button(button['rect'], button['text'], self.colors["LIGHT_BLUE"], highlight=highlight)
        
        # Draw control buttons
        for button in self.control_buttons:
            highlight = button['action'] == 'toggle_camera' and self.camera_enabled
            self.draw_button(button['rect'], button['text'], self.colors["GRAY"], highlight=highlight)
        
        # Draw message
        if self.message_timer > 0:
            message_text = self.small_font.render(self.message, True, self.colors["YELLOW"])
            self.screen.blit(message_text, message_text.get_rect(center=(self.WINDOW_WIDTH/2, 580)))
            self.message_timer -= 1
        
        # Draw shortcuts help
        shortcuts_text = self.small_font.render("Shortcuts: C=Toggle Camera, P=Add Player Card, D=Set Dealer Card, Q=Quit", True, self.colors["WHITE"])
        self.screen.blit(shortcuts_text, (self.WINDOW_WIDTH/2 - 300, 610))
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(60)
        
        # Cleanup
        self.camera_running = False
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=1.0)
        
        pygame.quit()

if __name__ == "__main__":
    counter = CardCounterCam()
    counter.run() 