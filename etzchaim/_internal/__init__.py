"""Internal subpackage — not part of the public API.

Modules here are imported by neutral-named entry points in
``etzchaim.cli``, ``etzchaim.deploy``, and ``etzchaim.api``. Public consumers
should never import from ``etzchaim._internal`` directly; the leading
underscore is the standard Python signal that the surface is private and may
change without notice.
"""
from __future__ import annotations
