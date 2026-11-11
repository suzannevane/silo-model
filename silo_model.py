"""
Silo-model: wij-zij-denken tussen engineers en managers
=======================================================

Agent-based model (Mesa 3) van hoe vertrouwen, groepsidentificatie en silo's
ontstaan uit dagelijkse interacties in een projectorganisatie.

Elke tick (= één werkdag) start iedere medewerker één gesprek. Gesprekken met
de andere groep slagen of mislukken; dat verandert vertrouwen, identificatie
en werktaal. Gesprekken binnen de eigen groep verspreiden vertrouwen (roddel).

Mechanismen en hun basis in de literatuur:
  1. Contact en vertrouwen ........ Pettigrew & Tropp (2006), Barlow e.a. (2012)
  2. Identiteit en homofilie ...... Ashforth & Mael (1989), McPherson e.a. (2001)
  3. Status en werktaal ........... Kende e.a. (2018), Nooteboom e.a. (2007)
     - werktaalverschil verlaagt de kans dat een gesprek slaagt
     - statusverschil dempt hoeveel vertrouwen een goed gesprek oplevert
  4. Roddel in de eigen groep ..... Flache e.a. (2017)
  5. Interventies ................. gedeeld doel, plat organiseren, training,
                                    brugfiguren, meer projectcontact
Silovorming meten we met de E-I index (Krackhardt & Stern, 1988).
"""

import numpy as np
import pandas as pd
import mesa

ENGINEER = "engineer"
MANAGER = "manager"


