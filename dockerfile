FROM gorialis/discord.py

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

#ENV discord_token=
#ENV twitter_access_token=
#ENV twitter_access_token_secret=
#ENV twitter_api_key=
#ENV twitter_api_key_secret=

CMD [ "python", "bot.py"]