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


# ── tijdschema ──────────────────────────────────────────────────────

TIJDSCHEMA = """<table>
<tr><th></th><th>done - km</th><th>to go - km</th><th>42 km/h</th></tr>
<tr><td>start - real</td><td>0</td><td>185.2</td><td>12:50</td></tr>
<tr><td>intermediate sprint</td><td>129.1</td><td>56.1</td><td>15:54</td></tr>
<tr><td>Orci&egrave;res-Merlette</td><td>185.2</td><td>0</td><td>17:12</td></tr>
</table>"""


def test_parse_times(wt):
    assert wt._parse_times(TIJDSCHEMA) == [56.1]
    assert wt._parse_times(TIJDSCHEMA.replace("intermediate sprint", "feed zone")) == []




# ── live, en de geschatte stip ──────────────────────────────────────

def _klok(uur, minuut):
    """Een 'nu' zoals `dt_util.now()` er een geeft; alleen uur en minuut."""
    from datetime import datetime
    return datetime(2026, 9, 8, uur, minuut)


def test_live_nu_alleen_tussen_start_en_finish(wt):
    from datetime import date, timedelta
    vandaag = date(2026, 9, 8)

    # vóór de start is het niet live
    assert not wt._live_nu(vandaag, vandaag, "13:10", "17:25", _klok(12, 0))
    # tijdens de koers wel
    assert wt._live_nu(vandaag, vandaag, "13:10", "17:25", _klok(15, 30))
    # precies op de starttijd telt al mee
    assert wt._live_nu(vandaag, vandaag, "13:10", "17:25", _klok(13, 10))
    # na de verwachte finish nog even, want die tijd is een verwachting
    assert wt._live_nu(vandaag, vandaag, "13:10", "17:25", _klok(18, 0))
    assert not wt._live_nu(vandaag, vandaag, "13:10", "17:25", _klok(18, 30))
    # een andere dag is nooit live
    assert not wt._live_nu(vandaag + timedelta(days=1), vandaag, "13:10",
                           "17:25", _klok(15, 30))


def test_live_nu_gokt_niet_zonder_starttijd(wt):
    """Geen starttijd betekent: we weten het niet, dus niet live."""
    from datetime import date
    vandaag = date(2026, 9, 8)
    assert not wt._live_nu(vandaag, vandaag, "", "17:25", _klok(15, 30))
    assert not wt._live_nu(vandaag, vandaag, None, None, _klok(15, 30))
    # zonder finishtijd blijft hij wél live: het einde is dan onbekend, en
    # dat is iets anders dan weten dat hij klaar is
    assert wt._live_nu(vandaag, vandaag, "13:10", "", _klok(20, 0))


def test_show_state_wordt_live_met_de_tijden_erbij(wt, monkeypatch):
    from datetime import date
    vandaag = date(2026, 9, 8)
    monkeypatch.setattr(wt.dt_util, "now", lambda: _klok(15, 30))

    # dit is de reparatie: zonder tijden bleef een koers in de pop-up
    # "Vandaag" melden terwijl hij op dat moment reed
    assert wt._show_state_for(vandaag, vandaag) == "Vandaag"
    assert wt._show_state_for(vandaag, vandaag, "13:10", "17:25") == "LIVE"
    assert wt._show_state_for(vandaag, vandaag, "18:00", "20:00") == "Vandaag"


def test_schema_positie_zonder_profiel_is_lineair(wt):
    """Zonder hoogteprofiel valt hij terug op de tijd, en zegt dat ook."""
    # halverwege de tijd, dus halverwege de kilometers
    assert wt._schema_positie("14:00", "18:00", 200, _klok(16, 0)) == (100.0, 50, "tijd")
    # net begonnen
    assert wt._schema_positie("14:00", "18:00", 200, _klok(14, 0)) == (200.0, 0, "tijd")
    # op de verwachte finish
    assert wt._schema_positie("14:00", "18:00", 200, _klok(18, 0)) == (0.0, 100, "tijd")


def _profiel(punten):
    """Een hoogteprofiel als `[[km, meter], ...]`."""
    return [[k, h] for k, h in punten]


def test_schema_positie_volgt_het_hoogteprofiel(wt):
    """Een slotklim kost meer tijd per kilometer dan de vlakke aanloop.

    100 km vlak gevolgd door 20 km klimmen aan 8%. Lineair in de tijd zou de
    koers halverwege de rijtijd op 60 km staan; met het profiel erbij ligt
    dat punt verder, want die laatste twintig kilometer slokken een groot
    deel van de tijd op.
    """
    prof = _profiel([(0, 0), (100, 0), (120, 1600)])
    km, pct, model = wt._schema_positie("12:00", "16:00", 120, _klok(14, 0), prof)
    assert model == "profiel"
    lineair = 120 * 0.5
    gereden = 120 - km
    assert gereden > lineair + 10, "de klim hoort duidelijk zwaarder te wegen"
    assert gereden < 100, "maar niet zo zwaar dat de vlakke aanloop gratis is"
    assert pct == int(round(gereden / 120 * 100))


