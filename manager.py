import os
import sys
import subprocess
import json
from kafka import KafkaProducer, KafkaConsumer
from config import config


def ensure_topic_exists(topic, zookeeper_server, partitions):
    # kafka-topics.sh --create --if-not-exists
    # --zookeeper localhost:2181
    # --replication-factor 1
    # --partitions 4
    # --topic test
    cmd = '{} --create --if-not-exists --zookeeper {} --replication-factor 1 --partitions {} --topic {}'.format(
        os.path.join(config['kafka_bin_path'], 'kafka-topics.sh'),
        ','.join(zookeeper_server),
        partitions,
        topic
    )
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        pass


def run_etk_processes(project_name, processes):
    for i in xrange(processes):
        cmd = 'python -u {run_core_path} \
        --tag-mydig-etk-{project_name}-{idx} \
        --config "{working_dir}/etk_config.json" \
        --kafka-input-server "{input_server}" \
        --kafka-input-topic "{project_name}_in" \
        --kafka-input-group-id "{input_group_id}" \
        --kafka-input-session-timeout {session_timeout} \
        --kafka-output-server "{output_server}" \
        --kafka-output-topic "{project_name}_out" \
        > "{working_dir}/etk_stdout_{idx}.txt" &'.format(
            run_core_path=os.path.join(config['etk_path'], 'etk/run_core.py'),
            project_name=project_name,
            working_dir=os.path.join(config['projects_path'], project_name, 'working_dir'),
            session_timeout=config['input_session_timeout'],
            input_server=','.join(config['input_server']),
            output_server=','.join(config['output_server']),
            input_group_id=config['input_group_id'],
            idx=i
        )
        ret = subprocess.call(cmd, shell=True)
        if ret != 0:
            pass


def kill_etk_process(project_name, ignore_error=False):
    cmd = 'ps -ef | grep -v grep | grep "tag-mydig-etk-{}" | awk \'{{print $2}}\' | xargs kill -9'.format(project_name)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0 and ignore_error:
        pass


def clean_data(project_name):
    pass

if __name__ == '__main__':
    # input init
    ensure_topic_exists(config['manager_topic'], config['input_zookeeper_server'], 1) # only need 1 partition
    consumer = KafkaConsumer(
        bootstrap_servers=config['input_server'],
        value_deserializer=lambda v: json.loads(v.decode('utf-8')))
    consumer.subscribe([config['manager_topic']])

    # output init
    producer = KafkaProducer(
        bootstrap_servers=config['output_server'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    # interpret
    for msg_obj in consumer:
        try:
            msg = msg_obj.value
            if msg['cmd'] == 'create_project':
                # create topic
                ensure_topic_exists(msg['project_name'] + '_in',
                                    config['input_zookeeper_server'], config['input_partitions'])
                ensure_topic_exists(msg['project_name'] + '_out',
                                    config['output_zookeeper_server'], config['output_partitions'])
            elif msg['cmd'] == 'run_etk':
                kill_etk_process(msg['project_name'], True)
                run_etk_processes(msg['project_name'], msg['number_of_workers'])
            elif msg['cmd'] == 'kill_etk':
                kill_etk_process(msg['project_name'])
            else:
                raise Exception('unknown command')
        except Exception as e:
            print e
