import json
import mongoengine
import os
import uuid

from models import (
    Base,
    PermissionsCommandModel,
    UsersCommandModel,
    UsersQueryModel,
    UsersPerPermissionsQueryModel,
)

from nameko.events import EventDispatcher
from nameko.rpc import rpc, RpcProxy
from nameko.web.handlers import http
from nameko.events import event_handler
from nameko.standalone.rpc import ClusterRpcProxy
from nameko_sqlalchemy import DatabaseSession

CONFIG = {
    'AMQP_URI': os.getenv('QUEUE_HOST')
}


class ApiService:

    name = 'api'
    query_rpc = RpcProxy('query_stack')

    @http('POST', '/user')
    def post(self, request):
        data = json.loads(request.get_data(as_text=True))
        if not data:
            return 400, 'Invalid payload'
        try:
            with ClusterRpcProxy(CONFIG) as cluster_rpc:
                cluster_rpc.command_stack.create_user.call_async(data)
            return 201, 'SUCCESS'
        except Exception as e:
            return 500, e

    @http('GET', '/users/<int:page>/<int:limit>')
    def get_users(self, request, page, limit):
        response = self.query_rpc.get_all_users(page, limit)
        return 200, {'Content-Type': 'application/json'}, response

    @http('GET', '/users/<string:user_id>')
    def get_user(self, request, user_id):
        response = self.query_rpc.get_user(user_id)
        return 200, {'Content-Type': 'application/json'}, response

    @http('GET', '/users/<string:permission>/permission')
    def get_users_by_permission(self, request, permission):
        response = self.query_rpc.get_users_by_permission(permission)
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
                permission=data['permission']
            )
            self.db.add(user)
            self.db.commit()
            data['id'] = user.id
            self.dispatch('user_created', data)
            self.dispatch('permission_user_related', data)
            return data
        except Exception as e:
            self.db.rollback()
            return e


class Events:
    name = 'events'
    db = DatabaseSession(Base)

    @event_handler('command_stack', 'user_created')
    def user_created_normalize_db(self, data):
        try:
            UsersQueryModel(
                id=data['id'],
                name=data['name'],
                email=data.get('email'),
                description=data.get('description'),
                permission=data.get('permission')
            ).save()
        except Exception as e:
            return e

    @event_handler('command_stack', 'permission_user_related')
    def permission_user_related_normalize_db(self, data):
        try:
            permission = self.db.query(PermissionsCommandModel).\
                filter_by(name=data['permission']).one()

            up = UsersPerPermissionsQueryModel(
                permission=permission.name,
                description=permission.description,
            )
            up.users.append(
                UsersQueryModel(
                    id=data['id'],
                    name=data['name'],
                    email=data.get('email'),
                    description=data.get('description'),
                    permission=data.get('permission')
                )
            )
            up.save()
        except Exception as e:
            return e


class QueryStack:
    name = 'query_stack'

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

    @rpc
    def get_users_by_permission(self, permission):
        try:
            per = UsersPerPermissionsQueryModel.objects.get(
                permission=permission
            )
            return per.to_json()
        except mongoengine.DoesNotExist as e:
            return e
        except Exception as e:
            return e
