# Database Persistence - Fix Summary

## Issues Found

### 1. Database Path Not Using Environment Variable ❌
**Problem:** The database code was using a hardcoded `DEFAULT_DB_PATH` instead of reading from the `DATABASE_PATH` environment variable specified in `.env`.

**Location:** `teletycoon/database/base.py`

**Fix:** Added `get_db_path()` function that:
- Reads `DATABASE_PATH` from environment variables
- Falls back to default path if not set
- Updated `get_engine()` to use this function

### 2. Game States Never Saved to Database ❌
**Problem:** Although a complete `GameRepository.save_game_state()` method existed, it was **never called** anywhere in the codebase. Games were running entirely in memory.

**Location:** `teletycoon/engine/game_engine.py`

**Fix:** 
- Added `repository` attribute to `GameEngine`
- Added `enable_persistence` parameter to control database saving
- Added `save()` method to persist game state
- Modified `start_game()` to save initial state
- Modified `execute_action()` to save after each successful action

## Changes Made

### File: `teletycoon/database/base.py`
```python
# Added environment variable support
def get_db_path() -> Path:
    """Get database path from environment or use default."""
    db_path_str = os.getenv("DATABASE_PATH")
    if db_path_str:
        return Path(db_path_str)
    return DEFAULT_DB_PATH
```

### File: `teletycoon/engine/game_engine.py`
```python
# Added database persistence
from teletycoon.database import GameRepository, get_session

class GameEngine:
    def __init__(self, game_id: str, enable_persistence: bool = True):
        # ... existing code ...
        self.enable_persistence = enable_persistence
        self.repository = None
        
        if enable_persistence:
            session = next(get_session())
            self.repository = GameRepository(session)
    
    def save(self) -> None:
        """Save the current game state to database."""
        if self.enable_persistence and self.repository:
            self.repository.save_game_state(self.state)
    
    # save() is now called in:
    # - start_game() - saves initial game state
    # - execute_action() - saves after each successful action
```

## Verification

Created `test_db_save.py` to verify the fixes work correctly:

```bash
$ python test_db_save.py
============================================================
Testing Database Persistence
============================================================

✓ Database path from .env: ./data/teletycoon.db

1. Creating new game engine...
2. Adding players...
3. Starting game...

4. Checking database...
   ✓ Game found in database!
   - Game ID: test_game_001
   - Status: active
   - Phase: stock_round
   - Created: 2025-12-31 17:32:14.712853
   - Bank Cash: ¥12000

5. Executing game action...
   Action result: Alice passed.
   ✓ Updated state saved to database!

============================================================
✅ Database persistence is working correctly!
============================================================
```

Database now contains:
- Games table: Game metadata and state
- Players table: Player information
- Game_players table: Player cash and holdings per game
- Companies table: Company state and treasury
- Trains table: Train ownership
- Game_log table: Action history

## How It Works Now

1. **Game Creation**: When a game starts, initial state is saved
2. **Each Action**: After every successful player action, state is automatically saved
3. **Database Path**: Reads from `DATABASE_PATH` in `.env` file
4. **Persistence Toggle**: Can disable persistence for testing with `enable_persistence=False`

## Testing

To verify your games are being saved:

```bash
# Check games in database
sqlite3 data/teletycoon.db "SELECT id, status, current_phase FROM games;"

# Check players
sqlite3 data/teletycoon.db "SELECT id, name, player_type FROM players;"

# Check game state
sqlite3 data/teletycoon.db "SELECT game_id, player_id, cash FROM game_players;"
```

## Next Steps

The database now works correctly! Future enhancements could include:
- Load saved games to resume play
- Game history and statistics
- Leaderboards
- Game replay functionality
