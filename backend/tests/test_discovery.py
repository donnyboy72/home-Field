"""Discovery tests use fake network objects and never open an application database."""
from types import SimpleNamespace

import pytest
import discovery


def test_lan_addresses_exclude_loopback_ipv6_and_public(monkeypatch):
    adapter = SimpleNamespace(ips=[SimpleNamespace(ip=address) for address in
        ['127.0.0.1', '192.168.1.4', '192.168.1.4', '10.0.0.5', '8.8.8.8', ('::1', 0, 0)]])
    monkeypatch.setattr(discovery.ifaddr, 'get_adapters', lambda: [adapter])
    assert discovery.lan_addresses() == ['10.0.0.5', '192.168.1.4']


def test_advertisement_has_api_port_and_closes_on_server_error(monkeypatch):
    events = []
    class Network:
        def __init__(self, **kwargs): pass
        def register_service(self, service, **kwargs): events.append(('register', service))
        def unregister_service(self, service): events.append(('unregister', service))
        def close(self): events.append(('close', None))
    monkeypatch.setattr(discovery, 'lan_addresses', lambda: ['192.168.1.4'])
    monkeypatch.setattr(discovery, 'Zeroconf', Network)
    with pytest.raises(RuntimeError, match='server stopped'):
        with discovery.advertise_host(50000):
            service = events[0][1]
            assert service.type == '_homefield._tcp.local.'
            assert service.port == 50000
            assert service.parsed_addresses() == ['192.168.1.4']
            assert service.properties[b'scheme'] == b'http'
            raise RuntimeError('server stopped')
    assert [event[0] for event in events] == ['register', 'unregister', 'close']


def test_discovery_failure_allows_manual_server_start(monkeypatch):
    monkeypatch.setattr(discovery, 'lan_addresses', lambda: ['192.168.1.4'])
    def unavailable(**kwargs):
        raise OSError('multicast blocked')
    monkeypatch.setattr(discovery, 'Zeroconf', unavailable)
    with discovery.advertise_host(50000):
        pass  # The server body still runs even when discovery cannot start.
