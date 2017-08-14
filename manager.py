import os
import sys
import traceback
import subprocess
import json
from kafka import KafkaProducer, KafkaConsumer
import logging
import logstash
from config import config

from flask import Flask, request, jsonify

app = Flask(__name__)

logger = logging.getLogger(config['logstash']['name'])
logger.addHandler(
    logstash.LogstashHandler(
        config['logstash']['host'], config['logstash']['port'], version=config['logstash']['version']))
logger.setLevel(config['logstash']['level'])


@app.route('/')
def home():
    return 'DIG ETL Engine\n'


@app.route('/create_project', methods=['POST'])
def create_project():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400

    # create topics
    ensure_topic_exists(
        args['project_name'] + '_in', config['input_zookeeper_server'], config['input_partitions'])
    ensure_topic_exists(
        args['project_name'] + '_out', config['output_zookeeper_server'], config['output_partitions'])
    return jsonify({}), 201


@app.route('/run_etk', methods=['POST'])
def run_etk():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400
    args['number_of_workers'] = args.get('number_of_workers', 4)

    kill_etk_process(args['project_name'], True)
    # reset input offset in `dig` group
    if 'input_offset' in args and args['input_offset'] == 'seek_to_end':
        seek_to_topic_end(args['project_name'] + '_in', config['input_server'], config['input_group_id'])
    # reset output offset in all groups
    if 'output_offset' in args and args['output_offset'] == 'seek_to_end':
        seek_to_topic_end(args['project_name'] + '_out', config['output_server'])
    if 'delete_input_topic' in args and args['delete_input_topic'] is True:
        delete_topic(args['project_name'] + '_in', config['input_zookeeper_server'])
    if 'delete_output_topic' in args and args['delete_output_topic'] is True:
        delete_topic(args['project_name'] + '_out', config['output_zookeeper_server'])
    run_etk_processes(args['project_name'], args['number_of_workers'])
    return jsonify({}), 202


@app.route('/kill_etk', methods=['POST'])
def kill_etk():
    args = request.get_json(force=True)
    if 'project_name' not in args:
        return jsonify({'error_message': 'invalid project_name'}), 400
    kill_etk_process(args['project_name'], True)
    return jsonify({}), 201


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


def seek_to_topic_end(topic, consumers, group_id=None):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=consumers,
        group_id=group_id)
    consumer.seek_to_end()
    logger.info('seek_to_topic_end finish: {}'.format(topic))


def delete_topic(topic, zookeeper_server):
    # in broker, set `delete.topic.enable` to `true`
    # kafka-topics.sh --delete --if-exists --zookeeper localhost:2181 --topic test
    # may have side effects
    cmd = '{} --delete --if-exists --zookeeper {} --topic {}'.format(
        os.path.join(config['kafka_bin_path'], 'kafka-topics.sh'),
        ','.join(zookeeper_server),
        topic
    )
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        logger.error('delete_topic: {}'.format(topic))
        return
    logger.info('delete_topic finish: {}'.format(topic))


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
        > "{working_dir}/etk_stdout_{idx}.txt"'.format(
            run_core_path=os.path.join(config['etk_path'], 'etk/run_core.py'),
            project_name=project_name,
            working_dir=os.path.join(config['projects_path'], project_name, 'working_dir'),
            session_timeout=config['input_session_timeout'],
            input_server=','.join(config['input_server']),
            output_server=','.join(config['output_server']),
            input_group_id=config['input_group_id'],
            idx=i
        )
        print cmd
        p = subprocess.Popen(cmd, shell=True) # async

    logger.info('run_etk_processes finish: {}'.format(project_name))
    print 'run_etk_processes finish'


def kill_etk_process(project_name, ignore_error=False):
    cmd = 'ps -ef | grep -v grep | grep "tag-mydig-etk-{}" | awk \'{{print $2}}\' | xargs kill -9'.format(project_name)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0 and ignore_error:
        print 'error'
    logger.info('kill_etk_process finish: {}'.format(project_name))
    print 'kill_etk_process finish'


if __name__ == '__main__':
    try:
        app.run(debug=config['debug'], host=config['server']['host'], port=config['server']['port'], threaded=True)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        print lines
        logger.error('\n'.join(line for line in lines))
