CREATE TABLE IF NOT EXISTS leagues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    league_id INTEGER NOT NULL,
    FOREIGN KEY (league_id) REFERENCES leagues (id)
);

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    max_points INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    points REAL NOT NULL,
    judge_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams (id),
    FOREIGN KEY (competition_id) REFERENCES competitions (id)
);

-- Insert some sample data
INSERT OR IGNORE INTO leagues (name) VALUES 
    ('Premier League'),
    ('Championship'),
    ('Division One');

INSERT OR IGNORE INTO competitions (name, category, max_points) VALUES 
    ('Math Quiz', 'Academic', 100),
    ('Science Fair', 'Academic', 100),
    ('Football', 'Sports', 50),
    ('Basketball', 'Sports', 50),
    ('Debate', 'Extracurricular', 75),
    ('Art Competition', 'Extracurricular', 75);

-- Insert some sample teams
INSERT OR IGNORE INTO teams (name, league_id) VALUES 
    ('Team Alpha', 1),
    ('Team Beta', 1),
    ('Team Gamma', 2),
    ('Team Delta', 2),
    ('Team Epsilon', 3),
    ('Team Zeta', 3); 