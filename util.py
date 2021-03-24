import string
import random
import os
import chardet


def get_random_string(length=4):
    return ''.join(random.choice(string.lowercase) for i in range(length))


def get_headers(file_dir, file_type):
    """
    :param file_dir: abs dir of the input file that is already downloaded
    :param file_type: ext
    :return:
    """
    ext = file_dir.split('.')[-1].lower().strip
    if ext == 'csv' or file_type == "csv":
        return get_headers_csv(file_dir)
    elif ext == 'json' or file_type == "json":
        print("json is not supported")
        return []
    else:
        return []


def get_headers_csv(file_dir):
    f = open(file_dir)
    header_str = ""
    for line in f.readlines():
        header_str = line
        break

    header = []
    start_q = False
    start_idx = 0

    # detected_encoding = chardet.detect(s)['encoding']
    # logger.debug("detected encoding %s for %s" % (detected_encoding, fname))
    # decoded_s = s.decode(detected_encoding)
    detected_encoding = chardet.detect(header_str)['encoding']
    print("detected encoding %s " % (detected_encoding))
    decoded_s = header_str.decode(detected_encoding)
    header_str = decoded_s

    print("header_string: "+header_str)
    for idx, ch in enumerate(header_str):
        if ch == '"' and start_q == True:
            start_q = False
        elif ch=='"':
            start_q = True
        elif ch=="," and start_q == False:
            curr = header_str[start_idx:idx]
            header.append(curr)
            start_idx = idx+1
    header.append(header_str[start_idx:])

    return header


def generate_r2rml_mappings(mapping_file_dir, file_name, entity_class, entity_column, mappings):
    #print "mappings are: "
    #print mappings
    mapping_id = get_random_string(10)
    single_property_mapping = u"""
        rr:predicateObjectMap [
          rr:predicateMap [ rr:constant <%s> ];
          rr:objectMap    [ rr:termType rr:Literal; rr:column "\\"%s\\""; ];
        ];
    """
    proper_mappings_list = [single_property_mapping % (m["val"], m["key"].upper()) for m in mappings]
    property_column_mapping = "\n".join(proper_mappings_list)
    print("predicate object mappings: ")
    print(property_column_mapping)
    table_name = file_name.upper()
    if table_name[-4:] == ".CSV":
        table_name = table_name[:-4]
    else:
        #print table_name[:-4]
        print("Note that the filename is not terminated with .CSV")
        #raise Exception("the file name should ends up with .CSV ")
    mapping_content = u"""
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix mpv: <http://mappingpedia.linkeddata.es/vocab/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <http://schema.org/> .
@base <http://mappingpedia.linkeddata.es/resource/> .
<%s>
    rr:logicalTable [
        rr:tableName  "\\"%s\\""
    ];
    rr:subjectMap [
        a rr:Subject; rr:termType rr:IRI; rr:class <%s>;
        rr:column "\\"%s\\"";
    ];
    %s
.
    """ % (mapping_id, table_name, entity_class, entity_column.upper(), property_column_mapping)
    print(mapping_content)
    f = open(mapping_file_dir, 'w')
    f.write(mapping_content.encode('utf8'))
    f.close()


