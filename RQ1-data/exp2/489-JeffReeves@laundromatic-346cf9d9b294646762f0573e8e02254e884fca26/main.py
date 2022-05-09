#!/usr/bin/env python3
"""
purpose: Discord Bot that sends laundry status messages.
    Built for use with a Raspberry Pi +
        photoresistor (light sensor) attached via GPIO pins.

author: Jeff Reeves
"""

# TODO:
# - Create command to get User ID by name
#   - Improve add_user and remove_user commands to support names
# - Get GPIO pins working with light sensor


#==[ IMPORTS ]=============================================================================================================================

from pprint import pprint
import logging
import sys
import os
import traceback
import json
import base64
import argparse
import getpass
import discord
from discord.ext import commands


#==[ CONFIG ]==============================================================================================================================

# logging
formatter = logging.Formatter('[ %(asctime)-23s ][ %(name)-8s ][ %(levelname)-8s ][ %(funcName)-20s ] (%(filename)s:%(lineno)s) - %(message)s')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('laundromatic.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


#==[ MAIN ]================================================================================================================================

def main(args):

    # config
    # use arguments if available, else get from user input
    token    = args.token               or getpass.getpass('Token: ')
    channel  = args.channel             or 'laundromatic'
    prefix   = args.prefix              or '!'
    loglevel = args.loglevel            or logging.INFO
    watchers = args.watchers            or []
    users    = dict.fromkeys(watchers)  or {}

    # set log level
    logger.setLevel(loglevel)

    logger.debug(f'All arguments passed to script: {args}')
    logger.debug(f'token:    {token}')
    logger.debug(f'channel:  {channel}')
    logger.debug(f'prefix:   {prefix}')
    logger.debug(f'loglevel: {loglevel}')
    logger.debug(f'watchers: {watchers}')
    logger.debug(f'users:    {users}')

    # discord client
    # NOTE: intents are needed to get users by id, 
    #   this must be set in the Discord Dev Center:
    #       https://discord.com/developers/applications/ ->
    #       Application -> Bot -> SERVER MEMBERS INTENT (ON)
    intents         = discord.Intents.default()
    intents.members = True
    #client          = discord.Client(intents = intents)
    client          = commands.Bot(command_prefix = prefix,
                                   intents        = intents)


    # CUSTOM FUNCTIONS

    # sets user details for all users
    async def set_user_details(users):
        user = None # clear user
        logger.debug(f'users: {users}')
        for index, user_id in enumerate(users):
            logger.debug(f'user id: {user_id}')
            # if user has no data, fetch it
            if user_id in users:
                logger.debug(f'user id ({user_id}) in users: {users}')
                if not users[user_id]:
                    logger.debug(f'users[user_id]: {users[user_id]} (bool: {bool(users[user_id])}')
                    user = await client.fetch_user(user_id)
                    if(user):
                        logger.debug(f'user: {user}')
                        users[user_id] = user
                        #users.update({ user_id: user })
                    else:
                        logger.error(f'unable to acquire user by user_id: {user_id}')
                else:
                    logger.debug(f'user already set: {user}')
        return users

    # send DM to a single user
    async def send_dm(user, message = 'test message'):
        logger.debug(f'Sending DM to: {user}')
        logger.debug(f'Message: {message}')
        await user.send(message)
        return

    # send DMs to many users
    async def send_dms(users, message = 'test message'):
        logger.debug('Sending DMs to all users')
        for index, user_id in enumerate(users):
            await send_dm(users[user_id], message)
        return

    # send message to specific channel
    async def send_channel_message(name = channel, message = 'test message'):
        logger.debug(f'channel name: {name}')
        channel_obj = discord.utils.get(client.get_all_channels(), name = name)
        if channel_obj:
            logger.debug(f'channel:    {channel_obj}')
            logger.debug(f'channel.id: {channel_obj.id}')
            #channel = client.get_channel(channel.id)
            logger.info(f'Sending message to #{channel_obj}: {message}')
            await channel_obj.send(message)
        return

    # send list of current users
    async def message_current_users(ctx, user_message = ''):
        current_users = ''
        nonlocal users
        if users:
            logger.info(f'Current Users:\n{users}')
            current_users = f'\nWatch List:\n```properties\n'
            for index, user_id in enumerate(users):
                current_users += f'{users[user_id].name} {users[user_id].id}\n'
            current_users += f'```'
        else:
            logger.info(f'No current users watching')
            current_users = f'\nNo current users watching'

        if user_message:
            user_message += '\n'

        if current_users:
            complete_message = user_message + current_users
            logger.info(f'complete_message: {complete_message}')
            await ctx.send(complete_message)

            # if command was received on a DM, also send output to a channel
            if ctx.message.channel.type == discord.ChannelType.private:
                logger.debug(f'Sending message of current_users:\n{current_users}')
                await send_channel_message(message = complete_message)

        return


    # COMMANDS

    # get user ID by username
    @client.command(name = 'id', aliases = ['get-id', 'user-id', 'uid'])
    async def get_id_by_username(ctx, *username):

        # if no username was passed as an argument, 
        #   assume the user passed their own username
        if not username:
            logger.debug('No argument passed to command')
            logger.debug(f'Using author {ctx.author.name} as argument')
            message = f'`{ctx.author.name}`\'s user ID is:\n`{str(user_id)}`'
            await ctx.send(message)
            return

        logger.info(f'Attempting to find user ID for: {username}')

        # get a member that matches the username, from all members of the guild
        member = discord.utils.get(client.get_all_members(), name = username)

        if member:
            logger.debug(f'member:   {member}')
            logger.info(f'member.id: {member.id}')
            message = f'`{username}`\'s user ID is:\n`{str(member.id)}`'

        await ctx.send(message)
        return 


    # add user to watch list
    @client.command(name = 'watch', aliases = ['subscribe'])
    async def add_user_to_watchers(ctx, *user_ids):

        # if no user IDs were passed as arguments, 
        #   assume the user passed their own user ID
        if not user_ids:
            logger.debug('No arguments passed to command')
            logger.debug(f'Using author ID {ctx.author.id} as argument')
            user_ids = [ str(ctx.author.id) ]

        logger.debug(f'user_ids: {user_ids}')

        # include nonlocal users 
        nonlocal users
        logger.debug(f'nonlocal users: {users}')

        user_message = ''
        # iterate over all user IDs
        for index, user_id in enumerate(user_ids):

            # if an argument wasn't numeric, skip it
            if not user_id.isnumeric():
                logger.warning(f'The arguments are not numeric ({user_id}). Skipping...')
                continue

            # if the user ID is not in the users dict, 
            #   1. add the user ID as a new key
            #   2. fetch user details
            #   3. DM the user to let them know they've been added

            if user_id not in users:
                logger.info(f'User ID {user_id} not in users list')
                users[user_id] = None
                logger.debug(f'Users: {users}')
                # TODO:
                # - improve time complexity with setting user details
                users = await set_user_details(users)
                #user_message  = f'Added `{users[user_id].name}#{users[user_id].discriminator}`'
                #user_message += f' (||`{users[user_id].id}`||) to the watch list'
                user_message  = f'Added `{users[user_id].name}` to the watch list'
                add_message   = f'You have been added to the watch list'
                if users[user_id].id != ctx.author.id:
                    #user_message += f'\n- requested by `{ctx.author}` (||`{ctx.author.id}`||)'
                    user_message += f'\n(requested by `{ctx.author.name}`)'
                    add_message  += f' by `{ctx.author.name}`'
                await send_dm(users[user_id], message = add_message)
            else:
                #user_message =  f'`{users[user_id].name}#{users[user_id].discriminator}`'
                #user_message += f' (||`{users[user_id].id}`||) is already on the watch list'
                user_message =  f'`{users[user_id].name} is already on the watch list'

            logger.info(user_message)

        await message_current_users(ctx, user_message)
        return

    # # handle errors on adding users
    # @add_user_to_watchers.error
    # async def add_user_to_watchers_error(ctx, error):
    #     logger.error(f'{error}')
    #     if isinstance(error, commands.BadArgument):
    #         await ctx.send('[ERROR] Invalid user ID(s)')
    #     return

    # remove user from watch list
    @client.command(name = 'stop', aliases = ['remove', 'unsubscribe', 'unwatch'])
    async def remove_user_from_watchers(ctx, *user_ids):

        # if no user IDs were passed as arguments, 
        #   assume the user passed their own user ID
        if not user_ids:
            logger.debug('No arguments passed to command')
            logger.debug(f'Using author ID {ctx.author.id} as argument')
            user_ids = [ str(ctx.author.id) ]

        logger.debug(f'user_ids: {user_ids}')

        # include nonlocal users
        nonlocal users
        logger.debug(f'nonlocal users: {users}')

        user_message = ''
        # iterate over all user IDs
        for index, user_id in enumerate(user_ids):

            # if an argument wasn't numeric, skip it
            if not user_id.isnumeric():
                logger.warning(f'The arguments are not numeric ({user_id}). Skipping...')
                continue

            # if the user ID is in the users dict: 
            #   1. message the user they are being removed from watch list
            #   2. delete the key from the users dict
            #   3. send a confirmation message the user was removed
            if user_id in users:
                #user_message   = f'Removed `{users[user_id].name}#{users[user_id].discriminator}`'
                #user_message  += f' (||`{users[user_id].id}`||) from the watch list'
                user_message   = f'Removed `{users[user_id].name}` from the watch list'
                remove_message = f'You have been removed from the watch list'
                if users[user_id].id != ctx.author.id:
                    #user_message   += f'\n- requested by `{ctx.author}` (||`{ctx.author.id}`||)'
                    user_message += f'\n(requested by `{ctx.author.name}`)'
                    remove_message += f' by `{ctx.author.name}`'
                await send_dm(users[user_id], message = remove_message)
                del users[user_id]
            else:
                user_message =  f'User (||`{user_id}`||) is not on the watch list'
                
            logger.info(user_message)

        await message_current_users(ctx, user_message)
        return

    # send a DM to all watchers
    @client.command(name = 'broadcast', aliases = ['dm'])
    async def send_dm_to_all_watchers(ctx, message = 'test DM to all watchers'):
        nonlocal users
        await send_dms(users, message)
        return

    # READY
    @client.event
    async def on_ready():

        # set an online message, log it, and send it to the management channel
        online_message = f'{client.user.name} is online and watching laundry'
        logger.info(online_message)
        await send_channel_message(channel, message = online_message)

        # if users are present, 
        #   set their user details and send them all a message too
        nonlocal users
        logger.debug(f'nonlocal users: {users}')
        if users:
            users = await set_user_details(users)
            await send_dms(users, message = online_message)

        return


    # DISCONNECT
    @client.event
    async def on_disconnect():
        logger.warning(f'{client.user} disconnected from Discord')
        return


    # ERROR
    @client.event
    async def on_error(event, *args, **kwargs):
        message = args[0] # get the message object
        logger.error(f'Error Message: {message}')
        logger.error(traceback.format_exc())
        error_message  = f'{client.user} has encountered an error. ' 
        error_message += 'Check server log for details.'
        await send_dms(users, message = error_message)
        return


    # MESSAGE
    @client.event
    async def on_message(message):

        # if the message is from the bot, return
        if message.author == client.user:
            return

        # process commands (required when using the on_message event)
        await client.process_commands(message)

        # # check for command prefix
        # if message.content.startswith(prefix):

        #     # debugging
        #     logger.debug(f'message: {message}')
        #     logger.debug(f'message.author.id: {message.author.id}')
        #     logger.debug(f'client.user: {client.user}')
        #     logger.debug(f'message.channel: {message.channel}')
        #     logger.debug(f'message.channel.type: {message.channel.type}')
        #     logger.debug(f'message: {message}')

        #     # # general commands
        #     # if message.content.startswith(prefix + 'watch'):
        #     #     await message.channel.send('Adding you to watch')

        #     # if message.content.startswith(prefix + 'stop'):
        #     #     await message.channel.send('Hello!')

        #     # check if private message
        #     if message.channel.type == discord.ChannelType.private:
        #         logger.debug('Received a private message')

        #         # send PM to the author
        #         #await message.author.send('👀 I see you 👍')
        #         #user = await get_user_by_id(message.author.id)
        #         #await send_dm(user, message = '👀 I see you 👍')

        #         # call commands
        #         await client.process_commands(message)

        #     else:
        #         logger.debug(f'message.channel.name: {message.channel.name}')

        #         # check if in '#laundromatic' channel
        #         if message.channel.name == 'laundromatic':
        #             logger.debug('Message received in #laundromatic channel')
        #             # call commands
        #             await client.process_commands(message)

    if token:
        client.run(token)
    else:
        logger.error('No token provided')

    return


#==[ COMMAND LINE ]========================================================================================================================

if __name__ == "__main__":

    # important values
    token    = None # REQUIRED
    channel  = None # Defaults to '#laundromatic' in main()
    prefix   = None # Defaults to '!'  in main()   
    loglevel = None # Defaults to 'info' in main()
    watchers = []   # Optional - user IDs

    # the values get set from (in order):
    #   1. JSON config file
    #   2. environment variables
    #   3. arguments passed via command line
    #   4. prompts to the user - in main()
    #   5. using commands in a direct message (DM) or a desired channel


    # 1. JSON config file
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file) as json_config_file:
            config = json.load(json_config_file)
            if 'token' in config:
                token = config['token']

            if 'channel' in config:
                channel = config['channel']

            if 'prefix' in config:
                prefix = config['prefix']

            if 'loglevel' in config:
                loglevel = config['loglevel']

            if 'watchers' in config:
                if all(config['watchers']):
                    watchers = config['watchers']


    # 2. environment variables
    if not token:
        token    = os.environ.get('LAUNDROMATIC_TOKEN')

    if not channel:
        channel  = os.environ.get('LAUNDROMATIC_CHANNEL')

    if not prefix:
        prefix   = os.environ.get('LAUNDROMATIC_PREFIX')

    if not loglevel:
        loglevel = os.environ.get('LAUNDROMATIC_LOGLEVEL')

    if not watchers:
        watchers = os.environ.get('LAUNDROMATIC_WATCHERS')
        if watchers:
            watchers = watchers.split() # convert space separated string to list


    # 3. arguments on command line
    parser = argparse.ArgumentParser()

    # token
    required     = bool(not token)
    group_tokens = parser.add_mutually_exclusive_group(required = required)    

    def decode_base64_token(base64_token):
        return base64.b64decode(base64_token).decode('UTF-8')

    group_tokens.add_argument('-t',
                              '--token',
                              dest = 'token',
                              type = str,
                              help = 'Token')

    group_tokens.add_argument('-b',
                              '--base64_token',
                              dest = 'token',
                              type = decode_base64_token,
                              help = 'Token (base64)')
    # channel
    parser.add_argument('-c',
                        '--channel',
                        dest = 'channel',
                        type = str,
                        help = 'Channel Name for management')

    # prefix
    parser.add_argument('-p',
                        '--prefix',
                        dest = 'prefix',
                        type = str,
                        help = 'Prefix for commands')

    # loglevels
    loglevels = {
        'debug'     : logging.DEBUG,
        'info'      : logging.INFO,
        'warning'   : logging.WARNING,
        'error'     : logging.ERROR,
        'critical'  : logging.CRITICAL,
    }

    def set_log_level(level):
        if level is None:
            level = 'info'
        if level not in loglevels:
            raise ValueError(f"Log Level must be one of: {' | '.join(loglevels.keys())}")
        return loglevels[level]

    parser.add_argument('-l',
                        '--loglevel',
                        dest = 'loglevel',
                        type = set_log_level,
                        help = f"Logging Level ({' | '.join(loglevels.keys())})")

    # watchers
    group_watchers = parser.add_mutually_exclusive_group(required = False)
    
    group_watchers.add_argument('-w',
                                '--watcher',
                                dest    = 'watchers',
                                type    = str,
                                action  = 'append',
                                help    = 'User ID of Watcher (can be used multiple times)')

    group_watchers.add_argument('--watchers',
                                dest    = 'watchers',
                                type    = str,
                                nargs   = '+',
                                help    = 'User IDs for Watchers (space separated list)')


    # parse arguments
    args, unknown = parser.parse_known_args()

    # set args values, if passed to argparse
    #   or use values set by environment variable or config file
    #   if no values found, use the defaults set at the beginning
    args.token      = args.token    or token
    args.channel    = args.channel  or channel
    args.prefix     = args.prefix   or prefix
    args.loglevel   = args.loglevel or loglevel
    args.watchers   = args.watchers or watchers

    main(args)