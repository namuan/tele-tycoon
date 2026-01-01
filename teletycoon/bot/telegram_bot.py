"""Telegram bot for TeleTycoon game."""

import logging
import os
import time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from teletycoon.database.base import init_db
from teletycoon.engine.game_engine import GameEngine

from .handlers import CommandHandlers, GameHandlers

logger = logging.getLogger(__name__)


class TeleTycoonBot:
    """Main Telegram bot for TeleTycoon game.

    Manages bot lifecycle and routes messages to handlers.

    Attributes:
        token: Telegram bot token.
        app: Telegram Application instance.
        games: Dictionary of active game engines.
        command_handlers: Handler for bot commands.
        game_handlers: Handler for game actions.
    """

    def __init__(self, token: str | None = None) -> None:
        """Initialize the Telegram bot.

        Args:
            token: Telegram bot token. If not provided, reads from env.
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not self.token:
            raise ValueError(
                "Telegram bot token required. Set TELEGRAM_BOT_TOKEN env var."
            )

        self.games: dict[str, GameEngine] = {}
        self.command_handlers = CommandHandlers(self)
        self.game_handlers = GameHandlers(self)
        self.app: Application | None = None

    def setup(self) -> None:
        """Set up the bot application and handlers."""
        # Initialize database
        init_db()

        # Create application with increased timeouts for LLM processing
        self.app = (
            Application.builder()
            .token(self.token)
            .read_timeout(60)  # Increased from default 5 seconds
            .write_timeout(60)  # Increased from default 5 seconds
            .connect_timeout(60)  # Increased from default 5 seconds
            .pool_timeout(60)  # Increased from default 1 second
            .build()
        )

        # Register command handlers
        self.app.add_handler(CommandHandler("start", self.command_handlers.start))
        self.app.add_handler(CommandHandler("help", self.command_handlers.help))
        self.app.add_handler(CommandHandler("newgame", self.command_handlers.new_game))
        self.app.add_handler(
            CommandHandler("joingame", self.command_handlers.join_game)
        )
        self.app.add_handler(
            CommandHandler("startgame", self.command_handlers.start_game)
        )
        self.app.add_handler(CommandHandler("status", self.command_handlers.status))
        self.app.add_handler(
            CommandHandler("portfolio", self.command_handlers.portfolio)
        )
        self.app.add_handler(
            CommandHandler("companies", self.command_handlers.companies)
        )
        self.app.add_handler(CommandHandler("actions", self.command_handlers.actions))
        self.app.add_handler(CommandHandler("pass", self.command_handlers.pass_turn))
        self.app.add_handler(CommandHandler("addai", self.command_handlers.add_ai))
        self.app.add_handler(CommandHandler("endgame", self.command_handlers.end_game))
        self.app.add_handler(CommandHandler("resume", self.command_handlers.resume))

        # Register callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.game_handlers.handle_callback))

        # Register message handler for game actions
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.game_handlers.handle_message,
            )
        )

        # Error handler
        self.app.add_error_handler(self.error_handler)

        logger.info("Bot setup complete")

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle errors in the bot."""
        logger.error(
            f"Exception while handling update: {context.error}", exc_info=context.error
        )

        if not isinstance(update, Update) or not update.effective_chat:
            return

        chat_id = update.effective_chat.id
        game_id = str(chat_id)
        effective_user_id = (
            str(update.effective_user.id) if update.effective_user else None
        )

        engine = self.games.get(game_id)

        saved = False
        if engine:
            try:
                engine.save()
                saved = True
                logger.info(f"Saved game state after error for game {game_id}")
            except Exception as save_error:
                logger.error(f"Failed to save game after error: {save_error}")

        if saved:
            message = (
                "❌ An error occurred, but your game has been saved.\n"
                "Use /status to continue playing."
            )
        elif engine:
            message = "❌ An error occurred. Please try /status to check game state."
        else:
            message = "❌ An error occurred. Please try again."

        if saved:
            current = engine.state.current_player if engine else None
            try:
                actions = engine.get_available_actions() if engine else []
            except Exception:
                actions = []

            is_current_user_turn = (
                current is not None
                and effective_user_id is not None
                and current.id == effective_user_id
            )
            if not actions or not is_current_user_turn:
                return

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
            )
        except Exception as msg_error:
            logger.error(f"Failed to send error message: {msg_error}")

    def run(self) -> None:
        """Run the bot (blocking)."""
        if not self.app:
            self.setup()

        logger.info("Starting bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    def get_game(self, game_id: str) -> GameEngine | None:
        """Get a game engine by ID.

        Args:
            game_id: Game ID.

        Returns:
            GameEngine or None.
        """
        return self.games.get(game_id)

    def create_game(self, game_id: str) -> GameEngine:
        """Create a new game.

        Args:
            game_id: Unique game ID.

        Returns:
            New GameEngine instance.
        """
        engine = GameEngine(game_id)
        self.games[game_id] = engine
        return engine

    def get_game_for_chat(self, chat_id: int) -> GameEngine | None:
        """Get the active game for a chat.

        Args:
            chat_id: Telegram chat ID.

        Returns:
            GameEngine or None.
        """
        # Simple mapping: use chat_id as game_id for now
        game_id = str(chat_id)

        # Check in-memory cache first
        if game_id in self.games:
            return self.games[game_id]

        # Try to load from database
        logger.info(f"Game {game_id} not in memory, attempting to load from database")
        t0 = time.perf_counter()
        engine = GameEngine.load_from_database(game_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if engine:
            self.games[game_id] = engine
            logger.info(
                f"Successfully loaded game {game_id} from database in {elapsed_ms:.0f}ms"
            )
        else:
            logger.info(
                f"No saved game found for {game_id} (checked in {elapsed_ms:.0f}ms)"
            )

        if elapsed_ms > 1500:
            logger.warning(
                f"Slow database load for game {game_id}: {elapsed_ms:.0f}ms (in_memory_games={len(self.games)})"
            )

        return engine

    def get_or_create_game_for_chat(self, chat_id: int) -> GameEngine:
        """Get or create a game for a chat.

        Args:
            chat_id: Telegram chat ID.

        Returns:
            GameEngine instance.
        """
        game_id = str(chat_id)

        # Check in-memory cache
        if game_id in self.games:
            return self.games[game_id]

        # Try to load from database
        logger.info(f"Game {game_id} not in memory, checking database...")
        t0 = time.perf_counter()
        engine = GameEngine.load_from_database(game_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if engine:
            self.games[game_id] = engine
            logger.info(
                f"Loaded existing game {game_id} from database in {elapsed_ms:.0f}ms"
            )
            return engine
        logger.info(
            f"No saved game found for {game_id} (checked in {elapsed_ms:.0f}ms)"
        )

        # Create new game
        logger.info(f"Creating new game {game_id}")
        self.games[game_id] = GameEngine(game_id)
        return self.games[game_id]
