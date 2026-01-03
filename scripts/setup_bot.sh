cd $1 || exit
uv sync --no-dev
bash ./scripts/start_screen.sh "$1" 'uv run python -m teletycoon.main'
