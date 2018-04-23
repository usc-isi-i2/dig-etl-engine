import time
from datetime import datetime
import json
import sys
import os
from argparse import ArgumentParser
import signal
import logging

from kafka import KafkaProducer, KafkaConsumer
# from digsandpaper.elasticsearch_indexing.index_knowledge_graph import index_knowledge_graph_fields

from config import config
sys.path.append(os.path.join(config['etk_path'], 'etk'))
from etk.etk import ETK
from etk.knowledge_graph import KGSchema


class ETKWorker(object):

    def __init__(self, master_config, em_paths, logger, worker_id,
                 project_name, kafka_input_args=None, kafka_output_args=None):
        self.logger = logger
        self.worker_id = worker_id

        try:
            kg_schema = KGSchema(master_config)
            self.etk_ins = ETK(kg_schema, em_paths)
        except:
            logger.exception('ETK initialization failed')

        # kafka input
        self.kafka_input_server = config['input_server']
        self.kafka_input_session_timeout = config['input_session_timeout']
        self.kafka_input_group_id = config['input_group_id']
        self.kafka_input_topic = '{project_name}_in'.format(project_name)
        self.kafka_input_args = dict() if kafka_input_args is None else kafka_input_args
        self.kafka_consumer = KafkaConsumer(
            bootstrap_servers=self.kafka_input_server,
            group_id=self.kafka_input_group_id,
            consumer_timeout_ms=self.kafka_input_session_timeout,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            **kafka_input_args
        )
        self.kafka_consumer.subscribe([self.kafka_input_topic])

        # kafka output
        self.kafka_output_server = config['output_server']
        self.kafka_output_topic = '{project_name}_out'.format(project_name)
        self.kafka_output_args = dict() if kafka_output_args is None else kafka_output_args
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=self.kafka_output_server,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            **self.kafka_output_args
        )

    def process(self):
        prev_doc_sent_time = None

        # high level api handles batching
        # will exit once timeout
        try:
            for msg in self.kafka_consumer:
                # force to commit, block till getting response
                self.kafka_consumer.commit()

                cdr = msg.value
                cdr['@execution_profile'] = {'@worker_id': self.worker_id}
                doc_arrived_time = time.time()
                cdr['@execution_profile']['@doc_arrived_time'] \
                    = datetime.utcfromtimestamp(doc_arrived_time).isoformat()
                cdr['@execution_profile']['@doc_wait_time'] \
                    = 0.0 if not prev_doc_sent_time \
                    else float(doc_arrived_time - prev_doc_sent_time)
                cdr['@execution_profile']['@doc_length'] = len(json.dumps(cdr))

                if 'doc_id' not in cdr or len(cdr['doc_id']) == 0:
                    self.logger.error('invalid cdr: unknown doc_id')

                self.logger.info('processing', cdr['doc_id'])
                try:
                    start_run_core_time = time.time()
                    # run etk module

                    doc = self.etk_ins.create_document(cdr)
                    doc, kg = self.etk_ins.process_ems(doc)
                    cdr = kg

                    # indexing
                    # TODO
                    # indexed_kg = index_knowledge_graph_fields(kg)
                    # if not indexed_kg:
                    #     logger.error('indexing in sandpaper failed')
                    #     continue
                    # cdr = indexed_kg

                    cdr['@execution_profile']['@run_core_time'] = float(time.time() - start_run_core_time)
                    doc_sent_time = time.time()
                    cdr['@execution_profile']['@doc_sent_time'] = datetime.utcfromtimestamp(doc_sent_time).isoformat()
                    prev_doc_sent_time = doc_sent_time
                    cdr['@execution_profile']['@doc_processed_time'] = float(doc_sent_time - doc_arrived_time)

                    # output result
                    r = self.kafka_producer.send(self.kafka_output_topic, cdr)
                    r.get(timeout=60)  # wait till sent

                    self.logger.info('{} done'.format(cdr['doc_id']))

                except Exception as e:
                    self.logger.exception('failed at', cdr['doc_id'])

        except ValueError as e:
            # I/O operation on closed epoll fd
            self.logger.info('consumer closed')

        except StopIteration as e:
            # timeout
            self.logger.info('consumer timeout')
            sys.exit()

    def __del__(self):

        self.logger.info('ETK worker {} is exiting...'.format(self.worker_id))

        if self.kafka_consumer:
            self.kafka_consumer.close()
        if self.kafka_producer:
            self.kafka_producer.close()
