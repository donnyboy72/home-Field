"""Direct API permission tests; every app uses pytest's temporary database."""
import sqlite3

import pytest

from app import create_app
from db import get_database

PASSWORD = 'permission-test-password'


def register(client, username):
    response = client.post('/api/auth/signup', json={'username': username, 'password': PASSWORD})
    assert response.status_code == 201
    return response.get_json()['user']


def login(client, username):
    token = client.post('/api/auth/login', json={'username': username, 'password': PASSWORD}).get_json()['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def host(app, client):
    user = register(client, 'administrator')
    result = app.test_cli_runner().invoke(args=['setup-host', 'administrator'])
    assert result.exit_code == 0
    client.environ_base['HTTP_AUTHORIZATION'] = login(client, 'administrator')['Authorization']
    return client, user


DATA_REQUESTS = [
    ('get', '/api/tasks'), ('get', '/api/tasks/1'), ('get', '/api/tasks/deleted'),
    ('post', '/api/tasks'), ('patch', '/api/tasks/1'), ('delete', '/api/tasks/1'),
    ('post', '/api/tasks/1/restore'), ('get', '/api/projects'),
    ('get', '/api/projects/1'), ('post', '/api/projects'),
    ('put', '/api/projects/1'), ('patch', '/api/projects/1'), ('delete', '/api/projects/1'),
    ('get', '/api/users'), ('patch', '/api/users/1'), ('delete', '/api/users/1'),
]


@pytest.mark.parametrize('method,path', DATA_REQUESTS)
@pytest.mark.parametrize('credential', [None, 'Bearer forged', 'host'])
def test_all_data_requires_session(client, method, path, credential):
    headers = {'Authorization': credential} if credential else {}
    assert getattr(client, method)(path, headers=headers, json={}).status_code == 401


def test_setup_and_role_spoofing(app, client, auth_headers):
    assert client.get('/api/auth/me', headers=auth_headers).get_json()['user']['role'] == 'user'
    for role in ('host', 'manager', 'user'):
        assert client.post('/api/auth/signup', json={
            'username': 'intruder', 'password': PASSWORD, 'role': role,
        }).status_code == 400
    runner = app.test_cli_runner()
    assert runner.invoke(args=['setup-host', 'missing']).exit_code != 0
    assert runner.invoke(args=['setup-host', 'dummy_user']).exit_code == 0
    # Existing sessions fetch the current database role on every request.
    assert client.get('/api/users', headers=auth_headers).status_code == 200
    register(client, 'another')
    assert runner.invoke(args=['setup-host', 'another']).exit_code != 0
    assert client.post('/api/auth/setup-host', json={'username': 'another'}).status_code == 404


def test_user_management_denied_to_nonhost(client, auth_headers):
    for method, path in [('get', '/api/users'), ('patch', '/api/users/1'), ('delete', '/api/users/1')]:
        headers = {**auth_headers, 'X-Role': 'host', 'X-Forwarded-For': '127.0.0.1'}
        assert getattr(client, method)(path, headers=headers, json={'role': 'host'}).status_code == 403


def test_host_users_and_safe_deletion(host, app):
    client, administrator = host
    other = register(client, 'other_user')
    other_session = login(client, 'other_user')
    second_session = login(client, 'other_user')
    assert client.patch(f"/api/users/{other['id']}/role", json={'role': 'manager'}).status_code == 200
    project = client.post('/api/projects', json={'name': 'Preserved'}, headers=other_session).get_json()['project']
    task = client.post('/api/tasks', headers=other_session, json={
        'title': 'Preserved', 'project_id': project['id'], 'assigned_to': other['id'],
    }).get_json()['task']
    deleted_task = client.post('/api/tasks', json={'title': 'Deleted assignment', 'assigned_to': other['id']}).get_json()['task']
    client.delete(f"/api/tasks/{deleted_task['id']}")
    users = client.get('/api/users').get_json()['users']
    assert len(users) == 2 and all('password_hash' not in user for user in users)
    assert client.patch(f"/api/users/{other['id']}", json={'username': 'renamed'}).status_code == 200
    assert client.patch(f"/api/users/{other['id']}", json={'role': 'host'}).status_code == 400
    assert client.delete(f"/api/users/{administrator['id']}").status_code == 403
    assert client.delete(f"/api/users/{other['id']}").status_code == 204
    for headers in (other_session, second_session):
        assert client.get('/api/tasks', headers=headers).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'renamed', 'password': PASSWORD}).status_code == 401
    saved = client.get(f"/api/tasks/{task['id']}").get_json()['task']
    assert saved['assigned_to'] is None and saved['created_by'] == other['id']
    assert saved['project_id'] == project['id']
    assert client.get(f"/api/projects/{project['id']}").status_code == 200
    assert client.post(f"/api/tasks/{deleted_task['id']}/restore").get_json()['task']['assigned_to'] is None
    assert client.delete(f"/api/users/{other['id']}").status_code == 404
    with app.app_context():
        assert get_database().execute('SELECT count(*) FROM session WHERE user_id = ?', (other['id'],)).fetchone()[0] == 0


def test_host_task_and_project_workflow(host):
    client, _ = host
    project = client.post('/api/projects', json={'name': 'Host project'}).get_json()['project']
    project_url = f"/api/projects/{project['id']}"
    assert client.patch(project_url, json={'name': 'Edited'}).status_code == 200
    task = client.post('/api/tasks', json={'title': 'Host task', 'project_id': project['id']}).get_json()['task']
    url = f"/api/tasks/{task['id']}"
    assert client.patch(url, json={'status': 'done'}).status_code == 200
    assert client.get(url).get_json()['task']['status'] == 'done'
    assert client.delete(url).status_code == 204
    assert client.get('/api/tasks/deleted').get_json()['tasks'][0]['id'] == task['id']
    assert client.post(url + '/restore').status_code == 200
    assert client.delete(project_url).status_code == 204
    assert client.get(url).status_code == 200


def test_user_migration_preserves_accounts_and_sessions(tmp_path):
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE user (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)')
        db.execute("INSERT INTO user VALUES (7, 'legacy', 'original-hash', 'original-time')")
    config = {'TESTING': True, 'DATABASE': str(path)}
    for _ in range(2):
        app = create_app(config)
        with app.app_context():
            row = get_database().execute('SELECT * FROM user WHERE id = 7').fetchone()
            assert dict(row) == {'id': 7, 'username': 'legacy', 'password_hash': 'original-hash', 'created_at': 'original-time', 'role': 'user'}


def test_expired_and_logged_out_sessions_cannot_read(host, app):
    client, _ = host
    headers = login(client, 'administrator')
    assert client.post('/api/auth/logout', headers=headers).status_code == 204
    assert client.get('/api/users', headers=headers).status_code == 401
    with app.app_context():
        db = get_database()
        db.execute("UPDATE session SET expires_at = '2000-01-01T00:00:00+00:00'")
        db.commit()
    assert client.get('/api/tasks').status_code == 401
