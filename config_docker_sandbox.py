import logging

config = {
    'debug': True,
    'server': {
        'host': '0.0.0.0',
        'port': 9999,
    },

    'logstash': {
        'host': 'localhost',
        'port': 5959,
        'level': logging.INFO,
        'version': 1,
        'name': 'dig_etl_engine'
    },

    'input_zookeeper_server': ['zookeeper:2181'],
    'output_zookeeper_server': ['zookeeper:2181'],
    'input_server': ['kafka:9092'],
    'output_server': ['kafka:9092'],

    # per project topic
    'input_partitions': 4,
    'output_partitions': 4,
    'input_session_timeout': 60*60*1000,
    'input_group_id': 'dig',

    'kafka_bin_path': '/app/kafka/bin',
    'projects_path': '/projects_data',
    'etk_path': '/app/etk'
}