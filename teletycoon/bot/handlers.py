"""Command and game handlers for Telegram bot."""

import logging
import uuid
from typing import TYPE_CHECKING, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from .telegram_bot import TeleTycoonBot

from teletycoon.models.player import PlayerType
from teletycoon.renderer.state_renderer import StateRenderer

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handlers for bot commands.

    Attributes:
        bot: Reference to the main bot instance.
    """

    def __init__(self, bot: "TeleTycoonBot") -> None:
        """Initialize command handlers.

        Args:
            bot: The TeleTycoonBot instance.
        """
        self.bot = bot

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome_text = """🚂 Welcome to TeleTycoon! 🚂

An 18XX railroad game (1889 - Shikoku) on Telegram!

Commands:
/newgame - Create a new game
/joingame - Join an existing game
/startgame - Start the game (needs 2-6 players)
/status - View current game state
/portfolio - View your holdings
/companies - View all companies
/actions - See available actions
/pass - Pass your turn
/addai - Add an AI player
/help - Show this help

Have fun building your railroad empire! 🚂💰"""

        await update.message.reply_text(welcome_text)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await self.start(update, context)

    async def new_game(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /newgame command."""
        chat_id = update.effective_chat.id
        user = update.effective_user

        # Check if game already exists
        existing = self.bot.get_game_for_chat(chat_id)
        if existing and existing.state.players:
            await update.message.reply_text(
                "⚠️ A game already exists in this chat. " "Use /endgame to end it first."
            )
            return

        # Create new game
        engine = self.bot.get_or_create_game_for_chat(chat_id)

        # Add the creator as first player
        player_id = str(user.id)
        player_name = user.first_name or f"Player_{user.id}"

        engine.add_player(
            player_id=player_id,
            name=player_name,
            player_type=PlayerType.HUMAN,
            telegram_id=user.id,
        )

        await update.message.reply_text(
            f"🎮 New game created!\n\n"
            f"👤 {player_name} has joined.\n\n"
            f"Other players can use /joingame to join.\n"
            f"Use /startgame when everyone is ready (2-6 players)."
        )

    async def join_game(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /joingame command."""
        chat_id = update.effective_chat.id
        user = update.effective_user

        engine = self.bot.get_game_for_chat(chat_id)
        if not engine:
            await update.message.reply_text(
                "❌ No game exists. Use /newgame to create one."
            )
            return

        if engine.state.current_phase.value != "setup":
            await update.message.reply_text(
                "❌ Game has already started. Wait for the next game."
            )
            return

        player_id = str(user.id)

        # Check if already joined
        if player_id in engine.state.players:
            await update.message.reply_text("You've already joined this game!")
            return

        if len(engine.state.players) >= 6:
            await update.message.reply_text("❌ Game is full (max 6 players).")
            return

        player_name = user.first_name or f"Player_{user.id}"
        engine.add_player(
            player_id=player_id,
            name=player_name,
            player_type=PlayerType.HUMAN,
            telegram_id=user.id,
        )

        player_list = ", ".join(p.name for p in engine.state.players.values())

        await update.message.reply_text(
            f"✅ {player_name} has joined!\n\n"
            f"Players ({len(engine.state.players)}): {player_list}\n\n"
            f"Use /startgame when ready."
        )

    async def start_game(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /startgame command."""
        chat_id = update.effective_chat.id
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text(
                "❌ No game exists. Use /newgame to create one."
            )
            return

        if len(engine.state.players) < 2:
            await update.message.reply_text(
                "❌ Need at least 2 players. Use /addai to add AI players."
            )
            return

        try:
            engine.start_game()

            renderer = StateRenderer(engine.state)
            snapshot = renderer.render_full_snapshot()

            await update.message.reply_text(f"🎮 Game started!\n\n{snapshot}")

            # Prompt first player
            await self._prompt_current_player(update, context, engine)

        except Exception as e:
            await update.message.reply_text(f"❌ Error starting game: {e}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        chat_id = update.effective_chat.id
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text(
                "❌ No game exists. Use /newgame to create one."
            )
            return

        renderer = StateRenderer(engine.state)
        snapshot = renderer.render_full_snapshot()

        await update.message.reply_text(snapshot)

    async def portfolio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /portfolio command."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text("❌ No game exists.")
            return

        player_id = str(user.id)
        if player_id not in engine.state.players:
            await update.message.reply_text("❌ You're not in this game.")
            return

        from teletycoon.renderer.stock_renderer import StockRenderer

        renderer = StockRenderer(engine.state)
        portfolio = renderer.render_player_portfolio(player_id)

        await update.message.reply_text(portfolio)

    async def companies(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /companies command."""
        chat_id = update.effective_chat.id
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text("❌ No game exists.")
            return

        from teletycoon.renderer.stock_renderer import StockRenderer

        renderer = StockRenderer(engine.state)
        table = renderer.render_stock_table()

        await update.message.reply_text(table)

    async def actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /actions command."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text("❌ No game exists.")
            return

        player_id = str(user.id)
        if player_id not in engine.state.players:
            await update.message.reply_text("❌ You're not in this game.")
            return

        # Check if it's this player's turn
        current = engine.state.current_player
        if not current or current.id != player_id:
            await update.message.reply_text("⏳ It's not your turn.")
            return

        actions = engine.get_available_actions()
        if not actions:
            await update.message.reply_text("No actions available.")
            return

        renderer = StateRenderer(engine.state)
        prompt = renderer.render_action_prompt(actions, current.name)

        # Create inline keyboard for actions
        keyboard = self._create_action_keyboard(actions)

        await update.message.reply_text(prompt, reply_markup=keyboard)

    async def pass_turn(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /pass command."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text("❌ No game exists.")
            return

        player_id = str(user.id)
        current = engine.state.current_player

        if not current or current.id != player_id:
            await update.message.reply_text("⏳ It's not your turn.")
            return

        result = engine.execute_action("pass")

        renderer = StateRenderer(engine.state)
        response = renderer.render_action_result(result)

        await update.message.reply_text(response)

        # Prompt next player
        await self._prompt_current_player(update, context, engine)

    async def add_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /addai command."""
        chat_id = update.effective_chat.id
        engine = self.bot.get_game_for_chat(chat_id)

        if not engine:
            await update.message.reply_text("❌ No game exists. Use /newgame first.")
            return

        if engine.state.current_phase.value != "setup":
            await update.message.reply_text("❌ Cannot add AI after game has started.")
            return

        if len(engine.state.players) >= 6:
            await update.message.reply_text("❌ Game is full.")
            return

        # Add AI player
        ai_num = (
            len(
                [
                    p
                    for p in engine.state.players.values()
                    if p.player_type == PlayerType.RULE_BASED_AI
                ]
            )
            + 1
        )

        ai_id = f"ai_{uuid.uuid4().hex[:8]}"
        ai_name = f"AI Player {ai_num}"

        engine.add_player(
            player_id=ai_id,
            name=ai_name,
            player_type=PlayerType.RULE_BASED_AI,
        )

        await update.message.reply_text(
            f"🤖 {ai_name} has joined!\n\n" f"Players: {len(engine.state.players)}"
        )

    async def end_game(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /endgame command."""
        chat_id = update.effective_chat.id

        if str(chat_id) in self.bot.games:
            del self.bot.games[str(chat_id)]
            await update.message.reply_text("🏁 Game ended.")
        else:
            await update.message.reply_text("No game to end.")

    def _create_action_keyboard(
        self, actions: list[dict[str, Any]]
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard for actions."""
        buttons = []

        for i, action in enumerate(actions[:8]):  # Limit to 8 buttons
            action_type = action.get("type", "")
            desc = action.get("description", action_type)

            # Shorten description if needed
            if len(desc) > 30:
                desc = desc[:27] + "..."

            callback_data = f"action:{i}"
            buttons.append([InlineKeyboardButton(desc, callback_data=callback_data)])

        return InlineKeyboardMarkup(buttons)

    async def _prompt_current_player(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        engine: Any,
    ) -> None:
        """Prompt the current player for their turn."""
        current = engine.state.current_player
        if not current:
            return

        # Check if AI player
        if current.player_type == PlayerType.RULE_BASED_AI:
            await self._process_ai_turn(update, context, engine, current)
            return

        # Human player
        actions = engine.get_available_actions()
        if not actions:
            return

        renderer = StateRenderer(engine.state)
        prompt = renderer.render_action_prompt(actions, current.name)
        keyboard = self._create_action_keyboard(actions)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=prompt,
            reply_markup=keyboard,
        )

    async def _process_ai_turn(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        engine: Any,
        ai_player: Any,
    ) -> None:
        """Process an AI player's turn."""
        from teletycoon.ai.rule_based_ai import RuleBasedAI

        ai = RuleBasedAI(ai_player.id, engine.state)
        actions = engine.get_available_actions()

        if not actions:
            return

        chosen = ai.choose_action(actions)
        reasoning = ai.get_reasoning()

        # Execute the action
        result = engine.execute_action(**chosen)

        # Report AI action
        renderer = StateRenderer(engine.state)
        msg = f"🤖 {ai_player.name}: {renderer.render_action_result(result)}\n💭 {reasoning}"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
        )

        # Continue if next player is also AI
        await self._prompt_current_player(update, context, engine)


class GameHandlers:
    """Handlers for game interactions.

    Attributes:
        bot: Reference to the main bot instance.
    """

    def __init__(self, bot: "TeleTycoonBot") -> None:
        """Initialize game handlers.

        Args:
            bot: The TeleTycoonBot instance.
        """
        self.bot = bot

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        user_id = str(update.effective_user.id)

        engine = self.bot.get_game_for_chat(chat_id)
        if not engine:
            await query.edit_message_text("❌ Game not found.")
            return

        # Check if it's this user's turn
        current = engine.state.current_player
        if not current or current.id != user_id:
            await query.edit_message_text("⏳ It's not your turn.")
            return

        # Parse callback data
        data = query.data
        if data.startswith("action:"):
            action_index = int(data.split(":")[1])
            actions = engine.get_available_actions()

            if 0 <= action_index < len(actions):
                action = actions[action_index]
                await self._execute_action(update, context, engine, action)

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle text messages for game actions."""
        chat_id = update.effective_chat.id
        user_id = str(update.effective_user.id)
        text = update.message.text.strip()

        engine = self.bot.get_game_for_chat(chat_id)
        if not engine:
            return  # No game, ignore message

        # Check if it's this user's turn
        current = engine.state.current_player
        if not current or current.id != user_id:
            return

        # Try to parse as action number
        try:
            action_index = int(text) - 1
            actions = engine.get_available_actions()

            if 0 <= action_index < len(actions):
                action = actions[action_index]
                await self._execute_action(update, context, engine, action)
        except ValueError:
            # Try to match action by keyword
            await self._handle_keyword_action(update, context, engine, text.lower())

    async def _execute_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        engine: Any,
        action: dict[str, Any],
    ) -> None:
        """Execute a game action."""
        result = engine.execute_action(**action)

        renderer = StateRenderer(engine.state)
        response = renderer.render_action_result(result)

        if update.callback_query:
            await update.callback_query.edit_message_text(response)
        else:
            await update.message.reply_text(response)

        # Check for game end
        if engine.state.current_phase.value == "game_end":
            end_msg = renderer.render_game_end()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=end_msg,
            )
            return

        # Prompt next player
        command_handlers = CommandHandlers(self.bot)
        await command_handlers._prompt_current_player(update, context, engine)

    async def _handle_keyword_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        engine: Any,
        keyword: str,
    ) -> None:
        """Handle action by keyword matching."""
        actions = engine.get_available_actions()

        for action in actions:
            action_type = action.get("type", "")
            desc = action.get("description", "").lower()

            if keyword in action_type or keyword in desc:
                await self._execute_action(update, context, engine, action)
                return

        # No match found
        await update.message.reply_text(
            "❓ Didn't understand that. Use /actions to see options."
        )
