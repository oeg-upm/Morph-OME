![OME](https://github.com/oeg-upm/OME/raw/master/logo.png)

An Online Mapping Editor to generate R2RML, RML, and YARRRML without writing a single line.
It also supports automatic suggestions of the subject and property columns using 
the APIs of [tada_web](https://github.com/oeg-upm/tada-web).
 

# Run with Docker
1. `sh run_docker.sh`
2. In the browser visit `http://127.0.0.1:5000`


# How to install it locally
1. Create virtual environment [here](https://docs.python-guide.org/dev/virtualenvs/) (recommended by not required) e.g. ```virtualenv -p /usr/bin/python2.7 .venv```
1. Access the virtual environment using `source .venv/bin/activate`
1. Install pip [here](https://pip.pypa.io/en/stable/installing/)
1. Install requirements ``` pip install -r requirements.txt ```
1. Set `TADA_HOST` to the url of the pytada_hdt_entity host. For example (`export TADA_HOST="http://127.0.0.1:5001/`)
1. Run the application ``` python app.py ```
1. Open the browser to the url [http://127.0.0.1:5000/](http://127.0.0.1:5000/)


# Automatic Suggestions
It uses the APIs of [web]. To use it, you need to export an environment variable `TADA_HOST` with the 
URL of the `tada-web` host url.
For example, you can set it like that
`export TADA_HOST="http://127.0.0.1:5001/"`


# Screenshot
![screenshot](https://github.com/oeg-upm/OME/raw/master/screenshot.png)


# Remarks
* To run the application on a specific port (e.g. say port 5001) ``` python app.py 5001```.
