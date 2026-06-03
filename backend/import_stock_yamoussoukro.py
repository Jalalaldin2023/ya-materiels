"""
Import stock Ya Matériels Yamoussoukro
Source : Proposition_Commande_DICOREP.xlsx
Inventaire physique du 01/06/2026
"""
import sqlite3, os, sys

DB_PATH = os.path.join(os.path.dirname(__file__), "quincaillerie.db")
MAGASIN_ID = 2  # Ya Matériels Yamoussoukro
DATE_INVENTAIRE = "2026-06-01"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_or_create_categorie(db, nom):
    row = db.execute("SELECT id FROM categories WHERE nom=? AND magasin_id=?", (nom, MAGASIN_ID)).fetchone()
    if row:
        return row["id"]
    cur = db.execute("INSERT INTO categories (nom, magasin_id) VALUES (?,?)", (nom, MAGASIN_ID))
    return cur.lastrowid

# ── Stock inventaire Yamoussoukro ─────────────────────────────────────────────
# (code, nom, categorie, unite, stock_actuel, stock_cible, prix_achat, priorite)

INVENTAIRE = [
    # ── CARREAUX ──────────────────────────────────────────────────────────────
    ("CARR30/30-GEN",  "Carreaux 30/30 Gris/Émaillé",     "Carreaux",      "Carton",  8,   80,  3300, "HAUTE"),
    ("CARR20/30-GEN",  "Carreaux 20/30",                   "Carreaux",      "Carton",  40, 100,  3300, "HAUTE"),
    ("CARR60/60-GEN",  "Carreaux 60/60 Émaillé",           "Carreaux",      "Carton",  63, 100,  6300, "MOYENNE"),
    ("CARR40/40-GEN",  "Carreaux 40/40",                   "Carreaux",      "Carton",  13,  40,  4800, "MOYENNE"),

    # ── SANITAIRE & PLOMBERIE ─────────────────────────────────────────────────
    ("LAVABO35",       "Lavabo 35",                        "Sanitaire",     "Unité",   47,  47,  3400, "BASSE"),
    ("WCCHASBAS",      "WC Chasse Basse",                  "Sanitaire",     "Unité",    9,  20, 15000, "MOYENNE"),
    ("EVIERSIMPLE",    "Évier 1 Trou Simple",              "Sanitaire",     "Unité",    9,  20,  5000, "MOYENNE"),
    ("TUY125PVC",      "Tuyau D.125/6M PVC",               "Tuyauterie",    "Unité",    5,  15,  6300, "HAUTE"),
    ("TUY100PVC",      "Tuyau D.100/6M PVC",               "Tuyauterie",    "Unité",   10,  20,  3950, "MOYENNE"),
    ("TUY75PVC",       "Tuyau D.75/6M PVC",                "Tuyauterie",    "Unité",   10,  20,  2950, "MOYENNE"),
    ("TUY40PVC",       "Tuyau D.40/6M PVC",                "Tuyauterie",    "Unité",   10,  20,  1650, "BASSE"),
    ("TUY32PR",        "Tuyau D.32/6M Pression",           "Tuyauterie",    "Unité",   10,  20,  2650, "BASSE"),

    # ── PEINTURE ──────────────────────────────────────────────────────────────
    ("PEINTRAP5KG",    "Peinture Trapeau 5KG",             "Peinture",      "Unité",    3,  15,  2100, "HAUTE"),
    ("TTB5KG",         "Titan Tête Bleu 5KG",              "Peinture",      "Unité",    4,  15,  2200, "HAUTE"),
    ("PEINTBOSS5KG",   "Peinture Boss 5KG",                "Peinture",      "Unité",    5,  15,  2800, "HAUTE"),
    ("PEINTRAP30KG",   "Peinture Trapeau 30KG",            "Peinture",      "Unité",  120, 120, 11750, "BASSE"),
    ("PEINTORI30KG",   "Peinture Original 30KG",           "Peinture",      "Unité",    9,  15, 13500, "MOYENNE"),
    ("PEINTSUPER15KG", "Peinture Super+ 15KG",             "Peinture",      "Unité",    4,  10,  6500, "MOYENNE"),
    ("PEINTSUPER5KG",  "Peinture Super+ 5KG",              "Peinture",      "Unité",    4,  10,  2300, "MOYENNE"),
    ("INDUSTRAP5KG",   "Industrap Extra 5KG",              "Peinture",      "Unité",    3,  10,  2500, "MOYENNE"),
    ("DILUANT20L",     "Diluant 20L",                      "Peinture",      "Unité",    2,  10,  5000, "MOYENNE"),
    ("MEGALO",         "Mégalo",                           "Peinture",      "Carton",   5,  10,  8000, "BASSE"),

    # ── CIMENT, COLLE & MATÉRIAUX ─────────────────────────────────────────────
    ("CIMENTBLANC",    "Ciment Blanc 50KG",                "Construction",  "Sac",      4,  20,  8500, "HAUTE"),
    ("SDCCTROUELLE",   "Sac Colle Trouelle 20KG",          "Colle",         "Sac",      0,  20,  4500, "HAUTE"),
    ("TUBECOLLET",     "Tube de Colle Tangit",             "Colle",         "Unité",    0,  30,  1250, "MOYENNE"),

    # ── QUINCAILLERIE & OUTILLAGE ─────────────────────────────────────────────
    ("BOTTEFER8",      "Botte de Fer 8",                   "Quincaillerie", "Botte",    2,   5, 45000, "MOYENNE"),
    ("BOTTEFER10",     "Botte de Fer 10",                  "Quincaillerie", "Botte",    2,   5, 45000, "MOYENNE"),
    ("BOTTEFER12",     "Botte de Fer 12",                  "Quincaillerie", "Botte",    2,   5, 45000, "MOYENNE"),
    ("POINTES",        "Pointes (carton assortis)",         "Quincaillerie", "Carton",   4,   6, 25000, "BASSE"),
    ("BAGUETTE-SOUD",  "Baguette à Souder",                "Quincaillerie", "Paquet",   3,   6,  3500, "BASSE"),

    # ── MACHINES EDON (prix à négocier) ───────────────────────────────────────
    ("EDON-MMA257",    "EDON MMA-257 Poste à Souder",      "Machines",      "Unité",    2,   3,      0, "BASSE"),
    ("EDON-4001",      "EDON 4001",                        "Machines",      "Unité",    7,  10,      0, "BASSE"),
    ("EDON-CS18S",     "EDON CS-18S/1650",                 "Machines",      "Unité",    3,   5,      0, "MOYENNE"),
    ("EDON-Z1CED32K",  "EDON Z1C-ED32K",                  "Machines",      "Unité",    3,   5,      0, "MOYENNE"),
    ("EDON-BLUE315",   "EDON Blue-315",                    "Machines",      "Unité",    4,   6,      0, "BASSE"),
    ("EDON-LV32110",   "EDON LV3-2110",                    "Machines",      "Unité",    3,   5,      0, "BASSE"),
    ("EDON-FIL50M",    "Fil EDON 50M",                     "Machines",      "Rouleau",  1,   5,      0, "HAUTE"),
    ("EDON-FIL35M",    "Fil EDON 35M",                     "Machines",      "Rouleau",  1,   5,      0, "HAUTE"),
]