def generate_rml_mappings_csv(mapping_file_dir, file_name, entity_class, entity_column, mappings):
    mapping_id = get_random_string(10)
    single_property_mapping = u"""
        rr:predicateObjectMap [
          rr:predicate <%s>;
          rr:objectMap    [ rml:reference "%s" ]
        ];
    """
    proper_mappings_list = [single_property_mapping % (m["val"], m["key"]) for m in mappings]
    property_column_mapping = "\n".join(proper_mappings_list)
    mapping_file = u"""
@prefix rr: <http://www.w3.org/ns/r2rml#>.
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix mail: <http://example.com/mail#>.
@prefix xsd: <http://www.w3.org/2001/XMLSchema#>.
@prefix ex: <http://www.example.com/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix transit: <http://vocab.org/transit/terms/> .
@prefix wgs84_pos: <http://www.w3.org/2003/01/geo/wgs84_pos#>.
@prefix schema: <http://schema.org/>.
@prefix gn: <http://www.geonames.org/ontology#>.
@prefix geosp: <http://www.telegraphis.net/ontology/geography/geography#> .
@base <http://mappingpedia.linkeddata.es/resource/> .
<%s>
rml:logicalSource [
    rml:source  "%s";
    rml:referenceFormulation ql:CSV

];
rr:subjectMap [
    rml:reference "%s";
    rr:class <%s>
];
%s
.
    """ % (mapping_id, file_name, entity_column, entity_class, property_column_mapping)
    print mapping_file
    mapping_file_path = mapping_file_dir
    # mapping_file_path = os.path.join(BASE_DIR, 'local', mapping_id+'.rml.ttl')
    print 'mapping file path:'
    print mapping_file_path
    f = open(mapping_file_path, 'w')
    f.write(mapping_file.encode('utf8'))
    f.close()
    return mapping_file_path


def get_json_path(j):
    max_no = 0
    json_path = []
    for k in j.keys():
        if isinstance(j[k], list):
            # print "list (%d): " % len(j[k])
            # print j[k]
            if len(j[k]) > max_no:
                # print "max list (%d): " % len(j[k])
                # print j[k]
                max_no = len(j[k])
                json_path = [k]
        elif isinstance(j[k], dict):
            j_dict = get_json_path(j[k])
            if j_dict["max_no"] > max_no:
                max_no = j_dict["max_no"]
                json_path = [k] + j_dict["json_path"]
        # else:
        #     print j[k]
        #     print type(j[k])
    return {"max_no": max_no, "json_path": json_path}


def generate_yarrrml_mappings_csv(mapping_file_dir, file_name, entity_class, entity_column, mappings):
    mapping_id = get_random_string(10)
    single_property_mapping = u"""            - [%s, %s]"""
    concept_name = entity_class.split('/')[-1].split('#')[-1]
    proper_mappings_list = [single_property_mapping % (m["val"], m["key"]) for m in mappings]
    class_as_po = single_property_mapping % ("a", entity_class)
    proper_mappings_list.append(class_as_po)
    property_column_mapping = "\n".join(proper_mappings_list)
    mapping_file = u"""

prefixes:
    ex: http://www.example.com/
    e: http://myontology.com/
    base: http://mappingpedia.linkeddata.es/resource/
    dbo: http://dbpedia.org/ontology/

mappings:
    %s:
        sources:
            - ['%s~csv']
        s: base:$(%s) 
        po:
%s
    """ % (concept_name, file_name, entity_column, property_column_mapping)
    print mapping_file
    mapping_file_path = mapping_file_dir
    # mapping_file_path = os.path.join(BASE_DIR, 'local', mapping_id+'.rml.ttl')
    print 'mapping file path:'
    print mapping_file_path
    f = open(mapping_file_path, 'w')
    f.write(mapping_file.encode('utf8'))
    f.close()
    return mapping_file_path


def get_classes_from_file(odir):
    """
    :param odir:
    :return:
    """
    f = open(odir)
    classes = f.read().split('\n')
    f.close()
    return classes


def get_properties_as_list(ontologies, data_dir):
    """
    :param ontologies:
    :return:
    """
    properties = []
    for o in ontologies:
        odir = os.path.join(data_dir, o, 'properties.txt')
        properties += get_classes_from_file(odir)
    return properties


def get_classes_as_txt(ontologies, data_dir):
    """
    :param ontologies:
    :return:
    """
    classes = []
    for o in ontologies:
        odir = os.path.join(data_dir, o, 'classes.txt')
        classes += get_classes_from_file(odir)
    # return classes
    txt = ""
    for c in classes:
        txt += '"' + c + '", '
    return txt
