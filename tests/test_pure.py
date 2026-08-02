"""Tests voor de reken- en parseerfuncties. Geen netwerk nodig."""
import math

import pytest


# ── tijd en getallen ────────────────────────────────────────────────

def test_secs(wt):
    assert wt._secs("52:14:33") == 188073
    assert wt._secs("1:20") == 80
    assert wt._secs("+0:14") == 14
    assert wt._secs("-") is None
    assert wt._secs("") is None


def test_move(wt):
    assert wt._move(5, 3) == 2       # gestegen
    assert wt._move(2, 4) == -2      # gedaald
    assert wt._move(None, 3) is None


def test_name_key_is_volgorde_onafhankelijk(wt):
    assert wt._name_key("Pogačar Tadej") == wt._name_key("Tadej Pogačar")
    assert wt._name_key("del Toro Isaac") != wt._name_key("Seixas Paul")


def test_noemt_dames(wt):
    assert wt._noemt_dames("Tour de France Femmes")
    assert wt._noemt_dames("Ronde van Vlaanderen WE")
    assert wt._noemt_dames("Giro d'Italia Women")
    assert not wt._noemt_dames("Santos Tour Down Under")
    assert not wt._noemt_dames("Gent-Wevelgem")


# ── adressen ────────────────────────────────────────────────────────

def test_gpx_urls_patronen(wt):
    # grote ronde: parcours.gpx als eerste kandidaat
    assert wt._gpx_urls("race/tour-de-france/2026", 14, False)[0].endswith(
        "tour-de-france/2026/stage-14-parcours.gpx")
    # overige rittenkoers en vrouwen: route.gpx
    assert wt._gpx_urls("race/paris-nice/2026", 4, False)[0].endswith(
        "paris-nice/2026/stage-4-route.gpx")
    assert wt._gpx_urls("race/tour-de-france-femmes/2026", 2, False)[0].endswith(
        "tour-de-france-femmes/2026/stage-2-route.gpx")
    # eendaags
    assert wt._gpx_urls("race/ronde-van-vlaanderen/2026", None, True)[0].endswith(
        "tour-of-flanders/2026/route.gpx")
    # onbekende koers
    assert wt._gpx_urls("race/onbekend/2026", 1, False) == []


def test_gpx_override_gaat_voor(wt, monkeypatch):
    monkeypatch.setitem(wt.GPX_OVERRIDE, "san-sebastian/2026", "https://x/eigen.gpx")
    assert wt._gpx_urls("race/san-sebastian/2026", None, True)[0] == "https://x/eigen.gpx"


def test_times_urls(wt):
    assert wt._times_urls("race/tour-de-france-femmes/2026", 2, False)[0].endswith(
        "tour-de-france-femmes/2026/stage-2-times.htm")
    assert wt._times_urls("race/san-sebastian/2026", None, True) == []


def test_stage_article_url(wt):
    assert wt._stage_article_url("race/tour-de-france/2026", 18, False) == (
        "https://www.cyclingstage.com/tour-de-france-2026-route/stage-18-tdf-2026/")
    assert wt._stage_article_url("race/tour-de-france-femmes/2026", 2, False) == (
        "https://www.cyclingstage.com/tour-de-france-femmes-2026/"
        "stage-2-tdf-2026-women/")


# ── hoogtelijn ──────────────────────────────────────────────────────

def _profiel_met_toppen():
    """221 km met zes scherpe toppen (zoals San Sebastián)."""
    klimmen = [(56, 2.2, 176), (70, 4.2, 307), (91, 8.6, 593),
               (111, 4.4, 273), (159, 7.9, 442), (178, 3.8, 403)]
    serie, km = [], 0.0
    while km < 221:
        h = 40.0
        for top, lengte, hoogte in klimmen:
            d = km - top
            if abs(d) < lengte:
                h += hoogte * (1 - abs(d) / lengte)
        serie.append((round(km, 3), round(h, 1)))
        km += 0.02
    return serie, klimmen


