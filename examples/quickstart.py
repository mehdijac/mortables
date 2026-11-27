"""
Exemple d'utilisation de mortables.

Ce script montre les principales fonctionnalités du package.
Il peut être exécuté tel quel ou copié dans un notebook Jupyter.
"""

from mortables import cashflows, get_table, life, list_tables

# ============================================================
# 1. Découvrir les tables disponibles
# ============================================================
print("=== Tables disponibles ===")
for t in list_tables():
    print(f"  {t['id']:8s}  {t['name']:10s}  {t['description']}")

# ============================================================
# 2. Charger une table du moment
# ============================================================
print("\n=== Table TH 00-02 (Hommes) ===")
th = get_table("TH0002")
print(f"  Âge max : {th.max_age}")
print(f"  qx à 0 ans  : {th.qx_at(0):.6f}")
print(f"  qx à 65 ans : {th.qx_at(65):.6f}")
print(f"  Espérance de vie à 0 ans  : {th.life_expectancy(0):.1f} ans")
print(f"  Espérance de vie à 65 ans : {th.life_expectancy(65):.1f} ans")

tf = get_table("TF0002")
print("\n=== Table TF 00-02 (Femmes) ===")
print(f"  Espérance de vie à 0 ans  : {tf.life_expectancy(0):.1f} ans")
print(f"  Espérance de vie à 65 ans : {tf.life_expectancy(65):.1f} ans")

# ============================================================
# 3. Table générationnelle
# ============================================================
print("\n=== Tables TGH 05 — Comparaison par génération ===")
for gen in [1940, 1950, 1970, 1990]:
    tg = get_table("TGH05", generation=gen)
    print(f"  Génération {gen} : e(65) = {tg.life_expectancy(65):.1f} ans, "
          f"qx(65) = {tg.qx_at(65):.5f}")

# ============================================================
# 4. Fonctions actuarielles
# ============================================================
print("\n=== Calculs actuariels (TH 00-02, taux 2%) ===")
rate = 0.02

ad = life.annuity_due(th, age=65, rate=rate)
print(f"  Annuité viagère due (ä65)     : {ad:.4f}")

ad10 = life.annuity_due(th, age=65, rate=rate, term=10)
print(f"  Annuité temporaire 10 ans     : {ad10:.4f}")

ax = life.whole_life_insurance(th, age=40, rate=rate)
print(f"  Assurance vie entière (A40)   : {ax:.4f}")

ti = life.term_insurance(th, age=40, rate=rate, term=20)
print(f"  Temporaire décès 20 ans       : {ti:.4f}")

p = life.net_premium_whole_life(th, age=30, rate=rate)
print(f"  Prime pure vie entière (P30)  : {p:.6f}")

# ============================================================
# 5. Projection de cash flows
# ============================================================
print("\n=== Projection de flux — Portefeuille de rentiers ===")
portfolio = [
    {"age": 65, "annual_rent": 12000, "gender": "M", "birth_year": 1961},
    {"age": 72, "annual_rent": 8000, "gender": "F", "birth_year": 1954},
    {"age": 58, "annual_rent": 15000, "gender": "F", "birth_year": 1968},
]

# TGH05 / TGF05 selon le sexe, génération propre à chaque rentier
flows = cashflows.project(portfolio, table="TGH05", rate=0.02)
print(flows.head(10).to_string(index=False))

prov = cashflows.total_provision(portfolio, table="TGH05", rate=0.02)
print(f"\n  Provision totale (BEL) : {prov:,.0f} €")

# ============================================================
# 6. Visualisation (décommenter pour afficher les graphiques)
# ============================================================
# from mortables import viz
#
# # Courbes de mortalité comparées
# fig = viz.plot_qx(["TH0002", "TF0002"], log_scale=True, age_range=(0, 100))
# fig.savefig("qx_comparison.png", dpi=150)
#
# # Survie
# fig = viz.plot_survival(["TH0002", "TF0002"])
# fig.savefig("survival.png", dpi=150)
#
# # Espérance de vie
# fig = viz.plot_life_expectancy(["TH0002", "TF0002"])
# fig.savefig("life_expectancy.png", dpi=150)
#
# # Comparaison par génération
# fig = viz.plot_generations("TGH05", generations=[1930, 1950, 1970, 1990])
# fig.savefig("generations.png", dpi=150)
#
# # Flux de trésorerie
# fig = viz.plot_cashflows(flows)
# fig.savefig("cashflows.png", dpi=150)

print("\nTerminé !")
