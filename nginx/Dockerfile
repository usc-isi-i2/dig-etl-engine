# mydig-webservice
FROM nginx

RUN apt-get update && apt-get install -y openssl

# add current dir to image at last (or it will break the cache of docker)
ADD ./start_nginx.sh /opt/start_nginx.sh

CMD chmod u+x /opt/start_nginx.sh & sh /opt/start_nginx.sh
