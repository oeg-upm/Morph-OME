import rdflib
import os
formats = ['xml', 'ttl']


def generate_lookup(f_dir, dataset_name):
    """
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
        properties_f_name = os.path.join(dataset_dir, 'properties.txt')
        f = open(properties_f_name,'w')
        for p in properties:
            f.write(p+"\n")
        f.close()

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

