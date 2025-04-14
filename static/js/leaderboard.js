const { useState, useEffect } = React;

const TeamRow = ({ team, position, onDelete }) => {
    const [isDeleting, setIsDeleting] = useState(false);
    const [showDelete, setShowDelete] = useState(false);

    return (
        <tr 
            className="team-row"
            onMouseEnter={() => setShowDelete(true)}
            onMouseLeave={() => setShowDelete(false)}
        >
            <td className="position">
                <span className="position-badge">{position}</span>
            </td>
            <td className="team-name">{team.name}</td>
            <td className="league-name">{team.league_name}</td>
            <td className="points">{team.total_points}</td>
            <td className="actions">
                {showDelete && (
                    <button 
                        className="delete-btn"
                        onClick={() => {
                            setIsDeleting(true);
                            onDelete(team.id);
                        }}
                        disabled={isDeleting}
                    >
                        {isDeleting ? '...' : '×'}
                    </button>
                )}
            </td>
        </tr>
    );
};

const LeaderboardHeader = ({ title, onBack }) => (
    <div className="leaderboard-header">
        {onBack && (
            <button className="back-btn" onClick={onBack}>
                ← Back
            </button>
        )}
        <h1>{title}</h1>
    </div>
);

const Leaderboard = () => {
    const [teams, setTeams] = useState(window.INITIAL_DATA.teams || []);
    const [leagues, setLeagues] = useState(window.INITIAL_DATA.leagues || []);
    const [currentLeague, setCurrentLeague] = useState(window.INITIAL_DATA.currentLeague);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchTeams = async (leagueId = null) => {
        setLoading(true);
        try {
            const url = leagueId 
                ? `/api/teams?league_id=${leagueId}`
                : '/api/teams';
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok) throw new Error(data.error);
            
            setTeams(data);
            setError(null);
        } catch (err) {
            setError('Failed to load teams');
            console.error('Error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteTeam = async (teamId) => {
        try {
            const response = await fetch(`/api/teams/${teamId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error);
            }

            setTeams(teams.filter(team => team.id !== teamId));
        } catch (err) {
            setError('Failed to delete team');
            console.error('Error:', err);
        }
    };

    const handleLeagueClick = (league) => {
        setCurrentLeague(league);
        fetchTeams(league.id);
    };

    const handleBack = () => {
        setCurrentLeague(null);
        fetchTeams();
    };

    useEffect(() => {
        if (!currentLeague) {
            fetchTeams();
        }
    }, []);

    if (loading) {
        return <div className="loading">Loading...</div>;
    }

    if (error) {
        return <div className="error">{error}</div>;
    }

    const sortedTeams = [...teams].sort((a, b) => b.total_points - a.total_points);

    return (
        <div className="leaderboard-container">
            <LeaderboardHeader 
                title={currentLeague ? currentLeague.name : "All Leagues"} 
                onBack={currentLeague ? handleBack : null}
            />
            
            {!currentLeague && (
                <div className="leagues-grid">
                    {leagues.map(league => (
                        <div 
                            key={league.id}
                            className="league-card"
                            onClick={() => handleLeagueClick(league)}
                        >
                            <h2>{league.name}</h2>
                            <p>{league.team_count} Teams</p>
                        </div>
                    ))}
                </div>
            )}

            {currentLeague && (
                <table className="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Position</th>
                            <th>Team</th>
                            <th>League</th>
                            <th>Points</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedTeams.map((team, index) => (
                            <TeamRow
                                key={team.id}
                                team={team}
                                position={index + 1}
                                onDelete={handleDeleteTeam}
                            />
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

ReactDOM.render(<Leaderboard />, document.getElementById('root')); 