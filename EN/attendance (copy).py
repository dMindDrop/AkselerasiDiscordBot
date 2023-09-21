import os
import psycopg2
import psycopg2.extras
import nextcord  # Make sure to add this line
import psycopg2.pool  # Import the pool module from psycopg2
import asyncio 

from datetime import datetime
from views import AttendanceInputView, send_qr_embed  # Import the AttendanceInputView and send_qr_embed
from nextcord.ext import commands
from io import BytesIO  # Import BytesIO for handling byte streams


# Initialize the connection pool
DATABASE_URL = os.environ['DATABASE_URL']
minconn = 1
maxconn = 10

conn_pool = psycopg2.pool.SimpleConnectionPool(minconn, maxconn, DATABASE_URL, sslmode='require')

# Function to get a connection from the pool
def get_conn():
    return conn_pool.getconn()

# Function to release a connection back to the pool
def release_conn(conn):
    conn_pool.putconn(conn)

# Initialize database and create table
def initialize_database():
    conn = get_conn()
    cur = conn.cursor()
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS ppl_attendance (
        id SERIAL PRIMARY KEY,
        date DATE,
        time TIME,
        attendee TEXT,
        status TEXT,
        class_id TEXT
    );
    '''
    cur.execute(create_table_query)
    conn.commit()
    cur.close()
    release_conn(conn)

# Call the function to initialize the database
initialize_database()

async def send_qr_embed(ctx):
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
        msg = await ctx.channel.send(embed=embed, file=file)
        await msg.delete(delay=45)
    else:
        msg = await ctx.channel.send("No QR code information found.")
        await msg.delete(delay=15)





async def mark_attendance(ctx):
    discord_id = str(ctx.author.id)  # Get the Discord ID of the user who invoked the command

    # Get a connection from the pool
    conn = get_conn()

    # Create a cursor with dictionary support
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Fetch staff_id from auth_data based on discord_id
    cur.execute("SELECT staff_id FROM auth_data WHERE discord_id = %s", (discord_id,))
    staff_id_row = cur.fetchone()
    if not staff_id_row:
        msg = await ctx.channel.send("You are not authorized to mark attendance.")
        await msg.delete(delay=15)
        return
    staff_id = staff_id_row['staff_id']

    # Fetch active students and principal from ppl_classes based on staff_id
    cur.execute("SELECT student_id, student_name, principal_id, class_id FROM ppl_classes WHERE (teacher_id = %s OR principal_id = %s) AND active = 'yes'", (staff_id, staff_id))
    people = cur.fetchall()

    if not people:
        msg = await ctx.channel.send("No active students or principals found for this class.")
        await msg.delete(delay=15)
        return

    # Initialize attendance data
    attendance_data = {
        'date': None,
        'time': None,
        'attendance': {}
    }

    # Ask the user for the date and time with validation
    while True:
        msg = await ctx.channel.send("Please enter the date of the class (dd-mm-yy):")
        await msg.delete(delay=15)
        date_msg = await ctx.bot.wait_for('message', check=lambda m: m.author == ctx.author)
        try:
            attendance_data['date'] = datetime.strptime(date_msg.content, '%d-%m-%y').strftime('%Y-%m-%d')
            break
        except ValueError:
            msg = await ctx.channel.send("Invalid date format. Please enter the date in the format dd-mm-yy.")
            await msg.delete(delay=15)

    while True:
        msg = await ctx.channel.send("Please enter the time of the class (hh:mm):")
        await msg.delete(delay=15)
        time_msg = await ctx.bot.wait_for('message', check=lambda m: m.author == ctx.author)
        try:
            attendance_data['time'] = datetime.strptime(time_msg.content, '%H:%M').strftime('%H:%M:%S')
            break
        except ValueError:
            msg = await ctx.channel.send("Invalid time format. Please enter the time in the format hh:mm.")
            await msg.delete(delay=15)

    # Iterate through each student in the class
    for person in people:
        person_id = person['student_id'] or person['principal_id']
        person_name = person['student_name']  # Assuming principal_name and student_name have the same key
        class_id = person['class_id']

        # Display the attendance buttons
        view = AttendanceInputView(ctx, person_name, person_id)
        msg = await ctx.channel.send(f"Mark attendance for {person_name} (ID: {person_id}):", view=view)
        await msg.delete(delay=15)
        await view.wait()

        # Record the attendance status
        attendance_data['attendance'][person_id] = view.status

        # Update 'active' status if "Not in Class" is selected
        if view.status == 'Not in Class':
            cur.execute("UPDATE ppl_classes SET active = 'no' WHERE student_id = %s AND teacher_id = %s", (person_id, staff_id))
            conn.commit()

    # Insert the attendance data into the 'ppl_attendance' table
    for person_id, status in attendance_data['attendance'].items():
        cur.execute("INSERT INTO ppl_attendance (date, time, attendee, status, class_id) VALUES (%s, %s, %s, %s, %s)",
                    (attendance_data['date'], attendance_data['time'], person_id, status, class_id))
        conn.commit()

    msg = await ctx.channel.send("Attendance has been successfully recorded.")
    await msg.delete(delay=15)

    # Send the QR code embedded message
    await send_qr_embed(ctx)  # Call the function here

    # Close the cursor
    cur.close()

    # Release the connection back to the pool
    release_conn(conn)







class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='attendance')
    async def mark_attendance_command(self, ctx):
        # Create a temporary channel for data input
        channel_name = f"{ctx.author.name}-attendance"
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        await temp_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)

        # Notify the user in the main channel to move to the temporary channel
        await ctx.send(f"{ctx.author.mention}, please move to {temp_channel.mention} to continue with the attendance.")

        # Update the context to use the temporary channel
        ctx.channel = temp_channel

        # Call the mark_attendance function
        await mark_attendance(ctx)

        # Delete the temporary channel after 60 seconds
        await asyncio.sleep(60)
        await temp_channel.delete()






# Add this setup function at the end of your attendance.py
def setup(bot):
    bot.add_cog(Attendance(bot))
