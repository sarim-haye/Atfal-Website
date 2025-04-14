from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, stream_with_context, g
from datetime import datetime
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import time
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)
DATABASE = 'scoring.db'

# Configure logging
LOG_FILE = 'activity_log.txt'

def log_activity(judge_name, action, details=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Judge: {judge_name} | Action: {action}"
    if details:
        log_entry += f" | Details: {details}"
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(log_entry + '\n')

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = dict_factory
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'judge_name' not in session:
            # Store the requested URL in the session
            session['next_url'] = request.url
            flash('Please log in to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'judge_name' in session:
        return redirect(url_for('judge_categories'))
        
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin')
        judge_name = request.form.get('judge_name')
        
        if not pin or not judge_name:
            error = "Please provide both PIN and name"
        elif pin == '1234':  # Replace with secure PIN verification
            session['judge_name'] = judge_name
            log_activity(judge_name, "LOGIN", "Successful login")
            
            # Redirect to the stored URL or default to judge_categories
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('judge_categories'))
        else:
            error = "Invalid PIN"
            log_activity(judge_name, "LOGIN_FAILED", "Invalid PIN attempt")
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    if 'judge_name' in session:
        log_activity(session['judge_name'], "LOGOUT", "User logged out")
        session.clear()
    return redirect(url_for('login'))

@app.route('/judge/categories')
@login_required
def judge_categories():
    return render_template('judge_categories.html')

@app.route('/judge/scoring')
@login_required
def judge_scoring():
    # Map lowercase input to proper case
    category_map = {
        'academic': 'Academic',
        'sports': 'Sports',
        'extracurricular': 'Extracurricular'
    }
    
    category = request.args.get('category', 'academic').lower()
    if category not in category_map:
        category = 'academic'
    
    db = get_db()
    try:
        # Fetch competitions for the selected category
        competitions = db.execute('''
            SELECT * FROM competitions 
            WHERE category = ? 
            ORDER BY name
        ''', [category_map[category]]).fetchall()
        
        # Fetch teams and leagues
        teams = db.execute('''
            SELECT t.*, l.name as league_name 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
            ORDER BY l.name, t.name
        ''').fetchall()
        
        leagues = db.execute('SELECT * FROM leagues ORDER BY name').fetchall()
        
        return render_template('scoring.html',
                             category=category,
                             competitions=competitions,
                             teams=teams,
                             leagues=leagues)
    except Exception as e:
        log_activity(session['judge_name'], 'ERROR', f'Error loading scoring page: {str(e)}')
        flash('An error occurred while loading the scoring page')
        return redirect(url_for('judge_categories'))

def calculate_team_scores():
    db = get_db()
    try:
        # Get all teams with their leagues
        teams = db.execute('''
            SELECT t.*, l.name as league_name 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
        ''').fetchall()
        
        # Calculate scores for each team
        for team in teams:
            # Get academic points
            academic = db.execute('''
                SELECT COALESCE(SUM(s.points), 0) as points
                FROM scores s
                JOIN competitions c ON s.competition_id = c.id
                WHERE s.team_id = ? AND c.category = 'Academic'
            ''', [team['id']]).fetchone()
            team['academic_points'] = academic['points']
            
            # Get sports points
            sports = db.execute('''
                SELECT COALESCE(SUM(s.points), 0) as points
                FROM scores s
                JOIN competitions c ON s.competition_id = c.id
                WHERE s.team_id = ? AND c.category = 'Sports'
            ''', [team['id']]).fetchone()
            team['sports_points'] = sports['points']
            
            # Get extracurricular points
            extra = db.execute('''
                SELECT COALESCE(SUM(s.points), 0) as points
                FROM scores s
                JOIN competitions c ON s.competition_id = c.id
                WHERE s.team_id = ? AND c.category = 'Extracurricular'
            ''', [team['id']]).fetchone()
            team['extra_points'] = extra['points']
            
            # Calculate total points
            team['total_points'] = (
                team['academic_points'] + 
                team['sports_points'] +
                team['extra_points']
            )
        
        return teams
    except Exception as e:
        log_activity(session.get('judge_name', 'System'), 'ERROR', f'Error calculating scores: {str(e)}')
        return []

@app.route('/leaderboard')
@login_required
def leaderboard():
    db = get_db()
    # Get leagues in specific order: Premier, Championship, Division One
    leagues = db.execute('''
        SELECT * FROM leagues 
        ORDER BY CASE name 
            WHEN 'Premier' THEN 1 
            WHEN 'Championship' THEN 2 
            WHEN 'Division One' THEN 3 
            ELSE 4 
        END
    ''').fetchall()
    initial_teams = calculate_team_scores()  # Get initial team data
    return render_template('leaderboard.html', 
                         leagues=leagues,
                         teams=initial_teams)

@app.route('/leaderboard/stream')
def leaderboard_stream():
    def generate():
        while True:
            teams = calculate_team_scores()
            data = json.dumps(teams)
            yield f"data: {data}\n\n"
            time.sleep(1)
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

@app.route('/judge/save-scores', methods=['POST'])
@login_required
def save_scores():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
        
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Expected an array of scores'}), 400
        
    db = get_db()
    try:
        cursor = db.cursor()
        for score in data:
            # Validate required fields
            if not all(k in score for k in ('team_id', 'competition_id', 'points')):
                raise ValueError('Missing required fields in score data')
                
            # Validate score value is between 0 and 100
            points = float(score['points'])
            if not (0 <= points <= 100):
                raise ValueError('Score must be between 0 and 100')
            
            # Ensure we don't exceed 100 points
            points = min(points, 100)
            
            cursor.execute('''
                INSERT OR REPLACE INTO scores (team_id, competition_id, points, judge_name)
                VALUES (?, ?, ?, ?)
            ''', (score['team_id'], score['competition_id'], 
                  points, session['judge_name']))
        
        db.commit()
        log_activity(session['judge_name'], 'SAVE_SCORES', f'Saved {len(data)} scores')
        return jsonify({'message': 'Scores saved successfully'})
        
    except Exception as e:
        db.rollback()
        log_activity(session['judge_name'], 'ERROR', f'Failed to save scores: {str(e)}')
        return jsonify({'error': str(e)}), 400

@app.route('/admin/teams')
@login_required
def manage_teams():
    db = get_db()
    try:
        # Get all teams with their league names and scores
        teams = db.execute('''
            SELECT t.*, l.name as league_name 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
        ''').fetchall()
        
        # Get all leagues
        leagues = db.execute('SELECT * FROM leagues ORDER BY name').fetchall()
        
        return render_template('manage_teams.html', teams=teams, leagues=leagues)
    except Exception as e:
        log_activity(session['judge_name'], 'ERROR', f'Error loading manage teams page: {str(e)}')
        flash('An error occurred while loading the teams page', 'error')
        return redirect(url_for('judge_categories'))

@app.route('/admin/add_team', methods=['POST'])
@login_required
def admin_add_team():
    team_name = request.form.get('team_name')
    league_id = request.form.get('league_id')
    
    if not team_name or not league_id:
        flash('Team name and league are required', 'error')
        return redirect(url_for('admin_leaderboard', league_id=league_id))
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO teams (name, league_id) VALUES (?, ?)', 
                      (team_name, league_id))
        db.commit()
        flash('Team added successfully', 'success')
    except sqlite3.Error as e:
        flash(f'Error adding team: {str(e)}', 'error')
    
    return redirect(url_for('admin_leaderboard', league_id=league_id))

