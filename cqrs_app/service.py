import json
import mongoengine
import uuid

from models import (
    Base,
    UsersCommandModel,
    UsersQueryModel,
)

from nameko.events import EventDispatcher
from nameko.rpc import rpc, RpcProxy
from nameko.web.handlers import http
from nameko.events import event_handler
from nameko_sqlalchemy import DatabaseSession


class ApiService:

    name = 'api'
    command_rpc = RpcProxy('command_stack')
    query_rpc = RpcProxy('query_stack')

    @http('POST', '/user')
    def post(self, request):
        data = json.loads(request.get_data(as_text=True))
        if not data:
            return 400, 'Invalid payload'
        try:
            response = self.command_rpc.create_user(data)
            return 201, json.dumps(response)
        except Exception as e:
            return 500, e

    @http('GET', '/users/<int:page>/<int:limit>')
    def get_list(self, request, page, limit):
        response = self.query_rpc.get_all_users(page, limit)
        return 200, {'Content-Type': 'application/json'}, response

    @http('GET', '/users/<string:user_id>')
    def get(self, request, user_id):
        response = self.query_rpc.get_user(user_id)
        return 200, {'Content-Type': 'application/json'}, response


class CommandStack:
    name = 'command_stack'
    dispatch = EventDispatcher()
    db = DatabaseSession(Base)

    @rpc
    def create_user(self, data):
        try:
            id = str(uuid.uuid1())
            user = UsersCommandModel(
                id=id,
                name=data['name'],
                email=data['email'],
                description=data['description'],
            )
            self.db.add(user)
            self.db.commit()
            data['id'] = user.id
            self.dispatch('replicate_db_event', data)
            return data
        except Exception as e:
            self.db.rollback()
            return e


class QueryStack:
    name = 'query_stack'

    @event_handler('command_stack', 'replicate_db_event')
    def normalize_db(self, data):
        try:
            UsersQueryModel(
                id=data['id'],
                name=data['name'],
                email=data.get('email'),
                description=data.get('description'),
            ).save()
        except Exception as e:
            return e

    @rpc
    def get_user(self, id):
        try:
            user = UsersQueryModel.objects.get(id=id)
            return user.to_json()
        except mongoengine.DoesNotExist as e:
            return e
        except Exception as e:
            return e

    @rpc
    def get_all_users(self, page, limit):
        try:
            if not page:
                page = 1
            offset = (page - 1) * limit
            users = UsersQueryModel.objects.skip(offset).limit(limit)
            return users.to_json()
        except Exception as e:
            return e
