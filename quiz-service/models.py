from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy

# get db
db = SQLAlchemy()


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    questions_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def questions(self):
        return json.loads(self.questions_json)

    @questions.setter
    def questions(self, value):
        self.questions_json = json.dumps(value)


class QuizSubmission(db.Model):
    __tablename__ = 'quiz_submissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    course_id = db.Column(db.String(100), nullable=False)
    answers_json = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def answers(self):
        return json.loads(self.answers_json)

    @answers.setter
    def answers(self, value):
        self.answers_json = json.dumps(value)