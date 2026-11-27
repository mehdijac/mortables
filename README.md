# mortables

**Les tables de mortalité réglementaires françaises en Python. Exactes. En une ligne.**

[![CI](https://github.com/mehdijac/mortables/actions/workflows/ci.yml/badge.svg)](https://github.com/mehdijac/mortables/actions)
[![PyPI](https://img.shields.io/pypi/v/mortables.svg)](https://pypi.org/project/mortables/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Fini les `qx` copiés-collés depuis un PDF ou un Excel douteux.
TH/TF 00-02 et TGH/TGF 05 sont embarquées, vérifiées, prêtes à l'emploi.

```bash
pip install mortables        # ou : uv add mortables
```

## En 30 secondes

```python
from mortables import get_table, life, cashflows

# Rente viagère d'un homme né en 1960, à 65 ans, taux technique 2 %
tg = get_table("TGH05", generation=1960)
life.annuity_due(tg, age=65, rate=0.02)                 # → 19.97

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

```python
th = get_table("TH0002")
th.lx[60]                 # → 85538.0 (valeur officielle)
th.life_expectancy(65)    # → 16.40 ans
th.to_dataframe()         # DataFrame pandas : age, lx, qx, px, dx, ex
```

## Ce que vous pouvez calculer

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
- **Rentes** : payées une fois par an, en début d'année (à terme à échoir).
- **Sources** : fichiers Lx diffusés par l'ISFA sur [ressources-actuarielles.net](http://www.ressources-actuarielles.net/EXT/ISFA/fp-isfa.nsf/34a14c286dfb0903c1256ffd00502d73/762c8e624ee98a5ec12577c100566d11). Seuls les textes du Journal officiel font foi.

> ⚠️ Vous utilisez la **0.1.0** ? Mettez à jour : ses tables étaient inexactes. Détails dans le [CHANGELOG](CHANGELOG.md).

## Bientôt

Rentes mensuelles et trimestrielles · réversion · décalages d'âge · table non genrée retraite collective · TD/TV 88-90 · Solvabilité 2 (courbe EIOPA, chocs) · analyse d'expérience (A/E).

Une table ou une fonction vous manque ? [Ouvrez une issue](https://github.com/mehdijac/mortables/issues).

## Contribuer

```bash
git clone https://github.com/mehdijac/mortables.git && cd mortables
uv sync && uv run pytest
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Licence [MIT](LICENSE).
