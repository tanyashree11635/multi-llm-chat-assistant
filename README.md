# 💬 LLM Chat Assistant

A modern, full-featured chatbot application supporting multiple AI providers (OpenAI GPT and Google Gemini) with a beautiful Streamlit interface.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)

## ✨ Features

- 🤖 **Multi-Provider Support**: Seamlessly switch between OpenAI GPT and Google Gemini models
- 🎨 **Modern UI**: Beautiful, responsive chat interface with gradient message bubbles
- 🔄 **Real-time Chat**: Interactive conversations with streaming responses
- 💾 **Session Management**: Create, clear, and export chat sessions
- 🎯 **Model Selection**: Choose from multiple models for each provider
- 🔐 **Secure**: Environment-based configuration for API keys
- 📊 **Provider Info**: See which model and provider generated each response

## 🚀 Supported Models

### OpenAI
- GPT-4
- GPT-3.5-turbo
- Custom OpenAI models

### Google Gemini
- Gemini 2.5 Flash Lite (fastest)
- Gemini 2.5 Flash Lite Preview
- Gemini 2.5 Pro (most powerful)
- Gemini 2.5 Pro Preview TTS

## 📋 Prerequisites

- Python 3.8 or higher
- OpenAI API key (optional, for GPT models)
- Google Gemini API key (optional, for Gemini models)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dheerajatmakuri/llm_chatbot.git
   cd llm_chatbot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   DEFAULT_PROVIDER=openai
   OPENAI_MODEL=gpt-3.5-turbo
   GEMINI_MODEL=gemini-2.5-flash-lite
   ```

## 🎯 Usage

### Running the Streamlit App

```bash
streamlit run frontend/streamlit_app.py
```

The app will open in your default browser at `http://localhost:8501`

### Using the Chat Interface

1. **Select Provider**: Choose between OpenAI, Gemini, or Auto in the sidebar
2. **Choose Model**: Select your preferred model for the chosen provider
3. **Start Chatting**: Type your message and click "Send Message"
4. **Manage Sessions**: Use sidebar buttons to create new sessions, clear conversations, or export chat history

## 📁 Project Structure

```
llm_chatbot/
│
├── frontend/
│   └── streamlit_app.py          # Streamlit web interface
│
├── src/
│   ├── api/
│   │   ├── models.py              # API data models
│   │   └── routes.py              # API routes (FastAPI)
│   │
│   ├── config/
│   │   └── settings.py            # Configuration and environment variables
│   │
│   ├── models/
│   │   └── chat_models.py         # Chat data models
│   │
│   ├── services/
│   │   ├── chat_service.py        # Chat session management
│   │   └── llm_service.py         # LLM provider integration
│   │
│   └── utils/
│       └── validators.py          # Input validation utilities
│
├── scripts/
│   └── diag_env.py                # Environment diagnostics
│
├── .env.example                   # Example environment variables
├── .gitignore                     # Git ignore file
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | - | Yes* |
| `GEMINI_API_KEY` | Your Google Gemini API key | - | Yes* |
| `DEFAULT_PROVIDER` | Default AI provider (`openai` or `gemini`) | `openai` |
| `OPENAI_MODEL` | Default OpenAI model | `gpt-3.5-turbo` | No |
| `GEMINI_MODEL` | Default Gemini model | `gemini-2.5-flash-lite` |
| `MAX_RESPONSE_TOKENS` | Maximum tokens in response | `512` |
| `APP_ENV` | Environment (`development`, `staging`, `production`) | `development` |
| `DEBUG` | Enable debug mode | `true` |

\* At least one API key (OpenAI or Gemini) is required

## 🎨 Features in Detail

### Modern Chat Interface
- **Gradient Message Bubbles**: User messages in blue, assistant in dark gray
- **Provider Information**: See which model generated each response
- **Responsive Design**: Works on desktop and mobile devices
- **Emoji Support**: Rich visual feedback with emojis

### Session Management
- **Multiple Sessions**: Create and manage multiple chat sessions
- **Clear Conversations**: Reset chat history with one click
- **Export Chats**: Download conversation history as JSON

### Smart Provider Switching
- **Auto Mode**: Automatically select the best available provider
- **Manual Selection**: Choose specific providers and models
- **Fallback Support**: Automatically fallback if primary provider fails

## 🔒 Security

- API keys stored in `.env` file (never committed to git)
- `.gitignore` configured to exclude sensitive files
- No hardcoded credentials in source code
- Environment-based configuration

## 🐛 Troubleshooting

### Common Issues

1. **"No valid messages to send"**
   - Make sure you've sent at least one message
   - Try creating a new session

2. **API Key Errors**
   - Verify your API keys in the `.env` file
   - Check that the keys have proper permissions
   - Ensure you have credits/quota remaining

3. **Model Not Found**
   - Some models require specific API access
   - Try switching to a different model
   - Check the Gemini/OpenAI documentation for available models

4. **Import Errors**
   - Make sure virtual environment is activated
   - Run `pip install -r requirements.txt` again

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Dheeraj Atmakuri**
- GitHub: [@dheerajatmakuri](https://github.com/dheerajatmakuri)

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for GPT models
- [Google](https://ai.google.dev/) for Gemini models
- [Streamlit](https://streamlit.io/) for the amazing web framework
- All contributors who help improve this project

## 📞 Support

If you encounter any issues or have questions, please [open an issue](https://github.com/dheerajatmakuri/llm_chatbot/issues) on GitHub.

---

Made with ❤️ by Dheeraj Atmakuri
