# **TeleTycoon :: Telegram 18XX Game – Full System Plan**

---

## **1️⃣ Project Overview**

**Goal:**
Develop a digital, turn-based 18XX game playable on Telegram with the following features:

* Play against humans, rule-based AI, or LLM-controlled players
* Beginner-friendly prompts and guided decisions
* Persistent state storage with SQLite
* Text + emoji-based visualization for board, stock, and trains
* Turn-based mechanics: Stock Rounds → Operating Rounds → Stock Rounds
* Optional teaching mode with reasoning explanations

---

## **2️⃣ Architecture Overview**

```
                  ┌─────────────────────────┐
                  │  Telegram User Chat     │
                  │ (Human Player Input)   │
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ Telegram Bot Interface  │
                  │ (Python, python-telegram-bot) │
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ Turn Manager            │
                  │ - Tracks SR/OR          │
                  │ - Current Player        │
                  │ - Validates input       │
                  │ - Enforces turn order   │
                  └───────────┬────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
      ┌─────────────────┐         ┌─────────────────┐
      │ Game Engine      │         │ Player AI/LLM   │
      │ - Board state    │         │ - Receives game │
      │ - Companies      │         │   state         │
      │ - Stocks/Trains  │         │ - Returns moves │
      │ - Revenue calc   │         │ - Optional reasoning │
      │ - Consequence calc│        │ - Rule-checking │
      └─────────┬────────┘         └─────────┬───────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    ┌────────────────────┐
                    │ SQLite Database    │
                    │ - Players          │
                    │ - Game state       │
                    │ - Companies        │
                    │ - Board/tiles      │
                    │ - Stocks, Trains   │
                    └─────────┬──────────┘
                              ▼
                    ┌────────────────────┐
                    │ State Renderer     │
                    │ - Text + emoji maps│
                    │ - Stock tables     │
                    │ - Prompts for turn │
                    │ - Consequence highlights│
                    └─────────┬──────────┘
                              ▼
                  ┌─────────────────────────┐
                  │ Telegram User Chat      │
                  │ (Snapshot + Prompt)    │
                  └─────────────────────────┘
```

---

## **3️⃣ Feature Set**

### **Core Gameplay**

* Stock Rounds:

  * Buy/sell shares
  * Start companies (president assignment)
  * Update stock price & treasury
  * Enforce legal actions
* Operating Rounds:

  * Lay tracks (text-based map)
  * Run trains (calculate revenue)
  * Pay dividends or withhold
  * Buy trains
  * Handle train rust / forced purchases
* Turn order enforcement
* Game end & scoring

### **Player Types**

1. **Human** – makes choices via Telegram messages
2. **Rule-based AI** – heuristic decisions based on game state
3. **LLM-controlled player** – human-like reasoning and strategic decisions

### **Interactive Features**

* Predefined action options to reduce paralysis
* Text + emoji visualizations for map, stock, treasury, and trains
* Immediate feedback with consequences explained
* Optional “teaching mode” with reasoning per move

### **Player & Game Management**

* Telegram ID registration
* Game lobby and invitations
* 2–5 players per game
* Save/load games
* Turn notifications

---

## **4️⃣ Development Roadmap**

**Phase 1: Core Game Engine**

* Implement 1889 rules for stock rounds and operating rounds
* Train purchase and rust logic
* Company ownership & treasury management
* Revenue calculation and dividends logic

**Phase 2: SQLite Integration**

* Store:

  * Player data
  * Game state
  * Company info
  * Board / tiles
  * Stock info
  * Train inventory
* Ensure crash recovery

**Phase 3: Telegram Bot Integration**

* Receive structured player input
* Send game snapshots + guided prompts
* Enforce turn order

**Phase 4: AI/LLM Player Integration**

* Rule-based AI: implement heuristics for stock & operating decisions
* LLM Player:

  * Pass full game state + available actions
  * Receive move and optional reasoning
  * Validate legal actions via game engine

