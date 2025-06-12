import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import base64
import sqlite3
from PyQt5.QtCore import QThread, pyqtSignal

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
    QMessageBox,
    QSpinBox
)
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QBuffer, QByteArray
from PyQt5.QtGui import QFont, QPalette, QColor, QResizeEvent, QIcon, QPixmap, QImage

load_dotenv()


class APIKeyManager:
    @staticmethod
    def validate_api_key(key: str) -> bool:
        """Basic validation of API key format."""
        return bool(key and len(key.strip()) >= 10)

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
        if not APIKeyManager.validate_api_key(key):
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
    def __init__(self, message, is_user=True, parent=None, image_path=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Store whether this is a user message
        self.setProperty("is_user", is_user)
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

        # WhatsApp colors (constant regardless of theme)
        user_bg = "#E1FFC7"  # WhatsApp light green
        user_text = "#000000"  # Black text
        bot_bg = "#FFFFFF"    # White background
        bot_text = "#000000"  # Black text

        self.bubble.setStyleSheet(f"""
            QTextEdit {{
                background-color: {user_bg if is_user else bot_bg};
                color: {user_text if is_user else bot_text};
                border-radius: 15px;
                padding: 8px;
                border: none;
            }}
        """)

        # Handle image if provided
        if image_path:
            image_label = QLabel()
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            container_layout.addWidget(image_label)

        # Set size policies for dynamic resizing
        self.bubble.setMinimumWidth(50)
        self.bubble.setMaximumWidth(int(self.window().width() * 0.7) if self.window() else 500)

        container_layout.addWidget(self.bubble)

        # Add timestamp with WhatsApp style color
        time = QLabel(datetime.now().strftime("%H:%M"))
        time.setStyleSheet("color: #9E9595; font-size: 10px;")  # WhatsApp timestamp color
        time.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        container_layout.addWidget(time, alignment=Qt.AlignRight)

        # Layout arrangement based on user/bot message
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
        
        # Define models with their colors
        models = [
            # Most Reliable Free Models (Green)
            ("openai/gpt-3.5-turbo (Free)", "green"),
            ("deepseek/deepseek-chat-v3 (Free)", "green"),
            # Other Free Models (Black)
            ("anthropic/claude-instant-1.2 (Free)", "orange"),
            ("meta-llama/llama-2-70b-chat (Free)", "orange"),
            ("mistralai/mixtral-8x7b (Free)", "orange"),
            ("phind/phind-codellama-34b (Free)", "orange"),
            ("openchat/openchat (Free)", "orange"),
            ("gryphe/mythomist-7b (Free)", "orange"),
            ("nousresearch/nous-hermes-2-mixtral-8x7b (Free)", "orange"),
            # Paid Models (Red)
            ("anthropic/claude-2", "red"),
            ("anthropic/claude-2.1", "red"),
            ("openai/gpt-4", "red"),
            ("openai/gpt-4-32k", "red")
        ]

        # Add items with colors
        for model, color in models:
            self.model_combo.addItem(model)
            index = self.model_combo.count() - 1
            self.model_combo.setItemData(
                index, 
                QColor(color), 
                Qt.ForegroundRole
            )

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


class ApiWorker(QThread):
    def __new__(cls, *args, **kwargs):
        return super(ApiWorker, cls).__new__(cls)

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_key, model, messages):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.messages = messages

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/Mustaffa96/ChatbotQT",
                "X-Title": "ChatbotQT",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": self.messages,
                "temperature": 0.7,
                "max_tokens": 500,
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            response_json = response.json()
            if "error" in response_json:
                self.error.emit(f"API Error: {response_json['error']}")
            else:
                self.finished.emit(response_json)
        except Exception as e:
            self.error.emit(f"Request Error: {str(e)}")


class DatabaseManager:
    def __init__(self):
        self.db_path = os.path.join(str(Path.home()), ".chatbotqt", "chat_history.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def save_message(self, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO messages (role, content) VALUES (?, ?)',
                (role, content)
            )
            conn.commit()

    def get_recent_messages(self, limit: int) -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT role, content FROM messages ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            return [{"role": role, "content": content} for role, content in cursor.fetchall()]


