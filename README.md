# Tele Tycoon

From novice to mogul: explanations that elevate your empire

![](docs/intro.png)

Tele Tycoon is a Telegram bot that brings the classic board game 18xx to your fingertips. Play against friends or AI opponents, manage railroads, and build your empire—all through an intuitive chat interface.

## ✨ Features

- 🎮 **Full 1889 Implementation** - Complete game rules and mechanics
- 🤖 **AI Players** - Rule-based and LLM-powered opponents
- 💬 **Telegram Interface** - Play directly in your favorite messenger
- 📊 **Rich Visualizations** - Clear game state and stock market displays
- 💾 **Auto-Save** - Game state automatically saved after every action
- 🔄 **Error Recovery** - Resume games after timeouts or bot restarts
- 🎯 **Multi-Player** - Support for 2-6 players per game

## 🚀 Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Python 3.12 or higher (uv will handle this)
- A Telegram account
- (Optional) OpenRouter API key for LLM-powered AI opponents

### Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # or on macOS:
   brew install uv
   ```

2. **Clone the repository**
   ```bash
   git clone https://github.com/namuan/tele-tycoon.git
   cd tele-tycoon
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**

   Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:
   ```bash
   # Required: Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_USER_ID=your_telegram_user_id

   # Optional: LLM AI Configuration (for AI opponents)
   OPENROUTER_API_KEY=your_openrouter_api_key
   OPENROUTER_PRIMARY_MODEL=anthropic/claude-3.5-sonnet
   OPENROUTER_FALLBACK_MODEL=anthropic/claude-3-haiku

   # Optional: Database Configuration
   DATABASE_PATH=./data/teletycoon.db
   ```

   **Getting your Telegram credentials:**
   - **Bot Token**: Talk to [@BotFather](https://t.me/botfather) on Telegram
     1. Send `/newbot` command
     2. Follow instructions to create your bot
     3. Copy the token provided
   - **User ID**: Talk to [@userinfobot](https://t.me/userinfobot) on Telegram
     1. Send `/start` command
     2. Copy your numeric user ID

5. **Run the bot**
   ```bash
   make run
   # or directly:
   uv run python -m teletycoon.main
   ```

### 🤖 Setting Up AI with LLM

Tele Tycoon supports two types of AI opponents:

1. **Rule-Based AI** - Always available, no configuration needed
2. **LLM-Powered AI** - Requires OpenRouter API key (recommended for smarter opponents)

#### Configuring LLM AI Players

To enable LLM-powered AI opponents that can reason about game strategy:

1. **Get an OpenRouter API key**
   - Visit [OpenRouter](https://openrouter.ai/)
   - Sign up for an account
   - Generate an API key from your dashboard
   - Add credits to your account (pay-as-you-go pricing)

2. **Configure your .env file**
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
   OPENROUTER_PRIMARY_MODEL=anthropic/claude-3.5-sonnet
   OPENROUTER_FALLBACK_MODEL=anthropic/claude-3-haiku
   ```

3. **Available Models**

   Popular models that work well with the game:
   - `anthropic/claude-3.5-sonnet` - Best reasoning (recommended)
   - `anthropic/claude-3-haiku` - Fast and economical
   - `openai/gpt-4-turbo` - Alternative strong model
   - `openai/gpt-3.5-turbo` - Budget option

   See [OpenRouter models](https://openrouter.ai/models) for the full list.

4. **How it works**

   When you create a game with LLM AI opponents:
   - The AI receives the full game state and available actions
   - It reasons about the best strategic move using the configured LLM
   - Provides explanations for its decisions
   - Falls back to the primary model if the fallback fails
   - If no API key is configured, defaults to rule-based AI behavior

5. **Cost considerations**

   - LLM API calls are pay-per-use
   - A typical game turn costs $0.001 - $0.01 depending on the model
   - Claude 3.5 Sonnet: ~$0.003 per turn (recommended)
   - Claude 3 Haiku: ~$0.0003 per turn (economical)
   - Full game (50-100 turns): approximately $0.15 - $1.00

**Without LLM Configuration:** The bot will still work perfectly! AI opponents will use the built-in rule-based strategy, which plays competently without requiring any API keys or external services.
