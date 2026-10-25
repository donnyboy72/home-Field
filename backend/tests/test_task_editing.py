"""Partial task edits must persist, validate inputs, and preserve server fields."""
import pytest
from app import create_app


def create(client):
    project = client.post('/api/projects', json={'name': 'Editing'}).get_json()['project']
    return client.post('/api/tasks', json={
        'title': 'Original', 'description': 'Keep description',
        'deadline': '2026-11-01', 'status': 'todo', 'project_id': project['id'],
    }).get_json()['task']


def test_partial_edit_persists(authenticated_client, app):
    client = authenticated_client
    original = create(client)
    url = f"/api/tasks/{original['id']}"
    response = client.patch(url, json={'title': '  Edited title  '})
    assert response.status_code == 200
    edited = response.get_json()['task']
    assert edited['title'] == 'Edited title'
    assert edited['updated_at'] > original['updated_at']
    for field in original:
        if field not in ('title', 'updated_at'):
            assert edited[field] == original[field]
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert restarted.get(url).get_json()['task'] == edited


def test_edit_all_fields_and_clear_nullable_values(authenticated_client):
    client = authenticated_client
    user = client.post('/api/auth/signup', json={
        'username': 'assignee', 'password': 'AnotherTestPassword123!'
    }).get_json()['user']
    original = create(client)
    url = f"/api/tasks/{original['id']}"
    patch = {'title': 'Changed', 'description': 'Details', 'status': 'done',
             'deadline': '2026-12-01', 'assigned_to': user['id']}
    response = client.patch(url, json=patch)
    assert response.status_code == 200
    edited = response.get_json()['task']
    for field, value in patch.items():
        assert edited[field] == value
    cleared = client.patch(url, json={'deadline': None, 'assigned_to': None, 'description': ''})
    assert cleared.status_code == 200
    assert cleared.get_json()['task']['deadline'] is None
    assert cleared.get_json()['task']['assigned_to'] is None
    assert cleared.get_json()['task']['description'] == ''


@pytest.mark.parametrize('payload', [
    {}, [], 'text', {'title': ''}, {'title': '  '}, {'title': None},
    {'description': None}, {'status': []}, {'status': {}}, {'status': None},
    {'status': 'invalid'}, {'deadline': ''}, {'deadline': 123},
    {'assigned_to': True}, {'assigned_to': -1}, {'assigned_to': 99999},
    {'id': 99}, {'created_by': 99}, {'project_id': 99},
    {'is_deleted': True}, {'deleted_at': 'today'}, {'created_at': 'today'},
    {'updated_at': 'today'}, {'title': 'Changed', 'unknown': 'value'},
])
def test_invalid_edit_does_not_change_task(authenticated_client, payload):
    client = authenticated_client
    original = create(client)
    url = f"/api/tasks/{original['id']}"
    response = client.patch(url, json=payload)
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert client.get(url).get_json()['task'] == original


def test_missing_and_deleted_tasks(authenticated_client):
    client = authenticated_client
    assert client.patch('/api/tasks/99999', json={'title': 'Edit'}).status_code == 404
    original = create(client)
    url = f"/api/tasks/{original['id']}"
    client.delete(url)
    assert client.patch(url, json={'title': 'Edit'}).status_code == 404
    assert client.post(url + '/restore').get_json()['task']['title'] == 'Original'


def test_edit_requires_login(client):
    assert client.patch('/api/tasks/1', json={'title': 'Edit'}).status_code == 401
    assert client.patch('/api/tasks/1', json={'title': 'Edit'},
                        headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_malformed_json(authenticated_client):
    client = authenticated_client
    original = create(client)
    response = client.patch(f"/api/tasks/{original['id']}",
                            data='{', content_type='application/json')
    assert response.status_code == 400
