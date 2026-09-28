from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, urllib.request, urllib.parse, json
from database import get_db

router = APIRouter()

AT_API_KEY   = os.environ.get("AT_API_KEY", "")
AT_USERNAME  = os.environ.get("AT_USERNAME", "sandbox")
AT_SENDER_ID = os.environ.get("AT_SENDER_ID", "")   # optionnel, laissé vide = numéro AT


class SMSRequest(BaseModel):
    client_ids: List[int]          # liste d'ids, vide = tous les clients du magasin
    message: str
    magasin_id: int


def _send_at(numero: str, message: str) -> dict:
    """Envoie un SMS via Africa's Talking."""
    if not AT_API_KEY or not AT_USERNAME:
        return {"status": "mock", "detail": "Clé AT_API_KEY non configurée — mode simulation"}

    # Normaliser le numéro ivoirien → +225XXXXXXXXXX
    n = numero.strip().replace(" ", "").replace("-", "")
    if n.startswith("0") and len(n) == 10:
        n = "+225" + n[1:]
    elif not n.startswith("+"):
        n = "+225" + n

    params = {
        "username": AT_USERNAME,
        "to":       n,
        "message":  message,
    }
    if AT_SENDER_ID:
        params["from"] = AT_SENDER_ID

    data = urllib.parse.urlencode(params).encode()
    req  = urllib.request.Request(
        "https://api.africastalking.com/version1/messaging",
        data=data,
        headers={"apiKey": AT_API_KEY, "Accept": "application/json",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


@router.post("/envoyer")
def envoyer_sms(req: SMSRequest):
    if not req.message.strip():
        raise HTTPException(400, "Message vide")

    db = get_db()

    # Récupérer les clients cibles avec numéro de téléphone
    if req.client_ids:
        placeholders = ",".join("?" * len(req.client_ids))
        clients = db.execute(
            f"SELECT id, nom, telephone FROM clients WHERE id IN ({placeholders}) AND magasin_id=? AND telephone IS NOT NULL AND telephone != ''",
            (*req.client_ids, req.magasin_id)
        ).fetchall()
    else:
        clients = db.execute(
            "SELECT id, nom, telephone FROM clients WHERE magasin_id=? AND telephone IS NOT NULL AND telephone != ''",
            (req.magasin_id,)
        ).fetchall()

    if not clients:
        db.close()
        raise HTTPException(404, "Aucun client avec numéro de téléphone trouvé")

    sent, failed, details = 0, 0, []
    for c in clients:
        result = _send_at(c["telephone"], req.message)
        ok = "error" not in result and result.get("status") in ("mock", None) or \
             "SMSMessageData" in result

        statut = "envoye" if (ok or result.get("status") == "mock") else "echec"
        db.execute(
            "INSERT INTO sms_logs (client_id, telephone, message, statut, magasin_id) VALUES (?,?,?,?,?)",
            (c["id"], c["telephone"], req.message, statut, req.magasin_id)
        )
        if statut == "envoye":
            sent += 1
        else:
            failed += 1
        details.append({"client": c["nom"], "tel": c["telephone"], "statut": statut})

    db.commit()
    db.close()
    return {"sent": sent, "failed": failed, "total": len(clients), "details": details}


@router.get("/historique")
def historique_sms(magasin_id: int, limit: int = 100):
    db = get_db()
    rows = db.execute(
        """SELECT s.id, s.telephone, s.message, s.statut, s.created_at,
                  c.nom as client_nom
           FROM sms_logs s
           LEFT JOIN clients c ON c.id = s.client_id
           WHERE s.magasin_id=?
           ORDER BY s.created_at DESC LIMIT ?""",
        (magasin_id, limit)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/stats")
def stats_sms(magasin_id: int):
    db = get_db()
    row = db.execute(
        """SELECT COUNT(*) as total,
                  SUM(CASE WHEN statut='envoye' THEN 1 ELSE 0 END) as envoyes,
                  SUM(CASE WHEN statut='echec'  THEN 1 ELSE 0 END) as echecs
           FROM sms_logs WHERE magasin_id=?""",
        (magasin_id,)
    ).fetchone()
    db.close()
    return dict(row)
