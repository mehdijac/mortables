# Changelog

Toutes les modifications notables de ce projet sont documentées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## [0.1.1] — 2026-11-27

> ⚠️ **Correctif majeur — tous les utilisateurs de la 0.1.0 doivent mettre à jour.**
> Les résultats obtenus avec la 0.1.0 (en particulier sur les rentes viagères) sont faux
> et doivent être recalculés.

### Corrigé
- **TGH05 / TGF05** : la 0.1.0 reconstituait les tables à partir d'une génération de base
  et de taux d'amélioration paramétriques, sans rapport avec les tables réglementaires
  (ex. l60 génération 1950 : 86 367 au lieu de 96 430 pour TGH05). Les tables sont
  désormais les **Lx officiels** (âges 0–120, générations 1900–2005), sans
  extrapolation. Chaque génération n'est définie qu'à partir de l'âge atteint en 1996.
- **TH 00-02 / TF 00-02** : remplacées par les Lx officiels, âges 0 à 120
  (ex. TH l1 = 99 511 au lieu de 99 514). Les `qx` sont déduits des `lx` et la table
  est fermée (`q_ω = 1`) : l'identité `Ax + d·äx = 1` est vérifiée à 1e-12 près.
- **Taux négatifs** : `cashflows.project` ignorait tout taux ≤ 0 (actualisation à 0 %).
- **Génération par rentier** : `cashflows.project` appliquait la même génération à tout
  le portefeuille. Chaque rentier peut maintenant porter `birth_year` (ou `generation`).
- La clé `gender` des rentiers, documentée mais ignorée, sélectionne désormais la table
  du sexe correspondant (TH0002 ↔ TF0002, TGH05 ↔ TGF05).
- Les `lx` des tables générationnelles ne sont plus arrondis à l'entier.
- Les montants actualisés ne sont plus arrondis ligne par ligne avant sommation.

### Modifié
- `cashflows.project` / `total_provision` : `years=None` par défaut (projection
  jusqu'à extinction) ; nouvelle colonne `discount_factor`.
- Validation des entrées : âge entier dans la table, `rate > -1`, durée entière ≥ 0.
- Nombres de commutation mis en cache par table et par taux.
- Ajout de `MortalityTable.min_age`, `MortalityTable.check_age`,
  `MortalityTable.from_lx` et `MortalityTable.from_qx` (tables personnalisées).
- Tables stockées en CSV (`TGH05.csv`, `TGF05.csv` au format large âge × génération),
  avec la source indiquée dans `TABLES.json` et les métadonnées.

### Ajouté
- `tests/test_reference.py` : valeurs officielles (lx, espérances de vie) et empreinte
  SHA-256 des fichiers de données.
- Workflow de CI GitHub Actions (lint + tests + build, Python 3.9 à 3.13).
- Projet géré avec **uv** (`uv.lock`, `.python-version`, outils de dev dans
  `[dependency-groups]`) : `uv sync`, `uv run pytest`, `uv build`.

## [0.1.0] — 2026-02-21

### Ajouté
- **Tables françaises** : TH 00-02, TF 00-02 (tables du moment), TGH 05, TGF 05 (tables générationnelles)
- **Module `core`** : chargement des tables, objet `MortalityTable` avec qx, lx, px, dx, ex
- **Module `life`** : nombres de commutation (Dx, Nx, Cx, Mx), annuités (due, immédiate, temporaire), assurances (vie entière, temporaire, mixte, capital différé), primes pures, provisions prospectives
- **Module `cashflows`** : projection des flux de trésorerie pour un portefeuille de rentiers
- **Module `viz`** : graphiques standards (courbes qx, survie, espérance de vie, comparaison, flux, générations)
