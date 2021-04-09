
![OME](static/logo-min.png)

[![Build Status](https://ahmad88me.semaphoreci.com/badges/Morph-OME/branches/master.svg)](https://ahmad88me.semaphoreci.com/projects/Morph-OME)
[![codecov](https://codecov.io/gh/oeg-upm/Morph-OME/branch/master/graph/badge.svg?token=TsSWMQGuoO)](https://codecov.io/gh/oeg-upm/Morph-OME)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3764202.svg)](https://doi.org/10.5281/zenodo.3764202)


An Online Mapping Editor to generate R2RML, RML, and YARRRML without writing a single line.
It also supports automatic suggestions of the subject and property columns using 
the APIs of [tada_web](https://github.com/oeg-upm/tada-web).


<!--
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

-->

# Automatic Suggestions
It uses the APIs of[tada_web](https://github.com/oeg-upm/tada-web). To use it, you need to export an environment variable `TADA_HOST` with the 
URL of the `tada-web` host url.
For example, you can set it like that
`export TADA_HOST="http://127.0.0.1:5001/"`




# Environment Variables
* `SECRET_KEY`:
    * A random text
* `TADA_HOST`:
    * (Optional)
    * The URL of TADA APIs. If it is missing, the class and properties won't be annotated automatically
    * Default: ""
* `UPLOAD_ONTOLOGY`: 
    * (Optional)
    * To show/hide an ontology upload page (in the main page) for the autocomplete functionality
    * Default: True
* `github_secret`:
    * Github app secret  
* `github_appid`:
    * Github app ID
* `MORPH_PATH`:
    * The local path to morph-rdb jar to generate ttl
* `RMLMAPPER_PATH`:
    * The local path to rmlmapper jar to generate the ttl


## To activate_this.py 
You can add these environment variables to `activate_this.py` in the virtualenv bin directory.
```
os.environ['SECRET_KEY']=""
os.environ['github_appid']=""
os.environ['github_secret']=""
os.environ['UPLOAD_ONTOLOGY']="false"
os.environ['RMLMAPPER_PATH']=""
os.environ['TADA_HOST']=""
```

## To a shell
```
export SECRET_KEY=""
export github_appid=""
export github_secret=""
export UPLOAD_ONTOLOGY="false"
export RMLMAPPER_PATH=""
export TADA_HOST=""
```


<!--
# Screenshot
![screenshot](https://github.com/oeg-upm/OME/raw/master/screenshot.png)
-->

# Remarks
* To run the application on a specific port (e.g. say port 5001) ``` python app.py 5001```.
* To run the application on a specific port (e.g. say port 5001, and any given host 0.0.0.0) ``` python app.py 0.0.0.0 5001```.

# To cite
```
@software{alobaid_ahmad_2020_3764202,
  author       = {Alobaid, Ahmad and
                  Corcho, Oscar},
  title        = {OME},
  month        = apr,
  year         = 2020,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.3764202},
  url          = {https://doi.org/10.5281/zenodo.3764202}
}
```

