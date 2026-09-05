"""De kalenderparser van cyclingstage, op echte HTML.

`tests/fixtures/cyclingstage_kalender_2026.html` is de pagina
https://www.cyclingstage.com/uci/cycling-calendar-2026/ zoals hij op
23 augustus 2026 was, opgeslagen in een browser. Geen verzonnen HTML: die
heeft in dit project al twee keer een echte bug gemaskeerd.
"""
from datetime import date
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "cyclingstage_kalender_2026.html"


@pytest.fixture(scope="module")
def kalender(cs):
    return cs.parse_kalender(FIXTURE.read_text(), 2026)


def _zoek(kalender, naam):
    for k in kalender:
        if k["name"] == naam:
            return k
    raise AssertionError(f"{naam} staat niet in de kalender")


def test_alle_koersen_komen_eruit(kalender):
    # tien maandtabellen, 49 koersen; verandert dit getal, dan is de pagina
    # veranderd en hoort de fixture ververst te worden
    assert len(kalender) == 49


def test_datums_lopen_niet_achteruit(kalender):
    krom = [k["name"] for k in kalender if k["end"] < k["start"]]
    assert krom == []


def test_koers_van_een_dag(kalender):
    lbl = _zoek(kalender, "Liège - Bastogne - Liège")
    assert lbl["start"] == date(2026, 4, 26)
    assert lbl["end"] == lbl["start"]


def test_koers_binnen_een_maand(kalender):
    renewi = _zoek(kalender, "Renewi Tour")
    assert (renewi["start"], renewi["end"]) == (date(2026, 8, 19), date(2026, 8, 23))


def test_koers_over_een_maandgrens(kalender):
    """De Vuelta staat als "8/22-13" in de tabel van september.

    Zonder het maandvoorvoegsel zou hij van 22 september tot 13 september
    lopen — een koers die achteruit rijdt.
    """
    vuelta = _zoek(kalender, "Vuelta a España")
    assert (vuelta["start"], vuelta["end"]) == (date(2026, 8, 22), date(2026, 9, 13))

    giro_w = _zoek(kalender, "Giro d'Italia Women")
    assert (giro_w["start"], giro_w["end"]) == (date(2026, 5, 30), date(2026, 6, 7))


def test_vrouwenkoersen_worden_herkend(kalender):
    for naam in ("Strade Bianche Donne", "Vuelta Femenina", "Giro d'Italia Women",
                 "Tour de France Femmes", "Paris - Roubaix Femmes",
                 "Amstel Gold Race (w)", "Tour of Flanders (w)"):
        assert _zoek(kalender, naam)["women"], naam

    for naam in ("Vuelta a España", "Paris - Roubaix", "Renewi Tour",
                 "Amstel Gold Race (m)", "Tour of Flanders (m)"):
        assert not _zoek(kalender, naam)["women"], naam


def test_geslacht_ook_uit_het_adres(cs):
    """Twee onafhankelijke signalen; één ervan volstaat."""
    html = ('<table><tr><td class="right">5</td>'
            '<td><a href="/ronde-van-drenthe-2026-women/">Ronde van Drenthe</a></td>'
            '<td>NL</td><td><a href="/ronde-van-drenthe-2026-women/route-rvd/">'
            'Route</a></td></tr></table>')
    koers, = cs.parse_kalender(html, 2026)
    assert koers["women"], "de naam zegt niets, het adres wel"


def test_route_adres_staat_erbij(kalender):
    vuelta = _zoek(kalender, "Vuelta a España")
    assert vuelta["route_url"] == (
        "https://www.cyclingstage.com/vuelta-2026-route/spain-route-2026/")
    # relatieve adressen worden volledig gemaakt
    assert all(not k["route_url"] or k["route_url"].startswith("https://")
               for k in kalender)


def test_koersen_zonder_route_blijven_staan(kalender):
    """Later in het seizoen is de route nog niet gepubliceerd."""
    zonder = [k["name"] for k in kalender if not k["route_url"]]
    assert "Tour of Lombardy" in zonder
    assert len(zonder) == 6


