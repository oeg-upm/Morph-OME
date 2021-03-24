import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
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

BASE_DIR = os.path.dirname(app.instance_path)
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload')
DOWNLOAD = False

set_config(logger, os.path.join(BASE_DIR, 'ome.log'))


@app.route("/")
def home():
    datasets = []
    print("datadir: " + DATA_DIR)
    for f in os.listdir(DATA_DIR):
        fdir = os.path.join(DATA_DIR, f)
        print("checking f: " + fdir)
        if os.path.isdir(fdir):
            print("isdir: " + fdir)
            if os.path.exists(os.path.join(fdir, 'classes.txt')) and os.path.exists(
                    os.path.join(fdir, 'properties.txt')):
                datasets.append(f)
    print(datasets)
    return render_template('index.html', datasets=datasets, UPLOAD_ONTOLOGY=UPLOAD_ONTOLOGY)


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
            f.write(r.content)
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
    logger.debug(headers_str_test)
    detected_encoding = chardet.detect(headers_str_test)['encoding']
    logger.debug("detected encoding %s " % (detected_encoding))
    decoded_s = headers_str_test.decode(detected_encoding)
    headers_str_test = decoded_s.encode('utf-8')
    logger.debug("headers utf-8 encoded: ")
    logger.debug(headers_str_test)




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


@app.route("/generate_mapping", methods=['POST'])
def generate_mapping():
    if 'entity_class' in request.form and 'entity_column' in request.form and 'file_name' in request.form and 'mapping_lang' in request.form:
        entity_class = request.form['entity_class']
        entity_column = request.form['entity_column']
        file_name = request.form['file_name']
        mapping_lang = request.form['mapping_lang']
        # print "request form: "
        # print list(request.form.keys())
        mappings = []
        for i in range(len(request.form.keys())):
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
