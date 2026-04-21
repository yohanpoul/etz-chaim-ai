"""Web — Interface locale de l'Arbre Etz Chaim.

Flask sur port 8080, dark mode.
"""

from .app import create_app

__all__ = ["create_app"]
