from nextcord.ext import commands
import os
import json
import nextcord

def register_test_input_command(bot, get_authenticated_class):

    class TestInputView(nextcord.ui.View):
        def __init__(self, ctx, question_num, student_name, answers):
            super().__init__()
            self.ctx = ctx
            self.question_num = question_num
            self.student_name = student_name
            self.answers = answers

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
            await interaction.response.send_message(f"Selected answer: {answer}")
            self.stop()

    @bot.command(name='testinput')
    async def test_input(ctx, sequence_number: str):
        CLASSES_JSON_FILE_PATH = 'classes.json'
        STUDENT_DATA_FOLDER_PATH = 'studentdata'

        class_name = get_authenticated_class(str(ctx.author.id))
        if class_name is None:
            await ctx.author.send("You are not authenticated as a teacher for any class.")
            return
        
        summary_message = ""  # Initialize summary_message here

        
        with open(CLASSES_JSON_FILE_PATH, 'r') as file:
            classes_data = json.load(file)
            students = classes_data[class_name]['students']

        for student in students:
            moodle_id = student['moodle_id']
            student_name = student['student_name']
            student_file_path = os.path.join(STUDENT_DATA_FOLDER_PATH, class_name, f'{moodle_id}.json')

            if not os.path.exists(student_file_path):
                student_data = {'level': 'l1', 'answers': []}
                os.makedirs(os.path.dirname(student_file_path), exist_ok=True)
                with open(student_file_path, 'w') as file:
                    json.dump(student_data, file)

            with open(student_file_path, 'r') as file:
                student_data = json.load(file)

            answers = []
            for question_num in range(2):
                view = TestInputView(ctx, question_num, student_name, answers)
                await ctx.author.send(
                    f"Please select the answer for {student_name}, Question {question_num + 1}:",
                    view=view)
                await view.wait()  # Wait for the view to stop

            previous_level = student_data['level']
            correct_answers_count = sum(1 for answer in answers if answer == 'B')
            if correct_answers_count == 2:
                student_data['level'] = f'l{min(int(student_data["level"][1]) + 1, 5)}'
            elif correct_answers_count == 0:
                student_data['level'] = f'l{max(int(student_data["level"][1]) - 1, 1)}'

            student_data['answers'].append({f'sequence{sequence_number}': answers})

            with open(student_file_path, 'w') as file:
                json.dump(student_data, file)

            level_change = "stayed at the same level"
            if student_data['level'] > previous_level:
                level_change = "gone up a level"
            elif student_data['level'] < previous_level:
                level_change = "gone down a level"

            summary_message += f"{student_name}: Previous Level: {previous_level}, Current Level: {student_data['level']}, Level Change: {level_change}, Answers: {answers}\n"

        await ctx.author.send(
            f"Test input completed successfully. Here's the summary:\n{summary_message}"
        )
