"""
Agent Sydia - Interface Web

Tout en un seul fichier. Dynamique depuis l'API Sydia.

Usage:
    pipenv run python app.py
"""

import os
import json
import asyncio
import httpx
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from openai import AzureOpenAI


MODELES_MAIL_SYDIA = {
    "adversaire_reclamation": 744,
    "demande_rib": 1584,
    "documents_manquants": 740,
    "relance_declaration": 1258,
}

TYPES_EVENEMENTS = {
    # ===== Autre =====
    "affectation_gestionnaire": 316,
    "assignation": 219,
    "autre": 12,
    "controle_audit": 112,
    "declaration": 178,
    "declaration_compagnie": 54,
    "fermeture": 13,
    "ouverture": 3,
    "pli_non_distribue": 308,
    "reouverture": 91,
    "revision": 113,
    "suspicion_gel": 224,
    "transfert_gestionnaire": 317,
    "transfert_dossier": 62,
    
    # ===== Comptabilité =====
    "encaissement": 315,
    "reglement_attente": 117,
    "reglement_valide": 56,
    "paiement": 56,
    
    # ===== Conformité =====
    "avis_technique": 131,
    "avis_technique_demande": 175,
    "dossier_complet": 120,
    "garantie": 179,
    "piece_manquante": 121,
    "pieces_manquantes": 121,
    "prise_en_charge": 247,
    
    # ===== Expertise =====
    "conclusions_techniques": 116,
    "expertise": 55,
    "mission_expert": 215,
    "rapport_expertise": 27,
    "expert": 55,
    
    # ===== Mails/Courriers/Tél =====
    "appel": 4,
    "appel_telephonique": 4,
    "courrier": 11,
    "courrier_lrar": 11,
    "email_envoye": 85,
    "envoi_email": 85,
    "sms_envoye": 89,
    "envoi_sms": 89,
    "email_recu": 84,
    "reception_email": 84,
    "sms_recu": 90,
    "reception_sms": 90,
    "reclamation_materielle": 217,
    
    # ===== PJ Ouverture =====
    "reception_declaration": 41,
    
    # ===== Réclamation =====
    "reclamation": 60,
    "reponse_reclamation": 61,
}

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sydia-mcp-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

azure_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
)
MODEL = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4.1-nano")

SYDIA_URL = os.getenv("SYDIA_API_URL", "https://preprod.sydia.fr")
SYDIA_TOKEN = os.getenv("SYDIA_API_TOKEN", "")

conversations = {}


async def sydia_call(endpoint: str, data: dict = None) -> dict:
    """Appelle l'API Sydia"""
    if data is None:
        data = {}
    data["token"] = SYDIA_TOKEN
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SYDIA_URL}/api/v2/{endpoint}",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
    return response.json()


async def get_sinistre(id_sinistre: int = None, ref_sinistre: str = None) -> dict:
    """Récupère un sinistre"""
    data = {}
    if id_sinistre:
        data["id_sinistre"] = str(id_sinistre)
    if ref_sinistre:
        data["ref_sinistre"] = ref_sinistre
    
    response = await sydia_call("sinistre/get", data)
    
    if response.get("status") == 200:
        return {"success": True, "data": response.get("data", {})}
    return {"success": False, "error": response.get("message", "Erreur")}


async def list_sinistres() -> dict:
    """Liste les sinistres"""
    response = await sydia_call("sinistre/list")
    
    if response.get("status") == 200:
        return {"success": True, "data": response.get("data", [])}
    return {"success": False, "error": response.get("message", "Erreur")}