@app.route('/admin/update_team_scores/<int:team_id>', methods=['POST'])
@login_required
def admin_update_team_scores(team_id):
    action = request.form.get('action')
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        if action == 'delete':
            cursor.execute('DELETE FROM teams WHERE id = ?', (team_id,))
            db.commit()
            flash('Team deleted successfully', 'success')
            return redirect(url_for('admin_leaderboard'))
        
        academic = float(request.form.get('academic_points', 0))
        sports = float(request.form.get('sports_points', 0))
        extra = float(request.form.get('extra_points', 0))
        
        # Ensure scores are within valid range
        academic = min(max(academic, 0), 100)
        sports = min(max(sports, 0), 100)
        extra = min(max(extra, 0), 100)
        
        if action == 'reduce':
            # Get current scores
            cursor.execute('''
                SELECT academic_points, sports_points, extra_points 
                FROM teams WHERE id = ?
            ''', (team_id,))
            current = cursor.fetchone()
            
            if current:
                # Subtract new values from current values, ensuring we don't go below 0
                academic = max(0, float(current['academic_points'] or 0) - academic)
                sports = max(0, float(current['sports_points'] or 0) - sports)
                extra = max(0, float(current['extra_points'] or 0) - extra)
        
        # Calculate total points
        total = academic + sports + extra
        
        cursor.execute('''
            UPDATE teams 
            SET academic_points = ?, 
                sports_points = ?, 
                extra_points = ?,
                total_points = ?
            WHERE id = ?
        ''', (academic, sports, extra, total, team_id))
        
        db.commit()
        flash('Scores updated successfully', 'success')
        
    except (sqlite3.Error, ValueError) as e:
        flash(f'Error updating scores: {str(e)}', 'error')
    
    # Get the league_id for redirect
    cursor.execute('SELECT league_id FROM teams WHERE id = ?', (team_id,))
    result = cursor.fetchone()
    league_id = result['league_id'] if result else None
    
    return redirect(url_for('admin_leaderboard', league_id=league_id))

