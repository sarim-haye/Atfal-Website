#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
import os
from models import Team, Activity, Points, db_session

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')

# Update database URL for Vercel
if os.environ.get('VERCEL_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

db = SQLAlchemy(app)

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def home():
    teams = Team.query.all()
    activities = Activity.query.all()
    points_data = {}
    
    for team in teams:
        points_data[team.name] = {}
        for activity in activities:
            points = Points.query.filter_by(team_id=team.id, activity_id=activity.id).first()
            points_data[team.name][activity.name] = points.points if points else 0
    
    return render_template('pages/home.html', teams=teams, activities=activities, points_data=points_data)


@app.route('/about')
def about():
    return render_template('pages/placeholder.about.html')


@app.route('/login')
def login():
    form = LoginForm(request.form)
    return render_template('forms/login.html', form=form)


@app.route('/register')
def register():
    form = RegisterForm(request.form)
    return render_template('forms/register.html', form=form)


@app.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)


@app.route('/manage')
def manage():
    teams = Team.query.all()
    activities = Activity.query.all()
    return render_template('pages/manage.html', teams=teams, activities=activities)


@app.route('/api/team', methods=['POST'])
def add_team():
    name = request.form.get('name')
    if name:
        team = Team(name=name)
        db_session.add(team)
        db_session.commit()
        return jsonify({'success': True, 'message': 'Team added successfully'})
    return jsonify({'success': False, 'message': 'Team name is required'})


@app.route('/api/team/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    team = Team.query.filter_by(id=team_id).first()
    if not team:
        return jsonify({'success': False, 'message': 'Team not found'}), 404
    
    # Delete all points associated with this team
    Points.query.filter_by(team_id=team_id).delete()
    db_session.delete(team)
    db_session.commit()
    return jsonify({'success': True, 'message': 'Team deleted successfully'})


@app.route('/api/activity', methods=['POST'])
def add_activity():
    name = request.form.get('name')
    if name:
        activity = Activity(name=name)
        db_session.add(activity)
        db_session.commit()
        return jsonify({'success': True, 'message': 'Activity added successfully'})
    return jsonify({'success': False, 'message': 'Activity name is required'})


@app.route('/api/activity/<int:activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    activity = Activity.query.filter_by(id=activity_id).first()
    if not activity:
        return jsonify({'success': False, 'message': 'Activity not found'}), 404
    
    # Delete all points associated with this activity
    Points.query.filter_by(activity_id=activity_id).delete()
    db_session.delete(activity)
    db_session.commit()
    return jsonify({'success': True, 'message': 'Activity deleted successfully'})


@app.route('/api/points', methods=['POST'])
def update_points():
    team_id = request.form.get('team_id')
    activity_id = request.form.get('activity_id')
    points = request.form.get('points', 0)
    
    if team_id and activity_id:
        points_record = Points.query.filter_by(team_id=team_id, activity_id=activity_id).first()
        if not points_record:
            points_record = Points(team_id=team_id, activity_id=activity_id, points=0)
            db_session.add(points_record)
        
        points_record.points = int(points)
        db_session.commit()
        return jsonify({'success': True, 'message': 'Points updated successfully'})
    return jsonify({'success': False, 'message': 'Missing required fields'})

# Error handlers.


@app.errorhandler(500)
def internal_error(error):
    db_session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

# Remove file logging for Vercel
if not app.debug and not os.environ.get('VERCEL_ENV'):
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# This is for local development
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