MARGE = 1.30  # +30% prix de vente


def main():
    db = get_db()
    try:
        print("\n🔧 YA MATÉRIELS YAMOUSSOUKRO — Importation inventaire physique")
        print(f"   Source : Proposition_Commande_DICOREP.xlsx  •  Date : {DATE_INVENTAIRE}\n")

        # Vérifier si déjà importé
        existing = db.execute(
            "SELECT COUNT(*) FROM produits WHERE magasin_id=?", (MAGASIN_ID,)
        ).fetchone()[0]
        if existing > 0:
            print(f"⚠️  {existing} produits déjà présents pour ce magasin.")
            rep = input("   Continuer et mettre à jour ? (o/N) : ").strip().lower()
            if rep != 'o':
                print("Importation annulée.")
                return

        nb_crees = nb_maj = 0
        valeur_stock = 0
        alertes_haute = []

        for code, nom, cat_nom, unite, stock, stock_cible, prix_achat, priorite in INVENTAIRE:
            cat_id = get_or_create_categorie(db, cat_nom)
            prix_vente = round(prix_achat * MARGE / 100) * 100 if prix_achat > 0 else 0
            # stock_min = la moitié du stock cible (seuil d'alerte)
            stock_min = max(2, stock_cible // 2)

            existing_prod = db.execute(
                "SELECT id, quantite FROM produits WHERE code=? AND magasin_id=?",
                (code, MAGASIN_ID)
            ).fetchone()

            if existing_prod:
                db.execute(
                    "UPDATE produits SET quantite=?, quantite_min=?, prix_achat=?, updated_at=datetime('now') WHERE id=?",
                    (stock, stock_min, prix_achat, existing_prod["id"])
                )
                prod_id = existing_prod["id"]
                nb_maj += 1
                action = "MAJ"
            else:
                cur = db.execute(
                    """INSERT INTO produits
                       (code, nom, categorie_id, prix_achat, prix_vente, quantite, quantite_min, unite, magasin_id)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (code, nom, cat_id, prix_achat, prix_vente, stock, stock_min, unite, MAGASIN_ID)
                )
                prod_id = cur.lastrowid
                nb_crees += 1
                action = "NEW"

            # Mouvement inventaire
            if stock > 0:
                db.execute(
                    """INSERT INTO mouvements_stock
                       (produit_id, type, quantite, reference, notes, magasin_id, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (prod_id, "entree", stock,
                     f"INV-YAM-{DATE_INVENTAIRE}",
                     f"Inventaire physique {DATE_INVENTAIRE} — Priorité {priorite}",
                     MAGASIN_ID, DATE_INVENTAIRE + " 08:00:00")
                )

            valeur_stock += stock * prix_achat

            # Log
            prio_icon = {"HAUTE": "🔴", "MOYENNE": "🟠", "BASSE": "🟢"}.get(priorite, "⚪")
            print(f"  {prio_icon} [{action}] {nom:<45} stock={stock:>4} / cible={stock_cible:>4}  {prix_achat:>8,} CFA")

            if priorite == "HAUTE" and (stock == 0 or stock < stock_cible * 0.3):
                alertes_haute.append((nom, stock, stock_cible))

        db.commit()

        print(f"\n{'='*65}")
        print(f"✅ Import terminé — Ya Matériels Yamoussoukro")
        print(f"   {nb_crees} produits créés  •  {nb_maj} mis à jour")
        print(f"   Valeur stock actuel : {valeur_stock:,.0f} FCFA")
        print(f"{'='*65}")

        # Résumé par catégorie
        cats = db.execute("""
            SELECT c.nom, COUNT(p.id) as nb, SUM(p.quantite) as total_qte,
                   SUM(p.quantite*p.prix_achat) as valeur
            FROM produits p JOIN categories c ON p.categorie_id=c.id
            WHERE p.magasin_id=?
            GROUP BY c.nom ORDER BY valeur DESC
        """, (MAGASIN_ID,)).fetchall()

        print(f"\n📦 STOCK PAR CATÉGORIE :")
        print(f"{'Catégorie':<20} {'Réf':>5} {'Unités':>8} {'Valeur':>18}")
        print("-" * 58)
        for r in cats:
            val = r['valeur'] or 0
            print(f"{r['nom']:<20} {r['nb']:>5} {r['total_qte']:>8} {val:>18,.0f} FCFA")
        print("-" * 58)
        total_val = sum((r['valeur'] or 0) for r in cats)
        print(f"{'TOTAL':<20} {sum(r['nb'] for r in cats):>5} {'':<8} {total_val:>18,.0f} FCFA")

        # Alertes critiques
        if alertes_haute:
            print(f"\n🚨 ALERTES CRITIQUES (stock < 30% cible) :")
            for nom, stock, cible in alertes_haute:
                print(f"   • {nom} : {stock} / {cible} — commande urgente !")

        print(f"\n💡 Montant estimé commande (articles à prix connus) : 2 231 000 FCFA")
        print(f"   + articles EDON (prix sur devis)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur : {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
