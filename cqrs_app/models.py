import enum
import os
from datetime import datetime
from mongoengine import (
    connect,
    Document,
    DateTimeField,
    StringField,
    EmbeddedDocumentListField,
)

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class PermissionsType(enum.Enum):
    admin = 'admin'
    user = 'user'


class UsersCommandModel(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    name = Column(String(length=200))
    email = Column(String(length=200))
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    permission = Column(Enum(PermissionsType), ForeignKey('pemissions.name'))

    __table_args__ = Index('index', 'id', 'email'),


class PermissionsCommandModel(Base):
    __tablename__ = 'permissions'

    name = Column(Enum(PermissionsType), primary_key=True)
    description = Column(String)

    __table_args__ = Index('index', 'id', 'email'),


connect('users', host=os.environ.get('QUERYBD_HOST'))


class UsersQueryModel(Document):
    id = StringField(primary_key=True)
    name = StringField(required=True, max_length=200)
    email = StringField(required=True, max_length=200)
    description = StringField(required=True)
    permission = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)


class UsersPerPermissionsQueryModel(Document):
    permission = StringField(primary_key=True)
    description = StringField()
    users = EmbeddedDocumentListField(UsersQueryModel)
