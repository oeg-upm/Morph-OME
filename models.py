from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()
# db.create_all()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(220), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(220), unique=True, nullable=False)

    def __repr__(self):
        return '<Group %r>' % self.name


class ManyUserGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

    def __repr__(self):
        return '<Many %d>' % self.id


class KG(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(220), unique=False, nullable=False)
    group = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

    def __repr__(self):
        return '<KG %r>' % self.name



# db.create_all()