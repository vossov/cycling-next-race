"""Meet hoe zwaar de attributen van de sensor wegen, per post.

    python3 tools/meet_attributen.py

De recorder van Home Assistant weigert attributen boven
`MAX_STATE_ATTRS_BYTES` (16384 bytes) en logt daar bij élke update een
waarschuwing over. De sensor en de kaart blijven dan gewoon werken — de
attributen gaan over de websocket — maar er is geen historie meer.

**Waarom dit script bestaat.** In CLAUDE.md stond jarenlang een schatting
("ruwweg 4 kB per koersblok, zo'n 28 kB in totaal"). Die was te laag: de
werkelijke standaardopstelling weegt 33 kB. Een schatting die niemand
narekent gaat schuiven; dit script is na te rekenen.

**Wat het níét is.** Het draait de coordinator niet — dat zou netwerk
vereisen. Het bouwt een attributenset met dezelfde vórm en realistische
inhoud: rijen zoals cyclingstage ze nu levert (rank, rider, country, time,
zonder team of dagwinst), een hoogteprofiel van 200 punten voor de getoonde
etappe en 60 per komende dag. Wijzigt de vorm van de attributen, dan hoort
dit bestand mee te veranderen.
"""
import json

MAX = 16384

def rij(i, tijd=True):
    r = {"rank": i, "rider": "Jonas Vingegaard Hansen", "country": "den"}
    r["time"] = "4:47:47" if i == 1 else ("s.t." if i < 4 else f"+ 0:{i:02d}")
    return r

def uitslag(n): return [rij(i) for i in range(1, n + 1)]
def profiel(n): return [[round(i * 0.9, 1), 400 + (i * 37) % 1600] for i in range(n)]

def etappe(punten=60, sprint=False):
    e = {"date": "2026-09-08", "eyebrow": "Etappe 16 · Vuelta a España",
         "label": "di 8 sep", "departure": "Poio", "arrival": "Mos. Castro de Herville",
         "distance_km": 167.9, "stage_type": "mountain", "profile_score": 122,
         "vertical_m": 3100, "race_key": "vuelta", "level": "m",
         "start_time": "13:05", "finish_est": "17:28",
         "elevation": profiel(punten),
         "climbs": [{"name": "Alto de Prado", "category": "", "km_to_finish": 24.1,
                     "top_m": 780, "length_km": 6.2, "steepness_pct": 5.4}] * 3}
    if sprint:
        e["sprints"] = [{"km": 88.0, "name": "Ribadumia", "time": "15:12"}]
    return e

def koersblok(key, primary=False):
    return {"key": key, "label": "Vuelta a España", "race_name": "Vuelta a España",
            "women": False, "level": "m", "jersey": "#e2231a", "primary": primary,
            "days_until": 0, "last_stage_label": "Etappe 15 · Vuelta a España",
            "last_result": uitslag(10), "gc_top": uitslag(10),
            "points_top": uitslag(10), "kom_top": uitslag(10), "youth_top": uitslag(10),
            "points_leader": "Mads Pedersen", "kom_leader": "Jay Vine",
            "youth_leader": "Juan Ayuso",
            "channels": ["Eurosport 1 14:00", "NPO 1 15:30"],
            "channels_detail": [{"name": "Eurosport 1", "time": "14:00"},
                                {"name": "NPO 1", "time": "15:30"}],
            "startlist_top": [], "startlist_riders": 0, "startlist_teams": 0}

def past_rij():
    return {"date": "2026-09-04", "race_key": "vuelta", "level": "m",
            "departure": "A Veiga", "arrival": "Monforte de Lemos",
            "distance_km": 143.2, "eyebrow": "Etappe 13 · Vuelta a España",
            "results": uitslag(5)}

