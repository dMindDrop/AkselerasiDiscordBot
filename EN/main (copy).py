import nextcord
from nextcord.ext import commands
import os
import json
import psycopg2.pool

# Create a connection pool
pool = psycopg2.pool.SimpleConnectionPool(0, 80, os.getenv('DATABASE_URL'))

# Define the intents
intents = nextcord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Invalid command.')
    else:
        await ctx.send(f'An error occurred: {error}')

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

@bot.command(name='hello')
async def hello(ctx):
    await ctx.send('Hello! I am your Math Test Bot.')

@bot.command(name='setsequence')
async def set_sequence(ctx, new_sequence: int):
    with open('config.json', 'r+') as f:
        config = json.load(f)
        config['current_sequence_number'] = new_sequence
        f.seek(0)
        json.dump(config, f)
        f.truncate()
    await ctx.send(f"Sequence number set to {new_sequence}.")

# Load the bi_weekly_test cog
bot.load_extension('bi_weekly_test')

# Load the attendance extension
bot.load_extension('attendance')

# Load the triple test extension
bot.load_extension('triple')

# Load the my_class extension
bot.load_extension('my_class')

bot.load_extension('authenticate')

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))

# Don't forget to put the connection back into the pool when you're done
# Commenting this out as 'conn' is not defined
# pool.putconn(conn)
