# mortables 📊

**Tables de mortalité réglementaires françaises & fonctions actuarielles en Python.**

[![CI](https://github.com/mehdijac/mortables/actions/workflows/ci.yml/badge.svg)](https://github.com/mehdijac/mortables/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Pourquoi ce package ?

Chaque actuaire français a un jour copié-collé des `qx` depuis un PDF ou un fichier Excel bancal pour les mettre dans un tableur. **mortables** élimine cette friction :

- 📦 Les tables réglementaires sont **embarquées** dans le package (pas besoin de connexion internet)
- 🔢 Les fonctions actuarielles classiques sont prêtes à l'emploi (commutations, annuités, primes, provisions)
- 📈 Les graphiques standards sont disponibles en une ligne de code
- 🧪 Le tout est **testé** et **documenté**

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
th.qx_at(65)       # → 0.0230
th.life_expectancy(0)   # → ~75.8 ans
th.life_expectancy(65)  # → ~16.5 ans

# Table du moment (femmes)
tf = get_table("TF0002")
tf.life_expectancy(0)   # → ~83.0 ans

# Table générationnelle (rentes viagères)
tg = get_table("TGH05", generation=1960)
tg.life_expectancy(65)  # → ~22 ans
```

### Calculs actuariels

```python
from mortables import get_table, life

th = get_table("TH0002")

# Annuité viagère due à 65 ans, taux technique 2%
life.annuity_due(th, age=65, rate=0.02)  # → ~14.5

# Annuité temporaire 10 ans
life.annuity_due(th, age=65, rate=0.02, term=10)  # → ~9.1

# Assurance vie entière
life.whole_life_insurance(th, age=40, rate=0.02)  # → ~0.43

# Temporaire décès
life.term_insurance(th, age=40, rate=0.02, term=20)  # → ~0.05

# Capital différé
life.pure_endowment(th, age=40, rate=0.02, term=20)  # → ~0.59

# Assurance mixte
life.endowment_insurance(th, age=40, rate=0.02, term=20)  # → ~0.64

# Prime pure annuelle (vie entière)
life.net_premium_whole_life(th, age=30, rate=0.02)  # → ~0.007

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

# Portefeuille de rentiers
portfolio = [
    {"age": 65, "annual_rent": 12000},
    {"age": 72, "annual_rent":  8000},
    {"age": 58, "annual_rent": 15000},
]

# Projection sur 40 ans avec un taux d'actualisation de 2%
flows = cashflows.project(portfolio, table="TF0002", years=40, rate=0.02)
print(flows.head())
#    year  expected_payment  survivors  pv_payment
# 0     0          35000.00     3.0000    35000.00
# 1     1          34720.15     2.9812    34038.38
# ...

# Provision totale (Best Estimate Liability)
cashflows.total_provision(portfolio, table="TF0002", years=60, rate=0.02)
# → ~650 000 €
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
git clone https://github.com/yourname/mortables.git
cd mortables
pip install -e ".[dev]"
pytest -v
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour contribuer.

## Roadmap

- [ ] **Phase 2** : Analyse d'expérience (ratios A/E), lissage Whittaker-Henderson, graduation de Makeham
- [ ] **Phase 3** : Modèles de projection (Lee-Carter, CBD), intervalles de confiance
- [ ] Tables internationales (HMD)
- [ ] Table TGHF05 (non genrée, loi Industrie Verte 2024)
- [ ] Tables INSEE annuelles

## Licence

[MIT](LICENSE)
