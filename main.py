import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Third-party imports
from dotenv import load_dotenv
import requests
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QInputDialog,
    QLineEdit,
    QFrame,
    QComboBox,
    QDialog,
)
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QResizeEvent, QIcon

load_dotenv()


class APIKeyManager:
    @staticmethod
    def get_cache_file():
        # Store in user's home directory to ensure write permissions
        home = str(Path.home())
        cache_dir = os.path.join(home, ".chatbotqt")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        return os.path.join(cache_dir, "api_key.cache")

    @staticmethod
    def get_cached_key():
        try:
            cache_file = APIKeyManager.get_cache_file()
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
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
            with open(cache_file, "w") as f:
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

        # Create message container
        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 5)

        # Create message bubble
        self.bubble = QTextEdit()
        self.bubble.setReadOnly(True)
        self.bubble.setFont(QFont("Segoe UI", 10))
        self.bubble.setText(message)
        self.bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Add typing animation for bot messages
        self.opacity = 0.0 if not is_user else 1.0
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Style the bubble based on theme
        is_dark = self.window().property("darkTheme") if self.window() else False
        user_bg = "#128C7E" if is_dark else "#DCF8C6"
        user_text = "#FFFFFF" if is_dark else "#000000"
        bot_bg = "#383838" if is_dark else "#FFFFFF"
        bot_text = "#FFFFFF" if is_dark else "#000000"
        
        self.bubble.setStyleSheet(f"""
            QTextEdit {{
                background-color: {user_bg if is_user else bot_bg};
                color: {user_text if is_user else bot_text};
                border-radius: 15px;
                padding: 8px;
                border: none;
            }}
        """)

        # Set size policies for dynamic resizing
        self.bubble.setMinimumWidth(50)
        self.bubble.setMaximumWidth(int(self.window().width() * 0.7) if self.window() else 500)

        container_layout.addWidget(self.bubble)

        # Add timestamp
        time = QLabel(datetime.now().strftime("%H:%M"))
        time.setStyleSheet(f"color: {'#A0A0A0' if is_dark else '#666666'}; font-size: 10px;")
        time.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        container_layout.addWidget(time, alignment=Qt.AlignRight)

        # Layout arrangement
        if is_user:
            layout.addStretch()
            layout.addWidget(container)
        else:
            layout.addWidget(container)
            layout.addStretch()

        self.setLayout(layout)
        
        if not is_user:
            QTimer.singleShot(0, self.animation.start)


class ChatSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat Settings")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Model selection
        model_label = QLabel("AI Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "deepseek/deepseek-chat:free",
            "anthropic/claude-2",
            "google/palm-2-chat-bison",
            "meta-llama/llama-2-70b-chat",
        ])
        layout.addWidget(model_label)
        layout.addWidget(self.model_combo)
        
        # Personality selection
        personality_label = QLabel("Chatbot Personality:")
        self.personality_combo = QComboBox()
        self.personality_combo.addItems([
            "Professional",
            "Friendly",
            "Technical",
            "Creative"
        ])
        layout.addWidget(personality_label)
        layout.addWidget(self.personality_combo)
        
        # Context window size
        context_label = QLabel("Context Window (messages):")
        self.context_combo = QComboBox()
        self.context_combo.addItems(["5", "10", "15", "20"])
        layout.addWidget(context_label)
        layout.addWidget(self.context_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)


class ChatbotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatbotQT")
        self.setMinimumSize(500, 600)
        self.setProperty("darkTheme", False)

        # Initialize settings
        self.model = "deepseek/deepseek-chat:free"
        self.personality = "Professional"
        self.context_window = 10
        
        # Initialize API key
        self.api_key = APIKeyManager.get_cached_key()
        if not self.api_key:
            self.request_api_key()

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create header with settings button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        title = QLabel("ChatbotQT")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        settings_button = QPushButton()
        settings_button.setIcon(QIcon(os.path.join("public", "icons", "settings.png")))
        settings_button.setFixedSize(32, 32)
        settings_button.clicked.connect(self.show_settings)
        settings_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 16px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        
        # Theme toggle button
        self.theme_button = QPushButton()
        self.theme_button.setFixedSize(32, 32)
        self.update_theme_icon()
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 16px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(settings_button)
        header_layout.addWidget(self.theme_button)

        # Create scroll area for chat
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Create chat container
        chat_container = QWidget()
        self.chat_layout = QVBoxLayout(chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(0, 10, 0, 10)
        
        self.scroll_area.setWidget(chat_container)

        # Create input container
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 15, 15, 15)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setFont(QFont("Segoe UI", 10))
        
        send_button = QPushButton()
        send_button.setIcon(QIcon(os.path.join("public", "icons", "send.png") if not getattr(sys, 'frozen', False) 
                                else os.path.join(sys._MEIPASS, "public", "icons", "send.png")))
        send_button.setFixedSize(40, 40)
        send_button.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_button)

        # Add widgets to main layout
        layout.addWidget(header)
        layout.addWidget(self.scroll_area)
        layout.addWidget(input_container)

        # Initialize conversation history with system message
        self.conversation_history = [
            {
                "role": "system",
                "content": self.get_personality_prompt()
            }
        ]
        
        # Initialize message cache for context window
        self.message_cache = []
        
        # Initialize loading indicator
        self.loading_indicator = None
        
        # Apply initial theme
        self.apply_theme()
        
        self.show()

    def update_theme_icon(self):
        is_dark = self.property("darkTheme")
        icon_name = "light.png" if is_dark else "dark.png"
        icon_path = os.path.join("public", "icons", icon_name)
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "public", "icons", icon_name)
        self.theme_button.setIcon(QIcon(icon_path))

    def toggle_theme(self):
        self.setProperty("darkTheme", not self.property("darkTheme"))
        self.update_theme_icon()
        self.apply_theme()
        
    def apply_theme(self):
        is_dark = self.property("darkTheme")
        
        # Set application style
        if is_dark:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1E1E1E;
                }
                QLabel {
                    color: #FFFFFF;
                }
                QScrollArea {
                    background-color: #1E1E1E;
                    border: none;
                }
                QWidget#chat_container {
                    background-color: #1E1E1E;
                }
                QTextEdit {
                    background-color: #383838;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 20px;
                    padding: 10px;
                }
                QTextEdit:focus {
                    border: 2px solid #128C7E;
                }
                QPushButton {
                    background-color: #128C7E;
                    color: white;
                    border-radius: 20px;
                }
                QPushButton:hover {
                    background-color: #0F7A6C;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #383838;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #666666;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #F0F2F5;
                }
                QLabel {
                    color: #000000;
                }
                QScrollArea {
                    background-color: #F0F2F5;
                    border: none;
                }
                QWidget#chat_container {
                    background-color: #F0F2F5;
                }
                QTextEdit {
                    background-color: #FFFFFF;
                    color: #000000;
                    border: none;
                    border-radius: 20px;
                    padding: 10px;
                }
                QTextEdit:focus {
                    border: 2px solid #128C7E;
                }
                QPushButton {
                    background-color: #128C7E;
                    color: white;
                    border-radius: 20px;
                }
                QPushButton:hover {
                    background-color: #0F7A6C;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #F0F2F5;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #C4C4C4;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        
    def get_personality_prompt(self) -> str:
        prompts = {
            "Professional": "You are a professional assistant. Provide clear, concise, and accurate responses in a formal tone.",
            "Friendly": "You are a friendly and approachable assistant. Use a casual, warm tone and engage in natural conversation.",
            "Technical": "You are a technical expert. Provide detailed technical explanations and use industry-standard terminology.",
            "Creative": "You are a creative assistant. Think outside the box and provide innovative solutions with an imaginative flair."
        }
        return prompts.get(self.personality, prompts["Professional"])

    def show_settings(self):
        dialog = ChatSettings(self)
        dialog.model_combo.setCurrentText(self.model)
        dialog.personality_combo.setCurrentText(self.personality)
        dialog.context_combo.setCurrentText(str(self.context_window))
        
        if dialog.exec_() == QDialog.Accepted:
            # Update settings
            new_model = dialog.model_combo.currentText()
            new_personality = dialog.personality_combo.currentText()
            new_context = int(dialog.context_combo.currentText())
            
            # Only reset conversation if settings changed
            if (new_model != self.model or 
                new_personality != self.personality or 
                new_context != self.context_window):
                
                self.model = new_model
                self.personality = new_personality
                self.context_window = new_context
                
                # Reset conversation with new system message
                self.conversation_history = [
                    {
                        "role": "system",
                        "content": self.get_personality_prompt()
                    }
                ]
                self.message_cache = []
                
                # Add system message to chat
                self.add_message("Settings updated. Starting new conversation.", False)

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
                # Update the maximum width of the bubble
                if widget.bubble:
                    widget.bubble.setMaximumWidth(int(self.width() * 0.7))
                    widget.bubble.document().adjustSize()
                    widget.adjustSize()

    def request_api_key(self):
        dialog = QInputDialog()
        dialog.setWindowTitle("API Key Required")
        dialog.setLabelText(
            "Please enter your OpenRouter API key:\n"
            "The key will be stored securely at ~/.chatbotqt/api_key.cache"
        )
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
        
        # Show loading indicator
        loading_message = MessageBubble("...", False)
        self.chat_layout.addWidget(loading_message)
        self.loading_indicator = loading_message
        self.scroll_to_bottom()

        # Update message cache
        self.message_cache.append({"role": "user", "content": user_message})
        if len(self.message_cache) > self.context_window:
            self.message_cache.pop(0)

        # Construct conversation history with system message and cached messages
        current_conversation = [self.conversation_history[0]] + self.message_cache

        try:
            # OpenRouter API endpoint
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": current_conversation,
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
            )

            # Remove loading indicator
            if self.loading_indicator:
                self.chat_layout.removeWidget(self.loading_indicator)
                self.loading_indicator.deleteLater()
                self.loading_indicator = None

            if response.status_code == 401:
                # Invalid API key, request a new one
                self.api_key = None  # Clear invalid key
                self.request_api_key()
                if self.api_key:  # If new key provided, retry the message
                    self.send_message()
                return

            response_json = response.json()
            bot_response = response_json["choices"][0]["message"]["content"]

            # Update message cache with bot response
            self.message_cache.append({"role": "assistant", "content": bot_response})
            if len(self.message_cache) > self.context_window:
                self.message_cache.pop(0)

            self.add_message(bot_response, False)

        except Exception as e:
            # Remove loading indicator
            if self.loading_indicator:
                self.chat_layout.removeWidget(self.loading_indicator)
                self.loading_indicator.deleteLater()
                self.loading_indicator = None
            
            self.add_message(f"Error: Could not get response from API. {str(e)}", False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotWindow()
    sys.exit(app.exec_())
