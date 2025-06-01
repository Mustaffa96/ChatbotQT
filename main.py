import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea,
    QSizePolicy, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QResizeEvent, QIcon

load_dotenv()

class APIKeyManager:
    @staticmethod
    def get_cache_file():
        # Store in user's home directory to ensure write permissions
        home = str(Path.home())
        cache_dir = os.path.join(home, '.chatbotqt')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        return os.path.join(cache_dir, 'api_key.cache')
    
    @staticmethod
    def get_cached_key():
        try:
            cache_file = APIKeyManager.get_cache_file()
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error reading cache: {e}")
        return None
    
    @staticmethod
    def save_key(key):
        if not key or len(key.strip()) < 10:  # Basic validation
            return False
            
        try:
            cache_file = APIKeyManager.get_cache_file()
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w') as f:
                f.write(key)
            print(f"API key saved to: {cache_file}")
            return True
        except Exception as e:
            print(f"Error saving cache: {e}")
            return False
            
    @staticmethod
    def clear_key():
        try:
            cache_file = APIKeyManager.get_cache_file()
            if os.path.exists(cache_file):
                os.remove(cache_file)
                return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
        return False

class MessageBubble(QWidget):
    def __init__(self, message, is_user=True, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Create message bubble
        self.bubble = QTextEdit()
        self.bubble.setReadOnly(True)
        self.bubble.setFont(QFont('Arial', 10))
        self.bubble.setText(message)
        self.bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Style the bubble
        self.bubble.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {'#DCF8C6' if is_user else '#FFFFFF'};
                border-radius: 10px;
                padding: 10px;
                margin: {'0px 10px 0px 50px' if is_user else '0px 50px 0px 10px'};
            }}
            """
        )
        
        # Set size policies for dynamic resizing
        self.bubble.setMinimumWidth(50)
        self.bubble.setMaximumWidth(int(self.window().width() * 0.6) if self.window() else 400)
        
        # Connect size adjustment with debouncing
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(lambda: self.adjust_size())
        
        self.bubble.document().documentLayout().documentSizeChanged.connect(
            lambda: self._resize_timer.start(100)
        )
        
        # Add timestamp
        time = QLabel(datetime.now().strftime("%H:%M"))
        time.setStyleSheet("color: #999999; font-size: 10px;")
        time.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Layout arrangement
        if is_user:
            layout.addStretch()
            layout.addWidget(self.bubble)
            layout.addWidget(time)
        else:
            layout.addWidget(self.bubble)
            layout.addWidget(time)
            layout.addStretch()
        
        self.setLayout(layout)
        QTimer.singleShot(0, self.adjust_size)
    
    def adjust_size(self):
        if not self.bubble:
            return
            
        # Update maximum width based on window size
        if self.window():
            self.bubble.setMaximumWidth(int(self.window().width() * 0.6))
        
        # Calculate required size based on content
        doc_size = self.bubble.document().size()
        margins = self.bubble.contentsMargins()
        
        # Calculate width and height
        content_width = doc_size.width()
        padding = margins.left() + margins.right() + 40
        
        # Set width based on content, with constraints
        max_width = self.bubble.maximumWidth()
        min_width = 50
        width = min(max_width, max(min_width, int(content_width + padding)))
        
        # Calculate height with padding
        height = int(doc_size.height() + margins.top() + margins.bottom() + 20)
        
        # Set the new size
        self.bubble.setFixedSize(width, height)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_size()

class ChatbotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatbotQT")
        self.setMinimumSize(400, 500)
        
        # Set window icon
        icon = QIcon('chatbot.png')
        self.setWindowIcon(icon)
        
        # Get or request API key
        self.api_key = APIKeyManager.get_cached_key()
        if not self.api_key:
            self.request_api_key()
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat display area with scroll
        chat_container = QWidget()
        self.chat_layout = QVBoxLayout(chat_container)
        self.chat_layout.addStretch()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(chat_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: #ECE5DD; 
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #128C7E;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        layout.addWidget(self.scroll_area)
        
        # Input area
        input_container = QWidget()
        input_container.setStyleSheet("background-color: #F0F0F0; padding: 10px;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        self.input_field = QTextEdit()
        self.input_field.setFixedHeight(50)
        self.input_field.setFont(QFont('Arial', 10))
        self.input_field.setStyleSheet("""
            QTextEdit {
                border-radius: 20px;
                padding: 10px;
                background-color: white;
                border: none;
            }
        """)
        self.input_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        send_button = QPushButton("Send")
        send_button.setFixedSize(70, 50)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #128C7E;
                color: white;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #075E54;
            }
        """)
        send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_button)
        layout.addWidget(input_container)
        
        # Initialize conversation history
        self.conversation_history = []
        
        self.show()
    
    def add_message(self, message, is_user=True):
        bubble = MessageBubble(message, is_user)
        self.chat_layout.addWidget(bubble)
        # Scroll to bottom after adding message
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        # Update all message bubbles when window is resized
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, MessageBubble):
                widget.adjust_size()
    
    def request_api_key(self):
        dialog = QInputDialog()
        dialog.setWindowTitle('API Key Required')
        dialog.setLabelText('Please enter your OpenRouter API key:\n'
                          'The key will be stored securely at ~/.chatbotqt/api_key.cache\n'
                          'Copyright 2024 Mustaffa96 GitHub')
        dialog.setTextEchoMode(QLineEdit.Password)
        
        if dialog.exec_() == QInputDialog.Accepted:
            key = dialog.textValue()
            if key:
                if APIKeyManager.save_key(key):
                    self.api_key = key
                else:
                    self.add_message("Error: Invalid API key format", False)
                    self.request_api_key()  # Try again
            else:
                sys.exit()
        else:
            sys.exit()

    def send_message(self):
        user_message = self.input_field.toPlainText().strip()
        if not user_message:
            return
            
        self.add_message(user_message, True)
        self.input_field.clear()
        
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        try:
            # OpenRouter API endpoint for free Deepseek access
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "model": "deepseek/deepseek-chat:free",
                "messages": self.conversation_history
            }
            
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 401:
                # Invalid API key, request a new one
                self.api_key = None  # Clear invalid key
                self.request_api_key()
                if self.api_key:  # If new key provided, retry the message
                    self.send_message()
                return
            
            response_json = response.json()
            bot_response = response_json['choices'][0]['message']['content']
            
            # Add bot response to conversation history
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            self.add_message(bot_response, False)
            
        except Exception as e:
            self.add_message(f"Error: Could not get response from API. {str(e)}", False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatbotWindow()
    sys.exit(app.exec_())
