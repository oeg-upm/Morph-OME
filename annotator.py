import requests
import os
import io

TADA_HOST = os.environ['TADA_HOST']


def annotate_subject(source_dir, subject_col_id, top_k=3):
    """
    :param source_dir: the directory of the source file
    :param subject_col_id: the index of the subject column
    :param top_k: the number of suggested classes to return
    :return: list of string (classes)
    """
    data = {
        'col_id': subject_col_id,
        'alpha': 0.9,
    }
    # data['source'] = (source_dir.split(os.sep)[-1], open(source_dir), 'text/plain')
    # f = open(source_dir)
    # file_content = f.read()
    # data['source'] = (io.BytesIO(file_content), source_dir.split(os.sep)[-1])
    # response = requests.post(TADA_HOST+'/subject', data=data)
    # headers = {'Content-type': 'multipart/form-data'}
    # response = requests.post(TADA_HOST+'/subject', data=data, headers=headers)
    files = {
        'source': (source_dir.split(os.sep)[-1], open(source_dir), 'text/plain')
    }
    response = requests.post(TADA_HOST+'/subject', data=data, files=files)
    if response.status_code == 200:
        print("entities: ")
        print(response.json())
        entities = response.json()['entities']
        entities = entities[:top_k]
    else:
        entities = []
        print(response.json())
    return entities
