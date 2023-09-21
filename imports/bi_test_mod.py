import pandas as pd
import random
import csv

# Read the CSV file into a DataFrame
df = pd.read_csv('bi.csv')

# Add new columns for multiple-choice options and the correct answer
df['A'] = ''
df['B'] = ''
df['C'] = ''
df['D'] = ''
df['right'] = ''

# Iterate through each row to populate the new columns
for index, row in df.iterrows():
    try:
        # Remove extra quotes and newline characters
        cleaned_task = row['task'].replace('"', '').strip().replace('\n', '')
        
        # Check if the task can be split into task and correct_answer
        if ' = … (' in cleaned_task or ' = ... (' in cleaned_task:
            # Replace three dots with ellipsis for uniformity
            cleaned_task = cleaned_task.replace(' = ... (', ' = … (')
            
            # Split the task and the correct answer
            task, correct_answer = cleaned_task.split(' = … (')
            correct_answer = correct_answer.rstrip(')')
            
            # Update the task field to only contain the task
            df.at[index, 'task'] = task
            
            # Generate alternative answers based on the topic
            if 'sisa' in correct_answer:
                alternatives = [f"{int(correct_answer.split(' ')[0]) + random.randint(-2, 2)} sisa {random.randint(1, 5)}" for _ in range(3)]
            else:
                alternatives = [str(int(correct_answer) + random.randint(-5, 5)) for _ in range(3)]
            
            # Randomly place the correct answer among the alternatives
            choices = ['A', 'B', 'C', 'D']
            random.shuffle(choices)
            choices_dict = {choices[i]: ans for i, ans in enumerate([correct_answer] + alternatives)}
            
            # Update the DataFrame
            for choice, ans in choices_dict.items():
                df.at[index, choice] = ans
            
            # Store the correct answer's field name
            df.at[index, 'right'] = correct_answer
        else:
            print(f"Skipping row {index} due to inconsistent format. Cleaned task: {cleaned_task}, Problematic row: {row}")

    except Exception as e:
        print(f"Skipping row {index} due to error: {e}. Problematic row: {row}")

# Save the modified DataFrame to a new CSV file
df.to_csv('modified_bi.csv', index=False)