def test_lttb_behoudt_toppen(wt):
    serie, klimmen = _profiel_met_toppen()
    voor = wt._lttb(serie, 45)
    assert len(voor) == 45
    assert voor[0] == serie[0] and voor[-1] == serie[-1]
    for top, _lengte, hoogte in klimmen:
        dichtst = min(voor, key=lambda p: abs(p[0] - top))
        assert abs((40 + hoogte) - dichtst[1]) < 5, f"top op {top} km verdwenen"


def test_lttb_randgevallen(wt):
    kort = [(0.0, 1.0), (1.0, 2.0)]
    assert wt._lttb(kort, 150) == kort          # minder punten dan gevraagd
    serie, _ = _profiel_met_toppen()
    uit = wt._lttb(serie, 200)
    assert all(uit[i][0] <= uit[i + 1][0] for i in range(len(uit) - 1))


# ── klimdetectie ────────────────────────────────────────────────────

def _rit(stukken, stap=0.05):
    """stukken: lijst van ('vlak'|'klim'|'daal', lengte_km, stijging_m)."""
    serie, km = [], 0.0
    for soort, lengte, stijging in stukken:
        n = max(1, int(lengte / stap))
        for k in range(n):
            if soort == "vlak":
                h = 35 + 4 * math.sin(km * 2.1)
            elif soort == "klim":
                h = 35 + stijging * (k + 1) / n
            else:
                h = 35 + stijging * (1 - (k + 1) / n)
            serie.append([round(km, 3), round(h, 1)])
            km += stap
    return serie


def test_korte_steile_klim_wordt_gevonden(wt):
    # drie keer Montmartre: 1,1 km met 65 hoogtemeters
    stukken = [("vlak", 38.9, 0)]
    for _ in range(3):
        stukken += [("klim", 1.1, 65), ("daal", 1.6, 65), ("vlak", 14.0, 0)]
    cl = wt._detect_climbs(_rit(stukken))
    assert len(cl) == 3, f"verwacht 3 beklimmingen, kreeg {len(cl)}"


def test_vlakke_rit_heeft_geen_klimmen(wt):
    assert wt._detect_climbs(_rit([("vlak", 150, 0)])) == []


# ── kijkscore ───────────────────────────────────────────────────────

def test_watchability_zonder_data_is_none(wt):
    assert wt._watchability(None, 234, [], "RR", None) is None


def test_watchability_met_data(wt):
    top = [{"category": "HC", "km_to_finish": 0}]
    assert wt._watchability(438, 170.9, top, "RR", 5624) >= 9      # aankomst bergop
    assert wt._watchability(25, 180, [], "RR", 900) == 3           # vlakke sprint
    assert wt._watchability(None, 180, [], "RR", 3200) == 5        # alleen hoogtemeters
    mm = [{"name": "Montmartre", "category": "4", "km_to_finish": k,
           "length_km": 1.1, "steepness_pct": 5.9} for k in (43.7, 27.0, 10.3)]
    assert wt._watchability(40, 89, mm, "RR", 1028) >= 7           # circuitfinale


# ── tijdschema en zenders ───────────────────────────────────────────

TIJDSCHEMA = """<table>
<tr><th></th><th>done - km</th><th>to go - km</th><th>42 km/h</th></tr>
<tr><td>start - real</td><td>0</td><td>185.2</td><td>12:50</td></tr>
<tr><td>intermediate sprint</td><td>129.1</td><td>56.1</td><td>15:54</td></tr>
<tr><td>Orci&egrave;res-Merlette</td><td>185.2</td><td>0</td><td>17:12</td></tr>
</table>"""


def test_parse_times(wt):
    assert wt._parse_times(TIJDSCHEMA) == [56.1]
    assert wt._parse_times(TIJDSCHEMA.replace("intermediate sprint", "feed zone")) == []


