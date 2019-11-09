FROM smart-program/worker-base-image

ADD . /app
WORKDIR /app

RUN pip install -r ./requirements.txt

CMD ["./start.sh"]