def test_kapotte_link_op_de_pagina_wordt_genegeerd(kalender):
    """Cyclingstage heeft bij de Tour de France Femmes een link die geen
    adres is (`http://Tour de France Femmes 2026`). Die telt niet mee, maar
    de koers zelf blijft staan omdat zijn routeadres wél klopt."""
    tdff = _zoek(kalender, "Tour de France Femmes")
    assert tdff["url"] == ""
    assert tdff["route_url"].endswith("/route-tdf-2026-women/")
    assert tdff["women"]


def test_onzin_levert_een_lege_lijst(cs):
    assert cs.parse_kalender("", 2026) == []
    assert cs.parse_kalender("<html><body>niets</body></html>", 2026) == []


def test_onmogelijke_datum_laat_de_rest_heel(cs):
    html = ('<h2>February</h2><table>'
            '<tr><td class="right">31</td><td><a href="/x/">Koers X</a></td>'
            '<td>NL</td><td><a href="/x/route/">Route</a></td></tr>'
            '<tr><td class="right">3</td><td><a href="/y/">Koers Y</a></td>'
            '<td>NL</td><td><a href="/y/route/">Route</a></td></tr></table>')
    koersen = cs.parse_kalender(html, 2026)
    assert [k["name"] for k in koersen] == ["Koers Y"]


# ── etappelijst ─────────────────────────────────────────────────────

ROUTE = Path(__file__).parent / "fixtures" / "cyclingstage_vuelta_2026_route.html"


@pytest.fixture(scope="module")
def etappes(cs):
    return cs.parse_etappes(ROUTE.read_text(), 2026)


def test_alle_etappes_en_geen_rustdagen(etappes):
    """De Vuelta 2026 heeft 21 etappes en twee rustdagen.

    Rustdagen staan als eigen rij in dezelfde tabel; die horen er niet in,
    want de rest van de integratie rekent elke regel als een etappe.
    """
    assert len(etappes) == 21
    assert [e["idx"] for e in etappes] == list(range(1, 22))


def test_datums_lopen_door_over_de_maandgrens(etappes):
    assert etappes[0]["date"] == date(2026, 8, 22)
    assert etappes[-1]["date"] == date(2026, 9, 13)
    # de rustdag van 31 augustus zit tussen etappe 9 en 10, maar telt niet mee
    assert etappes[8]["date"] == date(2026, 8, 30)
    assert etappes[9]["date"] == date(2026, 9, 1)
    # oplopend, zonder gaten in de nummering
    assert all(a["date"] < b["date"] for a, b in zip(etappes, etappes[1:]))


def test_start_en_finish_los(etappes):
    vier = etappes[3]
    assert vier["departure"] == "Andorra La Vella"
    assert vier["arrival"] == "Andorra La Vella"
    # een plaatsnaam met een koppelteken erin mag niet in tweeën vallen
    zeven = etappes[6]
    assert zeven["departure"] == "Vall d'Alba"
    assert zeven["arrival"] == "Valdelinares"


def test_afstand_en_terrein(etappes):
    assert etappes[0]["distance_km"] == 9.4
    assert etappes[0]["stage_type"] == "itt"
    assert etappes[3]["distance_km"] == 104.8
    assert etappes[3]["stage_type"] == "mountain"
    assert etappes[4]["stage_type"] == "flat"


def test_typefout_op_de_site_wordt_opgevangen(etappes):
    """Etappe 2 staat op cyclingstage als "hils" in plaats van "hills"."""
    assert etappes[1]["stage_type"] == "hilly"


def test_elke_etappe_draagt_zijn_eigen_adres(etappes):
    assert etappes[3]["url"] == (
        "https://www.cyclingstage.com/vuelta-2026-route/stage-4-spain-2026/")
    assert all(e["url"].startswith("https://www.cyclingstage.com/") for e in etappes)


def test_routepagina_zonder_tabel(cs):
    assert cs.parse_etappes("<html><body>nog geen route</body></html>", 2026) == []
    assert cs.parse_etappes("", 2026) == []


