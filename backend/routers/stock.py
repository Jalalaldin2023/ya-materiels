from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class AjustementIn(BaseModel):
    produit_id: int
    quantite: int
    type: str = "ajustement"
    notes: Optional[str] = None
    magasin_id: int


@router.get("/mouvements")
def list_mouvements(magasin_id: int, produit_id: int = 0, limit: int = 100):
    db = get_db()
    q = """SELECT m.*, p.nom as produit_nom, p.code as produit_code
           FROM mouvements_stock m JOIN produits p ON m.produit_id=p.id
           WHERE m.magasin_id=?"""
    params = [magasin_id]
    if produit_id:
        q += " AND m.produit_id=?"; params.append(produit_id)
    q += " ORDER BY m.created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/alertes")
def alertes_stock(magasin_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM produits WHERE magasin_id=? AND quantite<=quantite_min ORDER BY quantite ASC",
        (magasin_id,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/rapport")
def rapport_stock(magasin_id: int):
    """Rapport stock : entrées, sorties, stock final par produit."""
    db = get_db()
    rows = db.execute("""
        SELECT
            p.id, p.code, p.nom, p.unite,
            c.nom as categorie,
            p.prix_achat,
            p.prix_vente  as pv1,
            p.prix_vente2 as pv2,
            p.prix_vente3 as pv3,
            p.quantite    as stock_final,
            p.quantite_min,
            COALESCE(SUM(CASE WHEN m.type='entree' THEN m.quantite ELSE 0 END), 0) as total_entrees,
            COALESCE(SUM(CASE WHEN m.type='sortie' THEN m.quantite ELSE 0 END), 0) as total_sorties
        FROM produits p
        LEFT JOIN categories c ON p.categorie_id = c.id
        LEFT JOIN mouvements_stock m ON m.produit_id = p.id AND m.magasin_id = p.magasin_id
        WHERE p.magasin_id = ?
        GROUP BY p.id
        ORDER BY c.nom, p.nom
    """, (magasin_id,)).fetchall()
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        # Coût de revient = prix_achat × stock_final
        d['cout_revient'] = (d['prix_achat'] or 0) * (d['stock_final'] or 0)
        # Valeur stock PV1
        d['valeur_pv1'] = (d['pv1'] or 0) * (d['stock_final'] or 0)
        # Marge brute PV1
        d['marge_pv1'] = round(((d['pv1'] or 0) - (d['prix_achat'] or 0)) / (d['pv1'] or 1) * 100, 1) if d['pv1'] else 0
        result.append(d)
    return result


@router.post("/ajustement")
def ajuster_stock(a: AjustementIn):
    db = get_db()
    try:
        if a.type == "entree":
            db.execute("UPDATE produits SET quantite=quantite+?,updated_at=datetime('now') WHERE id=?", (a.quantite, a.produit_id))
        elif a.type == "sortie":
            db.execute("UPDATE produits SET quantite=quantite-?,updated_at=datetime('now') WHERE id=?", (a.quantite, a.produit_id))
        else:
            db.execute("UPDATE produits SET quantite=?,updated_at=datetime('now') WHERE id=?", (a.quantite, a.produit_id))
        db.execute(
            "INSERT INTO mouvements_stock (produit_id,type,quantite,notes,magasin_id) VALUES (?,?,?,?,?)",
            (a.produit_id, a.type, a.quantite, a.notes, a.magasin_id)
        )
        db.commit()
        return {"message": "Stock ajusté"}
    finally:
        db.close()
