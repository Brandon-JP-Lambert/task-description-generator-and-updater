import os
import requests
import openai
import json

# Initialize OpenAI API
openai.api_key = '[REPLACE]'

# Set headers for ClickUp API
headers = {
    'Authorization': '[REPLACE]',
    'Content-Type': '[REPLACE]'
}

def get_organization_ids():
    url = "https://api.clickup.com/api/v2/team"
    response = requests.get(url, headers=headers)
    organizations = response.json()['teams']
    org_ids = [org['id'] for org in organizations]
    return org_ids

def get_spaces(team_id):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/space?archived=false"
    response = requests.get(url, headers=headers)
    spaces = response.json()['spaces']
    return spaces

# Function to get all active tasks from ClickUp
def get_folders(space_id):
    url = f"https://api.clickup.com/api/v2/space/{space_id}/folder?archived=false"
    response = requests.get(url, headers=headers)
    folders = response.json()['folders']
    return folders


def get_lists(folder_id=None, space_id=None):
    if folder_id:
        url = f"https://api.clickup.com/api/v2/folder/{folder_id}/list?archived=false"
    elif space_id:
        url = f"https://api.clickup.com/api/v2/space/{space_id}/list?archived=false"
    else:
        return []

    response = requests.get(url, headers=headers)
    lists = response.json()['lists']
    return lists


def get_tasks(list_id):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    params = {
        'archived': 'false',
        'statuses[]': ['open', 'in progress', "ongoing"]
    }
    response = requests.get(url, headers=headers, params=params)
    tasks = response.json().get('tasks', [])
    return tasks


def get_active_tasks(organization_ids):
    all_tasks = []

    for org_id in organization_ids:
        spaces = get_spaces(org_id)

        for space in spaces:
            space_id = space['id']

            # Get tasks from lists inside folders
            folders = get_folders(space_id)
            for folder in folders:
                folder_id = folder['id']
                lists = get_lists(folder_id=folder_id)

                for list_ in lists:
                    tasks = get_tasks(list_['id'])
                    all_tasks.extend(tasks)
                    print(f"Fetched {len(tasks)} tasks from list '{list_['name']}' in folder '{folder['name']}' and space '{space['name']}'")

            # Get tasks from lists directly associated with spaces
            lists = get_lists(space_id=space_id)
            for list_ in lists:
                tasks = get_tasks(list_['id'])
                all_tasks.extend(tasks)
                print(f"Fetched {len(tasks)} tasks from list '{list_['name']}' in space '{space['name']}'")

    return all_tasks




# Function to call OpenAI API for task description and subtasks
def generate_task_info(prompt):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        temperature=0.5,
        max_tokens=400,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].text.strip()


# Function to update task description in ClickUp
def update_task_description(task_id, description):
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    payload = json.dumps({'description': description})
    response = requests.put(url, headers=headers, data=payload)
    if response.status_code != 200:
        print(f"Error updating task {task_id}: {response.content}")
    return response.status_code


def main():
    organization_ids = get_organization_ids()
    tasks = get_active_tasks(organization_ids)

    for task in tasks:
        if not task['description']:  # Task does not have a description
            list_title = task['list']['name']
            task_title = task['name']
            prompt = f"Act as an experienced executive assistant with a friendly and helpful approach. Please provide a brief summary of the '{task_title}' task in the '{list_title}' list and a list of specific subtasks related to it. Subtasks should be actionable steps, presented as bullet points. Include any other notes, etc. that you feel are relevant."

            task_info = generate_task_info(prompt)
            update_status = update_task_description(task['id'], task_info)

            if update_status == 200:
                print(f"Successfully updated task '{task_title}' with description and subtasks.")
            else:
                print(f"Failed to update task '{task_title}'.")


if __name__ == "__main__":
    main()
