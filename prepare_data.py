###################
# Data processing #
###################

import sqlite3 as lite
import sys
from operator import itemgetter
import time, datetime
from datetime import date, timedelta


# Constants
max_week = 100
week1 = datetime.date(int(2013), int(1), int(27)).isocalendar()[1]
fdate_week1 = datetime.date(int(2013), int(1), int(21))
ldate_week1 = datetime.date(int(2013), int(1), int(27))



# Get database
def get_db(DATABASE):
    con = None
    con = lite.connect(DATABASE)
    cur = con.cursor()
    return cur

# Check if two dates are in the same week week
def check_sameweek(m, d, y, m1, d1, y1):
    isSameWeek = True
    d = datetime.date(int(y), int(m), int(d))
    #td = date.today()
    td = datetime.date(int(y1), int(m1), int(d1))
    wkd = td.weekday()
    fd = td - datetime.timedelta(days = wkd)
    if d < fd or d > td:
        isSameWeek = False
    return isSameWeek


# Past activities for a single user
def past_activities(DATABASE, username):

    # Get database
    cur = get_db(DATABASE)

    # Get all past activities for this username
    cur.execute('select * from activities where username = ?', [username]);
    activities = [dict(aid=row[0], username=row[1], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                       low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], week=0) for row in cur.fetchall()]

    social = [0] * 6                                        # How social is your activities
    low_week = [0] * max_week                               # Minutes of low intensity activities for each week
    moderate_week = [0] * max_week                          # Minutes of moderate intensity activities for each week
    high_week = [0] * max_week                              # Minutes of high intensity activities for each week
    points_week = [0] * max_week                            # Points for each week
    low_weekday = [0] * 7                                   # Minutes of low intensity activities for each day of the week (0 is Sunday)
    moderate_weekday = [0] * 7                              # Minutes of moderate intensity activities for each day of the week (0 is Sunday)
    high_weekday = [0] * 7                                  # Minutes of high intensity activities for each day of the week (0 is Sunday)
    points_weekday = [0] * 7                                # Points for each day of the week (0 is Sunday)
    intensity_weekday = [0] * 7                             # Average intensity for each day of the week (0 is Sunday)
    weeks = [dict(fm=0,fd=0,lm=0,ld=0) for i in range(0, max_week)]
    activity_list = []                                      # My activity list
    activity_type = []                                      # My activity information
    

    # Current week
    td = date.today()
    tweek = td.isocalendar()[1] - week1

    # Start and end dates for each week
    for i in range(0, max_week):
        thisfdate = fdate_week1 + datetime.timedelta(days=i*7)
        thisldate = ldate_week1 + datetime.timedelta(days=i*7)
        weeks[i]['fm'] = thisfdate.month
        weeks[i]['fd'] = thisfdate.day
        weeks[i]['lm'] = thisldate.month
        weeks[i]['ld'] = thisldate.day

    # Classify the activities into their weeks
    for activity in activities:
        d = datetime.date(activity['year'], activity['month'], activity['day'])
        activity['week'] = d.isocalendar()[1] - week1

        low_week[activity['week']] += activity['low']
        moderate_week[activity['week']] += activity['moderate']
        high_week[activity['week']] += activity['high']
        points_week[activity['week']] += activity['newpoints']

        low_weekday[d.weekday()] += activity['low']
        moderate_weekday[d.weekday()] += activity['moderate']
        high_weekday[d.weekday()] += activity['high']        
        points_weekday[d.weekday()] += activity['newpoints']

        if activity['ppl'] >= 5:
            social[5] += activity['newpoints']
        else:
            social[activity['ppl']] += activity['newpoints']

        # Activity pattern
        if activity['activity'] in activity_list:
            for thistype in activity_type:
                if thistype['name'] == activity['activity']:
                    thistype['points'] += activity['newpoints']
                    thistype['times'] += 1
        else:
            activity_list.append(activity['activity'])
            activity_type.append({'name': activity['activity'], 'points': activity['newpoints'], 'times': 1})

    # Average intensity for each weekday
    for weekday in range(0,7):
        total_minutes = low_weekday[weekday] + moderate_weekday[weekday] + high_weekday[weekday]
        if total_minutes == 0:
            intensity_weekday[weekday] = 0.0
        else:
            intensity_weekday[weekday] = float(1 * low_weekday[weekday] + 2 * moderate_weekday[weekday] + 3 * high_weekday[weekday]) / float(total_minutes)

    return [intensity_weekday, points_weekday, points_week, low_week, moderate_week, high_week, tweek, weeks, social, activity_type]




# Group activities
def group_points(DATABASE, username):

    # Get database
    cur = get_db(DATABASE)

    # User's current group
    cur.execute('select groupname from profiles where username = ?', [username])
    groupnames = [row[0] for row in cur.fetchall()]
    groupname = groupnames[0]

    # Points distribution in user's current group
    cur.execute('select username from profiles where groupname = ?', [groupname])
    users = [dict(username=row[0]) for row in cur.fetchall()]
    cur.execute('select points.* from points, profiles where points.username = profiles.username and profiles.groupname = ?', [groupname])
    points = [dict(username=row[0], point=row[1], level=row[2]) for row in cur.fetchall()]
    points_sorted = sorted(points, key = itemgetter('point'),  reverse = True)

    group_points_week = [0] * max_week
    group_points_weekday = [0] * 7                                # Points for each day of the week (0 is Sunday)

    # Current week
    td = date.today()
    tweek = td.isocalendar()[1] - week1


    # Group history
    for user in users:
        cur.execute('select newpoints, year, month, day from activities where username = ?', [user['username']])
        activities = [dict(newpoints=row[0], year=row[1], month=row[2], day=row[3], week=0) for row in cur.fetchall()]
        for activity in activities:
            d = datetime.date(activity['year'], activity['month'], activity['day'])
            activity['week'] = d.isocalendar()[1] - week1
            group_points_week[activity['week']] += activity['newpoints']
            group_points_weekday[d.weekday()] += activity['newpoints']

    return [points_sorted, group_points_week, group_points_weekday, tweek]