# ── de etappetekst ──────────────────────────────────────────────────

ETAPPE4 = Path(__file__).parent / "fixtures" / "cyclingstage_vuelta_2026_stage4.html"


def test_meta_uit_de_etappetekst(cs):
    """Deze drie kwamen tot nu toe van procyclingstats.

    De verwachte finishtijd is zelfs beter dan wat we hadden: die werd
    geschat uit afstand en profiel, en staat hier gewoon op de pagina.
    """
    meta = cs.parse_etappe_meta(ETAPPE4.read_text())
    assert meta == {"start_time": "14:40", "finish_time": "17:30",
                    "vertical_m": 2953}


def test_meta_verzint_niets(cs):
    """Wat er niet staat, komt er niet in."""
    assert cs.parse_etappe_meta("<p>Een etappe zonder tijden.</p>") == {}
    assert cs.parse_etappe_meta("") == {}


def test_hoogtemeters_zonder_duizendtalkomma(cs):
    meta = cs.parse_etappe_meta("<p>a route with 850 metres of climbing</p>")
    assert meta["vertical_m"] == 850


def test_de_bestaande_colparser_leest_deze_pagina(wt, monkeypatch):
    """`_fetch_stage_names` in sensor.py is gebouwd op deze teksten en
    blijft; hier wordt hij op echte HTML nagelopen in plaats van alleen op
    de pagina's die toevallig binnenkwamen."""
    import io
    import urllib.request

    ruw = ETAPPE4.read_bytes()

    class Nep(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: Nep(ruw))
    climbs, route = wt._fetch_stage_names("https://x/", 104.8)

    assert route["departure"] == "Andorra La Vella"
    assert route["arrival"] == "Andorra La Vella"
    assert route["finish_time"] == "17:30"
    namen = [c["name"] for c in climbs]
    assert namen == ["Port d'Envalira", "Collada de Beixalis",
                     "Col d'Ordino", "Alto de la Comella"]
    assert climbs[1]["length_km"] == 6.5 and climbs[1]["steepness_pct"] == 8.5
    # de tekst noemt alleen bij de Ordino hoeveel er nog te gaan is
    assert climbs[2]["km_to_finish"] == 26.1


# ── adressen uit de bron in plaats van uit een tabel ────────────────

def test_slug_uit_de_kalenderadressen(cs, kalender):
    """Nagelopen op alle 49 koersen van 2026, niet op een handvol.

    Tot 0.18 stond deze koppeling in drie handmatige tabellen. Een
    verkeerd geraden slug liet het profiel stilletjes leeg — dat is precies
    wat er met de Vuelta gebeurde.
    """
    gevonden = {k["name"]: cs.slug_van(k["url"] or k["route_url"], 2026)
                for k in kalender}
    assert gevonden["Vuelta a España"] == "vuelta"
    assert gevonden["Giro d'Italia"] == "giro"
    assert gevonden["Tour de France"] == "tour-de-france"
    assert gevonden["Tour Down Under"] == "tour-down-under"
    assert gevonden["Paris - Roubaix"] == "paris-roubaix"
    # het jaartal staat bij vrouwenkoersen middenin het pad
    assert gevonden["Tour of Flanders (w)"] == "tour-of-flanders-women"
    assert gevonden["Amstel Gold Race (w)"] == "amstel-gold-race-women"
    # elke koers levert een slug op, en geen enkele houdt het jaartal
    assert all(gevonden.values())
    assert not any("2026" in s for s in gevonden.values())


def test_slug_van_onzin(cs):
    assert cs.slug_van("", 2026) == ""
    assert cs.slug_van("https://elders.nl/iets/", 2026) == ""


def test_gpx_adressen(cs):
    urls = cs.gpx_urls("vuelta", 2026, 4)
    assert urls[0] == ("https://cdn.cyclingstage.com/images/vuelta/2026/"
                       "stage-4-parcours.gpx")
    assert any(u.endswith("stage-4-route.gpx") for u in urls)
    # eendaagse koers: geen etappenummer
    assert cs.gpx_urls("paris-roubaix", 2026)[0].endswith("/2026/route.gpx")
    assert cs.gpx_urls("", 2026, 4) == []


