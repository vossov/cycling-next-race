"""Register van bronnen: welke koers wordt door welk platform bediend.

Cyclingstage is een redactionele selectie — 49 koersen in 2026, waarvan 11 bij
de vrouwen. Wat er niet in staat bestaat voor deze integratie niet: de Ronde
van Polen, Denemarken, Guangxi en alle vrouwenrondes van een week. Een tweede
algemene bron is er niet (zie "FirstCycling is uitgesloten" in CLAUDE.md), dus
de weg naar meer koersen loopt via de organisatoren, koers voor koers.

Dit bestand is het scharnier daarvoor. Het bevat **geen** parsers: een bron
levert drie functies en het register weet welke koers bij welke bron hoort.

Een bron toevoegen is dan:

1. `robots.txt` van de organisator nalezen. Staat daar `Disallow: /`, dan
   houdt het op — dat is bij FirstCycling gebeurd en dat gold.
2. Een echte pagina opslaan en er een parser tegenaan zetten, met de HTML in
   `tests/fixtures/`. Nooit op verzonnen HTML; dat heeft in dit project al
   twee keer een echte bug gemaskeerd.
3. `registreer(Bron(...))` aanroepen.
4. De koers in `EXTRA_KOERSEN` zetten als geen enkele kalender hem noemt, of
   `bron` op zijn kalenderregel zetten als hij er wel in staat maar de
   etappes elders vandaan moeten komen.

Wat een bron moet kunnen:

- `etappes(koers) -> list[dict]` — de etappelijst. Elke etappe draagt
  minstens `date`, `stage_url`, `idx`, `one_day`, `race_url`, `race_name`,
  `women` en `level`; `distance_km`, `stage_type`, `departure` en `arrival`
  mogen leeg blijven.
- `uitslag(etappe, result_n, gc_n) -> dict` — met in elk geval `ok`,
  `finished` en `results`. Wat een bron niet geeft blijft leeg; niets
  invullen wat er niet staat.
- `kalender(jaar) -> list[dict]` — alleen voor een bron die zelf koersen
  aandraagt. Een organisator die één koers bedient laat dit weg.

Een bron die faalt hoort leeg terug te geven, niet te gooien: één stukke
organisatorsite mag de rest van het dashboard niet meenemen.
"""
from __future__ import annotations

import logging
from typing import Callable

_LOGGER = logging.getLogger(__name__)

# De bron die een koers krijgt als er niets is opgegeven. Dit is wat de
# integratie al deed voordat dit register bestond, dus bestaande kalenders
# blijven werken zonder dat er iets aan ze verandert.
STANDAARD = "cyclingstage"


class Bron:
    """Eén platform dat koersgegevens levert.

    `kalender` mag None zijn: een organisator die alleen zijn eigen koers
    bedient hoeft geen kalender te kunnen.
    """

    def __init__(self, naam: str,
                 etappes: Callable[[dict], list],
                 uitslag: Callable[..., dict],
                 kalender: Callable[[int], list] | None = None):
        self.naam = naam
        self.etappes = etappes
        self.uitslag = uitslag
        self.kalender = kalender

    def __repr__(self) -> str:      # pragma: no cover - alleen voor het log
        return f"<Bron {self.naam}>"


BRONNEN: dict[str, Bron] = {}


def registreer(bron: Bron) -> None:
    """Een bron aanmelden. Dezelfde naam twee keer overschrijft de eerste."""
    BRONNEN[bron.naam] = bron


def bron_van(koers_of_etappe: dict) -> Bron | None:
    """De bron die bij deze koers of etappe hoort.

    Onbekend of niet aangemeld levert None op; de aanroeper logt dat en gaat
    verder met een lege lijst. Een koers uit een oudere versie draagt geen
    `bron` en valt dus vanzelf terug op de standaard.
    """
    naam = str(koers_of_etappe.get("bron") or STANDAARD)
    bron = BRONNEN.get(naam)
    if bron is None:
        _LOGGER.debug("Onbekende bron %r voor %s", naam,
                      koers_of_etappe.get("race_name")
                      or koers_of_etappe.get("name") or "?")
    return bron


# ── Koersen die geen enkele kalender noemt ────────────────────────────
#
# Vul aan naarmate er bronnen bij komen. Elke regel heeft `name`, `start`,
# `end`, `women`, `level`, `bron` en `url` nodig — dezelfde velden die
# `_fetch_calendar` aan een kalenderkoers geeft. `start` en `end` zijn
# `datetime.date`.
#
# Bewust leeg: een koers hier neerzetten zonder bron die hem kan bedienen
# levert een koers zonder etappes op, en die verdwijnt stil weer. Zet hem er
# pas bij als stap 1 tot en met 3 hierboven gedaan zijn.
EXTRA_KOERSEN: list[dict] = []


def extra_koersen(jaar: int, niveaus) -> list[dict]:
    """De handmatige koersen van dit jaar, gefilterd op de gekozen niveaus."""
    gekozen = set(niveaus or [])
    uit = []
    for k in EXTRA_KOERSEN:
        if k.get("start") is None or k["start"].year != jaar:
            continue
        if gekozen and str(k.get("level", "")) not in gekozen:
            continue
        uit.append(dict(k))
    return uit
