import sqlite3
from datetime import datetime, timedelta, timezone
import pytest
from app import create_app


def test_delete_restore_and_restart(client, app):
    original = client.post('/api/tasks', json={'title': 'Saved task', 'status': 'done'}).get_json()['task']
    url = f"/api/tasks/{original['id']}"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.get('/api/tasks').get_json()['tasks'] == []
    deleted = client.get('/api/tasks/deleted').get_json()['tasks'][0]
    assert deleted['is_deleted'] and deleted['deleted_at']
    assert client.delete(url).status_code == 404
    assert client.get('/api/tasks/deleted').get_json()['tasks'][0]['deleted_at'] == deleted['deleted_at']
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert restarted.get(url).status_code == 404
    response = restarted.post(url + '/restore')
    assert response.status_code == 200
    restored = response.get_json()['task']
    assert restored['title'] == original['title']
    assert restored['status'] == original['status']
    assert restored['created_at'] == original['created_at']
    assert restored['deleted_at'] is None and not restored['is_deleted']
    assert restarted.get('/api/tasks/deleted').get_json()['tasks'] == []
    assert restarted.get(url).status_code == 200


@pytest.mark.parametrize('hours,code', [(23, 200), (24, 410), (25, 410)])
def test_recovery_limit(client, app, hours, code):
    task_id = client.post('/api/tasks', json={'title': 'Test'}).get_json()['task']['id']
    url = f'/api/tasks/{task_id}'
    client.delete(url)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute('UPDATE task SET deleted_at = ? WHERE id = ?',
                   ((datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(), task_id))
    assert len(client.get('/api/tasks/deleted').get_json()['tasks']) == (1 if code == 200 else 0)
    assert client.post(url + '/restore').status_code == code
    if code == 410:
        with sqlite3.connect(app.config['DATABASE']) as db:
            assert db.execute('SELECT is_deleted FROM task WHERE id = ?', (task_id,)).fetchone()[0] == 1


def test_missing_and_active(client):
    assert client.delete('/api/tasks/999').status_code == 404
    assert client.post('/api/tasks/999/restore').status_code == 404
    task_id = client.post('/api/tasks', json={'title': 'Test'}).get_json()['task']['id']
    assert client.post(f'/api/tasks/{task_id}/restore').status_code == 404
