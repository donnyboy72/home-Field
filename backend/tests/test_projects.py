"""Project views select only their own active tasks in the host database."""
import pytest

from app import create_app


def test_project_workflow_and_isolation(authenticated_client, app):
    client = authenticated_client
    a = client.post('/api/projects', json={'name': '  Project A  '}).get_json()['project']
    b = client.post('/api/projects', json={'name': 'Project B'}).get_json()['project']
    assert a['name'] == 'Project A'
    assert a['created_at'].endswith('+00:00')
    assert client.get('/api/projects').get_json() == {'projects': [a, b]}

    def task(title, project_id):
        response = client.post('/api/tasks', json={'title': title, 'project_id': project_id})
        assert response.status_code == 201
        return response.get_json()['task']

    ta = task('A task', a['id'])
    tb = task('B task', b['id'])
    unassigned = task('Unassigned', None)
    deleted = task('Deleted A task', a['id'])
    client.delete(f"/api/tasks/{deleted['id']}")
    assert client.get(f"/api/tasks?project_id={a['id']}").get_json()['tasks'] == [ta]
    assert client.get(f"/api/tasks?project_id={b['id']}").get_json()['tasks'] == [tb]
    assert client.get('/api/tasks?project_id=unassigned').get_json()['tasks'] == [unassigned]
    assert client.get('/api/tasks').get_json()['tasks'] == [ta, tb, unassigned]
    restored = client.post(f"/api/tasks/{deleted['id']}/restore").get_json()["task"]
    assert client.get(f"/api/tasks?project_id={a['id']}").get_json()['tasks'] == [ta, restored]

    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert restarted.get('/api/projects').get_json()['projects'] == [a, b]
    assert restarted.get(f"/api/tasks?project_id={b['id']}").get_json()['tasks'] == [tb]


@pytest.mark.parametrize('payload', [None, [], 'text', {}, {'name': ''}, {'name': '  '}, {'name': 4}])
def test_invalid_projects(authenticated_client, payload):
    response = authenticated_client.post('/api/projects', json=payload)
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert authenticated_client.get('/api/projects').get_json()['projects'] == []


def test_project_creation_requires_login(client):
    assert client.post('/api/projects', json={'name': 'Private'}).status_code == 401


@pytest.mark.parametrize('value', ['', '0', '-1', 'true', 'null', '1.5', 'abc', '9223372036854775808', '9' * 5000])
def test_invalid_project_filter(client, value):
    response = client.get('/api/tasks', query_string={'project_id': value})
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_unknown_project_and_duplicate_filter(authenticated_client):
    client = authenticated_client
    assert client.get('/api/tasks?project_id=999').status_code == 404
    assert client.get('/api/tasks?project_id=1&project_id=2').status_code == 400
    response = client.post('/api/tasks', json={'title': 'Invalid reference', 'project_id': 999})
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Project does not exist'}
    assert client.get('/api/tasks').get_json()['tasks'] == []


@pytest.mark.parametrize('method', ['put', 'patch'])
def test_edit_project(authenticated_client, app, method):
    client = authenticated_client
    original = client.post('/api/projects', json={'name': 'Original'}).get_json()['project']
    response = getattr(client, method)(f"/api/projects/{original['id']}", json={'name': '  Renamed  '})
    assert response.status_code == 200
    edited = response.get_json()['project']
    assert edited['name'] == 'Renamed'
    assert edited['updated_at'] > original['updated_at']
    for field in ('id', 'created_at', 'is_deleted', 'deleted_at'):
        assert edited[field] == original[field]
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert restarted.get('/api/projects').get_json()['projects'] == [edited]


