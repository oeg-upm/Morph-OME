import os
import json
from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
from werkzeug.utils import secure_filename
import requests
import util
import sys
import string
import random
import generate_lookup
import logging
import io
import annotator
import chardet
import rdflib
import subprocess
import shutil


import models


if 'UPLOAD_ONTOLOGY' in os.environ:
    UPLOAD_ONTOLOGY = os.environ['UPLOAD_ONTOLOGY'].lower() == "true"
else:
    UPLOAD_ONTOLOGY = True


def set_config(logger, logdir=""):
    if logdir != "":
        handler = logging.FileHandler(logdir)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


logger = logging.getLogger(__name__)
# set_config(logger)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

BASE_DIR = os.path.dirname(app.instance_path)
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload')
KG_DIR = os.path.join(BASE_DIR, 'kg')
DOWNLOAD = False

set_config(logger, os.path.join(BASE_DIR, 'ome.log'))

# SQL
print('sqlite:///'+BASE_DIR+'/test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+BASE_DIR+'/test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = models.db
db.init_app(app)
app.app_context().push()
db.create_all()


# Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    print("Trying to fetch user with id: " + str(user_id))
    return models.User.query.get(int(user_id))


@app.route("/")
def home():
    datasets = []
    print("datadir: " + DATA_DIR)
    for f in os.listdir(DATA_DIR):
        fdir = os.path.join(DATA_DIR, f)
        print("checking f: " + fdir)
        if os.path.isdir(fdir):
            print("is dir: " + fdir)
            if os.path.exists(os.path.join(fdir, 'classes.txt')) and os.path.exists(
                    os.path.join(fdir, 'properties.txt')):
                datasets.append(f)
    print(datasets)
    return render_template('index.html', datasets=datasets, UPLOAD_ONTOLOGY=UPLOAD_ONTOLOGY)


@app.route("/logout")
def logout_view():
    logout_user()
    return render_template('msg.html', msg="Logged out")


@app.route("/current")
def current_view():
    return render_template('user.html')


@app.route("/callback")
def callback_view():
    if'state' in session:
        if 'state' in request.args:
            if session['state']== request.args.get('state'):
                print("State match")
                if 'code' in request.args:
                    session['code'] = request.args.get('code')
                    data = {
                        'client_id': os.environ['github_appid'],
                        'client_secret': os.environ['github_secret'],
                        'code': session['code'],
                        'state': session['state']
                    }
                    response = requests.post('https://github.com/login/oauth/access_token', data=data)
                    print("response status code: "+str(response.status_code))
                    print("response content: "+str(response.text))
                    try:
                        session['access_token'] = response.text.split('&')[0].split('=')[1]
                        print("got access token")
                        headers = {
                            "Authorization": "token %s" % session['access_token']
                        }
                        response = requests.get("https://api.github.com/user", headers=headers)
                        try:
                            j = response.json()
                            print("user info: ")
                            print(j)
                            session['avatar'] = j['avatar_url']
                            user = models.User.query.filter_by(username=j['login']).first()
                            if user is None:
                                print("Creating a new user")
                                user = models.User(username=j['login'])
                                group = models.Group(name=j['login']+"-Group")
                                # user_group_repl = models.ManyUserGroup(user=user.id, group=group.id)
                                db.session.add(user)
                                # db.session.commit()
                                db.session.add(group)
                                # db.session.commit()
                                # db.session.add(user_group_repl)
                                db.session.commit()
                                user_group_repl = models.ManyUserGroup(user=user.id, group=group.id)
                                db.session.add(user_group_repl)
                                db.session.commit()

                            else:
                                print("Login an existing user")
                            login_user(user, remember=True)
                            return render_template('msg.html', msg='Logged in successfully')
                        except Exception as e:
                            print("error fetching user info from GitHub")
                            print("Exception: " + str(e))
                    except Exception as e:
                        print("error getting the access token")
                        print("Exception: "+str(e))
                else:
                    print("code is not passed in GitHub response")
            else:
                print("state mismatch: <%s> and <%s>" % (session['state'], request.args.get('state')))
        else:
            print("state is not passed in Github response")
    else:
        print("Missing state")
    return render_template('msg.html', error_msg="Security error. Try to login again")


def get_random_string(length):
    # With combination of lower and upper case
    result_str = ''.join(random.choice(string.ascii_letters) for i in range(length))
    # print random string
    print(result_str)


@app.route("/login")
def login_view():
    session['state'] = get_random_text(10)
    print("Generated state: "+session['state'])
    return redirect("https://github.com/login/oauth/authorize?client_id=%s&state=%s" % (os.environ['github_appid'], session['state']))


@app.route("/predict_subject", methods=['POST'])
def predict_subject():
    global logger
    if 'file_name' in request.form:
        fname = request.form['file_name']
        logger.debug('predict> file_name: ' + fname)
        source_dir = os.path.join(UPLOAD_DIR, fname)
        logger.debug('predict> source_dir: ' + source_dir)
        if os.path.exists(source_dir):
            logger.debug("predict> exists" + source_dir)
            if 'subject' in request.form:
                logger.debug("predict> subject in form" + request.form['subject'])
                if request.form['subject'].strip() != "":
                    subject_column_name = request.form['subject']
                    logger.debug("predict> subject in 2" + subject_column_name)
                    headers = util.get_headers_csv(source_dir)
                    subject_col_id = None
                    for i, h in enumerate(headers):
                        if h == subject_column_name:
                            subject_col_id = i

                    if subject_col_id is None:
                        return jsonify({'error': 'The provided subject header is not found'}), 400
                    else:
                        logger.debug("predict> will try to annotate the subject column")
                        entities = annotator.annotate_subject(source_dir, subject_col_id, 3, logger=logger)
                        return jsonify({'entities': entities})
        else:
            jsonify({'error': 'The provided file does not exist on the server'}), 404
    return jsonify({'error': 'missing values'}), 400


@app.route("/predict_properties", methods=['POST'])
def predict_properties():
    global logger
    if 'file_name' in request.form:
        fname = request.form['file_name']
        logger.debug('predict_property> file_name: ' + fname)
        source_dir = os.path.join(UPLOAD_DIR, fname)
        logger.debug('predict_property> source_dir: ' + source_dir)
        if os.path.exists(source_dir):
            logger.debug("predict_property> exists" + source_dir)
            subject_column_name = None
            if 'subject' in request.form:
                logger.debug("predict_property> subject in form" + request.form['subject'])
                if request.form['subject'].strip() != "":
                    subject_column_name = request.form['subject']
                    logger.debug("predict_property> subject in 2" + subject_column_name)
                    headers = util.get_headers_csv(source_dir)
                    subject_col_id = None
                    for i, h in enumerate(headers):
                        if h == subject_column_name:
                            subject_col_id = i

                    if subject_col_id is None:
                        return jsonify({'error': 'The provided subject header is not found'}), 400
                    else:
                        pairs = annotator.annotate_property(source_dir, subject_col_id, 3, logger=logger)
                        print(pairs)
                        return jsonify({'cols_properties': pairs})
        else:
            jsonify({'error': 'The provided file does not exist on the server'}), 404
    return jsonify({'error': 'missing values'}), 400


@app.route("/editor", methods=['POST'])
def editor():
    if 'format' in request.form:
        file_type = request.form['format']
    else:
        file_type = 'csv'
    if 'callback' in request.form:
        callback_url = request.form['callback']
    else:
        callback_url = ""
    ontologies = request.form.getlist('ontologies')
    if len(ontologies) == 0:
        return render_template('msg.html', msg="You should select at least one ontology", msg_title="Error")
    print("number of ontologies: " + str(len(ontologies)))
    print(ontologies)
    print(request.form)
    error_msg = None
    warning_msg = None
    uploaded = False
    if 'source' not in request.form or request.form['source'].strip() == "":
        if 'sourcefile' in request.files:
            sourcefile = request.files['sourcefile']
            if sourcefile.filename != "":
                original_file_name = sourcefile.filename
                filename = secure_filename(sourcefile.filename)
                fname = util.get_random_string(4) + "-" + filename
                uploaded_file_dir = os.path.join(UPLOAD_DIR, fname)
                if not os.path.exists(UPLOAD_DIR):
                    os.mkdir(UPLOAD_DIR)
                sourcefile.save(uploaded_file_dir)
                uploaded = True
            else:
                print("blank source file")
        else:
            print('not sourcefile')
        if not uploaded:
            return render_template('msg.html', msg="Expecting an input file", msg_title="Error")
    else:
        source = request.form['source']
        original_file_name = source.split('/')[-1]
        filename = secure_filename(original_file_name)
        r = requests.get(source, allow_redirects=True)
        if r.status_code == 200:
            fname = util.get_random_string(4) + "-" + filename
            uploaded_file_dir = os.path.join(UPLOAD_DIR, fname)
            f = open(uploaded_file_dir, 'w')
            f.write(r.text)
            f.close()
        else:
            error_msg = "the source %s can not be accessed" % source
            print(error_msg)
            return render_template('msg.html', msg=error_msg, msg_title="Error")

    headers = util.get_headers(uploaded_file_dir, file_type=file_type)
    if headers == []:
        error_msg = "Can't parse the source file "
        return render_template('msg.html', msg=error_msg, msg_title="Error")

    print(headers)
    logger.debug("headers: ")
    logger.debug(str(headers))
    headers_str_test = headers[-1]#str(headers)
    logger.debug("headers string: ")
    # logger.debug(headers_str_test)
    # detected_encoding = chardet.detect(headers_str_test)['encoding']
    # logger.debug("detected encoding %s " % (detected_encoding))
    # decoded_s = headers_str_test.decode(detected_encoding)
    # headers_str_test = decoded_s.encode('utf-8')
    # logger.debug("headers utf-8 encoded: ")
    # logger.debug(headers_str_test)

    labels = util.get_classes_as_txt(ontologies, data_dir=DATA_DIR)
    # f = open(os.path.join(DATA_DIR, "labels.txt"))
    return render_template('editor.html', labels_txt=labels, ontologies_txt=",".join(ontologies), headers=headers,
                           callback=callback_url, file_name=fname, error_msg=error_msg, warning_msg=warning_msg)


@app.route("/get_properties")
def get_properties():
    ontologies_txt = request.args.get('ontologies')
    ontologies = ontologies_txt.split(',')
    return jsonify({'properties': util.get_properties_as_list(ontologies, data_dir=DATA_DIR)})


@app.route("/get_properties_autocomplete")
def get_properties_autocomplete():
    if 'ontologies' in request.args:
        ontologies = request.args.get('ontologies').split(',')
    else:
        return jsonify({'error': 'missing ontologies parameter'}), 400
    if 'term' in request.args:
        term = request.args.get('term')
        if len(term) == 0:
            return jsonify({'error': 'term should be of a length 1 at least'}), 400
        fname = term.lower()[0] + ".txt"
        properties = []
        for o in ontologies:
            fdir = os.path.join(DATA_DIR, o, "lookup", fname)
            if os.path.exists(fdir):
                print("fdir exists: ")
                print(fdir)
                f = open(fdir)
                for line in f.readlines():
                    p = line.strip()
                    if p == "":
                        continue
                    properties.append(p)
            else:
                print("not: ")
                print(fdir)
        return jsonify({'properties': properties})


@app.route("/sparql", methods=['POST', 'GET'])
def sparql_view():
    if request.method == "GET":
        if 'id' in request.args:
            print("Getting ID from GET")
            return render_template('sparql.html', kgid=request.args.get('id'))
        else:
            print("Missing ID from GET")
            return render_template('msg.html', error_msg="KG ID is missing")
    else:
        if 'kgid' in request.form and request.form['kgid'] != "":
            if 'query' in request.form:
                query = request.form['query']
                print("Query: ")
                print(query)
                print("request form: ")
                print(request.form)
                print("kgid")
                print(request.form['kgid'])
                fname = str(request.form['kgid']) + ".ttl"
                fpath = os.path.join(KG_DIR, fname)

                if not os.path.exists(fpath):
                    return jsonify(error="Invalid KG id"), 400

                g = rdflib.Graph()
                print("will parse: "+fpath)
                g.parse(fpath, format="ttl")
                print("query kg with: "+query)
                qres = g.query(query)
                results = []
                for row in qres:
                    print(row)
                    results.append([str(v) for v in row])

                print("results: ")
                print(results)
                return jsonify(results=results)
                # return results

            else:
                print("Missing query")
                return jsonify(error="missing query"), 400

        else:
            print("Missing id")
            return jsonify(error="missing id"), 400


def generate_kg_rml(mapping_fdir):
    """
    :param mapping_fdir: The directory to the generated fdir
    :return:
    """
    if not os.path.exists(KG_DIR):
        os.makedirs(KG_DIR)
    if current_user.is_authenticated:
        print("user is authenticated: "+current_user.username)
        if 'RMLMAPPER_PATH' in os.environ:
            jar_path = os.environ['RMLMAPPER_PATH']
            print("jar_path exists: "+jar_path)

            user_group_rel = models.ManyUserGroup.query.filter_by(user=current_user.id).first()
            if user_group_rel:
                group = models.Group.query.filter_by(id=user_group_rel.group).first()
                if group:
                    kg = models.KG(group=group.id, name=get_random_text(n=10))
                    db.session.add(kg)
                    db.session.commit()
                    fname = str(kg.id)
                else:
                    print("group does not exists")
                    fname = "test1"
            else:
                print("user group membership does not exists")
                fname = "test2"
            out_path = os.path.join(KG_DIR, fname+".ttl")

            cmd = """cd "%s" ;java -jar "%s" -m "%s" -o "%s" """ % (UPLOAD_DIR, jar_path, mapping_fdir, out_path)
            print("cmd: %s" % cmd)
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            return fname
        else:
            print("MORPH_PATH is missing")
    else:
        print("user is not authenticated")
    return None


@app.route("/generate_mapping", methods=['POST'])
def generate_mapping():
    if 'entity_class' in request.form and 'entity_column' in request.form and 'file_name' in request.form and 'mapping_lang' in request.form:
        entity_class = request.form['entity_class']
        entity_column = request.form['entity_column']
        file_name = request.form['file_name']
        mapping_lang = request.form['mapping_lang']
        print("request form list: ")
        print(list(request.form.keys()))
        print("request form: ")
        print(request.form.keys())
        mappings = []
        for i in range(len(list(request.form.keys()))):
            key = 'form_key_' + str(i)
            val = 'form_val_' + str(i)
            # print "key = ", key
            # print "val = ", val
            # print list(request.form.keys())

            if key in request.form and val in request.form:
                if request.form[val].strip() != '':
                    element = {"key": request.form[key], "val": request.form[val]}
                    mappings.append(element)
            else:
                continue

        print("mappings = ")
        print(mappings)
        # Assuming the file name has at least a single . to separate the file name and the extension
        file_name_without_ext = ".".join(file_name.split('.')[:-1])
        mapping_file_name = file_name_without_ext + "-" + get_random_text() + "." + mapping_lang  # ".r2rml"
        mapping_file_dir = os.path.join(UPLOAD_DIR, mapping_file_name)
        if mapping_lang == "r2rml":
            util.generate_r2rml_mappings(mapping_file_dir, file_name, entity_class, entity_column, mappings)
        elif mapping_lang == "rml":
            util.generate_rml_mappings_csv(mapping_file_dir, file_name, entity_class, entity_column, mappings)
        elif mapping_lang == "yarrrml":
            util.generate_yarrrml_mappings_csv(mapping_file_dir, file_name, entity_class, entity_column, mappings)
        elif mapping_lang == "kg-rml":
            util.generate_rml_mappings_csv(mapping_file_dir, file_name, entity_class, entity_column, mappings)
            kgid = generate_kg_rml(mapping_file_dir)
            if kgid is None:
                return render_template('msg.html', error_msg="Error generating KG")
            else:
                return render_template('msg.html', msg="Generated the KG.", html="<a href='/sparql?id=%s'>Go to SPARQL</a>" % (str(kgid)))
        else:
            return render_template('msg.html', msg="Invalid mapping language", msg_title="Error")
        f = open(mapping_file_dir)
        mapping_content = f.read()
        f.close()
        # return render_template('msg.html', msg=mapping_content)
        if 'callback' in request.form and request.form['callback'].strip() != "":
            callback_url = request.form['callback'].strip()
            files = {'file': open(mapping_file_dir, 'rb')}
            try:
                r = requests.post(callback_url, files=files)
                if r.status_code == 200:
                    return render_template('msg.html', msg="Your mappings has been sent", msg_title="Result")
                else:
                    print(r.content)
                    return render_template('msg.html', msg="Error sending the mappings to :" + callback_url,
                                           msg_title="Error")
            except Exception as e:
                print("Exception: " + str(e))
                return render_template('msg.html', error_msg="Invalid callback URL :" + callback_url)
        return send_from_directory(UPLOAD_DIR, mapping_file_name, as_attachment=True)
    else:
        return render_template('msg.html', warning_msg='missing values ... make sure to use our editor')


def get_random_text(n=4):
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(n)])


@app.route("/add_ontology", methods=["POST"])
def add_ontology():
    if 'name' not in request.form:
        return render_template('msg.html', msg="Ontology name is not passed", msg_title="Error")
    if 'sourcefile' in request.files:
        sourcefile = request.files['sourcefile']
        if sourcefile.filename != "":
            filename = secure_filename(sourcefile.filename)
            uploaded_file_dir = os.path.join(UPLOAD_DIR, filename)
            print("to save the file to: " + uploaded_file_dir)
            if not os.path.exists(UPLOAD_DIR):
                os.mkdir(UPLOAD_DIR)
            sourcefile.save(uploaded_file_dir)
            generate_lookup.generate_lookup(uploaded_file_dir, request.form['name'].strip(), data_dir=DATA_DIR)
            return render_template('msg.html', msg="Ontology added successfully", msg_title="Success")
        else:
            print("blank source file")
            return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")
    else:
        return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        app.run(debug=True, port=int(sys.argv[1]))
    elif len(sys.argv) == 3 and sys.argv[2].isdigit():
        app.run(debug=True, host=sys.argv[1], port=int(sys.argv[2]))
    else:
        app.run(debug=True)