**Phase 5: Visualization & UX**

* ASCII + emoji board rendering
* Stock tables with emoji cues
* Guided prompts with consequences
* Beginner-friendly tips between rounds

**Phase 6: Multiplayer Management**

* Lobby creation & invitations
* Turn notifications
* Save/resume ongoing games

**Phase 7: Optional Advanced Features**

* Leaderboards
* Multiple 18XX variants
* AI difficulty levels
* Turn timers / automatic skips

---

## **5️⃣ Sample Turn Flow: Human + AI/LLM Opponent**

**Scenario:** Player A (human) → Player B (LLM) → Stock Round

```
1. Telegram Bot sends snapshot + prompt to Player A
2. Player A replies with choice (e.g., “Buy 1 IY”)
3. Turn Manager validates input
4. Game Engine updates:
   - Cash
   - Treasury
   - Stock ownership
   - Trains / rust
   - Consequences
5. SQLite saves game state
6. State Renderer generates new snapshot:
   - Map
   - Stock tables
   - Train info
   - Consequence explanation
7. Telegram Bot sends snapshot + prompt to next player
8. Player B (LLM) receives prompt:
   - LLM analyzes game state
   - Returns move + optional reasoning
9. Turn Manager validates LLM move
10. Repeat steps 4–7
```

**Emoji Example in Snapshot:**

```
========================
💰 Player Cash:
A: ¥400 | B: ¥400 | C: ¥500

🚂 Companies:
IY – President: A | Treasury: ¥230 | 2-train x1
SR – President: B | Treasury: ¥220 | 2-train x1

📈 Stock Prices:
Company | Price | A | B | C
IY      | 80    | 2 | 1 | 1
SR      | 110   | 0 | 2 | 0

🗺 Map:
[IY] === o === o === [CITY] === o === [SR]

🔜 Next Train Available: 3-train (¥180)
========================

Options for Player B:
1️⃣ Buy 1 share IY
2️⃣ Buy 2 shares SR
3️⃣ Sell 1 share IY
4️⃣ Pass
```

---

## **6️⃣ AI / LLM Player Integration**

**Rule-Based AI:**

* Stock Round: buy shares for control, avoid bankruptcy
* Operating Round: lay track toward revenue, buy trains at optimal timing
* Heuristic decision tree + randomness

**LLM Player:**

* Receives **full game state**
* Receives **available options**
* Receives **personality / strategy instructions**
* Returns **choice + optional reasoning**
* Game Engine validates move to ensure legality

---

## **7️⃣ Key Design Considerations**

1. **Atomic Turn Processing** – action → update → snapshot → next player
2. **Persistence with SQLite** – crash recovery, save/load games
3. **Clear Visualization** – emoji + text board, stock, treasury, trains
4. **Guided Input** – predefined options, reduces beginner errors
5. **Feedback / Teaching Mode** – reasoning explanations, red-flag warnings
6. **Configurable Opponents** – human, AI, LLM; adjustable difficulty and strategy

---

## **8️⃣ Next Steps Before Coding**

* Finalize board tiles and map layout
* Define train types, costs, and rust schedule
* Create SQLite database schema for:

  * Players
  * Companies
  * Game state
  * Stocks
  * Trains
* Create text + emoji templates for:

  * Stock Round
  * Operating Round
  * Game snapshot
  * Player prompt
* Develop **rule-based AI**
* Develop **LLM prompt templates** with constraints

---

✅ **Outcome:**
Following this plan, you can build a Telegram-based 1889 game with **full multiplayer, AI, and LLM support**, with visual clarity, beginner-friendly guidance, and persistence, ready for coding and iteration.

---

If you want, I can **draft the exact SQLite schema with all tables, columns, and relationships**, fully optimized for rule enforcement, AI/LLM integration, and Telegram gameplay.

Do you want me to do that next?
