"""
Import stock Ya Matériels Divo depuis les deux devis :
  - GMS Devis S174064 (Peinture, Sanitaire, Plomberie...)
  - DICOREP Devis S175224 (Outils, Électricité, Carreaux...)
"""
import sqlite3, os, sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "quincaillerie.db")
MAGASIN_ID = 1  # Ya Matériels Divo

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ── Catégories à utiliser ─────────────────────────────────────────────────────
CATEGORIES = {
    "Peinture":       ["Peinture", "Diluant", "Email", "Vernis", "Colorant", "Titan", "Champion"],
    "Plomberie":      ["Robinet", "Tuyau", "Flexible", "Siphon", "Coude", "Raccord",
                       "Téflon", "Fixation", "Mécanisme", "Abattant", "Gang", "Colle tangit",
                       "Tube de colle", "Sac de carreau colle"],
    "Sanitaire":      ["WC", "Lavabo", "Évier", "Miroir", "Porte serviette", "Porte savon",
                       "Tablette", "Brouette"],
    "Électricité":    ["Goulotte", "Contact", "Prise", "Fil", "Douille", "Brasseur",
                       "Rouleau fil", "Attache"],
    "Outils":         ["Marteau", "Massette", "Pince", "Tenaille", "Cisaille", "Truelle",
                       "Décamètre", "Règle", "Balance", "Coupe carreau", "Epica", "Canon"],
    "Quincaillerie":  ["Paumelle", "Crochet", "Pointe", "Botte", "Carton baguette",
                       "Paquet de gang"],
    "Construction":   ["Lambris", "Baguette pvc", "Tôle", "Carreau", "Carreaux",
                       "Ciment", "Colorant", "Carreau colle"],
    "Gaz":            ["Gaz", "Tête de gaz"],
    "Ventilation":    ["Ventilateur"],
    "Autre":          [],
}

def detect_categorie(nom):
    nom_lower = nom.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in nom_lower:
                return cat
    return "Autre"

# ── Données des deux devis ────────────────────────────────────────────────────
# Format : (code, nom, quantite, prix_achat, unite)

DEVIS_GMS = {
    "reference": "GMS-S174064",
    "fournisseur": "GMS (Générale de Matériel et de Services)",
    "date": "2025-10-14",
    "total": 2373000,
    "lignes": [
        ("GLYCERODELBLANC",   "Glycero Delux Blanc 1KG",         24,  2200, "pcs"),
        ("GLYCEDORANGE01",    "Glycero Delux Orange 1KG",        24,  2200, "pcs"),
        ("DELUX1KGVERT",      "Delux 1kg Vert",                  24,  2500, "pcs"),
        ("GLYCERODELUXBLEU",  "Glycero Delux Bleu 1KG",          24,  2200, "pcs"),
        ("DR1KG",             "Delux Rouge 1kg",                 24,  2200, "pcs"),
        ("DELUBLANC4KG",      "Delux Blanc 4kg",                  6,  7500, "pcs"),
        ("DELUJ4KG",          "Delux Jaune 4kg",                  6,  7500, "pcs"),
        ("DELUO4KG",          "Delux Orange 4kg",                 6,  7500, "pcs"),
        ("DELUGF4KG",         "Delux Gris Foncé 4kg",             3,  7500, "pcs"),
        ("DELUGC4KG",         "Delux Gris Clair 4kg",             3,  7500, "pcs"),
        ("PORTSERVIETTE004",  "Porte Serviette Industrap",       25,  1000, "pcs"),
        ("PSD002",            "Porte Savon Delux",               25,   700, "pcs"),
        ("CPAUMELLE140",      "Carton Paumelle 140",              1, 22000, "ctn"),
        ("PEINTMIL30KG",      "Peinture Milano 30KG",            50, 13500, "pcs"),
        ("PEINTMIL",          "Peinture Milano 15KG",            30,  6500, "pcs"),
        ("PEINTBOSS30KG",     "Peinture Boss 30kg",              20, 14900, "pcs"),
        ("CARTONGAZ",         "Carton de Gaz",                    1, 16500, "ctn"),
        ("PTG10PCS",          "Paquet Tête de Gaz 10pcs",         2,  6500, "pqt"),
        ("DILUANTA1L",        "Diluant A 1L",                    20,   800, "pcs"),
        ("DILUANTC1L",        "Diluant C 1L",                    20,  1300, "pcs"),
        ("EMBLANC",           "Email Delux Blanc",               24,   400, "pcs"),
        ("EMDGRIS",           "Email Delux Gris",                24,   400, "pcs"),
        ("EMDROUGE",          "Email Delux Rouge",               24,   400, "pcs"),
        ("SDCCTROUELLE",      "Sac Carreau Colle Truelle",       15,  4600, "sac"),
        ("61750",             "Robinet de Douche Elena",         15,   900, "pcs"),
        ("RLAVABO",           "Robinet de Lavabo",               15,  1600, "pcs"),
        ("PAQUETTELONGRD",    "Paquet Téflon Grand",              2,  2250, "pqt"),
        ("FLEXIBLELAVABOMF",  "Flexible Lavabo M/F",             20,   650, "pcs"),
        ("MIROIRSPLE",        "Miroir Simple",                   25,  1400, "pcs"),
        ("COUDE100",          "Coude 100 PVC",                   20,   600, "pcs"),
        ("TABLETTE0024",      "Tablette en Caoutchouc",          15,  1000, "pcs"),
        ("FIXATIONLAVABO",    "Fixation Lavabo",                 15,   300, "pcs"),
        ("RIVA130",           "Siphon Gaine 32 Riva",            15,   700, "pcs"),
        ("GDY61253",          "Mécanisme Oli Plus",              15,  2700, "pcs"),
        ("ABATTANTWC",        "Abattant WC",                     15,  2000, "pcs"),
        ("FLEXIBLEWCMF",      "Flexible WC M/F",                 15,   650, "pcs"),
        ("REQUERRE001",       "Robinet Équerre",                 15,   650, "pcs"),
        ("TRUELLE20",         "Truelle N°20",                    10,   900, "pcs"),
        ("RGCOMPLET",         "Raccord de Gaz Complet",          10,  1500, "pcs"),
        ("RRDGAZ",            "Rouleau Raccord de Gaz",           2,  7000, "roul"),
        ("FS1676U",           "Ventilateur Solstar FS1676U",     10, 16000, "pcs"),
        ("FS1848U",           "Ventilateur Solstar FS1848U",      5, 20000, "pcs"),
    ]
}