def _tv_blok(tijd, naam, vlaggen):
    vl = "".join(f'<img alt="{v}" src="https://x/svg/flags/{v}.svg">' for v in vlaggen)
    return (f'<div><span>{tijd}</span><img src="https://cyclingflash.com/_next/'
            f'image?url=https%3A%2F%2Fcdn%2F1%2Fx.jpg&amp;w=1920"><span>{naam}</span>'
            f'{vl}</div>')


TV = ('<h5><a href="https://www.wielerflits.nl/wielerkalender/tour-de-france-2026'
      '/etappes/13/">Tour de France</a></h5>'
      + _tv_blok("12:45", "Eurosport 1", ["NL", "BE"])
      + _tv_blok("14:15", "NPO1", ["NL"])
      + '<h5><a href="https://www.wielerflits.nl/wielerkalender/andere-2026'
        '/etappes/2/">Andere koers</a></h5>'
      + _tv_blok("15:00", "Pickx+ Sports 1", ["BE"]))


def test_parse_channels(wt):
    ch = wt._parse_channels(TV, "tour-de-france", "2026", 13, "Tour de France")
    assert [c["name"] for c in ch] == ["Eurosport 1", "NPO1"]     # alleen NL-vlag
    assert ch[0]["time"] == "12:45"
    assert ch[0]["logo"].startswith("https://") and "_next" not in ch[0]["logo"]
    assert wt._parse_channels(TV, "tour-de-france", "2026", 99, "Tour de France") == []


# ── naamreparatie ───────────────────────────────────────────────────

def test_repair_rows_zet_verwisselde_namen_terug(wt):
    roster = {wt._name_key(n): t for n, t in {
        "Pidcock Tom": "Pinarello Q36.5 Pro Cycling Team",
        "Carapaz Richard": "EF Education - EasyPost"}.items()}
    rijen = [
        {"rank": 8, "rider": "Pidcock Tom", "team": "EF Education - EasyPost"},
        {"rank": 9, "rider": "Carapaz Richard",
         "team": "Pinarello Q36.5 Pro Cycling Team"},
    ]
    assert wt._repair_rows(rijen, roster) == 2
    assert rijen[0]["rider"] == "Carapaz Richard"
    assert rijen[1]["rider"] == "Pidcock Tom"


def test_repair_rows_laat_goede_rijen_met_rust(wt):
    roster = {wt._name_key("Ayuso Juan"): "Lidl - Trek"}
    rijen = [{"rank": 7, "rider": "Ayuso Juan", "team": "Lidl - Trek"}]
    assert wt._repair_rows(rijen, roster) == 0
    assert rijen[0]["rider"] == "Ayuso Juan"


# ── dagwinst op positie ─────────────────────────────────────────────

def test_gain_time_by_rank(wt):
    # stand na etappe 18 (positie -> tijd)
    vorige = {1: "64:35:13", 2: "64:39:45", 5: "64:44:35", 10: "64:56:13"}
    rijen = [
        {"rank": 1, "time": "67:53:00", "prev": 1},
        {"rank": 2, "time": "68:00:11", "prev": 2},
        {"rank": 7, "time": "68:08:58", "prev": 5},
        {"rank": 8, "time": "68:14:15", "prev": 10},
    ]
    assert wt._gain_time_by_rank(rijen, vorige) == 4
    assert rijen[1]["gain_s"] == 159      # +2:39 verloren
    assert rijen[2]["gain_s"] == 396      # +6:36 verloren
    assert rijen[3]["gain_s"] == 15       # +0:15


def test_gain_pts_by_rank(wt):
    rijen = [{"rank": 1, "points": 502, "prev": 1},
             {"rank": 5, "points": 230, "prev": 6}]
    wt._gain_pts_by_rank(rijen, {1: 477, 6: 210})
    assert [r["gain"] for r in rijen] == [25, 20]
