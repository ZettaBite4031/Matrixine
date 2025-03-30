import io
import typing as t
import random as r
import datetime as dt
from urllib.parse import quote

import discord
import requests
from PIL import Image
from discord.ext import commands
from pixelsort import pixelsort as pxs

SRA_EFFECTS = {
    "blur": {
        "name": "Blur!",
        "endpoint": "canvas/misc/blur/",
    },
    "pixelate": {"name": "Pixelate!", "endpoint": "canvas/misc/pixelate/"},
    "simp": {"name": "SIMP!", "endpoint": "canvas/misc/simpcard/"},
    "horny": {"name": "Horny.", "endpoint": "canvas/misc/horny/"},
    "lolice": {
        "name": "Lolice!",
        "endpoint": "canvas/misc/lolice",
    },
    "gay-bg": {"name": "G A Y!", "endpoint": "canvas/misc/lgbt"},
    "pan-bg": {"name": "Pan 🍳", "endpoint": "canvas/misc/pansexual"},
    "nonbinary-bg": {"name": "Nonbinary", "endpoint": "canvas/misc/nonbinary"},
    "lesbian-bg": {"name": "Lesbian", "endpoint": "canvas/misc/lesbian"},
    "bisexual-bg": {"name": "Bisexual", "endpoint": "canvas/misc/bisexual"},
    "trans-bg": {"name": "Trans!", "endpoint": "canvas/misc/transgender"},
    "circle": {"name": "Snip! Cropped to a circle!", "endpoint": "canvas/misc/circle"},
    "genshin": {"name": "Gayshit Infact", "endpoint": "canvas/misc/namecard"},
    "spin": {"name": "Spin.", "endpoint": "canvas/misc/spin"},
    "ps2": {"name": "D V D", "endpoint": "canvas/misc/tonikawa"},
    "blue": {"name": "Blue-ified!", "endpoint": "canvas/filter/blue"},
    "blurple": {"name": "Blurple!", "endpoint": "canvas/filter/blurple"},
    "blurple2": {
        "name": "Blurple 2 electric boogaloo!!",
        "endpoint": "canvas/filter/blurple2",
    },
    "greyscale": {
        "name": "All grey 1920's like!",
        "endpoint": "canvas/filter/greyscale",
    },
    "invertgreyscale": {
        "name": "Inverted and grey!",
        "endpoint": "canvas/filter/invertgreyscale",
    },
}


