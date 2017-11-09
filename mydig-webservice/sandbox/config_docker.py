# this file is from mydig-webservice/ws/config_docker.py
import logging
import os
import base64

config = {
    # if it's True, two daemon threads (one by flask, one by flask spawn) in mydig
    # will overwrite the same status file, which will cause a conflict
    'debug': False,
    'server': {
        'host': '0.0.0.0',
        'port': 9879,
    },
    'repo': {
        'local_path': '/shared_data/projects',
        'git': {
            'enable_sync': False,
            'remote_url': 'https://github.com/<user_name>/<repo_name>.git',
        }
    },
    'logging': {
        'file_path': 'log.log',
        'format': '%(asctime)s %(levelname)s %(message)s',
        'level': logging.INFO
    },
    'es': {
        # do not add / at the end
        'sample_url': 'http://elasticsearch:9200',
        'full_url': 'http://elasticsearch:9200'
    },
    'etk': {
        'path': '/app/etk',
        'conda_path': '/app/miniconda/bin/',
        'daemon': {
            'host': 'localhost',
            'port': 12121
        },
        # 'number_of_processes': 8
    },
    'etl': {
        'url': 'http://dig_etl_engine:9999',
        'number_of_workers': int(os.getenv('NUM_ETK_PROCESSES', '4')),
        'timeout': 20
    },
    'kafka': {
        'servers': ['kafka:9092']
    },
    'sandpaper': {
        'url': 'http://sandpaper:9876',
        'ws_url': 'http://mydig_ws:9879'
    },
    'users': {
        'admin': '123' # basic YWRtaW46MTIz
    },
    'frontend': {
        'host': '0.0.0.0',
        'port': 9880,
        'debug': True,
        'backend_url': 'http://{}:{}/mydig/'.format(
            os.getenv('DOMAIN', 'localhost'), os.getenv('PORT', '12497')),
        'landmark_url': 'http://{}:{}/landmark/'.format(
            os.getenv('DOMAIN', 'localhost'), os.getenv('PORT', '12497')),  # add slash at the end
        'digui_url': 'http://{}:{}/search.html'.format(
            os.getenv('DOMAIN', 'localhost'), os.getenv('PORT', '12497')),
        'kibana_url': 'http://{}:{}/kibana/'.format(
            os.getenv('DOMAIN', 'localhost'), os.getenv('PORT', '12497')),
        'spacy_ui_url': 'http://{}:{}/mydig/spacy_ui/'.format(
            os.getenv('DOMAIN', 'localhost'), os.getenv('PORT', '12497')),
        'spacy_backend_sever_name_base64': base64.b64encode('{}:{}/mydig'.format(
            os.getenv('DOMAIN', 'localhost'), os.getenv('PORT', '12497'))),
        'spacy_backend_auth_base64': base64.b64encode('{}:{}'.format(
            os.getenv('DIG_AUTH_USER', 'admin'), os.getenv('DIG_AUTH_PASSWORD', '123')))
    },
    'landmark': {
        'url': 'http://landmark-rest:5000/project/create_from_dig/{project_name}'
    },
    'ache': {
        'kafka_topic': 'ache',
        'group_id': 'mydig',
        'upload': {
            'endpoint': 'http://mydig_ws:9879/projects/{project_name}/data?sync=true&log=false',
            'file_name': 'ache', # file name in data folder
            # send to endpoint when get more than max_size or max_wait_time
            # 'max_size': 10, # 10 docs
            # 'max_wait_time': 10 * 1000, # 10s, float('inf')
        }
    },
    'data_pushing_worker_backoff_time': 5,
    'project_name_blacklist': ('logs', 'dig-logs', 'dig-states', 'dig-profiles', '.kibana'),
    'default_glossary_dicts_path': '/shared_data/dig3-resources/builtin_resources',
    'default_glossaries_path': '/shared_data/dig3-resources/glossaries',
    'default_spacy_rules_path': '/shared_data/dig3-resources/custom_spacy_rules'
}
