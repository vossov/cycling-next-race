"""De koersblokken voor de pop-up (`races`).

Mannen en vrouwen koersen vaak op dezelfde dag. De tegel toont er één; de
andere zijn in de pop-up aan te klikken. Deze tests draaien de coordinator
met een gestubde `_fetch_stage`, dus zonder netwerk.
"""
import asyncio
import re
from datetime import date, timedelta

import pytest

VANDAAG = date(2026, 7, 18)


def _stages(race_url, naam, dagen, women=False):
    """Etappelijst zoals `_event_stages` hem oplevert."""
    return [{
        "date": d, "stage_url": f"{race_url}/stage-{i}", "profile_icon": "",
        "name": "", "idx": i, "one_day": False, "race_url": race_url,
        "race_name": naam, "women": women,
    } for i, d in enumerate(dagen, 1)]


def _uitslag(finished=True):
    return {
        "ok": True, "finished": finished,
        "results": [{"rank": 1, "rider": "Vollering Demi", "team": "FDJ",
                     "time": "3:02:11"}],
        "gc": [{"rank": 1, "rider": "Vollering Demi", "time": "9:14:02"}],
        "points_top": [{"rank": 1, "rider": "Wiebes Lorena", "points": 120}],
        "kom_top": [], "youth_top": [],
    }


@pytest.fixture
def coordinator(wt, monkeypatch):
    """Een coordinator die niets ophaalt: `_job` roept de functie direct aan."""
    co = wt.CyclingCoordinator(hass=None)

    async def _job(fn, *args):
        return fn(*args)

    co._job = _job
    # een koersblok haalt ook de startlijst, de ranglijst, de tv-gids en de
    # vorige stand op; die gaan hier niet het net op
    monkeypatch.setattr(wt, "_fetch_startlist", lambda *a: [])
    monkeypatch.setattr(wt, "_fetch_ranking", lambda *a: {})
    monkeypatch.setattr(wt, "_fetch_tv_html", lambda *a: "")
    monkeypatch.setattr(wt, "_fetch_rank_maps", lambda *a: {})
    return co


def _draai(co, primair, andere, today=VANDAAG):
    return asyncio.run(co._races_block(primair, andere, today))


def _kandidaat(ev, stages):
    """Zoals `kandidaten` in `_async_update_data`: (datum, gpx, dames, i, ev, st)."""
    return (VANDAAG, 0, 1 if ev.get("women") else 0, 1, ev, stages)


PRIMAIR = {"key": "tour-de-france", "label": "Tour de France",
           "race_name": "Tour de France", "women": False}

FEMMES = {"name": "Tour de France Femmes", "url": "race/tour-de-france-femmes/2026",
          "start": date(2026, 7, 16), "end": date(2026, 7, 24), "women": True}


def test_alleen_de_getoonde_koers(coordinator):
    """Zonder andere koersen blijft er één blok over en is `other_*` leeg."""
    uit = _draai(coordinator, PRIMAIR, [])
    assert [r["key"] for r in uit["races"]] == ["tour-de-france"]
    assert uit["races"][0]["primary"] is True
    assert uit["other_label"] == "" and uit["other_result"] == []


def test_andere_koers_krijgt_eigen_uitslag_en_stand(wt, coordinator, monkeypatch):
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 16), date(2026, 7, 17), VANDAAG], women=True)
    # de etappe van vandaag is nog niet binnen; die van gisteren wel
    monkeypatch.setattr(wt, "_fetch_stage", lambda url, *a: _uitslag(
        finished=not url.endswith("stage-3")))

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    blok = uit["races"][1]

    assert blok["key"] == "tour-de-france-femmes"
    assert blok["label"] == "Tour de France Femmes"   # naam noemt de dames al
    assert blok["last_stage_label"] == "Etappe 2 · Tour de France Femmes"
    assert blok["last_result"][0]["rider"] == "Vollering Demi"
    assert blok["gc_top"] and blok["points_top"]
    # de etappe van vandaag is nog bezig, dus die staat bovenaan het blok
    assert blok["eyebrow"] == "Etappe 3 · Tour de France Femm…"
    assert blok["show_state"] == "Vandaag"


def test_uitslag_van_vandaag_schuift_door_naar_de_volgende_etappe(
        wt, coordinator, monkeypatch):
    """Dezelfde rollover als op de tegel: uitslag binnen = volgende etappe tonen."""
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 17), VANDAAG, date(2026, 7, 19)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert blok["last_stage_label"] == "Etappe 2 · Tour de France Femmes"
    assert blok["eyebrow"] == "Etappe 3 · Tour de France Femm…"
    assert blok["show_state"] == "Morgen"


