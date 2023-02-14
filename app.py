import os
import json
import traceback
from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
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
import csv

import models

MAX_ONT_SIZE = 1024 * 1024 * 20  # 20 MB/1000 KB


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
app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)


def app_setup(app, db_name='test.db'):
    global BASE_DIR, DATA_DIR, UPLOAD_DIR, KG_DIR, ONT_DIR, DOWNLOAD, login_manager, db, ANN_DIR
    # app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    # app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    # app.config['MAX_CONTENT_LENGTH'] = 50 * 1024  # 50 Kb
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1 MB/1000 KB
    if 'MAX_CONTENT_LENGTH' in os.environ:
        app.config['MAX_CONTENT_LENGTH'] = int(os.environ['MAX_CONTENT_LENGTH'])

    BASE_DIR = os.path.dirname(app.instance_path)
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    UPLOAD_DIR = os.path.join(BASE_DIR, 'upload')
    KG_DIR = os.path.join(BASE_DIR, 'kg')
    ONT_DIR = os.path.join(BASE_DIR, 'ontology')
    ANN_DIR = os.path.join(BASE_DIR, 'anns.csv')
    DOWNLOAD = False

    set_config(logger, os.path.join(BASE_DIR, 'ome.log'))

    # SQL
    print('sqlite:///' + BASE_DIR + "/" + db_name)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, db_name)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = models.db
    db.init_app(app)
    app.app_context().push()
    db.create_all()

    # Login
    # login_manager = LoginManager()
    # login_manager.init_app(app)
    return app


def get_app(test=False, db_name='atest.db'):
    global app
    # app = Flask(__name__)
    if test:
        app.config['TESTING'] = True
    app = app_setup(app=app, db_name=db_name)
    return app


@login_manager.user_loader
def load_user(user_id):
    print("Trying to fetch user with id: " + str(user_id))
    return models.User.query.get(int(user_id))


# def user_in_group(user, group_id):
#     a = models.ManyUserGroup.query.filter_by(user=user.id, group=group_id).first()
#     return a is None


def create_folders():
    global DATA_DIR, UPLOAD_DIR, KG_DIR, ONT_DIR
    ds = [DATA_DIR, UPLOAD_DIR, KG_DIR, ONT_DIR]
    for d in ds:
        if not os.path.exists(d):
            os.makedirs(d)


# get public ontologies
def get_public_ontologies():
    datasets = []
    create_folders()
    for f in os.listdir(DATA_DIR):
        fdir = os.path.join(DATA_DIR, f)
        # print("checking f: " + fdir)
        if os.path.isdir(fdir):
            # print("is dir: " + fdir)
            if os.path.exists(os.path.join(fdir, 'classes.txt')) and os.path.exists(
                    os.path.join(fdir, 'properties.txt')):
                datasets.append(f)
    # print(datasets)
    return datasets


@app.route("/about")
def about_view():
    return render_template('about.html')


@app.route("/tutorial")
def tutorial_view():
    return render_template('tutorial.html')


@app.route("/knowledgegraphs")
@login_required
def knowledge_graphs_view():
    mems = models.ManyUserGroup.query.filter_by(user=current_user.id).all()
    k = []
    for m in mems:
        g = models.Group.query.filter_by(id=m.group).first()
        kgs = models.KG.query.filter_by(group=g.id).all()
        for kg in kgs:
            d = {
                'kg': kg,
                'group': g
            }
            k.append(d)

    return render_template('kgs.html', kgs=k)


