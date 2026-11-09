"""Advertise the manually started Flask host; never started by create_app/tests."""

from contextlib import contextmanager
import ipaddress
import logging
import socket

import ifaddr
from zeroconf import IPVersion, ServiceInfo, Zeroconf

SERVICE_TYPE = "_homefield._tcp.local."


def lan_addresses():
    """Include each private IPv4 interface, rather than guessing the active Wi-Fi."""
    addresses = set()
    for adapter in ifaddr.get_adapters():
        for interface in adapter.ips:
            if not isinstance(interface.ip, str):  # IPv6 uses a tuple.
                continue
            address = ipaddress.ip_address(interface.ip)
            if address.version == 4 and address.is_private and not address.is_loopback:
                addresses.add(str(address))
    return sorted(addresses)


@contextmanager
def advertise_host(port):
    """Discovery failure must not prevent manual connections to Flask."""
    discovery = None
    service = None
    registered = False
    try:
        addresses = lan_addresses()
        if addresses:
            hostname = socket.gethostname().split('.')[0][:40] or 'HomeField'
            service = ServiceInfo(
                SERVICE_TYPE,
                f"{hostname} HomeField.{SERVICE_TYPE}",
                parsed_addresses=addresses,
                port=port,
                properties={"app": "homefield", "version": "1", "scheme": "http"},
                server=f"{hostname}.local.",
            )
            discovery = Zeroconf(ip_version=IPVersion.V4Only)
            discovery.register_service(service, allow_name_change=True)
            registered = True
        else:
            logging.warning("No LAN address found; use manual connection entry.")
    except Exception:
        logging.exception("Host discovery unavailable; manual connections still work.")
    try:
        yield
    finally:
        if discovery is not None:
            try:
                if registered:
                    discovery.unregister_service(service)
            finally:
                discovery.close()
