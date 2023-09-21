import os
import json
import psycopg2
import psycopg2.extras
import nextcord
import asyncio
from io import BytesIO  # Add this import at the top of your file
from nextcord.ext import commands
from datetime import datetime
from main import get_conn, release_conn  # Importing from main.py

# Create test_bi_results and ppl_current_topic tables if they don't exist
conn = get_conn()
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS test_bi_results (
    id SERIAL PRIMARY KEY,
    time_stamp TIMESTAMP,
    sequence INTEGER,
    student_ID TEXT,
    topic TEXT,
    next_topic TEXT
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

async def send_qr_embed(ctx, channel):
    # Get a connection from the pool
    conn = get_conn()

    # Create a cursor
    cur = conn.cursor()

    # Fetch the QR code and link with the title 'Student Attendance'
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'Training';")
    row = cur.fetchone()

    # Close the cursor and release the connection back to the pool
    cur.close()
    release_conn(conn)

    if row:
        title, description, binary_data, link = row

        # Create a byte stream from binary data
        byte_stream = BytesIO(binary_data)

        # Upload the image to Discord as a file
        file = nextcord.File(byte_stream, filename="qrcode.png")
        
        # Create an embedded message
        embed = nextcord.Embed(title=title, description=description, color=nextcord.Color.green())
        embed.add_field(name="Link", value=f"[Click here if you're on mobile]({link})", inline=False)
        
        # Set a placeholder for the image URL in the embed
        embed.set_image(url="attachment://qrcode.png")

        # Send the embedded message along with the file
        msg = await channel.send(embed=embed, file=file)
        await msg.delete(delay=90)
    else:
        msg = await ctx.channel.send("No QR code information found.")
        await msg.delete(delay=90)


class TopicSelectionView(nextcord.ui.View):
    def __init__(self, ctx, student_name, student_id):
        super().__init__()
        self.ctx = ctx
        self.student_name = student_name
        self.student_id = student_id
        self.selected_topic = None

    @nextcord.ui.button(label='Penjumlahan', style=nextcord.ButtonStyle.primary)
    async def select_penjumlahan(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.selected_topic = 'Penjumlahan'
        self.stop()

    @nextcord.ui.button(label='Pengurangan', style=nextcord.ButtonStyle.primary)
    async def select_pengurangan(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.selected_topic = 'Pengurangan'
        self.stop()

    @nextcord.ui.button(label='Perkalian', style=nextcord.ButtonStyle.primary)
    async def select_perkalian(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.selected_topic = 'Perkalian'
        self.stop()

    @nextcord.ui.button(label='Pembagian Habis', style=nextcord.ButtonStyle.primary)
    async def select_pembagian_habis(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.selected_topic = 'Pembagian Habis'
        self.stop()

    @nextcord.ui.button(label='Pembagian Sisa', style=nextcord.ButtonStyle.primary)
    async def select_pembagian_sisa(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.selected_topic = 'Pembagian Sisa'
        self.stop()




class ConfirmView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @nextcord.ui.button(label='Konfirmasi', style=nextcord.ButtonStyle.success)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = True
        self.stop()

    @nextcord.ui.button(label='Batal', style=nextcord.ButtonStyle.danger)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = False
        self.stop()






from datetime import datetime
import psycopg2.extras
import nextcord
import asyncio
from main import get_conn, release_conn  # Importing from main.py

class BiWeeklyTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='quiz')
    async def mark_bi_weekly_test_command(self, ctx, sequence: int):
        print("Quiz command executed.")
        channel_name = f"{ctx.author.name}-bi"
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        await temp_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
        
        await ctx.send(f"{ctx.author.mention}, Silakan lanjutkan proses tes dua mingguan di {temp_channel.mention}.", delete_after=30)
        await temp_channel.send(f"{ctx.author.mention}, Silakan lanjutkan proses tes dua mingguan di sini.")
        
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
            student_topic_map = await mark_bi_weekly_test(temp_channel, teacher_staff_id, class_id, sequence)
        else:
            await temp_channel.send("Teacher or class not found.")
        
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        confirm_view = ConfirmView()
        confirm_msg = await temp_channel.send("Do you want to save these inputs?", view=confirm_view)
        await confirm_view.wait()

        if confirm_view.value:
            try:
                print("About to insert data into test_bi_results and ppl_current_topic.")
                for student_id, selected_topic in student_topic_map.items():
                    cur.execute("INSERT INTO test_bi_results (time_stamp, event_date, sequence, student_ID, topic, next_topic) VALUES (%s, %s, %s, %s, %s, %s)",
                                (datetime.now(), event_date, sequence, student_id, selected_topic, selected_topic))
                    cur.execute("INSERT INTO ppl_current_topic (time_stamp, student_ID, current_topic, assessment_tool) VALUES (%s, %s, %s, %s)",
                                (datetime.now(), student_id, selected_topic, 'bi_weekly'))
                conn.commit()
                
                print("Data inserted successfully.")
                await send_qr_embed(ctx, temp_channel)
            
            except Exception as e:
                print(f"An error occurred: {e}")

        cur.close()
        release_conn(conn)

        await asyncio.sleep(90)
        await temp_channel.delete()







async def mark_bi_weekly_test(ctx, teacher_staff_id, class_id, sequence):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT student_id, student_name FROM ppl_classes WHERE class_id = %s AND active = 'yes'", (class_id,))
    students = cur.fetchall()

    student_topic_map = {}
    summary_text = "Summary of Inputs:\n"

    for student in students:
        student_id = student['student_id']
        student_name = student['student_name']

        view = TopicSelectionView(ctx, student_name, student_id)
        msg = await ctx.send(f"Select topic for {student_name} (ID: {student_id}):", view=view)
        await view.wait()
        await msg.delete()

        selected_topic = view.selected_topic
        student_topic_map[student_id] = selected_topic
        summary_text += f"Student: {student_name}, Selected Topic: {selected_topic}\n"

    await ctx.send(summary_text)
    return student_topic_map

def setup(bot):
    bot.add_cog(BiWeeklyTest(bot))

