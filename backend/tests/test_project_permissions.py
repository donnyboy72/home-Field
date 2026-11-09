"""Ordinary-user permissions are enforced with direct API requests."""
import sqlite3

import pytest

from app import create_app
from db import get_database
from test_host_permissions import host, login, register  # noqa: F401


@pytest.fixture
def workspace(host):
    client, administrator = host
    ordinary = register(client, 'ordinary_user')
    colleague = register(client, 'colleague')
    outsider = register(client, 'outsider')
    manager = register(client, 'project_manager')
    assert client.patch(f"/api/users/{manager['id']}/role", json={'role': 'manager'}).status_code == 200
    projects = [client.post('/api/projects', json={'name': name}).get_json()['project']
                for name in ('Allowed', 'Private')]
    task = client.post('/api/tasks', json={'title': 'Allowed task', 'project_id': projects[0]['id']}).get_json()['task']
    hidden = client.post('/api/tasks', json={'title': 'Private task', 'project_id': projects[1]['id']}).get_json()['task']
    unassigned = client.post('/api/tasks', json={'title': 'No project'}).get_json()['task']
    for user in (ordinary, colleague):
        assert client.put(f"/api/projects/{projects[0]['id']}/members/{user['id']}").status_code == 204
    return dict(client=client, administrator=administrator, ordinary=ordinary,
                colleague=colleague, outsider=outsider, manager=manager,
                projects=projects, task=task, hidden=hidden, unassigned=unassigned,
                headers=login(client, ordinary['username']),
                manager_headers=login(client, manager['username']))


FORBIDDEN = [
    ('post', '/api/tasks'), ('delete', '/api/tasks/{task}'),
    ('post', '/api/tasks/{task}/restore'), ('get', '/api/tasks/deleted'),
    ('post', '/api/projects'), ('patch', '/api/projects/{project}'),
    ('put', '/api/projects/{project}'), ('delete', '/api/projects/{project}'),
    ('get', '/api/users'), ('delete', '/api/users/{user}'),
    ('patch', '/api/users/{user}'), ('patch', '/api/users/{user}/role'),
    ('get', '/api/projects/{project}/members'),
    ('put', '/api/projects/{project}/members/{user}'),
    ('delete', '/api/projects/{project}/members/{user}'),
]


@pytest.mark.parametrize('method,path', FORBIDDEN)
def test_ordinary_user_cannot_manage_resources(workspace, method, path):
    w = workspace
    url = path.format(task=w['task']['id'], project=w['projects'][0]['id'], user=w['ordinary']['id'])
    headers = {**w['headers'], 'X-Role': 'host', 'X-Forwarded-For': '127.0.0.1'}
    response = getattr(w['client'], method)(url, headers=headers,
        json={'title': 'Forged', 'name': 'Forged', 'role': 'manager', 'username': 'forged'})
    assert response.status_code == 403
    assert 'error' in response.get_json()
    assert w['client'].get(f"/api/tasks/{w['task']['id']}").get_json()['task'] == w['task']
    assert w['client'].get(f"/api/projects/{w['projects'][0]['id']}").get_json()['project'] == w['projects'][0]


def test_visibility_and_permitted_editing(workspace):
    w = workspace
    client, headers = w['client'], w['headers']
    assert client.get('/api/auth/me', headers=headers).get_json()['user']['role'] == 'user'
    assert client.get('/api/projects', headers=headers).get_json()['projects'] == [w['projects'][0]]
    assert client.get('/api/tasks', headers=headers).get_json()['tasks'] == [w['task']]
    assert client.get(f"/api/tasks?project_id={w['projects'][0]['id']}", headers=headers).get_json()['tasks'] == [w['task']]
    assert client.get('/api/tasks?project_id=unassigned', headers=headers).get_json()['tasks'] == []
    for project_id in (w['projects'][1]['id'], 999):
        assert client.get(f'/api/projects/{project_id}', headers=headers).status_code == 404
        assert client.get(f'/api/tasks?project_id={project_id}', headers=headers).status_code == 404
        assert client.get(f'/api/projects/{project_id}/assignees', headers=headers).status_code == 404
    for task in (w['hidden'], w['unassigned']):
        url = f"/api/tasks/{task['id']}"
        assert client.get(url, headers=headers).status_code == 404
        assert client.patch(url, headers=headers, json={'title': 'Intrusion'}).status_code == 404
        assert client.get(url).get_json()['task'] == task
    url = f"/api/tasks/{w['task']['id']}"
    patch = {'title': 'Edited', 'description': 'Details', 'deadline': '2026-11-05',
             'status': 'review', 'assigned_to': w['colleague']['id']}
    response = client.patch(url, headers=headers, json=patch)
    assert response.status_code == 200
    assert all(response.get_json()['task'][key] == value for key, value in patch.items())
    for status in ('todo', 'in_progress', 'done'):
        assert client.patch(url, headers=headers, json={'status': status}).status_code == 200
    assert client.patch(url, headers=headers, json={'assigned_to': None}).status_code == 200
    assert client.patch(url, headers=headers, json={'project_id': w['projects'][1]['id']}).status_code == 400
    assert client.patch(url, headers=headers, json={'is_deleted': True}).status_code == 400


