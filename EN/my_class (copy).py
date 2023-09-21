import nextcord
from nextcord.ext import commands
import psycopg2.pool
import os
from collections import defaultdict

class MyClass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = psycopg2.pool.SimpleConnectionPool(0, 80, os.getenv('DATABASE_URL'))

    @commands.command(name='myclass')
    async def my_class(self, ctx, sequence: int):
        author_id = str(ctx.author.id)
        conn = self.pool.getconn()
        cur = conn.cursor()

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
                cur.execute("SELECT task, a, b, c, d, correct FROM test_bi_questions WHERE topic = %s AND sequence = %s LIMIT 2", (current_topic, sequence))
                questions = cur.fetchall()
                topic_question_cache[current_topic] = questions

        message = f"📚 **Class Information for Sequence {sequence}** 📚\n"

        for topic, student_names in topic_student_map.items():
            questions = topic_question_cache[topic]
            question_text = ""

            if len(questions) < 2:
                question_text = "Not enough questions available."
            else:
                for i, (task, a, b, c, d, correct) in enumerate(questions):
                    question_text += f"  - **Question {i+1}**: {task}\n"
                    question_text += f"    - Choices: A:{a}, B:{b}, C:{c}, D:{d}\n"
                    question_text += f"    - Correct Answer: {correct}\n"

            message += f"\n📚 **Topic**: {topic}\n"
            message += question_text
            message += f"👩‍🎓 **Students**: {', '.join(student_names)}\n\n\n"

        await ctx.author.send(message)

        cur.close()
        self.pool.putconn(conn)

def setup(bot):
    bot.add_cog(MyClass(bot))
