from decouple import config
import os
import json
import requests
import pandas as pd 
import numpy as np

import utilities as util
# import pytz


API_ENDPOINT  = config('API_ENDPOINT')
API_KEY       = config('API_KEY')

TEAM_ID   = config('TEAM_ID')
ANWARI_ID = config('ANWARI_ID')
RAQUEL_ID = config('RAQUEL_ID')
TIAGO_ID  = config('TIAGO_ID')

TIMEZONE  = config('TIMEZONE')

persons = {
  '1': ANWARI_ID,
  '2': RAQUEL_ID,
  '3': TIAGO_ID
}


columns_time_entries = [  'task_id', 'task_name',
                          'time_id', 'time_start', 'time_end', 'time_duration', 
                          'user_id', 'user_name']


def main() :

  # dates in format YYYY-MM-DD
  start = input("Begin since when? (in YYYY-MM-DD): ") # since early dec
  end = input("Until when? (defaults to today): ") # string or None
  assignee = input("Generate whose report?\n  1: Anwari \n  2: Raquel\n  3: Tiago\nPick one: ")

  start_ts = util.str_to_timestamp( start )
  end_ts = util.get_eod_timestamp( end )

  api_time_entries = f"{API_ENDPOINT}team/{TEAM_ID}/time_entries?start_date={start_ts-1}&end_date={end_ts}&assignee={persons[assignee]}"
  api_task = f"{API_ENDPOINT}task/"


  headers = {"Authorization": API_KEY }

  try:
    # read time_entries from API
    r = requests.get(api_time_entries, headers=headers)

  except:
    print('error konek coi')

  # write file for the first time
  time_entries = None

  if (r.status_code == 200):
    f = open('./time_entries.json', 'w')
    time_entries = r.json()
    f.write( r.text )
    f.close()
    print( f"There are { len(time_entries['data']) } time logs." )


  else:
    print( 'Response gagal. Status:', r.status_code )


  # # read time entries from file
  # f = open('./time_entries.json', 'r')
  # time_entries = json.load(f)
  # f.close()
  # # print(time_entries)

  tasks = {}

  # info about time_entries
  time_entries_rows = []


  for time_entry in time_entries['data'] :
    # populate the tasks object
    tasks[time_entry['task']['id']] = None

    # append new row
    time_entries_rows.append([  time_entry['task']['id'], 
                                time_entry['task']['name'],
                                time_entry['id'],         
                                pd.to_datetime(time_entry['start'], unit='ms', utc=True).tz_convert( TIMEZONE ), 
                                pd.to_datetime(time_entry['end'], unit='ms', utc=True).tz_convert( TIMEZONE ), 
                                int(time_entry['duration']),
                                time_entry['user']['id'], 
                                time_entry['user']['username'] ] )

  # create new dataframe
  time_entries_df = pd.DataFrame(time_entries_rows, columns=columns_time_entries)

  print( f"Found in { len(tasks) } tasks." )


  # =====
  # iterate over the task ids
  i = 0
  for task_id in tasks.keys() :

    print(f"> {str(i+1).rjust(3)}/{len(tasks)} | Fetching info about task {task_id}")

    t = requests.get(f"{api_task}{task_id}", headers=headers)
    tasks[task_id] = t.json()

    i+=1

  # ====
  # woohoo got the list's details here. We can work on something, finally.
  with open('./tasks.json', 'w') as tasks_file :
    # write the file
    json.dump(tasks, tasks_file)
    tasks_file.close()


  # # read tasks from file instead of API
  # with open('./tasks.json', 'r') as tasks_r_file :
  #   tasks = json.load( tasks_r_file )
  #   tasks_r_file.close()


  # create lists dataframe
  lists_df = pd.DataFrame([ [ tasks[task]['list']['id'],
                              tasks[task]['list']['name'], 
                              tasks[task]['id'] 
                              ] for task in tasks ], 
                            columns=['list_id', 'list_name', 'task_id'])
  
  # join everything
  all_df = pd.merge( time_entries_df, lists_df, how="left", on='task_id' )

  # .assign() to create new column
  all_df = all_df.assign(hours= lambda x: x.time_duration / (3600 * 1000))

  grouped_by_user = all_df.groupby('user_name')

  for username, user_frame in grouped_by_user :


    # --> INSERT SCRIPT to DIVIDE BETWEEN USERS HERE <--
    total_time = user_frame['time_duration'].sum()
    total_hour = total_time / (3600*1000)
    ten_percent = total_time * 0.1
    project_group = user_frame.groupby('list_name', sort=True)
    tasks_group = user_frame.groupby(['list_name', 'task_name'])


    print( f"\n\n\n>>>>>>> { username } " )
    print( "====== TASKS ======" )

    # print one by one huvt
    for project, project_frame in project_group:
      time_spent = project_frame['hours'].sum()
      fraction = time_spent / total_hour
      print( f"### {project.ljust(20)} | {time_spent:4.1f} hrs | {fraction:6.2%}" )
      # print(frame.iloc[:,[1, -1] ], end="\n\n\n")


    # export to CSV
    # todo: export per person.
    tasks_filename = f"{username} - tasks { util.timestamp_to_human( start_ts ) } - { util.timestamp_to_human( end_ts) }.csv"
    tasks_group['hours'].sum().rename_axis(['Project', 'Task']).reset_index().to_csv(f"./report/{ tasks_filename }")
    print( f"\nThe detailed tasks have been saved to: { tasks_filename }" )



    # fill user_frame with missing dates
    missing_dates = pd.date_range( start, util.get_end_date( end_ts), tz=TIMEZONE )

    missing_str = [ 'test' for _ in range(len(missing_dates)) ]
    missing_num = [ 0 for _ in range(len(missing_dates)) ]
    missing_empty = [ 0 for _ in range(len(missing_dates)) ]

    missing_df = pd.DataFrame({ 'task_id': missing_str, 'task_name': missing_str,
                            'time_id': missing_str, 'time_start': missing_dates, 
                            'time_end': missing_dates, 'time_duration': missing_num, 
                            'list_id': missing_str, 'list_name': missing_empty,
                            'user_id': missing_str, 'user_name': missing_str, 'hours': missing_empty})
    

    full_frame = user_frame.append( missing_df )

    # kinda work but missing some dates
    # print( full_frame.tail(20) )
    timesheet_df = pd.pivot_table(full_frame, index=['list_name'], margins=True, margins_name='Total', columns='time_start', values=['hours'], aggfunc=[np.sum], fill_value='')

    timesheet_filename = f"{ username } - timesheet { util.timestamp_to_human( start_ts ) } - { util.timestamp_to_human( end_ts) }.csv"
    # timesheet_df.loc['Total'] = timesheet_df.sum(numeric_only=True, axis=0)

    timesheet_df.to_csv(f"./report/{ timesheet_filename }")
    
    print( f"\n====== TIMESHEET ======" )
    print( timesheet_df )
    print( f"The timesheet is saved to: {timesheet_filename}" )



# call the function woohoo
if __name__ == "__main__":
  main()