def clip(x, lo=0.0, hi=1.0):
    """Houd een waarde tussen lo en hi."""
    return max(lo, min(hi, x))


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------
class Person(mesa.Agent):
    """Een medewerker: engineer of manager (eventueel een brugfiguur)."""

    def __init__(self, model, group, index, team, is_bridge=False):
        super().__init__(model)
        self.group = group          # ENGINEER of MANAGER
        self.index = index          # rij/kolom in de netwerkmatrix
        self.team = team            # projectteam
        self.is_bridge = is_bridge  # brugfiguur (alleen bij interventie)

        # Vertrouwen in de ANDERE groep (0 = geen, 1 = volledig)
        self.trust = clip(self.rng.normal(model.trust_init, 0.1))

        if is_bridge:
            # Brugfiguur: spreekt beide talen en voelt zich weinig 'kamp'
            self.identification = 0.1
            self.jargon = 0.5
            self.language = 0.5
        else:
            # Hoe sterk iemand zich engineer/manager voelt (0-1)
            self.identification = clip(self.rng.normal(model.identification_init, 0.1))
            # Werktaal: 0 = puur technisch, 1 = puur zakelijk.
            # 'jargon' is de typische werktaal van de eigen beroepsgroep.
            half_gap = model.language_gap / 2
            self.jargon = 0.5 - half_gap if group == ENGINEER else 0.5 + half_gap
            self.language = clip(self.rng.normal(self.jargon, 0.05))

    @property
    def other_group(self):
        return MANAGER if self.group == ENGINEER else ENGINEER

    # -- elke tick ----------------------------------------------------------
    def step(self):
        partner = self.choose_partner()
        if partner is not None:
            self.model.interact(self, partner)

    def choose_partner(self):
        """Kies een gesprekspartner (regel 1: projectwerk, regel 2: homofilie)."""
        m = self.model

        # Projectwerk dwingt soms contact af met de andere groep in je team
        if self.random.random() < m.forced_contact:
            colleagues = m.team_members[self.team][self.other_group]
            if colleagues:
                return self.random.choice(colleagues)

        # Vrije keuze: zonder homofilie kies je willekeurig. Hoe sterker je
        # identificatie, hoe vaker je iemand uit je eigen groep kiest.
        own = [p for p in m.members[self.group] if p is not self]
        other = m.members[self.other_group]
        base_own = len(own) / (len(own) + len(other))
        p_own = base_own + (1 - base_own) * m.homophily * self.identification
        pool = own if self.random.random() < p_own else other
        return self.random.choice(pool) if pool else None

    def update_after_contact(self, other_language, success):
        """Werk vertrouwen, identificatie en werktaal bij na contact met de andere groep."""
        m = self.model
        # Brugfiguren worden minder snel 'kampgenoot'
        id_rate = m.identification_rate * (0.25 if self.is_bridge else 1.0)

        if success:
            # Hoe groter het statusverschil, hoe minder een goed gesprek
            # het vertrouwen opbouwt (Kende e.a., 2018)
            self.trust += m.trust_rate * (1 - m.status_gap) * (1 - self.trust)
            self.identification -= id_rate * self.identification
            self.language += m.language_learning * (other_language - self.language)
        else:
            # Negatief contact weegt zwaarder (Barlow e.a., 2012)
            self.trust -= m.trust_rate * m.negativity_bias * self.trust
            self.identification += id_rate * (1 - self.identification)

        self.trust = clip(self.trust)
        self.identification = clip(self.identification)


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------
class SiloModel(mesa.Model):
    """Projectorganisatie met engineers en managers."""

    def __init__(
        self,
        # --- organisatie
        n_engineers=45,
        n_managers=15,
        n_teams=4,
        # --- startwaarden
        trust_init=0.5,             # gemiddeld vertrouwen in de andere groep
        identification_init=0.5,    # gemiddelde groepsidentificatie
        language_gap=0.5,           # afstand in werktaal tussen de groepen
        # --- gedrag
        base_success=0.7,           # basiskans dat contact met de andere groep slaagt
        language_weight=0.3,        # hoeveel werktaalverschil de slaagkans verlaagt
        status_gap=0.3,             # hoeveel statusverschil de opbouw van vertrouwen dempt
        trust_weight=0.4,           # hoeveel wederzijds vertrouwen de slaagkans verhoogt
        trust_rate=0.05,            # leersnelheid van vertrouwen
        negativity_bias=2.0,        # slechte ervaring telt zoveel keer zwaarder
        identification_rate=0.03,   # hoe snel identificatie reageert op contact
        ingroup_reinforcement=0.005, # identiteit groeit licht door contact met groepsgenoten
        homophily=1.0,              # hoe sterk identificatie de partnerkeuze stuurt
        language_learning=0.02,     # hoe snel werktalen naar elkaar toe schuiven na succes
        jargon_pull=0.02,           # hoe sterk gesprekken binnen de groep je terugtrekken naar vakjargon
        gossip=0.05,                # hoeveel vertrouwen je overneemt van groepsgenoten
        forced_contact=0.2,         # aandeel gesprekken dat projectwerk afdwingt
        tie_decay=0.02,             # hoe snel netwerkbanden verzwakken per tick
        # --- interventies
        shared_goal=0.0,            # extra slaagkans door een gedeeld projectdoel
        n_bridges=0,                # aantal engineers dat brugfiguur wordt
        seed=None,
    ):
        super().__init__(rng=seed)

        # Bewaar alle parameters als attributen (self.base_success, ...)
        params = dict(locals())
        for name in ("self", "seed", "__class__"):
            params.pop(name, None)
        self.params = params
        for name, value in params.items():
            setattr(self, name, value)

        # --- maak de mensen aan en verdeel ze over teams
        # De eerste n_bridges engineers worden brugfiguur (verdeeld over de teams)
        people = []
        for i in range(n_engineers):
            people.append((ENGINEER, i % n_teams, i < n_bridges))
        for i in range(n_managers):
            people.append((MANAGER, i % n_teams, False))
        self.people = [
            Person(self, group, index, team, is_bridge)
            for index, (group, team, is_bridge) in enumerate(people)
        ]
        self.members = {
            ENGINEER: [p for p in self.people if p.group == ENGINEER],
            MANAGER: [p for p in self.people if p.group == MANAGER],
        }
        self.team_members = [
            {g: [p for p in self.members[g] if p.team == t] for g in (ENGINEER, MANAGER)}
            for t in range(n_teams)
        ]

        # --- netwerk: wie praat met wie (gewogen, symmetrisch)
        n = len(self.people)
        self.ties = np.zeros((n, n))
        groups = np.array([p.group for p in self.people])
        self.same_group = groups[:, None] == groups[None, :]
        np.fill_diagonal(self.same_group, False)
        self.ei_random = self._ei_under_random_mixing()

        # --- tellers per tick
        self.contacts = 0
        self.cross_contacts = 0
        self.cross_successes = 0

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "E-I index": lambda m: m.ei_index(),
                "Vertrouwen engineers": lambda m: m.mean("trust", ENGINEER),
                "Vertrouwen managers": lambda m: m.mean("trust", MANAGER),
                "Identificatie engineers": lambda m: m.mean("identification", ENGINEER),
                "Identificatie managers": lambda m: m.mean("identification", MANAGER),
                "Werktaalverschil": lambda m: m.mean("language", MANAGER) - m.mean("language", ENGINEER),
                "Aandeel contact tussen groepen": lambda m: m.cross_contacts / max(m.contacts, 1),
                "Slaagkans contact tussen groepen": lambda m: (
                    m.cross_successes / m.cross_contacts if m.cross_contacts else np.nan
                ),
            }
        )

    # -- interactie ----------------------------------------------------------
    def success_probability(self, a, b):
        """Kans dat een gesprek tussen een engineer en een manager goed gaat."""
        language_distance = abs(a.language - b.language)
        mean_trust = (a.trust + b.trust) / 2
        p = (
            self.base_success
            + self.shared_goal
            - self.language_weight * language_distance
            + self.trust_weight * (mean_trust - 0.5)
        )
        return clip(p, 0.05, 0.95)

    def interact(self, a, b):
        """Voer één gesprek uit tussen a en b."""
        self.ties[a.index, b.index] += 1
        self.ties[b.index, a.index] += 1
        self.contacts += 1

        if a.group == b.group:
            # Roddel: vertrouwen schuift naar elkaar toe; identiteit wordt bevestigd
            mean_trust = (a.trust + b.trust) / 2
            for p in (a, b):
                p.trust += self.gossip * (mean_trust - p.trust)
                bridge_factor = 0.25 if p.is_bridge else 1.0
                p.identification += (
                    self.ingroup_reinforcement * bridge_factor * (1 - p.identification)
                )
                # Praten met groepsgenoten versterkt het eigen vakjargon
                p.language += self.jargon_pull * (p.jargon - p.language)
            return

        # Contact tussen de groepen
        self.cross_contacts += 1
        success = self.random.random() < self.success_probability(a, b)
        self.cross_successes += success
        language_a, language_b = a.language, b.language  # oude waarden bewaren
        a.update_after_contact(language_b, success)
        b.update_after_contact(language_a, success)

    # -- metingen ------------------------------------------------------------
    def mean(self, attribute, group):
        return float(np.mean([getattr(p, attribute) for p in self.members[group]]))

    def ei_index(self):
        """E-I index: (extern - intern) / (extern + intern). -1 = volledig silo."""
        internal = self.ties[self.same_group].sum()
        external = self.ties[~self.same_group].sum()  # diagonaal is altijd 0
        total = internal + external
        return (external - internal) / total if total else np.nan

    def _ei_under_random_mixing(self):
        """E-I index die je verwacht als iedereen willekeurig een partner kiest."""
        n = len(self.people)
        n_eng = len(self.members[ENGINEER])
        n_man = len(self.members[MANAGER])
        share_cross = (n_eng * n_man / (n - 1) + n_man * n_eng / (n - 1)) / n
        return 2 * share_cross - 1

    # -- tijdstap ------------------------------------------------------------
    def step(self):
        self.contacts = self.cross_contacts = self.cross_successes = 0
        self.agents.shuffle_do("step")
        self.ties *= 1 - self.tie_decay
        self.datacollector.collect(self)