def test_gpx_overzichtspagina(cs):
    assert cs.gpx_index_url("vuelta", 2026) == (
        "https://www.cyclingstage.com/vuelta-2026-gpx/")
    assert cs.gpx_index_url("", 2026) == ""


def test_tijdschema_adressen(cs):
    urls = cs.times_url("vuelta", 2026, 4)
    assert urls[0] == ("https://www.cyclingstage.com/images/vuelta/2026/"
                       "stage-4-times.htm")
    assert cs.times_url("vuelta", 2026, None) == []


# ── de keten: kalender -> etappes ───────────────────────────────────

def test_kalender_en_etappes_samen(wt, monkeypatch):
    """Van kalenderpagina tot etappelijst, met de echte pagina's.

    Dit is de test die de overstap dekt: hij loopt dezelfde weg als de
    coordinator en gebruikt geen enkele handmatige tabel meer.
    """
    kal = (Path(__file__).parent / "fixtures"
           / "cyclingstage_kalender_2026.html").read_text()
    route = ROUTE.read_text()

    def nep_haal(url, wat=""):
        if "cycling-calendar" in url:
            return kal
        # de etappetabel staat op /vuelta-2026-route/, niet op de routepagina
        return route if url.endswith("/vuelta-2026-route/") else ""

    monkeypatch.setattr(wt, "_haal_html", nep_haal)

    koersen, telling, fouten = wt._fetch_calendar(2026, ["m", "v"])
    assert fouten == []
    assert telling == {"Mannen": 38, "Vrouwen": 11}

    vuelta = next(k for k in koersen if k["name"] == "Vuelta a España")
    assert vuelta["slug"] == "vuelta"

    etappes = wt._event_stages(vuelta)
    assert len(etappes) == 21
    eerste, vierde, laatste = etappes[0], etappes[3], etappes[-1]

    assert eerste["date"] == date(2026, 8, 22)
    assert laatste["date"] == date(2026, 9, 13)
    assert vierde["idx"] == 4
    assert vierde["departure"] == "Andorra La Vella"
    assert vierde["distance_km"] == 104.8
    assert vierde["stage_type"] == "mountain"
    assert vierde["race_slug"] == "vuelta"
    assert vierde["stage_url"].endswith("/stage-4-spain-2026/")
    assert vierde["level"] == "m" and not vierde["women"]

    # en de adressen die daaruit volgen, zonder één handmatige tabel
    assert wt._gpx_urls(vierde)[0].endswith("vuelta/2026/stage-4-parcours.gpx")
    assert wt._times_urls(vierde)[0].endswith("vuelta/2026/stage-4-times.htm")
    assert wt._gpx_index_urls(vierde) == [
        "https://www.cyclingstage.com/vuelta-2026-gpx/"]
    assert wt._is_grote_ronde(vuelta["slug"])
    assert wt._leiderstrui(vuelta["slug"]) == "#D0021B"


def test_eendaagse_koers_krijgt_een_etappe(wt, monkeypatch):
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": "")
    koers = {"name": "Paris - Roubaix",
             "url": "https://www.cyclingstage.com/paris-roubaix-2026/route-pr-2026/",
             "slug": "paris-roubaix", "start": date(2026, 4, 12),
             "end": date(2026, 4, 12), "women": False, "level": "m"}
    etappes = wt._event_stages(koers)
    assert len(etappes) == 1
    assert etappes[0]["one_day"] is True
    assert etappes[0]["idx"] is None
    # eendaags: geen etappenummer in het GPX-adres, geen tijdschema
    assert wt._gpx_urls(etappes[0])[0].endswith("paris-roubaix/2026/route.gpx")
    assert wt._times_urls(etappes[0]) == []


# ── uitslag en klassement ───────────────────────────────────────────

