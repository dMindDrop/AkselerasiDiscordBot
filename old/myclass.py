import os  # Import os for environment variables
import psycopg2  # Import PostgreSQL adapter for Python

# Function to get authenticated class
def get_authenticated_class(staff_id, cur):
    """
    This function fetches the authenticated class for a given staff ID.
    """
    query = "SELECT class_id FROM ppl_classes WHERE teacher_id = %s OR principal_id = %s;"
    cur.execute(query, (staff_id, staff_id))
    result = cur.fetchone()
    return result[0] if result else None

# Function to register my_class command
def register_my_class_command(bot, conn):
    """
    This function registers the 'myclass' command for the bot.
    """
    # Use environment variables to connect to PostgreSQL
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    
    @bot.command(name='myclass')
    async def my_class(ctx):
        """
        This function handles the 'myclass' command.
        """
        cur = conn.cursor()
        # Get StaffID from auth_data table based on Discord ID
        query = "SELECT staff_id FROM auth_data WHERE discord_id = %s;"
        cur.execute(query, (str(ctx.author.id),))
        result = cur.fetchone()
        staff_id = result[0] if result else None

        if not staff_id:
            await ctx.author.send("You are not authenticated.")
            return

        class_id = get_authenticated_class(staff_id, cur)
        if class_id is None:
            await ctx.author.send("You are not authenticated as a teacher or principal for any class.")
            return

        # Fetch student data from ppl_classes table
        query = "SELECT student_id, student_name FROM ppl_classes WHERE class_id = %s;"
        cur.execute(query, (class_id,))
        students = cur.fetchall()

        student_data_list = []
        for student_id, student_name in students:
            query = "SELECT current_status, test_results FROM student_data WHERE student_id = %s;"
            cur.execute(query, (student_id,))
            result = cur.fetchone()
            current_status, test_results = result if result else ('l1', [])

            # Format test results by sequence
            formatted_test_results = {}
            for ans_dict in test_results:
                for seq, ans in ans_dict.items():
                    if seq not in formatted_test_results:
                        formatted_test_results[seq] = []
                    formatted_test_results[seq].append(ans)

            student_data_list.append({
                'student_name': student_name,
                'current_status': current_status,
                'test_results': formatted_test_results
            })

        summary_message = "Summary of the class"  # Replace this with your actual summary formatting logic

        # Split the summary_message into smaller chunks
        chunk_size = 2000  # Discord's character limit per message
        summary_chunks = [summary_message[i:i + chunk_size] for i in range(0, len(summary_message), chunk_size)]

        # Send each chunk as a separate message
        for chunk in summary_chunks:
            await ctx.author.send(chunk)

        cur.close()
