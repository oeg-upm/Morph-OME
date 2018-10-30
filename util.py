import string, random


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
    import pandas as pd
    pcsv = pd.read_csv(file_dir, nrows=1)
    print "pcsv: "
    print pcsv
    print "columns: "
    print pcsv.columns
    print list(pcsv.columns)
    return list(pcsv.columns)


def generate_r2rml_mappings(mapping_file_dir, file_name, entity_class, entity_column, mappings):
    #print "mappings are: "
    #print mappings
    mapping_id = get_random_string(10)
    single_property_mapping = u"""
        rr:predicateObjectMap [
          rr:predicateMap [ rr:constant schema:%s ];
          rr:objectMap    [ rr:termType rr:Literal; rr:column "\\"%s\\""; ];
        ];
    """
    proper_mappings_list = [single_property_mapping % (m["val"].replace('http://schema.org/', ''), m["key"].upper()) for m in mappings]
    property_column_mapping = "\n".join(proper_mappings_list)
    print "predicate object mappings: "
    print property_column_mapping
    table_name = file_name.upper()
    if table_name[-4:] == ".CSV":
        table_name = table_name[:-4]
    else:
        #print table_name[:-4]
        print "Note that the filename is not terminated with .CSV"
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
            a rr:Subject; rr:termType rr:IRI; rr:class schema:%s;
            rr:column "\\"%s\\"";
        ];
        %s
    .
    """ % (mapping_id, table_name, entity_class, entity_column.upper(), property_column_mapping)
    print mapping_content
    f = open(mapping_file_dir, 'w')
    f.write(mapping_content.encode('utf8'))
    f.close()