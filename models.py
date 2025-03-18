from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy import Column, Integer, String
# from app import db

engine = create_engine('sqlite:///database.db', echo=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    points = relationship("Points", back_populates="team")

    def __repr__(self):
        return f'<Team {self.name}>'

class Activity(Base):
    __tablename__ = 'activities'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    points = relationship("Points", back_populates="activity")

    def __repr__(self):
        return f'<Activity {self.name}>'

class Points(Base):
    __tablename__ = 'points'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    activity_id = Column(Integer, ForeignKey('activities.id'), nullable=False)
    points = Column(Integer, default=0)
    
    team = relationship("Team", back_populates="points")
    activity = relationship("Activity", back_populates="points")

    def __repr__(self):
        return f'<Points {self.points}>'

# Set your classes here.

'''
class User(Base):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(30))

    def __init__(self, name=None, password=None):
        self.name = name
        self.password = password
'''

# Create tables.
Base.metadata.create_all(bind=engine)
