"""Main entry point for Tele Tycoon."""

import logging
import os
import sys

from dotenv import load_dotenv


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Run the Tele Tycoon Telegram bot."""
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("🚂 Starting TeleTycoon Bot...")

    # Check for required environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN environment variable is required. "
            "Set it in .env file or environment."
        )
        sys.exit(1)

    # Import and run bot
    from teletycoon.bot.telegram_bot import TeleTycoonBot

    try:
        bot = TeleTycoonBot(token)
        bot.setup()
        bot.run()
    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")
        sys.exit(1)


def run_demo() -> None:
    """Run a demo game without Telegram."""
    from teletycoon.engine.game_engine import GameEngine
    from teletycoon.models.player import PlayerType
    from teletycoon.renderer.state_renderer import StateRenderer

    print("🚂 TeleTycoon 1889 Demo 🚂")
    print("=" * 40)

    # Create a game
    engine = GameEngine("demo_game")

    # Add players
    engine.add_player("p1", "Alice", PlayerType.HUMAN)
    engine.add_player("p2", "Bob", PlayerType.RULE_BASED_AI)
    engine.add_player("p3", "Charlie", PlayerType.RULE_BASED_AI)

    # Start the game
    engine.start_game()

    # Render initial state
    renderer = StateRenderer(engine.state)
    print(renderer.render_full_snapshot())
    print()

    # Show available actions
    actions = engine.get_available_actions()
    print(renderer.render_action_prompt(actions, engine.state.current_player.name))


if __name__ == "__main__":
    # Check if demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        main()
