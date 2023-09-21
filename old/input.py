from nextcord.ext import commands
from views import InitialChoiceView  # Import the InitialChoiceView class
from bi_weekly_test import mark_bi_weekly_test_in_bi_weekly_file  # Import the renamed function
from attendance import mark_attendance  # Import the mark_attendance function
from triple import mark_triple_test
from shared_functions import get_authenticated_class  # Import from shared_functions.py

@commands.command(name='input')
async def register_test_input_command(ctx):
    # Display the initial choice buttons (Bi-weekly Test, Triple Test, Attendance)
    view = InitialChoiceView(ctx)
    await ctx.send("Please choose an option:", view=view)
    await view.wait()

    # Get the choice made by the user
    choice = view.choice

    # Call the appropriate function based on the choice
    if choice == 'bi_weekly_test':
        await mark_bi_weekly_test_in_bi_weekly_file(ctx)
    elif choice == 'triple_test':
        await mark_triple_test(ctx)
    elif choice == 'attendance':
        await mark_attendance(ctx)
    else:
        await ctx.send("Invalid choice.")

# Add this at the end to add the command to the bot
def setup(bot):
    bot.add_command(register_test_input_command)