UITSLAG2 = (Path(__file__).parent / "fixtures"
            / "cyclingstage_vuelta_2026_stage2_results.html")


@pytest.fixture(scope="module")
def uitslag(cs):
    return cs.parse_uitslag(UITSLAG2.read_text())


def test_etappe_uitslag(uitslag):
    """Cyclingstage zet de uitslag als tekst onder een kop, niet in een tabel."""
    res = uitslag["results"]
    assert len(res) == 10
    assert res[0] == {"rank": 1, "rider": "Matthew Brennan",
                      "country": "gbr", "time": "4:47:47"}
    # "s.t." blijft heel; die punt hoort erbij
    assert res[1]["time"] == "s.t."
    assert res[-1]["rank"] == 10


def test_algemeen_klassement(uitslag):
    gc = uitslag["gc"]
    assert len(gc) == 10
    assert gc[0]["rider"] == "Tadej Pogacar" and gc[0]["time"] == ""
    assert gc[1] == {"rank": 2, "rider": "Wout van Aert",
                     "country": "bel", "time": "+0:09"}
    assert gc[-1]["time"] == "+0:27"


def test_landcode_is_geen_ploeg(uitslag):
    """Cyclingstage geeft het land, niet de ploeg.

    Een land in het ploegveld zetten zou precies het verzinnen zijn dat dit
    project niet doet, dus het gaat als `country` mee.
    """
    for rij in uitslag["results"] + uitslag["gc"]:
        assert "team" not in rij
        assert len(rij["country"]) in (2, 3)


def test_namen_met_accenten_en_streepjes(uitslag):
    namen = [r["rider"] for r in uitslag["gc"]]
    assert "Léo Bisiaux" in namen
    assert "Stefan Küng" in namen
    assert "Finn Fisher-Black" in namen


def test_blokken_dragen_hun_kop(cs):
    koppen = [k for k, _ in cs.parse_blokken(UITSLAG2.read_text())]
    assert koppen == ["Stage 2 Results – 2026 Vuelta", "GC after stage 1"]


def test_kop_bepaalt_niet_bij_welke_etappe_het_hoort(uitslag):
    """De pagina van etappe 2 zet "GC after stage 1" boven het klassement
    ná etappe 2. Dat nummer is dus onbruikbaar om mee te rekenen; het telt
    alleen om te zien wélk klassement het is."""
    assert uitslag["gc"][0]["rider"] == "Tadej Pogacar"


def test_tekst_die_toevallig_genummerd_is_telt_niet(cs):
    """Een alinea die met "1." begint is nog geen uitslag."""
    html = ("<h2>Race report</h2><p>1. Dit is gewoon tekst zonder land<br>"
            "2. En nog een regel</p>")
    assert cs.parse_blokken(html) == []


def test_gaten_in_de_nummering_maken_het_ongeldig(cs):
    html = ("<h2>Results</h2><p>1. Eerste Renner (ned) 1:00<br>"
            "3. Derde Renner (bel) s.t.</p>")
    assert cs.parse_uitslag(html)["results"] == []


def test_lege_pagina(cs):
    leeg = cs.parse_uitslag("")
    assert all(v == [] for v in leeg.values())
    assert set(leeg) == {"results", "gc", "points", "kom", "youth"}
    assert cs.parse_blokken("") == []


def test_klassementen_staan_er_nog_niet_op(cs, uitslag):
    """Cyclingstage publiceert punten-, berg- en jongerenklassement (nog)
    niet in leesbare vorm: de resultatenpagina heeft ze niet en de eigen
    klassementspagina's bevatten alleen de puntenverdeling met de melding
    dat de standen "in a table during La Vuelta" komen."""
    assert uitslag["points"] == []
    assert uitslag["kom"] == []
    assert uitslag["youth"] == []


