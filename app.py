import os
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
import requests
import util
import sys
import string
import random
from generate_lookup import generate_lookup

app = Flask(__name__)


BASE_DIR = os.path.dirname(app.instance_path)
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload')
DOWNLOAD = False


@app.route("/")
def home():
    datasets = []
    print("datadir: "+DATA_DIR)
    for f in os.listdir(DATA_DIR):
        fdir = os.path.join(DATA_DIR,f)
        print("checking f: "+fdir)
        if os.path.isdir(fdir):
            print("isdir: "+fdir)
            if os.path.exists(os.path.join(fdir, 'classes.txt')) and os.path.exists(os.path.join(fdir, 'properties.txt')):
                datasets.append(f)
    print(datasets)
    return render_template('index.html', datasets=datasets)


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
    print("number of ontologies: "+str(len(ontologies)))
    print(ontologies)
    print(request.form)
    error_msg = None
    warning_msg = None
    uploaded = False
    if 'source' not in request.form or request.form['source'].strip()=="":
        if 'sourcefile' in request.files:
            sourcefile = request.files['sourcefile']
            if sourcefile.filename != "":
                original_file_name = sourcefile.filename
                filename = secure_filename(sourcefile.filename)
                uploaded_file_dir = os.path.join(UPLOAD_DIR, filename)
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
    labels = util.get_classes_as_txt(ontologies)
    #f = open(os.path.join(DATA_DIR, "labels.txt"))
    return render_template('editor.html', labels_txt=labels, ontologies_txt=",".join(ontologies), headers=headers, callback=callback_url, file_name=original_file_name, error_msg=error_msg, warning_msg=warning_msg)


@app.route("/get_properties")
def get_properties():
    ontologies_txt = request.args.get('ontologies')
    ontologies = ontologies_txt.split(',')
    return jsonify({'properties': util.get_properties_as_list(ontologies)})


@app.route("/generate_mapping", methods=['POST'])
def generate_mapping():
    if 'entity_class' in request.form and 'entity_column' in request.form and 'file_name' in request.form and 'mapping_lang' in request.form:
        entity_class = request.form['entity_class']
        entity_column = request.form['entity_column']
        file_name = request.form['file_name']
        mapping_lang = request.form['mapping_lang']
        #print "request form: "
        #print list(request.form.keys())
        mappings = []
        for i in range(len(request.form.keys())):
            key = 'form_key_' + str(i)
            val = 'form_val_' + str(i)
            #print "key = ", key
            #print "val = ", val
            #print list(request.form.keys())

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
        mapping_file_name = file_name_without_ext+"-"+get_random_text()+ "." + mapping_lang #".r2rml"
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
                    return render_template('msg.html', msg="Error sending the mappings to :"+callback_url, msg_title="Error")
            except Exception as e:
                print("Exception: "+str(e))
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
            print("to save the file to: "+uploaded_file_dir)
            sourcefile.save(uploaded_file_dir)
            generate_lookup(uploaded_file_dir, request.form['name'].strip())
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
