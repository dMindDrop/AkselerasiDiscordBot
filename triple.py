import os
import json
import psycopg2
import psycopg2.extras
import psycopg2.pool  # Import the pool module
import nextcord
from nextcord.ext import commands
from datetime import datetime
from io import BytesIO
from views import TripleInputView
import asyncio  # Import asyncio for asynchronous operations
from main import get_conn, release_conn  # Importing from main.py


# Create test_triple and ppl_current_topic tables if they don't exist
conn = get_conn()
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS test_triple (
    index SERIAL PRIMARY KEY,
    time_stamp TIMESTAMP,
    sequence INTEGER,
    student_ID TEXT,
    topic_based_on_result TEXT
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS ppl_current_topic (
    index SERIAL PRIMARY KEY,
    time_stamp TIMESTAMP,
    student_ID TEXT,
    current_topic TEXT,
    assessment_tool TEXT
);
''')

conn.commit()
cur.close()
release_conn(conn)

async def send_qr_embed_for_triple(ctx):
    conn = get_conn()  # Get a connection from the pool
    cur = conn.cursor()
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'Training';")
    row = cur.fetchone()
    cur.close()
    release_conn(conn)  # Release the connection back to the pool

    if row:
        title, description, binary_data, link = row
        byte_stream = BytesIO(binary_data)
        file = nextcord.File(byte_stream, filename="qrcode.png")
        embed = nextcord.Embed(title=title, description=description, color=nextcord.Color.green())
        embed.add_field(name="Link", value=f"[Click here if you're on mobile]({link})", inline=False)
        embed.set_image(url="attachment://qrcode.png")
        msg = await ctx.send(embed=embed, file=file)  # Changed here
        await msg.delete(delay=90)
    else:
        msg = await ctx.send("No QR code information found.")  # Changed here
        await msg.delete(delay=90)





class TripleTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='triple')
    async def mark_triple_test_command(self, ctx, sequence: int):
        channel_name = f"{ctx.author.name}-triple"
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        await temp_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
        
        await ctx.send(f"{ctx.author.mention}, Silakan lanjutkan proses triple test di {temp_channel.mention}.", delete_after=10)
        await temp_channel.send(f"{ctx.author.mention}, Silakan lanjutkan proses triple test di sini.")
        
        # Prompt for event date in the temporary channel
        event_date_msg = await temp_channel.send("Silakan masukkan tanggal acara dalam format dd-mm-yy:")
        def check(m):
            return m.channel == temp_channel and m.author == ctx.author
        event_date_response = await self.bot.wait_for('message', check=check)

        # Convert the entered date to datetime object
        try:
            event_date = datetime.strptime(event_date_response.content, '%d-%m-%y')
        except ValueError:
            await temp_channel.send("Format tanggal tidak valid. Silakan gunakan dd-mm-yy.")
            return

        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT staff_id FROM auth_data WHERE discord_id = %s", (str(ctx.author.id),))
        teacher_staff_id_row = cur.fetchone()
        teacher_staff_id = teacher_staff_id_row['staff_id'] if teacher_staff_id_row else None

        cur.execute("SELECT class_id FROM ppl_classes WHERE teacher_id = %s", (teacher_staff_id,))
        class_id_row = cur.fetchone()
        class_id = class_id_row['class_id'] if class_id_row else None

        cur.close()
        release_conn(conn)

        if teacher_staff_id and class_id:
            await mark_triple_test(temp_channel, teacher_staff_id, class_id, sequence, event_date)  # Pass event_date here
        else:
            await temp_channel.send("Guru atau kelas tidak ditemukan.")
        
        await asyncio.sleep(90)
        await temp_channel.delete()






async def mark_triple_test(ctx, teacher_staff_id, class_id, sequence, event_date):
    conn = get_conn()  # Get a connection from the pool
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    msg = await ctx.send(f"Saat ini memasukkan data untuk sekuens {sequence}.")
    await msg.delete(delay=90)

    cur.execute("SELECT student_id, student_name FROM ppl_classes WHERE class_id = %s AND active = 'yes'", (class_id,))
    students = cur.fetchall()

    for student in students:
        student_id = student['student_id']
        student_name = student['student_name']

        view = TripleInputView(ctx, student_name, student_id)
        msg = await ctx.send(f"Mark triple test for {student_name} (ID: {student_id}):", view=view)
        await msg.delete(delay=90)
        await view.wait()

        topic_based_on_result = view.topic

        cur.execute("INSERT INTO test_triple (time_stamp, event_date, sequence, student_ID, topic_based_on_result) VALUES (%s, %s, %s, %s, %s)",
                (datetime.now(), event_date, sequence, student_id, topic_based_on_result))  # Add event_date here
        conn.commit()

        cur.execute("INSERT INTO ppl_current_topic (time_stamp, student_ID, current_topic, assessment_tool) VALUES (%s, %s, %s, %s)",
                (datetime.now(), student_id, topic_based_on_result, 'triple'))  # No event_date here
        conn.commit()

    msg = await ctx.send(f"Triple test untuk {class_id} untuk sekuens {sequence} telah berhasil direkam.")
    await msg.delete(delay=90)

    await send_qr_embed_for_triple(ctx)
    cur.close()
    release_conn(conn)  # Release the connection back to the pool

def setup(bot):
    bot.add_cog(TripleTest(bot))
