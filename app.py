import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from api import app

if __name__ == '__main__':
    app.run()