def test_dames_erbij_als_de_naam_het_niet_zegt(wt, coordinator, monkeypatch):
    ev = dict(FEMMES, name="Ronde van Vlaanderen", url="race/rvv-vrouwen/2026")
    stages = _stages(ev["url"], ev["name"], [VANDAAG], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(ev, stages)])["races"][1]

    assert blok["label"] == "Ronde van Vlaanderen · Dames"
    assert blok["eyebrow"].endswith("· Dames")


def test_zonder_uitslag_blijft_het_blok_leeg_maar_bestaat_het(
        wt, coordinator, monkeypatch):
    """Een koers die nog moet beginnen krijgt geen verzonnen uitslag."""
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 20)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    blok = uit["races"][1]

    assert blok["last_result"] == [] and blok["gc_top"] == []
    assert blok["eyebrow"] == "Etappe 1 · Tour de France Femm…"
    assert uit["other_label"] == ""


def test_koers_zonder_uitslag_toont_de_startlijst(wt, coordinator, monkeypatch):
    """Nog niets gereden: dan is wie er meedoet het enige dat er te melden valt."""
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 20)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))
    monkeypatch.setattr(wt, "_fetch_startlist", lambda *a: [
        {"rider": "Vollering Demi", "rider_url": "rider/demi-vollering",
         "team": "FDJ - SUEZ", "team_url": "team/fdj-suez-2026"},
        {"rider": "Wiebes Lorena", "rider_url": "rider/lorena-wiebes",
         "team": "Team SD Worx", "team_url": "team/sd-worx-2026"},
    ])
    monkeypatch.setattr(wt, "_fetch_ranking", lambda *a: {
        "rider/lorena-wiebes": (1, 3120), "rider/demi-vollering": (3, 2480)})
    # de ploegcodes komen van een eigen pagina; die gaat hier niet het net op
    monkeypatch.setattr(wt, "_fetch_team_abbr", lambda *a: "")

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert [r["rider"] for r in blok["startlist_top"]] == [
        "Wiebes Lorena", "Vollering Demi"]
    assert blok["startlist_riders"] == 2 and blok["startlist_teams"] == 2


def test_koers_met_uitslag_laat_de_startlijst_weg(wt, coordinator, monkeypatch):
    """Met een uitslag zegt de startlijst niets meer en kost hij alleen ruimte."""
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 17), VANDAAG], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    monkeypatch.setattr(wt, "_fetch_startlist", lambda *a: [
        {"rider": "Wiebes Lorena", "rider_url": "rider/lorena-wiebes",
         "team": "Team SD Worx", "team_url": "team/sd-worx-2026"}])
    monkeypatch.setattr(wt, "_fetch_ranking", lambda *a: {
        "rider/lorena-wiebes": (1, 3120)})

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert blok["last_result"] and blok["startlist_top"] == []


def test_startlijst_zonder_ranglijst_blijft_leeg(wt, coordinator, monkeypatch):
    """Zonder bron voor de volgorde geen lijstje — maar wel de telling."""
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 20)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))
    monkeypatch.setattr(wt, "_fetch_startlist", lambda *a: [
        {"rider": "Wiebes Lorena", "rider_url": "rider/lorena-wiebes",
         "team": "Team SD Worx", "team_url": "team/sd-worx-2026"}])
    monkeypatch.setattr(wt, "_fetch_ranking", lambda *a: {})

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert blok["startlist_top"] == []
    assert blok["startlist_riders"] == 1 and blok["startlist_teams"] == 1


def test_oude_attributen_herhalen_de_eerste_koers_met_uitslag(
        wt, coordinator, monkeypatch):
    """`other_*` blijft bestaan voor kaarten van vóór `races`."""
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 17)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert uit["other_label"] == uit["races"][1]["last_stage_label"]
    assert uit["other_result"] == uit["races"][1]["last_result"]


