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
# logging.Formatter(config['logging']['format'])
log_stdout = logging.StreamHandler(sys.stdout)
# log_stdout.setFormatter(log_formatter)
logger.addHandler(log_stdout)
# logger.addHandler(
#     logstash.LogstashHandler(
#         config['logstash']['host'], config['logstash']['port'], version=config['logstash']['version']))
logger.setLevel(logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # turn off werkzeug logger for normal info


@app.route('/')
def home():
    return 'DIG ETL Engine\n'


@app.route('/create_project', methods=['POST'])
def create_project():
    """
    make sure auto.create.topics.enable=true in kafka
    """
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400

    etl_config = get_project_etl_config(args['project_name'])
    output_topic = etl_config.get('output_topic', args['project_name'] + '_out')
    output_partition = etl_config.get('output_partitions', config['output_partitions'])

    # update logstash pipeline
    output_server = etl_config.get('output_server', config['output_server'])
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

    etl_config = get_project_etl_config(args['project_name'])

    kill_and_clean_up_queue(args, etl_config)

    run_etk_processes(args['project_name'], args['number_of_workers'], etl_config)
    return jsonify({}), 202


@app.route('/kill_etk', methods=['POST'])
def kill_etk():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400

    config_path = os.path.join(config['projects_path'], args['project_name'], 'working_dir/etl_config.json')
    project_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            project_config = json.loads(f.read())

    kill_and_clean_up_queue(args, project_config)

    return jsonify({}), 202


@app.route('/etk_status/<project_name>', methods=['GET'])
def etk_status(project_name):
    cmd = 'ps -ef | grep -v grep | egrep "tag-mydig-etk-{project_name}-[[:digit:]]{{1,}}" | wc -l' \
           .format(project_name=project_name)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    try:
        process_num = int(output) / 2
        return jsonify({'etk_processes': process_num})
    except:
        logger.exception('etk_status error: {}'.format(project_name))
        return 'error', 500


@app.route('/debug/ps', methods=['GET'])
def debug_ps():
    p = subprocess.Popen('ps -ef | grep -v grep | grep "tag-mydig-etk"', stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    return output, 200


def get_project_etl_config(project_name):
    """
    get project level etl config
    """
    config_path = os.path.join(config['projects_path'], project_name, 'working_dir/etl_config.json')
    etl_config = dict()
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            etl_config = json.loads(f.read())
    return etl_config


def kill_and_clean_up_queue(args, project_config):
    """
    Kill ETK processes, set kafka offset pointer to the end
    """
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


def seek_to_topic_end(topic, num_partitions, consumers, group_id=None):
    consumer = KafkaConsumer(
        bootstrap_servers=consumers,
        group_id=group_id)
    # need to manually assign partitions if seek_to_end needs to be used here
    partitions = [TopicPartition(topic, i) for i in range(num_partitions)]
    consumer.assign(partitions)  # conflict to subscribe
    consumer.seek_to_end()
    logger.info('seek_to_topic_end finish: {}'.format(topic))


def run_etk_processes(project_name, processes, project_config):
    for i in range(processes):
        cmd = 'python -u {etk_worker_path} \
        --tag-mydig-etk-{project_name}-{idx} \
        --project-name "{project_name}" \
        --kafka-input-args "{input_args}" \
        --kafka-output-args "{output_args}" \
        --worker-id "{idx}" \
        --logger-name "{logger_name}"'.format(
            etk_worker_path=os.path.abspath('etk_worker.py'),
            project_name=project_name,
            idx=i,
            input_args=json.dumps(project_config.get('input_args', {})).replace('"', '\\"'),
            output_args=json.dumps(project_config.get('output_args', {})).replace('"', '\\"'),
            logger_name=config['logstash']['name']
        )
        p = subprocess.Popen(cmd, shell=True)  # async

    logger.info('run_etk_processes finish: {}'.format(project_name))


def kill_etk_process(project_name, ignore_error=False):
    cmd = ('ps -ef | grep -v grep | egrep "tag-mydig-etk-{project_name}-[[:digit:]]{{1,}}"'
            '| awk \'{{print $2}}\'| xargs --no-run-if-empty kill ').format(project_name=project_name)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0 and not ignore_error:
        logger.error('error in kill_etk_process')
    logger.info('kill_etk_process finish: {}'.format(project_name))


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
    """
    create mapping in es
    """
    try:
        url = '{}/{}'.format(config['es_url'], index_name)
        resp = requests.get(url)
        if resp.status_code // 100 == 4:  # if no such index there
            with codecs.open(payload_file_path, 'r') as f:
                payload = f.read()  # stringfied json
            resp = requests.put(url, payload)
            if resp.status_code // 100 != 2:
                logger.error('can not create es index for {}'.format(index_name))
            else:
                logger.error('es index {} created'.format(index_name))
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
        logger.exception('Exception in dig-etl-engine manager')
