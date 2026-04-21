"""Adversarial agents — specialized failure injectors per Sephirah.

7 contre-Middot (Chesed→Malkuth) + 1 generic baseline.
Structure 3+7 du Zohar II:242b (les contre-Mochin sont dans sitra_achra/).
"""

from malakhim.adversarial.base_adversary import AdversaryBase, Attack, AttackResult
from malakhim.adversarial.generic_adversary import GenericAdversary
from malakhim.adversarial.samael_adversary import SamaelAdversary
from malakhim.adversarial.gamchicoth_adversary import GamchicothAdversary
from malakhim.adversarial.sathariel_adversary import SatharielAdversary
from malakhim.adversarial.gamaliel_adversary import GamalielAdversary
from malakhim.adversarial.aarab_zaraq_adversary import AarabZaraqAdversary
from malakhim.adversarial.thagirion_adversary import ThagirionAdversary
from malakhim.adversarial.golachab_adversary import GolachabAdversary
from malakhim.adversarial.hatehom_adversary import HaTehomAdversary
from malakhim.adversarial.ghagiel_adversary import GhagielAdversary

__all__ = [
    "AdversaryBase", "Attack", "AttackResult",
    "GenericAdversary",
    # Contre-Middot (7) — un par Sephirah des Midot
    "GamalielAdversary",     # vs Yesod (epistememory)
    "SamaelAdversary",       # vs Hod (selfmap)
    "AarabZaraqAdversary",   # vs Netzach (intentkeeper)
    "ThagirionAdversary",    # vs Tiferet (dissensuengine)
    "GolachabAdversary",     # vs Gevurah (autojudge)
    "GamchicothAdversary",   # vs Chesed (explorationengine)
    "SatharielAdversary",    # vs Binah (causalengine) — reclassé contre-Mochin
    # Contre-Mochin supérieurs
    "HaTehomAdversary",      # vs Da'at (selfmodel)
    "GhagielAdversary",      # vs Chokmah (insightforge)
]