@app.route("/updatekg", methods=["POST"])
@login_required
def update_kg():
    if 'name' in request.form and 'id' in request.form:
        kg = models.KG.query.filter_by(id=int(request.form['id'])).first()
        if kg:
            mem = models.ManyUserGroup.query.filter_by(user=current_user.id, group=kg.group).first()
            if mem:
                kg.name = request.form['name']
                db.session.commit()
                return redirect(url_for('knowledge_graphs_view'))
                # return redirect(url_for('sparql_view') + "?id=" + str(kg.id))
            else:
                return render_template('msg.html',
                                       msg="Invalid Knowledge Graph. You don't have a knowledge graph with this id",
                                       msg_title="Error")
        else:
            return render_template('msg.html',
                                   msg="Invalid Knowledge Graph.",
                                   msg_title="Error")

    else:
        return render_template('msg.html',
                               msg="Missing Knowledge Graph name and ID.",
                               msg_title="Error")


@app.route("/deletekg", methods=["POST"])
@login_required
def delete_kg():
    if 'id' in request.form:
        kg = models.KG.query.filter_by(id=int(request.form['id'])).first()
        if kg:
            mem = models.ManyUserGroup.query.filter_by(user=current_user.id, group=kg.group).first()
            if mem:
                kg_dir = os.path.join(KG_DIR, str(kg.id)+".ttl")
                try:
                    if os.path.exists(kg_dir):
                        os.remove(kg_dir)
                    db.session.delete(kg)
                    db.session.commit()
                    return redirect(url_for('knowledge_graphs_view'))

                except Exception as e:
                    print("Exception: "+str(e))
                    traceback.print_exc()
                    return render_template('msg.html',
                                           msg="Error deleting the Knowledge Graph",
                                           msg_title="Error")
            else:
                return render_template('msg.html',
                                       msg="Invalid Knowledge Graph. You don't have a knowledge graph with this ID",
                                       msg_title="Error")
        else:
            return render_template('msg.html',
                                   msg="Invalid Knowledge Graph.",
                                   msg_title="Error")
    else:
        return render_template('msg.html',
                               msg="Missing Knowledge Graph ID.",
                               msg_title="Error")


def get_anns(source_url):
    """
    Get the available annotation sources (HDT models) for a given source
    """
    response = requests.get(source_url+"sources")
    if response.status_code == 200:
        try:
            ann_sources = response.json()
            return ann_sources['sources']
        except Exception as e:
            print("get_anns> Exception: %s" % str(e))
            traceback.print_exc()
            return []

    print("get_anns> Error getting ann sources")
    return []


def get_source(source_id):
    sources = get_sources()
    for source in sources:
        if source["id"] == source_id:
            return source
    print("get_source> source <%s> is not found" % source_id)


def get_sources():
    """
    Get sources, which can have one or more annotators
    """
    global ANN_DIR
    sources = []
    if os.path.exists(ANN_DIR):
        with open(ANN_DIR, 'r') as data:
            for ann in csv.DictReader(data):
                print(ann)
                sources.append(ann)
    else:
        print("%s is not found" % ANN_DIR)
    return sources


def get_annotators():
    """
    Get annotators and sources with updated ids as: source_id,ann_id
    """
    sources = get_sources()
    anns = []

    for source in sources:
        try:
            s_anns = get_anns(source["url"])
            for ann in s_anns:
                ann["id"] = "%s,%s" % (source["id"], ann["id"])
            print("s_anns: ")
            print(s_anns)
            anns += s_anns
        except Exception as e:
            print("get_annotators> exception: %s" % str(e))
    return anns


@app.route("/")
def home():
    public_ontology_names = get_public_ontologies()
    public_ontologies = []
    private_ontologies = []
    for po in public_ontology_names:
        public_ontologies.append({'id': po, 'name': po})
    try:
        if current_user.is_authenticated:
            memberships = models.ManyUserGroup.query.filter_by(user=current_user.id).all()
            for mem in memberships:
                g = models.Group.query.filter_by(id=mem.group).first()
                g_ontologies = models.Ontology.query.filter_by(group=g.id).all()
                for o in g_ontologies:
                    d = {'id': o.id, 'name': o.name}
                    private_ontologies.append(d)

    except Exception as e:
        print("Error getting user ontologies")
        print("Exception: " + str(e))
        traceback.print_exc()

    return render_template('home.html', kgs=get_annotators(),
                           ontologies=public_ontologies + private_ontologies, UPLOAD_ONTOLOGY=UPLOAD_ONTOLOGY,
                           max_kb=app.config['MAX_CONTENT_LENGTH'] / 1024)


