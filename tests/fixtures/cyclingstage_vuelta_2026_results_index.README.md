# cyclingstage_vuelta_2026_results_index.html

`https://www.cyclingstage.com/vuelta-2026-results/`, opgehaald 7 september
2026.

De resultaten-overzichtspagina: de terugval die in 0.24 is toegevoegd en in
0.26.1 pas echt ging werken, en die tot nu toe alleen was beproefd op links
die toevallig in de routepagina stonden.

`parse_uitslag_index` vindt hier 15 etappes (1 t/m 15, de Vuelta was op dat
moment tot etappe 15 gereden), met exact de adressen die `uitslag_url` ook
afleidt:

    https://www.cyclingstage.com/vuelta-2026-results/stage-1-spain-results-2026/

Dat bevestigt twee dingen tegelijk: de afleiding klopt voor een grote ronde,
én de terugval leest dezelfde adressen als die afleiding zou opleveren.
