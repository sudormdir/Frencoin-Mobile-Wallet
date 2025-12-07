from aiohttp import TCPConnector


class ProxyConnector(TCPConnector):
    """
    Stub replacement for aiohttp_socks.ProxyConnector.

    We ignore all proxy-related kwargs and just behave like a normal
    TCPConnector. This is enough for Electrum to run without proxy support.
    """

    def __init__(self, *args, **kwargs):
        # Strip out proxy-related kwargs if Electrum passes them
        for key in ("proxy_type", "proxy_host", "proxy_port",
                    "proxy_username", "proxy_password", "rdns",
                    "proxy_url"):
            kwargs.pop(key, None)
        super().__init__(*args, **kwargs)


class ChainProxyConnector(ProxyConnector):
    """
    Stub replacement for aiohttp_socks.ChainProxyConnector.
    We just reuse ProxyConnector behavior.
    """
    pass
