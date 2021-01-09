import time
import datetime
import json
import requests
import pandas as pd 
import numpy as np


team_id = 2155452

anwari_id = 2440313
raquel_id = 2440555

persons = {
  '1': anwari_id,
  '2': raquel_id
}

# dates in format YYYY-MM-DD
start = input("Start date in YYYY-MM-DD: ") # since early dec
end = input("End date (defaults to today): ") # string or None
assignee = input("Who?\n1: anwari \n2: raquel\n")


def get_end_date( ts_ms ):
  return datetime.datetime.fromtimestamp( ts_ms/1000 ).strftime('%Y-%m-%d')

def get_end_tsm( s ) :
  if s == '' :
    # check for the end of day
    return int( datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp() * 1000) 
  else :
    return int( datetime.datetime.strptime( s, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=0).timestamp() * 1000 )

def str_to_tsm( s ):
  tt = datetime.datetime.strptime( s, '%Y-%m-%d').timetuple()
  return int( time.mktime( tt ) ) * 1000

def tsm_to_human( ts_ms ):
  return datetime.datetime.fromtimestamp( ts_ms /1000 ).strftime('%b %d')


start_ts = str_to_tsm( start )
end_ts = get_end_tsm( end )

# print(f"end: {end_ts}")

columns_time_entries = [  'task_id', 'task_name',
                          'time_id', 'time_start', 'time_end', 'time_duration', 
                          'user_id', 'user_name']


api_endpoint = "https://api.clickup.com/api/v2/"


api_time_entries = f"{api_endpoint}team/{team_id}/time_entries?start_date={start_ts}&end_date={end_ts}&assignee={persons[assignee]}"
api_task = f"{api_endpoint}task/"

API_KEY = "pk_2440313_HIA6COTHC9K46M7WXVW62K3Z9QUNAYTV"
headers = {"Authorization": API_KEY }


def main() :

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
    print( f"There are { len(time_entries['data']) } time logs found." )


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
    time_entries_rows.append([  time_entry['task']['id'], time_entry['task']['name'],
                                time_entry['id'],         pd.to_datetime(time_entry['start'], unit='ms'), pd.to_datetime(time_entry['end'], unit='ms'), int(time_entry['duration']),
                                time_entry['user']['id'], time_entry['user']['username'] ] )

  # create new dataframe
  time_entries_df = pd.DataFrame(time_entries_rows, columns=columns_time_entries)

  # print( time_entries_df )

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


    # --> INSERT SCRIPT u/ DIVIDE BETWEEN USERS HERE <--
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
    tasks_filename = f"{username} | tasks { tsm_to_human( start_ts )} - {tsm_to_human( end_ts)}.csv"
    tasks_group['hours'].sum().rename_axis(['Project', 'Task']).reset_index().to_csv(f"./{ tasks_filename }")
    print( f"\nThe detailed tasks have been saved to: { tasks_filename }" )



    # fill user_frame with missing dates
    missing_dates = pd.date_range( start, get_end_date( end_ts) )

    missing_str = [ 'test' for _ in range(len(missing_dates)) ]
    missing_num = [ 0 for _ in range(len(missing_dates)) ]
    missing_empty = [ '' for _ in range(len(missing_dates)) ]

    missing_df = pd.DataFrame({ 'task_id': missing_str, 'task_name': missing_str,
                            'time_id': missing_str, 'time_start': missing_dates, 'time_end': missing_dates, 'time_duration': missing_num, 
                            'list_id': missing_str, 'list_name': missing_empty,
                            'user_id': missing_str, 'user_name': missing_str, 'hours': missing_empty})
    

    full_frame = user_frame.append( missing_df )

    # kinda work but missing some dates
    # print( full_frame.tail(20) )
    timesheet_df = pd.pivot_table(full_frame, index='list_name', columns='time_start', values='hours', aggfunc=np.sum, fill_value='')
    timesheet_filename = f"{ username } | timesheet { tsm_to_human( start_ts )} - {tsm_to_human( end_ts)}.csv"
    timesheet_df.to_csv(f"./{ timesheet_filename }")
    print( f"\n====== TIMESHEET ======" )
    # print( timesheet_df )
    print( f"The timesheet is saved to: {timesheet_filename}" )

# call the thingy woohoo

if __name__ == "__main__":
  main()
