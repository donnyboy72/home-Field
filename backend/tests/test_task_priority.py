"""Priority survives API edits, recovery, and upgrades of existing databases."""
import sqlite3

import pytest

from app import create_app


@pytest.mark.parametrize('priority', ['high', 'med', 'low'])
def test_priority_round_trip(authenticated_client, app, priority):
    client = authenticated_client
    response = client.post('/api/tasks', json={'title': 'Priority task', 'priority': priority})
    assert response.status_code == 201
    task = response.get_json()['task']
    url = f"/api/tasks/{task['id']}"
    assert task['priority'] == priority
    assert client.get('/api/tasks').get_json()['tasks'][0]['priority'] == priority
    assert client.patch(url, json={'status': 'done'}).get_json()['task']['priority'] == priority
    changed = 'low' if priority == 'high' else 'high'
    assert client.patch(url, json={'priority': changed}).get_json()['task']['priority'] == changed
    assert client.delete(url).status_code == 204
    assert client.get('/api/tasks/deleted').get_json()['tasks'][0]['priority'] == changed
    assert client.post(url + '/restore').get_json()['task']['priority'] == changed
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    restarted.environ_base.update(client.environ_base)
    assert restarted.get(url).get_json()['task']['priority'] == changed


@pytest.mark.parametrize('priority', [None, '', 'medium', 'urgent', 'HIGH', True, 1, [], {}])
def test_invalid_priority_is_rejected(authenticated_client, priority):
    client = authenticated_client
    task = client.post('/api/tasks', json={'title': 'Default priority'}).get_json()['task']
    assert task['priority'] == 'med'
    assert client.post('/api/tasks', json={'title': 'Invalid', 'priority': priority}).status_code == 400
    url = f"/api/tasks/{task['id']}"
    assert client.patch(url, json={'priority': priority}).status_code == 400
    assert client.get(url).get_json()['task'] == task


def test_priority_migration_preserves_existing_tasks(tmp_path):
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE task (id INTEGER PRIMARY KEY, title TEXT NOT NULL, is_deleted INTEGER NOT NULL DEFAULT 0)')
        db.executemany('INSERT INTO task (id, title, is_deleted) VALUES (?, ?, ?)',
                       [(1, 'Active', 0), (2, 'Deleted', 1)])
    for _ in range(2):
        create_app({'TESTING': True, 'DATABASE': str(path)})
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT id, title, is_deleted, priority FROM task ORDER BY id').fetchall() == [
            (1, 'Active', 0, 'med'), (2, 'Deleted', 1, 'med')]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE task SET priority = 'urgent' WHERE id = 1")
