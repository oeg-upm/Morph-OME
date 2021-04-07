activate_this = '/home/sample/venv/bin/activate_this.py'

with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

import sys
sys.path.insert(0, '/home/sample/OME')


from app import app as application
application.debug = True