def test_niet_meer_koersen_dan_de_cap(wt, coordinator, monkeypatch):
    """Elke koers erbij kost verzoeken bij PCS en ruimte in de attributen."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    andere = []
    for n in range(wt.MAX_ANDERE_KOERSEN + 2):
        ev = dict(FEMMES, name=f"Koers {n}", url=f"race/koers-{n}/2026")
        andere.append(_kandidaat(ev, _stages(ev["url"], ev["name"], [VANDAAG])))

    uit = _draai(coordinator, PRIMAIR, andere)

    assert len(uit["races"]) == wt.MAX_ANDERE_KOERSEN + 1


def test_afgeronde_etappe_wordt_maar_een_keer_opgehaald(
        wt, coordinator, monkeypatch):
    """Anders zou elke ronde dezelfde uitslag opnieuw opgevraagd worden."""
    opgehaald = []

    def _fetch(url, *a):
        opgehaald.append(url)
        return _uitslag()

    monkeypatch.setattr(wt, "_fetch_stage", _fetch)
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 17)], women=True)

    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert len(opgehaald) == 1


def test_lopende_etappe_wordt_niet_bewaard(wt, coordinator, monkeypatch):
    """Een uitslag die nog binnenkomt moet elke ronde opnieuw opgehaald."""
    opgehaald = []

    def _fetch(url, *a):
        opgehaald.append(url)
        return _uitslag(finished=False)

    monkeypatch.setattr(wt, "_fetch_stage", _fetch)
    stages = _stages(FEMMES["url"], FEMMES["name"], [VANDAAG], women=True)

    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert len(opgehaald) == 2


def test_koers_die_omvalt_haalt_de_rest_niet_onderuit(wt, coordinator, monkeypatch):
    """Degraderen: een mislukte koers verdwijnt, de andere blijven staan."""
    def _fetch(url, *a):
        if "stuk" in url:
            raise RuntimeError("PCS geeft onzin terug")
        return _uitslag()

    monkeypatch.setattr(wt, "_fetch_stage", _fetch)
    stuk = dict(FEMMES, name="Kapotte Koers", url="race/stuk/2026")
    andere = [
        _kandidaat(stuk, _stages(stuk["url"], stuk["name"], [date(2026, 7, 17)])),
        _kandidaat(FEMMES, _stages(FEMMES["url"], FEMMES["name"],
                                   [date(2026, 7, 17)], women=True)),
    ]

    uit = _draai(coordinator, PRIMAIR, andere)

    assert [r["key"] for r in uit["races"]] == [
        "tour-de-france", "tour-de-france-femmes"]


# ── evenveel te zien als bij de tegelkoers ──────────────────────────

# De koersen in de pop-up horen hetzelfde beeld te geven als de koers op
# de tegel: waar hij te zien is, de klassementen mét dagwinst, en op het
# profiel de starttijd en de tussensprint.

ZENDER = [{"name": "NPO 1", "time": "14:15", "logo": ""}]


def test_koersblok_krijgt_zijn_eigen_tv_zenders(wt, coordinator, monkeypatch):
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))
    monkeypatch.setattr(wt, "_fetch_tv_html", lambda *a: "<html>")
    monkeypatch.setattr(wt, "_channels_from", lambda *a: list(ZENDER))
    stages = _stages(FEMMES["url"], FEMMES["name"], [VANDAAG], women=True)

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert blok["channels_detail"] == ZENDER
    assert blok["channels"] == ["NPO 1 14:15"]


def test_tv_gids_wordt_maar_een_keer_opgehaald(wt, coordinator, monkeypatch):
    """Op die pagina staan álle koersen; één verzoek volstaat."""
    opgehaald = []
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))
    monkeypatch.setattr(wt, "_fetch_tv_html",
                        lambda *a: opgehaald.append(1) or "<html>")
    monkeypatch.setattr(wt, "_channels_from", lambda *a: list(ZENDER))

    andere = []
    for n in range(3):
        ev = dict(FEMMES, name=f"Koers {n}", url=f"race/koers-{n}/2026")
        andere.append(_kandidaat(ev, _stages(ev["url"], ev["name"], [VANDAAG])))
    coordinator._options[wt.CONF_MAX_OTHER] = 3

    uit = _draai(coordinator, PRIMAIR, andere)

    assert len(uit["races"]) == 4
    assert len(opgehaald) == 1, f"{len(opgehaald)} verzoeken voor de tv-gids"


def test_geen_zenders_voor_een_koers_die_nog_ver_weg_is(wt, coordinator,
                                                        monkeypatch):
    """De tv-gids toont ~6 dagen vooruit; verder vragen heeft geen zin."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))
    monkeypatch.setattr(wt, "_fetch_tv_html", lambda *a: "<html>")
    monkeypatch.setattr(wt, "_channels_from", lambda *a: list(ZENDER))
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [VANDAAG + timedelta(days=20)], women=True)

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert blok["channels_detail"] == []


