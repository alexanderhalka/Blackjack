# CardCounter1.py

import pygame
import sys

class CardCounter:
    def __init__(self):
        pygame.init()
        self.WINDOW_WIDTH = 800
        self.WINDOW_HEIGHT = 600
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("Blackjack Card Counter")
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
            }
        ]
        
        self.selected_card = None
        self.selected_action = None
        self.input_mode = None
        self.message = ""
        self.message_timer = 0

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
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check card buttons
                for button in self.card_buttons:
                    if button['rect'].collidepoint(event.pos):
                        self.selected_card = button['value']
                        break
                
                # Check action buttons
                for button in self.action_buttons:
                    if button['rect'].collidepoint(event.pos):
                        if button['action'] == 'player' and self.selected_card:
                            self.player_cards.append(self.selected_card)
                            self.update_count(self.selected_card)
                            self.selected_card = None
                            self.message = f"Added {self.player_cards[-1]} to player hand"
                            self.message_timer = 90  # ~1.5 seconds at 60fps
                        
                        elif button['action'] == 'dealer' and self.selected_card:
                            self.dealer_up_card = self.selected_card
                            self.update_count(self.selected_card)
                            self.selected_card = None
                            self.message = f"Set dealer up card to {self.dealer_up_card}"
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
                        break

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
        title = self.title_font.render("Blackjack Card Counter", True, self.colors["WHITE"])
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
        
        # Draw card buttons
        for button in self.card_buttons:
            highlight = button['value'] == self.selected_card
            self.draw_button(button['rect'], button['value'], highlight=highlight)
        
        # Draw action buttons
        for button in self.action_buttons:
            self.draw_button(button['rect'], button['text'], self.colors["LIGHT_BLUE"])
        
        # Draw control buttons
        for button in self.control_buttons:
            self.draw_button(button['rect'], button['text'], self.colors["GRAY"])
        
        # Draw message
        if self.message_timer > 0:
            message_text = self.small_font.render(self.message, True, self.colors["YELLOW"])
            self.screen.blit(message_text, message_text.get_rect(center=(self.WINDOW_WIDTH/2, 560)))
            self.message_timer -= 1
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    counter = CardCounter()
    counter.run()