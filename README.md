# Deepseek Chatbot

A desktop chatbot application built with PyQt5 that integrates with the Deepseek API through OpenRouter (free access).

## Features
- Modern dark-themed UI
- Real-time chat interface
- Integration with Deepseek's AI model (free through OpenRouter)
- Conversation history support

## Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Get your free OpenRouter API key:
   - Visit [OpenRouter](https://www.openrouter.ai/)
   - Sign up or log in
   - Navigate to the API section
   - Click "Create Key" to generate your API key
4. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```
5. Edit `.env` and replace `your_openrouter_api_key_here` with your OpenRouter API key

## Running the Application
```bash
python main.py
```

## Usage
1. Launch the application
2. Type your message in the input field
3. Click "Send" or press Enter to send your message
4. The AI response will appear in the chat window

## Requirements
- Python 3.7+
- PyQt5
- requests
- python-dotenv

For Icon, credit to flaticon author, https://www.flaticon.com/free-icon/chatbot_5226034?term=chatbot&page=1&position=45&origin=tag&related_id=5226034
