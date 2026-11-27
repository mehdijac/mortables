# Contribuer à mortables

Merci de votre intérêt pour ce projet ! Voici comment contribuer.

## Signaler un bug ou proposer une fonctionnalité

Ouvrez une [issue](https://github.com/mehdijac/mortables/issues) en décrivant :
- Ce que vous attendiez
- Ce qui s'est passé
- Un exemple minimal pour reproduire le problème

## Développement local

```bash
# Cloner le dépôt
git clone https://github.com/mehdijac/mortables.git
cd mortables

# Installer l'environnement (uv : https://docs.astral.sh/uv/)
uv sync

# Lancer les tests
uv run pytest

# Vérifier le style
uv run ruff check .

# Ajouter une dépendance
uv add <paquet>            # dépendance du package
uv add --dev <paquet>      # outil de développement
```

## Ajouter une table de mortalité

1. Placez les données dans `mortables/tables/<pays>/`, **reprises à l'identique de la source
   officielle** (jamais reconstituées ni extrapolées)
2. Ajoutez une entrée dans le fichier `TABLES.json` du même répertoire, avec le champ `source`
3. Ajoutez des tests de référence dans `tests/test_reference.py` (valeurs officielles et
   empreinte SHA-256 du fichier)

Format CSV attendu (tables du moment), `lx` uniquement — les `qx` en sont déduits :
```
age,lx
0,100000
1,99511
...
```

Format CSV attendu (tables générationnelles), une colonne `lx` par année de naissance ;
une cellule vide signifie que l'âge n'est pas défini par la table :
```
age,1900,1901,...,2005
0,,,...,100000
...
```

## Conventions de code

- Python 3.9+
- Style : [ruff](https://docs.astral.sh/ruff/) avec les réglages du `pyproject.toml`
- Docstrings en anglais (pour la compatibilité avec les outils de documentation)
- Commentaires et messages utilisateur en français quand pertinent
- Tests avec pytest