def test_mislukte_tv_gids_kost_niet_het_hele_koersblok(wt, coordinator,
                                                       monkeypatch):
    def _stuk(*a):
        raise RuntimeError("wielerflits ligt eruit")

    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))
    monkeypatch.setattr(wt, "_fetch_tv_html", _stuk)
    stages = _stages(FEMMES["url"], FEMMES["name"], [VANDAAG], women=True)

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert len(uit["races"]) == 2, "het koersblok is verdwenen"
    assert uit["races"][1]["channels_detail"] == []


def test_dagwinst_ook_in_de_andere_koersen(wt, coordinator, monkeypatch):
    """Dezelfde berekening als op de tegel: koppelen op positie, niet op naam."""
    uitslag = dict(_uitslag(), gc=[
        {"rank": 1, "rider": "Vollering Demi", "time": "9:14:02", "prev": 1},
        {"rank": 2, "rider": "Kopecky Lotte", "time": "9:14:36", "prev": 2},
    ], points_top=[
        {"rank": 1, "rider": "Wiebes Lorena", "points": 120, "prev": 1},
    ])
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: uitslag)
    monkeypatch.setattr(wt, "_fetch_rank_maps", lambda *a: {
        "gc": {1: "6:10:00", 2: "6:10:20"},
        "points": {1: 95}, "kom": {}, "youth": {},
    })
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 16), date(2026, 7, 17)], women=True)

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    # nummer 2 verloor 14 seconden op de leider: (34) - (20)
    assert blok["gc_top"][1]["gain_s"] == 14
    assert blok["points_top"][0]["gain"] == 25