@pytest.mark.parametrize('payload', [
    None, [], {}, {'name': ''}, {'name': '  '}, {'name': None}, {'name': 12},
    {'name': 'Changed', 'id': 99}, {'name': 'Changed', 'is_deleted': True},
    {'name': 'Changed', 'created_at': 'yesterday'},
    {'name': 'Changed', 'updated_at': 'tomorrow'},
    {'name': 'Changed', 'deleted_at': 'today'}, {'name': 'Changed', 'unknown': 1},
])
def test_invalid_edit_preserves_project(authenticated_client, payload):
    client = authenticated_client
    original = client.post('/api/projects', json={'name': 'Original'}).get_json()['project']
    response = client.patch(f"/api/projects/{original['id']}", json=payload)
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert client.get('/api/projects').get_json()['projects'] == [original]


def test_project_delete_preserves_tasks(authenticated_client, app):
    from db import get_database

    client = authenticated_client
    project = client.post('/api/projects', json={'name': 'Archive'}).get_json()['project']
    other = client.post('/api/projects', json={'name': 'Other'}).get_json()['project']
    task = client.post('/api/tasks', json={
        'title': 'Preserve me', 'project_id': project['id'],
    }).get_json()['task']
    url = f"/api/projects/{project['id']}"
    response = client.delete(url)
    assert response.status_code == 204
    assert response.data == b''
    assert client.get('/api/projects').get_json()['projects'] == [other]
    assert client.get(f"/api/tasks?project_id={project['id']}").status_code == 404
    assert client.post('/api/tasks', json={
        'title': 'Rejected', 'project_id': project['id'],
    }).status_code == 400
    assert client.patch(url, json={'name': 'No rename'}).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.get('/api/tasks').get_json()['tasks'] == [task]
    assert client.get('/api/tasks?project_id=unassigned').get_json()['tasks'] == []
    assert client.get(f"/api/tasks/{task['id']}").get_json()['task'] == task
    with app.app_context():
        row = get_database().execute('SELECT * FROM project WHERE id = ?', (project['id'],)).fetchone()
        assert row['is_deleted'] == 1
        assert row['deleted_at'].endswith('+00:00')
        assert row['deleted_at'] == row['updated_at']
        assert row['name'] == project['name']
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert restarted.get('/api/projects').get_json()['projects'] == [other]
    assert restarted.get('/api/tasks').get_json()['tasks'] == [task]


@pytest.mark.parametrize('method', ['put', 'patch', 'delete'])
def test_project_mutations_require_login(client, method):
    response = getattr(client, method)('/api/projects/1', json={'name': 'Changed'})
    assert response.status_code == 401


@pytest.mark.parametrize('project_id', [0, 999, 9223372036854775808])
def test_missing_project_mutations(authenticated_client, project_id):
    client = authenticated_client
    url = f'/api/projects/{project_id}'
    for method in ('put', 'patch'):
        response = getattr(client, method)(url, json={'name': 'Missing'})
        assert response.status_code == 404
        assert response.get_json() == {'error': 'Project not found'}
    assert client.delete(url).status_code == 404


def test_malformed_project_edit(authenticated_client):
    client = authenticated_client
    project = client.post('/api/projects', json={'name': 'Original'}).get_json()['project']
    response = client.patch(f"/api/projects/{project['id']}", data='{', content_type='application/json')
    assert response.status_code == 400
    assert client.get('/api/projects').get_json()['projects'] == [project]


def test_project_migration_preserves_existing_data(tmp_path):
    import sqlite3

    path = tmp_path / 'old-projects.db'
    with sqlite3.connect(path) as database:
        database.execute('CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)')
        database.execute('INSERT INTO project VALUES (?, ?, ?)', (7, 'Existing', '2026-10-20T00:00:00+00:00'))
    config = {'TESTING': True, 'DATABASE': str(path)}
    # Running initialization twice must be safe and preserve migrated values.
    for _ in range(2):
        client = create_app(config).test_client()
        project = client.get('/api/projects').get_json()['projects'][0]
        assert project == {
            'id': 7, 'name': 'Existing', 'created_at': '2026-10-20T00:00:00+00:00',
            'updated_at': '2026-10-20T00:00:00+00:00', 'is_deleted': False, 'deleted_at': None,
        }
