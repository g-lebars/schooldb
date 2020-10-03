Create a virtual-environement (https://docs.python.org/3/library/venv.html))
python -m venv /path/to/new/virtual/environment


To setup you need the libraries in requirements.txt
pip install -r requirements.txt 

To initialize migrations library:

flask db init
flask db migrate -m "migrate message"
flask db upgrade


Activate virtual environements
source venv/bin/activate

For debug:
 export FLASK_ENV=development
 export FASK_APP=app
 flask run