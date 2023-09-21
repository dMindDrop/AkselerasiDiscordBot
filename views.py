import os
import psycopg2
import psycopg2.pool
import nextcord
import base64  # Import the base64 library
from io import BytesIO  # Import BytesIO for handling byte streams
from main import get_conn, release_conn  # Importing from main.py


# Function to send QR code embedded message
async def send_qr_embed(ctx):
    """
    Fetches the QR code and link with the title 'Student Attendance' from the admin_qrcode table
    and sends an embedded message to the user.
    """
    # Get a connection from the pool
    conn = get_conn()

    # Create a cursor
    cur = conn.cursor()

    # Fetch the QR code and link with the title 'Student Attendance'
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'student attendance';")
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
        await ctx.author.send(embed=embed, file=file)
    else:
        await ctx.author.send("No QR code information found.")

class TestInputView(nextcord.ui.View):
    def __init__(self, ctx, question_num, student_name, current_level, question_text, answers, sequence_number):
        super().__init__()
        self.ctx = ctx
        self.question_num = question_num
        self.student_name = student_name
        self.current_level = current_level
        self.question_text = question_text
        self.answers = answers
        self.sequence_number = sequence_number

    @nextcord.ui.button(label='A', style=nextcord.ButtonStyle.primary)
    async def answer_a(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.record_answer('A', interaction)

    @nextcord.ui.button(label='B', style=nextcord.ButtonStyle.primary)
    async def answer_b(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.record_answer('B', interaction)

    @nextcord.ui.button(label='C', style=nextcord.ButtonStyle.primary)
    async def answer_c(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.record_answer('C', interaction)

    @nextcord.ui.button(label='D', style=nextcord.ButtonStyle.primary)
    async def answer_d(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.record_answer('D', interaction)

    async def record_answer(self, answer, interaction):
        self.answers.append(answer)
        self.stop()

    async def on_timeout(self):
        await self.ctx.author.send(f"Sequence: {self.sequence_number}, Student: {self.student_name}, Time's up for Question {self.question_num + 1}: {self.question_text}.")

class InitialChoiceView(nextcord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.choice = None

    @nextcord.ui.button(label='Bi-weekly Test', style=nextcord.ButtonStyle.primary)
    async def bi_weekly_test(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.choice = 'bi_weekly_test'
        self.stop()

    @nextcord.ui.button(label='Triple Test', style=nextcord.ButtonStyle.primary)
    async def triple_test(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.choice = 'triple_test'
        self.stop()

    @nextcord.ui.button(label='Attendance', style=nextcord.ButtonStyle.primary)
    async def attendance(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.choice = 'attendance'
        self.stop()

class AttendanceInputView(nextcord.ui.View):
    def __init__(self, ctx, student_name, student_id):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.student_name = student_name
        self.student_id = student_id
        self.status = None

    @nextcord.ui.button(label='Hadir', style=nextcord.ButtonStyle.success)
    async def present(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.status = 'Hadir'
        self.stop()

    @nextcord.ui.button(label='Absen', style=nextcord.ButtonStyle.danger)
    async def absent(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.status = 'Absen'
        self.stop()

    @nextcord.ui.button(label='Pindah / Keluar', style=nextcord.ButtonStyle.secondary)
    async def not_in_class(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.status = 'Pindah / Keluar'
        self.stop()

class TripleInputView(nextcord.ui.View):
    def __init__(self, ctx, student_name, student_id):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.ctx = ctx
        self.student_name = student_name
        self.student_id = student_id
        self.topic = None

    @nextcord.ui.button(label="Penjumlahan", style=nextcord.ButtonStyle.primary)
    async def penjumlahan_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.topic = "Penjumlahan"
        self.stop()

    @nextcord.ui.button(label="Pengurangan", style=nextcord.ButtonStyle.primary)
    async def pengurangan_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.topic = "Pengurangan"
        self.stop()

    @nextcord.ui.button(label="Perkalian", style=nextcord.ButtonStyle.primary)
    async def perkalian_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.topic = "Perkalian"
        self.stop()

    @nextcord.ui.button(label="Pembagian Habis", style=nextcord.ButtonStyle.primary)
    async def pembagian_habis_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.topic = "Pembagian Habis"
        self.stop()

    @nextcord.ui.button(label="Pembagian Sisa", style=nextcord.ButtonStyle.primary)
    async def pembagian_sisa_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.topic = "Pembagian Sisa"
        self.stop()