@app.route("/public-ontologies", methods=["POST", "GET"])
def public_ontologies_view():
    if not UPLOAD_ONTOLOGY:
        return render_template('msg.html', msg="this function is disabled for now", msg_title="Error")
    if request.method == "POST":
        if 'name' not in request.form:
            return render_template('msg.html', msg="Ontology name is not passed", msg_title="Error")
        if 'sourcefile' in request.files:
            sourcefile = request.files['sourcefile']
            if sourcefile.filename != "":
                filename = secure_filename(sourcefile.filename)
                uploaded_file_dir = os.path.join(UPLOAD_DIR, filename)
                print("to save the file to: " + uploaded_file_dir)
                if not os.path.exists(UPLOAD_DIR):
                    os.makedirs(UPLOAD_DIR)
                sourcefile.save(uploaded_file_dir)
                generate_lookup.generate_lookup(uploaded_file_dir, request.form['name'].strip(), data_dir=DATA_DIR)
                return render_template('msg.html', msg="Ontology added successfully", msg_title="Success")
            else:
                print("blank source file")
                return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")
        else:
            return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")
    else:
        datasets = get_public_ontologies()
        # datasets = []
        return render_template('ontologies.html', datasets=datasets, UPLOAD_ONTOLOGY=UPLOAD_ONTOLOGY)


@app.route("/delete-ontology", methods=["POST"])
@login_required
def delete_ontology_view():
    try:
        if 'ontology' in request.form:
            ontology_id_str = request.form['ontology']
            ontology_id = int(ontology_id_str)
            ontology = models.Ontology.query.filter_by(id=ontology_id).first()
            if ontology:
                print("ontology is found")
                group_id = ontology.group
                u_g_mem = models.ManyUserGroup.query.filter_by(user=current_user.id, group=group_id).first()
                if u_g_mem:
                    print("membership is found")
                    db.session.delete(ontology)
                    db.session.commit()

                    try:
                        shutil.rmtree(os.path.join(ONT_DIR, ontology_id_str))
                    except Exception as e:
                        print("Exception in deleting the ontology: " + str(e))

                    return render_template('msg.html', msg="Ontology is deleted successfully!", msg_title="Success")
            return render_template('msg.html', msg="The ontology does not belong to this user", msg_title="Error")
        else:
            return render_template('msg.html', msg="Missing ontology", msg_title="Error")
    except Exception as e:
        print("Exception: " + str(e))
        return render_template('msg.html', msg="Internal error", msg_title="Error")


