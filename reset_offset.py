from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata

broker_list = [
    # '54.202.16.183:9093',
    # '54.213.217.208:9093',
    # '34.223.224.66:9093',
    # '54.214.183.205:9093',
    # '54.191.242.156:9093'
    'localhost:9092'
]

args = {
    # "security_protocol": "SSL",
    # "ssl_cafile": "/Users/yixiang/Projects/ISI/mydig-projects/dig3_ht/kafka_ssl/ca-cert.pem",
    # "ssl_certfile": "/Users/yixiang/Projects/ISI/mydig-projects/dig3_ht/kafka_ssl/client-cert.pem",
    # "ssl_keyfile": "/Users/yixiang/Projects/ISI/mydig-projects/dig3_ht/kafka_ssl/client-key.pem",
    # "ssl_check_hostname": False
}


part_num = 1
group_id = 'dig_test'
topic_id = 'test'

consumer = KafkaConsumer(
    bootstrap_servers=broker_list,
    group_id=group_id,
    **args
)

meta = consumer.partitions_for_topic(topic_id)
assigned_parts = []
for i in range(part_num):
    assigned_parts.append(TopicPartition(topic_id, i))
consumer.assign(assigned_parts)
for p in assigned_parts:
    consumer.seek(p, 0)
    # sometimes it is blocked, need to restart
    consumer.commit({p:OffsetAndMetadata(0, meta)})

print 'done'