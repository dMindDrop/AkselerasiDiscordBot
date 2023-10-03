import nextcord
from nextcord.ext import commands
import psycopg2
import logging
from main import DatabaseConnectionManager  # Importing from main.py
from collections import defaultdict

logger = logging.getLogger(__name__)


class MyClass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='kelassaya')
    async def my_class(self, ctx, sequence: int):
        author_id = str(ctx.author.id)
        try:
            # Use DatabaseConnectionManager with the with statement
            with DatabaseConnectionManager() as conn:
                with conn.cursor() as cur:
                    await self.fetch_and_send_class_info(ctx, sequence, author_id, cur)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            await ctx.author.send("An error occurred while processing your request.")

    async def fetch_and_send_class_info(self, ctx, sequence, author_id, cur):
        cur.execute("SELECT staff_id FROM auth_data WHERE discord_id = %s", (author_id,))
        teacher_id = cur.fetchone()
        if not teacher_id:
            await ctx.author.send("You are not a teacher.")
            return

        cur.execute("SELECT student_id, student_name, class_id FROM ppl_classes WHERE teacher_id = %s AND active = 'yes'", (teacher_id,))
        students = cur.fetchall()

        topic_student_map = defaultdict(list)
        topic_question_cache = {}

        for student_id, student_name, class_id in students:
            cur.execute("SELECT current_topic FROM ppl_current_topic WHERE student_id = %s ORDER BY time_stamp DESC LIMIT 1", (student_id,))
            current_topic = cur.fetchone()[0]

            topic_student_map[current_topic].append(student_name)

            if current_topic not in topic_question_cache:
                cur.execute("SELECT task, correct FROM test_bi_questions WHERE topic = %s AND sequence = %s LIMIT 2", (current_topic, sequence))
                questions = cur.fetchall()
                topic_question_cache[current_topic] = questions

        message = await self.generate_message(sequence, topic_student_map, topic_question_cache)
        await ctx.author.send(message)

    async def generate_message(self, sequence, topic_student_map, topic_question_cache):
        message = f"📚 **Informasi tentang Kelas Putaran {sequence}** 📚\n"

        for topic, student_names in topic_student_map.items():
            questions = topic_question_cache[topic]
            question_text = ""

            if len(questions) < 2:
                question_text = "Not enough questions available."
            else:
                for i, (task, correct) in enumerate(questions):
                    question_text += f"  - **Pertanyaan {i+1}**: {task}\n"
                    question_text += f"    - Jawaban Benar: {correct}\n"

            message += f"\n📚 **Topik**: {topic}\n"
            message += question_text
            message += f"👩‍🎓 **Siswa**: {', '.join(student_names)}\n\n\n"

        return message


def setup(bot):
    bot.add_cog(MyClass(bot))