@app.route('/admin/leaderboard')
@app.route('/admin/leaderboard/<int:league_id>')
@login_required
def admin_leaderboard(league_id=None):
    db = get_db()
    try:
        # Get all leagues
        leagues = db.execute('SELECT * FROM leagues ORDER BY name').fetchall()
        
        # If no league_id is provided, use the first league
        if league_id is None and leagues:
            league_id = leagues[0]['id']
        
        # Get teams for the selected league
        teams = db.execute('''
            SELECT t.*, l.name as league_name 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
            WHERE t.league_id = ?
            ORDER BY t.total_points DESC
        ''', [league_id]).fetchall()
        
        return render_template('admin_leaderboard.html', 
                             teams=teams, 
                             leagues=leagues, 
                             selected_league=league_id)
    except Exception as e:
        log_activity(session['judge_name'], 'ERROR', f'Error loading admin leaderboard: {str(e)}')
        flash('An error occurred while loading the leaderboard', 'error')
        return redirect(url_for('manage_teams'))

@app.route('/manage/leagues')
@login_required
def manage_leagues():
    db = get_db()
    cursor = db.cursor()
    
    # Get all leagues
    cursor.execute('SELECT * FROM leagues ORDER BY id')
    leagues = cursor.fetchall()
    
    # Get all teams with their league names
    cursor.execute('''
        SELECT t.*, l.name as league_name 
        FROM teams t 
        JOIN leagues l ON t.league_id = l.id 
        ORDER BY l.id, t.name
    ''')
    teams = cursor.fetchall()
    
    return render_template('manage_leagues.html', leagues=leagues, teams=teams)

@app.route('/manage/leagues/<int:league_id>', methods=['POST'])
@login_required
def update_league(league_id):
    league_name = request.form.get('league_name')
    
    if not league_name:
        flash('League name is required', 'error')
        return redirect(url_for('manage_leagues'))
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE leagues SET name = ? WHERE id = ?', 
                      (league_name, league_id))
        db.commit()
        flash('League updated successfully', 'success')
    except sqlite3.Error as e:
        flash(f'Error updating league: {str(e)}', 'error')
    
    return redirect(url_for('manage_leagues'))

@app.route('/manage/teams/add', methods=['POST'])
@login_required
def add_team():
    team_name = request.form.get('team_name')
    league_id = request.form.get('league_id')
    
    if not team_name or not league_id:
        flash('Team name and league are required', 'error')
        return redirect(url_for('manage_leagues'))
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if we already have 3 leagues
        cursor.execute('SELECT COUNT(*) as count FROM leagues')
        league_count = cursor.fetchone()['count']
        if league_count > 3:
            flash('Maximum of 3 leagues allowed', 'error')
            return redirect(url_for('manage_leagues'))
        
        cursor.execute('INSERT INTO teams (name, league_id) VALUES (?, ?)', 
                      (team_name, league_id))
        db.commit()
        flash('Team added successfully', 'success')
    except sqlite3.Error as e:
        flash(f'Error adding team: {str(e)}', 'error')
    
    return redirect(url_for('manage_leagues'))

@app.route('/manage/teams/<int:team_id>/delete', methods=['POST'])
@login_required
def delete_team(team_id):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM teams WHERE id = ?', (team_id,))
        db.commit()
        flash('Team deleted successfully', 'success')
    except sqlite3.Error as e:
        flash(f'Error deleting team: {str(e)}', 'error')
    
    return redirect(url_for('manage_leagues'))

if __name__ == '__main__':
    from flask import g
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True) 