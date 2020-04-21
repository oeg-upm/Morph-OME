import rdflib
import os
import string
import util
from collections import Counter

formats = ['xml', 'ttl']
DATA_DIR = 'data'


def generate_lookup(f_dir, dataset_name):
    """
    Extract classes and properties from a given ontology
    :param f_dir:
    :param dataset_name:
    :return:
    """
    dataset_dir = os.path.join('data', dataset_name)
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
    g = rdflib.Graph()
    found = False
    for format in formats:
        try:
            g.parse(f_dir, format=format)
            found = True
            break
        except:
            pass
    if found:
        classes = get_all_classes(g)
        classes_f_name = os.path.join(dataset_dir,'classes.txt')
        f = open(classes_f_name,'w')
        for c in classes:
            f.write(c+"\n")
        f.close()
        properties = get_all_properties(g)
        properties_f_dir = os.path.join(dataset_dir, 'properties.txt')
        f = open(properties_f_dir,'w')
        for p in properties:
            f.write(p+"\n")
        f.close()
        build_property_lookup(dataset_name,properties_f_dir)
    else:
        print("Unable to parse: "+f_dir)


def get_all_properties(g):
    """
    :param g:
    :return:
    """
    q = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    select ?a 
        where{
         {?a ?b owl:ObjectProperty} UNION
         {?a a rdf:Property } UNION
         {?a ?b owl:DatatypeProperty}
        }
    """
    result = g.query(q)
    properties = [str(row[0]).strip() for row in result]
    for r in properties:
        print(r)
    return properties


def get_all_classes(g):
    """
    :param g:
    :return:
    """
    q = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    select distinct ?class
        where{
            {?class rdf:type rdfs:Class} UNION {?class rdf:type owl:Class} .
        }
    """
    result = g.query(q)
    classes = [str(row[0]).strip() for row in result]
    for r in classes:
        print(r)
    return classes


def build_property_lookup(dataset_name,properties_fdir):
    """
    Build a property lookup
    :param properties_fdir:
    :return:
    """
    print("build_property_lookup> dataset_name: "+dataset_name)
    properties = util.get_properties_as_list([dataset_name])
    start_idx = predict_base_URL(properties)
    lookup_name = 'lookup'
    lookup_folder_dir = os.path.join(DATA_DIR,dataset_name,lookup_name)
    if not os.path.exists(lookup_folder_dir):
        os.mkdir(lookup_folder_dir)
    # for start in string.ascii_lowercase:
    #     start_dir = os.path.join(lookup_folder_dir, start+".txt")
    for p in properties:
        p_name = p[start_idx:]
        if len(p_name) == 0:
            continue
        # print("pname: <"+p_name+">")
        write_lookup_for(lookup_folder_dir, p_name.lower()[0], p)


def write_lookup_for(base_dir, letter, property_uri):
    fdir = os.path.join(base_dir, letter+".txt")
    f = open(fdir,'a+')
    f.write(property_uri+"\n")
    f.close()


def predict_base_URL(uris, checks=20, restrictive=True):
    """
    :param uris: a list of strings, each string is a URI
    :param checks: the number of checks to perform
    :param restrictive: if true, it will take the highest stop_idx instead of the most common
    :return:
    """
    upper = uris[:len(uris)/2]
    lower = uris[len(uris)/2:]
    stop_idx = []
    for u in upper[:checks]:
        for l in lower[:checks]:
            if u == l:
                continue
            for i in range(min(len(u),len(l))):
                if u[i] != l[i]:
                    # print("-------")
                    # print("u: "+u)
                    # print("l: "+l)
                    # print(i)
                    stop_idx.append(i)
                    break
    if restrictive:
        max_stop_idx = min(stop_idx)
        print("predicted_base: "+upper[0][:max_stop_idx])
        return max_stop_idx
    else:
        c = Counter(stop_idx)
        max_counts = 0
        idx_of_max = 0
        for k in c:
            if c[k] > max_counts:
                idx_of_max = k
                max_counts = c[k]
        return idx_of_max