def test_zonder_vorige_etappe_geen_dagwinst(wt, coordinator, monkeypatch):
    """Bij de eerste etappe valt er niets te vergelijken."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    gevraagd = []
    monkeypatch.setattr(wt, "_fetch_rank_maps",
                        lambda *a: gevraagd.append(a) or {})
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 17)],
                     women=True)

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert gevraagd == []
    assert "gain_s" not in blok["gc_top"][0]


def test_tussensprint_alleen_bij_de_eerste_etappe_van_een_popupkoers(
        wt, coordinator):
    """Die etappe wordt als profiel getekend; de rest is een profieltje."""
    gevraagd = []

    async def _entry(s, today, met_sprints=False):
        gevraagd.append((s["stage_url"], met_sprints))
        return {"race_key": wt._race_slug(s["race_url"])}

    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [VANDAAG, date(2026, 7, 19), date(2026, 7, 20)], women=True)

    async def _stages_for(ev, today):
        return stages

    coordinator._upcoming_entry = _entry
    coordinator._stages_for = _stages_for
    coordinator._calendar = [FEMMES]
    shown = {"stage_url": "race/tour-de-france/2026/stage-14",
             "race_url": "race/tour-de-france/2026", "date": VANDAAG}

    asyncio.run(coordinator._build_upcoming(
        99, shown, [], VANDAAG, {"tour-de-france-femmes"}))

    assert [m for _u, m in gevraagd] == [True, False, False]


def test_geen_tussensprint_voor_de_etappes_van_de_tegelkoers(wt, coordinator):
    """Die staat al in de gewone attributen; nog eens ophalen is verspilling."""
    gevraagd = []

    async def _entry(s, today, met_sprints=False):
        gevraagd.append(met_sprints)
        return {"race_key": wt._race_slug(s["race_url"])}

    coordinator._upcoming_entry = _entry
    coordinator._calendar = []
    eigen = _stages("race/tour-de-france/2026", "Tour de France",
                    [date(2026, 7, 19), date(2026, 7, 20)])
    shown = {"stage_url": "race/tour-de-france/2026/stage-14",
             "race_url": "race/tour-de-france/2026", "date": VANDAAG}

    asyncio.run(coordinator._build_upcoming(
        99, shown, eigen, VANDAAG, {"tour-de-france"}))

    assert gevraagd == [False, False]


def test_komende_etappe_draagt_starttijd_en_verwachte_finish(wt, coordinator):
    """Zonder die twee blijft de badge van een pop-upkoers zonder tijden."""
    meta = {"ok": True, "departure": "Pau", "arrival": "Luchon",
            "distance": 170.0, "vertical": 3000, "profile_score": 400,
            "stage_type": "", "startlist_quality": None, "start_time": "12:50"}

    async def _job(fn, *args):
        if fn is wt._fetch_stage_meta:
            return dict(meta)
        if fn is wt._fetch_gpx:
            return [], []
        if fn is wt._fetch_stage_climbs:
            return []
        return fn(*args)

    coordinator._job = _job
    s = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 19)],
                women=True)[0]

    e = asyncio.run(coordinator._upcoming_entry(s, VANDAAG))

    assert e["start_time"] == "12:50"
    assert re.match(r"^\d{2}:\d{2}$", e["finish_est"]), e["finish_est"]


# ── officiële ploegcode ─────────────────────────────────────────────

# De code komt van de ploegpagina bij procyclingstats. Er wordt niets uit
# de naam afgeleid: een zelfgemaakte afkorting lijkt op een UCI-ploegcode
# zonder het te zijn.

def _stub_pcs(monkeypatch, code):
    """Vervangt het procyclingstats-pakket door een Team met deze code."""
    import sys
    import types

    class _Team:
        def __init__(self, url):
            self.url = url

        def abbreviation(self):
            if isinstance(code, Exception):
                raise code
            return code

    mod = types.ModuleType("procyclingstats")
    mod.Team = _Team
    monkeypatch.setitem(sys.modules, "procyclingstats", mod)


def test_ploegcode_komt_van_de_ploegpagina(wt, monkeypatch):
    _stub_pcs(monkeypatch, " uad ")
    assert wt._fetch_team_abbr("team/uae-team-emirates-2026") == "UAD"


@pytest.mark.parametrize("waarde", [
    "UAE Team Emirates",       # de volledige naam, geen code
    "",                        # niets ingevuld
    None,
    "TEAMCODE",                # te lang om een ploegcode te zijn
    RuntimeError("pagina weg"),
])
def test_onbruikbare_ploegcode_wordt_niet_getoond(wt, monkeypatch, waarde):
    """Liever de volledige naam dan iets dat op een code lijkt."""
    _stub_pcs(monkeypatch, waarde)
    assert wt._fetch_team_abbr("team/x-2026") == ""


@pytest.fixture
def zonder_pauze(wt, monkeypatch):
    async def _slaap(_seconden):
        return None

    monkeypatch.setattr(wt.asyncio, "sleep", _slaap)


def _data(ploegen, per_lijst=1):
    rijen = [{"rank": i + 1, "rider": f"Renner {i}", "team": p}
             for i, p in enumerate(ploegen)]
    return {"results": rijen,
            "gc": [dict(r) for r in rijen[:per_lijst]],
            "team_urls": {p: f"team/{p.lower()}-2026" for p in ploegen}}


def test_ploegcode_komt_op_elke_rij(wt, coordinator, monkeypatch, zonder_pauze):
    opgehaald = []
    monkeypatch.setattr(wt, "_fetch_team_abbr",
                        lambda url: opgehaald.append(url) or url[5:8].upper())
    data = _data(["Alpha", "Beta"])

    asyncio.run(coordinator._ploegcodes(data))

    assert [r["team_code"] for r in data["results"]] == ["ALP", "BET"]
    assert data["gc"][0]["team_code"] == "ALP"
    # één verzoek per ploeg, niet per rij
    assert len(opgehaald) == 2


def test_ploegcode_wordt_maar_een_keer_opgehaald(wt, coordinator, monkeypatch,
                                                 zonder_pauze):
    opgehaald = []
    monkeypatch.setattr(wt, "_fetch_team_abbr",
                        lambda url: opgehaald.append(url) or "ABC")

    asyncio.run(coordinator._ploegcodes(_data(["Alpha"])))
    asyncio.run(coordinator._ploegcodes(_data(["Alpha"])))

    assert len(opgehaald) == 1


def test_mislukte_ploegcode_wordt_niet_elke_ronde_herhaald(
        wt, coordinator, monkeypatch, zonder_pauze):
    """Wel opnieuw bij een nieuwe kalenderdag; die leegt de cache."""
    opgehaald = []
    monkeypatch.setattr(wt, "_fetch_team_abbr",
                        lambda url: opgehaald.append(url) or "")
    data = _data(["Alpha"])

    asyncio.run(coordinator._ploegcodes(data))
    asyncio.run(coordinator._ploegcodes(data))

    assert len(opgehaald) == 1
    assert "team_code" not in data["results"][0], "lege code hoort niet op de rij"


def test_ploeg_zonder_adres_houdt_zijn_naam(wt, coordinator, monkeypatch,
                                            zonder_pauze):
    monkeypatch.setattr(wt, "_fetch_team_abbr", lambda url: "ABC")
    data = _data(["Alpha"])
    data["team_urls"] = {}

    asyncio.run(coordinator._ploegcodes(data))

    assert "team_code" not in data["results"][0]
    assert data["results"][0]["team"] == "Alpha"


def test_niet_alle_ploegcodes_in_een_keer(wt, coordinator, monkeypatch,
                                          zonder_pauze):
    """Een koers telt zo'n twintig ploegen; die niet in één ronde ophalen."""
    opgehaald = []
    monkeypatch.setattr(wt, "_fetch_team_abbr",
                        lambda url: opgehaald.append(url) or "ABC")
    ploegen = [f"Ploeg{n:02d}" for n in range(wt.MAX_PLOEGCODES_PER_RONDE + 3)]
    data = _data(ploegen)

    asyncio.run(coordinator._ploegcodes(data))
    assert len(opgehaald) == wt.MAX_PLOEGCODES_PER_RONDE
    zonder = [r for r in data["results"] if "team_code" not in r]
    assert len(zonder) == 3, "de rest hoort zijn volledige naam te houden"

    # de volgende ronde komt de rest erbij
    asyncio.run(coordinator._ploegcodes(data))
    assert len(opgehaald) == len(ploegen)
    assert all("team_code" in r for r in data["results"])