def test_klassement_wordt_herkend_zodra_het_er_is(cs):
    """De herkenning staat klaar; als cyclingstage het gaat publiceren
    loopt het mee zonder codewijziging."""
    html = ("<h2>Points classification after stage 5</h2>"
            "<p>1. Mads Pedersen (den) 96<br>2. Jasper Philipsen (bel) 74</p>"
            "<h2>KOM classification after stage 5</h2>"
            "<p>1. Jay Vine (aus) 31<br>2. Koen Bouwman (ned) 22</p>")
    uit = cs.parse_uitslag(html)
    assert [r["rider"] for r in uit["points"]] == ["Mads Pedersen", "Jasper Philipsen"]
    assert uit["points"][0]["time"] == "96"
    assert [r["rider"] for r in uit["kom"]] == ["Jay Vine", "Koen Bouwman"]
    # en zo'n kop mag niet als etappe-uitslag eindigen
    assert uit["results"] == []


def test_uitslagadres_uit_het_etappeadres(cs):
    """Nagekeken tegen de echte pagina: het adres hieronder is precies waar
    de opgeslagen uitslag van etappe 2 vandaan komt."""
    assert cs.uitslag_url(
        "https://www.cyclingstage.com/vuelta-2026-route/stage-2-spain-2026/"
    ) == "https://www.cyclingstage.com/vuelta-2026-results/stage-2-spain-results-2026/"
    assert cs.uitslag_url(
        "https://www.cyclingstage.com/tour-de-france-2026-route/stage-3-tdf-2026/"
    ).endswith("/tour-de-france-2026-results/stage-3-tdf-results-2026/")
    # een eendaagse koers heeft geen -route/ in het pad
    assert cs.uitslag_url("https://www.cyclingstage.com/paris-roubaix-2026/") == ""
    assert cs.uitslag_url("") == ""


def test_overzicht_en_klassementsadressen(cs):
    assert cs.uitslag_index_url("vuelta", 2026) == (
        "https://www.cyclingstage.com/vuelta-2026-results/")
    urls = cs.klassement_urls("vuelta", 2026)
    assert urls["points"].endswith("/vuelta-2026-points-classification/")
    assert urls["kom"].endswith("/vuelta-2026-kom-classification/")
    assert cs.klassement_urls("", 2026) == {}


def test_hele_keten_tot_en_met_de_uitslag(wt, monkeypatch):
    """Kalender -> etappes -> uitslag, met de vier echte pagina's."""
    fix = Path(__file__).parent / "fixtures"
    # op volledige achtervoegsels matchen; de etappeadressen bevatten het
    # routeadres, dus "bevat" zou de verkeerde pagina teruggeven
    paginas = {
        "/uci/cycling-calendar-2026/": (fix / "cyclingstage_kalender_2026.html").read_text(),
        "/vuelta-2026-route/": (fix / "cyclingstage_vuelta_2026_route.html").read_text(),
        "/stage-4-spain-2026/": (fix / "cyclingstage_vuelta_2026_stage4.html").read_text(),
        "/stage-2-spain-results-2026/": UITSLAG2.read_text(),
    }

    def nep_haal(url, wat=""):
        for sleutel, html in paginas.items():
            if url.endswith(sleutel):
                return html
        return ""

    monkeypatch.setattr(wt, "_haal_html", nep_haal)

    koersen, _, _ = wt._fetch_calendar(2026, ["m"])
    vuelta = next(k for k in koersen if k["name"] == "Vuelta a España")
    etappes = wt._event_stages(vuelta)

    # etappe 4: meta van zijn eigen pagina
    meta = wt._fetch_stage_meta(etappes[3])
    assert meta["start_time"] == "14:40"
    assert meta["finish_time"] == "17:30"
    assert meta["vertical"] == 2953
    assert meta["distance"] == 104.8
    assert meta["departure"] == "Andorra La Vella"

    # etappe 2: uitslag en klassement
    data = wt._fetch_stage(etappes[1], result_n=10, gc_n=10)
    assert data["ok"] and data["finished"]
    assert data["results"][0]["rider"] == "Matthew Brennan"
    assert data["results"][0]["time"] == "4:47:47"
    assert data["gc"][0]["rider"] == "Tadej Pogacar"
    assert len(data["gc"]) == 10
    # de klassementen die cyclingstage nog niet publiceert blijven leeg
    assert data["points_top"] == [] and data["kom_top"] == []
    assert data["points_leader"] == ""


