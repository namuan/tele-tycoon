cd $1 || exit
test -d venv || python3 -m venv venv
venv/bin/pip3 install -r requirements.txt
bash ./scripts/start_screen.sh "$1" 'venv/bin/python3 -m teletycoon.main'