async def add_sinistre(
    type_sinistre: int,
    date_sinistre: str,
    ville: str,
    cp: str,
    circonstances: str,
    nom: str,
    prenom: str,
    email: str,
    tel: str,
    immatriculation: str = "AA-000-AA"
) -> dict:
    """Déclare un nouveau sinistre"""
    import time
    ref_sinistre = f"MCP-{int(time.time())}"
    
    data = {
        "type_ouverture": "1",
        "type_sinistre": str(type_sinistre),
        "nature_sinistre": "1",
        "ref_sinistre": ref_sinistre,
        "sinistre[date_sinistre]": date_sinistre,
        "sinistre[ville]": ville,
        "sinistre[cp]": cp,
        "sinistre[circonstances]": circonstances,
        "sinistre[pays]": "FR",
        "sinistre[immatriculation]": immatriculation,
        "assure[statut]": "1",
        "assure[nom]": nom,
        "assure[prenom]": prenom,
        "assure[email]": email,
        "assure[tel1]": tel,
        "assure[ref_assure]": f"ASS-{tel[-4:]}",
        "assure[police]": "123456",
    }
    
    response = await sydia_call("sinistre/add", data)
    
    print(f"DEBUG add_sinistre response: {response}")
    
    if response.get("status") == 200:
        return {
            "success": True,
            "id_sinistre": response.get("id_sinistre"),
            "reference": response.get("reference") or ref_sinistre,
            "id_assure": response.get("id_assure")
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def list_documents(id_sinistre: int) -> dict:
    """Liste les documents d'un sinistre"""
    data = {
        "id_sinistre": str(id_sinistre)
    }
    
    response = await sydia_call("ged/list", data)
    
    print(f"DEBUG list_documents response: {response}")
    
    if response.get("status") == 200:
        data_obj = response.get("data", {})
        return {
            "success": True,
            "count": data_obj.get("count", 0),
            "documents": data_obj.get("geds", [])
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def get_document(id_ged: int) -> dict:
    """Récupère un document"""
    data = {
        "id_ged": str(id_ged)
    }
    
    response = await sydia_call("ged/get", data)
    
    print(f"DEBUG get_document response: {response}")
    
    if response.get("status") == 200:
        return {
            "success": True,
            "data": response.get("data", response)
        }
    if response.get("id_ged"):
        return {
            "success": True,
            "data": response
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def add_document(
    id_sinistre: int,
    filename: str,
    commentaire: str = "",
    content_text: str = ""
) -> dict:
    """Ajoute un document à un sinistre"""
    import base64
    
    if content_text:
        content_base64 = base64.b64encode(content_text.encode('utf-8')).decode('utf-8')
    else:
        content_base64 = base64.b64encode(b"Document vide").decode('utf-8')
    
    data = {
        "id_sinistre": str(id_sinistre),
        "filename": filename,
        "commentaire": commentaire,
        "content": content_base64,
        "public": "1",
        "notif_gestionnaire": "1",
    }
    
    response = await sydia_call("ged/add", data)
    
    print(f"DEBUG add_document response: {response}")
    
    if response.get("status") == 200:
        return {
            "success": True,
            "id_ged": response.get("id_ged"),
            "id_assure": response.get("id_assure")
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def update_assure(id_assure: int, **kwargs) -> dict:
    """Modifie les informations d'un assuré"""
    data = {
        "id_assure": str(id_assure)
    }

    champs_possibles = [
        "nom", "prenom", "email", "tel1", "tel2", 
        "adresse", "cp", "ville", "pays",
        "civilite", "naissance", "statut", "etat",
        "iban", "bic", "commentaire"
    ]
    
    for champ in champs_possibles:
        if champ in kwargs and kwargs[champ]:
            data[champ] = str(kwargs[champ])
    
    print(f"DEBUG update_assure data: {data}")
    
    response = await sydia_call("assure/update", data)
    
    print(f"DEBUG update_assure response: {response}")
    
    if response.get("status") == 200 or response.get("id_assure"):
        return {
            "success": True,
            "id_assure": response.get("id_assure") or id_assure
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def contact_gestionnaire(
    id_sinistre: int,
    type_demande: int,
    objet: str,
    commentaire: str = "",
    urgence: int = 1,
    rappel_preference: str = ""
) -> dict:
    """Contacte le gestionnaire du dossier et crée une tâche"""
    data = {
        "id_sinistre": str(id_sinistre),
        "type": str(type_demande),
        "objet": objet,
        "commentaire": commentaire,
        "urgence": str(urgence)
    }
    
    if type_demande == 1 and rappel_preference:
        data["rappel_preference"] = rappel_preference
    
    print(f"DEBUG contact_gestionnaire data: {data}")
    
    response = await sydia_call("sinistre/contact", data)
    
    print(f"DEBUG contact_gestionnaire response: {response}")
    
    if response.get("status") == 200 or response.get("id_tache"):
        return {
            "success": True,
            "id_tache": response.get("id_tache")
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def cloturer_sinistre(
    id_sinistre: int,
    date_fermeture: str,
    raison: int,
    commentaire: str = ""
) -> dict:
    """Clôture un sinistre"""
    data = {
        "id_sinistre": str(id_sinistre),
        "date_fermeture": date_fermeture,
        "raison": str(raison),
        "commentaire": commentaire
    }
    
    print(f"DEBUG cloturer_sinistre data: {data}")
    
    response = await sydia_call("sinistre/cloturer", data)
    
    print(f"DEBUG cloturer_sinistre response: {response}")
    
    if response.get("status") == 200 or response.get("id_sinistre"):
        return {
            "success": True,
            "id_sinistre": response.get("id_sinistre") or id_sinistre
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def list_reglements(
    status: int = None,
    sens: int = None,
    limit: int = 50
) -> dict:
    """Liste les règlements"""
    data = {
        "limit": str(limit)
    }
    
    if status is not None:
        data["status"] = str(status)
    if sens is not None:
        data["sens"] = str(sens)
    
    print(f"DEBUG list_reglements data: {data}")
    
    response = await sydia_call("sinistre/reglement/list", data)
    
    print(f"DEBUG list_reglements response: {response}")
    
    if response.get("status") == 200:
        return {
            "success": True,
            "data": response.get("data", [])
        }
    if isinstance(response, list):
        return {
            "success": True,
            "data": response
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def get_checklist(id_sinistre: int) -> dict:
    """Récupère la checklist des pièces requises pour un sinistre"""
    data = {
        "id_sinistre": str(id_sinistre)
    }
    
    print(f"DEBUG get_checklist data: {data}") 
    
    response = await sydia_call("sinistre/checklist/get", data)
    
    print(f"DEBUG get_checklist response: {response}")
    
    if response.get("status") == 200:
        return {
            "success": True,
            "checklist": response.get("data", {}).get("checklist", [])
        }
    if response.get("checklist"):
        return {
            "success": True,
            "checklist": response.get("checklist", [])
        }
    return {"success": False, "error": response.get("message", f"Erreur: {response}")}


async def generate_document(
    id_type: int,
    id_sinistre: int = None,
    id_assure: int = None,
    id_contrat: int = None
) -> dict:
    """Génère un document PDF (attestation, courrier, etc.)"""
    data = {
        "id_type": str(id_type),
        "token": SYDIA_TOKEN
    }
    
    if id_sinistre:
        data["id_sinistre"] = str(id_sinistre)
    if id_assure:
        data["id_assure"] = str(id_assure)
    if id_contrat:
        data["id_contrat"] = str(id_contrat)
    
    print(f"DEBUG generate_document data: {data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SYDIA_URL}/api/v2/ged/document/get",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        
        print(f"DEBUG generate_document status: {response.status_code}")
        print(f"DEBUG generate_document content-type: {response.headers.get('content-type')}")
        
        # Essayer de parser en JSON
        try:
            result = response.json()
            print(f"DEBUG generate_document response: {result}")
            
            if result.get("filename"):
                return {
                    "success": True,
                    "filename": result.get("filename"),
                    "size": result.get("size"),
                    "content": result.get("content")
                }
            if result.get("status") == 500:
                return {"success": False, "error": result.get("message", "Erreur")}
            return {
                "success": True,
                "data": result
            }
        except:
            if response.status_code == 200:
                return {
                    "success": True,
                    "filename": "document.pdf",
                    "size": len(response.content),
                    "content": response.content  # Binary
                }
            return {"success": False, "error": f"Erreur HTTP {response.status_code}"}
    except Exception as e:
        print(f"DEBUG generate_document error: {e}")
        return {"success": False, "error": str(e)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "identifier_assure",
            "description": "Identifie et authentifie un assuré par son nom, prénom et référence de sinistre. Utiliser AVANT d'afficher les infos sensibles d'un dossier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nom": {
                        "type": "string",
                        "description": "Nom de famille de l'assuré"
                    },
                    "prenom": {
                        "type": "string",
                        "description": "Prénom de l'assuré"
                    },
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre (ex: E0025151284)"
                    }
                },
                "required": ["nom", "prenom", "ref_sinistre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sinistre",
            "description": "Récupère les informations d'un sinistre depuis Sydia (après identification)",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_sinistre": {
                        "type": "integer",
                        "description": "L'ID du sinistre (ex: 221003)"
                    },
                    "ref_sinistre": {
                        "type": "string",
                        "description": "La référence du sinistre (ex: E0025151284)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_sinistres",
            "description": "Liste les sinistres disponibles",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Nombre de sinistres (défaut: 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_sinistre",
            "description": "Déclare un nouveau sinistre. Demander toutes les infos nécessaires avant d'appeler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type_sinistre": {
                        "type": "integer",
                        "description": "Type: 1=AUTO, 2=MRH, 3=PROTECTION JURIDIQUE, 4=AFFINITAIRE, 5=RC, 6=NVEI"
                    },
                    "date_sinistre": {
                        "type": "string",
                        "description": "Date du sinistre au format YYYY-MM-DD"
                    },
                    "ville": {
                        "type": "string",
                        "description": "Ville où s'est produit le sinistre"
                    },
                    "cp": {
                        "type": "string",
                        "description": "Code postal"
                    },
                    "circonstances": {
                        "type": "string",
                        "description": "Description des circonstances du sinistre"
                    },
                    "immatriculation": {
                        "type": "string",
                        "description": "Plaque d'immatriculation du véhicule (OBLIGATOIRE pour sinistre AUTO)"
                    },
                    "nom": {
                        "type": "string",
                        "description": "Nom de l'assuré"
                    },
                    "prenom": {
                        "type": "string",
                        "description": "Prénom de l'assuré"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email de l'assuré"
                    },
                    "tel": {
                        "type": "string",
                        "description": "Téléphone de l'assuré"
                    }
                },
                "required": ["type_sinistre", "date_sinistre", "ville", "cp", "circonstances", "nom", "prenom", "email", "tel", "immatriculation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_document",
            "description": "Ajoute un document/pièce à un sinistre (constat, carte grise, facture, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_sinistre": {
                        "type": "integer",
                        "description": "ID du sinistre auquel ajouter le document"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Nom du fichier avec extension (ex: constat.pdf, carte_grise.jpg)"
                    },
                    "commentaire": {
                        "type": "string",
                        "description": "Description du document (ex: Constat amiable, Carte grise du véhicule)"
                    },
                    "content_text": {
                        "type": "string",
                        "description": "Contenu texte du document (pour les notes ou commentaires)"
                    }
                },
                "required": ["id_sinistre", "filename", "commentaire"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "Liste les documents/pièces d'un sinistre",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_sinistre": {
                        "type": "integer",
                        "description": "ID du sinistre"
                    }
                },
                "required": ["id_sinistre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_document",
            "description": "Récupère les détails d'un document spécifique",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_ged": {
                        "type": "integer",
                        "description": "ID du document en GED"
                    }
                },
                "required": ["id_ged"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_assure",
            "description": "Modifie les informations d'un assuré (téléphone, email, adresse, etc.). Utiliser la référence du sinistre pour identifier l'assuré.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre pour identifier l'assuré (ex: MCP-1766592530)"
                    },
                    "nom": {
                        "type": "string",
                        "description": "Nouveau nom"
                    },
                    "prenom": {
                        "type": "string",
                        "description": "Nouveau prénom"
                    },
                    "email": {
                        "type": "string",
                        "description": "Nouvelle adresse email"
                    },
                    "tel1": {
                        "type": "string",
                        "description": "Nouveau numéro de téléphone principal"
                    },
                    "tel2": {
                        "type": "string",
                        "description": "Nouveau numéro de téléphone secondaire"
                    },
                    "adresse": {
                        "type": "string",
                        "description": "Nouvelle adresse postale"
                    },
                    "cp": {
                        "type": "string",
                        "description": "Nouveau code postal"
                    },
                    "ville": {
                        "type": "string",
                        "description": "Nouvelle ville"
                    }
                },
                "required": ["ref_sinistre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "contact_gestionnaire",
            "description": "Contacte le gestionnaire du dossier et crée une tâche. Utiliser pour demande de rappel, demande d'info, réclamation, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre (ex: MCP-1766592530)"
                    },
                    "type_demande": {
                        "type": "integer",
                        "description": "Type: 1=Demande de rappel, 2=Demande d'info, 3=Transmission pièces, 4=Modification infos, 5=Réclamation, 10=Autre"
                    },
                    "objet": {
                        "type": "string",
                        "description": "Objet de la demande (ex: Faire un point sur le dossier)"
                    },
                    "commentaire": {
                        "type": "string",
                        "description": "Description détaillée de la demande"
                    },
                    "urgence": {
                        "type": "integer",
                        "description": "Urgence: 1=Normal, 2=Prioritaire, 3=Critique (défaut: 1)"
                    },
                    "rappel_preference": {
                        "type": "string",
                        "description": "Préférences de rappel si type=1 (ex: Lundi après 16h)"
                    }
                },
                "required": ["ref_sinistre", "type_demande", "objet"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cloturer_sinistre",
            "description": "Clôture un sinistre. ATTENTION: action irréversible. Demander confirmation avant d'exécuter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre à clôturer (ex: MCP-1766592530)"
                    },
                    "raison": {
                        "type": "integer",
                        "description": "Raison: 20=Indemnisation complète, 21=Sans suite, 25=Autre, 26=Indemnisation partielle, 16=Désistement, 23=Doublon, 24=Fraude"
                    },
                    "commentaire": {
                        "type": "string",
                        "description": "Commentaire sur la clôture"
                    }
                },
                "required": ["ref_sinistre", "raison"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verifier_checklist",
            "description": "Vérifie la checklist d'un sinistre : compare les pièces requises avec les pièces déjà fournies. Indique ce qui manque.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre (ex: MCP-1766592530)"
                    }
                },
                "required": ["ref_sinistre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_reglements",
            "description": "Liste les règlements (paiements). Peut filtrer par statut et sens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "integer",
                        "description": "Statut: 0=Attente vérif, 1=Vérifié N1, 2=Vérifié N2, 3=Attente paiement, 4=Payé, 5=Attente transaction, 6=Bloqué"
                    },
                    "sens": {
                        "type": "integer",
                        "description": "Sens: 0=Sortant (on paye), 1=Entrant (on reçoit)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre max de résultats (défaut: 50, max: 100)"
                    }
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "generate_document",
            "description": "Génère un document PDF (attestation, courrier, carte verte, mise en demeure, etc.). Les modèles doivent être configurés dans Sydia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre (ex: MCP-1766592530)"
                    },
                    "id_type": {
                        "type": "integer",
                        "description": "Type de document à générer (ID du modèle configuré dans Sydia)"
                    }
                },
                "required": ["ref_sinistre", "id_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "preparer_mail",
            "description": "Ouvre la modale mail Sydia avec un modèle pré-chargé. Modèles disponibles: adversaire_reclamation, demande_rib, documents_manquants,relance_declaration",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_sinistre": {
                        "type": "string",
                        "description": "Référence du sinistre"
                    },
                    "type_mail": {
                        "type": "string",
                        "description": "Type de modèle: adversaire_reclamation"
                    }
                },
                "required": ["ref_sinistre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "creer_evenement",
            "description": """Ouvre la modale de création d'événement sur le dossier sinistre.
            Types disponibles:
            - Appels/Mails: appel, email_envoye, email_recu, sms_envoye, sms_recu, courrier
            - Conformité: piece_manquante, dossier_complet, prise_en_charge, garantie, avis_technique
            - Comptabilité: reglement_valide, reglement_attente, encaissement, paiement
            - Expertise: expertise, rapport_expertise, mission_expert, conclusions_techniques
            - Réclamation: reclamation, reponse_reclamation
            - Dossier: ouverture, fermeture, reouverture, transfert_dossier
            - Autre: autre, declaration
            
            Tu peux aussi définir une date et heure pour un rappel.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "commentaire": {
                        "type": "string",
                        "description": "Le commentaire/description de l'événement"
                    },
                    "type_evenement": {
                        "type": "string",
                        "description": "Type d'événement. Par défaut: appel"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date au format JJ/MM/AAAA (ex: 02/01/2026)"
                    },
                    "heure": {
                        "type": "string",
                        "description": "Heure au format HH:MM (ex: 15:30)"
                    }
                },
                "required": ["commentaire"]
            }
        }
    },
]


async def execute_tool(name: str, arguments: dict) -> str:
    """Exécute un outil"""
    
    if name == "identifier_assure":
        nom = arguments.get("nom", "").strip().upper()
        prenom = arguments.get("prenom", "").strip().upper()
        ref_sinistre = arguments.get("ref_sinistre", "").strip()
        
        # Récupérer le sinistre
        result = await get_sinistre(ref_sinistre=ref_sinistre)
        
        if not result["success"]:
            return f"❌ Sinistre non trouvé avec la référence {ref_sinistre}"
        
        s = result["data"]
        assure = s.get("assure", {})
        
        # Vérifier nom + prénom
        assure_nom = assure.get("nom", "").strip().upper()
        assure_prenom = assure.get("prenom", "").strip().upper()
        
        if assure_nom == nom and assure_prenom == prenom:
            # Identification réussie → afficher les infos du dossier
            ref = s.get("ref_assureur") or s.get("ref_courtier") or s.get("id")
            statut = "🟢 OUVERT" if s.get("statut") == 1 else "🔴 CLÔTURÉ"
            
            lines = []
            lines.append(f"✅ **IDENTIFICATION RÉUSSIE**")
            lines.append(f"")
            lines.append(f"**Assuré:** {assure.get('prenom')} {assure.get('nom')}")
            lines.append(f"**Email:** {assure.get('email', 'N/A')}")
            lines.append(f"**Tél:** {assure.get('tel1', 'N/A')}")
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
            lines.append(f"**📋 SINISTRE {ref}**")
            lines.append(f"")
            lines.append(f"**Statut:** {statut}")
            lines.append(f"**Type:** {s.get('type_sinistre', 'N/A')}")
            lines.append(f"**Assureur:** {s.get('nom_assureur', 'N/A')}")
            lines.append(f"**Gestionnaire:** {s.get('gestionnaire_nom') or 'Non assigné'}")
            lines.append(f"**Date ouverture:** {s.get('date_ouverture', 'N/A')}")
            
            details = s.get("sinistre", {})
            if details:
                lines.append(f"")
                lines.append(f"**📍 DÉTAILS DU SINISTRE**")
                if details.get("date_sinistre"):
                    lines.append(f"**Date:** {details['date_sinistre']} {details.get('heure_sinistre', '')}")
                if details.get("ville_sinistre"):
                    lines.append(f"**Lieu:** {details.get('cp_sinistre', '')} {details['ville_sinistre']}")
                if details.get("circonstance"):
                    lines.append(f"**Circonstances:** {details['circonstance']}")
            
            lines.append(f"")
            lines.append(f"**📊 CONTENU:** {len(s.get('taches', []))} tâches, {len(s.get('reglements', []))} règlements, {len(s.get('ged', []))} documents")
            
            if s.get("fraude") == 1:
                lines.append(f"")
                lines.append(f"⚠️ **ALERTE:** Suspicion fraude ({s.get('suspicion_tx', 0)}%)")
            if s.get("mecontent") == 1:
                lines.append(f"⚠️ **ALERTE:** Client mécontent")
            
            return "\n".join(lines)
        else:
            return f"""❌ **IDENTIFICATION ÉCHOUÉE**

Les informations fournies ne correspondent pas au dossier.
Veuillez vérifier le nom, prénom et la référence du sinistre."""
    
    # =========================================================================
    # GET SINISTRE
    # =========================================================================
    elif name == "get_sinistre":
        result = await get_sinistre(
            id_sinistre=arguments.get("id_sinistre"),
            ref_sinistre=arguments.get("ref_sinistre")
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        s = result["data"]
        
        lines = []
        ref = s.get("ref_assureur") or s.get("ref_courtier") or s.get("id")
        statut = "🟢 OUVERT" if s.get("statut") == 1 else "🔴 CLÔTURÉ"
        
        lines.append(f"**SINISTRE {ref}**")
        lines.append(f"")
        lines.append(f"**Statut:** {statut}")
        lines.append(f"**Type:** {s.get('type_sinistre', 'N/A')}")
        lines.append(f"**Assureur:** {s.get('nom_assureur', 'N/A')}")
        lines.append(f"**Gestionnaire:** {s.get('gestionnaire_nom') or 'Non assigné'}")
        lines.append(f"**Date ouverture:** {s.get('date_ouverture', 'N/A')}")
        
        assure = s.get("assure", {})
        if assure:
            nom = f"{assure.get('prenom', '')} {assure.get('nom', '')}".strip()
            lines.append(f"")
            lines.append(f"**ASSURÉ:** {nom}")
            lines.append(f"Email: {assure.get('email', 'N/A')}")
            lines.append(f"Tél: {assure.get('tel1', 'N/A')}")
        
        details = s.get("sinistre", {})
        if details:
            lines.append(f"")
            lines.append(f"**DÉTAILS**")
            if details.get("date_sinistre"):
                lines.append(f"Date: {details['date_sinistre']} {details.get('heure_sinistre', '')}")
            if details.get("ville_sinistre"):
                lines.append(f"Lieu: {details.get('cp_sinistre', '')} {details['ville_sinistre']}")
            if details.get("circonstance"):
                lines.append(f"Circonstances: {details['circonstance']}")
        
        lines.append(f"")
        lines.append(f"**CONTENU:** {len(s.get('taches', []))} tâches, {len(s.get('reglements', []))} règlements, {len(s.get('evenements', []))} événements")
        
        if s.get("fraude") == 1:
            lines.append(f"⚠️ **ALERTE:** Suspicion fraude ({s.get('suspicion_tx', 0)}%)")
        if s.get("mecontent") == 1:
            lines.append(f"⚠️ **ALERTE:** Client mécontent")
        
        return "\n".join(lines)
    
    # =========================================================================
    # LIST SINISTRES
    # =========================================================================
    elif name == "list_sinistres":
        limit = arguments.get("limit", 10)
        result = await list_sinistres()
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        sinistres = result["data"][:limit]
        
        lines = [f"**LISTE DES SINISTRES ({len(sinistres)} résultats)**", ""]
        
        for s in sinistres:
            statut = "🟢" if s.get("statut") == 1 else "🔴"
            ref = s.get("ref_assureur") or s.get("ref_courtier") or "N/A"
            lines.append(f"{statut} **{s.get('id')}** | {ref} | {s.get('type_sinistre', '?')}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # ADD SINISTRE
    # =========================================================================
    elif name == "add_sinistre":
        result = await add_sinistre(
            type_sinistre=arguments.get("type_sinistre"),
            date_sinistre=arguments.get("date_sinistre"),
            ville=arguments.get("ville"),
            cp=arguments.get("cp"),
            circonstances=arguments.get("circonstances"),
            nom=arguments.get("nom"),
            prenom=arguments.get("prenom"),
            email=arguments.get("email"),
            tel=arguments.get("tel"),
            immatriculation=arguments.get("immatriculation", "AA-000-AA")
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        types = {1: "AUTO", 2: "MRH", 3: "PROTECTION JURIDIQUE", 4: "AFFINITAIRE", 5: "RC", 6: "NVEI"}
        type_label = types.get(arguments.get("type_sinistre"), "?")
        
        return f"""✅ **SINISTRE CRÉÉ AVEC SUCCÈS**

**Référence:** {result['reference']}
**ID Sinistre:** {result['id_sinistre']}
**ID Assuré:** {result['id_assure']}

**Récapitulatif:**
- Type: {type_label}
- Date: {arguments.get('date_sinistre')}
- Lieu: {arguments.get('cp')} {arguments.get('ville')}
- Assuré: {arguments.get('prenom')} {arguments.get('nom')}

📧 Communiquez la référence **{result['reference']}** à l'assuré."""
    
    # =========================================================================
    # ADD DOCUMENT (GED)
    # =========================================================================
    elif name == "add_document":
        result = await add_document(
            id_sinistre=arguments.get("id_sinistre"),
            filename=arguments.get("filename"),
            commentaire=arguments.get("commentaire", ""),
            content_text=arguments.get("content_text", "")
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        return f"""✅ **DOCUMENT AJOUTÉ AVEC SUCCÈS**

**ID Document:** {result['id_ged']}
**Sinistre:** {arguments.get('id_sinistre')}
**Fichier:** {arguments.get('filename')}
**Description:** {arguments.get('commentaire')}

📎 Le document a été ajouté au dossier et le gestionnaire a été notifié."""
    
    elif name == "list_documents":
        result = await list_documents(
            id_sinistre=arguments.get("id_sinistre")
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        documents = result["documents"]
        count = result["count"]
        
        if not documents:
            return f"📂 Aucun document trouvé pour le sinistre {arguments.get('id_sinistre')}"
        
        lines = [f"**📂 DOCUMENTS DU SINISTRE {arguments.get('id_sinistre')}** ({count} pièces)", ""]
        
        for doc in documents:
            verified = "✅" if doc.get("piece_verifiee") == 1 else "⏳"
            poids = doc.get("poids", 0)
            if poids:
                poids_kb = int(poids) / 1024
                poids_str = f"{poids_kb:.1f} Ko"
            else:
                poids_str = "?"
            
            lines.append(f"{verified} **{doc.get('id_ged')}** | {doc.get('filename')} | {doc.get('categorie', 'Non classé')} | {poids_str}")
        
        return "\n".join(lines)
    
    elif name == "get_document":
        result = await get_document(
            id_ged=arguments.get("id_ged")
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        doc = result["data"]
        
        poids = doc.get("poids", 0)
        if poids:
            poids_kb = int(poids) / 1024
            poids_str = f"{poids_kb:.1f} Ko"
        else:
            poids_str = "?"
        
        verified = "✅ Vérifié" if doc.get("piece_verifiee") == "1" else "⏳ En attente"
        public = "🔓 Public" if doc.get("public") == "1" else "🔒 Privé"
        
        return f"""**📄 DOCUMENT {doc.get('id_ged')}**

**Fichier:** {doc.get('filename')}
**Extension:** {doc.get('extension')}
**Poids:** {poids_str}
**Date:** {doc.get('date', 'N/A')}
**Catégorie:** {doc.get('categorie', 'Non classé')}
**Commentaire:** {doc.get('commentaire') or 'Aucun'}

**Statut:** {verified} | {public}
**Sinistre:** {doc.get('id_sinistre') or 'N/A'}
**Assuré:** {doc.get('id_assure') or 'N/A'}"""
    
    elif name == "update_assure":
        ref_sinistre = arguments.get("ref_sinistre")
        
        sinistre_result = await get_sinistre(ref_sinistre=ref_sinistre)
        
        if not sinistre_result["success"]:
            return f"❌ Sinistre non trouvé avec la référence {ref_sinistre}"
        
        s = sinistre_result["data"]
        assure = s.get("assure", {})
        id_assure = assure.get("id")
        
        if not id_assure:
            return f"❌ Impossible de trouver l'assuré pour le sinistre {ref_sinistre}"
        
        champs = {}
        for key in ["nom", "prenom", "email", "tel1", "tel2", "adresse", "cp", "ville"]:
            if arguments.get(key):
                champs[key] = arguments[key]
        
        if not champs:
            return "❌ Aucun champ à modifier spécifié."
        
        result = await update_assure(id_assure, **champs)
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        notify_refresh(
            action='assure_updated',
            data={'id_assure': id_assure, 'ref_sinistre': ref_sinistre},
            endpoint='assure/update',
            fields=champs
        )
        
        modifications = "\n".join([f"• **{k}** → {v}" for k, v in champs.items()])
        
        return f"""✅ **ASSURÉ MODIFIÉ AVEC SUCCÈS**

**Sinistre:** {ref_sinistre}
**Assuré:** {assure.get('prenom')} {assure.get('nom')} (ID: {id_assure})

**Modifications effectuées:**
{modifications}

🔄 L'interface Sydia va se rafraîchir automatiquement."""

    elif name == "contact_gestionnaire":
        ref_sinistre = arguments.get("ref_sinistre")
        
        sinistre_result = await get_sinistre(ref_sinistre=ref_sinistre)
        
        if not sinistre_result["success"]:
            return f"❌ Sinistre non trouvé avec la référence {ref_sinistre}"
        
        s = sinistre_result["data"]
        id_sinistre = s.get("id")
        
        if not id_sinistre:
            return f"❌ Impossible de trouver l'ID du sinistre {ref_sinistre}"
        
        type_demande = arguments.get("type_demande", 10)
        objet = arguments.get("objet", "")
        commentaire = arguments.get("commentaire", "")
        urgence = arguments.get("urgence", 1)
        rappel_preference = arguments.get("rappel_preference", "")
        
        result = await contact_gestionnaire(
            id_sinistre=id_sinistre,
            type_demande=type_demande,
            objet=objet,
            commentaire=commentaire,
            urgence=urgence,
            rappel_preference=rappel_preference
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        types_labels = {
            1: "Demande de rappel",
            2: "Demande d'information",
            3: "Transmission de pièces",
            4: "Modification d'informations",
            5: "Réclamation",
            10: "Autre"
        }
        urgence_labels = {1: "🟢 Normal", 2: "🟠 Prioritaire", 3: "🔴 Critique"}
        
        notify_refresh(
            action='tache_created',
            data={'id_sinistre': id_sinistre, 'ref_sinistre': ref_sinistre, 'id_tache': result['id_tache']},
            endpoint='sinistre/contact',
            fields={'type_demande': type_demande, 'objet': objet, 'urgence': urgence}
        )
        
        return f"""✅ **TÂCHE CRÉÉE AVEC SUCCÈS**

**ID Tâche:** {result['id_tache']}
**Sinistre:** {ref_sinistre}

**Détails:**
• **Type:** {types_labels.get(type_demande, 'Autre')}
• **Objet:** {objet}
• **Commentaire:** {commentaire or 'Aucun'}
• **Urgence:** {urgence_labels.get(urgence, 'Normal')}

📧 Le gestionnaire a été notifié.
🔄 L'interface Sydia va se rafraîchir automatiquement."""
    
    elif name == "cloturer_sinistre":
        ref_sinistre = arguments.get("ref_sinistre")
        
        sinistre_result = await get_sinistre(ref_sinistre=ref_sinistre)
        
        if not sinistre_result["success"]:
            return f"❌ Sinistre non trouvé avec la référence {ref_sinistre}"
        
        s = sinistre_result["data"]
        id_sinistre = s.get("id")
        
        if not id_sinistre:
            return f"❌ Impossible de trouver l'ID du sinistre {ref_sinistre}"
        
        if s.get("statut") != 1:
            return f"❌ Le sinistre {ref_sinistre} est déjà clôturé."
        
        raison = arguments.get("raison", 25)
        commentaire = arguments.get("commentaire", "")
        
        from datetime import date
        date_fermeture = date.today().strftime("%Y-%m-%d")
        
        result = await cloturer_sinistre(
            id_sinistre=id_sinistre,
            date_fermeture=date_fermeture,
            raison=raison,
            commentaire=commentaire
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        raisons_labels = {
            20: "Indemnisation complète",
            21: "Sans suite",
            25: "Autre",
            26: "Indemnisation partielle",
            16: "Désistement",
            23: "Doublon",
            24: "Fraude",
            1: "Sans réponse",
            2: "Pièces manquantes"
        }
        
        notify_refresh(
            action='sinistre_cloture',
            data={'id_sinistre': id_sinistre, 'ref_sinistre': ref_sinistre},
            endpoint='sinistre/cloturer',
            fields={'raison': raison, 'date_fermeture': date_fermeture}
        )
        
        return f"""✅ **SINISTRE CLÔTURÉ AVEC SUCCÈS**

**Sinistre:** {ref_sinistre}
**ID:** {id_sinistre}
**Date de clôture:** {date_fermeture}
**Raison:** {raisons_labels.get(raison, 'Autre')}
**Commentaire:** {commentaire or 'Aucun'}

🔴 Le dossier est maintenant fermé.
🔄 L'interface Sydia va se rafraîchir automatiquement."""
    
    elif name == "verifier_checklist":
        ref_sinistre = arguments.get("ref_sinistre")
        
        sinistre_result = await get_sinistre(ref_sinistre=ref_sinistre)
        
        if not sinistre_result["success"]:
            return f"❌ Sinistre non trouvé avec la référence {ref_sinistre}"
        
        s = sinistre_result["data"]
        id_sinistre = s.get("id")
        
        if not id_sinistre:
            return f"❌ Impossible de trouver l'ID du sinistre {ref_sinistre}"
        
        checklist_result = await get_checklist(id_sinistre)
        
        if not checklist_result["success"]:
            return f"❌ Erreur checklist: {checklist_result['error']}"
        
        checklist_requise = checklist_result.get("checklist", [])
        
        if not checklist_requise:
            return f"📋 Aucune checklist configurée pour ce type de sinistre."
        
        docs_result = await list_documents(id_sinistre)
        documents_fournis = []
        if docs_result["success"]:
            documents_fournis = [d.get("filename", "").upper() for d in docs_result.get("documents", [])]
            documents_fournis += [d.get("categorie", "").upper() for d in docs_result.get("documents", [])]
        
        lines = [f"**📋 CHECKLIST DU SINISTRE {ref_sinistre}**", ""]
        
        pieces_ok = []
        pieces_manquantes = []
        
        for piece in checklist_requise:
            nom = piece.get("nom", "")
            description = piece.get("description", "")
            
            nom_upper = nom.upper()
            found = False
            for doc in documents_fournis:
                if nom_upper in doc or any(word in doc for word in nom_upper.split()):
                    found = True
                    break
            
            if found:
                pieces_ok.append(f"✅ **{nom}**")
            else:
                pieces_manquantes.append(f"❌ **{nom}** - {description}")
        
        if pieces_ok:
            lines.append("**Pièces fournies :**")
            lines.extend(pieces_ok)
            lines.append("")
        
        if pieces_manquantes:
            lines.append("**Pièces manquantes :**")
            lines.extend(pieces_manquantes)
            lines.append("")
        
        total = len(checklist_requise)
        ok = len(pieces_ok)
        manquant = len(pieces_manquantes)
        
        if manquant == 0:
            lines.append(f"🎉 **DOSSIER COMPLET !** ({ok}/{total} pièces)")
        else:
            lines.append(f"⚠️ **{manquant} pièce(s) manquante(s)** ({ok}/{total} pièces)")
        
        return "\n".join(lines)
    
    elif name == "list_reglements":
        status = arguments.get("status")
        sens = arguments.get("sens")
        limit = arguments.get("limit", 50)
        
        result = await list_reglements(
            status=status,
            sens=sens,
            limit=limit
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        reglements = result["data"]
        
        if not reglements:
            return "📋 Aucun règlement trouvé."
        
        status_labels = {
            0: "⏳ Attente vérif",
            1: "✅ Vérifié N1",
            2: "✅ Vérifié N2",
            3: "💳 Attente paiement",
            4: "✅ Payé",
            5: "⏳ Attente transaction",
            6: "🚫 Bloqué"
        }
        sens_labels = {0: "↗️ Sortant", 1: "↙️ Entrant"}
        
        lines = [f"**💰 LISTE DES RÈGLEMENTS** ({len(reglements)} résultats)", ""]
        
        for r in reglements[:20]:  
            statut_code = int(r.get("statut_code", 0))
            sens_code = int(r.get("sens_code", 0))
            
            lines.append(f"**#{r.get('id')}** | Sinistre {r.get('id_sinistre')} | {r.get('montant')} {r.get('devise', 'EUR')}")
            lines.append(f"   → {status_labels.get(statut_code, '?')} | {sens_labels.get(sens_code, '?')} | {r.get('destinataire', 'N/A')}")
            lines.append("")
        
        if len(reglements) > 20:
            lines.append(f"... et {len(reglements) - 20} autres règlements")
        
        return "\n".join(lines)
    
    elif name == "generate_document":
        ref_sinistre = arguments.get("ref_sinistre")
        id_type = arguments.get("id_type")
        
        sinistre_result = await get_sinistre(ref_sinistre=ref_sinistre)
        
        if not sinistre_result["success"]:
            return f"❌ Sinistre non trouvé avec la référence {ref_sinistre}"
        
        s = sinistre_result["data"]
        id_sinistre = s.get("id")
        
        if not id_sinistre:
            return f"❌ Impossible de trouver l'ID du sinistre {ref_sinistre}"
        
        result = await generate_document(
            id_type=id_type,
            id_sinistre=id_sinistre
        )
        
        if not result["success"]:
            return f"❌ Erreur: {result['error']}"
        
        notify_refresh(
            action='document_generated',
            data={'id_sinistre': id_sinistre, 'ref_sinistre': ref_sinistre, 'filename': result.get('filename')},
            endpoint='ged/document/get',
            fields={'id_type': id_type, 'filename': result.get('filename')}
        )
        
        size_kb = int(result.get('size', 0)) / 1024
        
        return f"""✅ **DOCUMENT GÉNÉRÉ AVEC SUCCÈS**

**Fichier:** {result.get('filename')}
**Taille:** {size_kb:.1f} Ko
**Sinistre:** {ref_sinistre}

📄 Le document PDF a été généré.
🔄 L'interface Sydia va se rafraîchir automatiquement."""

    elif name == "creer_evenement":
        commentaire = arguments.get("commentaire")
        type_evt = arguments.get("type_evenement", "appel")
        date_evt = arguments.get("date", "")
        heure_evt = arguments.get("heure", "")
        
        id_type = TYPES_EVENEMENTS.get(type_evt, 4)
        
        print(f"DEBUG creer_evenement: type_evt={type_evt}, id_type={id_type}, date={date_evt}, heure={heure_evt}")
        
        notify_refresh(
            action='open_event_modal',
            data={
                'commentaire': commentaire,
                'type_evenement': id_type,
                'date': date_evt,
                'heure': heure_evt
            },
            endpoint='evenement/create',
            fields={
                'commentaire': commentaire,
                'type_evenement': id_type,
                'date': date_evt,
                'heure': heure_evt
            }
        )
        
        return f"""✅ **MODALE ÉVÉNEMENT OUVERTE**

📝 **Type:** {type_evt} (ID: {id_type})
📝 **Commentaire:** {commentaire}
📅 **Date:** {date_evt if date_evt else 'Aujourd hui'}
🕐 **Heure:** {heure_evt if heure_evt else 'Maintenant'}

Le gestionnaire peut vérifier et cliquer sur "Enregistrer l'évènement"."""   
 
    elif name == "preparer_mail":
        ref_sinistre = arguments.get("ref_sinistre")
        type_mail = arguments.get("type_mail", "adversaire_reclamation")
    
    id_modele = MODELES_MAIL_SYDIA.get(type_mail, 744)
    
    sinistre_result = await get_sinistre(ref_sinistre=ref_sinistre)
    
    if not sinistre_result["success"]:
        return f"❌ Sinistre non trouvé: {ref_sinistre}"
    
    s = sinistre_result["data"]
    id_sinistre = s.get("id")
    id_assure = s.get("assure", {}).get("id", 0) 
    
    notify_refresh(
        action='open_mail_modal',
        data={
            'ref_sinistre': ref_sinistre,
            'id_modele': id_modele,
            'id_assure': id_assure,  
            'type_mail': type_mail
        },
        endpoint='mail/prepare',
        fields={
            'id_modele': id_modele,
            'id_assure': id_assure, 
            'type_mail': type_mail
        }
    )
    
    return f"""✅ **MODALE MAIL OUVERTE**

**Sinistre:** {ref_sinistre}
**Modèle:** {type_mail}
**ID Modèle:** {id_modele}

📧 La modale Sydia s'ouvre avec le modèle pré-chargé."""

    return f"❌ Outil inconnu: {name}"


def notify_refresh(action: str, data: dict, endpoint: str = None, fields: dict = None):
    """
    Envoie une notification WebSocket pour rafraîchir l'interface
    
    V2: Envoie le nom de l'endpoint + les champs modifiés pour refresh ciblé
    """
    socketio.emit('sydia_update', {
        'action': action,
        'endpoint': endpoint,
        'fields': fields or {},
        'timestamp': __import__('time').time()
    })
    print(f"📡 WebSocket V2: {action} | endpoint: {endpoint}")


SYSTEM_PROMPT = """Tu es un assistant Sydia spécialisé dans la gestion des sinistres.

=== RÈGLE D'IDENTIFICATION (TRÈS IMPORTANT - SUIVRE À LA LETTRE) ===

Pour TOUTE action sur un dossier, tu DOIS suivre ces 2 étapes OBLIGATOIRES :

ÉTAPE 1 : Demander la RÉFÉRENCE DU SINISTRE
→ "Quelle est votre référence de sinistre ?"

ÉTAPE 2 : APRÈS avoir reçu la référence, demander NOM et PRÉNOM
→ "Merci. Pour valider votre identité, quel est votre nom et prénom ?"

 RÈGLES STRICTES :
- Tu ne peux PAS faire d'action SANS identification
- Tu ne peux PAS appeler identifier_assure SANS avoir les 3 infos (référence + nom + prénom)
- Si l'utilisateur donne seulement la référence → demande le nom et prénom
- Si l'utilisateur donne seulement son nom → demande la référence d'abord

EXEMPLE DE CONVERSATION :
User: "Liste les règlements"
Toi: "Quelle est votre référence de sinistre ?"
User: "MCP-1766592530"
Toi: "Merci. Pour valider votre identité, quel est votre nom et prénom ?"
User: "Michel Michel"
Toi: [Appelle identifier_assure] puis [Appelle list_reglements]

=== APRÈS IDENTIFICATION RÉUSSIE ===

Une fois identifié, tu peux :
- Consulter le dossier (get_sinistre)
- Lister les documents (list_documents)
- Ajouter un document (add_document)
- Modifier l'assuré (update_assure)
- Contacter le gestionnaire (contact_gestionnaire)
- Clôturer le sinistre (cloturer_sinistre)
- Lister les règlements (list_reglements)

=== RÈGLE POUR CONTACTER LE GESTIONNAIRE ===
Pour créer une tâche/demande, utilise contact_gestionnaire avec :
- ref_sinistre
- type_demande (1=Rappel, 2=Info, 3=Pièces, 4=Modification, 5=Réclamation, 10=Autre)
- objet
- commentaire (optionnel)
- urgence (1=Normal, 2=Prioritaire, 3=Critique)

=== RÈGLE POUR CLÔTURER UN SINISTRE ===
Pour clôturer, utilise cloturer_sinistre avec :
- ref_sinistre
- raison (20=Indemnisation complète, 21=Sans suite, 25=Autre, etc.)
- commentaire (optionnel)
 DEMANDE TOUJOURS CONFIRMATION avant de clôturer !

=== AUTRES RÈGLES ===
1. Quand tu appelles un outil, AFFICHE les données reçues
2. Ne dis jamais "voir ci-dessus"
3. Sois concis et professionnel
4. Parle français

=== RÈGLE POUR PRÉPARER UN MAIL (TRÈS IMPORTANT) ===
Quand l'utilisateur demande de rédiger/préparer/écrire un mail ou propose une version de mail :
1. D'abord identifier l'assuré (référence + nom/prénom)
2. Ensuite appeler IMMÉDIATEMENT l'outil preparer_mail avec :
   - ref_sinistre
   - destinataire (email de l'assuré)
   - objet (objet du mail)
   - contenu (texte complet du mail)
   - type_mail (relance, demande_pieces, confirmation, information, autre)

 RÈGLES STRICTES POUR LES MAILS :
- NE JAMAIS écrire le mail dans la conversation !
- NE JAMAIS demander "Souhaitez-vous que je prépare ce mail ?"
- TOUJOURS appeler l'outil preparer_mail DIRECTEMENT
- Si l'utilisateur dit "oui", "propose une version", "prépare le mail" → appeler preparer_mail

EXEMPLE :
User: "Prépare-moi un mail de confirmation"
Toi: [Appelle preparer_mail avec objet et contenu générés]

User: "propose moi une version stp"
Toi: [Appelle preparer_mail avec objet et contenu générés]

## Création d'événements - Détection automatique du type
Quand tu utilises creer_evenement, détecte le TYPE automatiquement selon le contexte :
- APPEL reçu/passé → type_evenement: "appel"
- EMAIL envoyé → type_evenement: "email_envoye"
- EMAIL reçu → type_evenement: "email_recu"
- SMS envoyé → type_evenement: "sms_envoye"
- SMS reçu → type_evenement: "sms_recu"
- Dossier COMPLET → type_evenement: "dossier_complet"
- Pièces MANQUANTES → type_evenement: "piece_manquante"
- RÈGLEMENT validé/paiement → type_evenement: "reglement_valide"
- EXPERTISE/expert → type_evenement: "expertise"
- Rapport expertise → type_evenement: "rapport_expertise"
- RÉCLAMATION client → type_evenement: "reclamation"
- Réponse réclamation → type_evenement: "reponse_reclamation"
- RAPPEL/relance/clôturer → type_evenement: "autre"
- Sinon → type_evenement: "autre"
"""


def get_messages(session_id: str) -> list:
    if session_id not in conversations:
        conversations[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return conversations[session_id]


async def chat(session_id: str, user_message: str) -> str:
    messages = get_messages(session_id)
    messages.append({"role": "user", "content": user_message})
    
    response = azure_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    assistant_message = response.choices[0].message
    
    if assistant_message.tool_calls:
        messages.append(assistant_message)
        
        for tool_call in assistant_message.tool_calls:
            result = await execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
        
        final = azure_client.chat.completions.create(model=MODEL, messages=messages)
        content = final.choices[0].message.content
        messages.append({"role": "assistant", "content": content})
        return content
    
    content = assistant_message.content
    messages.append({"role": "assistant", "content": content})
    return content


HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sydia AI • Assistant Intelligent</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #030014;
            --surface: rgba(15, 10, 40, 0.7);
            --surface-light: rgba(30, 20, 70, 0.5);
            --border: rgba(139, 92, 246, 0.2);
            --border-glow: rgba(139, 92, 246, 0.5);
            --primary: #8b5cf6;
            --primary-light: #a78bfa;
            --secondary: #06b6d4;
            --accent: #f472b6;
            --success: #34d399;
            --danger: #ef4444;
            --text: #ffffff;
            --text-dim: rgba(255,255,255,0.6);
            --neon-purple: 0 0 20px rgba(139, 92, 246, 0.5), 0 0 40px rgba(139, 92, 246, 0.3);
        }
        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow: hidden;
        }
        .cosmos {
            position: fixed;
            inset: 0;
            z-index: -1;
            background: 
                radial-gradient(ellipse at 0% 0%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
                radial-gradient(ellipse at 100% 100%, rgba(6, 182, 212, 0.1) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(244, 114, 182, 0.05) 0%, transparent 70%);
        }
        .stars {
            position: absolute;
            width: 100%;
            height: 100%;
            background-image: 
                radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.8), transparent),
                radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.5), transparent),
                radial-gradient(1px 1px at 90px 40px, rgba(255,255,255,0.6), transparent);
            background-size: 200px 200px;
            animation: twinkle 5s ease-in-out infinite;
        }
        @keyframes twinkle { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .glow-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(100px);
            animation: orbit 25s linear infinite;
        }
        .glow-orb-1 { width: 500px; height: 500px; background: rgba(139, 92, 246, 0.3); top: -10%; left: -10%; }
        .glow-orb-2 { width: 400px; height: 400px; background: rgba(6, 182, 212, 0.2); bottom: -10%; right: -10%; animation-delay: -10s; }
        .glow-orb-3 { width: 300px; height: 300px; background: rgba(244, 114, 182, 0.15); top: 50%; left: 50%; transform: translate(-50%, -50%); }
        @keyframes orbit { 0% { transform: rotate(0deg) translateX(50px); } 100% { transform: rotate(360deg) translateX(50px); } }
        
        .app { display: flex; height: 100vh; }
        
        /* ========== SIDEBAR ========== */
        .sidebar {
            width: 320px;
            background: var(--surface);
            backdrop-filter: blur(40px);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }
        
        /* BRAND */
        .brand {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(180deg, rgba(139, 92, 246, 0.1) 0%, transparent 100%);
        }
        .brand-inner { display: flex; align-items: center; gap: 12px; }
        .brand-logo {
            width: 48px; height: 48px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: var(--neon-purple);
        }
        .brand-text h1 {
            font-size: 20px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, var(--primary-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-text span {
            font-size: 11px;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .brand-text span::before {
            content: '';
            width: 6px; height: 6px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--success);
        }
        
        /* STATS */
        .stats {
            padding: 14px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            border-bottom: 1px solid var(--border);
        }
        .stat-box {
            background: var(--surface-light);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 8px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
        }
        .stat-box:hover { transform: translateY(-2px); border-color: var(--primary); }
        .stat-num {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label { font-size: 9px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; }
        
        /* NEW CHAT BUTTON */
        .new-chat-section { padding: 14px; border-bottom: 1px solid var(--border); }
        .new-chat-btn {
            width: 100%;
            padding: 12px 18px;
            background: linear-gradient(135deg, var(--primary), #7c3aed);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 13px;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.3s;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.3);
        }
        .new-chat-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4); }
        
        /* HISTORY */
        .history { flex: 1; padding: 14px 10px; overflow-y: auto; }
        .history-group { margin-bottom: 16px; }
        .history-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--primary-light);
            padding: 0 10px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .history-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            color: var(--text-dim);
            margin-bottom: 4px;
            border: 1px solid transparent;
        }
        .history-item:hover {
            background: var(--surface-light);
            color: var(--text);
            border-color: var(--border);
            transform: translateX(4px);
        }
        .history-item.active {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1));
            color: var(--text);
            border-color: var(--border-glow);
        }
        .history-icon {
            width: 32px; height: 32px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            flex-shrink: 0;
        }
        .history-item:hover .history-icon,
        .history-item.active .history-icon {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-color: transparent;
        }
        .history-text { flex: 1; min-width: 0; }
        .history-title {
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .history-time { font-size: 10px; color: var(--text-dim); }
        .history-delete {
            opacity: 0;
            width: 24px; height: 24px;
            background: rgba(239, 68, 68, 0.2);
            border: none;
            border-radius: 6px;
            color: #ef4444;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            transition: all 0.3s;
        }
        .history-item:hover .history-delete { opacity: 1; }
        .history-delete:hover { background: #ef4444; color: white; }
        .history-empty {
            text-align: center;
            padding: 30px 16px;
            color: var(--text-dim);
        }
        .history-empty i { font-size: 36px; margin-bottom: 10px; opacity: 0.4; display: block; }
        .history-empty p { font-size: 12px; }
        
        /* ========== MAIN ========== */
        .main { flex: 1; display: flex; flex-direction: column; }
        
        /* TOPBAR */
        .topbar {
            padding: 18px 28px;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .topbar-left { display: flex; align-items: center; gap: 14px; }
        .ai-avatar {
            width: 50px; height: 50px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: var(--neon-purple);
        }
        .ai-info h2 { font-size: 18px; font-weight: 700; }
        .ai-info p { font-size: 12px; color: var(--text-dim); display: flex; align-items: center; gap: 6px; }
        .typing-dots { display: none; gap: 3px; }
        .typing-dots span {
            width: 5px; height: 5px;
            background: var(--primary);
            border-radius: 50%;
            animation: typingBounce 1.4s infinite;
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.15s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.3s; }
        @keyframes typingBounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }
        .topbar-right { display: flex; gap: 8px; }
        .topbar-btn {
            width: 40px; height: 40px;
            background: var(--surface-light);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-dim);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        .topbar-btn:hover { background: var(--surface); color: var(--text); border-color: var(--primary); }
        
        /* CHAT */
        .chat-area {
            flex: 1;
            padding: 28px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .msg {
            display: flex;
            gap: 14px;
            max-width: 70%;
            animation: msgIn 0.4s ease-out;
        }
        @keyframes msgIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .msg.user { align-self: flex-end; flex-direction: row-reverse; }
        .msg-avatar {
            width: 44px; height: 44px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        .msg.assistant .msg-avatar { background: linear-gradient(135deg, var(--primary), var(--secondary)); }
        .msg.user .msg-avatar { background: var(--surface-light); border: 2px solid var(--border); }
        .msg-content {
            padding: 16px 20px;
            border-radius: 18px;
            font-size: 13px;
            line-height: 1.6;
        }
        .msg.assistant .msg-content {
            background: var(--surface);
            border: 1px solid var(--border);
            border-bottom-left-radius: 4px;
        }
        .msg.user .msg-content {
            background: linear-gradient(135deg, var(--primary), #7c3aed);
            border-bottom-right-radius: 4px;
        }
        .msg-content strong { color: var(--secondary); }
        .msg-time { font-size: 9px; color: var(--text-dim); margin-top: 6px; display: flex; align-items: center; gap: 4px; }
        .msg-typing {
            display: none;
            padding: 16px 20px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 18px;
        }
        .msg-typing-dots { display: flex; gap: 5px; }
        .msg-typing-dots span {
            width: 10px; height: 10px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }
        .msg-typing-dots span:nth-child(2) { animation-delay: 0.15s; }
        .msg-typing-dots span:nth-child(3) { animation-delay: 0.3s; }
        @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-12px); } }
        
        /* INPUT */
        .input-area {
            padding: 20px 28px;
            background: var(--surface);
            border-top: 1px solid var(--border);
        }
        .suggestions {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .suggestion {
            padding: 8px 14px;
            background: var(--surface-light);
            border: 1px solid var(--border);
            border-radius: 20px;
            color: var(--text-dim);
            font-size: 11px;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .suggestion:hover {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1));
            border-color: var(--primary);
            color: var(--text);
            transform: translateY(-2px);
        }
        .input-box {
            display: flex;
            gap: 10px;
            background: var(--surface-light);
            border: 2px solid var(--border);
            border-radius: 18px;
            padding: 8px;
            transition: all 0.3s;
        }
        .input-box:focus-within { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15); }
        #user-input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 12px 16px;
            font-size: 14px;
            color: var(--text);
            font-family: inherit;
            outline: none;
        }
        #user-input::placeholder { color: var(--text-dim); }
        #mic-btn {
            width: 50px; height: 50px;
            background: var(--surface-light);
            border: 2px solid var(--border);
            border-radius: 14px;
            color: var(--text-dim);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        #mic-btn:hover { border-color: var(--primary); color: var(--text); }
        #mic-btn.recording {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            border-color: #ef4444;
            color: white;
            animation: pulse-mic 1s infinite;
        }
        @keyframes pulse-mic {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        #send-btn {
            width: 50px; height: 50px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 14px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        #send-btn:hover { transform: scale(1.05); }
        #send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        /* SUCCESS MODAL */
        .success-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(10px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .success-modal {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 40px;
            text-align: center;
            animation: successIn 0.4s ease-out;
        }
        @keyframes successIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
        .success-icon {
            width: 80px; height: 80px;
            background: linear-gradient(135deg, var(--success), #059669);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin: 0 auto 16px;
        }
        .success-text { font-size: 20px; font-weight: 700; }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--primary); }
    </style>
</head>
<body>
    <div class="cosmos">
        <div class="stars"></div>
        <div class="glow-orb glow-orb-1"></div>
        <div class="glow-orb glow-orb-2"></div>
        <div class="glow-orb glow-orb-3"></div>
    </div>

    <div class="app">
        <!-- ========== SIDEBAR ========== -->
        <aside class="sidebar">
            <div class="brand">
                <div class="brand-inner">
                    <div class="brand-logo">🤖</div>
                    <div class="brand-text">
                        <h1>Sydia AI</h1>
                        <span>Assistant Intelligent</span>
                    </div>
                </div>
            </div>

            <div class="stats">
                <div class="stat-box">
                    <div class="stat-num" id="stat-total">-</div>
                    <div class="stat-label">Total</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num" id="stat-open">-</div>
                    <div class="stat-label">Ouverts</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num" id="stat-closed">-</div>
                    <div class="stat-label">Fermés</div>
                </div>
            </div>

            <div class="new-chat-section">
                <button class="new-chat-btn" onclick="newConversation()">
                    <i class="fas fa-plus"></i>
                    Nouvelle conversation
                </button>
            </div>

            <div class="history" id="history-container">
                <!-- L'historique sera généré dynamiquement par JavaScript -->
            </div>
        </aside>

        <!-- ========== MAIN ========== -->
        <main class="main">
            <header class="topbar">
                <div class="topbar-left">
                    <div class="ai-avatar">🤖</div>
                    <div class="ai-info">
                        <h2>Agent Sydia</h2>
                        <p>
                            <span id="status-txt">Prêt à vous aider</span>
                            <span class="typing-dots" id="typing-dots">
                                <span></span><span></span><span></span>
                            </span>
                        </p>
                    </div>
                </div>
                <div class="topbar-right">
                    <button class="topbar-btn" onclick="clearCurrentChat()" title="Effacer cette conversation">
                        <i class="fas fa-eraser"></i>
                    </button>
                    <button class="topbar-btn" title="Paramètres">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
            </header>

            <div class="chat-area" id="chat">
                <div class="msg assistant">
                    <div class="msg-avatar">🤖</div>
                    <div>
                        <div class="msg-content" id="welcome">Connexion en cours...</div>
                        <div class="msg-time"><i class="fas fa-clock"></i> Maintenant</div>
                    </div>
                </div>
                <div class="msg assistant" id="typing-msg" style="display:none;">
                    <div class="msg-avatar">🤖</div>
                    <div class="msg-typing" style="display:block;">
                        <div class="msg-typing-dots"><span></span><span></span><span></span></div>
                    </div>
                </div>
            </div>

            <div class="input-area">
                <div class="suggestions">
                    <button class="suggestion" onclick="send('Je veux consulter mon dossier')">
                        <i class="fas fa-search"></i> Consulter dossier
                    </button>
                    <button class="suggestion" onclick="send('Je veux modifier mes informations')">
                        <i class="fas fa-user-edit"></i> Modifier infos
                    </button>
                    <button class="suggestion" onclick="send('Je veux être rappelé')">
                        <i class="fas fa-phone-alt"></i> Être rappelé
                    </button>
                    <button class="suggestion" onclick="send('Aide')">
                        <i class="fas fa-question-circle"></i> Aide
                    </button>
                </div>
                <div class="input-box">
                    <input type="text" id="user-input" placeholder="Écrivez ou parlez..." onkeypress="if(event.key==='Enter')sendMessage()" disabled>
                    <button id="mic-btn" onclick="toggleVoice()" title="Parler">
                        <i class="fas fa-microphone" id="mic-icon"></i>
                    </button>
                    <button id="send-btn" onclick="sendMessage()" disabled>
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </main>
    </div>

    <div class="success-overlay" id="success">
        <div class="success-modal">
            <div class="success-icon">✓</div>
            <div class="success-text">Succès !</div>
        </div>
    </div>

    <script>
        // ========== GESTION DE L'HISTORIQUE (localStorage) ==========
        const STORAGE_KEY = 'sydia_chat_history';
        const MAX_CONVERSATIONS = 20;
        
        let currentSessionId = null;
        let chatHistory = [];
        
        // Charger l'historique depuis localStorage
        function loadHistory() {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                try {
                    chatHistory = JSON.parse(saved);
                } catch(e) {
                    chatHistory = [];
                }
            }
            renderHistory();
        }
        
        // Sauvegarder l'historique dans localStorage
        function saveHistory() {
            // Limiter à MAX_CONVERSATIONS
            if (chatHistory.length > MAX_CONVERSATIONS) {
                chatHistory = chatHistory.slice(0, MAX_CONVERSATIONS);
            }
            localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
            renderHistory();
        }
        
        // Afficher l'historique dans la sidebar
        function renderHistory() {
            const container = document.getElementById('history-container');
            
            if (chatHistory.length === 0) {
                container.innerHTML = `
                    <div class="history-empty">
                        <i class="fas fa-comments"></i>
                        <p>Aucune conversation<br>Commencez à discuter !</p>
                    </div>
                `;
                return;
            }
            
            // Grouper par date
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            
            const groups = {
                today: [],
                yesterday: [],
                thisWeek: [],
                older: []
            };
            
            chatHistory.forEach(conv => {
                const convDate = new Date(conv.timestamp);
                if (isSameDay(convDate, today)) {
                    groups.today.push(conv);
                } else if (isSameDay(convDate, yesterday)) {
                    groups.yesterday.push(conv);
                } else if (isThisWeek(convDate)) {
                    groups.thisWeek.push(conv);
                } else {
                    groups.older.push(conv);
                }
            });
            
            let html = '';
            
            if (groups.today.length > 0) {
                html += renderGroup('📅 Aujourd\\'hui', groups.today);
            }
            if (groups.yesterday.length > 0) {
                html += renderGroup('📅 Hier', groups.yesterday);
            }
            if (groups.thisWeek.length > 0) {
                html += renderGroup('📅 Cette semaine', groups.thisWeek);
            }
            if (groups.older.length > 0) {
                html += renderGroup('📅 Plus ancien', groups.older);
            }
            
            container.innerHTML = html;
        }
        
        function renderGroup(label, conversations) {
            let html = `<div class="history-group"><div class="history-label">${label}</div>`;
            
            conversations.forEach(conv => {
                const isActive = conv.id === currentSessionId ? 'active' : '';
                const time = formatTime(conv.timestamp);
                const icon = getConversationIcon(conv.title);
                
                html += `
                    <div class="history-item ${isActive}" onclick="loadConversation('${conv.id}')">
                        <div class="history-icon"><i class="fas ${icon}"></i></div>
                        <div class="history-text">
                            <div class="history-title">${escapeHtml(conv.title)}</div>
                            <div class="history-time">${time}</div>
                        </div>
                        <button class="history-delete" onclick="event.stopPropagation(); deleteConversation('${conv.id}')" title="Supprimer">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
            });
            
            html += '</div>';
            return html;
        }
        
        function getConversationIcon(title) {
            const t = title.toLowerCase();
            if (t.includes('sinistre') || t.includes('dossier')) return 'fa-folder-open';
            if (t.includes('modifier') || t.includes('modification')) return 'fa-user-edit';
            if (t.includes('rappel') || t.includes('téléphone')) return 'fa-phone';
            if (t.includes('document')) return 'fa-file-alt';
            if (t.includes('clôture') || t.includes('fermer')) return 'fa-times-circle';
            return 'fa-comment';
        }
        
        function isSameDay(d1, d2) {
            return d1.getDate() === d2.getDate() && 
                   d1.getMonth() === d2.getMonth() && 
                   d1.getFullYear() === d2.getFullYear();
        }
        
        function isThisWeek(date) {
            const now = new Date();
            const weekStart = new Date(now);
            weekStart.setDate(now.getDate() - now.getDay());
            return date >= weekStart;
        }
        
        function formatTime(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Créer une nouvelle conversation
        function newConversation() {
            currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            
            // Reset le chat
            const chat = document.getElementById('chat');
            const typingMsg = document.getElementById('typing-msg');
            chat.innerHTML = '';
            
            // Message de bienvenue
            addMsg('**Bonjour ! 👋**\\n\\nJe suis votre assistant Sydia IA. Comment puis-je vous aider ?', false);
            
            chat.appendChild(typingMsg);
            
            // Créer l'entrée dans l'historique
            const newConv = {
                id: currentSessionId,
                title: 'Nouvelle conversation',
                timestamp: Date.now(),
                messages: []
            };
            
            chatHistory.unshift(newConv);
            saveHistory();
            
            document.getElementById('user-input').focus();
        }
        
        // Charger une conversation existante
        function loadConversation(id) {
            const conv = chatHistory.find(c => c.id === id);
            if (!conv) return;
            
            currentSessionId = id;
            
            // Reset le chat
            const chat = document.getElementById('chat');
            const typingMsg = document.getElementById('typing-msg');
            chat.innerHTML = '';
            
            // Recharger les messages
            if (conv.messages && conv.messages.length > 0) {
                conv.messages.forEach(msg => {
                    addMsg(msg.content, msg.isUser, false);
                });
            } else {
                addMsg('**Conversation reprise**\\n\\nContinuez où vous vous êtes arrêté.', false, false);
            }
            
            chat.appendChild(typingMsg);
            renderHistory();
        }
        
        // Supprimer une conversation
        function deleteConversation(id) {
            if (!confirm('Supprimer cette conversation ?')) return;
            
            chatHistory = chatHistory.filter(c => c.id !== id);
            saveHistory();
            
            if (id === currentSessionId) {
                newConversation();
            }
        }
        
        // Effacer la conversation actuelle
        function clearCurrentChat() {
            if (!confirm('Effacer cette conversation ?')) return;
            
            const conv = chatHistory.find(c => c.id === currentSessionId);
            if (conv) {
                conv.messages = [];
                conv.title = 'Conversation effacée';
                saveHistory();
            }
            
            // Reset le chat
            const chat = document.getElementById('chat');
            const typingMsg = document.getElementById('typing-msg');
            chat.innerHTML = '';
            addMsg('**Conversation effacée**\\n\\nCommencez une nouvelle discussion.', false, false);
            chat.appendChild(typingMsg);
        }
        
        // Mettre à jour le titre de la conversation basé sur le premier message
        function updateConversationTitle(message) {
            const conv = chatHistory.find(c => c.id === currentSessionId);
            if (conv && conv.title === 'Nouvelle conversation') {
                // Extraire un titre du message (premiers 40 caractères)
                let title = message.replace(/[*_#]/g, '').trim();
                if (title.length > 40) {
                    title = title.substring(0, 40) + '...';
                }
                conv.title = title || 'Conversation';
                saveHistory();
            }
        }
        
        // Sauvegarder un message dans l'historique
        function saveMessage(content, isUser) {
            const conv = chatHistory.find(c => c.id === currentSessionId);
            if (conv) {
                if (!conv.messages) conv.messages = [];
                conv.messages.push({ content, isUser, timestamp: Date.now() });
                conv.timestamp = Date.now(); // Mettre à jour le timestamp
                
                // Si c'est le premier message utilisateur, mettre à jour le titre
                if (isUser && conv.messages.filter(m => m.isUser).length === 1) {
                    updateConversationTitle(content);
                }
                
                // Réorganiser pour mettre la conversation active en premier
                chatHistory = chatHistory.filter(c => c.id !== currentSessionId);
                chatHistory.unshift(conv);
                
                saveHistory();
            }
        }
        
        // ========== FONCTIONS CHAT EXISTANTES ==========
        
        async function init() {
            try {
                const r = await fetch('/api/sinistres');
                const d = await r.json();
                if (d.success) {
                    const o = d.sinistres.filter(s => s.statut === 1).length;
                    const c = d.sinistres.length - o;
                    anim('stat-total', d.total);
                    anim('stat-open', o);
                    anim('stat-closed', c);
                    
                    document.getElementById('user-input').disabled = false;
                    document.getElementById('send-btn').disabled = false;
                    document.getElementById('status-txt').textContent = 'Connecté à Sydia';
                }
            } catch(e) {
                console.error('Erreur init:', e);
            }
            
            // Charger l'historique et créer une nouvelle session
            loadHistory();
            
            // Si pas de session active, en créer une nouvelle
            if (!currentSessionId) {
                newConversation();
            }
            
            // Message de bienvenue
            document.getElementById('welcome').innerHTML = '<strong>Bonjour ! 👋</strong><br><br>Je suis votre assistant Sydia IA. Je peux vous aider à :<br><br>• <strong>Consulter</strong> votre dossier<br>• <strong>Modifier</strong> vos informations<br>• <strong>Contacter</strong> votre gestionnaire<br><br><em>Que souhaitez-vous faire ?</em>';
        }
        
        function anim(id, t) {
            const el = document.getElementById(id);
            let c = 0;
            const inc = Math.ceil(t / 20);
            const i = setInterval(() => {
                c += inc;
                if (c >= t) { c = t; clearInterval(i); }
                el.textContent = c;
            }, 40);
        }
        
        function addMsg(txt, isUser, save = true) {
            const chat = document.getElementById('chat');
            const typ = document.getElementById('typing-msg');
            const div = document.createElement('div');
            div.className = 'msg ' + (isUser ? 'user' : 'assistant');
            let fmt = txt.split('**').map((part, i) => i % 2 === 1 ? '<strong>' + part + '</strong>' : part).join('');
            fmt = fmt.split('`').map((part, i) => i % 2 === 1 ? '<code>' + part + '</code>' : part).join('');
            fmt = fmt.split('\\n').join('<br>');
            const now = new Date();
            const t = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
            div.innerHTML = '<div class="msg-avatar">' + (isUser ? '👤' : '🤖') + '</div><div><div class="msg-content">' + fmt + '</div><div class="msg-time"><i class="fas fa-' + (isUser ? 'check-double' : 'clock') + '"></i> ' + t + '</div></div>';
            chat.insertBefore(div, typ);
            chat.scrollTop = chat.scrollHeight;
            
            if (!isUser && txt.includes('✅')) { showOk(); }
            
            // 🔊 VOCALISER LA RÉPONSE DE L'AGENT
            if (!isUser) {
                speakText(txt);
            }
            
            // Sauvegarder dans l'historique
            if (save) {
                saveMessage(txt, isUser);
            }
        }
                
        // ========== TEXT-TO-SPEECH ==========
        function speakText(text) {
            let cleanText = text;
            cleanText = cleanText.split('**').join('');
            cleanText = cleanText.split('`').join('');
            cleanText = cleanText.split('📧').join('');
            cleanText = cleanText.split('📞').join('');
            cleanText = cleanText.split('✅').join('');
            cleanText = cleanText.split('❌').join('');
            cleanText = cleanText.split('🟢').join('');
            cleanText = cleanText.split('🔴').join('');
            cleanText = cleanText.split('⚠️').join('');
            cleanText = cleanText.split('📎').join('');
            cleanText = cleanText.split('📋').join('');
            cleanText = cleanText.split('🎉').join('');
            cleanText = cleanText.split('✏️').join('');
            cleanText = cleanText.split('💰').join('');
            cleanText = cleanText.split('📄').join('');
            cleanText = cleanText.split('📂').join('');
            cleanText = cleanText.split('🤖').join('');
            cleanText = cleanText.split('👤').join('');
            cleanText = cleanText.split('---').join('');
            cleanText = cleanText.split('\\n').join('. ');
            cleanText = cleanText.trim();
            
            if (cleanText.length < 5) return;
            
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = 'fr-FR';
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            const voices = window.speechSynthesis.getVoices();
            const frenchVoice = voices.find(v => v.lang.startsWith('fr'));
            if (frenchVoice) {
                utterance.voice = frenchVoice;
            }
            
            window.speechSynthesis.speak(utterance);
        }

        function showOk() {
            const s = document.getElementById('success');
            s.style.display = 'flex';
            setTimeout(() => { s.style.display = 'none'; }, 1500);
        }
        
        async function sendMessage() {
            const inp = document.getElementById('user-input');
            const m = inp.value.trim();
            if (!m) return;
            inp.value = '';
            document.getElementById('send-btn').disabled = true;
            addMsg(m, true);
            
            const typ = document.getElementById('typing-msg');
            typ.style.display = 'flex';
            document.getElementById('typing-dots').style.display = 'flex';
            document.getElementById('status-txt').textContent = 'En train d\\'écrire...';
            
            try {
                const r = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: m, session_id: currentSessionId })
                });
                const d = await r.json();
                typ.style.display = 'none';
                document.getElementById('typing-dots').style.display = 'none';
                document.getElementById('status-txt').textContent = 'Connecté à Sydia';
                addMsg(d.response, false);
            } catch(e) {
                typ.style.display = 'none';
                addMsg('❌ Erreur de connexion.', false);
            }
            
            document.getElementById('send-btn').disabled = false;
            inp.focus();
        }
        
        function send(t) {
            document.getElementById('user-input').value = t;
            sendMessage();
        }
        // ========== RECONNAISSANCE VOCALE ==========
        let recognition = null;
        let isRecording = false;

        function initVoiceRecognition() {
            if ('webkitSpeechRecognition' in window) {
                recognition = new webkitSpeechRecognition();
                recognition.lang = 'fr-FR';
                recognition.continuous = false;
                recognition.interimResults = true;
                
                recognition.onstart = () => {
                    isRecording = true;
                    document.getElementById('mic-btn').classList.add('recording');
                    document.getElementById('mic-icon').className = 'fas fa-stop';
                    document.getElementById('user-input').placeholder = '🎤 Parlez maintenant...';
                };
                
                recognition.onend = () => {
                    isRecording = false;
                    document.getElementById('mic-btn').classList.remove('recording');
                    document.getElementById('mic-icon').className = 'fas fa-microphone';
                    document.getElementById('user-input').placeholder = 'Écrivez ou parlez...';
                };
                
                recognition.onresult = (event) => {
                    let finalTranscript = '';
                    let interimTranscript = '';
                    
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript;
                        } else {
                            interimTranscript += transcript;
                        }
                    }
                    
                    // Afficher en temps réel
                    document.getElementById('user-input').value = finalTranscript || interimTranscript;
                    
                    // Si final, envoyer automatiquement
                    if (finalTranscript) {
                        setTimeout(() => {
                            sendMessage();
                        }, 500);
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Erreur vocale:', event.error);
                    isRecording = false;
                    document.getElementById('mic-btn').classList.remove('recording');
                    document.getElementById('mic-icon').className = 'fas fa-microphone';
                    
                    if (event.error === 'not-allowed') {
                        alert('⚠️ Autorisez le microphone dans votre navigateur');
                    }
                };
                
                console.log('🎤 Reconnaissance vocale initialisée');
            } else {
                console.warn('❌ Reconnaissance vocale non supportée');
                document.getElementById('mic-btn').style.display = 'none';
            }
        }

        function toggleVoice() {
            if (!recognition) {
                initVoiceRecognition();
            }
            
            if (isRecording) {
                recognition.stop();
            } else {
                recognition.start();
            }
        }

        // Initialiser la reconnaissance vocale au chargement
        initVoiceRecognition();
        // Initialisation
        init();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/sinistres')