# ── niveau in de attributen ─────────────────────────────────────────
#
# De kaart laat zich per dashboardkaart op niveaus instellen en filtert
# daarvoor op `level`. Ontbreekt dat veld, dan valt er niets te filteren en
# staat elke koers op elke kaart.

def test_koersblok_draagt_zijn_niveau_en_dagen(wt, coordinator, monkeypatch):
    """Genoeg voor een kaart om deze koers zelf naar de tegel te halen."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    stages = _stages("race/tour-de-france-femmes/2026", "Tour de France Femmes",
                     [VANDAAG - timedelta(days=1), VANDAAG + timedelta(days=2)],
                     women=True)
    ev = dict(FEMMES, level="24")

    blok = asyncio.run(coordinator._race_entry(ev, stages, VANDAAG))
    assert blok["level"] == "24"
    assert blok["days_until"] == 2


def test_koersblok_zonder_komende_etappe_heeft_geen_dagen(wt, coordinator,
                                                          monkeypatch):
    """None en niet 0: een afgelopen koers is niet 'vandaag'."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    stages = _stages("race/tour-de-france-femmes/2026", "Tour de France Femmes",
                     [VANDAAG - timedelta(days=2)], women=True)

    blok = asyncio.run(coordinator._race_entry(dict(FEMMES, level="24"),
                                               stages, VANDAAG))
    assert blok["days_until"] is None


def test_koers_zonder_niveau_krijgt_een_leeg_veld(wt, coordinator, monkeypatch):
    """Een kalender van vóór de niveaus mag geen KeyError opleveren."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    stages = _stages("race/tour-de-france-femmes/2026", "Tour de France Femmes",
                     [VANDAAG + timedelta(days=1)], women=True)

    blok = asyncio.run(coordinator._race_entry(FEMMES, stages, VANDAAG))
    assert blok["level"] == ""


def test_etappes_dragen_het_niveau_van_hun_koers(wt):
    """`_event_stages` geeft het door; `_upcoming_entry` leest het daar."""
    eendaags = wt._event_stages({
        "name": "Milano-Sanremo", "url": "race/milano-sanremo/2026",
        "start": VANDAAG, "end": VANDAAG, "women": False, "level": "1"})
    assert [s["level"] for s in eendaags] == ["1"]


def test_komende_etappe_draagt_het_niveau(coordinator):
    """Zonder dit blijft een uitgezet niveau onder "Komende dagen" staan.

    De cache vooraf vullen scheelt het ophalen van profiel en meta; alles
    wat hier telt zet `_upcoming_entry` daarna alsnog.
    """
    stage = _stages("race/tour-de-france-femmes/2026", "Tour de France Femmes",
                    [VANDAAG + timedelta(days=1)], women=True)[0]
    stage["level"] = "24"
    coordinator._upcoming_cache[stage["stage_url"]] = {"elevation": [], "climbs": []}

    e = asyncio.run(coordinator._upcoming_entry(stage, VANDAAG))
    assert e["level"] == "24"
    assert e["race_key"] == "tour-de-france-femmes"
