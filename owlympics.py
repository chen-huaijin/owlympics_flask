# -*- coding: utf-8 -*-
"""
    Owlympics
"""

from __future__ import with_statement
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
from sqlite3 import dbapi2 as sqlite3
import string
import time, datetime
from datetime import date, timedelta
from operator import itemgetter
from sets import Set
from httplib import HTTPResponse
import json

# User modules
import autoemail
import prepare_data




# Configuration
DATABASE = 'owlympics_test.db'
SECRET_KEY = 'development key'
DEBUG = True
USERNAME = 'admin'
PASSWORD = ''




# Create the application 
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('OWLYMPICS_SETTINGS', silent=True)




##############
# DB related #
##############

def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

def add_db():
    """Add some database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('add_rate_activity_two.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

def paid_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('paid.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
    return top.sqlite_db
    
@app.teardown_appcontext
def close_db_connection(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()




##############
# Main pages #
##############

@app.route('/')
def show_entries():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    else:
        return render_template('show_entries.html', activities = activity_feed())




#############
# Home page #
#############

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # Get the list of activities
    cur = db.execute('select newpoints from activities where username = ? and isthisweek = 1', [username])
    newpoints = [row[0] for row in cur.fetchall()]
    points = sum(newpoints)
    level_ind = 'red'
    points_more_same = 200 - points
    points_more_next = 400 - points
    if points_more_same < 0:
        points_more_same = 0
        level_ind = 'yellow'
    if points_more_next < 0:
        points_more_next = 0
        level_ind = 'green'

    # Update user points
    cur = db.execute('update points set point = ? where username = ?', [points, username])
    db.commit()

    # Get the user level from the db
    cur = db.execute('select * from points where username = ?', [username])
    levels = [row[2] for row in cur.fetchall()]
    level = levels[0]

    # Get all past activities
    [intensity_weekday, points_weekday, points_week, low_week, moderate_week, high_week, tweek, weeks, social, activity_type] \
                            = prepare_data.past_activities(DATABASE, username)

    # Average points in the past four weeks
    avg_points_week = (points_week[tweek-4] + points_week[tweek-3] + points_week[tweek-2] + points_week[tweek-1]) / 4

    # Max points in the past four weeks
    max_points_week = max([points_week[tweek-4], points_week[tweek-3], points_week[tweek-2], points_week[tweek-1]])

    # Total points in the entire history
    total_points_week = sum(points_week)

    # Total points for each weekday in the entire history
    #points_weekday = sorted(points_weekday,  reverse = True)

    # Group points in the past weeks
    [points_sorted, group_points_week, group_points_weekday, tweek] = prepare_data.group_points(DATABASE, username)
    
    return render_template('home.html', points = points, points_more_same = points_more_same, points_more_next = points_more_next,
                            level_ind = level_ind, level = level,
                            points_week = points_week, points_weekday = points_weekday, intensity_weekday = intensity_weekday,
                            avg_points_week = avg_points_week, max_points_week = max_points_week, total_points_week = total_points_week,
                            low_week = low_week, moderate_week = moderate_week, high_week = high_week, tweek = tweek, weeks = weeks, social = social,
                            points_sorted = points_sorted, group_points_week = group_points_week, group_points_weekday = group_points_weekday,
                            activity_type = activity_type,
                            activities = activity_feed())




###############
# Leaderboard #
###############

@app.route('/leaderboard')
def leaderboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    return redirect(url_for('lb_gm'))
    
# Leaderboard for group members
@app.route('/leaderboard/gm')
def lb_gm():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # User's current group
    cur = db.execute('select groupname from profiles where username = ?', [username])
    groupnames = [row[0] for row in cur.fetchall()]
    groupname = groupnames[0]

    # User's current group information
    cur = db.execute('select username, paid from profiles where groupname = ?', [groupname])
    users = [dict(username=row[0], paid=row[1], realname=get_realname(row[0]), userealname=get_namepref(row[0])) for row in cur.fetchall()]
    cur = db.execute('select points.* from points, profiles where points.username = profiles.username and profiles.groupname = ?', [groupname])
    points = [dict(username=row[0], point=row[1], level=row[2]) for row in cur.fetchall()]
    points_sorted = sorted(points, key = itemgetter('point'),  reverse = True)

    return render_template('leaderboard_gm.html', groupname = groupname, users = users, points = points_sorted)
    
# Leaderboard for all members
@app.route('/leaderboard/am')
def lb_am():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # All users
    cur = db.execute('select username, paid from profiles')
    users = [dict(username=row[0], paid=row[1], realname=get_realname(row[0]), userealname=get_namepref(row[0])) for row in cur.fetchall()]

    # All users' information
    cur = db.execute('select * from points where username != ? and point != 0', [USERNAME])
    points = [dict(username=row[0], point=row[1], level=row[2]) for row in cur.fetchall()]
    points_sorted = sorted(points, key = itemgetter('point'),  reverse = True)
    
    return render_template('leaderboard_am.html', users = users, points = points_sorted)

# Leaderboard for all groups
@app.route('/leaderboard/gt')
def lb_gt():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # All groups ranked by their weekly points
    cur = db.execute('select * from groups')
    groups = [dict(gid=row[0], groupname=row[1], desc=row[2], size=row[3], weeklypoints=0, avgweeklypoints=0) for row in cur.fetchall()]
    for group in groups:
        thisgroupname = group['groupname'] # This groupname
        cur = db.execute('select username from profiles where groupname = ?', [thisgroupname])
        users = [row[0] for row in cur.fetchall()] # All users in this group
        for user in users:
            cur = db.execute('select newpoints, year, month, day from activities where username = ?', [user])
            activities = [dict(newpoints=row[0], year=row[1], month=row[2], day=row[3]) for row in cur.fetchall()]
            for activity in activities:
                if check_sameweek(activity['month'], activity['day'], activity['year']):
                   group['weeklypoints'] +=  activity['newpoints']
        if int(group['size']) != 0:
            group['avgweeklypoints'] = group['weeklypoints'] / int(group['size'])
    groups_sorted= sorted(groups, key = itemgetter('weeklypoints'),  reverse = True)

    return render_template('leaderboard_gt.html', groups = groups_sorted)

# Leaderboard for all groups
@app.route('/leaderboard/ga')
def lb_ga():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # All groups ranked by their weekly points
    cur = db.execute('select * from groups')
    groups = [dict(gid=row[0], groupname=row[1], desc=row[2], size=row[3], weeklypoints=0, avgweeklypoints=0) for row in cur.fetchall()]
    for group in groups:
        thisgroupname = group['groupname'] # This groupname
        cur = db.execute('select username from profiles where groupname = ?', [thisgroupname])
        users = [row[0] for row in cur.fetchall()] # All users in this group
        for user in users:
            cur = db.execute('select newpoints, year, month, day from activities where username = ?', [user])
            activities = [dict(newpoints=row[0], year=row[1], month=row[2], day=row[3]) for row in cur.fetchall()]
            for activity in activities:
                if check_sameweek(activity['month'], activity['day'], activity['year']):
                   group['weeklypoints'] +=  activity['newpoints']
        if int(group['size']) != 0:
            group['avgweeklypoints'] = group['weeklypoints'] / int(group['size'])
    groups_sorted= sorted(groups, key = itemgetter('avgweeklypoints'),  reverse = True)

    return render_template('leaderboard_ga.html', groups = groups_sorted)




################
# Edit profile #
################

@app.route('/profile_home')
def profile_home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template('profile_home.html', activities = activity_feed())

@app.route('/edit_profile')
def edit_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')
    password = session.get('password')

    # User profile from the db
    cur = db.execute('select * from profiles where username = ?', [username])
    profiles = [dict(isready=row[0], email=row[1], firstname=row[3], lastname=row[4], age=row[5], sex=row[6], department=row[7])
                for row in cur.fetchall()]
    profile = profiles[0]
    session['email'] = profile['email']
    
    return render_template('edit_profile.html', password = password, profile = profile, activities = activity_feed())

# Update profile (form submit callback)
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    error = None
    username = session.get('username')
    password = session.get('password')
    oldpassword = request.form['oldpassword']
    newpassword = request.form['newpassword']
    renewpassword = request.form['renewpassword']

    # Check old password
    if (error == None) and (oldpassword != password):
        error = 'Incorrect old password'
    # Check new password match
    if (error == None) and (newpassword != renewpassword):
        error = 'New passwords do not match'
    # Check new password length
    [isValid, pwerror] = check_password(newpassword)
    if (error == None) and (not isValid):
        error = pwerror
    # Check if new password is valid
    if (error == None) and (newpassword == oldpassword):
        error = 'You did not pick a NEW password'

    # If all checks passed
    if error == None:
        session['password'] = newpassword
        
        db.execute('update users set password = ? where username = ?',
                   [str(newpassword), username] )
        db.commit()
        flash('You have successfully updated your password')
        return redirect(url_for('home'))
    else:
        flash(error)
        return redirect(url_for('edit_profile'))




#############
# Edit name #
#############

@app.route('/edit_name')
def edit_name():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # User profile from the db
    cur = db.execute('select isready, firstname, lastname, userealname from profiles where username = ?', [username])
    profiles = [dict(isready=row[0], firstname=row[1], lastname=row[2], userealname=row[3]) for row in cur.fetchall()]
    profile = profiles[0]
    return render_template('edit_name.html', profile = profile, activities = activity_feed())

# Update name (form submit callback)
@app.route('/update_name', methods=['POST'])
def update_name():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    error = None
    username = session.get('username')
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    userealname = 'false'

    # Check if firstname/lastname is valid
    isValid = check_realname(firstname)
    if (error == None) and (not isValid):
        error = 'Invalid first name'
    isValid = check_realname(lastname)
    if (error == None) and (not isValid):
        error = 'Invalid last name'

    # If all checks passed
    if error == None:
        if request.form['userealname'] == '1':
            userealname = 'true'
        db.execute('update profiles set firstname = ?, lastname = ?, userealname = ? where username = ?',
                   [str(firstname), str(lastname), userealname, username])
        db.commit()
        flash('You have successfully updated your name preference')
        return redirect(url_for('profile_home'))
    else:
        flash(error)
        return redirect(url_for('edit_name'))




###############
# Edit avatar #
###############

@app.route('/edit_avatar')
def edit_avatar():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')
    
    owl_all = [dict(iid=i, imagepath='') for i in range(0, 12)]
    item1 = owl_all[0]
    item2 = owl_all[1]
    item3 = owl_all[2]
    item4 = owl_all[3]
    item5 = owl_all[4]
    item6 = owl_all[5]
    item7 = owl_all[6]
    item8 = owl_all[7]
    item9 = owl_all[8]
    item10 = owl_all[9]
    item11 = owl_all[10]
    item12 = owl_all[11]
    item1['imagepath'] = 'static/avatar/Owls/black_owl_template.png'
    item2['imagepath'] = 'static/avatar/Owls/blue_owl_template.png'
    item3['imagepath'] = 'static/avatar/Owls/gray_owl_template.png'
    item4['imagepath'] = 'static/avatar/Owls/green_owl_template.png'
    item5['imagepath'] = 'static/avatar/Owls/orange_owl_template.png'
    item6['imagepath'] = 'static/avatar/Owls/pink_owl_template.png'
    item7['imagepath'] = 'static/avatar/Owls/purple_owl_template.png'
    item8['imagepath'] = 'static/avatar/Owls/red_owl_template.png'
    item9['imagepath'] = 'static/avatar/Owls/standard_owl_template.png'
    item10['imagepath'] = 'static/avatar/Owls/violet_owl_template.png'
    item11['imagepath'] = 'static/avatar/Owls/white_owl_template.png'
    item12['imagepath'] = 'static/avatar/Owls/yellow_owl_template.png'

    glasses_all = [dict(iid=i, imagepath='') for i in range(0, 10)]
    item1 = glasses_all[0]
    item2 = glasses_all[1]
    item3 = glasses_all[2]
    item4 = glasses_all[3]
    item5 = glasses_all[4]
    item6 = glasses_all[5]
    item7 = glasses_all[6]
    item8 = glasses_all[7]
    item9 = glasses_all[8]
    item10 = glasses_all[9]
    item1['imagepath'] = 'static/avatar/Glasses/cyclops_laser_goggles.png'
    item2['imagepath'] = 'static/avatar/Glasses/goggles.png'
    item3['imagepath'] = 'static/avatar/Glasses/google_goggles.png'
    item4['imagepath'] = 'static/avatar/Glasses/harry_potter_glasses.png'
    item5['imagepath'] = 'static/avatar/Glasses/mascara.png'
    item6['imagepath'] = 'static/avatar/Glasses/nerd_glasses.png'
    item7['imagepath'] = 'static/avatar/Glasses/phantom_mask.png'
    item8['imagepath'] = 'static/avatar/Glasses/pirate_patch.png'
    item9['imagepath'] = 'static/avatar/Glasses/sunglasses.png'
    item10['imagepath'] = 'static/avatar/Glasses/white_bar_glasses.png'

    return render_template('edit_avatar.html', owl_all = owl_all, glasses_all = glasses_all)

# Update avatar (form submit callback)
@app.route('/update_avatar', methods=['POST'])
def update_avatar():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    error = None

    owl_img_num = request.form['owl_img_num']
    glasses_img_num = request.form['glasses_img_num']
    flash(owl_img_num)
    flash(glasses_img_num)
    
    return redirect(url_for('edit_avatar'))
    #return render_template('test.html', glasses_img_num = glasses_img_num, owl_img_num = owl_img_num)



################
# Manage group #
################

@app.route('/manage_group')
def manage_group():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')

    # User's current group
    cur = db.execute('select groupname from profiles where username = ?', [username])
    groupnames = [row[0] for row in cur.fetchall()]
    groupname = groupnames[0]
    
    # Fetch all the groups
    cur = db.execute('select * from groups')
    groups = [dict(gid=row[0], groupname=row[1], desc=row[2], size=row[3]) for row in cur.fetchall()]

    # Get user's current gid
    gid = '-1'
    for group in groups:
        if group['groupname'] == groupname:
            gid = group['gid']

    # If this group has been deleted
    cur = db.execute('select * from groups where groupname = ?', [groupname])
    if not cur.fetchall():
        groupname = 'Invalid_group'
        db.execute('update profiles set groupname = ? where username = ?', ['Invalid_group', username])
        db.commit()
        
    return render_template('manage_group.html', groups = groups, groupname = groupname,
                           gid = gid, activities = activity_feed())

# form submit callback for manage group
@app.route('/submit_manage_group', methods=['POST'])
def submit_manage_group():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')
    gid = request.form['gid']
    
    if request.form['manage'] == 'join':
        # Get the user's new group name and size
        cur = db.execute('select groupname, size from groups where id = ?', [gid])
        groups = [dict(groupname=row[0], size=row[1]) for row in cur.fetchall()]
        group = groups[0]
        # Get the user's old group name
        cur = db.execute('select groupname from profiles where username = ?', [username])
        groupnames = [row[0] for row in cur.fetchall()]
        groupname = groupnames[0]
        if groupname == group['groupname']:    # If it is the same group
            flash('You are already in ' + group['groupname'])
        else:
            # Update the new group size
            cur = db.execute('update groups set size = ? where id = ?', [group['size'] + 1, gid])
            db.commit()
            # Get the user's old group size
            cur = db.execute('select size from groups where groupname = ?', [groupname])
            sizes = [row[0] for row in cur.fetchall()]
            if len(sizes) != 0:
                size = sizes[0]
                # Update the old group's size
                cur = db.execute('update groups set size = ? where groupname = ?', [size - 1, groupname])
                db.commit()
            # Update the new group name for the user
            cur = db.execute('update profiles set groupname = ? where username = ?', [group['groupname'], username])
            db.commit()
            flash('You have successfully joined ' + group['groupname'])
        return redirect(url_for('manage_group'))

    elif request.form['manage'] == 'leave':
        # Get the user's old group name
        cur = db.execute('select groupname from profiles where username = ?', [username])
        groupnames = [row[0] for row in cur.fetchall()]
        groupname = groupnames[0]
        # Get the user's old group size
        cur = db.execute('select size from groups where groupname = ?', [groupname])
        sizes = [row[0] for row in cur.fetchall()]
        if len(sizes) != 0:
            size = sizes[0]
            # Update the old group's size
            cur = db.execute('update groups set size = ? where groupname = ?', [size - 1, groupname])
            db.commit()
        # Update the new group name for the user
        cur = db.execute('update profiles set groupname = ? where username = ?', ['Invalid_group', username])
        db.commit()
        flash('You have successfully left ' + groupname)
        return redirect(url_for('manage_group'))

    elif request.form['manage'] == 'edit':
        session['gid'] = gid
        session['newgrp'] = False
        return redirect(url_for('create_group'))
        
    elif request.form['manage'] == 'delete':
        if not session.get('admin'):
            flash('You do not have the premission to delete groups')
        else:
            db.execute('delete from groups where id = ?', [gid])
            db.commit()
            flash('Group deleted')
        return redirect(url_for('manage_group'))

    elif request.form['manage'] == 'view':
        return redirect(url_for('view_group', gid = gid))
    
    else:
        flash('Invalid action')
        return redirect(url_for('manage_group'))

# Create group
@app.route('/create_group', methods=['Get', 'POST'])
def create_group():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    if session.get('newgrp'):
        return render_template('create_group.html', newgrp = True, activities = activity_feed())
    else:
        session['newgrp'] = True
        cur = db.execute('select * from groups where id = ?', [session.get('gid')])
        thisgrps = [dict(gid=row[0], groupname=row[1], desc=row[2]) for row in cur.fetchall()]
        thisgrp = thisgrps[0]
        return render_template('create_group.html', newgrp = False, thisgrp = thisgrp, activities = activity_feed())

# form submit callback for create group
@app.route('/submit_create_group', methods=['POST'])
def submit_create_group():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')
    name = str(request.form['name'])
    desc = str(request.form['desc'])
    error = None

    # Check if this groupname is valid
    [isValid, gnerror] = check_name(name)
    if (error == None) and (not isValid):
        error = 'Group name' + gnerror 

    # Check if this description is valid
    if (error == None) and (len(desc) == 0):
        error = 'Group description cannot be empty'
    if (error == None) and (len(desc) > 100):
        error = 'Group description is too long'
    if (error == None) and (name == 'Invalid_group'):
        error = 'Invalid groupname'
    
    # Check if this groupname has been in the db
    if request.form['thisform'] == 'create':
        cur = db.execute('select * from groups where groupname = ?', [name])
        groups = [row[0] for row in cur.fetchall()]
        if (error == None) and (len(groups) != 0):
            error = 'This group name has been taken. Try another one'

    if (error == None):
        if request.form['thisform'] == 'create':
            db.execute('insert into groups (groupname, desc, size) values (?, ?, ?)', [str(name), str(desc), 0])
            db.commit()
            flash('You have successfully create a group ' + name)
            return redirect(url_for('manage_group'))
        elif request.form['thisform'] == 'update':
            cur = db.execute('select groupname from groups where id = ?', [session.get('gid')])
            oldgroupnames = [row[0] for row in cur.fetchall()]
            oldgroupname = oldgroupnames[0]
            # Update user's groupname
            db.execute('update profiles set groupname = ? where groupname = ?', [str(name), oldgroupname])
            db.commit()
            # Update group information
            db.execute('update groups set groupname = ?, desc = ? where id = ?', [str(name), str(desc), session.get('gid')])
            db.commit()
            flash('Group updated')
            session['newgrp'] = True
            session['gid'] = '-1'
            return redirect(url_for('manage_group'))
        else:
            flash('Invalid action')
            return redirect(url_for('manage_group'))
    else:
        flash(error)
        if request.form['thisform'] == 'create':
            return redirect(url_for('create_group'))
        else:
            return redirect(url_for('manage_group'))




#################
# Edit activity #
#################

@app.route('/edit_activity')
def edit_activity():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    if session.get('admin'):
        cur = db.execute('select * from activities order by id desc')
        myactivities = [dict(aid=row[0], username=row[1], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                           low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13],
                             hour=row[14], minute=row[15], second=row[16]) for row in cur.fetchall()]
    else:
        cur = db.execute('select * from activities where username = ? and isthisweek = 1 order by id desc', [session.get('username')])
        myactivities = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                           low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13],
                             hour=row[14], minute=row[15], second=row[16]) for row in cur.fetchall()]
    
    return render_template('edit_activity.html', myactivities = myactivities, activities = activity_feed())

# form submit callback
@app.route('/submit_edit_activity', methods=['POST'])
def submit_edit_activity():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    aid = request.form['aid']
    
    if request.form['manage'] == 'edit':
        session['aid'] = aid
        session['newact'] = False
        return redirect(url_for('report_activity'))
    elif request.form['manage'] == 'delete':
        aid = request.form['aid']
        db.execute('delete from activities where id = ?', [aid])
        db.commit()
        flash('Activity deleted')
    else:
        flash('Invalid action')
    return redirect(url_for('home'))




############################
# View all past activities #
############################

@app.route('/past_activity')
def past_activity():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    if session.get('admin'):
        cur = db.execute('select * from activities order by id desc')
        myactivities = [dict(aid=row[0], username=row[1], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                           low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13],
                             hour=row[14], minute=row[15], second=row[16], happiness=row[17], activeness=row[18]) for row in cur.fetchall()]
    else:
        cur = db.execute('select * from activities where username = ? and isthisweek = 0 order by id desc', [session.get('username')])
        myactivities = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                           low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13],
                             hour=row[14], minute=row[15], second=row[16], happiness=row[17], activeness=row[18]) for row in cur.fetchall()]
    
    return render_template('past_activity.html', myactivities = myactivities, activities = activity_feed())




###################
# Report activity #
###################

@app.route('/report_activity')
def report_activity():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    username = session.get('username')
    
    # All past activities for the user
    [intensity_weekday, points_weekday, points_week, low_week, moderate_week, high_week, tweek, weeks, social, activity_type] \
                            = prepare_data.past_activities(DATABASE, username)

    activity_type_sorted = sorted(activity_type, key = itemgetter('times'),  reverse = True)
    td = datetime.datetime.now()
    wkd = td.weekday()
        
    if session.get('newact'): # Report a new activity
        return render_template('report_activity.html', newact = True, activity_type = activity_type_sorted, \
                               wkd = int(td.weekday()), year = int(td.year), month = int(td.month), day = int(td.day))
    else:  # Update an old activity
        session['newact'] = True
        cur = db.execute('select * from activities where id = ?', [session.get('aid')])
        thisacts = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                         low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13],
                             hour=row[14], minute=row[15], second=row[16], happiness=row[17], activeness=row[18]) for row in cur.fetchall()]
        thisact = thisacts[0]
        return render_template('report_activity.html', newact = False, wkd = int(td.weekday()), thisact = thisact)

# Submit activity (form submit callback)
@app.route('/submit_activity', methods=['POST'])
def submit_activity():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    error = None
    
    db = get_db()
    username = session.get('username')
    activity_str = request.form['activity']
    low_str = request.form['low']
    moderate_str = request.form['moderate']
    high_str = request.form['high']
    ppl_str = request.form['ppl']
    note = str(request.form['note'])
    #rate = request.form['rate'] # Currently replaced by happiness and activeness
    rate = -1
    happiness = request.form['happiness']
    activeness = request.form['activeness']

    
    # Get date information
    rwkd_str = request.form['date'] # Reported weekday
    #rwkd = weekday_decode(rwkd_str)
    rwkd = int(rwkd_str)
    td = date.today()
    twkd = td.weekday() # Today as weekday
    rd = td + datetime.timedelta(days = (rwkd - twkd))
    year_str = rd.year
    month_str = rd.month
    day_str = rd.day

    # Get time information
    rtime = request.form['time'] # Reported time
    ampm = request.form['ampm']
    hour = int(rtime) / 2 + 12 * int(ampm)
    minute = (int(rtime) % 2) * 30
    second = 0
    #flash(datetime.time(hour, minute, second))

    # Get activity name
    if request.form['thisform'] == 'report' and activity_str == 'New':
        activity = request.form['new_activity']
    else:
        activity = activity_str
    
    # Need to check the data formart
    [isValid, dateerror] = check_date(month_str, day_str, year_str)
    if (error == None) and not isValid:
        error = dateerror
    [isValid, timeerror] = check_time(hour, minute, second)
    if (error == None) and not isValid:
        error = timeerror
    if (error == None) and len(low_str) == 0 and len(moderate_str) == 0 and len(high_str) == 0:
        error = 'Nothing was reported'
    if (error == None) and len(low_str) == 0:
        low_str = '0'
    if (error == None) and len(moderate_str) == 0:
        moderate_str = '0'
    if (error == None) and len(high_str) == 0:
        high_str = '0'
    if (error == None) and (not str(low_str).isdigit() or not str(moderate_str).isdigit() or not str(high_str).isdigit()):
        error = 'Invalid intensity'
    if (error == None) and (float(low_str) + float(moderate_str) + float(high_str) == 0):
        error = 'Nothing was reported'
    if (error == None) and (str(activity).isdigit()):
        error = 'Activity cannot be all digits'
    if (error == None) and (len(activity) == 0):
        error = 'Invalid activity'
    if (error == None) and (len(activity) > 100):
        error = 'Activity is too long'
    if (error == None) and len(ppl_str) == 0:
        ppl_str = '0'
    if (error == None) and not str(ppl_str).isdigit():
        error = 'Invalid number of participants'


    if error == None:
        year = int(year_str)
        month = int(month_str)
        day = int(day_str)
        low = float(low_str)
        moderate = float(moderate_str)
        high = float(high_str)
        ppl = int(ppl_str)
        if len(note) == 0:
            note = ' '

        # Calculate points for this activity
        cur = db.execute('select level from points where username = ?', [username])
        levels = [row[0] for row in cur.fetchall()]
        level = levels[0]
        #newpoints = (low / 45 + moderate / 30 + high / 20) * 100 * (1 + (level-1) * 0.1)
        newpoints = (low / 45 + moderate / 30 + high / 20) * 100
        newpoints = int(newpoints)
        if ppl > 0:
            newpoints = newpoints + 10

        # Add/update activity to the db
        if request.form['thisform'] == 'report':
            db.execute('insert into activities (username, year, month, day, activity, ppl, low, moderate, high, newpoints, \
                       isthisweek, note, rate, hour, minute, second, happiness, activeness) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', \
                       [session.get('username'), year, month, day, activity, ppl, int(low), int(moderate), int(high), newpoints, \
                        1, note, rate, hour, minute, second, happiness, activeness])
            db.commit()
            flash('New activity was successfully reported')
            flash('You just earned ' + str(int(newpoints)) + ' points')
            return redirect(url_for('home'))
        else:
            db.execute('update activities set year=?, month=?, day=?, activity=?, ppl=?, low=?, moderate=?, high=?, newpoints=?, \
                        note=?, rate=?, hour=?, minute=?, second=?, happiness=?, activeness=? where id=?', \
                       [year, month, day, activity, ppl, int(low), int(moderate), int(high), newpoints, \
                        note, rate, hour, minute, second, happiness, activeness, session.get('aid')])
            db.commit()
            flash('Activity updated')
            session['newact'] = True
            session['aid'] = '-1'
            return redirect(url_for('home'))
        
    else:
        flash(error)
        if request.form['thisform'] == 'report':
            return redirect(url_for('report_activity'))
        else:
            return redirect(url_for('edit_activity'))



############################
# Manage user (admin only) #
############################

@app.route('/manage_user')
def manage_user():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not session.get('admin'):
        abort(401)

    db = get_db()

    cur = db.execute('select * from users where username != ?', ['admin'])
    users = [dict(uid=row[0], username=row[1], password=row[2]) for row in cur.fetchall()]
    cur = db.execute('select username, email, groupname from profiles')
    profiles = [dict(username=row[0], email=row[1], groupname=row[2]) for row in cur.fetchall()]

    return render_template('manage_user.html', users = users, profiles = profiles, activities = activity_feed())

# form submit callback
@app.route('/submit_manage_user', methods=['POST'])
def submit_manage_user():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not session.get('admin'):
        abort(401)

    db = get_db()
    
    uid = request.form['user']
    cur = db.execute('select username from users where id = ?', [uid])
    usernames = [row[0] for row in cur.fetchall()]
    username = usernames[0]


    # Update group size
    cur = db.execute('select groupname from profiles where username = ?', [username])
    groupnames = [row[0] for row in cur.fetchall()]
    groupname = groupnames[0]
    if groupname != 'Invalid_group':
        cur = db.execute('select size from groups where groupname = ?', [groupname])
        sizes = [row[0] for row in cur.fetchall()]
        db.execute('update groups set size = ? where groupname = ?', [sizes[0]-1, groupname])
        db.commit()
    
    # delete profile
    db.execute('delete from profiles where username = ?', [username])
    db.commit()

    # delete point
    db.execute('delete from points where username = ?', [username])
    db.commit()
    
    # delete user
    db.execute('delete from users where id = ?', [uid])
    db.commit()

    flash('User deleted')
    return redirect(url_for('manage_user'))


#############################
# Login/Logout and Register #
#############################

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        db = get_db()

        # Get user
        cur = db.execute('select username, password from users where username = ?', [request.form['username']])
        entries = [dict(username = row[0], password = row[1])for row in cur.fetchall()]

        if len(entries) == 0:
            error = 'This username does not exist'
        else:
            for entry in entries:
                # Check password
                if str(entry['password']) != str(request.form['password']):
                    error = 'Incorrect password'
                    break

        # Log in user
        if error == None:
            session['logged_in'] = True
            session['username'] = request.form['username']
            session['password'] = request.form['password']
            session['newact'] = True
            session['newgrp'] = True
            session['aid'] = '-1'
            session['gid'] = '-1'
            # Admin user
            if request.form['username'] == USERNAME:
                session['admin'] = True
            else:
                session['admin'] = False

            # Clear all user points, update all levels, freeze all activities, if this is the first global login in a week
            cur = db.execute('select * from login')
            logins = [dict(year=row[0], month=row[1], day=row[2]) for row in cur.fetchall()]
            login = logins[0]
            if not check_sameweek(login['month'], login['day'], login['year']): # If this is the first global login
                # Update last global login
                td = datetime.datetime.now()
                db.execute('update login set year=?, month=?, day=?', [int(td.year), int(td.month), int(td.day)])
                db.commit()
                # Update all activities
                cur = db.execute('select id, year, month, day from activities')
                activities = [dict(id=row[0], year=row[1], month=row[2], day=row[3]) for row in cur.fetchall()]
                for activity in activities:
                    if not check_sameweek(activity['month'], activity['day'], activity['year']):
                        db.execute('update activities set isthisweek = 0 where id = ?', [activity['id']])
                        db.commit()
                # Update all user points and level
                cur = db.execute('select * from points')
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
                    db.execute('update points set point=?, level=? where username=?', [0, level_new, point['username']])
                    db.commit()

            cur = db.execute('select * from points where username = ?', [request.form['username']])
            mypoints = [dict(point=row[1], level=row[2], year=row[3], month=row[4], day=row[5]) for row in cur.fetchall()]
            mypoint = mypoints[0]
            flash('You were logged in as ' + session['username'])
            flash('Your last login was ' + str(mypoint['month']) + '/' + str(mypoint['day']) + '/' + str(mypoint['year']))
            # Update last login date
            td = datetime.datetime.now()
            db.execute('update points set year=?, month=?, day=? where username=?',
                        [int(td.year), int(td.month), int(td.day), session['username']])
            db.commit()
            
            return redirect(url_for('home'))
    
    return render_template('login.html', error = error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':

        # Get the db object
        db = get_db()

        # Check if the username is valid
        [isValid, unerror] = check_name(request.form['username'])
        if (error == None) and (not isValid):
            error = 'Username' + unerror

        # Check if this username has been in the db
        cur = db.execute('select username, password from users where username = ?',
                         [request.form['username']])
        entries = [dict(username = row[0], password = row[1]) for row in cur.fetchall()]
        for entry in entries:
            if (error == None) and (len(entries) != 0):
                error = "This username has been taken. Try another one"
                break

        # Check password match
        if (error == None) and (request.form['password'] != request.form['repassword']):
            error = 'Passwords do not match'

        # Check password
        [isValid, pwerror] = check_password(request.form['password'])
        if (error == None) and (not isValid):
            error = pwerror

        # Check email
        if (error == None) and (not '@' in request.form['email']):
            error = 'Invalid email address'

        # Check if this email has been in the db
        cur = db.execute('select * from profiles where email = ?',
                         [request.form['email']])
        entries = [dict(email = row[2]) for row in cur.fetchall()]
        for entry in entries:
            if (error == None) and (len(entries) != 0):
                error = "This email has been used"
                break

        # Check terms of use
        if (error == None) and (not request.form['ischecked'] == 'Yes'):
            error = 'You must agree the terms of use to register'
        
        # Register a new user
        if error == None:
            # Initialize user password
            db.execute('insert into users (username, password) values (?, ?)',
                       [request.form['username'], str(request.form['password'])])
            db.commit()
            # Initialize profile
            db.execute('insert into profiles (isready, email, username, firstname, lastname, age, sex, department, groupname) values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       ['false', request.form['email'], request.form['username'], '', '', '0', 'male', 'ECE', 'Invalid_group'])
            db.commit()
            # Initialize point
            td = datetime.datetime.now()
            db.execute('insert into points (username, point, level, year, month, day) values (?, ?, ?, ?, ?, ?)',
                       [request.form['username'], 0, 1, int(td.year), int(td.month), int(td.day)])
            db.commit()
            flash('You have successfully registered. Now you can log in')
            return redirect(url_for('login'))
    
    return render_template('register.html', error = error)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('password', None)
    session.pop('email', None)
    session.pop('admin', None)
    session.pop('newact', None)
    session.pop('newgrp', None)
    session.pop('aid', None)
    session.pop('gid', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))



#####################
# Password recovery #
#####################

@app.route('/recover', methods=['GET', 'POST'])
def recover():
    return render_template('recover.html')

# Recover password (form submit callback)
@app.route('/recover_password', methods=['POST'])
def recover_password():
    # Get the db object
    db = get_db()

    error = None
    email = request.form['email']

    # Check email
    if (error == None) and (not '@' in email):
        error = 'Invalid email address'
            
    # Get username from email
    cur = db.execute('select * from profiles where email = ?', [email])
    usernames = [row[2] for row in cur.fetchall()]

    if (error == None) and (len(usernames) == 0):
        error = 'This email has not been used'

    if error == None:
        username = usernames[0]
        # Get password from username
        cur = db.execute('select password from users where username = ?', [username])
        passwords = [row[0] for row in cur.fetchall()]
        password = passwords[0]
        # Try to send the email
        TEXT = 'This is an automatic email from OWLympics, please do not directly reply.' + '\r\n' + 'Your username is: ' + str(username) + '\r\n' + 'Your password is: ' + str(password)
        TO = [email]
        isSent = autoemail.send_email(TEXT, TO)
        if isSent:
            flash('An email has been sent to ' + email)
        else:
            flash('Your email ' + email + ' cannot be reached')
        return redirect(url_for('login'))

    flash(error)
    return redirect(url_for('recover'))




##################
# Universal urls #
##################

# Show an user's information and activity
@app.route('/view_user/<int:uid>', methods=['GET', 'POST'])
def view_user(uid):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    # Get username based on uid
    cur = db.execute('select username from users where id = ?', [uid])
    usernames = [row[0] for row in cur.fetchall()]
    if len(usernames) == 0:
        abort(401)
    username = usernames[0]

    # Get points and level
    cur = db.execute('select point, level from points where username = ?', [username])
    points = [dict(point=row[0], level=row[1]) for row in cur.fetchall()]
    point = points[0]

    # Get groupname
    cur = db.execute('select groupname from profiles where username = ?', [username])
    groupnames = [row[0] for row in cur.fetchall()]
    groupname = groupnames[0]

    # Get all activities for this username
    cur = db.execute('select * from activities where username = ? and isthisweek = 1 order by id desc', [username])
    myactivities = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                         low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12]) for row in cur.fetchall()]

    return render_template('view_user.html', username = username, point = point, groupname = groupname,
                           myactivities = myactivities)

# Show an user's information and activity
@app.route('/view_username/<string:username>', methods=['GET', 'POST'])
def view_username(username):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    # Get points and level
    cur = db.execute('select point, level from points where username = ?', [username])
    points = [dict(point=row[0], level=row[1]) for row in cur.fetchall()]
    if len(points) == 0:
        abort(401)
    point = points[0]

    # Get real name
    cur = db.execute('select firstname, lastname from profiles where username = ?', [username])
    realnames = [dict(firstname=row[0], lastname=row[1]) for row in cur.fetchall()]
    realname = realnames[0]
    
    # Get groupname
    cur = db.execute('select groupname from profiles where username = ?', [username])
    groupnames = [row[0] for row in cur.fetchall()]
    groupname = groupnames[0]
    if groupname == 'Invalid_group':
        groupname = 'Not in a group'
    
    # Get all activities for this username
    cur = db.execute('select * from activities where username = ? and isthisweek = 1 order by id desc', [username])
    myactivities = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                         low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12]) for row in cur.fetchall()]

    return render_template('view_user.html', username = username, point = point, groupname = groupname, realname = realname,
                           myactivities = myactivities)

# Show a group's information
@app.route('/view_group/<int:gid>', methods=['GET', 'POST'])
def view_group(gid):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    # Get groupname based on gid
    cur = db.execute('select groupname from groups where id = ?', [gid])
    groupnames = [row[0] for row in cur.fetchall()]
    if len(groupnames) == 0:
        abort(401)
    groupname = groupnames[0]
    
    # Get all users for this groupname
    cur = db.execute('select username, paid from profiles where groupname = ?', [groupname])
    users = [dict(username=row[0], paid=row[1], realname=get_realname(row[0]), userealname=get_namepref(row[0])) for row in cur.fetchall()]
    cur = db.execute('select points.* from points, profiles where points.username = profiles.username and profiles.groupname = ?', [groupname])
    points = [dict(username=row[0], point=row[1], level=row[2]) for row in cur.fetchall()]
    
    points_sorted = sorted(points, key = itemgetter('point'),  reverse = True)

    return render_template('view_group.html', groupname = groupname,
                           users = users, points = points_sorted)

# Show an activity
@app.route('/view_activity/<int:aid>', methods=['GET', 'POST'])
def view_activity(aid):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    # Get activity based on aid
    cur = db.execute('select * from activities where id = ?', [aid])
    thisacts = [dict(aid=row[0], username=row[1], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6],
                     low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12]) for row in cur.fetchall()]
    thisact = thisacts[0]

    return render_template('view_activity.html', thisact = thisact)

# Show an user's charts and compare with another user
@app.route('/view_chart/<string:username>', methods=['GET', 'POST'])
def view_chart(username):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    me = session.get('username')

    ### Statistics for username ###
    
    # Get the list of activities
    cur = db.execute('select newpoints from activities where username = ? and isthisweek = 1', [username])
    newpoints = [row[0] for row in cur.fetchall()]
    points = sum(newpoints)
    level_ind = 'red'
    points_more_same = 200 - points
    points_more_next = 400 - points
    if points_more_same < 0:
        points_more_same = 0
        level_ind = 'yellow'
    if points_more_next < 0:
        points_more_next = 0
        level_ind = 'green'

    # Get the user level from the db
    cur = db.execute('select * from points where username = ?', [username])
    levels = [row[2] for row in cur.fetchall()]
    level = levels[0]

    # Get all past activities
    [intensity_weekday, points_weekday, points_week, low_week, moderate_week, high_week, tweek, weeks, social, activity_type] \
                            = prepare_data.past_activities(DATABASE, username)

    # Average points in the past four weeks
    avg_points_week = (points_week[tweek-4] + points_week[tweek-3] + points_week[tweek-2] + points_week[tweek-1]) / 4

    # Max points in the past four weeks
    max_points_week = max([points_week[tweek-4], points_week[tweek-3], points_week[tweek-2], points_week[tweek-1]])

    # Total points in the entire history
    total_points_week = sum(points_week)

    ### Statistics for me ###
    
    # Get the list of activities
    cur = db.execute('select newpoints from activities where username = ? and isthisweek = 1', [me])
    newpoints_me = [row[0] for row in cur.fetchall()]
    points_me = sum(newpoints_me)
    level_ind_me = 'red'
    points_more_same_me = 200 - points_me
    points_more_next_me = 400 - points_me
    if points_more_same_me < 0:
        points_more_same_me = 0
        level_ind_me = 'yellow'
    if points_more_next_me < 0:
        points_more_next_me = 0
        level_ind_me = 'green'

    # Get the user level from the db
    cur = db.execute('select * from points where username = ?', [me])
    levels_me = [row[2] for row in cur.fetchall()]
    level_me = levels_me[0]

    # Get all past activities
    [intensity_weekday_me, points_weekday_me, points_week_me, low_week_me, moderate_week_me, high_week_me, tweek, weeks_me, social_me, activity_type_me] \
                            = prepare_data.past_activities(DATABASE, me)

    # Average points in the past four weeks
    avg_points_week_me = (points_week_me[tweek-4] + points_week_me[tweek-3] + points_week_me[tweek-2] + points_week_me[tweek-1]) / 4

    # Max points in the past four weeks
    max_points_week_me = max([points_week_me[tweek-4], points_week_me[tweek-3], points_week_me[tweek-2], points_week_me[tweek-1]])

    # Total points in the entire history
    total_points_week_me = sum(points_week_me)
    
    return render_template('view_chart.html',
                            points = points, points_more_same = points_more_same, points_more_next = points_more_next,
                            level_ind = level_ind, level = level,
                            points_week = points_week, points_weekday = points_weekday, intensity_weekday = intensity_weekday,
                            avg_points_week = avg_points_week, max_points_week = max_points_week, total_points_week = total_points_week,
                            low_week = low_week, moderate_week = moderate_week, high_week = high_week, tweek = tweek, weeks = weeks, social = social,
                            activity_type = activity_type,
                            \
                            points_me = points_me, points_more_same_me = points_more_same_me, points_more_next_me = points_more_next_me,
                            level_ind_me = level_ind_me, level_me = level_me,
                            points_week_me = points_week_me, points_weekday_me = points_weekday_me, intensity_weekday_me = intensity_weekday_me,
                            avg_points_week_me = avg_points_week_me, max_points_week_me = max_points_week_me, total_points_week_me = total_points_week_me,
                            low_week_me = low_week_me, moderate_week_me = moderate_week_me, high_week_me = high_week_me, social_me = social_me,
                            activity_type_me = activity_type_me,
                            \
                            activities = activity_feed(),
                            username = username, me = me
                            )




###########################################
# Handle the requests from the mobile app #
###########################################

# Registration request
@app.route('/mobile/register', methods=['POST'])
def mobile_register():
    
    # Get database
    db = get_db()
    
    # Retrieve the information from the request
    username = request.form['username']
    password = request.form['password']
    uuid = request.form['uuid']
   
    # Authenticate the user
    cur = db.execute('select username, password from users where username = ?', [username])
    entries = [dict(username=row[0], password=row[1]) for row in cur.fetchall()]
    msg = 'Authentication succeeded'
    if len(entries) == 0:
        msg = 'This username does not exist'
    else:
        entry = entries[0]
        if str(entry['password']) != str(password):
            msg = 'Incorrect password'
    
    # Add mobileid into the db
    if msg == 'Authentication succeeded':
        db.execute('update profiles set mobileid = ? where username = ?', [uuid, username])
        db.commit()
    
    return msg

# De-association request
@app.route('/mobile/detach', methods=['POST'])
def mobile_detach():

    # Get database
    db = get_db()

    # Retrieve the information from the request
    uuid = request.form['uuid']
    
    # Reset mobileid from the db
    db.execute('update profiles set mobileid = ? where mobileid = ?', ['0', uuid])
    db.commit()

    msg = 'Deauthorization succeeded'
    
    return msg

# Report activity request
@app.route('/mobile/submit', methods=['POST'])
def mobile_submit():

    # Get database
    db = get_db()

    # Retrieve the information from the request
    activity = request.form['exercise']
    # duration = request.form['time']
    low_str = request.form['lowintensity']
    moderate_str = request.form['moderateintensity']
    high_str = request.form['highintensity']
    # partners = request.form['partners']
    # rating = request.form['rating']
    # date = request.form['date']
    year_str = request.form['year']
    month_str = request.form['mon']
    day_str = request.form['day']
    uuid_str = request.form['uuid']
    ppl_str = request.form['social']
    note_str = request.form['note']
    rate_str = request.form['rate']
    hour_str = request.form['hour']
    min_str = request.form['min']
    sec_str = request.form['sec']
    happpiness_str = request.form['happy']
    activeness_str = request.form['activeness']
    

    low = float(low_str)
    moderate = float(moderate_str)
    high = float(high_str)
    ppl = int(ppl_str)
    hour = int(hour_str)
    minute = int(min_str)
    second = int(sec_str)
    happiness = int(happpiness_str)
    activeness = int(activeness_str)
    if len(note) == 0:
        note = ' '

    # Get username from mobileid
    cur = db.execute('select username from profiles where mobileid = ?', [uuid])
    entries = [dict(username=row[0]) for row in cur.fetchall()]
    if len(entries) == 0:
        return 'You have not yet registered'
    else:
        entry = entries[0]
        username = entry['username']
    
    # Information about this activity
    # td = date.today()
    # year = int(td.year)
    year = int(year_str)
    month = int(month_str)
    day = int(day_str)
    # day = int(td.day)
    # ppl = partners
    note = ' '

    # Calculate points for this activity
    cur = db.execute('select level from points where username = ?', [username])
    levels = [row[0] for row in cur.fetchall()]
    level = levels[0]
    #newpoints = (low / 45 + moderate / 30 + high / 20) * 100 * (1 + (level-1) * 0.1)
    newpoints = (low / 45 + moderate / 30 + high / 20) * 100
    newpoints = int(newpoints)
    if ppl > 0:
        newpoints = newpoints + 10

    # Add activity to the db
    # db.execute('insert into activities (username, year, month, day, activity, ppl, low, moderate, high, newpoints, isthisweek, note) values (?,?,?,?,?,?,?,?,?,?,?,?)',
    #             [username, year, month, day, activity, ppl, int(low), int(moderate), int(high), newpoints, 1, note])
    db.execute('insert into activities (username, year, month, day, activity, ppl, low, moderate, high, newpoints, \
                       isthisweek, note, rate, hour, minute, second, happiness, activeness) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', \
                       [session.get('username'), year, month, day, activity, ppl, int(low), int(moderate), int(high), newpoints, \
                        1, note, rate, hour, minute, second, happiness, activeness])
    db.commit()
    msg = 'Activity submission succeeded'

    return msg




# Update the user profile
@app.route('/mobile/profile', methods=['POST'])
def mobile_profile():

    # Get database
    db = get_db()

    # Retrieve the information from the request
    uuid = request.form['uuid']

    # Get username from mobileid
    cur = db.execute('select username from profiles where mobileid = ?', [uuid])
    entries = [dict(username=row[0]) for row in cur.fetchall()]
    if len(entries) == 0:
        return 'You have not yet registered'
    else:
        entry = entries[0]
        username = entry['username']

    # Retrieve the recent activities
    cur = db.execute('select * from activities where username = ? and isthisweek = 1 order by id desc', [username])
    #myactivities = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6], \
    #                    low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13], \
    #                    hour=row[14], minute=row[15], second=row[16]) for row in cur.fetchall()]

    myactivities = [dict(year=row[2], month=row[3], day=row[4], name=row[5], newpoints=row[10]) for row in cur.fetchall()]
    if len(myactivities) > 3:
        acts = myactivities[0:2]
    else:
        acts = myactivities

    # Refresh the user points and retrieve the user level information
    cur = db.execute('select newpoints from activities where username = ? and isthisweek = 1', [username])
    newpoints = [row[0] for row in cur.fetchall()]
    points = sum(newpoints)
    cur = db.execute('update points set point = ? where username = ?', [points, username])
    db.commit()
    cur = db.execute('select * from points where username = ?', [username])
    levels = [row[2] for row in cur.fetchall()]
    level = levels[0]

    data = [ {'points':points, 'level':level, 'acts':acts} ]
    return json.dumps(data)




# Update the user profile
@app.route('/mobile/profile/test', methods=['GET','POST'])
def mobile_profile_test():

    # Get database
    db = get_db()
    username = 'hang'

    # Retrieve the recent activities
    cur = db.execute('select * from activities where username = ? and isthisweek = 1 order by id desc', [username])
    #myactivities = [dict(aid=row[0], year=row[2], month=row[3], day=row[4], activity=row[5], ppl=row[6], \
    #                    low=row[7], moderate=row[8], high=row[9], newpoints=row[10], note=row[12], rate=row[13], \
    #                    hour=row[14], minute=row[15], second=row[16]) for row in cur.fetchall()]

    myactivities = [dict(year=row[2], month=row[3], day=row[4], name=row[5], newpoints=row[10]) for row in cur.fetchall()]
    if len(myactivities) > 3:
        acts = myactivities[0:2]
    else:
        acts = myactivities

    # Refresh the user points and retrieve the user level information
    cur = db.execute('select newpoints from activities where username = ? and isthisweek = 1', [username])
    newpoints = [row[0] for row in cur.fetchall()]
    points = sum(newpoints)
    cur = db.execute('update points set point = ? where username = ?', [points, username])
    db.commit()
    cur = db.execute('select * from points where username = ?', [username])
    levels = [row[2] for row in cur.fetchall()]
    level = levels[0]

    data = [ {'points':points, 'level':level, 'acts':acts} ]
    return json.dumps(data)
    #return HTTPResponse(json.dumps(data), mimetype="application/json")
    #return 'OK'



###################
# Owlympics store #
###################

@app.route('/store', methods=['GET', 'POST'])
def store():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()

    items = [dict(iid=i, imagepath='', category='', desc='', price=0) for i in range(0, 4)]
    item1 = items[0]
    item2 = items[1]
    item3 = items[2]
    item4 = items[3]
    item1['imagepath'] = 'static/avatar/Owls/black_owl_template.png'
    item1['category'] = 'Owls'
    item1['desc'] = 'A classic black owl that everyone likes!'
    item1['price'] = 20000
    item2['imagepath'] = 'static/avatar/Owls/orange_owl_template.png'
    item2['category'] = 'Owls'
    item2['desc'] = 'Have you ever seen an orange owl???'
    item2['price'] = 30000
    item3['imagepath'] = 'static/avatar/Glasses/goggles.png'
    item3['category'] = 'Glasses'
    item3['desc'] = 'Catch a mouse in 2 seconds with this goggle!'
    item3['price'] = 5500
    item4['imagepath'] = 'static/avatar/Hair/fro.png'
    item4['category'] = 'Hair'
    item4['desc'] = 'A bird nest on your head...'
    item4['price'] = 7000
    
    return render_template('store.html', items = items)

# form submit callback
@app.route('/submit_store', methods=['POST'])
def submit_store():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()

    return redirect(url_for('home'))




#######
# Gym #
#######

@app.route('/gym', methods=['GET', 'POST'])
def gym():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    
    return render_template('gym.html', items = items)




#####################
# db related macros #
#####################
def get_realname(username):
    db = get_db()
    username = str(username)
    cur = db.execute('select firstname, lastname from profiles where username = ?', [username])
    realnames = [dict(firstname=row[0], lastname=row[1]) for row in cur.fetchall()]
    if len(realnames) == 0:
        return ''
    else:
        realname = realnames[0]
        return str(realname['firstname']) + ' ' + (realname['lastname'])

def get_namepref(username):
    db = get_db()
    username = str(username)
    cur = db.execute('select userealname from profiles where username = ?', [username])
    userealnames = [dict(use=row[0]) for row in cur.fetchall()]
    if len(userealnames) == 0:
        return 0
    else:
        userealname = userealnames[0]
        if (userealname['use'] == 'true'):
            return 1
        else:
            return 0

def activity_feed():
    db = get_db()
    cur = db.execute('select * from activities order by id desc')
    num_activities = 3
    activities = [dict(aid=row[0], username=row[1], year=row[2], month=row[3], day=row[4], activity=row[5], newpoints=row[10],
                       realname=get_realname(row[1]), userealname=get_namepref(row[1])) for row in cur.fetchall()]
    if len(activities) > num_activities:
        activities = activities[0:num_activities]
    return activities




###########
# Utility #
###########

# Get level based on points
def get_level(points):
    points_up = [0, 300, 700, 1200, 1800,
                 2500, 3300, 4200, 5200, 6300,
                 7500, 8800, 10200, 11700, 13300]
    level = 0
    points_more = 0
    for i in range(0, len(points_up)):
        if points < points_up[i]:
            level = i 
            points_more = points_up[i] - points
            break
    if level == 0:
        level = 100
    return [level, points_more]

# Check if password is valid
def check_password(password):
    isValid = True
    error = None
    password = str(password)
    if len(password) < 4:
        isValid = False
        error = 'Password is too short (need at least 4 letters/digits)'
    return [isValid, error]

# Check if user/group name is valid
def check_name(name):
    isValid = True
    error = None
    name = str(name)
    if (error == None) and len(name) == 0:
        isValid = False
        error = ' cannot be empty'
    if (error == None) and len(name) > 30:
        isValid = False
        error = ' is too long'
    if (error == None) and (' ' in name):
        isValid = False
        error = ' must not contain space'
    if (error == None) and (name.isdigit()):
        isValid = False
        error = ' cannot be all digits'
    return [isValid, error]

# Check if date is valid
def check_date(m, d, y):
  isValid = True
  error = None
  try:
    d = datetime.date(int(y), int(m), int(d))
    td = date.today()
    wkd = td.weekday()
    fd = td - datetime.timedelta(days = wkd)
    if d > td:
        isValid = False
        error = 'Did you time travel from the future???'
    if d < fd and not session.get('admin'):
        isValid = False
        error = 'You can only report activities for this week'
  except ValueError as e:
    isValid = False
    error = 'Please input a valid date'
  return [isValid, error]

# Check if time is valid
def check_time(h, m, s):
  isValid = True
  error = None
  try:
    t = datetime.time(int(h), int(m), int(s))
  except ValueError as e:
    isValid = False
    error = 'Please input a valid time'
  return [isValid, error]

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

# Interpret a weekday
def weekday_decode(wkd_str):
    wkd = -1
    if wkd_str == 'Monday':
        wkd = 0
    if wkd_str == 'Tuesday':
        wkd = 1
    if wkd_str == 'Wednesday':
        wkd = 2
    if wkd_str == 'Thursday':
        wkd = 3
    if wkd_str == 'Friday':
        wkd = 4
    if wkd_str == 'Saturday':
        wkd = 5
    if wkd_str == 'Sunday':
        wkd = 6

    return wkd


# Check if first/last name is valid
def check_realname(name):
    isValid = True
    name = str(name)
    letters = Set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    if len(name) == 0:
        isValid = False
    if not Set(name).issubset(letters):
        isValid = False
    return isValid



########
# Main #
########
if __name__ == '__main__':
    init_db()
    app.debug = False
    app.run(host='0.0.0.0')
