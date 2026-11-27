# mortables

**Les tables de mortalité réglementaires françaises en Python. Exactes. En une ligne.**

[![CI](https://github.com/mehdijac/mortables/actions/workflows/ci.yml/badge.svg)](https://github.com/mehdijac/mortables/actions)
[![PyPI](https://img.shields.io/pypi/v/mortables.svg)](https://pypi.org/project/mortables/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Fini les `qx` copiés-collés depuis un PDF ou un Excel douteux.
TH/TF 00-02, TGH/TGF 05 et la table non genrée 2024 sont embarquées, vérifiées, prêtes à l'emploi.

```bash
pip install mortables        # ou : uv add mortables
```

## En 30 secondes

```python
from mortables import get_table, life, cashflows

# Rente mensuelle d'un homme né le 15/03/1961, réversible à 60 % sur son épouse,
# valorisée au 31/12/2026, taux technique 2 %
life.annuity("TGH05", birth_date="1961-03-15", valuation_date="2026-12-31",
             rate=0.02, frequency=12,
             reversion=0.6, spouse_table="TGF05", spouse_birth_date="1963-07-02")
# → 22.26  (âges exacts, générations déduites des dates de naissance)

# Provision d'un portefeuille de rentiers
rentiers = [
    {"age": 65, "annual_rent": 12000, "gender": "M", "birth_year": 1961},
    {"age": 72, "annual_rent":  8000, "gender": "F", "birth_year": 1954},
    {"age": 58, "annual_rent": 15000, "gender": "F", "birth_year": 1968},
]
cashflows.total_provision(rentiers, table="TGH05", rate=0.02)   # → 773 083 €
```

Chaque rentier est valorisé avec **sa** génération et **sa** table (TGH05 ou TGF05 selon `gender`).

## Pourquoi mortables

- ✅ **Exact** : les Lx officiels, à l'identique, contrôlés par des tests de référence
- 🧮 **Complet** : rentes, assurances décès, capitaux différés, primes pures, provisions
- 💶 **Portefeuilles** : projection des flux et provision en un appel
- 📈 **Visuel** : les graphiques classiques en une ligne
- 📦 **Hors ligne** : tout est dans le package, rien à télécharger

## Tables incluses

| Table | Usage | Réglementation |
|---|---|---|
| `TH0002` · `TF0002` | Décès (hommes · femmes) | Arrêté du 20/12/2005 |
| `TGH05` · `TGF05` | Rentes viagères, générations 1900 à 2005 | Arrêté du 01/08/2006 |
| `TGHF05` | Rentes, **retraite supplémentaire collective** (non genrée : 60 % TGH05 + 40 % TGF05) | Arrêté du 18/11/2024 |

```python
th = get_table("TH0002")
th.lx[60]                 # → 85538.0 (valeur officielle)
th.life_expectancy(65)    # → 16.40 ans
th.to_dataframe()         # DataFrame pandas : age, lx, qx, px, dx, ex
```

## Rentes viagères, comme dans la vraie vie

`life.annuity()` couvre les cas réels, combinables entre eux :

```python
tg = get_table("TGH05", generation=1960)

life.annuity(tg, 65, 0.02)                                # annuelle, à terme à échoir → 19.97
life.annuity(tg, 65, 0.02, frequency=12)                  # mensuelle
life.annuity(tg, 65, 0.02, frequency=4, timing="arrears") # trimestrielle, à terme échu
life.annuity(tg, 65.75, 0.02)                             # âge non entier
life.annuity(tg, 60, 0.02, deferred=5)                    # différée de 5 ans
life.annuity(tg, 65, 0.02, guaranteed=10)                 # 10 annuités garanties
life.annuity(tg, 65, 0.02, reversion=0.6,                 # réversion 60 %
             spouse_table=get_table("TGF05", generation=1962), spouse_age=63)
```

Montant annuel de 1 (versé en `frequency` fractions). Entre deux âges entiers, les lx sont
interpolés linéairement : les rentes fractionnées sont calculées exactement, sans
approximation de Woolhouse. `life.exact_age()` calcule l'âge à partir des dates
(jours/365,25, mois révolus ou années révolues).

**Ajuster une table** — décalage d'âge, abattement, chocs Solvabilité 2 :

```python
tg.age_shifted(-2)     # décalage d'âge : 2 ans plus jeune (plus prudent en rente)
tg.scaled(0.80)        # qx × 0,80 — choc de longévité
tg.scaled(1.15)        # qx × 1,15 — choc de mortalité
```

📓 Exemple complet : [valoriser un portefeuille de rentiers](examples/portefeuille_rentiers.ipynb)
(rentes mensuelles réversibles, choc de longévité, passage à TGHF05).

## Fonctions classiques

```python
th = get_table("TH0002")

life.annuity_due(th, age=65, rate=0.02)              # rente viagère       ä65   → 14.36
life.annuity_due(th, age=65, rate=0.02, term=10)     # rente temporaire    ä65:10 → 8.34
life.whole_life_insurance(th, age=40, rate=0.02)     # vie entière         A40   → 0.488
life.term_insurance(th, age=40, rate=0.02, term=20)  # temporaire décès          → 0.088
life.pure_endowment(th, age=40, rate=0.02, term=20)  # capital différé           → 0.597
life.net_premium_whole_life(th, age=30, rate=0.02)   # prime pure annuelle P30   → 0.0135
life.reserve_whole_life(th, age_at_issue=30, rate=0.02, duration=20)  # provision

life.commutation(th, rate=0.02).Nx[65]               # nombres de commutation Dx, Nx, Cx, Mx…
```

Taux négatifs acceptés. Flux année par année : `cashflows.project(rentiers, table="TGH05", rate=0.02)` renvoie un DataFrame.

## Graphiques

```bash
pip install "mortables[viz]"     # ou : uv add "mortables[viz]"  (guillemets requis sous zsh)
```

```python
from mortables import viz

viz.plot_qx(["TH0002", "TF0002"], save="qx.png")                 # → enregistre une image
viz.plot_generations("TGH05", generations=[1950, 1970, 1990], show=True)   # → ouvre une fenêtre
viz.plot_cashflows(cashflows.project(rentiers, table="TGH05", rate=0.02))
```

Dans **Jupyter**, le graphique s'affiche tout seul (dernière ligne de la cellule).
Dans un **script**, ajoutez `save="fichier.png"` ou `show=True`.

## Bon à savoir

- **Tables générationnelles** : une génération commence à l'âge atteint en 1996, comme dans la table officielle (46 ans pour la génération 1950). `tg.min_age` vous donne cet âge.
- **Espérance de vie** : calculée en années entières (« curtate »), comme la colonne Ex des fichiers officiels.
- **Rentes** : `annuity_due` et `cashflows` paient une fois par an, en début d'année ; `life.annuity` gère fréquence, terme échu ou à échoir, réversion, etc.
- **Références externes** : les rentes TGH05, TGF05 et TGHF05 (avec et sans réversion) publiées par SPAC Actuaires sont retrouvées au centime près (`tests/test_annuity.py`).
- **Sources** : fichiers Lx diffusés par l'ISFA sur [ressources-actuarielles.net](http://www.ressources-actuarielles.net/EXT/ISFA/fp-isfa.nsf/34a14c286dfb0903c1256ffd00502d73/762c8e624ee98a5ec12577c100566d11). Seuls les textes du Journal officiel font foi.

> ⚠️ Vous utilisez la **0.1.0** ? Mettez à jour : ses tables étaient inexactes. Détails dans le [CHANGELOG](CHANGELOG.md).

## Bientôt

Portefeuilles de rentes mensuelles et réversibles · TD/TV 88-90 · Solvabilité 2 (courbe EIOPA, chocs) · analyse d'expérience (A/E).

Une table ou une fonction vous manque ? [Ouvrez une issue](https://github.com/mehdijac/mortables/issues).

## Contribuer

```bash
git clone https://github.com/mehdijac/mortables.git && cd mortables
uv sync && uv run pytest
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Licence [MIT](LICENSE).
