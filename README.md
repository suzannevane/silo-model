# Silo-model: wij-zij-denken tussen engineers en managers

Agent-based model (Python, [Mesa](https://mesa.readthedocs.io)) van hoe vertrouwen, groepsidentificatie en silo's ontstaan uit dagelijkse gesprekken in een projectorganisatie, en welke interventies dat tegengaan.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/suzanneve/silo-model/blob/main/silo_model_colab.ipynb)


## Wat zit erin

| Bestand | Inhoud |
|---|---|
| `silo_model.py` | Het model: agenten, gedragsregels en metingen |
| `run_experiments.py` | Vier experimenten die alle grafieken en CSV's in `results/` maken |
| `silo_model_colab.ipynb` | Notebook om het model in je browser te draaien en zelf te experimenteren |
| `results/` | Grafieken (PNG) en ruwe uitkomsten (CSV) |
| `requirements.txt` | Benodigde Python-pakketten |

## Starten

**In de browser (aanbevolen):** klik op de *Open in Colab*-knop en kies *Runtime → Run all*. Je hoeft niets te installeren.

**Op je eigen computer** (Python 3.12 of nieuwer):

```bash
pip install -r requirements.txt
python silo_model.py                 # één testrun, print een tabel
python run_experiments.py --quick    # snelle versie van alle experimenten
python run_experiments.py            # volledige versie (ongeveer een minuut)
```

## Hoe het model werkt

Een projectorganisatie van 45 engineers en 15 managers in 4 projectteams. Elke tick is één werkdag; elke medewerker voert dan één gesprek.

**Eigenschappen per medewerker**

| Eigenschap | Betekenis | Theorie |
|---|---|---|
| `trust` | vertrouwen in de andere groep (0–1) | intergroepscontact |
| `identification` | hoe sterk iemand zich engineer of manager voelt (0–1) | sociale identiteit |
| `language` | werktaal, van technisch (0) tot zakelijk (1) | cognitieve afstand |
| statusverschil | managers hebben meer beslismacht (`status_gap`, geldt voor de hele organisatie) | status en hiërarchie |

**Gedragsregels per gesprek**

1. **Partner kiezen.** Een deel van de gesprekken dwingt het projectwerk af met de andere groep in je team. De rest kies je zelf: hoe sterker je identificatie, hoe vaker je een groepsgenoot kiest (homofilie).
2. **Gesprek met de andere groep.** Slaagt met een kans die daalt met werktaalverschil en stijgt met vertrouwen en een gedeeld doel.
    - Geslaagd: vertrouwen stijgt (minder bij groot statusverschil), identificatie daalt, werktalen schuiven naar elkaar toe.
    - Mislukt: vertrouwen daalt, twee keer zo hard (negativiteitsbias); identificatie stijgt.
3. **Gesprek binnen de eigen groep.** Vertrouwen schuift naar dat van de ander (roddel), identiteit wordt licht bevestigd en je werktaal schuift terug naar het vakjargon van je groep.

**Metingen per tick:** de E-I index van het informele netwerk (Krackhardt & Stern, 1988), gemiddeld vertrouwen en identificatie per groep, werktaalverschil en het slagingspercentage van gesprekken tussen de groepen.

## Eerste resultaten

> Let op: de parameters zijn nog geschat, niet gemeten. Lees de resultaten als verkenning van het mechanisme, niet als voorspelling voor een echt bedrijf.

**1. Zonder ingrijpen ontstaat een silo.** Vertrouwen daalt in een jaar van 0,50 naar 0,29. De E-I index zakt naar −0,35, onder de −0,24 die je bij willekeurig contact zou verwachten. Engineers gaan zich sterker met hun eigen groep identificeren (0,50 → 0,65); managers niet, omdat zij als kleine groep vooral met engineers praten.

![Basisrun](results/01_basisrun.png)

**2. Het netwerk laat het zien.** In de basis vormen managers een eigen kern. Met alle interventies samen zitten ze verspreid over de projectteams.

![Netwerk](results/02_netwerk.png)

**3. Losse interventies helpen weinig, samen veel.** Plat organiseren en een gedeeld projectdoel geven de grootste losse winst (vertrouwen ±0,38). Negen brugfiguren alleen doen bijna niets. Alle interventies samen brengen het vertrouwen naar 0,60. *Meer projectcontact* verhoogt de E-I index vooral per definitie, omdat contact wordt afgedwongen; kijk bij die interventie naar vertrouwen.

![Interventies](results/03_interventies.png)

**4. Er is een kantelpunt.** Bij de standaard-negativiteitsbias gaat vertrouwen van 0,29 naar 0,52 als de basiskans op een goed gesprek stijgt van 0,70 naar 0,80, en naar 0,80 bij 0,85. Kleine verbeteringen in de kwaliteit van contact hebben dus groot effect.

![Kantelpunt](results/04_kantelpunt.png)

## Belangrijkste parameters

| Parameter | Standaard | Betekenis |
|---|---|---|
| `base_success` | 0.7 | basiskans dat een gesprek met de andere groep goed gaat |
| `language_weight` | 0.3 | hoeveel werktaalverschil die kans verlaagt |
| `language_gap` | 0.5 | startafstand in werktaal tussen de groepen |
| `trust_weight` | 0.4 | hoeveel wederzijds vertrouwen die kans verhoogt |
| `negativity_bias` | 2.0 | hoeveel zwaarder een slechte ervaring telt |
| `status_gap` | 0.3 | hoeveel statusverschil de opbouw van vertrouwen dempt |
| `homophily` | 1.0 | hoe sterk identificatie de partnerkeuze stuurt |
| `gossip` | 0.05 | hoeveel vertrouwen je overneemt van groepsgenoten |
| `forced_contact` | 0.2 | aandeel gesprekken dat projectwerk afdwingt |
| `shared_goal` | 0.0 | extra slaagkans door een gedeeld projectdoel (interventie) |
| `n_bridges` | 0 | aantal engineers dat brugfiguur wordt (interventie) |

Alle parameters staan met uitleg in `SiloModel.__init__` in `silo_model.py`.

## Volgende stappen

- [ ] Rotatie toevoegen: elke 50 ticks mensen van projectteam laten wisselen
- [ ] Testen of meer contact averechts werkt als gesprekken vaak mislukken (Flache & Macy, 2011)
- [ ] Interviews en enquête: startwaarden en parameters onderbouwen
- [ ] Validatie: E-I index uit het model vergelijken met een echt netwerk
- [ ] Gevoeligheidsanalyse en scenario's met de [EMA Workbench](https://pypi.org/project/ema_workbench/)
- [ ] Modelbeschrijving volgens het ODD-protocol

## Literatuur

Ashforth & Mael (1989); Barlow e.a. (2012); Flache & Macy (2011); Flache e.a. (2017); Kende e.a. (2018); Krackhardt & Stern (1988); McPherson e.a. (2001); Nooteboom e.a. (2007); Pettigrew & Tropp (2006). Volledige lijst en uitleg in het bijbehorende literatuuroverzicht.
