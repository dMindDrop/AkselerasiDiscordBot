import os
import nextcord
import psycopg2
import psycopg2.pool
import asyncio

from nextcord.ext import commands
from io import BytesIO  # Import BytesIO for handling byte streams

# Initialize the connection pool
DATABASE_URL = os.environ['DATABASE_URL']
conn_pool = psycopg2.pool.SimpleConnectionPool(1, 20, DATABASE_URL, sslmode='require')

# Function to get a connection from the pool
def get_conn():
    return conn_pool.getconn()

# Function to release a connection back to the pool
def release_conn(conn):
    conn_pool.putconn(conn)

# Create a new table for authentication data if it doesn't exist
def create_auth_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_data (
            discord_id TEXT PRIMARY KEY,
            pref_lang TEXT,
            first_name TEXT,
            last_name TEXT,
            group_code TEXT,
            staff_id TEXT UNIQUE
        );
    """)
    conn.commit()
    cur.close()
    release_conn(conn)





# Call the function to ensure the table exists
create_auth_table()





# Function to send QR code embedded message
async def send_qr_embed(temp_channel):
    conn = get_conn()  # Get a connection from the pool
    cur = conn.cursor()
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'student attendance';")
    row = cur.fetchone()
    cur.close()
    # Release the connection back to the pool
    release_conn(conn)

    if row:
        title, description, binary_data, link = row
        byte_stream = BytesIO(binary_data)
        file = nextcord.File(byte_stream, filename="qrcode.png")
        embed = nextcord.Embed(title=title, description=description, color=nextcord.Color.green())
        embed.add_field(name="Link", value=f"[Click here if you're on mobile]({link})", inline=False)
        embed.set_image(url="attachment://qrcode.png")
        return await temp_channel.send(embed=embed, file=file)  # Use temp_channel.send
    else:
        msg = await ctx.send("No QR code information found.")
        await msg.delete(delay=100)
        return None  # Return None if no QR code information is found



class Authenticate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def authenticate(self, ctx):
        channel_name = f"{ctx.author.name}-input-data-here"
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        await temp_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
        
        # Message to direct the user to the temporary channel
        await ctx.send(f"{ctx.author.mention}, please continue the authentication process in {temp_channel.mention}.")
        
        await temp_channel.send(f"{ctx.author.mention}, please continue the authentication process here.")
        await authenticate_member(temp_channel, ctx.author, self.bot)
        
        # Delete the temporary channel after 60 seconds
        await asyncio.sleep(60)
        await temp_channel.delete()



async def authenticate_member(temp_channel, member, bot):
         
    # Check if the user has the 'onboarding' role
    onboarding_role = nextcord.utils.get(member.guild.roles, name='onboarding')
    if onboarding_role not in member.roles:
        msg = await temp_channel.send("You must have the 'onboarding' role to use this command.")
        await msg.delete(delay=100)
        return

    # Create a cursor
    conn = get_conn()  # Get a connection from the pool
    cur = conn.cursor()

    # Collect user information
    # Collect user's preferred language
    valid_languages = ['EN', 'ID']
    while True:
        msg = await temp_channel.send('Please enter your preferred language (EN/ID):')
        await msg.delete(delay=100)
        pref_lang_msg = await bot.wait_for('message', check=lambda m: m.author == member)
        pref_lang = pref_lang_msg.content.upper()
        if pref_lang in valid_languages:
            break
        msg = await temp_channel.send('Invalid language. Please enter a valid language (EN/ID).')
        await msg.delete(delay=100)

    msg = await temp_channel.send('Please enter your first name:')
    await msg.delete(delay=100)
    first_name_msg = await bot.wait_for('message', check=lambda m: m.author == member)
    first_name = first_name_msg.content

    msg = await temp_channel.send('Please enter your last name:')
    await msg.delete(delay=100)
    last_name_msg = await bot.wait_for('message', check=lambda m: m.author == member)
    last_name = last_name_msg.content

    valid_group_codes = ['JGB1', 'JGB2', 'JGS1', 'JGS2', 'JKB1', 'JKB2', 'JKS1', 'JKS2', 'KGB1', 'KGB2', 'KGS1', 'KGS2', 'KKB1A', 'KKB1B', 'KKB1C', 'KKB1D', 'KKB1E', 'KKB2A', 'KKB2B', 'KKB2C', 'KKB2D', 'KKB2E', 'KKS1A', 'KKS1B', 'KKS1C', 'KKS1D', 'KKS1E', 'KKS2A', 'KKS2B', 'KKS2C', 'KKS2D', 'KKS2D', 'PILOT', 'CORE']
    while True:
        msg = await temp_channel.send('Please enter your group code:')
        await msg.delete(delay=100)
        group_code_msg = await bot.wait_for('message', check=lambda m: m.author == member)
        group_code = group_code_msg.content.upper()
        if group_code in valid_group_codes:
            break
        msg = await temp_channel.send('Invalid group code. Please enter a valid group code.')
        await msg.delete(delay=100)

    while True:
        msg = await temp_channel.send('Please enter your 8-digit Staff ID:')
        await msg.delete(delay=100)
        staff_id_msg = await bot.wait_for('message', check=lambda m: m.author == member)
        staff_id = staff_id_msg.content

        # Validate staff_id against ppl_classes table
        cur.execute("""
            SELECT * FROM ppl_classes WHERE teacher_id = %s OR principal_id = %s
        """, (staff_id, staff_id))
        valid_staff = cur.fetchone()
        if valid_staff and len(staff_id) == 8 and staff_id.isdigit():
            break
        msg = await temp_channel.send('Invalid Staff ID. It must be 8 digits and exist in the ppl_classes table.')
        await msg.delete(delay=100)

    # Confirm collected information
    confirm_msg = f"Preferred Language: {pref_lang}\nFirst Name: {first_name}\nLast Name: {last_name}\nGroup Code: {group_code}\nStaff ID: {staff_id}\nIs this information correct? (yes/no)"
    msg = await temp_channel.send(confirm_msg)
    await msg.delete(delay=100)
    confirm_response = await bot.wait_for('message', check=lambda m: m.author == member)
    if confirm_response.content.lower() != 'yes':
        msg = await temp_channel.send('Starting the authentication process again.')
        await msg.delete(delay=100)
        return

    # Check if the user is already authenticated
    cur.execute("SELECT * FROM auth_data WHERE discord_id = %s", (str(member.id),))
    existing_user = cur.fetchone()

    # Insert or update the user information in the PostgreSQL database
    if existing_user:
        msg = await temp_channel.send('You are already authenticated. Do you want to modify your existing data? (yes/no)')
        await msg.delete(delay=100)
        proceed_response = await bot.wait_for('message', check=lambda m: m.author == member)
        if proceed_response.content.lower() != 'yes':
            msg = await temp_channel.send('Authentication process terminated.')
            await msg.delete(delay=100)
            return

        cur.execute("""
            UPDATE auth_data
            SET pref_lang = %s, first_name = %s, last_name = %s, group_code = %s, staff_id = %s
            WHERE discord_id = %s
        """, (pref_lang, first_name, last_name, group_code, staff_id, str(member.id)))
    else:
        cur.execute("""
            INSERT INTO auth_data (discord_id, pref_lang, first_name, last_name, group_code, staff_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(member.id), pref_lang, first_name, last_name, group_code, staff_id))

    # Commit the changes and close the cursor
    conn.commit()
    cur.close()
    # Release the connection back to the pool
    release_conn(conn)

    # Remove the 'onboarding' role from the user
    onboarding_role = nextcord.utils.get(member.guild.roles, name='onboarding')
    await member.remove_roles(onboarding_role)

# Assign the 'authenticated' role to the user based on their group code
    group_role = nextcord.utils.get(member.guild.roles, name=f'c{group_code}')
    if group_role:
        await member.add_roles(group_role)
    else:
        msg = await temp_channel.send(f"No role found for the group code {group_code}.")
        await msg.delete(delay=100)

# Assign the general 'c' role to the user
    general_role = nextcord.utils.get(member.guild.roles, name='c')
    if general_role:
        await member.add_roles(general_role)
    else:
        msg = await temp_channel.send("No general 'c' role found.")
        await msg.delete(delay=100)

    
    # Send a confirmation message
    msg = await temp_channel.send('You have been successfully authenticated.')
    await msg.delete(delay=100)

    # Display QR code
    qr_msg = await send_qr_embed(temp_channel)  # Pass temp_channel here
    if qr_msg:  # Check if qr_msg is not None
        await asyncio.sleep(45)  # Wait for 45 seconds
        await qr_msg.delete()  # Delete the QR code message
        


def setup(bot):
    bot.add_cog(Authenticate(bot))