# docker pull docker.elastic.co/logstash/logstash:5.5.1
docker run --rm -it -d -e PATH_CONFIG=/usr/share/logstash/pipeline -v /Users/amandeep/Github/dig-etl-engine/logstash/pipeline/:/usr/share/logstash/pipeline/ -v /Users/amandeep/Github/dig-etl-engine/logstash/settings/logstash.yml:/usr/share/logstash/config/logstash.yml docker.elastic.co/logstash/logstash:5.5.1 