DEVIS_DICOREP = {
    "reference": "DICOREP-S175224",
    "fournisseur": "DICOREP Inter SARL",
    "date": "2025-10-18",
    "total": 6231000,
    "lignes": [
        ("OOG1000",          "Massette Manche en Bois 1kg",          6,  3000, "pcs"),
        ("MAD001",           "Marteau Arrache-Clou Manche Bois 16OZ",12,  2200, "pcs"),
        ("MARTEAU1.5KG",     "Marteau 1.5kg",                        6,  2000, "pcs"),
        ("EP30018",          "Epica Star 30018 Marteau Arrache-Clou", 7,  1100, "pcs"),
        ("MARTEAU2KG",       "Marteau 2kg",                         12,  2500, "pcs"),
        ("MARTEAU25",        "Marteau N°25",                         4,  1200, "pcs"),
        ("MARTEAU18",        "Marteau N°18",                         3,   800, "pcs"),
        ("PEINTRAP5KG",      "Peinture Trapeau 5KG",                10,  2100, "pcs"),
        ("PEINTRAP15KG",     "Peinture Trapeau 15KG",               10,  6500, "pcs"),
        ("PEINTSUPER5KG",    "Peinture Super 5KG",                   5,  2300, "pcs"),
        ("EHO1420",          "Balance 20kg",                         8,  8000, "pcs"),
        ("GOUL3FIL",         "Goulotte 3 Fils",                     36,  1300, "pcs"),
        ("VENTMETROCOU",     "Ventilateur Metro Court",              4,  8000, "pcs"),
        ("GOULOTTE1FIL",     "Goulotte 1 Passage Autocollant",     120,   550, "pcs"),
        ("GOULOTTE2FILS",    "Goulotte 2 Passages",                 80,   750, "pcs"),
        ("PAQUETCRO8",       "Paquet Crochet 8",                    12,  2000, "pqt"),
        ("PAQCROCHET12",     "Paquet Crochet 12",                   12,  3500, "pqt"),
        ("PAQUETPAUMELLE110","Paquet Paumelle 110 (G-D)",            2,  3500, "pqt"),
        ("POINTACIER01",     "Paquet Pointe Acier N°7",             15,   900, "pqt"),
        ("POINTAC5",         "Paquet Pointe Acier N°5",             15,   900, "pqt"),
        ("POINTAC4",         "Paquet Pointe Acier N°4",             15,   900, "pqt"),
        ("POINTAC3",         "Paquet Pointe Acier N°3",             15,   900, "pqt"),
        ("TNC208",           "Tenaille 8 Pouces",                   20,  2000, "pcs"),
        ("HTC04601",         "Coupe Carreau 600mm",                  3, 28500, "pcs"),
        ("EP50025",          "Epica Star 50025 Pince Coupante",     18,  1500, "pcs"),
        ("EP50361",          "Epica Star 50361 Pince Long Bec 6\"", 18,  1500, "pcs"),
        ("CSV05",            "Canon Simple Vachette 5 Clés",        30,  1000, "pcs"),
        ("PINCE",            "Pince",                               36,  1200, "pcs"),
        ("CN30",             "Cisaille N°30",                       15, 18000, "pcs"),
        ("FL113",            "Flexible de Douche Caoutchouc",       25,  1200, "pcs"),
        ("D100M",            "Décamètre 100M",                       7,  5500, "pcs"),
        ("DECAMETRE30M",     "Décamètre 30m",                       19,  2000, "pcs"),
        ("REGLE3MA",         "Règle Allu 3m avec Niveau",            5, 11000, "pcs"),
        ("REGLE25MA",        "Règle Allu 2.5m avec Niveau",          5,  8500, "pcs"),
        ("PCVV",             "Paquet Contact Va-Vient",             25,  3300, "pqt"),
        ("PCDSENCASTRE",     "Paquet Contact Double Simple Encastré",25, 3700, "pqt"),
        ("PPENCASTRE",       "Paquet Prise Encastrée",              25,  3300, "pqt"),
        ("ATTACHE7",         "Attache 7",                           20,   250, "pqt"),
        ("PQUETATTACHE8",    "Paquet Attache N°8",                  20,   250, "pqt"),
        ("ATTACHE10",        "Paquet Attache 10",                   20,   350, "pqt"),
        ("PAQUETA12",        "Paquet Attache 12",                   20,   600, "pqt"),
        ("PAQDOUILLE50",     "Paquet Douille 50pcs",                20,  4000, "pqt"),
        ("BLSOLSTAR",        "Brasseur Log Solstar",                 3, 15000, "pcs"),
        ("WCCHASBAS",        "WC Chasse Basse",                     20, 15000, "pcs"),
        ("LAVABO35",         "Lavabo 35",                           20,  3400, "pcs"),
        ("POINTEPVC",        "Pointe PVC de Lambris",               25,  1500, "pqt"),
        ("EVIERSIMPLE",      "Évier 1 Trou Simple",                  5,  5000, "pcs"),
        ("TUY100PVC",        "Tuyau 100 PVC",                       10,  3950, "pcs"),
        ("TUY75PVC",         "Tuyau 75 PVC",                        10,  2950, "pcs"),
        ("TUY40PVC",         "Tuyau 40 PVC",                        10,  1650, "pcs"),
        ("PGANG",            "Paquet de Gang",                      10,  6500, "pqt"),
        ("TUY32PR",          "Tuyau 32 Pression",                   10,  2650, "pcs"),
        ("VERNISEAU",        "Vernis à Eau 1L",                     48,  2400, "pcs"),
        ("DILMUANTA4L",      "Diluant A 4L",                        10,  3900, "pcs"),
        ("COLTANGIT1KG",     "Colle Tangit 1kg",                    16,  7500, "pcs"),
        ("TUBECOLLET",       "Tube de Colle Tangit",                60,  1250, "pcs"),
        ("EMAILDELUX",       "Email Delux Rouge",                  192,   400, "pcs"),
        ("EMDNOIR",          "Email Delux Noir",                   144,   400, "pcs"),
        ("SACCB50KG",        "Sac de Ciment Blanc 50kg",             5,  8500, "sac"),
        ("CCJO",             "Carton Colorant Jaune Oxyde",          2, 16800, "ctn"),
        ("CCO",              "Carton Colorant Orange",               1, 16800, "ctn"),
        ("CCR",              "Carton Colorant Rouge",                2, 16800, "ctn"),
        ("CCN",              "Carton Colorant Noir",                 2, 16800, "ctn"),
        ("CCJV",             "Carton Colorant Jaune Vif",            2, 16800, "ctn"),
        ("CCVERT",           "Carton Colorant Vert",                 2, 16800, "ctn"),
        ("CCB",              "Carton Colorant Bleu",                 1, 16800, "ctn"),
        ("PEINTMIL5KG",      "Peinture Milano 5KG",                 10,  2300, "pcs"),
        ("PEINTBOSS5KG",     "Peinture Boss 5kg",                   10,  2800, "pcs"),
        ("PEINTRAP30KG",     "Peinture Trapeau 30KG",               18, 11750, "pcs"),
        ("PEINCHAMP5KG",     "Peinture Champion 5kg",                5,  2300, "pcs"),
        ("TTB5KG",           "Titan Tête Bleu 5kg",                 10,  2200, "pcs"),
        ("PLL20SANTUOS",     "Paquet Lambris Larg.20 Santuos",      30, 20000, "pqt"),
        ("BAGUETTEPVC",      "Baguette PVC",                        30,  1100, "pcs"),
        ("CARR2030",         "Carton Carreaux 20/30",               40,  3300, "ctn"),
        ("CARR3030E",        "Carton Carreaux 30/30 Émaillé",       20,  4400, "ctn"),
        ("CARR3030",         "Carton Carreaux 30/30 Gris",          50,  3250, "ctn"),
        ("CARR3030AD",       "Carton Carreaux 30/30 AD Gris",       30,  3400, "ctn"),
        ("TBS",              "Tôle Petite Feuille Blanc Soleil",   100,  1800, "pcs"),
        ("TBLEUS",           "Tôle Petite Feuille Bleu Soleil",    100,  2200, "pcs"),
        ("TRS",              "Tôle Petite Feuille Rouge Soleil",   100,  2200, "pcs"),
        ("TPFVSOLEIL",       "Tôle Petite Feuille Verte Soleil",   100,  2200, "pcs"),
        ("BOTTEFILFER",      "Botte Fil Fer Noir",                  10,  5500, "btte"),
        ("TH15BLEUIMP",      "Rouleau Fil TH1.5 Bleu Importé",     10, 12500, "roul"),
        ("TH25BLEUIMP",      "Rouleau Fil TH2.5 Bleu Importé",     10, 20000, "roul"),
        ("PLASTB15",         "Rouleau TH1.5 Bleu Plasticable",      10, 15200, "roul"),
        ("BBLEU",            "Brouette Bleue",                       2, 17000, "pcs"),
        ("BVERTE",           "Brouette Verte",                       3, 19000, "pcs"),
        ("CARTONBAGUETTE25", "Carton Baguette 2.5",                  1, 15000, "ctn"),
        ("TUY125PVC",        "Tuyau 125 PVC",                       10,  6300, "pcs"),
        # Carton paumelle (aussi dans GMS)
        ("CPAUMELLE140B",    "Carton Paumelle 140 (lot 2)",          2, 22000, "ctn"),
    ]
}


