from dotenv import load_dotenv
import urllib
import os


class Config:
    def __init__(self):
        load_dotenv()
        self.DiscordToken = os.getenv("DISCORD_TOKEN")
        mongo_pwd = urllib.parse.quote(os.getenv("MONGO_PASSWD"))
        self.MongoLogin = f"mongodb://{os.getenv('MONGO_USER')}:{mongo_pwd}@{os.getenv('MONGO_HOST')}/MatrixineDB?authSource=admin"
        self.LavalinkURI = f"ws://{os.getenv('LAVALINK_URI')}"
        self.LavalinkPasswd = os.getenv("LAVALINK_PASSWD")
        self.SpotifyUser = os.getenv("SPOTIFY_USER")
        self.SpotifySecret = os.getenv("SPOTIFY_SECRET")
        self.Password = os.getenv("PASSWORD")
        self.IP_Addr = os.getenv("IP_ADDR")
