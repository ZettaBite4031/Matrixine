import datetime as dt
import pathlib as pl

import aiohttp
import discord
import logging
from pymongo import MongoClient
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import inspect
from discord.utils import _ColourFormatter

from .config import Config


class MatrixineBot(commands.Bot):
    def __init__(self, config: Config):
        self.CONFIG = config
        self.TOKEN = self.CONFIG.DiscordToken
        self.COLOR = 0x1EACC4
        self.OWNER_ID = [901689854411300904]
        self.OWNER_UN = "zettabitep"
        self.VERSION = "0.0.1"
        self.PREFIX = "M!"
        self.DISCORD_API = "https://discord.com/api/v9/"
        self.APSCHEDULER = AsyncIOScheduler
        self.MONGO_CLIENT = MongoClient(config.MongoLogin)
        self.MONGO_DB = self.MONGO_CLIENT["MatrixineDB"]
        self.STDOUT_ID = 1230708641481363538

        self.LOGGER = logging.getLogger("Matrixine")
        self.LOGGER.setLevel(logging.DEBUG)
        self.LOGGER.handlers.clear()
        console_handler = logging.StreamHandler()
        formatter = _ColourFormatter()
        console_handler.setFormatter(formatter)
        self.LOGGER.addHandler(console_handler)

        self.COGS = [p.stem for p in pl.Path(".").glob("./src/bot/cogs/*.py")]
        super().__init__(
            command_prefix=commands.when_mentioned_or(self.PREFIX),
            intents=discord.Intents.all(),
            activity=discord.Game(name=f"/help OR {self.PREFIX}help"),
            help_command=None,
        )

    @property
    def latency_ms(self):
        return f"{super().latency * 1000:,.2f}ms"

    def log(self, level, message):
        import inspect

        self.LOGGER.log(
            level=level,
            msg=f"\x1b[35m{inspect.stack()[1].function}:{inspect.stack()[1].lineno:<12}\x1b[0m {message}",
        )

    async def setup_hook(self) -> None:
        self.log(logging.INFO, "Beginning setup...")
        for cog in self.COGS:
            await self.load_extension(f"bot.cogs.{cog}")
            self.log(logging.INFO, f"Loaded {cog.capitalize()} cog")

        self.log(logging.INFO, "Setup finished...")

    def run(self, **kwargs):
        self.log(logging.INFO, "Running bot...")
        super().run(token=self.TOKEN, reconnect=True)

    async def close(self):
        self.log(logging.INFO, "Closing connection to Discord...")
        self.MONGO_CLIENT.close()
        await self.AIOHTTP_SESSION.close()
        await super().close()

    async def on_connect(self):
        self.log(logging.INFO, f"Bot connected to Discord. Latency: {self.latency_ms}")

    async def on_resumed(self):
        self.log(logging.INFO, f"Connection resumed... Latency: {self.latency_ms}")

    # async def on_error(self, err, *args, **kwargs):
    #     self.log(logging.ERROR, f"Encountered error! {err}")

    async def on_command_error(self, ctx, exc):
        import inspect

        for stack in inspect.stack():
            self.log(logging.ERROR, f"{stack.function}:{stack.lineno}")
        self.log(
            logging.ERROR,
            f"Encountered error ({exc}) in {ctx.command} from {ctx.guild.name} ({ctx.guild.id})",
        )
        if hasattr(exc, "original"):
            raise exc.original
        raise exc

    async def on_ready(self):
        self.AIOHTTP_SESSION = aiohttp.ClientSession()
        self.BOT_INFO = await self.application_info()
        self.CLIENT_ID = self.BOT_INFO.id
        self.STDOUT = self.get_channel(self.STDOUT_ID)
        await self.STDOUT.send(
            f"`{dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}` | Bot ready! Latency: {self.latency_ms}."
        )
        self.log(logging.INFO, f"Bot ready... Latency: {self.latency_ms}")

        await self.wait_until_ready()
        import wavelink

        node: list[wavelink.Node] = [
            wavelink.Node(
                uri=self.CONFIG.LavalinkURI, password=self.CONFIG.LavalinkPasswd
            )
        ]
        await wavelink.Pool.connect(nodes=node, client=self, cache_capacity=100)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)
        if ctx.command is not None:
            self.log(
                logging.INFO,
                f"Processing command `{ctx.command.name}` from {ctx.guild.name} ({ctx.guild.id})",
            )
            await self.invoke(ctx)

    async def on_message(self, msg):
        if not msg.author.bot:
            await self.process_commands(msg)

    @commands.is_owner()
    @commands.hybrid_command(name="refresh_commands")
    @discord.app_commands.guilds(977346571815501905)
    async def _refresh(self, ctx):
        dev_guild: discord.Guild = self.get_guild(977346571815501905)
        self.log(logging.INFO, f"Current development server: {dev_guild.name}")
        self.tree.clear_commands(guild=dev_guild)
        synced_commands = await self.tree.sync(guild=dev_guild)
        self.log(logging.INFO, f"Synced {len(synced_commands)} commands with Discord")
        await ctx.reply("Refreshed the commands!")
