# mortables 📊

**Tables de mortalité réglementaires françaises & fonctions actuarielles en Python.**

[![CI](https://github.com/mehdijac/mortables/actions/workflows/ci.yml/badge.svg)](https://github.com/mehdijac/mortables/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

> ⚠️ **Utilisateurs de la version 0.1.0 : mettez à jour.** Les tables embarquées dans la 0.1.0
> n'étaient pas les tables réglementaires (TGH05/TGF05 reconstituées par un modèle
> paramétrique, TH/TF 00-02 inexactes), ce qui sous-estimait fortement les engagements
> de rentes. Depuis la 0.1.1, les tables sont les fichiers Lx officiels, vérifiés par des
> tests de référence. Voir le [CHANGELOG](CHANGELOG.md).

## Pourquoi ce package ?

Chaque actuaire français a un jour copié-collé des `qx` depuis un PDF ou un fichier Excel bancal pour les mettre dans un tableur. **mortables** élimine cette friction :

- 📦 Les tables réglementaires sont **embarquées** dans le package (pas besoin de connexion internet)
- 🔢 Les fonctions actuarielles classiques sont prêtes à l'emploi (commutations, annuités, primes, provisions)
- 📈 Les graphiques standards sont disponibles en une ligne de code
- 🧪 Le tout est **testé** et **documenté**, avec des tests de référence sur les valeurs officielles

## Installation

```bash
pip install mortables
```

Avec les graphiques (nécessite matplotlib) :
```bash
pip install mortables[viz]
```

## Démarrage rapide

### Charger une table

```python
from mortables import get_table, list_tables

# Voir les tables disponibles
list_tables()
# [{'id': 'TH0002', 'name': 'TH 00-02', ...}, ...]

# Table du moment (hommes)
th = get_table("TH0002")
th.lx[60]               # → 85538.0 (valeur officielle)
th.qx_at(65)            # → 0.01719
th.life_expectancy(0)   # → 75.01 ans (espérance de vie « curtate », comme les fichiers officiels)
th.life_expectancy(65)  # → 16.40 ans

# Table du moment (femmes)
tf = get_table("TF0002")
tf.life_expectancy(0)   # → 82.49 ans

# Table générationnelle (rentes viagères)
tg = get_table("TGH05", generation=1960)
tg.life_expectancy(65)  # → 24.95 ans
```

### Calculs actuariels

```python
from mortables import get_table, life

th = get_table("TH0002")

# Annuité viagère due à 65 ans, taux technique 2%
life.annuity_due(th, age=65, rate=0.02)  # → 14.36

# Annuité temporaire 10 ans
life.annuity_due(th, age=65, rate=0.02, term=10)  # → 8.34

# Assurance vie entière
life.whole_life_insurance(th, age=40, rate=0.02)  # → 0.488

# Temporaire décès
life.term_insurance(th, age=40, rate=0.02, term=20)  # → 0.088

# Capital différé
life.pure_endowment(th, age=40, rate=0.02, term=20)  # → 0.597

# Assurance mixte
life.endowment_insurance(th, age=40, rate=0.02, term=20)  # → 0.685

# Prime pure annuelle (vie entière)
life.net_premium_whole_life(th, age=30, rate=0.02)  # → 0.0135

# Les taux négatifs sont acceptés (taux > -100 %)
life.annuity_due(th, age=65, rate=-0.005)

# Provision prospective
life.reserve_whole_life(th, age_at_issue=30, rate=0.02, duration=20)
```

### Nombres de commutation

```python
from mortables import get_table, life

th = get_table("TH0002")
ct = life.commutation(th, rate=0.02)

ct.Dx[65]  # D65
ct.Nx[65]  # N65
ct.Mx[65]  # M65
```

### Projection de cash flows

```python
from mortables import cashflows

# Portefeuille de rentiers : chaque rentier a son sexe et son année de naissance
portfolio = [
    {"age": 65, "annual_rent": 12000, "gender": "M", "birth_year": 1961},
    {"age": 72, "annual_rent":  8000, "gender": "F", "birth_year": 1954},
    {"age": 58, "annual_rent": 15000, "gender": "F", "birth_year": 1968},
]

# Projection jusqu'à extinction (years=None par défaut), taux d'actualisation 2 %.
# "gender" sélectionne automatiquement TGH05 ou TGF05 (idem TH0002 ↔ TF0002).
flows = cashflows.project(portfolio, table="TGH05", rate=0.02)
print(flows.head())
# colonnes : year, expected_payment, survivors, discount_factor, pv_payment

# Provision totale = Σ rente × ä(âge), rentes payées annuellement d'avance
cashflows.total_provision(portfolio, table="TGH05", rate=0.02)
# → 773 083 €
```

### Visualisation

```python
from mortables import viz

# Courbes de mortalité (qx en échelle log)
fig = viz.plot_qx(["TH0002", "TF0002"], log_scale=True)
fig.savefig("qx.png")

# Courbes de survie
fig = viz.plot_survival(["TH0002", "TF0002"])

# Espérance de vie par âge
fig = viz.plot_life_expectancy(["TH0002", "TF0002"])

# Comparaison de deux tables (ratio de qx)
fig = viz.plot_comparison("TH0002", "TF0002", age_range=(30, 90))

# Effet de la génération sur la mortalité
fig = viz.plot_generations("TGH05", generations=[1930, 1950, 1970, 1990])

# Graphique des flux projetés
fig = viz.plot_cashflows(flows)
```

### Export pandas

```python
th = get_table("TH0002")
df = th.to_dataframe()
df.to_excel("TH0002.xlsx", index=False)
```

## Tables disponibles

| Identifiant | Nom | Type | Genre | Réglementation | Usage |
|---|---|---|---|---|---|
| `TH0002` | TH 00-02 | Moment | Hommes | Arrêté 20/12/2005 | Décès, capital |
| `TF0002` | TF 00-02 | Moment | Femmes | Arrêté 20/12/2005 | Décès, capital |
| `TGH05` | TGH 05 | Générationnelle | Hommes | Arrêté 01/08/2006 | Rentes viagères |
| `TGF05` | TGF 05 | Générationnelle | Femmes | Arrêté 01/08/2006 | Rentes viagères |

> **Note** : Les tables TGH05/TGF05 sont générationnelles. Il faut préciser l'année de naissance :
> `get_table("TGH05", generation=1960)`. Générations disponibles : 1900 à 2005.
> Conformément aux tables officielles, chaque génération n'est définie qu'à partir de l'âge
> atteint en 1996 (radix 100 000 à cet âge, par ex. 46 ans pour la génération 1950) :
> `tg.min_age` donne cet âge, et un calcul à un âge antérieur lève une erreur.

### Sources des données

Les tables sont reprises **à l'identique** (colonne Lx, âges 0 à 120) des fichiers diffusés sur
[ressources-actuarielles.net](http://www.ressources-actuarielles.net/EXT/ISFA/fp-isfa.nsf/34a14c286dfb0903c1256ffd00502d73/762c8e624ee98a5ec12577c100566d11) (ISFA) :
`TH00-02_D.xls`, `TF00-02_D.xls`, `TGHF05.xls`. Les `qx` sont déduits des `lx`
(`qx = 1 − l(x+1)/l(x)`, table fermée à 120 ans). Le fichier `tests/test_reference.py`
vérifie des valeurs officielles et l'empreinte SHA-256 des fichiers de données.
Seuls les textes publiés au Journal officiel font foi.

## Fonctions disponibles

### Module `life`

| Fonction | Description | Notation |
|---|---|---|
| `commutation()` | Nombres de commutation | Dx, Nx, Sx, Cx, Mx, Rx |
| `life_expectancy()` | Espérance de vie résiduelle | ex |
| `annuity_due()` | Annuité viagère due | äx, äx:n⌉ |
| `annuity_immediate()` | Annuité viagère immédiate | ax |
| `whole_life_insurance()` | Assurance vie entière | Ax |
| `term_insurance()` | Temporaire décès | A¹x:n⌉ |
| `pure_endowment()` | Capital différé | ₙEx |
| `endowment_insurance()` | Assurance mixte | Ax:n⌉ |
| `net_premium_whole_life()` | Prime pure vie entière | Px |
| `net_premium_term()` | Prime pure temporaire | P¹x:n⌉ |
| `net_premium_endowment()` | Prime pure mixte | Px:n⌉ |
| `reserve_whole_life()` | Provision prospective | tVx |

### Module `cashflows`

| Fonction | Description |
|---|---|
| `project()` | Projection des flux pour un portefeuille de rentiers |
| `total_provision()` | Provision totale (BEL) |

### Module `viz`

| Fonction | Description |
|---|---|
| `plot_qx()` | Courbe de mortalité qx |
| `plot_survival()` | Courbe de survie lx |
| `plot_life_expectancy()` | Espérance de vie par âge |
| `plot_comparison()` | Ratio qx entre deux tables |
| `plot_generations()` | Comparaison par génération |
| `plot_cashflows()` | Graphique des flux projetés |

## Développement

```bash
git clone https://github.com/mehdijac/mortables.git
cd mortables
uv sync              # crée .venv et installe le package + les outils de dev (uv.lock)
uv run pytest -v
uv run ruff check .
uv build             # construit sdist et wheel dans dist/
```

Le projet est géré avec [uv](https://docs.astral.sh/uv/).

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour contribuer.

## Roadmap

- [ ] **Phase 2** : Analyse d'expérience (ratios A/E), lissage Whittaker-Henderson, graduation de Makeham
- [ ] **Phase 3** : Modèles de projection (Lee-Carter, CBD), intervalles de confiance
- [ ] Tables internationales (HMD)
- [ ] Table non genrée pour la retraite supplémentaire collective (loi Industrie verte, arrêté de novembre 2024)
- [ ] Tables INSEE annuelles

## Licence

[MIT](LICENSE)
