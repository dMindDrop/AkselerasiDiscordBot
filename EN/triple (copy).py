import os
import json
import psycopg2
import psycopg2.extras
import nextcord
from nextcord.ext import commands
from datetime import datetime
from io import BytesIO
from views import TripleInputView

# Initialize database connection
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Create a cursor
cur = conn.cursor()

# Create test_triple and ppl_current_topic tables if they don't exist
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

async def send_qr_embed_for_triple(ctx):
    cur = conn.cursor()
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'PreMidPost test';")
    row = cur.fetchone()
    cur.close()

    if row:
        title, description, binary_data, link = row
        byte_stream = BytesIO(binary_data)
        file = nextcord.File(byte_stream, filename="qrcode.png")
        embed = nextcord.Embed(title=title, description=description, color=nextcord.Color.green())
        embed.add_field(name="Link", value=f"[Click here if you're on mobile]({link})", inline=False)
        embed.set_image(url="attachment://qrcode.png")
        msg = await ctx.channel.send(embed=embed, file=file)
        await msg.delete(delay=45)
    else:
        msg = await ctx.channel.send("No QR code information found.")
        await msg.delete(delay=15)





class TripleTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='tri')
    async def mark_triple_test_command(self, ctx, sequence: int):
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT staff_id FROM auth_data WHERE discord_id = %s", (str(ctx.author.id),))
        teacher_staff_id_row = cur.fetchone()
        teacher_staff_id = teacher_staff_id_row['staff_id'] if teacher_staff_id_row else None

        cur.execute("SELECT class_id FROM ppl_classes WHERE teacher_id = %s", (teacher_staff_id,))
        class_id_row = cur.fetchone()
        class_id = class_id_row['class_id'] if class_id_row else None

        cur.close()

        if teacher_staff_id and class_id:
            await mark_triple_test(ctx, teacher_staff_id, class_id, sequence)
        else:
            msg = await ctx.channel.send("Teacher or class not found.")
            await msg.delete(delay=15)






async def mark_triple_test(ctx, teacher_staff_id, class_id, sequence):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    with open('current_sequence.json', 'r') as f:
        current_sequence_data = json.load(f)
    current_sequence = current_sequence_data['triple']

    msg = await ctx.channel.send(f"Currently inputting data for sequence {sequence}.")
    await msg.delete(delay=15)

    cur.execute("SELECT student_id, student_name FROM ppl_classes WHERE class_id = %s AND active = 'yes'", (class_id,))
    students = cur.fetchall()

    for student in students:
        student_id = student['student_id']
        student_name = student['student_name']

        view = TripleInputView(ctx, student_name, student_id)
        msg = await ctx.channel.send(f"Mark triple test for {student_name} (ID: {student_id}):", view=view)
        await msg.delete(delay=15)
        await view.wait()

        topic_based_on_result = view.topic

        cur.execute("INSERT INTO test_triple (time_stamp, sequence, student_ID, topic_based_on_result) VALUES (%s, %s, %s, %s)",
                    (datetime.now(), current_sequence, student_id, topic_based_on_result))
        conn.commit()

        cur.execute("INSERT INTO ppl_current_topic (time_stamp, student_ID, current_topic, assessment_tool) VALUES (%s, %s, %s, %s)",
                    (datetime.now(), student_id, topic_based_on_result, 'triple'))
        conn.commit()

    msg = await ctx.channel.send(f"Triple test for {class_id} for sequence {sequence} has been successfully recorded.")
    await msg.delete(delay=15)

    await send_qr_embed_for_triple(ctx)
    cur.close()

def setup(bot):
    bot.add_cog(TripleTest(bot))
