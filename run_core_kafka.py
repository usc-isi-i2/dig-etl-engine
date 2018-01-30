import time
from datetime import datetime
import json
import codecs
import sys
import os
from argparse import ArgumentParser
import traceback
import signal

from kafka import KafkaProducer, KafkaConsumer
from digsandpaper.elasticsearch_indexing.index_knowledge_graph import index_knowledge_graph_fields

from config import config
sys.path.append(os.path.join(config['etk_path'], 'etk'))
import core


consumer_pointer = None
producer_pointer = None


def run_serial_cdrs(etk_core, consumer, producer, producer_topic, indexing=False, worker_id=0):
    prev_doc_sent_time = None

    # high level api will handle batch thing
    # will exit once timeout
    try:
        for msg in consumer:
            # force to commit, block till getting response
            consumer.commit()

            cdr = msg.value
            cdr['@execution_profile'] = {'@worker_id': worker_id}
            doc_arrived_time = time.time()
            cdr['@execution_profile']['@doc_arrived_time'] = datetime.utcfromtimestamp(doc_arrived_time).isoformat()
            cdr['@execution_profile']['@doc_wait_time'] = 0.0 if not prev_doc_sent_time \
                else float(doc_arrived_time - prev_doc_sent_time)
            cdr['@execution_profile']['@doc_length'] = len(json.dumps(cdr))

            if 'doc_id' not in cdr or len(cdr['doc_id']) == 0:
                print 'invalid cdr: unknown doc_id'
            print 'processing', cdr['doc_id']

            try:
                start_run_core_time = time.time()
                # run core
                cdr = etk_core.process(cdr, create_knowledge_graph=True)
                if not cdr:
                    prev_doc_sent_time = time.time()
                    raise Exception('run core error')

                # indexing
                if indexing:
                    cdr = index_knowledge_graph_fields(cdr)
                if not cdr:
                    prev_doc_sent_time = time.time()
                    raise Exception('indexing in sandpaper failed')
                cdr['@execution_profile']['@run_core_time'] = float(time.time() - start_run_core_time)

                # nested docs
                if 'nested_docs' in cdr:
                    print 'detected nested_docs'
                    for nested_cdr in cdr['nested_docs']:
                        print 'processing nested_docs', nested_cdr['doc_id']
                        nested_cdr['@execution_profile'] = {
                            '@worker_id': cdr['@execution_profile']['@worker_id'],
                            '@doc_arrived_time': cdr['@execution_profile']['@doc_arrived_time'],
                            '@doc_wait_time': cdr['@execution_profile']['@doc_wait_time'],
                            '@doc_length': len(json.dumps(nested_cdr))
                        }

                        nested_start_run_core_time = time.time()
                        # fill tld by parent tld
                        nested_cdr['tld'] = cdr['tld']

                        # run core
                        nested_cdr = etk_core.process(nested_cdr, create_knowledge_graph=True)
                        if not nested_cdr:
                            print 'run core error in nested doc {}'.format(nested_cdr['doc_id'])
                            continue

                        # indexing
                        if indexing:
                            nested_cdr = index_knowledge_graph_fields(nested_cdr)
                        if not nested_cdr:
                            print 'indexing error in nested doc {}'.format(nested_cdr['doc_id'])
                            continue

                        nested_cdr['@execution_profile']['@run_core_time'] = \
                            float(time.time() - nested_start_run_core_time)

                        nested_doc_sent_time = time.time()
                        nested_cdr['@execution_profile']['@doc_sent_time'] = \
                            datetime.utcfromtimestamp(nested_doc_sent_time).isoformat()
                        nested_cdr['@execution_profile']['@doc_processed_time'] = \
                            float(nested_doc_sent_time - doc_arrived_time) # use its parent's doc_arrived_time
                        if nested_cdr:
                            r = producer.send(producer_topic, nested_cdr)
                            r.get(timeout=60)  # wait till sent
                        else:
                            etk_core.log('fail to indexing nested doc {}'.format(nested_cdr['doc_id']), core._ERROR)

                    # remove nested_docs from original result
                    del cdr['nested_docs']

                doc_sent_time = time.time()
                cdr['@execution_profile']['@doc_sent_time'] = datetime.utcfromtimestamp(doc_sent_time).isoformat()
                prev_doc_sent_time = doc_sent_time
                cdr['@execution_profile']['@doc_processed_time'] = float(doc_sent_time - doc_arrived_time)
                # dumping result
                if cdr:
                    r = producer.send(producer_topic, cdr)
                    r.get(timeout=60)  # wait till sent
                else:
                    etk_core.log('fail to indexing doc {}'.format(cdr['doc_id']), core._ERROR)

                print 'done'


            except Exception as e:
                # print e
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                print ''.join(lines)
                print 'failed at', cdr['doc_id']

    except ValueError as e:
        # I/O operation on closed epoll fd
        print 'consumer closed'

    except StopIteration as e:
        # timeout
        print 'consumer timeout'
        sys.exit()


