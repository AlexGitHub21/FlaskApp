from extensions import db
from flask_login import UserMixin


class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number_rows = db.Column(db.Integer())
    number_seats = db.Column(db.String())
    number_visitors = db.Column(db.Integer())
    visitor_preferences = db.Column(db.String())
    answer = db.Column(db.String())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, number_rows, number_seats, number_visitors, visitor_preferences, answer, user_id):
        self.number_rows = number_rows
        self.number_seats = number_seats
        self.number_visitors = number_visitors
        self.visitor_preferences = visitor_preferences
        self.answer = answer
        self.user_id = user_id


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), nullable=False, unique=True)
    psw = db.Column(db.String(500), nullable=False, unique=True)
    role_type = db.Column(db.String(10))
    tests = db.relationship('Test', backref=db.backref('user', lazy='joined'), lazy='select')

    def __init__(self, login, psw, role_type):
        self.login = login
        self.psw = psw
        self.role_type = role_type

    @staticmethod
    def getUser(user_id):
        return User.query.filter_by(id=user_id).first()