def get_or_create_categorie(db, nom, magasin_id):
    row = db.execute("SELECT id FROM categories WHERE nom=? AND magasin_id=?", (nom, magasin_id)).fetchone()
    if row:
        return row["id"]
    cur = db.execute("INSERT INTO categories (nom, magasin_id) VALUES (?,?)", (nom, magasin_id))
    return cur.lastrowid


def get_or_create_fournisseur(db, nom, magasin_id):
    row = db.execute("SELECT id FROM fournisseurs WHERE nom=? AND magasin_id=?", (nom, magasin_id)).fetchone()
    if row:
        return row["id"]
    cur = db.execute("INSERT INTO fournisseurs (nom, magasin_id) VALUES (?,?)", (nom, magasin_id))
    return cur.lastrowid


def gen_achat_numero(prefix, db):
    count = db.execute("SELECT COUNT(*) FROM achats WHERE numero LIKE ?", (f"{prefix}%",)).fetchone()[0]
    return f"{prefix}-{count+1:03d}"


def import_devis(db, devis, magasin_id, prix_vente_majoration=1.25):
    """
    Importe un devis : crée les produits manquants + un achat + mouvements de stock.
    prix_vente_majoration : marge appliquée au prix d'achat pour calculer le prix de vente
    """
    print(f"\n{'='*60}")
    print(f"Importation : {devis['reference']} — {devis['fournisseur']}")
    print(f"{'='*60}")

    fourn_id = get_or_create_fournisseur(db, devis["fournisseur"], magasin_id)

    # Créer l'achat
    numero = f"AC{magasin_id}-{devis['reference']}"
    total = devis["total"]

    # Vérifier si cet achat existe déjà
    existing = db.execute("SELECT id FROM achats WHERE numero=?", (numero,)).fetchone()
    if existing:
        print(f"⚠️  Achat {numero} déjà importé — ignoré.")
        return 0

    cur = db.execute(
        "INSERT INTO achats (numero, fournisseur_id, total, montant_paye, statut, notes, magasin_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (numero, fourn_id, total, total, "paye",
         f"Importé depuis devis {devis['reference']} du {devis['date']}", magasin_id, devis["date"] + " 08:00:00")
    )
    achat_id = cur.lastrowid

    nb_crees = 0
    nb_maj = 0

    for code, nom, qte, prix_achat, unite in devis["lignes"]:
        # Catégorie automatique
        cat_nom = detect_categorie(nom)
        cat_id = get_or_create_categorie(db, cat_nom, magasin_id)

        # Prix de vente = prix achat + marge
        prix_vente = round(prix_achat * prix_vente_majoration / 100) * 100  # arrondi à 100 CFA

        # Vérifier si produit existe déjà (par code)
        existing_prod = db.execute(
            "SELECT id, quantite FROM produits WHERE code=? AND magasin_id=?", (code, magasin_id)
        ).fetchone()

        if existing_prod:
            # Mettre à jour stock existant
            db.execute(
                "UPDATE produits SET quantite=quantite+?, prix_achat=?, updated_at=datetime('now') WHERE id=?",
                (qte, prix_achat, existing_prod["id"])
            )
            prod_id = existing_prod["id"]
            print(f"  📦 MAJ stock : {nom} (+{qte}) → {existing_prod['quantite']+qte}")
            nb_maj += 1
        else:
            # Créer le produit
            cur2 = db.execute(
                """INSERT INTO produits (code, nom, categorie_id, prix_achat, prix_vente, quantite, quantite_min, unite, magasin_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (code, nom, cat_id, prix_achat, prix_vente, qte, max(2, qte//10), unite, magasin_id)
            )
            prod_id = cur2.lastrowid
            print(f"  ✅ Créé : [{code}] {nom} — {qte} {unite} × {prix_achat:,} CFA")
            nb_crees += 1

        # Ligne d'achat
        db.execute(
            "INSERT INTO achat_lignes (achat_id, produit_id, quantite, prix_unitaire, total) VALUES (?,?,?,?,?)",
            (achat_id, prod_id, qte, prix_achat, qte * prix_achat)
        )

        # Mouvement de stock
        db.execute(
            "INSERT INTO mouvements_stock (produit_id, type, quantite, reference, notes, magasin_id, created_at) VALUES (?,?,?,?,?,?,?)",
            (prod_id, "entree", qte, numero,
             f"Réception {devis['reference']} — {devis['fournisseur']}", magasin_id, devis["date"] + " 08:00:00")
        )

    print(f"\n  📊 Résumé : {nb_crees} produits créés, {nb_maj} stocks mis à jour")
    print(f"  💰 Total achat : {total:,} FCFA")
    return nb_crees + nb_maj


def main():
    db = get_db()
    try:
        print("\n🔧 YA MATÉRIELS DIVO — Importation du stock initial")
        print("Fournisseurs : GMS + DICOREP Inter SARL\n")

        total_produits = 0
        total_produits += import_devis(db, DEVIS_GMS, MAGASIN_ID, prix_vente_majoration=1.30)
        total_produits += import_devis(db, DEVIS_DICOREP, MAGASIN_ID, prix_vente_majoration=1.30)

        db.commit()
        print(f"\n{'='*60}")
        print(f"✅ Import terminé : {total_produits} lignes traitées")
        print(f"   Magasin : Ya Matériels Divo (ID={MAGASIN_ID})")
        print(f"   Total valeur stock : {(DEVIS_GMS['total'] + DEVIS_DICOREP['total']):,} FCFA")
        print(f"{'='*60}\n")

        # Résumé par catégorie
        cats = db.execute("""
            SELECT c.nom, COUNT(p.id) as nb, SUM(p.quantite) as total_qte, SUM(p.quantite*p.prix_achat) as valeur
            FROM produits p JOIN categories c ON p.categorie_id=c.id
            WHERE p.magasin_id=?
            GROUP BY c.nom ORDER BY valeur DESC
        """, (MAGASIN_ID,)).fetchall()

        print("📦 STOCK PAR CATÉGORIE :")
        print(f"{'Catégorie':<20} {'Réf':>5} {'Unités':>8} {'Valeur':>15}")
        print("-" * 55)
        total_val = 0
        for r in cats:
            val = r['valeur'] or 0
            total_val += val
            print(f"{r['nom']:<20} {r['nb']:>5} {r['total_qte']:>8} {val:>15,.0f} FCFA")
        print("-" * 55)
        print(f"{'TOTAL':<20} {sum(r['nb'] for r in cats):>5} {'':>8} {total_val:>15,.0f} FCFA")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