class ChatbotWindow(QMainWindow):
    def __new__(cls, *args, **kwargs):
        return super(ChatbotWindow, cls).__new__(cls)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatbotQT")
        self.setMinimumSize(500, 600)
        self.setProperty("darkTheme", False)

        # Initialize API key
        self.api_key = APIKeyManager.get_cached_key()
        if not self.api_key:
            self.request_api_key()

        # Initialize model and context window
        self.model = "openai/gpt-3.5-turbo"  # Default model
        self.context_window = 10  # Default context window size
        self.personality = "Professional"  # Default personality

        # Initialize conversation history and message cache
        self.db_manager = DatabaseManager()
        recent_messages = self.db_manager.get_recent_messages(self.context_window)
        self.conversation_history = recent_messages
        self.message_cache = recent_messages

        # Main layout
        layout = QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Header layout with settings button
        header_layout = QHBoxLayout()
        
        # Theme toggle button with round borders
        self.theme_toggle = QPushButton("🌙" if self.property("darkTheme") else "☀️")
        self.theme_toggle.setFixedSize(40, 40)
        self.theme_toggle.setStyleSheet("""
            QPushButton {
                border: 2px solid #ccc;
                border-radius: 20px;
                padding: 5px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_toggle)

        # Add stretch to push buttons to opposite sides
        header_layout.addStretch()

        # Settings button with round borders
        settings_button = QPushButton("⚙️")
        settings_button.setFixedSize(40, 40)
        settings_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #ccc;
                border-radius: 20px;
                padding: 5px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        settings_button.clicked.connect(self.show_settings)
        header_layout.addWidget(settings_button)

        layout.addLayout(header_layout)

        # Create chat area with WhatsApp-like styling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c1c1c1;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
        """)

        chat_container = QWidget()
        chat_container.setObjectName("chat_container")
        self.chat_layout = QVBoxLayout(chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)
        self.scroll_area.setWidget(chat_container)

        # Create input area with modern styling
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 20px;
                padding: 10px;
                background-color: white;
            }
        """)

        send_button = QPushButton()
        send_button.setIcon(QIcon(os.path.join("public","icons", "send.png")))
        send_button.setFixedSize(40, 40)
        send_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 20px;
                background-color: #128C7E;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #075E54;
            }
        """)
        send_button.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_button)

        # Add components to main layout
        layout.addWidget(self.scroll_area)
        layout.addWidget(input_container)

        # Initialize theme
        self.toggle_theme()  

        # Initialize conversation history with system message
        self.conversation_history.append({
            "role": "system",
            "content": self.get_personality_prompt()
        })

        # Add messages to chat
        for msg in reversed(self.conversation_history):
            self.add_message(msg["content"], msg["role"] == "user")

        # Initialize loading indicator
        self.loading_indicator = None

        self.apply_theme()

        self.show()

    def apply_theme(self):
        """Apply the current theme (light/dark) to the window."""
        is_dark = self.property("darkTheme")
        
        # Create palette for the theme
        palette = QPalette()
        
        if is_dark:
            # Dark theme colors
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.white)
        else:
            # Light theme colors
            palette.setColor(QPalette.Window, Qt.white)
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.Link, QColor(0, 0, 255))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.white)

        # Apply palette to both the window and application
        self.setPalette(palette)
        QApplication.instance().setPalette(palette)

        # Update input field style
        self.input_field.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {'#666' if is_dark else '#ccc'};
                border-radius: 20px;
                padding: 10px;
                background-color: {QColor(53, 53, 53).name() if is_dark else 'white'};
                color: {'white' if is_dark else 'black'};
            }}
        """)

        # Update scroll area style
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {'#2c2c2c' if is_dark else 'transparent'};
            }}
            QScrollBar:vertical {{
                border: none;
                background-color: {'#404040' if is_dark else '#f0f0f0'};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {'#666' if is_dark else '#c1c1c1'};
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {'#808080' if is_dark else '#a8a8a8'};
            }}
        """)

    def update_theme_icon(self):
        is_dark = self.property("darkTheme")
        icon_name = "light.png" if is_dark else "dark.png"
        icon_path = os.path.join("icons", icon_name)
        self.theme_button.setIcon(QIcon(icon_path))

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        is_dark = not self.property("darkTheme")
        self.setProperty("darkTheme", is_dark)
        
        # Update theme toggle button text
        self.theme_toggle.setText("🌙" if is_dark else "☀️")
        
        # Update application style
        app = QApplication.instance()
        palette = QPalette()
        
        if is_dark:
            # Dark theme colors
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.white)

            # Dark theme input field
            self.input_field.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #666;
                    border-radius: 20px;
                    padding: 10px;
                    background-color: #383838;
                    color: white;
                }
            """)
        else:
            # Light theme colors
            palette.setColor(QPalette.Window, Qt.white)
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.Link, QColor(0, 0, 255))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.white)

            # Light theme input field
            self.input_field.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #ccc;
                    border-radius: 20px;
                    padding: 10px;
                    background-color: white;
                    color: black;
                }
            """)

        app.setPalette(palette)

        # Update scroll area style
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c1c1c1;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
        """)

        # Update message bubbles
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, MessageBubble) and widget.bubble:
                is_user = widget.property("is_user")
                user_bg = "#128C7E" if is_dark else "#DCF8C6"
                user_text = "#FFFFFF" if is_dark else "#000000"
                bot_bg = "#383838" if is_dark else "#FFFFFF"
                bot_text = "#FFFFFF" if is_dark else "#000000"
                
                widget.bubble.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {user_bg if is_user else bot_bg};
                        color: {user_text if is_user else bot_text};
                        border-radius: 15px;
                        padding: 8px;
                        border: none;
                    }}
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

    def add_message(self, message, is_user=True, image_path=None):
        bubble = MessageBubble(message, is_user, image_path=image_path)
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
            "The key will be stored securely at ~/.chatbotqt/api_key.cache\n"
            "Get your API key from: https://openrouter.ai/keys"
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

        # Clean model name by removing the "(Free)" suffix if present
        model_name = self.model.split(" (Free)")[0]

        # Show loading indicator
        loading_message = MessageBubble("...", False)
        self.chat_layout.addWidget(loading_message)
        self.loading_indicator = loading_message
        self.scroll_to_bottom()

        # Save user message to database
        self.db_manager.save_message("user", user_message)

        # Update message cache
        self.message_cache.append({"role": "user", "content": user_message})
        if len(self.message_cache) > self.context_window:
            self.message_cache.pop(0)

        # Create and start API worker thread
        self.worker = ApiWorker(self.api_key, model_name, self.message_cache)
        self.worker.finished.connect(self.handle_api_response)
        self.worker.error.connect(self.handle_api_error)
        self.worker.start()

    def handle_api_response(self, response_json):
        # Remove loading indicator
        if self.loading_indicator:
            self.chat_layout.removeWidget(self.loading_indicator)
            self.loading_indicator.deleteLater()
            self.loading_indicator = None

        bot_response = response_json["choices"][0]["message"]["content"]

        # Save bot response to database
        self.db_manager.save_message("assistant", bot_response)

        # Update message cache
        self.message_cache.append({"role": "assistant", "content": bot_response})
        if len(self.message_cache) > self.context_window:
            self.message_cache.pop(0)

        self.add_message(bot_response, False)

    def handle_api_error(self, error_message):
        # Remove loading indicator
        if self.loading_indicator:
            self.chat_layout.removeWidget(self.loading_indicator)
            self.loading_indicator.deleteLater()
            self.loading_indicator = None

        self.add_message(f"Error: Could not get response from API. {error_message}", False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotWindow()
    sys.exit(app.exec_())
