# Minimal stub of aiohttp_socks for Android build.
# We don't actually support SOCKS proxies in this build.
# This just keeps Electrum imports happy.

from .connector import ProxyConnector, ChainProxyConnector  # noqa: F401