def bouw(upcoming_n, upcoming_punten, max_other, past_n):
    a = {
        "show_state": "Vandaag", "eyebrow": "Etappe 15 · Vuelta a España",
        "stage_label": "A Veiga → Monforte de Lemos", "departure": "A Veiga",
        "arrival": "Monforte de Lemos", "distance_km": 143.2, "vertical_m": 2953,
        "profile_score": 143, "stage_type": "mountain", "startlist_quality": None,
        "watchability": 4, "start_time": "13:05",
        "climbs": [{"name": "Alto de San Antoniño", "category": "", "km_to_finish": 31.0,
                    "top_m": 640, "length_km": 5.1, "steepness_pct": 6.1}] * 5,
        "elevation": profiel(200),
        "upcoming": [etappe(upcoming_punten, sprint=(i == 0))
                     for i in range(upcoming_n)],
        "names_diag": [], "levels_diag": {"Mannen": 38, "Vrouwen": 11},
        "last_result": uitslag(10), "past": [past_rij() for _ in range(past_n)],
        "gc_top": uitslag(10), "points_leader": "Mads Pedersen",
        "kom_leader": "Jay Vine", "points_top": uitslag(10), "kom_top": uitslag(10),
        "youth_leader": "Juan Ayuso", "youth_top": uitslag(10),
        "last_stage_label": "Etappe 14 · Vuelta a España",
        "startlist_top": [], "startlist_riders": 0, "startlist_teams": 0,
        "race_name": "Vuelta a España", "type": "Etappekoers",
        "date": "22 aug – 13 sep", "countdown": "🟢 Bezig — dag 15/23",
        "stage_today": "A Veiga → Monforte de Lemos", "terrain": "Bergrit",
        "stars": "⭐⭐⭐", "is_live": True, "today_or_tomorrow": True,
        "days_until": 0, "women": False,
        "gpx_diag": ["vuelta/2026/stage-15-parcours.gpx"],
        "gpx_used": "vuelta/2026/stage-15-parcours.gpx",
        "times_diag": ["vuelta/2026/stage-15-times.htm"],
        "elevation_source": "gpx",
        "sprints": [{"km": 96.4, "name": "Chantada", "time": "15:24"}],
        # het primaire blok draagt geen uitslagen: die staan al in de
        # gewone attributen (zie _races_block)
        "races": [{"key": "vuelta", "label": "Vuelta a España",
                   "race_name": "Vuelta a España", "women": False, "level": "m",
                   "jersey": "#e2231a", "primary": True}]
                 + [koersblok(f"koers{i}") for i in range(max_other)],
        # backward-compat: herhaalt letterlijk het eerste andere koersblok
        "other_label": "Etappe 5 · Tour of Britain", "other_result": uitslag(10),
        "other_gc": uitslag(5),
        "finish_est": "17:28",
        "channels": ["Eurosport 1 14:00", "NPO 1 15:30"],
        "channels_detail": [{"name": "Eurosport 1", "time": "14:00"},
                            {"name": "NPO 1", "time": "15:30"}],
        "live_km_to_go": None, "live_avg_speed": None, "live_status": "",
        "live_url": "", "highlights_url": "https://www.youtube.com/results?search_query=x",
    }
    return a

def omvang(o): return len(json.dumps(o, ensure_ascii=False, separators=(",", ":")))

def rapport(naam, a):
    tot = omvang(a)
    print(f"\n{naam}: {tot} bytes  ({'PAST' if tot <= MAX else 'te groot, +%d' % (tot-MAX)})")
    posten = sorted(((omvang(v), k) for k, v in a.items()), reverse=True)[:8]
    for n, k in posten:
        print(f"   {k:<16} {n:>6}")

# zoals de standaardinstellingen nu staan
rapport("standaard (upcoming 10x60, max_other 2, past 3)",
        bouw(10, 60, 2, 3))
rapport("past_n op 21", bouw(10, 60, 2, 21))
rapport("upcoming 6 etappes", bouw(6, 60, 2, 3))
rapport("upcoming zonder profieltjes", {**bouw(10, 0, 2, 3)})
rapport("max_other 1", bouw(10, 60, 1, 3))
rapport("upcoming 6 + max_other 1", bouw(6, 60, 1, 3))


# ── wat is er nodig om écht onder 16 kB te komen ─────────────────────
def krap(a, gc_n=None, result_n=None):
    """Kortere klassementen in de pop-upblokken en op de tegel."""
    import copy
    a = copy.deepcopy(a)
    for k in ("gc_top", "points_top", "kom_top", "youth_top"):
        if gc_n is not None:
            a[k] = a[k][:gc_n]
    if result_n is not None:
        a["last_result"] = a["last_result"][:result_n]
    for blok in a["races"]:
        if blok.get("primary"):
            continue
        for k in ("gc_top", "points_top", "kom_top", "youth_top"):
            if gc_n is not None:
                blok[k] = blok[k][:gc_n]
        if result_n is not None:
            blok["last_result"] = blok["last_result"][:result_n]
    return a

def zonder_legacy(a):
    a = dict(a)
    a["other_label"], a["other_result"], a["other_gc"] = "", [], []
    return a

rapport("alle knoppen zuinig (upcoming 4x45, max_other 1, past 2, 5 renners)",
        krap(bouw(4, 45, 1, 2), gc_n=5, result_n=5))
rapport("  + zonder de other_*-herhaling",
        zonder_legacy(krap(bouw(4, 45, 1, 2), gc_n=5, result_n=5)))
rapport("  + zonder profieltjes in Komende dagen",
        zonder_legacy(krap(bouw(4, 0, 1, 2), gc_n=5, result_n=5)))
rapport("  + max_other 0 (geen tweede koers in de pop-up)",
        zonder_legacy(krap(bouw(4, 0, 0, 2), gc_n=5, result_n=5)))

