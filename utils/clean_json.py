import json
from pprint import pprint

def clean_sessions(min_submissions):
    # Load the JSON data from the file
    with open('utils/job_tracking.json', 'r') as file:
        data = json.load(file)
    
    # Filter sessions based on the minimum number of submissions
    filtered_sessions, garbage_sessions = [], []
    for session in data['sessions']:
        if session['session_submissions'] > min_submissions:
            filtered_sessions.append(session)
        else:
            garbage_sessions.append(session)
    
    # Update the total_submissions
    total_submissions = sum(session['session_submissions'] for session in filtered_sessions)
    
    # Update the data dictionary
    data['sessions'] = filtered_sessions
    data['total_submissions'] = total_submissions
    
    # Write the updated data back to the JSON file
    with open('utils/job_tracking.json', 'w') as file:
        json.dump(data, file, indent=4)
    
    # Log success message and pprint the cleaned sessions
    if not garbage_sessions:
        print("✅ No sessions were thrown out")
    else:
        print("✅ The following sessions have been thrown out:")
        for session in garbage_sessions:
            pprint(session)

if __name__ == "__main__":
    min_submissions = 1  # Set your threshold here
    clean_sessions(min_submissions)
