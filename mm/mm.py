import argparse
import itertools
from random import choice

import discord
from redbot.core import Config
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
import asyncio

BOT_COMMANDER_ROLES = ["Bot Commander", "High-Elder"]


def grouper(n, iterable, fillvalue=None):
    """Helper function to split lists.

    Example:
    grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return (
        [e for e in t if e is not None]
        for t in itertools.zip_longest(*args))


class MemberManagement(commands.Cog):
    """Member Management plugin for Red Discord bot."""

    def __init__(self, bot: Red):
        """Init."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=209287691722817536, force_registration=True)
        default_global = {}
        default_guild = {}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    def parser(self):
        """Process MM arguments."""
        # Process arguments
        parser = argparse.ArgumentParser(prog='[p]mm')
        # parser.add_argument('key')
        parser.add_argument(
            'roles',
            nargs='*',
            default='_',
            help='Include roles')
        parser.add_argument(
            '-x', '--exclude',
            nargs='+',
            help='Exclude roles')
        parser.add_argument(
            '-o', '--output',
            choices=['id', 'mention', 'mentiononly'],
            help='Output options')
        parser.add_argument(
            '-r1', '--onlyrole',
            action='store_true',
            help='Check members with exactly one role')
        parser.add_argument(
            '-e', '--everyone',
            action='store_true',
            help='Include everyone.')
        parser.add_argument(
            '-s', '--sort',
            choices=['join', 'alpha'],
            default='join',
            help='Sort options')
        parser.add_argument(
            '-r', '--result',
            choices=['embed', 'csv', 'list', 'none'],
            default='embed',
            help='How to display results')
        parser.add_argument(
            '-m', '--macro',
            help='Macro name. Create using [p]mmset')
        return parser

    @commands.guild_only()
    @commands.command()
    @commands.has_any_role(*BOT_COMMANDER_ROLES)
    async def mm(self, ctx, *args):
        """Member management by roles.

        !mm [-h] [-x EXCLUDE [EXCLUDE ...]]
             [-o {id,mention,mentiononly}] [-r1] [-e] [-s {join,alpha}]
             [-r {embed,csv,list,none}] [-m MACRO]
             [roles [roles ...]]

        Find members with roles: Member, Elder
        !mm Member Elder

        Find members with roles: Member, Elder but not: Heist, CoC
        !mm Member Elder -exclude Heist CoC
        !mm Member Elder -x Heist CoC

        Output ID
        !mm Alpha Elder --output id
        !mm Alpha Elder -o id

        Optional arguments
        --exclude, -x
            Exclude list of roles
        --output, -o {id, mention, meniononly}
            id: Append list of user ids in the result.
            mention: Append list of user mentions in the result.
            mentiononly: Append list of user mentions only.
        --sort, s {join, alpha}
            join (default): Sort by date joined.
            alpha: Sort alphabetically
        --result, -r {embed, csv, list, none}
            Result display options
            embed (default): Display as Discord Embed.
            csv: Display as comma-separated values.
            list: Display as a list.
            none: Do not display results (show only count + output specified.
        --everyone
            Include everyone. Useful for finding members without specific roles.
        """
        parser = self.parser()
        try:
            pargs = parser.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return

        option_output_mentions = (pargs.output == 'mention')
        option_output_id = (pargs.output == 'id')
        option_output_mentions_only = (pargs.output == 'mentiononly')
        option_everyone = pargs.everyone or 'everyone' in pargs.roles
        option_sort_alpha = (pargs.sort == 'alpha')
        option_csv = (pargs.result == 'csv')
        option_list = (pargs.result == 'list')
        option_none = (pargs.result == 'none')
        option_only_role = pargs.onlyrole

        guild = ctx.message.guild
        guild_roles_names = [r.name.lower() for r in guild.roles]
        plus = set([r.lower() for r in pargs.roles if r.lower() in guild_roles_names])
        minus = set()
        if pargs.exclude is not None:
            minus = set([r.lower() for r in pargs.exclude if r.lower() in guild_roles_names])

        out = ["**Member Management**"]

        # Used for output only, so it won’t mention everyone in chat
        plus_out = plus.copy()

        if option_everyone:
            plus.add('@everyone')
            plus_out.add('everyone')

        help_str = (
            'Syntax Error: You must include at '
            'least one role to display results.')

        if len(plus) < 1:
            out.append(help_str)
        else:
            out.append("Listing members who have these roles: {}".format(
                ', '.join(plus_out)))
        if len(minus):
            out.append("but not these roles: {}".format(
                ', '.join(minus)))

        await ctx.send('\n'.join(out))

        # only output if argument is supplied
        if len(plus):
            # include roles with '+' flag
            # exclude roles with '-' flag
            out_members = set()
            for m in guild.members:
                roles = set([r.name.lower() for r in m.roles])
                if option_everyone:
                    roles.add('@everyone')
                exclude = len(roles & minus)
                if not exclude and roles >= plus:
                    out_members.add(m)

            # only role
            if option_only_role:
                out_members = [m for m in out_members if len(m.roles) == 2]

            suffix = 's' if len(out_members) > 1 else ''
            await ctx.send("**Found {} member{}.**".format(
                len(out_members), suffix))

            # sort join
            out_members = list(out_members)
            out_members.sort(key=lambda x: x.joined_at)

            # sort alpha
            if option_sort_alpha:
                out_members = list(out_members)
                out_members.sort(key=lambda x: x.display_name.lower())

            # embed output
            if not option_output_mentions_only:
                if option_none:
                    pass
                elif option_csv:
                    for page in pagify(
                            self.get_member_csv(out_members), shorten_by=50):
                        await ctx.send(page)
                elif option_list:
                    for page in pagify(
                            self.get_member_list(out_members), shorten_by=50):
                        await ctx.send(page)
                else:
                    for data in self.get_member_embeds(out_members, ctx.message.created_at):
                        try:
                            await ctx.send(embed=data)
                        except discord.HTTPException:
                            await ctx.send(
                                "I need the `Embed links` permission "
                                "to send this")

            # Display a copy-and-pastable list
            if option_output_mentions | option_output_mentions_only:
                mention_list = [m.mention for m in out_members]
                await ctx.send(
                    "Copy and paste these in message to mention users listed:")

                out = ' '.join(mention_list)
                for page in pagify(out, shorten_by=24):
                    await ctx.send(box(page))

            # Display a copy-and-pastable list of ids
            if option_output_id:
                id_list = [str(m.id) for m in out_members]
                await ctx.send(
                    "Copy and paste these in message to mention users listed:")
                out = ' '.join(id_list)
                for page in pagify(out, shorten_by=24):
                    await ctx.send(box(page))

    @staticmethod
    def get_member_csv(members):
        """Return members as a list."""
        names = [m.display_name for m in members]
        return ', '.join(names)

    @staticmethod
    def get_member_list(members):
        """Return members as a list."""
        out = []
        for m in members:
            out.append('+ {}'.format(m.display_name))
        return '\n'.join(out)

    @staticmethod
    def get_member_embeds(members, timestamp):
        """Discord embed of data display."""
        color = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        color = int(color, 16)
        embeds = []

        # split embed output to multiples of 25
        # because embed only supports 25 max fields
        out_members_group = grouper(25, members)

        for out_members_list in out_members_group:
            data = discord.Embed(
                color=discord.Colour(value=color))
            for m in out_members_list:
                value = []
                roles = [r.name for r in m.roles if r.name != "@everyone"]
                value.append(', '.join(roles))

                name = m.display_name
                since_joined = (timestamp - m.joined_at).days

                data.add_field(
                    name=str(name),
                    value=str(
                        ''.join(value) +
                        '\n{} days ago'.format(
                            since_joined)))
            embeds.append(data)
        return embeds

    def get_guild_roles(self, guild, *role_names):
        """Return list of guild roles object by name."""
        if guild is None:
            return []
        if len(role_names):
            roles_lower = [r.lower() for r in role_names]
            roles = [
                r for r in guild.roles if r.name.lower() in roles_lower
            ]
        else:
            roles = guild.roles
        return roles

    @commands.guild_only()
    @commands.command()
    async def listroles(self, ctx, *roles):
        """List all the roles on the guild."""
        guild = ctx.message.guild
        if guild is None:
            return
        out = []
        out.append("__List of roles on {}__".format(guild.name))
        roles_to_list = self.get_guild_roles(guild, *roles)

        out_roles = {}
        for role in roles_to_list:
            out_roles[role.id] = {'role': role, 'count': 0}
        for member in guild.members:
            for role in member.roles:
                if role in roles_to_list:
                    out_roles[role.id]['count'] += 1
        for role in guild.roles:
            if role in roles_to_list:
                out.append(
                    "**{}** ({} members)".format(
                        role.name, out_roles[role.id]['count']))
        for page in pagify("\n".join(out), shorten_by=12):
            await ctx.send(page)

    @commands.guild_only()
    @commands.command()
    async def listrolecolors(self, ctx, *roles):
        """List role colors on the guild."""
        guild = ctx.message.guild
        role_objs = self.get_guild_roles(guild, *roles)
        out = []
        for role in guild.roles:
            if role in role_objs:
                rgb = role.color.to_rgb()
                out.append('**{name}**: {color_rgb}, {color_hex}'.format(
                    name=role.name,
                    color_rgb=rgb,
                    color_hex='#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                ))
        for page in pagify("\n".join(out), shorten_by=12):
            await ctx.send(page)

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def changerole(self, ctx, member: discord.Member = None, *roles: str):
        """Change roles of a user.

        Example: !changerole SML +Delta "-Foxtrot Lead" "+Delta Lead"

        Multi-word roles must be surrounded by quotes.
        Operators are used as prefix:
        + for role addition
        - for role removal
        """
        guild = ctx.message.guild
        author = ctx.message.author
        if member is None:
            await ctx.send("You must specify a member")
            return
        elif roles is None or not roles:
            await ctx.send("You must specify a role.")
            return

        guild_role_names = [r.name for r in guild.roles]
        role_args = []
        flags = ['+', '-']
        for role in roles:
            has_flag = role[0] in flags
            flag = role[0] if has_flag else '+'
            name = role[1:] if has_flag else role

            if name.lower() in [r.lower() for r in guild_role_names]:
                role_args.append({'flag': flag, 'name': name})

        plus = [r['name'].lower() for r in role_args if r['flag'] == '+']
        minus = [r['name'].lower() for r in role_args if r['flag'] == '-']
        # disallowed_roles = [r.lower() for r in DISALLOWED_ROLES]

        for role in guild.roles:
            role_in_minus = role.name.lower() in minus
            role_in_plus = role.name.lower() in plus
            role_in_either = role_in_minus or role_in_plus

            if role_in_either:
                # respect role hiearchy
                if role.position >= author.top_role.position:
                    await ctx.send(
                        "{} does not have permission to edit {}.".format(
                            author.display_name, role.name))
                else:
                    try:
                        if role_in_minus:
                            await member.remove_roles(role)
                        if role_in_plus:
                            await member.add_roles(role)
                    except discord.Forbidden:
                        await ctx.send(
                            "{} does not have permission to edit {}’s roles.".format(
                                author.display_name, member.display_name))
                        continue
                    except discord.HTTPException:
                        if role_in_minus:
                            await ctx.send(
                                "Failed to remove {}.").format(role.name)
                            continue
                        if role_in_plus:
                            await ctx.send(
                                "failed to add {}.").format(role.name)
                            continue
                    else:
                        if role_in_minus:
                            await ctx.send(
                                "Removed {} from {}".format(
                                    role.name, member.display_name))
                        if role_in_plus:
                            await ctx.send(
                                "Added {} for {}".format(
                                    role.name, member.display_name))

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def searchmember(self, ctx, name=None):
        """Search member on guild by name."""
        if name is None:
            await ctx.send_help()
            return
        if name.startswith("<@"):
            return await ctx.send("Use a plain text name instead of a mention.")
        guild = ctx.message.guild
        results = []
        for member in guild.members:
            for member_name in [member.display_name, member.name]:
                if name.lower() in member_name.lower():
                    results.append(member)
                    break

        if not len(results):
            await ctx.send("Cannot find any users with that name.")
            return

        await ctx.send('Found {} members.'.format(len(results)))

        for member in results:
            role_list = (', '.join([r.name for r in member.roles])).replace("@everyone, ", "")
            out = [
                '---------------------',
                'Display Name: {}'.format(member.display_name),
                'Username: {}'.format(str(member)),
                'Roles: {}'.format(role_list),
                'User ID: {}'.format(member.id)
            ]
            await ctx.send('\n'.join(out))

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def addrole2role(self, ctx, with_role_name, to_add_role_name):
        """Add a role to users with a specific role."""
        guild = ctx.message.guild
        with_role = discord.utils.get(guild.roles, name=with_role_name)
        to_add_role = discord.utils.get(guild.roles, name=to_add_role_name)
        if with_role is None:
            await ctx.send("Cannot find the role **{}** on this guild.".format(with_role_name))
            return
        if to_add_role is None:
            await ctx.send("Cannot find the role **{}** on this guild.".format(to_add_role_name))
            return

        guild_members = [member for member in guild.members]
        for member in guild_members:
            if with_role in member.roles:
                if to_add_role not in member.roles:
                    try:
                        await ctx.invoke(self.changerole, member, to_add_role_name)
                    except:
                        pass

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def multiaddrole(self, ctx, role, *members: discord.Member):
        """Add a role to multiple users.

        !multiaddrole rolename User1 User2 User3
        """
        for member in members:
            await ctx.invoke(self.changerole, member, role)

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def multiremoverole(self, ctx, role, *members: discord.Member):
        """Remove a role from multiple users.

        !multiremoverole rolename User1 User2 User3
        """
        role = '-{}'.format(role)
        for member in members:
            await ctx.invoke(self.changerole, member, role)

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def channelperm(self, ctx, member: discord.Member):
        """Return channels viewable by member."""
        author = ctx.message.author
        guild = ctx.message.guild
        if not member:
            member = author

        text_channels = [c for c in guild.channels if type(c) == discord.channel.TextChannel]
        text_channels = sorted(text_channels, key=lambda c: c.position)
        voice_channels = [c for c in guild.channels if type(c) == discord.channel.VoiceChannel]
        voice_channels = sorted(voice_channels, key=lambda c: c.position)

        out = []
        for c in text_channels:
            channel_perm = c.permissions_for(member)
            tests = ['read_messages', 'send_messages']
            perms = [t for t in tests if getattr(channel_perm, t)]
            if len(perms):
                out.append("{channel} {perms}".format(channel=c.mention, perms=', '.join(perms)))

        for c in voice_channels:
            channel_perm = c.permissions_for(member)
            tests = ['connect']
            perms = [t for t in tests if getattr(channel_perm, t)]
            if len(perms):
                out.append("{channel}: {perms}".format(channel=c.name, perms=', '.join(perms)))

        for page in pagify('\n'.join(out)):
            await ctx.send(page)


    async def remove_role(self, member, role, channel=None, reason=None):
        await member.remove_roles(
            role,
            reason=reason
        )
        if channel is not None:
            await channel.send(
                f"Removed {role} for {member}"
            )


    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def removerolefromall(self, ctx, role_name):
        """Remove a role from all members with the role."""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send("Role not found.")
            return
        guild = ctx.guild

        members = []
        for member in guild.members:
            if role in member.roles:
                members.append(member)
        if not members:
            await ctx.send("No members with that role found")
            return

        async with ctx.typing():
            tasks = [
                self.remove_role(member, role, channel=ctx.channel)
                for member in members
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for m, r in zip(members, results):
                if isinstance(r, Exception):
                    await ctx.send("Error removing role from {}".format(m))
            await ctx.send("Task completed.")