# --------------------------------------------------------------------------
# Hulpfuncties om het model te draaien
# --------------------------------------------------------------------------
def run_model(steps=250, seed=None, **params):
    """Draai één run en geef (tijdreeks als DataFrame, model) terug."""
    model = SiloModel(seed=seed, **params)
    for _ in range(steps):
        model.step()
    data = model.datacollector.get_model_vars_dataframe()
    data.index = pd.RangeIndex(1, len(data) + 1, name="tick")
    return data, model


def run_many(runs=20, steps=250, first_seed=0, **params):
    """Draai meerdere runs met dezelfde parameters (verschillende seeds)."""
    frames = []
    for r in range(runs):
        data, _ = run_model(steps=steps, seed=first_seed + r, **params)
        frames.append(data.assign(run=r))
    return pd.concat(frames).reset_index()


def final_values(data, last=25):
    """Gemiddelde over de laatste `last` ticks per run."""
    cutoff = data["tick"].max() - last
    return data[data["tick"] > cutoff].groupby("run").mean(numeric_only=True)


if __name__ == "__main__":
    # Snelle test: één run met standaardwaarden
    data, model = run_model(steps=250, seed=1)
    print(data.iloc[[0, 49, 99, 249]].round(3).T)
    print(f"\nE-I index bij willekeurige partnerkeuze: {model.ei_random:.3f}")
