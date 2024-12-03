from extensions import db


class Tests(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    number_rows = db.Column(db.Integer())
    number_seats = db.Column(db.String())
    number_visitors = db.Column(db.Integer())
    visitor_preferences = db.Column(db.String())
    answer = db.Column(db.String())

    def __init__(self, number_rows, number_seats, number_visitors, visitor_preferences, answer):
        self.number_rows = number_rows
        self.number_seats = number_seats
        self.number_visitors = number_visitors
        self.visitor_preferences = visitor_preferences
        self.answer = answer


