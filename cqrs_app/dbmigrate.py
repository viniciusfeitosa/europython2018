import os
from models import Base
from sqlalchemy import create_engine


def create_db():
    db = create_engine(os.environ.get("COMMANDDB_HOST"))
    Base.metadata.create_all(db)


if __name__ == '__main__':
    print('creating databases')
    create_db()
    print('databases created')
