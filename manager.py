import os
import sys
import traceback
import subprocess
import json
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
import logging
import logstash
import codecs
import requests
import time
from flask import Flask, request, jsonify

from config import config

app = Flask(__name__)

# logging
logger = logging.getLogger(config['logstash']['name'])
logger.setLevel(config['logstash']['level'])
# logger.addHandler(
#     logstash.LogstashHandler(
#         config['logstash']['host'], config['logstash']['port'], version=config['logstash']['version']))
logger.addHandler(logging.FileHandler('log.log'))
# logging.getLogger('werkzeug').setLevel(logging.ERROR) # turn off werkzeug logger for normal info

@app.route('/')
def home():
    return 'DIG ETL Engine\n'


@app.route('/create_project', methods=['POST'])
def create_project():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400

    config_path = os.path.join(config['projects_path'], args['project_name'], 'working_dir/etl_config.json')
    project_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            project_config = json.loads(f.read())

    # # create topics
    # input_topic = project_config.get('input_topic', args['project_name'] + '_in')
    # input_zookeeper_server = project_config.get('input_zookeeper_server', config['input_zookeeper_server'])
    # input_partition = project_config.get('input_partitions', config['input_partitions'])
    # ensure_topic_exists(input_topic, input_zookeeper_server, input_partition)

    output_topic = project_config.get('output_topic', args['project_name'] + '_out')
    # output_zookeeper_server = project_config.get('output_zookeeper_server', config['output_zookeeper_server'])
    output_partition = project_config.get('output_partitions', config['output_partitions'])
    # ensure_topic_exists(output_topic, output_zookeeper_server, output_partition)

    # update logstash pipeline
    output_server = project_config.get('output_server', config['output_server'])
    if config['version'] == 'sandbox':
        update_logstash_pipeline(
            args['project_name'], output_server, output_topic, output_partition)

    return jsonify({}), 201


@app.route('/run_etk', methods=['POST'])
def run_etk():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400
    args['number_of_workers'] = args.get('number_of_workers')

    config_path = os.path.join(config['projects_path'], args['project_name'], 'working_dir/etl_config.json')
    project_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            project_config = json.loads(f.read())

    kill_etk_process(args['project_name'], True)

    # reset input offset in `dig` group
    if 'input_offset' in args and args['input_offset'] == 'seek_to_end':
        input_partitions = project_config.get('input_partitions', config['input_partitions'])
        seek_to_topic_end(args['project_name'] + '_in', input_partitions,
                          config['input_server'], config['input_group_id'])
    # reset output offset in default group
    if 'output_offset' in args and args['output_offset'] == 'seek_to_end':
        output_partitions = project_config.get('output_partitions', config['output_partitions'])
        seek_to_topic_end(args['project_name'] + '_out', output_partitions,
                          config['output_server'])

    run_etk_processes(args['project_name'], args['number_of_workers'], project_config)
    return jsonify({}), 202


@app.route('/kill_etk', methods=['POST'])
def kill_etk():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400
    kill_etk_process(args['project_name'], True)
    return jsonify({}), 201

# @app.route('/delete_topics', methods=['POST'])
# def delete_topics():
#     args = request.get_json(force=True)
#     if 'project_name' not in args:
#         return jsonify({'error_message': 'invalid project_name'}), 400
#
#     config_path = os.path.join(config['projects_path'], args['project_name'], 'working_dir/etl_config.json')
#     project_config = {}
#     if os.path.exists(config_path):
#         with open(config_path, 'r') as f:
#             project_config = json.loads(f.read())
#
#     input_topic = project_config.get('input_topic', args['project_name'] + '_in')
#     output_topic = project_config.get('output_topic', args['project_name'] + '_out')
#     input_zookeeper_server = project_config.get('input_zookeeper_server', config['input_zookeeper_server'])
#     output_zookeeper_server = project_config.get('output_zookeeper_server', config['output_zookeeper_server'])
#     delete_topic(input_topic, input_zookeeper_server)
#     delete_topic(output_topic, output_zookeeper_server)
#     return jsonify({}), 201

@app.route('/etk_status/<project_name>', methods=['GET'])
def etk_status(project_name):
    cmd = 'ps -ef | grep -v grep | grep "tag-mydig-etk-{project_name}"'.format(project_name=project_name)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    return jsonify({'etk_processes':len(output)})