def test_uitslag_wordt_afgekapt_op_de_ingestelde_lengte(wt, monkeypatch):
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": UITSLAG2.read_text())
    etappe = {"stage_url":
              "https://www.cyclingstage.com/vuelta-2026-route/stage-2-spain-2026/"}
    data = wt._fetch_stage(etappe, result_n=3, gc_n=5)
    assert len(data["results"]) == 3
    assert len(data["gc"]) == 5


def test_etappe_zonder_uitslagpagina(wt, monkeypatch):
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": "")
    etappe = {"stage_url":
              "https://www.cyclingstage.com/vuelta-2026-route/stage-9-spain-2026/"}
    data = wt._fetch_stage(etappe)
    assert data["ok"] is False and data["finished"] is False
    assert data["results"] == []


# ── de weg naar de etappelijst als de kalender hem niet geeft ────────
#
# De kalender van 2026 laat de routekolom leeg voor de Tour of Britain, het
# WK, Lombardije, Parijs-Tours en de twee Canadese eendaagse. Die koersen
# komen dus met hun kóérspagina binnen in plaats van met hun routepagina, en
# daar staat de etappetabel niet vooraan.


def test_kalender_koersen_zonder_routeadres(kalender):
    """Vastleggen wélke koersen dit raakt; verandert dat, dan is de bron
    veranderd en hoort de fixture ververst te worden."""
    zonder = [k["name"] for k in kalender if not k["route_url"]]
    assert zonder == ["Tour of Britain", "Grand Prix de Québec",
                      "Grand Prix de Montréal", "World Championships",
                      "Tour of Lombardy", "Paris - Tours"]
    # de koerspagina staat er wél, en die linkt naar de rest
    tob = _zoek(kalender, "Tour of Britain")
    assert tob["url"] == "https://www.cyclingstage.com/tour-of-britain-2026/"
    assert tob["start"] == date(2026, 9, 2) and tob["end"] == date(2026, 9, 6)


def test_de_rijkste_tabel_wint(cs, etappes):
    """Een tabel eerder op de pagina mag de etappetabel niet verdringen.

    Dit is wat de Tour of Britain één etappe gaf: de eerste tabel van de
    koerspagina werd gelezen en die had precies één bruikbare rij. Geen
    fout, geen leeg veld — een verkeerd beeld.
    """
    stoorzender = ('<table><tr><td>1</td><td>2-9</td>'
                   '<td>Lincoln - Lincoln</td><td>170</td><td>flat</td></tr>'
                   '</table>')
    gemengd = stoorzender + ROUTE.read_text()
    assert len(cs.parse_etappes(gemengd, 2026)) == len(etappes) == 21
    # staat er niets beters op de pagina, dan telt die ene rij gewoon mee
    alleen = cs.parse_etappes(stoorzender, 2026)
    assert len(alleen) == 1 and alleen[0]["departure"] == "Lincoln"


def test_route_kandidaten_uit_de_koerspagina(cs):
    """Op echte HTML: de Vuelta-routepagina linkt naar zijn eigen subpagina's."""
    kandidaten = cs.route_kandidaten(
        ROUTE.read_text(), "https://www.cyclingstage.com/vuelta-2026-route/")
    assert kandidaten == [
        "https://www.cyclingstage.com/vuelta-2026-route/spain-route-2026/"]


def test_route_kandidaten_laten_de_rest_van_de_site_staan(cs):
    """De menubalk noemt élke koers; alleen wat onder déze koers hangt telt.

    Zonder die eis zou een koers zonder routeadres de hele navigatie als
    kandidaat krijgen — 268 links op de echte pagina.
    """
    html = ROUTE.read_text()
    for kandidaat in cs.route_kandidaten(html, "https://www.cyclingstage.com/vuelta-2026-route/"):
        assert "/vuelta-2026-route/" in kandidaat
    # een koerspagina die niet in deze HTML voorkomt levert niets op
    assert cs.route_kandidaten(html, "https://www.cyclingstage.com/tour-of-britain-2026/") == []
    assert cs.route_kandidaten("", "https://www.cyclingstage.com/x-2026/") == []
    assert cs.route_kandidaten(html, "") == []