def api_sinistres():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(list_sinistres())
    loop.close()
    
    if result["success"]:
        sinistres = [{"id": s.get("id"), "ref": s.get("ref_assureur") or s.get("ref_courtier"), "statut": s.get("statut")} for s in result["data"]]
        return jsonify({"success": True, "total": len(sinistres), "sinistres": sinistres})
    return jsonify({"success": False, "error": result["error"]})


@app.route('/chat', methods=['POST'])
def chat_route():
    data = request.json
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(chat(data.get('session_id', 'default'), data.get('message', '')))
    loop.close()
    return jsonify({'response': response})


@app.route('/api/upload', methods=['POST'])
def upload_route():
    """Upload un document via l'API"""
    data = request.json
    
    async def do_upload():
        upload_data = {
            "id_sinistre": str(data.get("id_sinistre")),
            "filename": data.get("filename"),
            "commentaire": data.get("commentaire", ""),
            "content": data.get("content"),
            "public": "1",
            "notif_gestionnaire": "1",
        }
        
        response = await sydia_call("ged/add", upload_data)
        print(f"DEBUG upload response: {response}")
        
        if response.get("status") == 200:
            return {
                "success": True,
                "id_ged": response.get("id_ged"),
                "id_assure": response.get("id_assure")
            }
        return {"success": False, "error": response.get("message", "Erreur upload")}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(do_upload())
    loop.close()
    return jsonify(result)


if __name__ == '__main__':
    print("=" * 50)
    print("🤖 AGENT SYDIA + WebSocket")
    print("=" * 50)
    print(f"🧠 Modèle: {MODEL}")
    print(f"📡 API: {SYDIA_URL}")
    print(f"📡 WebSocket: Activé")
    print()
    print("🌐 http://localhost:5000")
    print()
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
