# cyclingstage_tour_of_britain_2026_route.html

`https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/`, opgehaald
7 september 2026.

**Dit adres was de openstaande aanname van 0.24.** Dat het bestaat kwam uit
een zoekresultaat; nu is het nagekeken en het klopt. De koerspagina linkt er
ook echt naartoe, dus `route_kandidaten` vindt hem.

Maar de pagina heeft **geen tabel**. Het is een lopend verhaal met per etappe:

    <em>Stage 1</em> – <small>182.5 kilometres, 1,393 metres of elevation gain</small><br>
    The Tour of Britain opens with a big loop north of ...

Dat is een derde vorm naast de etappetabel van een grote ronde en de
programmatabel van het WK. Wat er staat: nummer, afstand, hoogtemeters. Wat
er niet staat: de datum per etappe, start en finish, en een etappe-adres.

`parse_etappes_tekst` leest die drie velden; `_datums_verdelen` in sensor.py
vult de datums aan, maar alleen als er precies zoveel etappes zijn als
koersdagen (5 etappes, 2 t/m 6 september). Bij minder etappes dan dagen
zitten er rustdagen tussen en is niet te zeggen welke — dan blijft het leeg.
