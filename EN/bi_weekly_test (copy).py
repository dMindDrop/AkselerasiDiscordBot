import nextcord
from nextcord.ext import commands
import psycopg2
import os
import json
import asyncio
from io import BytesIO  # Import BytesIO for handling byte streams

# Function to send QR code embedded message
async def send_qr_embed(temp_channel):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute("SELECT title, description, image, link FROM admin_qrcode WHERE title = 'student attendance';")
    row = cur.fetchone()
    cur.close()

    if row:
        title, description, binary_data, link = row
        byte_stream = BytesIO(binary_data)
        file = nextcord.File(byte_stream, filename="qrcode.png")
        embed = nextcord.Embed(title=title, description=description, color=nextcord.Color.green())
        embed.add_field(name="Link", value=f"[Click here if you're on mobile]({link})", inline=False)
        embed.set_image(url="attachment://qrcode.png")
        await temp_channel.send(embed=embed, file=file, delete_after=45)
    else:
        await temp_channel.send("No QR code information found.", delete_after=45)

class ConfirmationView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @nextcord.ui.button(label='Yes', style=nextcord.ButtonStyle.success)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = True
        self.stop()

    @nextcord.ui.button(label='No', style=nextcord.ButtonStyle.danger)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = False
        self.stop()

class BiWeeklyTestView(nextcord.ui.View):
    def __init__(self, ctx, question_text, student_name, current_topic):
        super().__init__()
        self.ctx = ctx
        self.question_text = question_text
        self.student_name = student_name
        self.current_topic = current_topic
        self.answers = []

    @nextcord.ui.button(label='A', style=nextcord.ButtonStyle.primary, custom_id="A")
    async def answer_a(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.answers.append('A')
        self.stop()

    @nextcord.ui.button(label='B', style=nextcord.ButtonStyle.primary, custom_id="B")
    async def answer_b(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.answers.append('B')
        self.stop()

    @nextcord.ui.button(label='C', style=nextcord.ButtonStyle.primary, custom_id="C")
    async def answer_c(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.answers.append('C')
        self.stop()

    @nextcord.ui.button(label='D', style=nextcord.ButtonStyle.primary, custom_id="D")
    async def answer_d(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.answers.append('D')
        self.stop()

class BiWeeklyTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='bi')
    async def mark_bi_weekly_test(self, ctx, sequence_number: int):
        # Create a temporary channel for the test
        channel_name = f"{ctx.author.name}-bi-weekly-test"
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        await temp_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
        await temp_channel.send(f"{ctx.author.mention}, please continue the bi-weekly test process here.")

        # Notify the user in the main channel to move to the temporary channel
        await ctx.send(f"{ctx.author.mention}, please move to {temp_channel.mention} to continue with the bi-weekly test.")
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Fetch staff_id based on discord_id
        cur.execute("SELECT staff_id FROM auth_data WHERE discord_id = %s", (str(ctx.author.id),))
        staff_id = cur.fetchone()[0]

        # Fetch student information based on the teacher's staff_id and only active students
        cur.execute("SELECT student_id, student_name FROM ppl_classes WHERE teacher_id = %s AND active = 'yes'", (staff_id,))
        students = cur.fetchall()

        all_answers = {}
        summary_text = "Summary of Inputs:\n"

        for student_id, student_name in students:
            # Fetch the current topic for the student
            cur.execute("SELECT current_topic FROM ppl_current_topic WHERE student_id = %s", (student_id,))
            current_topic = cur.fetchone()[0] if cur.fetchone() else 'Penjumlahan'

            # Fetch the questions for the current topic and sequence
            cur.execute("SELECT task FROM test_bi_questions WHERE topic = %s AND sequence = %s", (current_topic, sequence_number))
            questions = cur.fetchall()

            student_answers = []
            for i, question_text in enumerate(questions):
                view = BiWeeklyTestView(temp_channel, question_text[0], student_name, current_topic)  # Changed ctx to temp_channel
                message = await temp_channel.send(f"Student: {student_name}\nTopic: {current_topic}\nQuestion: {question_text[0]}", view=view)
                await view.wait()
                await message.delete(delay=30)
                student_answers.extend(view.answers)

            all_answers[student_id] = student_answers
            summary_text += f"Student: {student_name}, Answers: {student_answers}\n"

        # Display summary
        await temp_channel.send(summary_text, delete_after=100)

        # Confirmation logic
        confirm_message = f"Do you want to store the answers for sequence {sequence_number}?"


        class ConfirmationView(nextcord.ui.View):
            def __init__(self):
                super().__init__(timeout=10)
                self.value = None

            @nextcord.ui.button(label='Yes', style=nextcord.ButtonStyle.success)
            async def yes_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
                self.value = True
                self.stop()

            @nextcord.ui.button(label='No', style=nextcord.ButtonStyle.danger)
            async def no_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
                self.value = False
                self.stop()

        confirm_view = ConfirmationView()
        confirmation_msg = await temp_channel.send(confirm_message, view=confirm_view)
        await confirm_view.wait()
        await confirmation_msg.delete()  # Manually delete the message

        if confirm_view.value:
            # Store the answers in the database
            for student_id, answers in all_answers.items():
                answers_json = json.dumps({"question1": answers[0], "question2": answers[1]})
                cur.execute("INSERT INTO test_bi_results (sequence, student_id, topic, answers) VALUES (%s, %s, %s, %s)", 
                            (sequence_number, student_id, current_topic, answers_json))
                conn.commit()

            # Send QR code embedded message
            await send_qr_embed(temp_channel)

        cur.close()
        conn.close()

# Delete the temporary channel after a delay
        await asyncio.sleep(60)
        await temp_channel.delete()


def setup(bot):
    bot.add_cog(BiWeeklyTest(bot))
