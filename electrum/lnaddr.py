# lnaddr.py - Lightning stub for Frencoin Android build

from enum import Enum


class LnDecodeException(Exception):
    """Lightning invoices are not supported in this Android build."""
    pass


class LnAddr:
    """Dummy LnAddr; exists so imports succeed, but cannot be used."""
    def __init__(self, *args, **kwargs):
        raise LnDecodeException("Lightning is not supported in this Android wallet build.")


def parse_lightning_invoice(*args, **kwargs):
    raise LnDecodeException("Lightning is not supported in this Android wallet build.")


def lnencode(*args, **kwargs):
    raise LnDecodeException("Lightning is not supported in this Android wallet build.")


def lnencode_clearnet_path(*args, **kwargs):
    raise LnDecodeException("Lightning is not supported in this Android wallet build.")


def lndecode(*args, **kwargs):
    """
    Stub for code that imports `lndecode` from electrum.lnaddr.
    Always raises because LN is not supported.
    """
    raise LnDecodeException("Lightning is not supported in this Android wallet build.")


__all__ = [
    "LnAddr",
    "LnDecodeException",
    "parse_lightning_invoice",
    "lnencode",
    "lnencode_clearnet_path",
    "lndecode",
]
