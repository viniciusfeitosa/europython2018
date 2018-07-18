import json
import logging
import mongoengine
import os
import uuid

from models import (
    Base,
    PermissionsCommandModel,
    UsersCommandModel,
    UsersQueryModel,
    UsersPerPermissionsQueryModel,
    UsersStruct,
)

from nameko.events import EventDispatcher
from nameko.rpc import rpc, RpcProxy
from nameko.web.handlers import http
from nameko.events import event_handler
from nameko.standalone.rpc import ClusterRpcProxy
from nameko_sqlalchemy import DatabaseSession

CONFIG = {'AMQP_URI': os.environ.get('QUEUE_HOST')}


class ApiService:

    name = 'api'
    query_rpc = RpcProxy('query_stack')

    @http('POST', '/create_user')
    def post(self, request):
        data = json.loads(request.get_data(as_text=True))
        if not data:
            return 400, 'Invalid payload'
        try:
            with ClusterRpcProxy(CONFIG) as cluster_rpc:
                data['id'] = str(uuid.uuid1())
                cluster_rpc.command_stack.user_domain.call_async(data)
            localtion = {
                'Location': 'http://localhost/user/{}'.format(data['id'])
            }
            return 202, localtion, 'ACCEPTED'
        except Exception as e:
            return 500, e

    @http('GET', '/users/<int:page>/<int:limit>')
    def get_users(self, request, page, limit):
        response = self.query_rpc.get_all_users(page, limit)
        return 200, {'Content-Type': 'application/json'}, response

    @http('GET', '/user/<string:user_id>')
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
    def user_domain(self, data):
        try:
            user = UsersCommandModel(
                id=data['id'],
                name=data['name'],
                email=data['email'],
                description=data['description'],
                permission=data['permission']
            )
            self.db.add(user)
            self.db.commit()
            self.dispatch('user_created', data)

            permission = self.db.query(PermissionsCommandModel).\
                filter_by(name=data['permission']).one()
            data['permission_description'] = permission.description
            self.dispatch('permission_user_related', data)
        except Exception as e:
            self.db.rollback()
            logging.error(e)


class EventsComponent:
    name = 'events_component'

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
            logging.error(e)

    @event_handler('command_stack', 'permission_user_related')
    def permission_user_related_normalize_db(self, data):
        user_struct = UsersStruct(
            id=data['id'],
            name=data['name'],
            email=data.get('email'),
            description=data.get('description'),
            permission=data['permission']
        )
        try:
            up = UsersPerPermissionsQueryModel.objects.get(
                permission=data['permission']
            )
            up.users.append(user_struct)
            up.save()
        except mongoengine.DoesNotExist:
            try:
                up = UsersPerPermissionsQueryModel(
                    permission=data['permission'],
                    description=data['permission_description'],
                )
                up.users.append(user_struct)
                up.save()
            except Exception as e:
                logging.error(e)


class QueryStack:
    name = 'query_stack'

    @rpc
    def get_user(self, id):
        try:
            user = UsersQueryModel.objects.get(id=id)
            return user.to_json()
        except mongoengine.DoesNotExist as e:
            return json.dumps({'error': e})
        except Exception as e:
            return json.dumps({'error': e})

    @rpc
    def get_all_users(self, page, limit):
        try:
            if not page:
                page = 1
            offset = (page - 1) * limit
            users = UsersQueryModel.objects.skip(offset).limit(limit)
            return users.to_json()
        except Exception as e:
            return json.dumps({'error': e})

    @rpc
    def get_users_by_permission(self, permission):
        try:
            per = UsersPerPermissionsQueryModel.objects.get(
                permission=permission
            )
            return per.to_json()
        except mongoengine.DoesNotExist as e:
            return json.dumps({'error': e})
        except Exception as e:
            return json.dumps({'error': e})
