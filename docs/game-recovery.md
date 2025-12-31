# Game Recovery & Error Resilience

## Overview

The TeleTycoon bot now automatically saves game state to the database after every action and can recover from errors, timeouts, or bot restarts without losing game progress.

## Features

### 🔄 Automatic State Persistence
- Game state is saved to database after every successful action
- No manual intervention required
- Works transparently in the background

### 🛡️ Error Recovery
- When errors occur (timeouts, crashes, etc.), the current game state is saved
- Games can be resumed from where they left off
- Users receive helpful messages about recovery options

### 💾 Database-Backed Games
- All games are stored in SQLite database (configured via `.env`)
- Games persist across bot restarts
- Automatic loading from database when accessed

## How It Works

### When Playing
1. **Action Executed** → Game state automatically saved to database
2. **Error Occurs** → Current state saved (if possible)
3. **Bot Restarts** → Games automatically loaded when accessed

### Game Lifecycle

```
┌─────────────┐
│  /newgame   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Game Created   │ ─────► Saved to DB
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Action Executed │ ─────► Saved to DB
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Error/Timeout   │ ─────► State Saved
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   Bot Restart   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ /status or      │ ─────► Loaded from DB
│ /resume         │
└─────────────────┘
```

## Commands

### /resume
Explicitly reload a game from the database. Useful if:
- You want to ensure you have the latest saved state
- The bot had an error and you want to continue
- You're not sure if the game is loaded correctly

**Usage:**
```
/resume
```

**Response:**
```
✅ Game resumed!

📊 Game Status
Phase: Stock Round 2
...
```

### /status
View current game state. Will automatically load from database if game is not in memory.

## Error Messages

### Timeout Error
```
❌ An error occurred, but your game has been saved.
Use /status to continue playing.
```
**Action:** Just use `/status` or continue playing normally.

### Game Not Found
```
❌ No saved game found for this chat.
Use /newgame to create a new game.
```
**Action:** Start a new game with `/newgame`.

## Technical Details

### Automatic Loading
When you execute any command, the bot:
1. Checks if game is in memory
2. If not, tries to load from database
3. Caches in memory for performance

### What Gets Saved
- Game phase and round numbers
- All player cash and holdings
- Company states and treasuries
- Train ownership
- Stock market positions
- Complete action history

### When State Is Saved
- When game starts (`/startgame`)
- After each successful action (buy, sell, pass, etc.)
- When an error occurs (best effort)

## Examples

### Scenario 1: Timeout During Play
```
You: /actions
Bot: [Shows actions, then timeout error]
     ❌ An error occurred, but your game has been saved.
     Use /status to continue playing.

You: /status
Bot: ✅ Game state loaded
     [Shows current game state]
     
You: /actions
Bot: [Shows available actions - game continues normally]
```

### Scenario 2: Bot Restart
```
[Bot restarts]

You: /status
Bot: [Automatically loads game from database]
     📊 Game Status
     Phase: Operating Round 3
     ...
```

### Scenario 3: Explicit Resume
```
You: /resume
Bot: ✅ Game resumed!
     
     📊 Game Status
     Phase: Stock Round 1
     Current Player: Alice
     ...
```

## Configuration

Ensure your `.env` file has the database path configured:

```env
DATABASE_PATH=./data/teletycoon.db
```

## Troubleshooting

### "No saved game found"
- The game might not have been started yet - use `/newgame`
- Database file might be missing - check `DATABASE_PATH` in `.env`
- Game might have been deleted - use `/newgame` to start fresh

### Game state seems wrong
1. Use `/resume` to force reload from database
2. Check `/status` to see current state
3. If still wrong, contact support with game details

## Benefits

✅ **Never lose progress** - All games automatically saved  
✅ **Resilient to errors** - Timeouts don't lose state  
✅ **Bot can restart** - Games survive restarts  
✅ **Multiple games** - Each chat has its own saved game  
✅ **Transparent** - Works automatically, no user action needed  

## Development Notes

### For Contributors

**GameEngine.load_from_database(game_id)**
- Class method to load a game from database
- Returns GameEngine instance or None
- Automatically used by bot when accessing games

**GameEngine.save()**
- Saves current state to database
- Called automatically after actions
- Safe to call multiple times

**Error Handler**
- Saves game state when errors occur
- Provides helpful recovery messages
- Logs errors for debugging

### Testing
Run the recovery test:
```bash
python test_game_recovery.py
```

This verifies:
- Games are saved correctly
- Games can be loaded after deletion
- Loaded games are playable
- State is preserved accurately
