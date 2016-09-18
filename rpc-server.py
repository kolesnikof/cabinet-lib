#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import bcrypt

from flask import Flask, session, request
from flask_jsonrpc import JSONRPC, _parse_sig
from firebase_token_generator import create_token
from inspect import getargspec

from cabinet import Cabinet
from rpc import authenticate

app = Flask(__name__)


class ExtendedJSONRPC(JSONRPC):
    def method(self, name, authenticated=False, safe=False, validate=False,
               **options):
        def decorator(f):
            """This decorator doesn't have assumptions about the arguments."""

            arg_names = getargspec(f)[0]
            X = {'name': name, 'arg_names': arg_names}
            if authenticated:
                _f = self.auth_backend(f, authenticated)
            else:
                _f = f
            method, arg_types, return_type = _parse_sig(X['name'],
                                                        X['arg_names'],
                                                        validate)
            _f.json_args = X['arg_names']
            _f.json_arg_types = arg_types
            _f.json_return_type = return_type
            _f.json_method = method
            _f.json_safe = safe
            _f.json_sig = X['name']
            _f.json_validate = validate
            self.site.register(method, _f)
            return _f
        return decorator


jsonrpc = ExtendedJSONRPC(app, '/api/v1', auth_backend=authenticate)

account_id = 'my-name@my-company.com'
password = b'asdfasdf'

name = 'test-vault'
temp_config_path = os.path.join(os.getcwd(), 'test.data', 'secrets')
test_vault_path = os.path.join(os.getcwd(), 'test.data', 'vaults')
cab = Cabinet(account_id, password, temp_config_path)
cab.open(name, test_vault_path)


def generateToken(username, password, vault_path):
    SECURITY_SALT = bcrypt.gensalt().decode("utf-8")
    auth_payload = {
        'uid': username,
        'password': password,
        'vault_path': vault_path
    }
    token = create_token(SECURITY_SALT, auth_payload)
    session['username'] = username
    session['vault_path'] = vault_path
    session['token'] = token
    session.permanent = True


def check_auth(token):
    token = request.headers.get('token')
    if 'token' in session:
        return token == session['token']
    return False


@jsonrpc.method('App.login(username=str, password=str, vault_path=str) -> str')
def login(username, password, vault_path):
    generateToken(username, password, vault_path)
    return session['token']


@jsonrpc.method('App.get_all')
def get_all():
    return cab.get_all()


@jsonrpc.method('App.get(name=str)')
def get(name):
    return cab.get(name)


@jsonrpc.method('App.add(item=dict)')
def add(item):
    return cab.add(item)


@jsonrpc.method('Cabinet.test', authenticated=check_auth)
def index():
    return u'hello world!'


@jsonrpc.method('App.echo(name=str) -> str', validate=True,
                authenticated=check_auth)
def echo(name='Flask JSON-RPC'):
    return u'Hello {0}'.format(name)


def get_random_open_port():
    # # serve on a random port:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


if __name__ == '__main__':
    app.secret_key = bcrypt.gensalt().decode('utf8')
    # app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(port=5000, debug=True)  # only localhost, default port

    # port = get_random_open_port()
    # app.run(port=port)