def test_route_kandidaten_zetten_route_vooraan(cs):
    """Wat "route" heet gaat voor; de rest blijft als terugval staan.

    Synthetische HTML, en dat is hier te verantwoorden: het gaat om de
    vólgorde van de kandidaten, niet om het lezen van andermans pagina. Dat
    laatste staat hierboven op de echte Vuelta-pagina.
    """
    html = ('<a href="/tour-of-britain-2026/favourites-gb-2026/">Favourites</a>'
            '<a href="/tour-of-britain-2026/route-gb-2026/">Route</a>'
            '<a href="/tour-of-britain-2026/stage-1-gb-2026/">Stage 1</a>'
            '<a href="/tour-of-britain-2025/route-gb-2025/">2025</a>')
    assert cs.route_kandidaten(
        html, "https://www.cyclingstage.com/tour-of-britain-2026/") == [
        "https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/",
        "https://www.cyclingstage.com/tour-of-britain-2026/favourites-gb-2026/",
    ]


# ── de weg naar de uitslag ──────────────────────────────────────────


def test_uitslagadres_van_een_grote_ronde(cs):
    """De vorm die op de echte pagina is nagekeken."""
    assert cs.uitslag_url(
        "https://www.cyclingstage.com/vuelta-2026-route/stage-2-spain-2026/"
    ) == ("https://www.cyclingstage.com/vuelta-2026-results/"
          "stage-2-spain-results-2026/")


def test_uitslagadres_van_een_koers_zonder_routemap(cs):
    """Koersen buiten de grote rondes hebben geen `-route`-map.

    Tot 0.23 gaf `uitslag_url` daar niets terug en had zo'n koers dus nooit
    een uitslag — dat trof 46 van de 49 koersen in de kalender.
    """
    assert cs.uitslag_url(
        "https://www.cyclingstage.com/tour-of-britain-2026/stage-1-gb-2026/"
    ) == ("https://www.cyclingstage.com/tour-of-britain-2026-results/"
          "stage-1-gb-results-2026/")


def test_geen_uitslagadres_zonder_etappenummer(cs):
    """Een eendaagse koers heeft geen `stage-N`-pagina.

    Zijn uitslag staat op de resultatenpagina van de koers zelf; een
    afgeleid adres zou elke ronde een verzoek zijn dat niets kan opleveren.
    """
    assert cs.uitslag_url(
        "https://www.cyclingstage.com/paris-roubaix-2026/route-pr-2026/") == ""
    assert cs.uitslag_url("") == ""
    assert cs.uitslag_url("https://www.cyclingstage.com/los-2026/") == ""


def test_uitslagoverzicht_op_echte_links(cs):
    """De vórm van de link staat in de opgeslagen Vuelta-routepagina.

    De indexpagina zelf is niet opgeslagen (de proxy laat cyclingstage niet
    door), maar `/vuelta-2026-results/stage-2-spain-results-2026/` staat er
    letterlijk in — precies het soort adres dat deze parser moet vinden.
    """
    index = cs.parse_uitslag_index(ROUTE.read_text(), "vuelta", 2026)
    assert index[2] == ("https://www.cyclingstage.com/vuelta-2026-results/"
                        "stage-2-spain-results-2026/")
    # de routepagina van een ánder jaar of een andere koers telt niet mee
    assert cs.parse_uitslag_index(ROUTE.read_text(), "vuelta", 2025) == {}
    assert cs.parse_uitslag_index(ROUTE.read_text(), "giro", 2026) == {}
    assert cs.parse_uitslag_index("", "vuelta", 2026) == {}
    assert cs.parse_uitslag_index("<a href='/x/'>x</a>", "", 2026) == {}