def test_assignment_restrictions_apply_to_every_role(workspace):
    w = workspace
    client = w['client']
    project_id = w['projects'][0]['id']
    users = client.get(f'/api/projects/{project_id}/assignees', headers=w['headers']).get_json()['users']
    assert {user['id'] for user in users} == {w[key]['id'] for key in ('administrator', 'manager', 'ordinary', 'colleague')}
    assert all(set(user) == {'id', 'username'} for user in users)
    url = f"/api/tasks/{w['task']['id']}"
    for headers in (w['headers'], w['manager_headers'], {}):
        response = client.patch(url, headers=headers, json={'assigned_to': w['outsider']['id']})
        assert response.status_code == 400
        assert client.get(url).get_json()['task']['assigned_to'] is None
        for key in ('administrator', 'manager', 'ordinary', 'colleague'):
            assert client.patch(url, headers=headers, json={'assigned_to': w[key]['id']}).status_code == 200
        assert client.patch(url, headers=headers, json={'assigned_to': None}).status_code == 200
    for headers in ({}, w['manager_headers']):
        assert client.post('/api/tasks', headers=headers, json={
            'title': 'Bad assignment', 'project_id': project_id, 'assigned_to': w['outsider']['id'],
        }).status_code == 400
        assert client.post('/api/tasks', headers=headers, json={
            'title': 'No project', 'assigned_to': w['ordinary']['id'],
        }).status_code == 400


@pytest.mark.parametrize('actor', ['host', 'manager'])
def test_grant_and_revoke_apply_to_existing_sessions(workspace, actor):
    w = workspace
    client = w['client']
    headers = {} if actor == 'host' else w['manager_headers']
    url = f"/api/projects/{w['projects'][1]['id']}/members/{w['ordinary']['id']}"
    task_url = f"/api/tasks/{w['hidden']['id']}"
    assert client.put(url, headers=headers).status_code == 204
    assert client.put(url, headers=headers).status_code == 204
    assert client.get(task_url, headers=w['headers']).status_code == 200
    assert client.patch(task_url, headers=w['headers'], json={'assigned_to': w['ordinary']['id']}).status_code == 200
    deleted = client.post('/api/tasks', json={'title': 'Deleted', 'project_id': w['projects'][1]['id'], 'assigned_to': w['ordinary']['id']}).get_json()['task']
    assert client.delete(f"/api/tasks/{deleted['id']}").status_code == 204
    assert client.delete(url, headers=headers).status_code == 204
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(task_url, headers=w['headers']).status_code == 404
    assert client.patch(task_url, headers=w['headers'], json={'title': 'Revoked'}).status_code == 404
    assert client.get(task_url).get_json()['task']['assigned_to'] is None
    assert client.post(f"/api/tasks/{deleted['id']}/restore").get_json()['task']['assigned_to'] is None
    assert client.get('/api/projects', headers=w['headers']).get_json()['projects'] == [w['projects'][0]]


def test_deleted_project_and_creator_assignment_do_not_grant_access(workspace, app):
    w = workspace
    client = w['client']
    # Existing authored/assigned records must not bypass explicit project access.
    with app.app_context():
        database = get_database()
        database.execute('UPDATE task SET created_by = ?, assigned_to = ? WHERE id = ?',
                         (w['ordinary']['id'], w['ordinary']['id'], w['hidden']['id']))
        database.commit()
    assert client.get(f"/api/tasks/{w['hidden']['id']}", headers=w['headers']).status_code == 404
    assert client.delete(f"/api/projects/{w['projects'][0]['id']}").status_code == 204
    assert client.get('/api/tasks', headers=w['headers']).get_json()['tasks'] == []
    assert client.get('/api/projects', headers=w['headers']).get_json()['projects'] == []
    assert client.patch(f"/api/tasks/{w['task']['id']}", headers=w['headers'], json={'status': 'done'}).status_code == 404
    assert client.get(f"/api/tasks/{w['task']['id']}").status_code == 200


