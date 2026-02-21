# Contribuer à mortables

Merci de votre intérêt pour ce projet ! Voici comment contribuer.

## Signaler un bug ou proposer une fonctionnalité

Ouvrez une [issue](https://github.com/yourname/mortables/issues) en décrivant :
- Ce que vous attendiez
- Ce qui s'est passé
- Un exemple minimal pour reproduire le problème

## Développement local

```bash
# Cloner le dépôt
git clone https://github.com/yourname/mortables.git
cd mortables

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Installer en mode développement
pip install -e ".[dev]"

# Lancer les tests
pytest

# Vérifier le style
ruff check .
```

## Ajouter une table de mortalité

1. Placez les données dans `mortables/tables/<pays>/` (CSV pour les tables du moment, JSON pour les tables générationnelles)
2. Ajoutez une entrée dans le fichier `TABLES.json` du même répertoire
3. Ajoutez un test dans `tests/`

Format CSV attendu (tables du moment) :
```
age,lx,qx
0,100000,0.00486
1,99514,0.00041
...
```

Format JSON attendu (tables générationnelles) :
```json
{
  "name": "...",
  "gender": "M",
  "type": "generational",
  "base_generation": 1950,
  "min_generation": 1900,
  "max_generation": 2005,
  "max_age": 120,
  "base_qx": [...],
  "annual_improvement": [...]
}
```

## Conventions de code

- Python 3.9+
- Style : [ruff](https://docs.astral.sh/ruff/) avec les réglages du `pyproject.toml`
- Docstrings en anglais (pour la compatibilité avec les outils de documentation)
- Commentaires et messages utilisateur en français quand pertinent
- Tests avec pytest
