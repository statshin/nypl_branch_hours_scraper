#!/usr/bin/env python
# coding: utf-8

# Import packages

from bs4 import BeautifulSoup
import urllib.request
from IPython.display import HTML
import re
import pandas as pd
import numpy as np
from datetime import datetime

# Retrieve List of NYPL Branch URL Links from https://www.nypl.org/locations

locations = urllib.request.urlopen('https://www.nypl.org/locations').read()
soup_locations = BeautifulSoup(locations, "lxml").find(id = "locations-list")

location_link = []
for link in soup_locations.find_all('a', attrs = {'href' : re.compile("^https://www.nypl.org/locations/")}):
    location_link.append(str(link))

# Functions for extracting Branch Name and Branch URL from Raw HTML

link = re.compile('\"https://www.nypl.org/locations/.+\"')
branch = re.compile('>.+<')

def branch_extract(x):
    match_obj = branch.search(x)
    return match_obj.group().strip("><")

def link_extract(x):
    match_obj = link.search(x)
    return match_obj.group().strip("\"")

# Create Dataframe of list of Branches and Branch URL Links

loc_df = pd.DataFrame({'raw_html': location_link})
loc_df['branch'] = loc_df['raw_html'].apply(branch_extract)
loc_df['link'] = loc_df['raw_html'].apply(link_extract)

# Extract Operational Hours from each Branch's home page

branch_hrs_df = pd.DataFrame({'branch': [], 'day': [], 'hours': []})

for x in range(0, len(loc_df.index), 1):
    r = urllib.request.urlopen(loc_df['link'][x]).read()
    soup = BeautifulSoup(r, "lxml").find(class_ = "hours")

    if soup is None: # Handle Branch that is temporarily closed
        temp_hrs_df = pd.DataFrame({'branch': [loc_df['branch'][x]] * 7, 'day': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 'hours': ['CLOSED'] * 7})
    else:
        branch_hours = soup.find_all('td')
    
        temp_days = []
        for days in branch_hours[::2]:
            temp_days.append(days.text)
        
        temp_hours = []
        for hours in branch_hours[1::2]:
            temp_hours.append(hours.text)

        temp_hrs_df = pd.DataFrame({'branch': [loc_df['branch'][x]] * 7, 'day': temp_days, 'hours': temp_hours})
    
    temp_hrs_df.index = temp_hrs_df['branch']
    branch_hrs_df = pd.concat([branch_hrs_df, temp_hrs_df])

# Split off Hours column into two columns - Open Time and Close Time
branch_hrs_df['hours'] = branch_hrs_df['hours'].str.replace(chr(8211), ' - ')
branch_hrs_df[['Open Time', 'Close Time']] = branch_hrs_df['hours'].str.split(" - ", expand = True)

# Add minutes to standardize time format (Ex. 10 AM - 10:00 AM)

branch_hrs_df['Open Time'][branch_hrs_df['Open Time'].str.match('\d+ [AP]M') ==  True] = branch_hrs_df['Open Time'][branch_hrs_df['Open Time'].str.match('\d+ [AP]M')].str.replace(' ', ':00 ')
branch_hrs_df['Close Time'][branch_hrs_df['Close Time'].str.match('\d+ [AP]M') ==  True] = branch_hrs_df['Close Time'][branch_hrs_df['Close Time'].str.match('\d+ [AP]M') ==  True].str.replace(' ', ':00 ')

# Calculate Hours Open

branch_hrs_df['Hours Open'] = None

for t in range(0, len(branch_hrs_df.index), 1):
    temp_open = branch_hrs_df['Open Time'][t]
    temp_close = branch_hrs_df['Close Time'][t]

    if temp_open == "CLOSED":
        temp_duration = 0.0
    else:
        temp_duration = (datetime.strptime(temp_close, '%I:%M %p') - datetime.strptime(temp_open, '%I:%M %p')).total_seconds() / 60 / 60

    branch_hrs_df['Hours Open'][t] = temp_duration

# Trim Branch and Day Column

branch_hrs_df['day'] = branch_hrs_df['day'].str.strip(': ')
branch_hrs_df['branch'] = branch_hrs_df['branch'].str.strip(' ')

# Write to CSV

branch_hrs_df.to_csv('NYPL Branch Hours.csv', encoding = 'utf-8', index = False)
