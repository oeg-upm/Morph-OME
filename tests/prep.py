import os


def create_dbpedia(dbpedia_path):
    if not os.path.exists(dbpedia_path):
        os.makedirs(dbpedia_path)
        lookup_dir = os.path.join(dbpedia_path, 'lookup')
        os.makedirs(lookup_dir)
        f = open(os.path.join(dbpedia_path, "classes.txt"), "w")
        f.write("http://dbpedia.org/ontology/Boxer\n")
        f.close()
        f = open(os.path.join(dbpedia_path, "properties.txt"), "w")
        f.write("http://dbpedia.org/ontology/height\n")
        f.close()
        f = open(os.path.join(lookup_dir, "a.txt"), "w")
        f.write("http://dbpedia.org/ontology/album\n")
        f.close()
