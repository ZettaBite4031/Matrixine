import pathlib
import random
import datetime as dt
import typing as t
import requests
import time


import aiohttp
import discord
from discord.ext import commands
from urllib.parse import quote

import util


def _count_generator(reader):
    b = reader(1024 * 1024)
    while b:
        yield b
        b = reader(1024 * 1024)


class Fun(commands.Cog):
    """Just random fun commands to add some personality"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="hello",
        aliases=["hi", "hey", "hiya", "sup"],
        description="Greets the user",
    )
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def greet_command(self, ctx):
        await ctx.send(
            f"{random.choice(['Hello', 'Hi', 'Whats up', 'Hiya'])}, {ctx.author.mention}"
        )

    @commands.hybrid_command(
        name="dice",
        aliases=["roll"],
        description="Rolls a dice. Format: 6d20. Rolls 6 20 sided die",
    )
    async def roll_dice_command(self, ctx, die_string: str, summed: str = "yes"):
        dice, value = (int(term) for term in die_string.split("d"))
        if dice <= 0 or value <= 0:
            return await ctx.send("Please choose a value above 0")
        elif dice > 100 or value > 10000:
            return await ctx.send("Please choose smaller values!")
        rolls = [random.randint(1, value) for _ in range(dice)]
        response = (
            sum(rolls)
            if summed.lower() == "yes"
            else " + ".join([str(roll) for roll in rolls]) + f" = {sum(rolls)}"
        )
        await ctx.send(response)

    @roll_dice_command.error
    async def roll_dice_error(self, ctx, exc):
        if isinstance(exc.original, discord.HTTPException):
            await ctx.send("Too many dice rolled! Discord message length hit!")

    @commands.hybrid_command(name="slap", aliases=["hit"], description="Slap a dude")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def slap_member_command(
        self, ctx, member: discord.Member, *, reason: t.Optional[str] = "no reason"
    ):
        choices = [
            "slapped",
            "hit",
            "punched",
            "socked",
            "bitch-slapped",
            "brutally assaulted",
        ]
        await ctx.send(
            f"{ctx.author.mention} {random.choice(choices)} {member.mention} for {reason}"
        )

    @slap_member_command.error
    async def slap_member_error(self, ctx, exc):
        if isinstance(exc, commands.BadArgument):
            await ctx.send("That member does not exit!")
        elif isinstance(exc, commands.MissingRequiredArgument):
            await ctx.send("You need to specify a member!")

    @commands.hybrid_command(
        name="echo", description="Echos the input and deletes the original command"
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def echo_message_command(self, ctx, *, message):
        await ctx.message.delete()
        await ctx.send(message)

    @commands.hybrid_command(
        name="animal_fact",
        aliases=["afact"],
        description="Shows a fun animal fact."
        "\nOptions are: dog, cat, panda, bird, fox,"
        " koala, red_panda, raccoon, and kangaroo",
    )
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def animal_fact_command(self, ctx, animal: t.Optional[str]):
        choices = [
            "dog",
            "cat",
            "panda",
            "bird",
            "fox",
            "koala",
            "red_panda",
            "raccoon",
            "kangaroo",
        ]
        if animal == "red panda":
            animal = "red_panda"
        if not animal or animal not in choices:
            animal = random.choice(choices)

        url = "https://some-random-api.com/animal/{}".format(animal)
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await resp.json()
            image = data["image"]
            fact = data["fact"]
            embed = discord.Embed(
                title=f"{animal.capitalize()} fact!",
                description=f"**{fact}**",
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_image(url=image)
            embed.set_footer(text=f"API: {url[8:]}")
            await ctx.send(embed=embed)

    @animal_fact_command.error
    async def animal_fact_command_error(self, ctx, exc):
        pass

    @commands.hybrid_command(
        name="animal_image",
        aliases=["apic", "apicture"],
        description="Show a picture of 9 separate animals! "
        "Dogs, cats, pandas, birds, foxes, koalas, red pandas, racoons, and kangaroos!",
    )
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def animal_image_command(self, ctx, animal: t.Optional[str]):
        choices = [
            "dog",
            "cat",
            "panda",
            "bird",
            "fox",
            "koala",
            "red_panda",
            "raccoon",
            "kangaroo",
        ]
        if animal == "red panda":
            animal = "red_panda"
        if not animal or animal not in choices:
            animal = random.choice(choices)

        url = "https://some-random-api.com/img/{}".format(animal)
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await resp.json()
            image = data["link"]
            embed = discord.Embed(
                title=f"{animal.capitalize().replace('_', ' ')} image!",
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_image(url=image)
            embed.set_footer(text=f"API: {url[8:]}")
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar.url
            )
            await ctx.send(embed=embed)

    @animal_image_command.error
    async def animal_image_command_error(self, ctx, exc):
        pass

    @commands.hybrid_command(name="quote", description="Sends a random quote.")
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def quote(self, ctx):
        url = "https://zenquotes.io/api?api=quotes"
        async with aiohttp.request("GET", url, headers={}) as response:
            if response.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await response.json()
            data = data[0]
            quote = data["q"]
            author = data["a"]
            embed = discord.Embed(
                description="{}".format(quote),
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_author(name="Quote: ", icon_url=ctx.author.avatar.url)
            embed.set_footer(text="Quote by {}".format(author))
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="Pings the bot for its latency to the API and the WebSocket.",
    )
    async def _ping(self, ctx):
        start_time = time.time()
        await self.bot.fetch_channel(ctx.channel.id)
        end_time = time.time()
        api_latency = round((end_time - start_time) * 1000)
        ws_latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title="Latency", color=self.bot.COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(name="Ping", value=f"```{api_latency}ms```")
        embed.add_field(name="WebSocket", value=f"```{ws_latency}ms```")
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="anime", description="Allows the user to hug, wink at, and pat users!"
    )
    async def anime_command(
        self, ctx, action: t.Optional[str], target: t.Optional[discord.User]
    ):
        choices = ["wink", "pat", "hug"]
        if action is None or action not in choices:
            action = random.choice(choices)

        url = "https://some-random-api.com/animu/{}".format(action)
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            if target is None:
                content = f"Don't worry, I'll {action} you, {ctx.author.mention}..."
                title = f"Don't worry, I'll {action} you, {ctx.author.display_name}..."
            else:
                choices = [
                    f"{ctx.author.mention} gave {target.mention} a little bit of a {action}",
                    f"{ctx.author.mention} just {action}ed {'at ' if action == 'wink' else ''} {target.mention}",
                    f"{ctx.author.mention} {action}ed {'at ' if action == 'wink' else ''} {target.mention}",
                ]
                content = random.choice(choices)
                title = action.capitalize() + "!"

            data = await resp.json()
            gif = data["link"]
            embed = discord.Embed(
                title=title, color=self.bot.COLOR, timestamp=dt.datetime.now()
            )
            embed.set_image(url=gif)
            embed.set_footer(text=f"API: {url[8:]}")
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar.url
            )
            await ctx.send(content, embed=embed)

    @commands.hybrid_command(
        name="joke",
        description="Sends a joke. The devs are not reasonable for how cringe they are.",
    )
    async def send_joke_command(self, ctx):
        url = "https://some-random-api.com/joke"
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await resp.json()
            joke = data["joke"]
            embed = discord.Embed(
                title="You asked for this.",
                description=joke,
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_footer(text=f"API: {url[8:]}")
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar.url
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="pokedex",
        aliases=["pokemon"],
        description="Sends the information of a pokemon!",
    )
    async def pokedex_command(self, ctx, pokemon: str):
        pokemon = pokemon.lower()
        url = f"https://some-random-api.com/pokemon/pokedex?pokemon={pokemon}"
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await resp.json()
            name = data["name"]
            ID = data["id"]
            types = data["type"]
            species = data["species"]
            abilities = data["abilities"]
            height = data["height"]
            weight = data["weight"]
            base_xp = data["base_experience"]
            gender_distribution = data["gender"]
            egg_groups = data["egg_groups"]
            stats = data["stats"]
            hp = stats["hp"]
            attack = stats["attack"]
            defense = stats["defense"]
            sp_atk = stats["sp_atk"]
            sp_def = stats["sp_def"]
            speed = stats["speed"]
            total = stats["total"]
            family = data["family"]
            evolution_stage = family["evolutionStage"]
            evolution_line = family["evolutionLine"]
            sprites = data["sprites"]
            description = data["description"]
            generation = data["generation"]

            description = (
                f"{name.capitalize()}, ID {ID}, is a {', '.join(types)} {species[0]} pokemon with "
                f"{', '.join(abilities)} abilities. Standing at {height} and weighing in at {weight}, "
                f"{name.capitalize()} is a pokemon with {base_xp} base experience and a gender distribution "
                f"of {' and '.join(gender_distribution)} and is considered to have {', '.join(egg_groups)} "
                f"egg groups by studiers. {name.capitalize()} has {hp} hp with an attack that deals {attack}"
                f" damage and a defense of {defense}, but has been recorded to have special attacks and "
                f"defenses that deal {sp_atk} and {sp_def} accordingly, and can move at a speed of {speed} "
                f"for a total of {total}.\nBeing at evolution stage {evolution_stage} of an evolution line "
                f"of {', '.join(evolution_line)}, a description of {name.capitalize()} is one of that "
                f"{description}\n{name.capitalize()} is generation {generation}."
            )

            embed = discord.Embed(
                title=name.capitalize(),
                description=description,
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar.url
            )
            embed.set_footer(text=f"API: some-random-api.com/pokemon/pokedex")
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="meme", description="Sends meme pog")
    async def meme_command(self, ctx):
        url = "https://some-random-api.com/meme"
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await resp.json()
            embed = discord.Embed(
                title=f"**{data['caption']}**",
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar.url
            )
            embed.set_footer(text=f"API: {url[8:]}")
            embed.set_image(url=data["image"])
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="token",
        aliases=["genToken"],
        description="Generates a completely random, unreproducible *fake* bot token.",
    )
    async def generate_bot_token_command(self, ctx):
        seed = random.SystemRandom().randint(ctx.author.id, ctx.author.id * 10)
        url = f"https://some-random-api.com/bottoken?id={seed}"
        async with aiohttp.request("GET", url, headers={}) as resp:
            if resp.status != 200:
                return await ctx.send(
                    "Hmm... Something went wrong.. Perhaps try again?"
                )

            data = await resp.json()
            embed = discord.Embed(
                title="Bot Token",
                description=f"Here is your generated bot token!\n{data['token']}",
                color=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar.url
            )
            embed.set_footer(text=f"*These tokens are all fake.* API: {url[8:26]}")
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="color",
        description="Sends an embed with the corresponding hexadecimal color sent in the command.",
    )
    async def hex_to_color_command(self, ctx, hexadecimal: str):
        embed = discord.Embed(
            title=hexadecimal, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: https://some-random-api.com/canvas/colorviewer")
        embed.set_image(
            url=f"https://some-random-api.com/canvas/colorviewer?hex={hexadecimal.replace('0x', '')}"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="lines",
        description="Displays the number of lines in the bot's source code.",
    )
    async def lines_of_code_command(self, ctx):
        cogs = [p.stem for p in pathlib.Path(".").glob("./src/bot/cogs/*.py")]
        total = 12
        cog_dict = dict()
        for cog in cogs:
            with open(f"./src/bot/cogs/{cog}.py", "rb") as fp:
                c_generator = _count_generator(fp.raw.read)
                count = sum(buffer.count(b"\n") for buffer in c_generator)
                cog_dict[cog] = count
                total += count

        with open("./src/bot/bot.py", "rb") as fp:
            c_generator = _count_generator(fp.raw.read)
            main_count = sum(buffer.count(b"\n") for buffer in c_generator)
            total += main_count

        embed = discord.Embed(
            title=f"{self.bot.BOT_INFO.name} source code length!",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="Bot developed by " + self.bot.OWNER_UN)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(
            name="Total length:", value=f"`{total}` lines of code!", inline=False
        )
        embed.add_field(
            name="Main File:", value=f"`{main_count}` lines of code", inline=False
        )
        embed.add_field(name="**Modules**", value="** **", inline=False)
        cog_dict_keys = sorted(cog_dict.keys(), key=lambda k: cog_dict[k], reverse=True)
        for cog in cog_dict_keys:
            embed.add_field(
                name=cog.capitalize(), value=f"`{cog_dict[cog]}` lines.", inline=True
            )

        for _ in range(len(embed.fields) % 3):
            embed.add_field(name="", value="", inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="color_viewer", description="Generates a picture of the specified color"
    )
    async def color_viewer_command(self, ctx, color: str):
        try:
            color = hex(int(color.strip("0x"), 16))
        except ValueError:
            return await ctx.send("Please supply valid hexadecimal! (0xFFFFFF)")

        url = f"https://some-random-api.com/canvas/misc/colorviewer?hex={color}&avatar=".replace(
            "0x", ""
        )
        embed = discord.Embed(
            title=str(color), color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/misc/colorviewer")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="nobitches",
        description="Returns the no bitches meme but with a custom message",
    )
    async def no_bitches_command(self, ctx, *, msg: str):
        url = f"https://some-random-api.com/canvas/misc/nobitches?no={quote(msg)}"
        embed = discord.Embed(
            title=msg, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: some-random-api.com/canvas/misc/nobitches")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="oogway", description="Share Master Oogway's wisdom")
    async def oogway_command(self, ctx, *, msg: str):
        url = "https://some-random-api.com/canvas/misc/oogway"
        if random.randint(0, 5000) > 2500:
            url += "2"
        url += f"?quote={quote(msg)}"

        embed = discord.Embed(
            title="Master Oogway's Wisdom",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: some-random-api.com/canvas/misc/oogway")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="dictionary", aliases=["definition"], description="An actual dictionary"
    )
    async def dictionary_command(self, ctx, word: str):
        url = f"https://some-random-api.com/others/dictionary?word={word}"
        data = requests.get(url=url).json()
        response = f"The definition of the word \"{word}\" is as follows:\n{data['definition']}"
        await ctx.reply(response)

    @commands.hybrid_command(
        name="binary",
        description="Encode or decode text to/from binary. i.e binary decode 01000001",
    )
    async def binary_text_command(self, ctx, option, *, content):
        url = f"https://some-random-api.com/others/binary?{option}={quote(content)}"
        data = requests.get(url).json()
        index = "binary" if option == "encode" else "text"
        response = f"{content}\n**=**\n{data[index]}"
        await ctx.reply(response)

    @commands.hybrid_command(
        name="base64", description="Encode or decode text to/from base64"
    )
    async def binary_text_command(self, ctx, option, *, content):
        url = f"https://some-random-api.com/others/base64?{option}={quote(content)}"
        data = requests.get(url).json()
        index = "base64" if option == "encode" else "text"
        response = f"{content}\n**=**\n{data[index]}"
        await ctx.reply(response)

    @commands.hybrid_command(name="uptime")
    async def uptime_command(self, ctx):
        start_datetime = self.bot.START_DATETIME
        now_datetime = dt.datetime.now(tz=dt.timezone.utc)

        uptime_timedelta = now_datetime - start_datetime
        uptime_string = util.timedelta_to_string(uptime_timedelta)
        embed = discord.Embed(
            title="Matrixine Uptime!",
            description=f"Matrixine has been running nonstop since \n`{start_datetime.strftime('%m-%d-%Y %H:%M:%S')}`",
            color=self.bot.COLOR,
        )
        embed.add_field(
            name="That's a total time of", value=f"```{uptime_string}```", inline=False
        )
        embed.set_author(name="Uptime Info", icon_url=self.bot.user.avatar.url)
        embed.set_footer(
            text=f"Uptime requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url,
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))
