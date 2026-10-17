"""Additional recovery edge cases; existing endpoint tests remain unchanged."""
from datetime import datetime, timedelta, timezone

import pytest

from tasks import is_recoverable


@pytest.mark.parametrize('age,expected', [
    (timedelta(0), True),
    (timedelta(hours=24, microseconds=-1), True),
    (timedelta(hours=24), False),
    (timedelta(hours=24, microseconds=1), False),
    (timedelta(seconds=-1), False),
])
def test_exact_recovery_boundary(age, expected):
    now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    row = {'deleted_at': (now - age).isoformat()}
    assert is_recoverable(row, now) is expected


@pytest.mark.parametrize('timestamp', [None, '', 'invalid'])
def test_invalid_deletion_timestamp(timestamp):
    assert not is_recoverable({'deleted_at': timestamp}, datetime.now(timezone.utc))


def test_recovery_accepts_equivalent_timezone():
    now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    assert is_recoverable({'deleted_at': '2026-10-17T07:00:00-04:00'}, now)


def test_restore_twice_and_delete_again(authenticated_client):
    client = authenticated_client
    user = client.get('/api/auth/me').get_json()['user']
    original = client.post('/api/tasks', json={
        'title': 'Restore all fields', 'description': 'Keep description',
        'deadline': '2026-10-20', 'status': 'in_progress',
        'project_id': 1, 'created_by': user['id'] + 1, 'assigned_to': user['id'],
    }).get_json()['task']
    url = f"/api/tasks/{original['id']}"
    client.delete(url)
    restored = client.post(url + '/restore').get_json()['task']
    for field in ('id', 'title', 'description', 'deadline', 'status',
                  'project_id', 'created_by', 'assigned_to', 'created_at'):
        assert restored[field] == original[field]
    assert restored['updated_at'] >= original['updated_at']
    assert client.post(url + '/restore').status_code == 404
    assert client.delete(url).status_code == 204
    assert client.post(url + '/restore').status_code == 200
    assert client.get('/api/tasks').get_json()['tasks'][0]['id'] == original['id']
