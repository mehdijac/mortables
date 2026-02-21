# Changelog

Toutes les modifications notables de ce projet sont documentées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## [0.1.0] — 2026-02-21

### Ajouté
- **Tables françaises** : TH 00-02, TF 00-02 (tables du moment), TGH 05, TGF 05 (tables générationnelles)
- **Module `core`** : chargement des tables, objet `MortalityTable` avec qx, lx, px, dx, ex
- **Module `life`** : nombres de commutation (Dx, Nx, Cx, Mx), annuités (due, immédiate, temporaire), assurances (vie entière, temporaire, mixte, capital différé), primes pures, provisions prospectives
- **Module `cashflows`** : projection des flux de trésorerie pour un portefeuille de rentiers
- **Module `viz`** : graphiques standards (courbes qx, survie, espérance de vie, comparaison, flux, générations)
