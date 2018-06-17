import os
from datetime import datetime
from mongoengine import (
    connect,
    Document,
    DateTimeField,
    StringField,
)

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class UsersCommandModel(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    name = Column(String(length=200))
    email = Column(String(length=200))
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = Index('index', 'id', 'email'),


connect('users', host=os.environ.get('QUERYBD_HOST'))


class UsersQueryModel(Document):
    id = StringField(primary_key=True)
    name = StringField(required=True, max_length=200)
    email = StringField(required=True, max_length=200)
    description = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