def termination_handler(signum, frame):
    global consumer_pointer, producer_pointer

    print 'SIGNAL #{} received, trying to exit...'.format(signum)

    if consumer_pointer:
        consumer_pointer.close()
    if producer_pointer:
        producer_pointer.close()


def usage():
    return """\
Usage: python run_core.py [args]
-c, --config <config>
                                         
--kafka-input-server <host:port,...>
--kafka-input-topic <topic_name>
--kafka-input-group-id <group_id>
--kafka-input-session-timeout <ms>
--kafka-output-server <host:port,...>
--kafka-output-topic <topic_name>

--indexing
    """

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", action="store", type=str, dest="configPath")

    parser.add_argument("--kafka-input-server", action="store", type=str, dest="kafkaInputServer")
    parser.add_argument("--kafka-input-topic", action="store", type=str, dest="kafkaInputTopic")
    parser.add_argument("--kafka-input-group-id", action="store", type=str, dest="kafkaInputGroupId")
    parser.add_argument("--kafka-input-session-timeout", action="store", type=int,
                        dest="kafkaInputSessionTimeout", default=60*60*1000) # default to 1 hour
    parser.add_argument("--kafka-output-server", action="store", type=str, dest="kafkaOutputServer")
    parser.add_argument("--kafka-output-topic", action="store", type=str, dest="kafkaOutputTopic")
    parser.add_argument("--kafka-input-args", action="store", type=str, dest="kafkaInputArgs")
    parser.add_argument("--kafka-output-args", action="store", type=str, dest="kafkaOutputArgs")
    parser.add_argument("--indexing", action="store_true", dest="indexing")

    parser.add_argument("--worker-id", action="store", type=str, dest="workerId")

    c_options, args = parser.parse_known_args()

    if not c_options.configPath or \
        not c_options.kafkaInputServer or not c_options.kafkaInputTopic or \
        not c_options.kafkaInputGroupId or not c_options.kafkaOutputServer or \
        not c_options.kafkaOutputTopic:
        usage()
        sys.exit()

    worker_id = int(c_options.workerId) if c_options.workerId is not None else 0

    signal.signal(signal.SIGINT, termination_handler)
    signal.signal(signal.SIGTERM, termination_handler)

    try:
        # parse input and output args
        input_args = json.loads(c_options.kafkaInputArgs) if c_options.kafkaInputArgs else {}
        output_args = json.loads(c_options.kafkaOutputArgs) if c_options.kafkaOutputArgs else {}

        # print 'input:'
        # print c_options.kafkaInputServer.split(',')
        # print c_options.kafkaInputGroupId
        # print c_options.kafkaInputSessionTimeout
        # print c_options.kafkaInputTopic
        # print input_args

        kafka_input_server = c_options.kafkaInputServer.split(',')
        consumer = KafkaConsumer(
            bootstrap_servers=kafka_input_server,
            group_id=c_options.kafkaInputGroupId,
            consumer_timeout_ms=c_options.kafkaInputSessionTimeout,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            **input_args
        )
        consumer.subscribe([c_options.kafkaInputTopic])
        consumer_pointer = consumer

        kafka_output_server = c_options.kafkaOutputServer.split(',')
        producer = KafkaProducer(
            bootstrap_servers=kafka_output_server,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            **output_args
        )
        producer_pointer = producer

        c = core.Core(json.load(codecs.open(c_options.configPath, 'r')))

        run_serial_cdrs(c, consumer, producer, c_options.kafkaOutputTopic, indexing=c_options.indexing,
                        worker_id=worker_id)

    except Exception as e:
        # print e
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        print ''.join(lines)

