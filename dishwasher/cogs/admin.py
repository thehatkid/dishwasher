import discord
from discord.ext import commands
from discord.ext.commands import Cog
import traceback
import inspect
import re
import datetime
import json
import config
import random
import asyncio
from helpers.checks import check_if_bot_manager


class Admin(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_eval_result = None
        self.previous_eval_code = None

    @commands.guild_only()
    @commands.check(check_if_bot_manager)
    @commands.command(name="exit", aliases=["quit", "bye"])
    async def _exit(self, ctx):
        """[O] Shuts down (or restarts) the bot."""
        await ctx.message.reply(
            content=random.choice(self.bot.config.death_messages), mention_author=False
        )
        await self.bot.close()

    @commands.guild_only()
    @commands.check(check_if_bot_manager)
    @commands.command()
    async def fetchdata(self, ctx):
        """[O] Returns data files."""
        data_files = [discord.File(fpath) for fpath in self.bot.wanted_jsons]
        await ctx.message.reply(
            content="Here's the current data files:",
            files=data_files,
            mention_author=False,
        )

    @commands.guild_only()
    @commands.check(check_if_bot_manager)
    @commands.command(name="eval")
    async def _eval(self, ctx, *, code: str):
        """[O] Evaluates some code."""
        try:
            code = code.strip("` ")

            env = {
                "bot": self.bot,
                "ctx": ctx,
                "message": ctx.message,
                "server": ctx.guild,
                "guild": ctx.guild,
                "channel": ctx.message.channel,
                "author": ctx.message.author,
                # modules
                "discord": discord,
                "commands": commands,
                "datetime": datetime,
                "json": json,
                "asyncio": asyncio,
                "random": random,
                # utilities
                "_get": discord.utils.get,
                "_find": discord.utils.find,
                # last result
                "_": self.last_eval_result,
                "_p": self.previous_eval_code,
            }
            env.update(globals())

            self.bot.log.info(f"Evaling {repr(code)}:")
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result

            if result is not None:
                self.last_eval_result = result

            self.previous_eval_code = code

            sliced_message = await self.bot.slice_message(
                repr(result), prefix="```", suffix="```"
            )
            for msg in sliced_message:
                await ctx.send(msg)
        except:
            sliced_message = await self.bot.slice_message(
                traceback.format_exc(), prefix="```", suffix="```"
            )
            for msg in sliced_message:
                await ctx.send(msg)

    async def cog_load_actions(self, cog_name):
        # Used for specific cog actions, tore out the verification cog since don't need it.
        pass

    @commands.guild_only()
    @commands.check(check_if_bot_manager)
    @commands.command()
    async def pull(self, ctx, auto=False):
        """[O] Performs a git pull."""
        tmp = await ctx.message.reply(content="Pulling...", mention_author=False)
        git_output = await self.bot.async_call_shell("git pull")
        allowed_mentions = discord.AllowedMentions(replied_user=False)
        await tmp.edit(
            content=f"Pull complete. Output: ```{git_output}```",
            allowed_mentions=allowed_mentions,
        )
        if auto:
            cogs_to_reload = re.findall(r"cogs/([a-z_]*).py[ ]*\|", git_output)
            for cog in cogs_to_reload:
                cog_name = "cogs." + cog
                if cog_name not in config.initial_cogs:
                    continue

                try:
                    await self.bot.unload_extension(cog_name)
                    await self.bot.load_extension(cog_name)
                    self.bot.log.info(f"Reloaded ext {cog}")
                    await ctx.message.reply(
                        content=f":white_check_mark: `{cog}` successfully reloaded."
                    )
                    await self.cog_load_actions(cog)
                except:
                    await ctx.message.reply(
                        content=f":x: Cog reloading failed, traceback: "
                        f"```\n{traceback.format_exc()}\n```"
                    )
                    return

    @commands.guild_only()
    @commands.check(check_if_bot_manager)
    @commands.command()
    async def load(self, ctx, ext: str):
        """[O] Loads a cog."""
        try:
            await self.bot.load_extension("cogs." + ext)
            await self.cog_load_actions(ext)
        except:
            await ctx.message.reply(
                content=f":x: Cog loading failed, traceback: "
                f"```\n{traceback.format_exc()}\n```"
            )
            return
        self.bot.log.info(f"Loaded ext {ext}")
        await ctx.message.reply(
            content=f":white_check_mark: `{ext}` successfully loaded."
        )

    @commands.guild_only()
    @commands.check(check_if_bot_manager)
    @commands.command()
    async def unload(self, ctx, ext: str):
        """[O] Unloads a cog."""
        await self.bot.unload_extension("cogs." + ext)
        self.bot.log.info(f"Unloaded ext {ext}")
        await ctx.message.reply(
            content=f":white_check_mark: `{ext}` successfully unloaded."
        )

    @commands.check(check_if_bot_manager)
    @commands.command()
    async def reload(self, ctx, ext="_"):
        """[O] Reloads a cog."""
        if ext == "_":
            ext = self.lastreload
        else:
            self.lastreload = ext

        try:
            await self.bot.unload_extension("cogs." + ext)
            await self.bot.load_extension("cogs." + ext)
            await self.cog_load_actions(ext)
        except:
            await ctx.message.reply(
                content=f":x: Cog reloading failed, traceback: "
                f"```\n{traceback.format_exc()}\n```"
            )
            return
        self.bot.log.info(f"Reloaded ext {ext}")
        await ctx.message.reply(
            content=f":white_check_mark: `{ext}` successfully reloaded."
        )


async def setup(bot):
    await bot.add_cog(Admin(bot))
