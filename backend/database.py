import sqlite3
import os
import hashlib

# En production, stocker la DB dans /data (volume persistant Render)
_data_dir = os.environ.get("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(_data_dir, "quincaillerie.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS magasins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            slogan TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            rccm TEXT DEFAULT '',
            nif TEXT DEFAULT '',
            logo TEXT DEFAULT '',
            devise TEXT DEFAULT 'FCFA',
            theme_primary TEXT DEFAULT '#1a56db',
            theme_sidebar TEXT DEFAULT '#1e293b',
            recu_pied TEXT DEFAULT 'Merci pour votre achat !',
            actif INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'caissier',
            magasin_id INTEGER REFERENCES magasins(id),
            actif INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(nom, magasin_id)
        );

        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            nom TEXT NOT NULL,
            description TEXT,
            categorie_id INTEGER REFERENCES categories(id),
            fournisseur_id INTEGER REFERENCES fournisseurs(id),
            prix_achat REAL DEFAULT 0,
            prix_vente REAL NOT NULL,
            quantite INTEGER DEFAULT 0,
            quantite_min INTEGER DEFAULT 5,
            unite TEXT DEFAULT 'pcs',
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(code, magasin_id)
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            solde REAL DEFAULT 0,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            client_id INTEGER REFERENCES clients(id),
            total REAL NOT NULL,
            remise REAL DEFAULT 0,
            montant_paye REAL DEFAULT 0,
            mode_paiement TEXT DEFAULT 'especes',
            statut TEXT DEFAULT 'payee',
            notes TEXT,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            caissier_id INTEGER REFERENCES utilisateurs(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS vente_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vente_id INTEGER NOT NULL REFERENCES ventes(id) ON DELETE CASCADE,
            produit_id INTEGER NOT NULL REFERENCES produits(id),
            quantite INTEGER NOT NULL,
            prix_unitaire REAL NOT NULL,
            total REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS achats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            fournisseur_id INTEGER REFERENCES fournisseurs(id),
            total REAL NOT NULL,
            montant_paye REAL DEFAULT 0,
            statut TEXT DEFAULT 'paye',
            notes TEXT,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS achat_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            achat_id INTEGER NOT NULL REFERENCES achats(id) ON DELETE CASCADE,
            produit_id INTEGER NOT NULL REFERENCES produits(id),
            quantite INTEGER NOT NULL,
            prix_unitaire REAL NOT NULL,
            total REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            montant REAL NOT NULL,
            categorie TEXT DEFAULT 'autre',
            date TEXT DEFAULT (date('now')),
            notes TEXT,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mouvements_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id INTEGER NOT NULL REFERENCES produits(id),
            type TEXT NOT NULL,
            quantite INTEGER NOT NULL,
            reference TEXT,
            notes TEXT,
            magasin_id INTEGER NOT NULL REFERENCES magasins(id),
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # ── Migrations : nouvelles colonnes sur table existante ─────────────────
    migrations = [
        ("produits",     "prix_vente2",  "ALTER TABLE produits ADD COLUMN prix_vente2 REAL DEFAULT 0"),
        ("produits",     "prix_vente3",  "ALTER TABLE produits ADD COLUMN prix_vente3 REAL DEFAULT 0"),
        ("produits",     "transport",    "ALTER TABLE produits ADD COLUMN transport REAL DEFAULT 0"),
        ("produits",     "manutention",  "ALTER TABLE produits ADD COLUMN manutention REAL DEFAULT 0"),
        ("utilisateurs", "permissions",  "ALTER TABLE utilisateurs ADD COLUMN permissions TEXT DEFAULT ''"),
        ("magasins",     "photo",        "ALTER TABLE magasins ADD COLUMN photo TEXT DEFAULT ''"),
    ]
    for table, col, sql in migrations:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            cur.execute(sql)

    # ── Magasins par défaut ──────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM magasins")
    if cur.fetchone()[0] == 0:
        magasins = [
            ("Ya Matériels Divo",       "Votre quincaillerie de confiance", "Divo, Côte d'Ivoire"),
            ("Ya Matériels Yamoussoukro","Votre quincaillerie de confiance", "Yamoussoukro, Côte d'Ivoire"),
        ]
        for nom, slogan, adresse in magasins:
            cur.execute(
                "INSERT INTO magasins (nom, slogan, adresse) VALUES (?,?,?)",
                (nom, slogan, adresse)
            )

    # ── Utilisateurs par défaut ──────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM utilisateurs")
    if cur.fetchone()[0] == 0:
        # Admin unique (magasin_id NULL = accès aux deux)
        cur.execute(
            "INSERT INTO utilisateurs (nom, username, password, role, magasin_id) VALUES (?,?,?,?,?)",
            ("Administrateur", "admin", hash_pwd("admin123"), "admin", None)
        )
        # Caissier Divo
        cur.execute(
            "INSERT INTO utilisateurs (nom, username, password, role, magasin_id) VALUES (?,?,?,?,?)",
            ("Caissier Divo", "caissier.divo", hash_pwd("caisse123"), "caissier", 1)
        )
        # Caissier Yamoussoukro
        cur.execute(
            "INSERT INTO utilisateurs (nom, username, password, role, magasin_id) VALUES (?,?,?,?,?)",
            ("Caissier Yamoussoukro", "caissier.yam", hash_pwd("caisse123"), "caissier", 2)
        )

    # ── Catégories par défaut pour chaque magasin ───────────────────────────
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        cats = ["Outils", "Visserie", "Plomberie", "Électricité", "Peinture", "Bois", "Quincaillerie", "Autre"]
        cur.execute("SELECT id FROM magasins")
        mag_ids = [r[0] for r in cur.fetchall()]
        for mid in mag_ids:
            cur.executemany(
                "INSERT OR IGNORE INTO categories (nom, magasin_id) VALUES (?,?)",
                [(c, mid) for c in cats]
            )

    conn.commit()
    conn.close()
