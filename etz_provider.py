#!/usr/bin/env python3
"""etz_provider.py — Gestion du profil LLM actif.

שַׁעַר הַכְּלִים — La Porte des Receptacles.
Chaque profil est un ensemble de Kelim (receptacles)
qui determinent comment la Lumiere (information) descend
a travers les 4 Mondes.

Usage:
    python etz_provider.py status       # Voir le profil actif
    python etz_provider.py profiles     # Lister tous les profils
    python etz_provider.py switch <nom> # Changer de profil
    python etz_provider.py test         # Tester chaque olam
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def cmd_status() -> None:
    """Afficher le profil actif et l'etat de chaque olam."""
    # Force reload
    import olamot
    olamot.reload_config()

    cfg = _load_config()
    profile_name = cfg.get("active_profile", "ollama_local")
    profiles = cfg.get("profiles", {})
    profile = profiles.get(profile_name, {})

    print(f"Profil actif : {profile_name}")
    print(f"  {profile.get('description', '(pas de description)')}")
    print()

    olamot_cfg = profile.get("olamot", {})
    models_ok = olamot.check_models()

    for olam_name in ["atziluth", "briah", "yetzirah", "assiah"]:
        olam = olamot_cfg.get(olam_name, {})
        prov = olam.get("provider", "?")
        model = olam.get("model", "?")
        timeout = olam.get("timeout", "?")
        think = olam.get("think", False)

        ok = models_ok.get(olam_name, False)
        status_icon = "OK" if ok else "MISSING"

        think_str = " think:true" if think else ""
        print(f"  {olam_name:<12} {prov}/{model}{think_str} (timeout: {timeout}s) [{status_icon}]")

    emb = profile.get("embedding", {})
    emb_ok = models_ok.get("embedding", False)
    print(f"  {'embedding':<12} {emb.get('provider', 'ollama')}/{emb.get('model', '?')} [{'OK' if emb_ok else 'MISSING'}]")


def cmd_profiles() -> None:
    """Lister tous les profils disponibles."""
    cfg = _load_config()
    active = cfg.get("active_profile", "ollama_local")
    profiles = cfg.get("profiles", {})

    print("Profils disponibles :")
    print()
    for name, profile in profiles.items():
        marker = " <-- ACTIF" if name == active else ""
        desc = profile.get("description", "")
        print(f"  {name}{marker}")
        print(f"    {desc}")

        olamot = profile.get("olamot", {})
        for olam_name in ["atziluth", "briah", "yetzirah", "assiah"]:
            olam = olamot.get(olam_name, {})
            prov = olam.get("provider", "?")
            model = olam.get("model", "?")
            print(f"      {olam_name:<12} {prov}/{model}")
        print()


def cmd_switch(profile_name: str) -> None:
    """Changer le profil actif dans config.yaml."""
    cfg = _load_config()
    profiles = cfg.get("profiles", {})

    if profile_name not in profiles:
        print(f"Erreur : profil '{profile_name}' inconnu.")
        print(f"Disponibles : {', '.join(profiles.keys())}")
        sys.exit(1)

    cfg["active_profile"] = profile_name

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    desc = profiles[profile_name].get("description", "")
    print(f"Profil switche vers : {profile_name}")
    print(f"  {desc}")

    # Force reload
    try:
        import olamot
        olamot.reload_config()
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)


def cmd_test() -> None:
    """Tester chaque olam avec un prompt simple."""
    import olamot
    olamot.reload_config()

    profile_name = olamot.get_active_profile_name()
    print(f"Test du profil : {profile_name}")
    print()

    test_prompt = "Reponds en une seule phrase : quel est ton nom de modele ?"
    test_kavvanah = {
        "intention": "Test de connectivite provider",
        "critere_succes": "Reponse non-vide",
        "anti_pattern": "pas de message d'erreur",
    }

    for olam_name in ["assiah", "yetzirah", "briah"]:
        provider = olamot.get_provider(olam_name)
        model = olamot.get_model(olam_name)
        timeout = olamot.get_timeout(olam_name)

        print(f"  {olam_name:<12} ({provider}/{model}, timeout={timeout}s)")
        print(f"    ", end="", flush=True)

        try:
            t0 = time.monotonic()
            response, latency = olamot.ollama_generate(
                olam_name, test_prompt, timeout=timeout,
                kavvanah=test_kavvanah,
            )
            elapsed = (time.monotonic() - t0) * 1000

            # Tronquer la reponse pour affichage
            preview = response[:120].replace("\n", " ")
            if len(response) > 120:
                preview += "..."

            is_error = response.startswith("[Erreur")
            status = "FAIL" if is_error else "OK"
            print(f"[{status}] {elapsed:.0f}ms")
            print(f"    {preview}")
        except Exception as e:
            print(f"[FAIL] {e}")
        print()

    # Atziluth — skip si optionnel et indisponible
    provider = olamot.get_provider("atziluth")
    model = olamot.get_model("atziluth")
    print(f"  {'atziluth':<12} ({provider}/{model})")
    print(f"    ", end="", flush=True)
    try:
        t0 = time.monotonic()
        response, latency = olamot.ollama_generate(
            "atziluth", test_prompt, timeout=60,
            kavvanah=test_kavvanah,
        )
        elapsed = (time.monotonic() - t0) * 1000
        preview = response[:120].replace("\n", " ")
        is_error = response.startswith("[Erreur")
        status = "FAIL" if is_error else "OK"
        print(f"[{status}] {elapsed:.0f}ms")
        print(f"    {preview}")
    except Exception as e:
        print(f"[SKIP] {e}")
    print()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "profiles":
        cmd_profiles()
    elif cmd == "switch":
        if len(sys.argv) < 3:
            print("Usage: python etz_provider.py switch <profile_name>")
            sys.exit(1)
        cmd_switch(sys.argv[2])
    elif cmd == "test":
        cmd_test()
    else:
        print(f"Commande inconnue: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
