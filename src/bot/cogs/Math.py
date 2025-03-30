import datetime as dt
import math as m
import typing as t
import base64
import scipy

import pymep.realParser
from pymep.realParser import parse
from pymep.realParser import eval

import discord
from discord.ext import commands


class Math(commands.Cog):
    """Pretty much a fancy calculator on the bot :)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="hex",
        description="Translates an RGB value (0 to 255) to a hexadecimal value.",
    )
    async def rgb_to_hex_command(
        self, ctx: commands.Context, red: int, green: int, blue: int
    ):

        if abs(red) > 255 or abs(green) > 255 or abs(blue) > 255:
            return await ctx.send("Please choose a valid rgb value.")

        hexa = (red << 16) | (green << 8) | blue
        await ctx.send(f"{red}, {green}, {blue} to hex is 0x{hex(hexa)}")

    @commands.hybrid_command(
        name="rgb",
        description="Translates a hexadecimal value (0x000000 to 0xFFFFFF) to an RGB value.",
    )
    async def hex_to_rgb_command(self, ctx: commands.Context, hexa: str):
        hexa = hexa.replace("0x", "")
        if len(hexa) != 6:
            return await ctx.send("Please choose a valid hex value.")

        r = int(hexa[0:2], 16)
        g = int(hexa[2:4], 16)
        b = int(hexa[4:6], 16)
        await ctx.send(f"0x{hexa.upper()} to rgb is {r},{g},{b}")

    @commands.hybrid_command(
        name="inttohex",
        description="Takes a normal decimal integer and translates it to hexadecimal!",
    )
    async def int_to_hex(self, ctx, integer: int):
        await ctx.send(f"{integer} -> 0x{hex(integer)}")

    @int_to_hex.error
    async def int_to_hex_error(self, ctx, exc):
        if isinstance(exc, ValueError) or isinstance(exc, commands.BadArgument):
            await ctx.send(
                "Only integers allowed. No floating point (decimal) numbers!"
            )

    @commands.hybrid_command(
        name="hextoint",
        description="Takes a hexadecimal number and translates it to a ",
    )
    async def hex_to_int(self, ctx, hexadecimal):
        hexadecimal = hexadecimal.replace("0x", "")
        await ctx.send(f"0x{hexadecimal} -> {int(hexadecimal, 16)}")

    @commands.hybrid_command(
        name="inttob64",
        description="Translates a decimal number to its base64 counterpart.",
    )
    async def int_to_b64(self, ctx, num: int):
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")
        await ctx.send(f"{num} -> {base64.b64encode(num_bytes).decode('utf-8')}")

    @commands.hybrid_command(
        name="b64toint", description="Translates a base64 number to a decimal integer"
    )
    async def b64_to_int(self, ctx, b64):
        decoded = base64.b64decode(b64)
        await ctx.send(f"{b64} -> {int.from_bytes(decoded, byteorder='big')}")

    @commands.hybrid_command(
        name="hextob64",
        description="Translates a hexadecimal number to a base64 representation",
    )
    async def hex_to_b64(self, ctx, hexadecimal):
        hexadecimal = hexadecimal.replace("0x", "")
        integer = int(hexadecimal, 16)
        int_bytes = integer.to_bytes((integer.bit_length() + 7) // 8, byteorder="big")
        await ctx.send(f"0x{hexadecimal} -> {base64.b64encode(int_bytes).decode()}")

    @commands.hybrid_command(
        name="b64tohex", description="Translates a base64 number to a decimal integer"
    )
    async def b64_to_hex(self, ctx, b64):
        decoded = base64.b64decode(b64)
        integer = int.from_bytes(decoded, byteorder="big")
        await ctx.send(f"{b64} -> {hex(integer)}")

    @commands.hybrid_command(
        name="subtract", description="Returns the difference of two numbers"
    )
    async def subtract_command(self, ctx, num1, num2):
        await ctx.send(f"{num1} - {num2} = {num1-num2}")

    @commands.hybrid_command(name="addition", description="Returns the sum of two numbers")
    async def addition_command(self, ctx, num1, num2):
        await ctx.send(f"{num1} + {num2} = {num2+num1}")

    @commands.hybrid_command(name="multiply", description="Returns the product of two numbers")
    async def multiply_command(self, ctx, num1, num2):
        await ctx.send(f"{num1} * {num2} = {num1*num2}")

    @commands.hybrid_command(
        name="divide", description="Returns the the quotient of two numbers"
    )
    async def divide_command(self, ctx, num1, num2):
        await ctx.send(f"{num1} / {num2} = {num1/num2}")

    @commands.hybrid_command(
        name="exponent",
        aliases=["power", "pow"],
        description="Returns the power of two numbers",
    )
    async def exponent_command(self, ctx, base, exp):
        await ctx.send(f"{base}^{exp} = {pow(base, exp)}")

    @commands.hybrid_command(name="sqrt", description="Returns the square root of a number")
    async def sqrt_command(self, ctx, num: float):
        imaginary = ""
        if num < 0:
            imaginary = "i"
        await ctx.send(f"The square root of {num} is {imaginary}{m.sqrt(abs(num))}")

    @commands.hybrid_command(name="nth_root", description="Returns the nth root of a number")
    async def nth_root_command(self, ctx, num: float, n: int):
        imaginary = ""
        if num < 0 and n % 2 == 0:
            imaginary = "i"
        await ctx.send(f"The {n}th root of {num} is {imaginary}{pow(num, 1/n)}")

    @commands.hybrid_command(
        name="parse", description="A basic parser for arithmetic expressions."
    )
    async def parse_expression(self, ctx, *, expression: str):
        try:
            result = parse(expression)
        except pymep.realParser.CalculatorException:
            return await ctx.send(
                "I could not evaluate that expression! Did you send invalid syntax?"
            )
        await ctx.send(f"`{expression}` = {result:10.4f}")

    @commands.hybrid_command(
        name="eval",
        description="A basic evaluation statement for arithmetic expressions."
        " Usage: `M!eval x 2 x^2`",
    )
    async def evaluate_equation(self, ctx, var, val, *, equation):
        try:
            result = eval(f" {equation}", {var: val})
        except pymep.realParser.CalculatorException:
            return await ctx.send(
                "I could not evaluate that expression! Did you send invalid syntax?"
            )
        await ctx.send(f"`{equation}` where {var} is {val} = {result:.4f}")

    @commands.hybrid_command(
        name="sin", aliases=["sine"], description="Returns the sine of a number"
    )
    async def sin_command(self, ctx, n):
        if "pi" in n:
            num = n
            num = num[:-2]
            if not num:
                num = "1"
            num = float(num)
            res = m.sin(m.pi * num)
        else:
            res = m.sin(float(n))
        await ctx.send(f"sin({n}) = {res:.4f}")

    @commands.hybrid_command(
        name="cos", aliases=["cosine"], description="Returns the cosine of a number"
    )
    async def cos_command(self, ctx, n):
        if "pi" in n:
            num = n
            num = num[:-2]
            if not num:
                num = "1"
            num = float(num)
            res = m.cos(m.pi * num)
        else:
            res = m.cos(float(n))
        await ctx.send(f"cos({n}) = {res:.4f}")

    @commands.hybrid_command(
        name="tan", aliases=["tangent"], description="Returns the tangent of a number"
    )
    async def tan_command(self, ctx, n):
        if "pi" in n:
            num = n
            num = num[:-2]
            if not num:
                num = "1"
            num = float(num)
            res = m.tan(m.pi * num)
        else:
            res = m.tan(float(n))
        await ctx.send(f"tan({n}) = {res:.4f}")

    @commands.hybrid_command(
        name="asin",
        aliases=["arcsin", "inverse_sine"],
        description="Returns the inverse sine of a number",
    )
    async def arcsin_command(self, ctx, n):
        if "pi" in n:
            num = n
            pi = num[-2:]
            num = num[:-2]
            if not num:
                num = "1"
            num = float(num)
            if num > 1.0 or pi:
                await ctx.send(
                    "The Inverse Sine of numbers greater than 1.0 are undefined"
                )
                return
            res = m.asin(m.pi * num)
        else:
            if float(n) > 1.0:
                await ctx.send(
                    "The Inverse Cosine of numbers greater than 1.0 are undefined"
                )
                return
            res = m.asin(float(n))
        await ctx.send(f"asin({n}) = {res:.4f}")

    @commands.hybrid_command(
        name="acos",
        aliases=["arccos", "inverse_cosine"],
        description="Returns the inverse cosine of a number",
    )
    async def arccos_command(self, ctx, n):
        if "pi" in n:
            num = n
            pi = num[-2:]
            num = num[:-2]
            if not num:
                num = "1"
            num = float(num)
            if num > 1.0 or pi:
                await ctx.send(
                    "The Inverse Cosine of numbers greater than 1.0 are undefined"
                )
                return
            res = m.acos(m.pi * num)
        else:
            if float(n) > 1.0:
                await ctx.send(
                    "The Inverse Cosine of numbers greater than 1.0 are undefined"
                )
                return
            res = m.acos(float(n))
        await ctx.send(f"acos({n}) = {res:.4f}")

    @commands.hybrid_command(
        name="atan",
        aliases=["arctan", "inverse_tangent"],
        description="Returns the inverse tangent of a number",
    )
    async def arctan_command(self, ctx, n):
        if "pi" in n:
            num = n
            num = num[:-2]
            if not num:
                num = "1"
            num = float(num)
            res = m.atan(m.pi * num)
        else:
            res = m.atan(float(n))
        await ctx.send(f"atan({n}) = {res:.4f}")

    @commands.hybrid_command(
        name="factorial", description="Returns the factorial of any real number"
    )
    async def factorial_command(self, ctx, n):
        await ctx.send(f"{n}! = {scipy.special.gamma(float(n) + 1)}")


async def setup(bot):
    await bot.add_cog(Math(bot))
