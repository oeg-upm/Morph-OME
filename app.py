import os
import json
from flask import Flask, render_template, jsonify, request
app = Flask(__name__)


BASE_DIR = os.path.dirname(app.instance_path)
DATA_DIR = os.path.join(BASE_DIR, 'data')


@app.route("/")
def editor():
    f = open(os.path.join(DATA_DIR, "labels.txt"))
    return render_template('editor.html', labels_txt=f.read(), headers=["AAA", "BBB", "CCC"])


@app.route("/get_properties")
def get_properties():
    concept = request.args.get('concept', default=None)
    if concept:
        concept = concept.strip()
        schema_prop_path = os.path.join(DATA_DIR, 'schema-prop.json')
        print 'schema_prop_path: %s' % schema_prop_path
        f = open(schema_prop_path)
        properties_j = json.loads(f.read())
        if concept in properties_j:
            properties = list(set(properties_j[concept]))
            return jsonify({'properties': properties})
    return jsonify({'properties': []})


if __name__ == '__main__':
   app.run(debug=True)