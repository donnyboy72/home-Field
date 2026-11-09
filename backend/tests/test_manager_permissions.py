"""Manager authorization and data-preserving role migration tests."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from db import get_database
from users import hash_token
from test_host_permissions import host, login, register  # noqa: F401


@pytest.fixture
def manager(host):
    client, administrator = host
    user = register(client, 'manager_account')
    headers = login(client, 'manager_account')
    assert client.patch(f"/api/users/{user['id']}/role", json={'role': 'manager'}).status_code == 200
    return client, administrator, user, headers


def test_role_changes_apply_to_existing_sessions(host):
    client, _ = host
    user = register(client, 'candidate')
    sessions = [login(client, 'candidate'), login(client, 'candidate')]
    url = f"/api/users/{user['id']}/role"
    for headers in sessions:
        assert client.get('/api/users', headers=headers).status_code == 403
    promoted = client.patch(url, json={'role': 'manager'})
    assert promoted.status_code == 200
    assert promoted.get_json()['user']['role'] == 'manager'
    for headers in sessions:
        assert client.get('/api/users', headers=headers).status_code == 200
        assert client.get('/api/auth/me', headers=headers).get_json()['user']['role'] == 'manager'
    assert client.patch(url, json={'role': 'user'}).status_code == 200
    for headers in sessions:
        assert client.get('/api/users', headers=headers).status_code == 403
        assert client.patch(f"/api/users/{user['id']}", headers=headers, json={'username': 'changed'}).status_code == 403
        assert client.get('/api/auth/me', headers=headers).get_json()['user']['role'] == 'user'


def test_manager_user_permissions(manager):
    client, administrator, user, headers = manager
    other = register(client, 'another_user')
    second = register(client, 'second_manager')
    assert client.patch(f"/api/users/{second['id']}/role", json={'role': 'manager'}).status_code == 200
    listed = client.get('/api/users', headers=headers)
    assert listed.status_code == 200
    assert len(listed.get_json()['users']) == 4
    assert all('password_hash' not in row for row in listed.get_json()['users'])
    for target in (user, other, second):
        assert client.patch(f"/api/users/{target['id']}", headers=headers,
                            json={'username': target['username']}).status_code == 200
    host_url = f"/api/users/{administrator['id']}"
    assert client.patch(host_url, headers=headers, json={'username': 'hijacked'}).status_code == 403
    assert client.get('/api/auth/me').get_json()['user']['username'] == 'administrator'
    for target in (administrator, user, other, second):
        url = f"/api/users/{target['id']}"
        assert client.delete(url, headers=headers).status_code == 403
        for role in ('user', 'manager', 'host'):
            assert client.patch(url + '/role', headers=headers, json={'role': role}).status_code == 403
            # The username endpoint must not become an alternate role API.
            assert client.patch(url, headers=headers, json={'role': role}).status_code == 400
    assert client.delete(f"/api/users/{second['id']}").status_code == 204


def test_manager_accesses_all_projects_and_tasks(manager):
    client, _, user, headers = manager
    # This project belongs to the shared host data; no membership is granted.
    project = client.post('/api/projects', json={'name': 'Host created'}).get_json()['project']
    project_url = f"/api/projects/{project['id']}"
    assert client.get(project_url, headers=headers).status_code == 200
    assert client.get('/api/projects', headers=headers).get_json()['projects'] == [project]
    assert client.patch(project_url, headers=headers, json={'name': 'Manager edited'}).status_code == 200
    assert client.put(project_url, headers=headers, json={'name': 'Edited again'}).status_code == 200
    created = client.post('/api/projects', headers=headers, json={'name': 'Manager created'})
    assert created.status_code == 201
    task = client.post('/api/tasks', json={'title': 'Host task', 'project_id': project['id']}).get_json()['task']
    url = f"/api/tasks/{task['id']}"
    assert client.get(url, headers=headers).status_code == 200
    assert client.get('/api/tasks', headers=headers).get_json()['tasks'] == [task]
    assert client.patch(url, headers=headers, json={'title': 'Manager edit', 'status': 'done', 'assigned_to': user['id']}).status_code == 200
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get('/api/tasks/deleted', headers=headers).get_json()['tasks'][0]['id'] == task['id']
    assert client.post(url + '/restore', headers=headers).status_code == 200
    new_task = client.post('/api/tasks', headers=headers, json={'title': 'Manager task', 'project_id': project['id']})
    assert new_task.status_code == 201
    assert new_task.get_json()['task']['created_by'] == user['id']
    assert client.delete(project_url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 200


def test_manager_obeys_recovery_window(manager, app):
    client, _, _, headers = manager
    task = client.post('/api/tasks', json={'title': 'Expired'}).get_json()['task']
    url = f"/api/tasks/{task['id']}"
    assert client.delete(url, headers=headers).status_code == 204
    with app.app_context():
        database = get_database()
        database.execute('UPDATE task SET deleted_at = ? WHERE id = ?',
                         ((datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(), task['id']))
        database.commit()
    assert client.post(url + '/restore', headers=headers).status_code == 410


@pytest.mark.parametrize('payload', [None, [], {}, {'role': 'host'}, {'role': 'owner'},
                                    {'role': None}, {'role': True}, {'role': []},
                                    {'role': 'manager', 'username': 'extra'}])
def test_host_role_validation(host, payload):
    client, _ = host
    user = register(client, 'candidate')
    assert client.patch(f"/api/users/{user['id']}/role", json=payload).status_code == 400
    assert client.get('/api/users').get_json()['users'][1]['role'] == 'user'


def test_host_role_is_immutable_and_missing_users(host):
    client, administrator = host
    for role in ('user', 'manager'):
        assert client.patch(f"/api/users/{administrator['id']}/role", json={'role': role}).status_code == 403
    for user_id in (0, 999, 9223372036854775808):
        assert client.patch(f'/api/users/{user_id}/role', json={'role': 'manager'}).status_code == 404


@pytest.mark.parametrize('credential', [None, 'Bearer forged'])
def test_role_endpoint_requires_authentication(client, credential):
    headers = {'Authorization': credential} if credential else {}
    assert client.patch('/api/users/1/role', headers=headers, json={'role': 'manager'}).status_code == 401


def test_step1_migration_preserves_data_sessions_and_sequence(tmp_path):
    path = tmp_path / 'step1.db'
    token = 'existing-session'
    with sqlite3.connect(path) as database:
        database.executescript("""
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'host')),
                created_at TEXT NOT NULL);
            CREATE UNIQUE INDEX one_host ON user(role) WHERE role = 'host';
            CREATE TABLE session (token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES user(id), expires_at TEXT NOT NULL);
            INSERT INTO user VALUES (3, 'administrator', 'saved-hash', 'host', 'saved-time');
            INSERT INTO user VALUES (8, 'ordinary', 'another-hash', 'user', 'saved-time');
            INSERT INTO user VALUES (99, 'deleted', 'old-hash', 'user', 'saved-time');
            DELETE FROM user WHERE id = 99;
        """)
        database.execute('INSERT INTO session VALUES (?, 3, ?)',
                         (hash_token(token), (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
    for _ in range(2):
        app = create_app({'TESTING': True, 'DATABASE': str(path)})
        client = app.test_client()
        headers = {'Authorization': f'Bearer {token}'}
        assert client.get('/api/users', headers=headers).status_code == 200
        with app.app_context():
            database = get_database()
            assert database.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert database.execute('PRAGMA foreign_key_check').fetchall() == []
            assert dict(database.execute('SELECT * FROM user WHERE id = 3').fetchone()) == {
                'id': 3, 'username': 'administrator', 'password_hash': 'saved-hash',
                'role': 'host', 'created_at': 'saved-time',
            }
            assert database.execute("SELECT seq FROM sqlite_sequence WHERE name = 'user'").fetchone()[0] == 99
            with pytest.raises(sqlite3.IntegrityError):
                database.execute("UPDATE user SET role = 'host' WHERE id = 8")
            database.rollback()
        assert client.patch('/api/users/8/role', headers=headers, json={'role': 'manager'}).status_code == 200
        assert client.patch('/api/users/8/role', headers=headers, json={'role': 'user'}).status_code == 200
    assert register(client, 'new_account')['id'] > 99
