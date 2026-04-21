"""Flask blueprints — découpage de web/app.py (audit cycle 4, N1).

Pattern : chaque blueprint est défini dans un module séparé, importé
puis enregistré par create_app(). Le before_request d'auth défini sur
l'app s'applique automatiquement aux routes des blueprints.
"""
