import os
from models import (
    Base,
    PermissionsCommandModel,
    PermissionsType,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_db():
    db = create_engine(os.environ.get("COMMANDDB_HOST"))
    Base.metadata.create_all(db)
    session = sessionmaker(bind=db)
    per1 = PermissionsCommandModel(
        permission=PermissionsType.admin,
        description='Admin is a super user to the app'
    )
    per2 = PermissionsCommandModel(
        permission=PermissionsType.user,
        description='User is just a client to the app'
    )
    session.add_all([per1, per2])
    session.commit()


if __name__ == '__main__':
    print('creating databases')
    create_db()
    print('databases created')
