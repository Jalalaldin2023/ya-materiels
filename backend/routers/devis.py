from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter()


class LigneDevisIn(BaseModel):
    produit_id: int
    quantite: float
    prix_unitaire: float


class DevisIn(BaseModel):
    magasin_id: int
    commercial_id: Optional[int] = None
    client_id: Optional[int] = None
    lignes: List[LigneDevisIn]
    remise: float = 0
    validite: Optional[str] = None  # date ISO
    notes: Optional[str] = None
    statut: str = "brouillon"


class StatutIn(BaseModel):
    statut: str


def gen_numero_devis(magasin_id, db):
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"DV{magasin_id}-{today}"
    count = db.execute("SELECT COUNT(*) FROM devis WHERE numero LIKE ?", (f"{prefix}%",)).fetchone()[0]
    return f"{prefix}-{count+1:03d}"


@router.get("")
def list_devis(magasin_id: int, search: str = "", statut: str = ""):
    db = get_db()
    q = """SELECT d.*, c.nom as client_nom, u.nom as commercial_nom
           FROM devis d
           LEFT JOIN clients c ON d.client_id=c.id
           LEFT JOIN utilisateurs u ON d.commercial_id=u.id
           WHERE d.magasin_id=?"""
    params = [magasin_id]
    if statut:
        q += " AND d.statut=?"
        params.append(statut)
    if search:
        q += " AND (d.numero LIKE ? OR c.nom LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY d.created_at DESC"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{did}")
def get_devis(did: int):
    db = get_db()
    d = db.execute(
        """SELECT d.*, c.nom as client_nom, c.telephone as client_tel, c.adresse as client_adresse,
                  u.nom as commercial_nom
           FROM devis d
           LEFT JOIN clients c ON d.client_id=c.id
           LEFT JOIN utilisateurs u ON d.commercial_id=u.id
           WHERE d.id=?""",
        (did,)
    ).fetchone()
    if not d:
        raise HTTPException(404, "Devis non trouvé")
    lignes = db.execute(
        """SELECT dl.*, p.nom as produit_nom, p.code as produit_code
           FROM devis_lignes dl
           JOIN produits p ON dl.produit_id=p.id
           WHERE dl.devis_id=?""",
        (did,)
    ).fetchall()
    db.close()
    return {**dict(d), "lignes": [dict(l) for l in lignes]}


@router.post("")
def create_devis(d: DevisIn):
    db = get_db()
    try:
        numero = gen_numero_devis(d.magasin_id, db)
        total_brut = sum(l.quantite * l.prix_unitaire for l in d.lignes)
        total = total_brut - d.remise
        db.execute(
            """INSERT INTO devis (numero, magasin_id, client_id, commercial_id,
               total, remise, statut, validite, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (numero, d.magasin_id, d.client_id, d.commercial_id,
             total, d.remise, d.statut, d.validite, d.notes)
        )
        did = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for l in d.lignes:
            db.execute(
                "INSERT INTO devis_lignes (devis_id, produit_id, quantite, prix_unitaire, total) VALUES (?,?,?,?,?)",
                (did, l.produit_id, l.quantite, l.prix_unitaire, l.quantite * l.prix_unitaire)
            )
        db.commit()
        return {"id": did, "numero": numero, "total": total}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/{did}/statut")
def update_statut(did: int, body: StatutIn):
    db = get_db()
    if not db.execute("SELECT id FROM devis WHERE id=?", (did,)).fetchone():
        db.close()
        raise HTTPException(404, "Devis non trouvé")
    db.execute("UPDATE devis SET statut=? WHERE id=?", (body.statut, did))
    db.commit()
    db.close()
    return {"ok": True}


@router.post("/{did}/convertir")
def convertir_en_vente(did: int):
    """Convertit un devis accepté en vente."""
    from routers.ventes import gen_numero
    db = get_db()
    try:
        d = db.execute("SELECT * FROM devis WHERE id=?", (did,)).fetchone()
        if not d:
            raise HTTPException(404, "Devis non trouvé")
        d = dict(d)
        lignes = db.execute("SELECT * FROM devis_lignes WHERE devis_id=?", (did,)).fetchall()
        lignes = [dict(l) for l in lignes]

        numero = gen_numero(d["magasin_id"], db)
        db.execute(
            """INSERT INTO ventes (numero, magasin_id, client_id, caissier_id,
               total, remise, montant_paye, mode_paiement, statut, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (numero, d["magasin_id"], d["client_id"], d["commercial_id"],
             d["total"], d["remise"], 0, "especes", "en_attente",
             f"Converti depuis devis {d['numero']}")
        )
        vid = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for l in lignes:
            db.execute(
                "INSERT INTO vente_lignes (vente_id, produit_id, quantite, prix_unitaire, total) VALUES (?,?,?,?,?)",
                (vid, l["produit_id"], l["quantite"], l["prix_unitaire"], l["total"])
            )
            db.execute(
                "UPDATE produits SET quantite=quantite-? WHERE id=?",
                (l["quantite"], l["produit_id"])
            )
            db.execute(
                "INSERT INTO mouvements_stock (produit_id, type, quantite, reference, magasin_id) VALUES (?,?,?,?,?)",
                (l["produit_id"], "sortie", l["quantite"], numero, d["magasin_id"])
            )

        db.execute("UPDATE devis SET statut='converti' WHERE id=?", (did,))
        db.commit()
        return {"id": vid, "numero": numero}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.delete("/{did}")
def delete_devis(did: int):
    db = get_db()
    if not db.execute("SELECT id FROM devis WHERE id=?", (did,)).fetchone():
        db.close()
        raise HTTPException(404, "Devis non trouvé")
    db.execute("DELETE FROM devis WHERE id=?", (did,))
    db.commit()
    db.close()
    return {"ok": True}
