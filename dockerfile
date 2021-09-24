FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .
COPY ./DB/emoji_map.json ./DB

CMD [ "python3", "-u", "bot.py"]