import sqlite3 as lite
import sys
from operator import itemgetter
import time, datetime
from datetime import date, timedelta


# Check if date is in this week
def check_sameweek(m, d, y):
    isSameWeek = True
    d = datetime.date(int(y), int(m), int(d))
    td = date.today()
    wkd = td.weekday()
    fd = td - datetime.timedelta(days = wkd)
    if d < fd:
        isSameWeek = False
    return isSameWeek




# Clear all user points, update all levels, freeze all activities, if this is the first global login in a week
def main_loop():
    DATABASE = '/tmp/owlympics_test.db'
    con = None
    con = lite.connect(DATABASE)
    cur = con.cursor()
    while True:
        cur.execute('select * from login')
        logins = [dict(year=row[0], month=row[1], day=row[2]) for row in cur.fetchall()]
        login = logins[0]
        if not check_sameweek(login['month'], login['day'], login['year']): # If this is the first global login
            # Update last global login
            td = datetime.datetime.now()
            cur.execute('update login set year=?, month=?, day=?', [int(td.year), int(td.month), int(td.day)])
            cur.commit()
            # Update all activities
            cur.execute('select id, year, month, day from activities')
            activities = [dict(id=row[0], year=row[1], month=row[2], day=row[3]) for row in cur.fetchall()]
            for activity in activities:
                if not check_sameweek(activity['month'], activity['day'], activity['year']):
                    cur.execute('update activities set isthisweek = 0 where id = ?', [activity['id']])
                    cur.commit()
            # Update all user points and level
            cur.execute('select * from points')
            points = [dict(username=row[0], point=row[1], level=row[2]) for row in cur.fetchall()]
            for point in points:
                if int(point['point']) >= 400:
                    level_new = point['level'] + 1
                elif int(point['point']) >= 200:
                        level_new = point['level']
                else:
                    level_new = point['level'] - 1
                if level_new < 1:
                    level_new = 1
                cur.execute('update points set point=?, level=? where username=?', [0, level_new, point['username']])
                cur.commit()

        td = datetime.datetime.now()
        f = open('GlobalLogIn.txt', 'a')
        f.write(str(td.year) + '/' + str(td.month) + '/' + str(td.day))
        f.close()
                
        # Check every one hour
        time.sleep(5)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)
