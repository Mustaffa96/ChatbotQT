# ChatbotQT

A modern desktop chatbot application built with PyQt5 and integrated with the Deepseek API.

## Features

- Modern, responsive UI with light/dark theme support
- Integration with Deepseek API for intelligent responses
- Message history with SQLite storage
- Configurable chat settings
- Cross-platform support (Windows, macOS, Linux)

## Prerequisites

- Python 3.8 or higher
- PyQt5
- OpenRouter API key (get one from [OpenRouter](https://openrouter.ai/keys))

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Mustaffa96/ChatbotQT.git
cd ChatbotQT
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```bash
cp .env.example .env
```
Edit `.env` and add your OpenRouter API key.

## Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Run tests:
```bash
python -m pytest tests/
```

## Project Structure

```
ChatbotQT/
├── chatbotqt/           # Main package
│   ├── ui/             # UI components
│   │   ├── chat_window.py
│   │   ├── message_bubble.py
│   │   └── settings_dialog.py
│   ├── utils/          # Utility modules
│   │   ├── api_manager.py
│   │   ├── db_manager.py
│   │   └── api_worker.py
│   └── __init__.py
├── tests/              # Test suite
├── public/             # Static assets
├── .env.example        # Example environment variables
├── requirements.txt    # Production dependencies
└── README.md          # This file
```

## Configuration

The application can be configured through environment variables in the `.env` file:

- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `DEFAULT_MODEL`: Default chat model to use
- `CONTEXT_WINDOW`: Number of messages to keep in context
- `DEFAULT_THEME`: UI theme (light/dark)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
