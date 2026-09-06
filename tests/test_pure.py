"""Tests voor de reken- en parseerfuncties. Geen netwerk nodig."""
import math

import pytest


# ── namen ───────────────────────────────────────────────────────────

def test_noemt_dames(wt):
    assert wt._noemt_dames("Tour de France Femmes")
    assert wt._noemt_dames("Ronde van Vlaanderen WE")
    assert wt._noemt_dames("Giro d'Italia Women")
    assert not wt._noemt_dames("Santos Tour Down Under")
    assert not wt._noemt_dames("Gent-Wevelgem")


# ── adressen ────────────────────────────────────────────────────────

def _etappe(slug, idx=None, one_day=False, jaar=2026):
    """Een etappe zoals `_event_stages` hem oplevert (alleen wat adressen
    nodig hebben)."""
    from datetime import date
    return {"race_slug": slug, "idx": idx, "one_day": one_day,
            "date": date(jaar, 7, 1)}


def test_gpx_urls_patronen(wt):
    """De slug komt uit de kalender; alleen de bestandsnaam is nog aanname."""
    # grote ronde: parcours.gpx als eerste kandidaat
    assert wt._gpx_urls(_etappe("tour-de-france", 14))[0].endswith(
        "tour-de-france/2026/stage-14-parcours.gpx")
    # elke rittenkoers krijgt dezelfde kandidaten; welke bestaat blijkt vanzelf
    assert any(u.endswith("paris-nice/2026/stage-4-route.gpx")
               for u in wt._gpx_urls(_etappe("paris-nice", 4)))
    assert any(u.endswith("tour-de-france-femmes/2026/stage-2-route.gpx")
               for u in wt._gpx_urls(_etappe("tour-de-france-femmes", 2)))
    # eendaags
    assert wt._gpx_urls(_etappe("tour-of-flanders", one_day=True))[0].endswith(
        "tour-of-flanders/2026/route.gpx")
    # zonder slug valt er niets af te leiden
    assert wt._gpx_urls(_etappe("", 1)) == []


def test_gpx_override_gaat_voor(wt, monkeypatch):
    monkeypatch.setitem(wt.GPX_OVERRIDE, "clasica-san-sebastian/2026",
                        "https://x/eigen.gpx")
    urls = wt._gpx_urls(_etappe("clasica-san-sebastian", one_day=True))
    assert urls[0] == "https://x/eigen.gpx"


def test_times_urls(wt):
    assert wt._times_urls(_etappe("tour-de-france-femmes", 2))[0].endswith(
        "tour-de-france-femmes/2026/stage-2-times.htm")
    # een eendaagse koers heeft geen tijdschema
    assert wt._times_urls(_etappe("clasica-san-sebastian", one_day=True)) == []


def test_gpx_index_url(wt):
    assert wt._gpx_index_urls(_etappe("vuelta", 4)) == [
        "https://www.cyclingstage.com/vuelta-2026-gpx/"]
    assert wt._gpx_index_urls(_etappe("", 4)) == []


def test_race_slug_neemt_slug_of_adres(wt):
    assert wt._race_slug("vuelta") == "vuelta"
    assert wt._race_slug(
        "https://www.cyclingstage.com/vuelta-2026-route/spain-route-2026/") == "vuelta"
    assert wt._race_slug("") == ""


def test_grote_rondes(wt):
    assert wt._is_grote_ronde("vuelta")
    assert wt._is_grote_ronde("https://www.cyclingstage.com/giro-2026-route/")
    assert not wt._is_grote_ronde("renewi-tour")
    assert not wt._is_grote_ronde("vuelta-femenina")


def test_leiderstrui_op_de_nieuwe_slugs(wt):
    assert wt._leiderstrui("vuelta") == "#D0021B"
    assert wt._leiderstrui("giro") == "#E6007E"
    assert wt._leiderstrui("tour-de-france") == "#F3C700"
    assert wt._leiderstrui("renewi-tour") == ""


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
