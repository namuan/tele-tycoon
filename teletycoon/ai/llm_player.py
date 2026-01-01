"""LLM-based AI player for TeleTycoon."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState

from .base_ai import BaseAI


class LLMPlayer(BaseAI):
    """AI player powered by Large Language Model.

    Uses an LLM to make strategic decisions based on game state.
    Can provide human-like reasoning for its moves.

    Attributes:
        player_id: ID of the player this AI controls.
        state: Reference to game state.
        last_reasoning: Explanation of last decision.
        personality: Strategy personality for the LLM.
        llm_client: Client for LLM API calls.
    """

    def __init__(
        self,
        player_id: str,
        state: "GameState",
        personality: str = "balanced",
        llm_client: Any = None,
    ) -> None:
        """Initialize LLM player.

        Args:
            player_id: Player ID this AI controls.
            state: The game state.
            personality: Strategy personality (balanced, aggressive, conservative).
            llm_client: Client for making LLM API calls.
        """
        super().__init__(player_id, state)
        self.last_reasoning = ""
        self.personality = personality
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            f"LLMPlayer initialized for player {player_id} with personality={personality}"
        )

    def choose_action(self, available_actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose an action using LLM reasoning.

        Args:
            available_actions: List of valid action dictionaries.

        Returns:
            The chosen action dictionary.
        """
        self.logger.debug(
            f"LLM choosing action from {len(available_actions)} available actions"
        )

        if not available_actions:
            self.last_reasoning = "No actions available"
            self.logger.info("No actions available for LLM, passing by default")
            return {"type": "pass"}

        # Build prompt for LLM
        prompt = self._build_prompt(available_actions)

        # If no LLM client, fall back to first action
        if not self.llm_client:
            self.last_reasoning = "LLM not configured, using default action"
            self.logger.warning(
                "LLM client not configured, using first available action"
            )
            return available_actions[0]

        try:
            self.logger.debug("Calling LLM for action decision")
            response = self._call_llm(prompt)
            action, reasoning = self._parse_response(response, available_actions)
            self.last_reasoning = reasoning
            self.logger.info(
                f"LLM chose action: {action.get('type', 'unknown')} - {reasoning[:100]}"
            )
            return action
        except Exception as e:
            self.logger.error(
                f"LLM error occurred: {e}, falling back to default action"
            )
            self.last_reasoning = f"LLM error: {e}, using default"
            return available_actions[0]

    def get_reasoning(self) -> str:
        """Get explanation for last decision.

        Returns:
            String explaining the decision reasoning.
        """
        return self.last_reasoning

    def _build_prompt(self, actions: list[dict[str, Any]]) -> str:
        """Build prompt for LLM with game state and options.

        Args:
            actions: Available actions.

        Returns:
            Formatted prompt string.
        """
        player = self.get_player()
        player_name = player.name if player else self.player_id
        player_cash = player.cash if player else 0

        game_context = self._get_game_context()
        action_list = self._format_actions(actions)

        stock_round_checklist = """STOCK ROUND CHECKLIST (1889 / Beginner-Safe)
Goal: Improve your position without becoming responsible for a future disaster.

Before You Buy Anything
☐ Do I already control a company? → If yes, be very cautious starting another one. If no, starting one is usually correct.
☐ If I buy this share, could I accidentally become President later? → If yes and I don’t want that company, don’t buy.
☐ How many turns until the next train type appears? → If “soon,” assume everything will get more expensive.

When Starting a Company
☐ Can this company afford its first two trains without my money? → If no, don’t start it yet.
☐ Does its home location point toward real revenue, not just open space? → If no, reconsider.
☐ Am I emotionally ready to be blamed for this company? → If no, don’t start it.

When Buying Shares
☐ Does buying this share give me control, or just risk? → Control is good. Risk without control is bad.
☐ Am I buying this because it’s “cheap,” or because it helps me win? → Cheap is a trap.
☐ Will this purchase make someone else’s life worse right now? → If yes, that’s often correct.

When Selling Shares
☐ Will this force someone else to deal with a problem before they’re ready? → If yes, selling is strong.
☐ Am I selling because I need cash, or because I’m panicking? → Panic selling usually loses games.
☐ After I sell, am I safe from becoming President? → Double-check. Always.

Before Passing
☐ Could someone use my pass to hurt me? → If yes, consider acting first.
☐ Do I understand why I’m passing? → “Because I don’t know what to do” is not a reason.
"""

        operating_round_checklist = """OPERATING ROUND CHECKLIST (1889 / Beginner-Safe)
Goal: Keep your companies alive without chaining yourself to them.

Track Laying
☐ Does this tile increase current or near-future revenue? → Flexibility without income is fake.
☐ Does this placement block someone or protect me from being blocked? → If yes, that’s a bonus.
☐ Will I regret this tile in 3 rounds? → If yes, stop and rethink.
🟥 Beginner rule: Always aim toward money, not options.

Route Selection
☐ Am I running the highest legal route right now? → “Saving it for later” is usually wrong.
☐ Does this route support the next train, not just the current one? → Think one train ahead.

Dividends Decision
☐ Does this company need cash for a train soon? → If yes, withhold.
☐ Is the stock price already high enough to sell later? → If yes, paying is optional.
☐ Am I paying dividends just to feel good? → That’s a mistake.
🟥 Beginner rule: Early game withhold, mid-game decide, late game pay.

Train Buying (CRITICAL)
☐ What is the next train this company will be forced to buy? → Not the one available now—the next one.
☐ Can the company afford it without me? → If no, danger.
☐ If trains rust this round, do I survive? → If you haven’t checked, you’re already late.
☐ Would buying this train help my opponents more than me? → If yes, delay if legal.
🟥 Beginner rule: Never buy a train just because you can.

End of Company Turn
☐ Is this company now safer, or more fragile? → Fragile companies attract attacks.
☐ Would I be okay losing control of this company next Stock Round? → If no, prepare defenses.
"""

        checklist = (
            stock_round_checklist
            if self.state.round_type.value == "stock"
            else operating_round_checklist
        )

        personality_desc = {
            "aggressive": "You play aggressively, taking risks for higher rewards. You prefer to control companies and dominate the stock market.",
            "conservative": "You play conservatively, minimizing risk. You prefer steady gains and strong defensive positions.",
            "balanced": "You balance risk and reward, adapting your strategy to the situation.",
        }.get(self.personality, "You play a balanced strategy.")

        prompt = f"""You are playing an 18XX railroad game (1889 - Shikoku).

PERSONALITY: {personality_desc}

CURRENT GAME STATE:
{game_context}

YOUR SITUATION:
- Player: {player_name}
- Cash: ¥{player_cash}
- Round: {"Stock Round" if self.state.round_type.value == "stock" else "Operating Round"}

SURVIVAL CHECKLIST (use this as your decision rubric):
{checklist}

AVAILABLE ACTIONS:
{action_list}

Choose the best action and explain your reasoning.

Rules for choosing:
- Use the checklist as a filter. If an item doesn’t apply to this implementation or to the available actions, ignore it.
- Prioritize avoiding future disasters (unwanted presidency, forced train buys, insolvency) over small short-term gains.
- If uncertain, prefer the safest non-losing move that keeps flexibility and liquidity.

Respond with valid JSON only in this format:
{{
    "action_index": <number from 1 to N>,
    "reasoning": "<1-3 sentences, citing 1-2 checklist items that drove the choice>"
}}

Consider:
1. Cash flow and liquidity
2. Company control and presidency
3. Train rust schedule
4. Stock price manipulation
5. Future round implications

One sentence to remember: “You don’t lose 18XX because of one bad move. You lose because you didn’t notice a bad future forming.”
"""
        return prompt

    def _get_game_context(self) -> str:
        """Get formatted game context."""
        lines = []

        # Players
        lines.append("Players:")
        for pid in self.state.player_order:
            p = self.state.players.get(pid)
            if p:
                lines.append(f"  {p.name}: ¥{p.cash}")

        # Active companies
        lines.append("\nCompanies:")
        for cid, company in self.state.companies.items():
            if company.is_floated:
                pres = self.state.players.get(company.president_id or "")
                pres_name = pres.name if pres else "None"
                trains = len([t for t in company.trains if not t.rusted])
                lines.append(
                    f"  {cid}: Price ¥{company.stock_price}, "
                    f"Treasury ¥{company.treasury}, "
                    f"President: {pres_name}, "
                    f"Trains: {trains}"
                )

        # Phase
        lines.append(f"\nGame Phase: {self.state.train_depot.current_phase}")

        return "\n".join(lines)

    def _format_actions(self, actions: list[dict[str, Any]]) -> str:
        """Format actions as numbered list."""
        lines = []
        for i, action in enumerate(actions, 1):
            desc = action.get("description", action.get("type", "Unknown"))
            lines.append(f"{i}. {desc}")
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM API with prompt.

        Args:
            prompt: The prompt to send.

        Returns:
            LLM response text.
        """
        import os

        if not self.llm_client:
            raise ValueError("LLM client not configured")

        # Use httpx client for OpenRouter API
        if hasattr(self.llm_client, "post"):
            model = os.getenv(
                "OPENROUTER_PRIMARY_MODEL",
                "xiaomi/mimo-v2-flash:free",
            )

            self.logger.debug(f"Calling OpenRouter API with model: {model}")

            try:
                response = self.llm_client.post(
                    "/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert 18XX board game player who uses survival checklists to avoid future disasters (unwanted presidency, train rush/rust, insolvency). Return valid JSON only with keys 'action_index' (1-based) and 'reasoning'. Do not include markdown or extra text.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()
                self.logger.debug(f"OpenRouter API response: {data}")
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                self.logger.error(f"OpenRouter API error: {e}")
                if hasattr(e, "response"):
                    self.logger.error(f"Response status: {e.response.status_code}")
                    self.logger.error(f"Response body: {e.response.text}")
                raise
        elif hasattr(self.llm_client, "chat"):
            # OpenAI-style client
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert 18XX board game player who uses survival checklists to avoid future disasters (unwanted presidency, train rush/rust, insolvency). Return valid JSON only with keys 'action_index' (1-based) and 'reasoning'. Do not include markdown or extra text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        elif callable(self.llm_client):
            # Simple callable
            return self.llm_client(prompt)
        else:
            raise ValueError("Unsupported LLM client type")

    def _parse_response(
        self, response: str, actions: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        """Parse LLM response to extract action.

        Args:
            response: LLM response text.
            actions: Available actions.

        Returns:
            Tuple of (chosen action, reasoning).
        """
        try:
            # Try to parse JSON from response
            # Handle potential markdown code blocks
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)
            action_index = data.get("action_index", 1) - 1
            reasoning = data.get("reasoning", "No reasoning provided")

            if 0 <= action_index < len(actions):
                return actions[action_index], reasoning
            else:
                return actions[0], f"Invalid index, defaulting. {reasoning}"

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # Try to extract action from text
            for i, action in enumerate(actions):
                if action.get("type", "") in response.lower():
                    return action, f"Parsed from text: {response[:100]}"

            return actions[0], f"Could not parse response: {e}"

    def set_personality(self, personality: str) -> None:
        """Change the AI's personality.

        Args:
            personality: New personality (aggressive, conservative, balanced).
        """
        if personality in ("aggressive", "conservative", "balanced"):
            self.personality = personality

    def get_teaching_explanation(self, action: dict[str, Any]) -> str:
        """Get a teaching-mode explanation for an action.

        Args:
            action: The action to explain.

        Returns:
            Detailed explanation suitable for teaching.
        """
        action_type = action.get("type", "unknown")

        explanations = {
            "start_company": (
                "Starting a company requires buying the president's certificate "
                "(2 shares) at the chosen par value. This gives you control of "
                "the company and its initial treasury."
            ),
            "buy_ipo": (
                "Buying from IPO adds money to the company's treasury, "
                "strengthening it. This is generally better than buying "
                "from the market for companies you support."
            ),
            "buy_market": (
                "Buying from the market removes shares from public sale "
                "without adding to the company treasury. Good for companies "
                "with enough treasury already."
            ),
            "sell": (
                "Selling shares moves them to the market and drops the "
                "stock price. Consider the impact on stock value and "
                "whether you might dump your presidency."
            ),
            "pass": (
                "Passing means you're done for this stock round. "
                "Once all players pass, we move to operating rounds."
            ),
            "run_trains": (
                "Running trains calculates revenue based on routes. "
                "You then choose to pay dividends (increases stock price) "
                "or withhold (keeps cash in treasury)."
            ),
            "buy_train": (
                "Companies need trains to run! Watch the rust schedule - "
                "when newer trains appear, older ones are removed from the game."
            ),
        }

        base = explanations.get(action_type, "Consider how this affects your position.")
        return f"💡 {base}\n\n{self.last_reasoning}"