class Avatar(commands.Cog):
    """Some fun avatar filters/overlays/etc to mess with profile pictures"""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group("avatar", aliases=["pfp"])
    async def avatar_command_group(self, ctx):
        pass

    @avatar_command_group.command(
        name="glitch", description="Glitches a user's profile picture."
    )
    async def glitch_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        target = target or ctx.author

        async with ctx.typing():
            re = requests.get(
                f"{target.avatar.url}".replace("webp", "png").replace("gif", "png")
            )
            img = Image.open(io.BytesIO(re.content))
            glitch = pxs(
                img,
                lower_threshold=0.1,
                upper_threshold=0.85,
                sorting_function="saturation",
                randomness=10,
            )
            img_binary = io.BytesIO()
            glitch.save(img_binary, "PNG")
            img_binary.seek(0)
            await ctx.send(
                "Here is your a̶̩͇͛̎̽̉̉̚v̷̞͖̣͊̇̆͆͘ą̴̪͈͚̓̊̎͌̽͆̀͒̎̽͒̉̕͘͜ţ̸̲̗͇̯̼̱̱͊͗̋͆̋͐͘a̶̓͗̅͒͑̈́̾͜͝r̸̬̪̬͊̀",
                file=discord.File(fp=img_binary, filename="glitched.png"),
            )

    @avatar_command_group.command(
        name="sort",
        description="Sorts the user's pfp.\nThere are 5 sort choices: Lightness, Hue, "
        "Intensity, Minimum, and Saturation.\nThresholds describe the bounds of "
        "the sort, and are limited to 0 through 1.\nThe angle determines at what"
        " angle the sort starts.\nThe randomness controls how accurate the "
        "sort is.",
    )
    async def pixelsort_avatar_command(
        self,
        ctx: commands.Context,
        sort: t.Optional[str],
        low_threshold: t.Optional[float],
        up_threshold: t.Optional[float],
        angle: t.Optional[float],
        randomness: t.Optional[float],
        target: t.Optional[discord.User],
    ):
        target = target or ctx.author
        low_threshold = low_threshold or 0
        up_threshold = up_threshold or 1
        angle = angle or 0
        randomness = randomness or 0

        if 0 > up_threshold or up_threshold > 1:
            return await ctx.send("The upper threshold must be within 0-1.")
        if 0 > low_threshold or low_threshold > 1:
            return await ctx.send("The lower threshold must be within 0-1.")

        from pixelsort.sorting import choices

        choices = list(choices.keys())
        sort = sort or r.choice(choices)
        sort = sort.lower()
        if sort not in choices:
            return await ctx.send(
                "You must choose one of the viable sorts!\n"
                + ", ".join(choices).capitalize()
            )

        async with ctx.typing():
            re = requests.get(
                f"{target.avatar.url}".replace("webp", "png").replace("gif", "png")
            )
            img = Image.open(io.BytesIO(re.content))
            sortedImg = pxs(
                img,
                lower_threshold=low_threshold,
                upper_threshold=up_threshold,
                sorting_function=sort,
                angle=abs(angle),
                randomness=abs(randomness),
            )
            img_binary = io.BytesIO()
            sortedImg.save(img_binary, "PNG")
            img_binary.seek(0)
            await ctx.send(
                "Here is your sorted avatar!",
                file=discord.File(fp=img_binary, filename="sorted.png"),
            )

    async def some_random_api(self, ctx, effect, target):
        target = target or ctx.author
        effect = SRA_EFFECTS[effect]
        embed = discord.Embed(
            title=effect["name"], color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/{effect['endpoint']}")
        embed.set_image(
            url=f"https://some-random-api.com/{effect['endpoint']}?avatar={target.avatar.replace(format='png', size=1024)}"
        )
        await ctx.send(embed=embed)

    @avatar_command_group.command(name="blur", description="Blurs a user's avatar")
    async def blur_avatar_command(
        self, ctx: commands.Command, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "blur", target)

    @avatar_command_group.command(
        name="pixelate", description="Pixelates the user's profile picture."
    )
    async def pixelate_command(self, ctx, target: t.Optional[discord.Member]):
        await self.some_random_api(ctx, "pixelate", target)

    @avatar_command_group.command(
        name="simp",
        aliases=["simpcard"],
        description="Calls the mentioned a user a simp.",
    )
    async def simpcard_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "simp", target)

    @avatar_command_group.command(
        name="horny", description="Proves the mentioned user is a horny bastard."
    )
    async def horny_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "horny", target)

    @avatar_command_group.command(
        name="lolice", description="Call the loli police on a user."
    )
    async def lolice_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "horny", target)

    @avatar_command_group.group(name="filter")
    async def avatar_filter_command_group(self, ctx):
        pass

    @avatar_filter_command_group.command(
        name="gay-bg", description="Adds a gay border to a user's profile picture."
    )
    async def gay_background_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "gay-bg", target)

    @avatar_filter_command_group.command(
        name="pansexual-bg",
        description="Adds a pansexual border to a user's profile picture.",
    )
    async def pan_the_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "pan-bg", target)

    @avatar_filter_command_group.command(
        name="nonbinary-bg",
        description="Adds a nonbinary border to a user's profile picture.",
    )
    async def nonbinary_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "nonbinary-bg", target)

    @avatar_filter_command_group.command(
        name="lesbian-bg",
        description="Adds a lesbian border to a user's profile picture.",
    )
    async def lesbian_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "lesbian-bg", target)

    @avatar_filter_command_group.command(
        name="bisexual-bg",
        description="Adds a bisexual border to a user's profile picutre.",
    )
    async def bisexual_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "bisexual-bg", target)

    @avatar_filter_command_group.command(
        name="trans-bg", description="Adds a trans border to a user's profile picture."
    )
    async def transgender_avatar_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "trans-bg", target)

    @avatar_filter_command_group.command(
        name="circle", description="Crops the avatar to a circle"
    )
    async def crop_circle_avatar_command(self, ctx, target: t.Optional[discord.User]):
        await self.some_random_api(ctx, "circle", target)

    @avatar_command_group.command(name="ps2", description="Scene from Tonikawa")
    async def tonikawa_scene_avatar_command(
        self, ctx, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "ps2", target)

    @avatar_command_group.command(
        name="tweet", description="What has this user tweeted?"
    )
    async def tweet_avatar_command(self, ctx, target: discord.User, *, comment: str):
        print(target)
        url = f"https://some-random-api.com/canvas/misc/tweet"
        url += f"?avatar={quote(target.avatar.url)}"
        url += f"&comment={quote(comment)}"
        url += f"&displayname={quote(target.display_name)}"
        url += f"&username={quote(target.name)}"
        url += f"&replies={r.randint(-1, 1000)}"
        url += f"&likes={r.randint(-1, 100000)}"
        url += f"&retweets={r.randint(-1, 50000)}"
        url += f"&theme={r.choice(['light', 'dim', 'dark'])}"
        embed = discord.Embed(
            title=f"New tweet from {target.name}!",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: some-random-api.com/canvas/misc/tweet")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_command_group.command(
        name="youtube", aliases=["comment"], description="What has this user commented?"
    )
    async def youtube_comment_avatar_command(
        self, ctx, target: discord.User, *, comment: str
    ):
        url = f"https://some-random-api.com/canvas/youtube-comment"
        url += f"?avatar={quote(target.avatar.url)}"
        url += f"&comment={quote(comment)}"
        url += f"&username={quote(target.name)}"
        embed = discord.Embed(
            title=f"Brighter!", color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: some-random-api.com/canvas/misc/youtube-comment")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_filter_command_group.command(
        name="blue", description="Adds a blue filter to the pfp"
    )
    async def blue_filter_command(self, ctx, target: t.Optional[discord.User]):
        await self.some_random_api(ctx, "blue", target)

    @avatar_filter_command_group.command(
        name="blurple", description="Adds a blurple filter to the pfp"
    )
    async def blurple_filter_command(self, ctx, target: t.Optional[discord.User]):
        await self.some_random_api(ctx, "blurple", target)

    @avatar_filter_command_group.command(
        name="blurple2", description="Adds another blurple filter to the pfp"
    )
    async def blurple2_filter_command(self, ctx, target: t.Optional[discord.User]):
        await self.some_random_api(ctx, "blurple2", target)

    @avatar_filter_command_group.command(
        name="brightness", description="Adjusts the brightness of the pfp between 0-100"
    )
    async def brightness_filter_command(
        self, ctx, brightness: int, target: t.Optional[discord.User]
    ):
        target = target or ctx.author

        if 0 > brightness or brightness > 100:
            return await ctx.send("Brightness must be between 0-100!")

        url = f"https://some-random-api.com/canvas/filter/brightness"
        url += f"?avatar={quote(target.avatar.url)}"
        url += f"&brightness={quote(str(brightness))}"

        embed = discord.Embed(
            title=f"{target.name} commented",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: some-random-api.com/canvas/filter/brightness")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_filter_command_group.command(name="greyscale")
    async def greyscale_filter_command(self, ctx, target: t.Optional[discord.User]):
        await self.some_random_api(ctx, "greyscale", target)

    @avatar_filter_command_group.command(name="invertgreyscale")
    async def invertgreyscale_filter_command(
        self, ctx, target: t.Optional[discord.User]
    ):
        await self.some_random_api(ctx, "invertgreyscale", target)

    @avatar_filter_command_group.command(
        name="threshold", description="Threshold the pfp"
    )
    async def brightness_filter_command(
        self, ctx, threshold: int, target: t.Optional[discord.User]
    ):
        target = target or ctx.author

        if 0 > threshold or threshold > 100:
            return await ctx.send("Threshold must be between 0-100!")

        url = f"https://some-random-api.com/canvas/filter/threshold"
        url += f"?avatar={quote(target.avatar.url)}"
        url += f"&threshold={quote(str(threshold))}"

        embed = discord.Embed(
            title=f"Thresholded!", color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text="API: some-random-api.com/canvas/filter/threshold")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_filter_command_group.command(
        name="sepia", description="Adds a sepia filter"
    )
    async def sepia_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/sepia?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/sepia")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_filter_command_group.command(name="red", description="Adds a red filter")
    async def red_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/red?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/red")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_filter_command_group.command(
        name="green", description="Adds a green filter"
    )
    async def green_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/green?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/green")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_filter_command_group.command(
        name="invert", description="Inverts the colors"
    )
    async def invert_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/invert?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/invert")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_command_group.group(name="overlay")
    async def avatar_overlay_command_group(self, ctx):
        pass

    @avatar_overlay_command_group.command(
        name="glass", description="Adds a glass filter"
    )
    async def glass_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/glass?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/glas")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_overlay_command_group.command(
        name="wasted", description="Adds a GTA wasted filter"
    )
    async def wasted_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/wasted?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/wasted")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_overlay_command_group.command(
        name="passed", description="Adds a GTA mission passed filter"
    )
    async def passed_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/passed?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/passed")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_overlay_command_group.command(name="jail", description="Adds a jail filter")
    async def jail_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/jail?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/jail")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_overlay_command_group.command(
        name="comrade", description="Adds a soviet flag filter"
    )
    async def comrade_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/comrade?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/comrade")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @avatar_overlay_command_group.command(
        name="triggered", description="Adds a triggered filter"
    )
    async def triggered_overlay(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        if target is None:
            target = ctx.author
        url = f"https://some-random-api.com/canvas/triggered?avatar={target.avatar.replace(format='png', size=1024)}"
        embed = discord.Embed(
            title=target.display_name, color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f"API: some-random-api.com/canvas/triggered")
        embed.set_image(url=url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Avatar(bot))
