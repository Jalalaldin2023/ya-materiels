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
        SELECT strftime('%Y-%m', created_at) as date, SUM(total) as total, COUNT(*) as count
        FROM ventes WHERE magasin_id=? AND created_at>=date('now','-365 days')
        GROUP BY strftime('%Y-%m', created_at) ORDER BY date
    """, (magasin_id,)).fetchall()

    top_produits = db.execute("""
        SELECT p.nom, SUM(vl.quantite) as qty_vendue, SUM(vl.total) as ca
        FROM vente_lignes vl JOIN produits p ON vl.produit_id=p.id
        JOIN ventes v ON vl.vente_id=v.id
        WHERE v.magasin_id=? AND v.created_at>=date('now','-365 days')
        GROUP BY p.id ORDER BY qty_vendue DESC LIMIT 5
    """, (magasin_id,)).fetchall()

    ventes_annee = db.execute(
        "SELECT COALESCE(SUM(total),0) as total, COUNT(*) as count FROM ventes WHERE magasin_id=? AND strftime('%Y',created_at)=strftime('%Y',created_at,'start of year')",
        (magasin_id,)
    ).fetchone()

    ventes_total = db.execute(
        "SELECT COALESCE(SUM(total),0) as total, COUNT(*) as count FROM ventes WHERE magasin_id=?",
        (magasin_id,)
    ).fetchone()

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
        "ventes_total": {"total": ventes_total["total"], "count": ventes_total["count"]},
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
def get_comptabilite(magasin_id: int, annee: str = ""):
    db = get_db()

    # Filtre de période : année spécifique ou mois courant pour les KPIs
    if annee and annee != "all":
        yr_filter_v  = f" AND strftime('%Y',created_at)='{annee}'"
        yr_filter_d  = f" AND strftime('%Y',date)='{annee}'"
    elif annee == "all":
        yr_filter_v  = ""
        yr_filter_d  = ""
    else:
        yr_filter_v  = " AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')"
        yr_filter_d  = " AND strftime('%Y-%m',date)=strftime('%Y-%m','now')"

    recettes = db.execute(
        f"SELECT COALESCE(SUM(montant_paye),0) as total FROM ventes WHERE magasin_id=?{yr_filter_v}",
        (magasin_id,)
    ).fetchone()["total"]

    depenses = db.execute(
        f"SELECT COALESCE(SUM(montant),0) as total FROM depenses WHERE magasin_id=?{yr_filter_d}",
        (magasin_id,)
    ).fetchone()["total"]

    achats_total = db.execute(
        f"SELECT COALESCE(SUM(montant_paye),0) as total FROM achats WHERE magasin_id=?{yr_filter_v.replace('created_at','created_at')}",
        (magasin_id,)
    ).fetchone()["total"]

    # Ventes par mois (toutes années disponibles ou filtrées)
    if annee and annee != "all":
        ventes_par_mois = db.execute(
            "SELECT strftime('%Y-%m',created_at) as mois, SUM(total) as total FROM ventes WHERE magasin_id=? AND strftime('%Y',created_at)=? GROUP BY mois ORDER BY mois",
            (magasin_id, annee)
        ).fetchall()
    else:
        ventes_par_mois = db.execute(
            "SELECT strftime('%Y-%m',created_at) as mois, SUM(total) as total FROM ventes WHERE magasin_id=? GROUP BY mois ORDER BY mois",
            (magasin_id,)
        ).fetchall()

    depenses_par_cat = db.execute(
        f"SELECT categorie, SUM(montant) as total FROM depenses WHERE magasin_id=?{yr_filter_d} GROUP BY categorie",
        (magasin_id,)
    ).fetchall()

    # Balance comptable : toutes données mensuelle (ventes + achats + dépenses)
    if annee and annee != "all":
        balance_rows = db.execute("""
            SELECT mois,
                   COALESCE(SUM(recettes),0) as recettes,
                   COALESCE(SUM(achats),0)   as achats,
                   COALESCE(SUM(dep),0)      as depenses
            FROM (
                SELECT strftime('%Y-%m',created_at) as mois, SUM(montant_paye) as recettes, 0 as achats, 0 as dep
                FROM ventes WHERE magasin_id=? AND strftime('%Y',created_at)=?
                GROUP BY strftime('%Y-%m',created_at)
                UNION ALL
                SELECT strftime('%Y-%m',created_at), 0, SUM(montant_paye), 0
                FROM achats WHERE magasin_id=? AND strftime('%Y',created_at)=?
                GROUP BY strftime('%Y-%m',created_at)
                UNION ALL
                SELECT strftime('%Y-%m',date), 0, 0, SUM(montant)
                FROM depenses WHERE magasin_id=? AND strftime('%Y',date)=?
                GROUP BY strftime('%Y-%m',date)
            ) GROUP BY mois ORDER BY mois
        """, (magasin_id, annee, magasin_id, annee, magasin_id, annee)).fetchall()
    else:
        balance_rows = db.execute("""
            SELECT mois,
                   COALESCE(SUM(recettes),0) as recettes,
                   COALESCE(SUM(achats),0)   as achats,
                   COALESCE(SUM(dep),0)      as depenses
            FROM (
                SELECT strftime('%Y-%m',created_at) as mois, SUM(montant_paye) as recettes, 0 as achats, 0 as dep
                FROM ventes WHERE magasin_id=? GROUP BY strftime('%Y-%m',created_at)
                UNION ALL
                SELECT strftime('%Y-%m',created_at), 0, SUM(montant_paye), 0
                FROM achats WHERE magasin_id=? GROUP BY strftime('%Y-%m',created_at)
                UNION ALL
                SELECT strftime('%Y-%m',date), 0, 0, SUM(montant)
                FROM depenses WHERE magasin_id=? GROUP BY strftime('%Y-%m',date)
            ) GROUP BY mois ORDER BY mois
        """, (magasin_id, magasin_id, magasin_id)).fetchall()

    # Années disponibles pour le sélecteur
    annees_dispo = db.execute(
        "SELECT DISTINCT strftime('%Y',created_at) as yr FROM ventes WHERE magasin_id=? ORDER BY yr DESC",
        (magasin_id,)
    ).fetchall()

    db.close()

    # Calcul solde cumulé
    balance = []
    cumul = 0.0
    for r in balance_rows:
        resultat = r["recettes"] - r["achats"] - r["depenses"]
        cumul += resultat
        balance.append({
            "mois": r["mois"],
            "recettes": r["recettes"],
            "achats": r["achats"],
            "depenses": r["depenses"],
            "resultat": resultat,
            "solde_cumul": cumul,
        })

    return {
        "recettes": recettes, "depenses": depenses, "achats": achats_total,
        "benefice": recettes - depenses - achats_total,
        "ventes_par_mois": [dict(r) for r in ventes_par_mois],
        "depenses_par_cat": [dict(r) for r in depenses_par_cat],
        "balance": balance,
        "annees_dispo": [r["yr"] for r in annees_dispo],
        "annee_selectionnee": annee or "mois",
    }


@router.get("/journal")
def get_journal(magasin_id: int, annee: str = "", mois: str = ""):
    db = get_db()

    def yr_clause_v(field="created_at"):
        if mois: return f" AND strftime('%Y-%m',{field})='{mois}'"
        if annee and annee != "all": return f" AND strftime('%Y',{field})='{annee}'"
        return ""

    # Ventes → Débit 531 Caisse / Crédit 701 Ventes
    ventes = db.execute(f"""
        SELECT date(v.created_at) as date, v.numero as piece, v.montant_paye as montant,
               COALESCE(c.nom,'Comptant') as tiers, v.notes
        FROM ventes v LEFT JOIN clients c ON v.client_id=c.id
        WHERE v.magasin_id=?{yr_clause_v()} AND v.montant_paye>0
        ORDER BY v.created_at
    """, (magasin_id,)).fetchall()

    # Achats → Débit 601 Achats / Crédit 531 Caisse
    achats = db.execute(f"""
        SELECT date(a.created_at) as date, a.numero as piece, a.montant_paye as montant,
               COALESCE(f.nom,'Fournisseur') as tiers, a.notes
        FROM achats a LEFT JOIN fournisseurs f ON a.fournisseur_id=f.id
        WHERE a.magasin_id=?{yr_clause_v()} AND a.montant_paye>0
        ORDER BY a.created_at
    """, (magasin_id,)).fetchall()

    # Dépenses → Débit 614 Charges / Crédit 531 Caisse
    depenses = db.execute(f"""
        SELECT date, description||' ('||categorie||')' as piece,
               montant, 'Divers' as tiers, notes
        FROM depenses WHERE magasin_id=?{yr_clause_v('date')} AND montant>0
        ORDER BY date
    """, (magasin_id,)).fetchall()

    db.close()

    entries = []
    for v in ventes:
        entries.append({"date": v["date"], "piece": v["piece"],
                        "compte_debit": "531", "libelle_debit": "Caisse",
                        "compte_credit": "701", "libelle_credit": "Ventes de marchandises",
                        "tiers": v["tiers"], "montant": v["montant"], "type": "vente"})
    for a in achats:
        entries.append({"date": a["date"], "piece": a["piece"],
                        "compte_debit": "601", "libelle_debit": "Achats de marchandises",
                        "compte_credit": "531", "libelle_credit": "Caisse",
                        "tiers": a["tiers"], "montant": a["montant"], "type": "achat"})
    for dep in depenses:
        entries.append({"date": dep["date"], "piece": dep["piece"],
                        "compte_debit": "614", "libelle_debit": "Charges et dépenses",
                        "compte_credit": "531", "libelle_credit": "Caisse",
                        "tiers": dep["tiers"], "montant": dep["montant"], "type": "depense"})

    entries.sort(key=lambda x: x["date"])
    return entries


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