@app.route('/debug/ps', methods=['GET'])
def debug_ps():
    p = subprocess.Popen('ps -ef | grep -v grep | grep "tag-mydig-etk"', stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    return output, 200

def ensure_topic_exists(topic, zookeeper_server, partitions):
    # kafka-topics.sh --create --if-not-exists
    # --zookeeper localhost:2181
    # --replication-factor 1
    # --partitions 4
    # --topic test
    cmd = '{} --create --if-not-exists --zookeeper {} \
    --replication-factor 1 --partitions {} --topic {}'.format(
        os.path.join(config['kafka_bin_path'], 'kafka-topics.sh'),
        ','.join(zookeeper_server),
        partitions,
        topic
    )
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        logger.error('ensure_topic_exists error: {}'.format(topic))
        return
    logger.info('ensure_topic_exists finish: {}'.format(topic))


def seek_to_topic_end(topic, num_partitions, consumers, group_id=None):
    consumer = KafkaConsumer(
        bootstrap_servers=consumers,
        group_id=group_id)
    # need to manually assign partitions if seek_to_end needs to be used here
    partitions = [TopicPartition(topic, i) for i in xrange(num_partitions)]
    consumer.assign(partitions) # conflict to subscribe
    consumer.seek_to_end()
    logger.info('seek_to_topic_end finish: {}'.format(topic))


# def delete_topic(topic, zookeeper_server):
#     # in broker, set `delete.topic.enable` to `true`
#     # kafka-topics.sh --delete --if-exists --zookeeper localhost:2181 --topic test
#     # may have side effects
#     cmd = '{} --delete --if-exists --zookeeper {} --topic {}'.format(
#         os.path.join(config['kafka_bin_path'], 'kafka-topics.sh'),
#         ','.join(zookeeper_server),
#         topic
#     )
#     ret = subprocess.call(cmd, shell=True)
#     if ret != 0:
#         logger.error('delete_topic: {}'.format(topic))
#         return
#     logger.info('delete_topic finish: {}'.format(topic))


def run_etk_processes(project_name, processes, project_config):
    for i in xrange(processes):
        cmd = 'python -u {run_core_path} \
        --tag-mydig-etk-{project_name}-{idx} \
        --config "{working_dir}/etk_config.json" \
        --kafka-input-server "{input_server}" \
        --kafka-input-topic "{input_topic}" \
        --kafka-input-group-id "{input_group_id}" \
        --kafka-input-session-timeout {session_timeout} \
        --kafka-output-server "{output_server}" \
        --kafka-output-topic "{output_topic}" \
        --kafka-input-args "{input_args}" \
        --kafka-output-args "{output_args}" \
        --indexing \
        --worker-id "{idx}" \
        > "{working_dir}/etk_stdout_{idx}.txt"'.format(
            # os.path.join(config['etk_path'], 'etk/run_core_kafka.py')
            run_core_path=os.path.abspath('run_core_kafka.py'),
            project_name=project_name,
            input_topic=project_config.get('input_topic', project_name + '_in'),
            output_topic=project_config.get('output_topic', project_name + '_out'),
            working_dir=os.path.join(config['projects_path'], project_name, 'working_dir'),
            session_timeout=project_config.get('input_session_timeout', config['input_session_timeout']),
            input_server=','.join(project_config.get('input_server', config['input_server'])),
            output_server=','.join(project_config.get('output_server', config['output_server'])),
            input_group_id=project_config.get('input_group_id', config['input_group_id']),
            idx=i,
            input_args=json.dumps(project_config.get('input_args', {})).replace('"', '\\"'),
            output_args=json.dumps(project_config.get('output_args', {})).replace('"', '\\"')
        )
        print cmd
        p = subprocess.Popen(cmd, shell=True) # async

    logger.info('run_etk_processes finish: {}'.format(project_name))
    print 'run_etk_processes finish'


def kill_etk_process(project_name, ignore_error=False):
    cmd = 'ps -ef | grep -v grep | grep "tag-mydig-etk-{}" | awk \'{{print $2}}\' | xargs kill '.format(project_name)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0 and not ignore_error:
        print 'error in kill_etk_process'
    logger.info('kill_etk_process finish: {}'.format(project_name))
    print 'kill_etk_process finish'


def update_logstash_pipeline(project_name, output_server, output_topic, output_partition):
    content = \
'''input {{
  kafka {{
    bootstrap_servers => ["{server}"]
    topics => ["{output_topic}"]
    consumer_threads => "{output_partition}"
    codec => json {{}}
    type => "{project_name}"
    max_partition_fetch_bytes => "10485760"
    max_poll_records => "10"
    fetch_max_wait_ms => "1000"
    poll_timeout_ms => "1000"
   }}
}}
filter {{
  if [type] == "{project_name}" {{
    mutate {{ remove_field => ["_id"] }}
  }}
}}
output {{
  if [type] == "{project_name}" {{
    elasticsearch {{
      document_id  => "%{{doc_id}}"
      document_type => "ads"
      hosts => ["{es_server}"]
      index => "{project_name}"
    }}
  }}
}}'''.format(
    server='","'.join(output_server),
    output_topic=output_topic,
    output_partition=output_partition,
    project_name=project_name,
    es_server=config['es_server']
)

    path = os.path.join(config['logstash']['pipeline'], 'logstash-{}.conf'.format(project_name))
    if not os.path.exists(path):
        with codecs.open(path, 'w') as f:
            f.write(content)


def create_mappings(index_name, payload_file_path):
    try:
        url = '{}/{}'.format(config['es_url'], index_name)
        resp = requests.get(url)
        if resp.status_code // 100 == 4: # if no such index there
            with codecs.open(payload_file_path, 'r') as f:
                payload = f.read() # stringfied json
            resp = requests.put(url, payload)
            if resp.status_code // 100 != 2:
                print 'can not create es index for {}'.format(index_name)
            else:
                print 'es index {} created'.format(index_name)
    except requests.exceptions.ConnectionError:
        # es if not online, retry
        time.sleep(5)
        create_mappings(index_name, payload_file_path)


if __name__ == '__main__':
    try:
        # digui will create indices itself
        # create_mappings('dig-logs', 'elasticsearch/sandbox/mappings/dig_logs.json')
        # create_mappings('dig-states', 'elasticsearch/sandbox/mappings/dig_states.json')

        # general logs
        create_mappings('logs', 'elasticsearch/sandbox/mappings/logs.json')

        app.run(debug=config['debug'], host=config['server']['host'], port=config['server']['port'], threaded=True)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        lines = ''.join(lines)
        print lines
        logger.error(lines)
