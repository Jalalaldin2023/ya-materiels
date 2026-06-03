from fastapi import APIRouter
from database import get_db

router = APIRouter()


@router.get("")
def get_dashboard(magasin_id: int):
    db = get_db()

    ventes_jour = db.execute(
        "SELECT COALESCE(SUM(total),0) as total, COUNT(*) as count FROM ventes WHERE magasin_id=? AND date(created_at)=date('now')",
        (magasin_id,)
    ).fetchone()

    ventes_mois = db.execute(
        "SELECT COALESCE(SUM(total),0) as total, COUNT(*) as count FROM ventes WHERE magasin_id=? AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')",
        (magasin_id,)
    ).fetchone()

    depenses_mois = db.execute(
        "SELECT COALESCE(SUM(montant),0) as total FROM depenses WHERE magasin_id=? AND strftime('%Y-%m',date)=strftime('%Y-%m','now')",
        (magasin_id,)
    ).fetchone()

    achats_mois = db.execute(
        "SELECT COALESCE(SUM(total),0) as total FROM achats WHERE magasin_id=? AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')",
        (magasin_id,)
    ).fetchone()

    stock_bas = db.execute(
        "SELECT COUNT(*) as count FROM produits WHERE magasin_id=? AND quantite<=quantite_min",
        (magasin_id,)
    ).fetchone()

    total_produits = db.execute("SELECT COUNT(*) as count FROM produits WHERE magasin_id=?", (magasin_id,)).fetchone()

    ventes_graph = db.execute("""
        SELECT date(created_at) as date, SUM(total) as total, COUNT(*) as count
        FROM ventes WHERE magasin_id=? AND created_at>=date('now','-30 days')
        GROUP BY date(created_at) ORDER BY date
    """, (magasin_id,)).fetchall()

    top_produits = db.execute("""
        SELECT p.nom, SUM(vl.quantite) as qty_vendue, SUM(vl.total) as ca
        FROM vente_lignes vl JOIN produits p ON vl.produit_id=p.id
        JOIN ventes v ON vl.vente_id=v.id
        WHERE v.magasin_id=? AND v.created_at>=date('now','-30 days')
        GROUP BY p.id ORDER BY qty_vendue DESC LIMIT 5
    """, (magasin_id,)).fetchall()

    dernieres_ventes = db.execute("""
        SELECT v.numero, v.total, v.created_at, v.statut, c.nom as client_nom, u.nom as caissier_nom
        FROM ventes v LEFT JOIN clients c ON v.client_id=c.id
        LEFT JOIN utilisateurs u ON v.caissier_id=u.id
        WHERE v.magasin_id=? ORDER BY v.created_at DESC LIMIT 10
    """, (magasin_id,)).fetchall()

    db.close()
    benefice = ventes_mois["total"] - depenses_mois["total"] - achats_mois["total"]

    return {
        "ventes_jour": {"total": ventes_jour["total"], "count": ventes_jour["count"]},
        "ventes_mois": {"total": ventes_mois["total"], "count": ventes_mois["count"]},
        "depenses_mois": depenses_mois["total"],
        "achats_mois": achats_mois["total"],
        "benefice_mois": benefice,
        "stock_bas": stock_bas["count"],
        "total_produits": total_produits["count"],
        "ventes_graph": [dict(r) for r in ventes_graph],
        "top_produits": [dict(r) for r in top_produits],
        "dernieres_ventes": [dict(r) for r in dernieres_ventes],
    }


@router.get("/comptabilite")
def get_comptabilite(magasin_id: int):
    db = get_db()

    recettes = db.execute(
        "SELECT COALESCE(SUM(montant_paye),0) as total FROM ventes WHERE magasin_id=? AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')",
        (magasin_id,)
    ).fetchone()["total"]

    depenses = db.execute(
        "SELECT COALESCE(SUM(montant),0) as total FROM depenses WHERE magasin_id=? AND strftime('%Y-%m',date)=strftime('%Y-%m','now')",
        (magasin_id,)
    ).fetchone()["total"]

    achats_total = db.execute(
        "SELECT COALESCE(SUM(montant_paye),0) as total FROM achats WHERE magasin_id=? AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')",
        (magasin_id,)
    ).fetchone()["total"]

    ventes_par_mois = db.execute("""
        SELECT strftime('%Y-%m',created_at) as mois, SUM(total) as total
        FROM ventes WHERE magasin_id=? AND strftime('%Y',created_at)=strftime('%Y','now')
        GROUP BY mois ORDER BY mois
    """, (magasin_id,)).fetchall()

    depenses_par_cat = db.execute("""
        SELECT categorie, SUM(montant) as total FROM depenses
        WHERE magasin_id=? AND strftime('%Y-%m',date)=strftime('%Y-%m','now')
        GROUP BY categorie
    """, (magasin_id,)).fetchall()

    db.close()
    return {
        "recettes": recettes, "depenses": depenses, "achats": achats_total,
        "benefice": recettes - depenses - achats_total,
        "ventes_par_mois": [dict(r) for r in ventes_par_mois],
        "depenses_par_cat": [dict(r) for r in depenses_par_cat],
    }


@router.get("/consolidé")
def get_consolide():
    """Vue consolidée des deux magasins pour l'admin."""
    db = get_db()
    magasins = db.execute("SELECT id, nom FROM magasins ORDER BY id").fetchall()
    result = []
    for m in magasins:
        mid = m["id"]
        ventes = db.execute(
            "SELECT COALESCE(SUM(total),0) as total, COUNT(*) as count FROM ventes WHERE magasin_id=? AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')",
            (mid,)
        ).fetchone()
        depenses = db.execute(
            "SELECT COALESCE(SUM(montant),0) as total FROM depenses WHERE magasin_id=? AND strftime('%Y-%m',date)=strftime('%Y-%m','now')",
            (mid,)
        ).fetchone()
        achats = db.execute(
            "SELECT COALESCE(SUM(total),0) as total FROM achats WHERE magasin_id=? AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')",
            (mid,)
        ).fetchone()
        stock_bas = db.execute("SELECT COUNT(*) as c FROM produits WHERE magasin_id=? AND quantite<=quantite_min", (mid,)).fetchone()
        result.append({
            "id": mid, "nom": m["nom"],
            "ventes_total": ventes["total"], "ventes_count": ventes["count"],
            "depenses": depenses["total"], "achats": achats["total"],
            "benefice": ventes["total"] - depenses["total"] - achats["total"],
            "stock_bas": stock_bas["c"],
        })
    db.close()
    return result
