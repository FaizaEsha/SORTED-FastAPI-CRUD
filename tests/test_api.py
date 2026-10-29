"""Offline contracts: provider behavior is mocked; SQLite uses a temporary file."""
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

import auth
import main


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'DB_PATH', tmp_path / 'tasks.db')
    main.init_db()
    provider = Mock()
    user = SimpleNamespace(id='user-a', email='test@example.com', created_at='2026-01-01')
    provider.get_user.return_value = SimpleNamespace(user=user)
    provider.sign_up.return_value = SimpleNamespace(user=user)
    provider.sign_in_with_password.return_value = SimpleNamespace(session=SimpleNamespace(
        access_token='valid', refresh_token='refresh'))
    main.app.dependency_overrides[auth.get_auth] = lambda: provider
    with TestClient(main.app) as client:
        yield client, provider
    main.app.dependency_overrides.clear()


def test_original_crud_and_dashboard(api):
    client, _ = api
    assert client.get('/').json()['name'] == 'Task API'
    assert client.get('/health').json() == {'status': 'ok'}
    assert 'SORT<em>ED.' in client.get('/app').text
    assert client.get('/static/app.js').status_code == 200
    assert len(client.get('/tasks').json()) == 3
    created = client.post('/tasks', json={'title': '  Keep existing design  '})
    assert created.status_code == 201
    task_id = created.json()['id']
    assert client.get(f'/tasks/{task_id}').json()['title'] == 'Keep existing design'
    assert client.put(f'/tasks/{task_id}', json={'done': True}).json()['done'] is True
    main.init_db()
    assert client.get(f'/tasks/{task_id}').status_code == 200
    assert client.post('/tasks', json={}).status_code == 400
    assert client.delete(f'/tasks/{task_id}').status_code == 204
    assert client.get(f'/tasks/{task_id}').status_code == 404


@pytest.mark.parametrize('route', ['/auth/signup', '/auth/login'])
@pytest.mark.parametrize('body', [{}, {'email': 'test@example.com'}, {'email': ' ', 'password': 'x'},
                                  {'email': 'x', 'password': ''}, {'email': 'x', 'password': None}])
def test_credentials_validation(api, route, body):
    client, provider = api
    assert client.post(route, json=body).status_code == 400
    provider.sign_up.assert_not_called()
    provider.sign_in_with_password.assert_not_called()


def test_signup_login(api):
    client, provider = api
    data = {'email': 'test@example.com', 'password': 'password123'}
    signup = client.post('/auth/signup', json=data)
    assert signup.status_code == 201
    assert set(signup.json()) == {'id', 'email', 'created_at'}
    login = client.post('/auth/login', json=data)
    assert login.status_code == 200
    assert login.json()['access_token'] == 'valid'
    assert login.json()['refresh_token'] == 'refresh'
    assert login.headers['cache-control'] == 'no-store'
    provider.sign_in_with_password.side_effect = AuthApiError('secret provider error', 400, 'invalid_credentials')
    assert client.post('/auth/login', json=data).json() == {'error': 'Invalid login credentials'}


@pytest.mark.parametrize('route', ['/protected/profile', '/protected/dashboard', '/auth/logout'])
@pytest.mark.parametrize('header', [None, 'Basic abc', 'Bearer', 'Bearer a b', 'raw-token'])
def test_missing_malformed_tokens(api, route, header):
    client, provider = api
    result = client.request('POST' if route.endswith('logout') else 'GET', route,
                            headers={} if header is None else {'Authorization': header})
    assert result.status_code == 401
    assert result.json() == {'error': 'Access token required'}
    provider.get_user.assert_not_called()


def test_verified_routes_logout_and_rejection(api):
    client, provider = api
    headers = {'Authorization': 'Bearer valid'}
    assert client.get('/protected/profile', headers=headers).json()['id'] == 'user-a'
    assert client.get('/protected/dashboard', headers=headers).status_code == 200
    result = client.post('/auth/logout', headers=headers)
    assert result.status_code == 204 and result.content == b''
    provider.admin.sign_out.assert_called_once_with('valid', scope='local')
    provider.get_user.side_effect = AuthApiError('tampered', 401, 'bad_jwt')
    assert client.get('/protected/profile', headers=headers).json() == {'error': 'Invalid or expired token'}
    assert client.get('/protected/dashboard', headers=headers).status_code == 401
    assert client.post('/auth/logout', headers=headers).status_code == 401
    provider.admin.sign_out.assert_called_once()


def test_provider_outage_and_empty_user(api):
    client, provider = api
    provider.get_user.return_value = SimpleNamespace(user=None)
    assert client.get('/protected/profile', headers={'Authorization': 'Bearer invalid'}).status_code == 401
    provider.get_user.side_effect = httpx.ConnectError('network')
    assert client.get('/protected/profile', headers={'Authorization': 'Bearer valid'}).status_code == 503


def test_public_and_swagger(api):
    client, _ = api
    assert client.get('/public/info').json() == {'message': 'Welcome stranger! This info is public.'}
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    assert schema['components']['securitySchemes']['HTTPBearer']['scheme'] == 'bearer'
    for route, method in [('/protected/profile', 'get'), ('/protected/dashboard', 'get'), ('/auth/logout', 'post')]:
        assert schema['paths'][route][method]['security'] == [{'HTTPBearer': []}]
    assert 'security' not in schema['paths']['/public/info']['get']


def test_missing_config_does_not_break_existing_app(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_KEY', raising=False)
    with TestClient(main.app) as client:
        assert client.get('/health').status_code == 200
        assert client.get('/protected/profile').status_code == 401
        assert client.get('/protected/profile', headers={'Authorization': 'Bearer valid'}).status_code == 503
