import sys

# Add your project directory to the Python path
path = '/home/your_username/Atfal-Website'
if path not in sys.path:
    sys.path.append(path)

from app import app as application 