@app.route("/ontologies", methods=["POST", "GET"])
@login_required
def ontologies_view():
    app.config['MAX_CONTENT_LENGTH'] = MAX_ONT_SIZE
    if request.method == "POST":
        if 'name' not in request.form:
            return render_template('msg.html', msg="Ontology name is not passed", msg_title="Error")
        if 'group' not in request.form:
            return render_template('msg.html', msg="No group is passed", msg_title="Error")
        if 'sourcefile' not in request.files:
            return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")
        try:
            group_id = int(request.form['group'])
        except Exception as e:
            print("Exception: " + str(e))
            return render_template('msg.html', msg="Invalid group is passed", msg_title="Error")

        user_group_membership = models.ManyUserGroup.query.filter_by(user=current_user.id, group=group_id).first()
        if user_group_membership is None:
            return render_template('msg.html', msg="Invalid group", msg_title="Error")

        sourcefile = request.files['sourcefile']

        ont = models.Ontology(group=group_id, name=request.form['name'].strip())
        db.session.add(ont)
        db.session.commit()

        if sourcefile.filename != "":
            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)
            if not os.path.exists(ONT_DIR):
                os.makedirs(ONT_DIR)
            uploaded_file_dir = os.path.join(UPLOAD_DIR, str(ont.id) + ".txt")
            print("to save the file to: " + uploaded_file_dir)
            sourcefile.save(uploaded_file_dir)
            # generate_lookup.generate_lookup(uploaded_file_dir, request.form['name'].strip(), data_dir=ONT_DIR)
            generate_lookup.generate_lookup(uploaded_file_dir, str(ont.id), data_dir=ONT_DIR)
            return render_template('msg.html', msg="Ontology added successfully", msg_title="Success")
        else:
            print("blank source file")
            return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")
    else:
        groups = models.ManyUserGroup.query.filter_by(user=current_user.id).all()
        l = []
        groups_obj = []
        for gr in groups:
            onts = models.Ontology.query.filter_by(group=gr.id).all()
            grobj = models.Group.query.filter_by(id=gr.id).first()
            groups_obj.append(grobj)
            for o in onts:
                l.append({'group': grobj.name + " (" + str(gr.id) + ")", 'ontology': o.name, 'ontology_id': o.id})
        return render_template('ontologies.html', ont_group_pairs=l, groups=groups_obj)
        # datasets = get_datasets()
        # datasets = []
        # return render_template('ontologies.html', datasets=datasets, UPLOAD_ONTOLOGY=UPLOAD_ONTOLOGY)


@app.route("/logout")
def logout_view():
    logout_user()
    return render_template('msg.html', msg="Logged out")


@app.route("/current")
def current_view():
    return render_template('user.html')


@app.route("/callback")
def callback_view():
    if 'state' in session:
        if 'state' in request.args:
            if session['state'] == request.args.get('state'):
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
                    print("response status code: " + str(response.status_code))
                    print("response content: " + str(response.text))
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
                                group = models.Group(name=j['login'] + "-Group")
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
                        print("Exception: " + str(e))
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
    print("Generated state: " + session['state'])
    return redirect("https://github.com/login/oauth/authorize?client_id=%s&state=%s" % (
        os.environ['github_appid'], session['state']))


@app.route("/predict_subject", methods=['POST'])
def predict_subject():
    global logger
    if 'file_name' in request.form and 'kg' in request.form and 'alpha' in request.form:
        kg = request.form['kg'].strip()
        parts = kg.split(',')
        if len(parts) != 2:
            return jsonify({'error': 'Wrong KG. Expected the format source_id,ann_id'}), 400
        source_id, ann_id = parts
        try:
            alpha = float(request.form['alpha'])
        except Exception as e:
            print(e)
            return jsonify({'error': 'Invalid alpha value. It should be a float between 0 and 1.'})
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
                        s = get_source(source_id)
                        if not s:
                            return jsonify({'error': 'The provided source is not found'}), 400
                        entities = annotator.annotate_subject(source_url=s["url"], ann_id=ann_id, source_dir=source_dir,
                                                              subject_col_id=subject_col_id, top_k=3,
                                                              alpha=alpha, logger=logger)
                        return jsonify({'entities': entities})
        else:
            jsonify({'error': 'The provided file does not exist on the server or the kg is not passed or alpha is not passed'}), 404
    return jsonify({'error': 'missing values'}), 400