def test_schema_positie_op_vlak_terrein_blijft_lineair(wt):
    """Zonder hoogteverschil mag het profiel niets veranderen."""
    prof = _profiel([(0, 50), (60, 50), (120, 50)])
    km, pct, model = wt._schema_positie("12:00", "16:00", 120, _klok(14, 0), prof)
    assert model == "profiel"
    assert abs(km - 60) < 0.2 and abs(pct - 50) <= 1


def test_tempoverdeling_weigert_een_onbruikbaar_profiel(wt):
    assert wt._tempoverdeling(None) is None
    assert wt._tempoverdeling([]) is None
    assert wt._tempoverdeling([[0, 0], [10, 0]]) is None      # te weinig punten
    # een profiel dat niet vooruit loopt levert niets op
    assert wt._tempoverdeling([[0, 0], [0, 10], [0, 20]]) is None


def test_tempoverdeling_begrenst_uitschieters(wt):
    """Een steile afdaling in de GPX mag geen oneindige snelheid geven."""
    prof = _profiel([(0, 0), (1, -400), (2, -800), (3, -1200)])
    verdeling = wt._tempoverdeling(prof)
    assert verdeling is not None
    # elk stuk is even steil, dus de tijd verdeelt gelijk over de drie
    delen = [d for _, d in verdeling]
    assert delen[0] == 0.0 and abs(delen[-1] - 1.0) < 1e-9
    assert abs(delen[1] - 1 / 3) < 0.01


def test_schema_positie_zwijgt_als_ze_niets_weet(wt):
    leeg = (None, None, "")
    # vóór de start en ná de verwachte finish niets tekenen
    assert wt._schema_positie("14:00", "18:00", 200, _klok(13, 0)) == leeg
    assert wt._schema_positie("14:00", "18:00", 200, _klok(18, 30)) == leeg
    # zonder tijd of zonder afstand valt er niets te verdelen
    assert wt._schema_positie("", "18:00", 200, _klok(16, 0)) == leeg
    assert wt._schema_positie("14:00", "", 200, _klok(16, 0)) == leeg
    assert wt._schema_positie("14:00", "18:00", None, _klok(16, 0)) == leeg
    assert wt._schema_positie("14:00", "18:00", 0, _klok(16, 0)) == leeg
    # een finishtijd vóór de start levert geen negatieve duur op
    assert wt._schema_positie("18:00", "14:00", 200, _klok(16, 0)) == leeg


def test_starttijd_van_de_getoonde_etappe_komt_van_de_etappepagina(wt, monkeypatch):
    """De tegel las de starttijd nooit, en dat zag je nergens aan.

    `_fetch_stage` levert de uitslag en die kent geen starttijd;
    `_fetch_stage_meta` leest hem van de etappepagina maar draaide alleen
    voor `upcoming`, waar de getoonde etappe juist niet in staat. Gevolg:
    `start_time` altijd leeg, dus geen tijden op de badge, nooit LIVE, en
    nooit het snellere verversingsritme.
    """
    from datetime import date
    pagina = ("<html><body><p>Stage 16 of the Vuelta starts at 13:20 and the "
              "race is expected to finish around 17:25 - both local times "
              "(CEST).</p><p>1,050 metres of elevation gain</p></body></html>")
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": pagina)
    wt._ETAPPE_HTML.clear()
    etappe = {"stage_url": "https://www.cyclingstage.com/vuelta-2026-route/stage-16-spain-2026/",
              "date": date(2026, 9, 8), "idx": 16, "distance_km": 181.1}
    meta = wt._fetch_stage_meta(etappe)
    assert meta["ok"]
    assert meta["start_time"] == "13:20"
    assert meta["finish_time"] == "17:25"
    # en daarmee wordt de etappe ook echt live genoemd
    assert wt._live_nu(date(2026, 9, 8), date(2026, 9, 8), meta["start_time"],
                       meta["finish_time"], _klok(16, 3))
    km, pct, model = wt._schema_positie(meta["start_time"], meta["finish_time"],
                                        181.1, _klok(16, 3))
    assert km is not None and 0 < km < 181.1 and model == "tijd"
