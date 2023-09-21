import os
import nextcord
import psycopg2
import psycopg2.pool
import asyncio

from nextcord.ext import commands
from io import BytesIO  # Import BytesIO for handling byte streams
from main import get_conn, release_conn


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
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'Authenticate';")
    row = cur.fetchone()
    cur.close()
    # Release the connection back to the pool
    release_conn(conn)

    if row:
        title, description, binary_data, link = row
        byte_stream = BytesIO(binary_data)
        file = nextcord.File(byte_stream, filename="qrcode.png")
        embed = nextcord.Embed(title=title, description=description, color=nextcord.Color.green())
        embed.add_field(name="Link", value=f"[Klik di sini jika Anda menggunakan ponsel]({link})", inline=False)
        embed.set_image(url="attachment://qrcode.png")
        return await temp_channel.send(embed=embed, file=file)  # Use temp_channel.send
    else:
        msg = await ctx.send("No QR code information found.")
        await msg.delete(delay=300)
        return None  # Return None if no QR code information is found



class Authenticate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='autentikasi')
    async def authenticate(self, ctx):
        channel_name = f"{ctx.author.name}-authenticate"
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        await temp_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
        
        # Message to direct the user to the temporary channel
        await ctx.send(f"{ctx.author.mention}, Silahkan lanjutkan proses otentikasi di {temp_channel.mention}.")
        
        await temp_channel.send(f"{ctx.author.mention}, Silahkan lanjutkan proses verifikasi di sini.")
        await authenticate_member(temp_channel, ctx.author, self.bot)
        
        # Delete the temporary channel after 60 seconds
        await asyncio.sleep(60)
        await temp_channel.delete()



async def authenticate_member(temp_channel, member, bot):
         
    # Check if the user has the 'onboarding' role
    onboarding_role = nextcord.utils.get(member.guild.roles, name='onboarding')
    if onboarding_role not in member.roles:
        msg = await temp_channel.send("Anda harus memiliki peran 'onboarding' untuk menggunakan perintah ini.")
        await msg.delete(delay=300)
        return

    # Create a cursor
    conn = get_conn()  # Get a connection from the pool
    cur = conn.cursor()

    # Collect user information
    # Collect user's preferred language
    valid_languages = ['EN', 'ID']
    while True:
        msg = await temp_channel.send('Silakan masukkan bahasa yang Anda sukai (ID) - Please enter your preferred language (EN)')
        await msg.delete(delay=300)
        pref_lang_msg = await bot.wait_for('message', check=lambda m: m.author == member)
        pref_lang = pref_lang_msg.content.upper()
        if pref_lang in valid_languages:
            break
        msg = await temp_channel.send('Invalid language. Please enter a valid language (EN)Masukkan bahasa yang Anda sukai (ID).')
        await msg.delete(delay=300)

    msg = await temp_channel.send('Nama Depan:')
    await msg.delete(delay=300)
    first_name_msg = await bot.wait_for('message', check=lambda m: m.author == member)
    first_name = first_name_msg.content

    msg = await temp_channel.send('Nama Belakang:')
    await msg.delete(delay=300)
    last_name_msg = await bot.wait_for('message', check=lambda m: m.author == member)
    last_name = last_name_msg.content

    valid_group_codes = ['JGB1', 'JKB1','KGS2', 'KKS2', 'KGS1', 'KKS1', 'PILOT', 'CORE']
    while True:
        msg = await temp_channel.send('Masukkan kode kelompok Anda:')
        await msg.delete(delay=300)
        group_code_msg = await bot.wait_for('message', check=lambda m: m.author == member)
        group_code = group_code_msg.content.upper()
        if group_code in valid_group_codes:
            break
        msg = await temp_channel.send('Kode grup tidak valid. Silakan masukkan kode grup yang benar.')
        await msg.delete(delay=300)

    while True:
        msg = await temp_channel.send('Masukkan ID karyawan 8-digit Anda:')
        await msg.delete(delay=300)
        staff_id_msg = await bot.wait_for('message', check=lambda m: m.author == member)
        staff_id = staff_id_msg.content

        # Validate staff_id against ppl_classes table
        cur.execute("""
            SELECT * FROM ppl_classes WHERE teacher_id = %s OR principal_id = %s
        """, (staff_id, staff_id))
        valid_staff = cur.fetchone()
        if valid_staff and len(staff_id) == 8 and staff_id.isdigit():
            break
        msg = await temp_channel.send('ID Staf tidak valid. Harus 8 digit dan ada dalam daftar kepala sekolah dan guru.')
        await msg.delete(delay=300)

    # Confirm collected information
    confirm_msg = f"Preferred Language: {pref_lang}\nNama Depan: {first_name}\nNama Belakang: {last_name}\nKode Grup: {group_code}\nID Staf: {staff_id}\nApakah informasi ini akurat? (yes/no)"
    msg = await temp_channel.send(confirm_msg)
    await msg.delete(delay=300)
    confirm_response = await bot.wait_for('message', check=lambda m: m.author == member)
    if confirm_response.content.lower() != 'yes':
        msg = await temp_channel.send('Memulai kembali proses otentikasi.')
        await msg.delete(delay=300)
        return

    # Check if the user is already authenticated
    cur.execute("SELECT * FROM auth_data WHERE discord_id = %s", (str(member.id),))
    existing_user = cur.fetchone()

    # Insert or update the user information in the PostgreSQL database
    if existing_user:
        msg = await temp_channel.send('Anda sudah terverifikasi. Apakah Anda ingin mengubah data yang ada? (yes/no)')
        await msg.delete(delay=300)
        proceed_response = await bot.wait_for('message', check=lambda m: m.author == member)
        if proceed_response.content.lower() != 'yes':
            msg = await temp_channel.send('Otentikasi dibatalkan.')
            await msg.delete(delay=300)
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
        await msg.delete(delay=300)

# Assign the general 'c' role to the user
    general_role = nextcord.utils.get(member.guild.roles, name='c')
    if general_role:
        await member.add_roles(general_role)
    else:
        msg = await temp_channel.send("No general 'c' role found.")
        await msg.delete(delay=300)

    
    # Send a confirmation message
    msg = await temp_channel.send('Anda telah berhasil diverifikasi.')
    await msg.delete(delay=300)

    # Display QR code
    qr_msg = await send_qr_embed(temp_channel)  # Pass temp_channel here
    if qr_msg:  # Check if qr_msg is not None
        await asyncio.sleep(45)  # Wait for 45 seconds
        await qr_msg.delete()  # Delete the QR code message
        


def setup(bot):
    bot.add_cog(Authenticate(bot))