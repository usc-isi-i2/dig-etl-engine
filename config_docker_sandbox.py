import logging
import os

config = {
    'version': 'sandbox',

    'debug': True,
    'server': {
        'host': '0.0.0.0',
        'port': 9999,
    },

    'logstash': {
        'host': 'logstash',
        'port': 5959,
        'level': logging.INFO,
        'version': 1,
        'name': 'dig_etl_engine',
        'pipeline': '/app/logstash_pipeline'
    },

    'input_zookeeper_server': ['zookeeper:2181'],
    'output_zookeeper_server': ['zookeeper:2181'],
    'input_server': ['kafka:9092'],
    'output_server': ['kafka:9092'],
    'es_server': 'elasticsearch:9200',

    # per project topic
    'input_partitions': int(os.getenv('KAFKA_NUM_PARTITIONS', '4')),
    'output_partitions': int(os.getenv('KAFKA_NUM_PARTITIONS', '4')),
    'input_session_timeout': 60*60*1000,
    'input_group_id': 'dig_etk',
    'logstash_group_id': 'dig_logstash',

    'kafka_bin_path': '/app/kafka/bin',
    'projects_path': '/shared_data/projects',
    'etk_path': '/app/etk',
    'es_url': 'http://elasticsearch:9200'
}