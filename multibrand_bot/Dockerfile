FROM python:stretch
COPY ./multibrand_bot/requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
ADD . /code
WORKDIR /code
CMD ["python3", "./multibrand_bot/bot.py"]