@app.route("/predict_properties", methods=['POST'])
def predict_properties():
    global logger
    if 'file_name' in request.form and 'kg' in request.form:
        kg = request.form['kg'].strip()
        parts = kg.split(',')
        if len(parts) != 2:
            jsonify({'error': 'Wrong KG. Expected the format source_id,ann_id'}), 400
        source_id, ann_id = parts
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
                        err_msg = 'The provided subject header is not found'
                        print(err_msg)
                        return jsonify({'error': err_msg}), 400
                    else:
                        s = get_source(source_id)
                        if not s:
                            err_msg = 'The provided source is not found'
                            print(err_msg)
                            return jsonify({'error': err_msg}), 400

                        class_uri = None
                        if 'class_uri' in request.form:
                            if len(request.form['class_uri'].strip()) > 0:
                                class_uri = request.form['class_uri'].strip()
                        pairs = annotator.annotate_property(source_url=s["url"], ann_id=ann_id, source_dir=source_dir,
                                                            subject_col_id=subject_col_id, top_k=3, logger=logger,
                                                            class_uri=class_uri)
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
    kg = None
    if 'kg' in request.form:
        if request.form['kg'].strip() != "":
            kg = request.form['kg'].strip()
            parts = kg.split(',')
            if len(parts) != 2: # it should be source_id,ann_id.
                return render_template('msg.html', msg="Source ID and Ann ID shouldn't include commas",
                                       msg_title="Error")
    ontologies = request.form.getlist('ontologies')
    if len(ontologies) == 0:
        return render_template('msg.html', msg="You should select at least one ontology", msg_title="Error")
    logger.debug("number of ontologies: " + str(len(ontologies)))
    logger.debug(str(ontologies))
    logger.debug(str(request.form))
    error_msg = None
    warning_msg = None
    uploaded = False
    if 'source' not in request.form or request.form['source'].strip() == "":
        if 'sourcefile' in request.files:
            sourcefile = request.files['sourcefile']
            if sourcefile.filename != "":
                # original_file_name = sourcefile.filename
                filename = secure_filename(sourcefile.filename)
                fname = util.get_random_string(4) + "-" + filename
                uploaded_file_dir = os.path.join(UPLOAD_DIR, fname)
                if not os.path.exists(UPLOAD_DIR):
                    os.makedirs(UPLOAD_DIR)
                sourcefile.save(uploaded_file_dir)
                uploaded = True
            else:
                logger.debug("blank source file")
        else:
            logger.debug('not sourcefile')
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
            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)
            f = open(uploaded_file_dir, 'w', encoding='utf-8')
            f.write(r.text)
            f.close()
        else:
            error_msg = "the source %s can not be accessed" % source
            logger.debug(error_msg)
            return render_template('msg.html', msg=error_msg, msg_title="Error")

    headers = util.get_headers(uploaded_file_dir, file_type=file_type)
    if not headers:
        error_msg = "Can't parse the source file "
        return render_template('msg.html', msg=error_msg, msg_title="Error")

    logger.debug("headers: ")
    logger.debug(str(headers))
    labels = ""
    for o in ontologies:
        o_labels = None
        try:
            o_labels = util.get_classes_as_txt([o], data_dir=DATA_DIR)
        except:
            o_labels = util.get_classes_as_txt([o], data_dir=ONT_DIR)
        if o_labels:
            labels += o_labels
    logger.debug("labels: ")
    logger.debug(str(labels))

    return render_template('editor.html', labels_txt=labels, ontologies_txt=",".join(ontologies), headers=headers,
                           kg=kg,
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
        print("get_properties_autocomplete> fname: " + fname)
        properties = []
        for o in ontologies:
            print("get_properties_autocomplete> ontology: " + o)
            for D in [DATA_DIR, ONT_DIR]:
                try:
                    fdir = os.path.join(D, o, "lookup", fname)
                    if os.path.exists(fdir):
                        print("fdir exists: ")
                        print(fdir)
                        f = open(fdir, encoding='utf-8')
                        for line in f.readlines():
                            p = line.strip()
                            if p == "":
                                break
                            print("p: " + p)
                            properties.append(p)
                        break
                    else:
                        print("not: ")
                        print(fdir)
                except:
                    continue
        print("properties: ")
        print(properties)
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
                print("will parse: " + fpath)
                g.parse(fpath, format="ttl")
                print("query kg with: " + query)
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
        print("user is authenticated: " + current_user.username)
        if 'RMLMAPPER_PATH' in os.environ:
            jar_path = os.environ['RMLMAPPER_PATH']
            print("jar_path exists: " + jar_path)

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
            out_path = os.path.join(KG_DIR, fname + ".ttl")

            cmd = """cd "%s" ;java -jar "%s" -m "%s" -o "%s" """ % (UPLOAD_DIR, jar_path, mapping_fdir, out_path)
            print("cmd: %s" % cmd)
            try:
                subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
                return fname
            except Exception as e:
                print("Exception: "+str(e))
                traceback.print_exc()
                raise Exception(e)
        else:
            print("MORPH_PATH is missing")
    else:
        print("user is not authenticated")
    return None


@app.route("/generate_mapping", methods=['POST'])
def generate_mapping():
    print("generate_mapping> ")
    if 'entity_class' in request.form and 'entity_column' in request.form and 'file_name' in request.form and 'mapping_lang' in request.form:
        print("form: ")
        print(request.form)
        entity_class = request.form['entity_class']
        entity_column = request.form['entity_column']
        if entity_column[0] == '"' and entity_column[-1] == '"':
            entity_column = entity_column[1:-1]
        file_name = request.form['file_name']
        mapping_lang = request.form['mapping_lang']
        print("request form list: ")
        print(list(request.form.keys()))
        print("request form: ")
        print(request.form.keys())
        mappings = []
        for i in range(len(list(request.form.keys()))):
            key = 'form_key_' + str(i+1)
            val = 'form_val_' + str(i+1)
            print("key = %s" % key)
            print("val = %s" % val)

            if key in request.form and val in request.form:
                if request.form[val].strip() != '':
                    k = request.form[key]
                    v = request.form[val]
                    if k[0] == '"' and k[-1] == '"':
                        k = k[1:-1]

                    if v[0] == '"' and v[-1] == '"':
                        v = v[1:-1]

                    element = {"key": k, "val": v}
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
                return render_template('msg.html', msg="Generated the KG.",
                                       html="<a href='/sparql?id=%s'>Go to SPARQL</a>" % (str(kgid)))
        else:
            return render_template('msg.html', msg="Invalid mapping language", msg_title="Error")
        f = open(mapping_file_dir, encoding='utf-8')
        mapping_content = f.read()
        f.close()
        # return render_template('msg.html', msg=mapping_content)
        if 'callback' in request.form and request.form['callback'].strip() != "":
            callback_url = request.form['callback'].strip()
            files = {'file': open(mapping_file_dir, 'rb', encoding='utf-8')}
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
    app.config['MAX_CONTENT_LENGTH'] = MAX_ONT_SIZE
    if not UPLOAD_ONTOLOGY:
        return render_template('msg.html', msg="Uploading ontologies for all users is not allowed", msg_title="Error")
    if 'name' not in request.form:
        return render_template('msg.html', msg="Ontology name is not passed", msg_title="Error")
    if 'sourcefile' in request.files:
        sourcefile = request.files['sourcefile']
        if sourcefile.filename != "":
            filename = secure_filename(sourcefile.filename)
            uploaded_file_dir = os.path.join(UPLOAD_DIR, filename)
            print("to save the file to: " + uploaded_file_dir)
            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
            sourcefile.save(uploaded_file_dir)
            print("request form:")
            print(request.form['name'].strip())
            generate_lookup.generate_lookup(uploaded_file_dir, request.form['name'].strip(), data_dir=DATA_DIR)
            return render_template('msg.html', msg="Ontology added successfully", msg_title="Success")
        else:
            print("blank source file")
            return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")
    else:
        return render_template('msg.html', msg="Ontology file is not passed", msg_title="Error")

    # create_folders()
    # return app


if __name__ == '__main__':
    app = get_app()
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        app.run(debug=True, port=int(sys.argv[1]))
    elif len(sys.argv) == 3 and sys.argv[2].isdigit():
        app.run(debug=True, host=sys.argv[1], port=int(sys.argv[2]))
    else:
        app.run(debug=True)
