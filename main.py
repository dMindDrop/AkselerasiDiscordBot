import nextcord
from nextcord.ext import commands, tasks
import os
import json
import psycopg2.pool
import psycopg2
import logging
from datetime import datetime, timezone, timedelta


# Enable info logging
logging.basicConfig(level=logging.INFO)

# Initialize the connection pool
DATABASE_URL = os.environ['DATABASE_URL']
conn_pool = psycopg2.pool.SimpleConnectionPool(1, 88, DATABASE_URL, sslmode='require')

# Dictionary to store the last used time for each connection
connection_timestamps = {}

# Modified get_conn function
def get_conn():
    logging.info("Acquiring connection from pool.")
    conn = conn_pool.getconn()
    connection_timestamps[conn] = datetime.now()
    return conn

# Modified release_conn function
def release_conn(conn):
    logging.info("Releasing connection back to pool.")
    connection_timestamps[conn] = datetime.now()
    conn_pool.putconn(conn)

# Function to close inactive connections
def close_inactive_connections():
    now = datetime.now()
    for conn, timestamp in list(connection_timestamps.items()):  # Use list() to avoid RuntimeError due to dictionary size change
        if (now - timestamp).seconds > 300:  # 5 minutes
            conn.close()
            del connection_timestamps[conn]
            logging.info("Closed an inactive connection.")

# Periodic task to close inactive connections
@tasks.loop(seconds=60)
async def close_inactive_connections_task():
    close_inactive_connections()

# Function to get the number of used connections
def get_used_connections():
    return len(conn_pool._used)

# Function to close all connections and reset the pool
def close_all_connections():
    conn_pool.closeall()

# Define the intents
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# DatabaseConnectionManager class
class DatabaseConnectionManager:
    def __enter__(self):
        self.conn = get_conn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info("Releasing connection through DatabaseConnectionManager.")
        release_conn(self.conn)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Invalid command.')
    elif hasattr(error, 'original'):
        if isinstance(error.original, psycopg2.OperationalError):
            conn = get_conn()
            release_conn(conn)
            await ctx.send('Ups, we were out for a quick coffee. Please try again.')
        elif isinstance(error.original, psycopg2.pool.PoolError):
            await ctx.send('Terlalu banyak orang yang mencoba hal yang sama. Silakan coba lagi dalam 10 detik.')

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    close_inactive_connections_task.start()  # Start the task to close inactive connections

@bot.command(name='hello')
async def hello(ctx):
    await ctx.send('Hello! I am your Math Test Bot.')

@bot.command(name='check_pool')
async def check_pool(ctx):
    used_connections = get_used_connections()
    await ctx.send(f'Used connections: {used_connections}')

@bot.command(name='close_all_connections')
async def close_all_connections(ctx):
    logging.info("Attempting to close all connections in the pool.")
    conn_pool.closeall()
    logging.info("All connections in the pool have been closed.")
    await ctx.send('Closed all database connections.')

@tasks.loop(seconds=60)
async def temp_channel_cleanup():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name.endswith("-attendance") or channel.name.endswith("-bi") or channel.name.endswith("-triple") or channel.name.endswith("-authenticate"):
                last_message = await channel.history(limit=1).flatten()
                if not last_message:
                    await channel.delete(reason="No messages, assumed inactive")
                    continue
                
                last_message = last_message[0]
                time_since_last_message = (datetime.utcnow().replace(tzinfo=timezone.utc) - last_message.created_at).seconds
                if time_since_last_message > 300:
                    await channel.delete(reason="Inactivity timeout")

# Load the cogs
bot.load_extension('bi_weekly_test')
bot.load_extension('attendance')
bot.load_extension('triple')
bot.load_extension('my_class')
bot.load_extension('authenticate')

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))