def test_demotion_loses_implicit_access_and_clears_inaccessible_assignments(workspace):
    w = workspace
    client = w['client']
    for task in (w['task'], w['hidden'], w['unassigned']):
        assert client.patch(f"/api/tasks/{task['id']}", json={'assigned_to': w['manager']['id']}).status_code == 200
    assert client.patch(f"/api/users/{w['manager']['id']}/role", json={'role': 'user'}).status_code == 200
    assert client.get('/api/tasks', headers=w['manager_headers']).get_json()['tasks'] == []
    assert client.delete(f"/api/tasks/{w['task']['id']}", headers=w['manager_headers']).status_code == 403
    assert all(client.get(f"/api/tasks/{task['id']}").get_json()['task']['assigned_to'] is None
               for task in (w['task'], w['hidden'], w['unassigned']))
    assert client.put(f"/api/projects/{w['projects'][0]['id']}/members/{w['manager']['id']}").status_code == 204
    assert client.get(f"/api/tasks/{w['task']['id']}", headers=w['manager_headers']).status_code == 200


@pytest.mark.parametrize('credential', [None, 'Bearer forged'])
@pytest.mark.parametrize('method,path', [
    ('get', '/api/projects/1/members'), ('get', '/api/projects/1/assignees'),
    ('put', '/api/projects/1/members/1'), ('delete', '/api/projects/1/members/1'),
])
def test_membership_endpoints_require_authentication(client, credential, method, path):
    headers = {'Authorization': credential} if credential else {}
    assert getattr(client, method)(path, headers=headers).status_code == 401


def test_membership_validation_and_user_deletion(workspace):
    w = workspace
    client = w['client']
    project_id = w['projects'][0]['id']
    for user_id in (999, 9223372036854775808):
        assert client.put(f'/api/projects/{project_id}/members/{user_id}').status_code == 404
    for user_id in (w['administrator']['id'], w['manager']['id']):
        assert client.put(f'/api/projects/{project_id}/members/{user_id}').status_code == 400
        assert client.delete(f'/api/projects/{project_id}/members/{user_id}').status_code == 400
    assert client.put(f"/api/projects/999/members/{w['ordinary']['id']}").status_code == 404
    assert client.delete(f"/api/users/{w['ordinary']['id']}").status_code == 204
    members = client.get(f'/api/projects/{project_id}/members').get_json()['users']
    assert members == [{'id': w['colleague']['id'], 'username': w['colleague']['username']}]
    assert client.get('/api/tasks', headers=w['headers']).status_code == 401


def test_membership_migration_preserves_existing_data(workspace, app):
    w = workspace
    path = app.config['DATABASE']
    with sqlite3.connect(path) as database:
        # Simulate a Step 2 database: retain everything except the new table.
        database.execute('DROP TABLE project_member')
        before = {table: database.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
                  for table in ('user', 'session', 'project', 'task')}
    for _ in range(2):
        restarted = create_app({'TESTING': True, 'DATABASE': path}).test_client()
        assert restarted.get('/api/projects', headers=w['headers']).get_json()['projects'] == []
        with sqlite3.connect(path) as database:
            assert before == {table: database.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
                              for table in before}
    host_headers = {'Authorization': w['client'].environ_base['HTTP_AUTHORIZATION']}
    url = f"/api/projects/{w['projects'][0]['id']}/members/{w['ordinary']['id']}"
    assert restarted.put(url, headers=host_headers).status_code == 204
    restarted = create_app({'TESTING': True, 'DATABASE': path}).test_client()
    assert restarted.get('/api/tasks', headers=w['headers']).get_json()['tasks'] == [w['task']]


def test_ordinary_cannot_restore_deleted_task_even_with_project_access(workspace):
    w = workspace
    url = f"/api/tasks/{w['task']['id']}"
    assert w['client'].delete(url).status_code == 204
    assert w['client'].post(url + '/restore', headers=w['headers']).status_code == 403
    assert w['client'].get('/api/tasks/deleted', headers=w['headers']).status_code == 403
    assert w['client'].get(url, headers=w['headers']).status_code == 404
    assert w['client'].post(url + '/restore').status_code == 200


def test_explicit_membership_survives_promotion_and_demotion(workspace):
    w = workspace
    client = w['client']
    role_url = f"/api/users/{w['ordinary']['id']}/role"
    assert client.patch(role_url, json={'role': 'manager'}).status_code == 200
    assert len(client.get('/api/projects', headers=w['headers']).get_json()['projects']) == 2
    task_url = f"/api/tasks/{w['task']['id']}"
    assert client.patch(task_url, headers=w['headers'], json={'assigned_to': w['ordinary']['id']}).status_code == 200
    assert client.patch(role_url, json={'role': 'user'}).status_code == 200
    assert client.get('/api/projects', headers=w['headers']).get_json()['projects'] == [w['projects'][0]]
    assert client.get(task_url, headers=w['headers']).get_json()['task']['assigned_to'] == w['ordinary']['id']
    assert client.post('/api/tasks', headers=w['headers'], json={'title': 'Cannot create'}).status_code == 403
