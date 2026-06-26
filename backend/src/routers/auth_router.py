# src/routers/auth.py
from fastapi import APIRouter
from datetime import datetime
from src.models.schemas import LoginRequest
from src.services.cosmos_connector import cosmos_connector  
from src.services.auth_service import verify_password, create_access_token, hash_password

DATABASE_NAME = "users"
USER_CONTAINER_NAME = "users_list"

router = APIRouter(
    tags=["Authentication"]
)

@router.post("/register")
def register_user(credentials: LoginRequest):
    try:
        try:
            existing_user = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=credentials.user_id,
                partition_key=credentials.user_id  
            )
            if existing_user:
                return {"success": False, "error": "Questo User ID è già registrato."}
        except Exception:
            pass

        password_encrypted = hash_password(credentials.password)

        user_document = {
            "id": credentials.user_id,          
            "user_id": credentials.user_id,     
            "password_hash": password_encrypted,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }

        cosmos_connector.upsert_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item=user_document
        )
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/login")
def login(credentials: LoginRequest):
    try:
        try:
            user_document = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=credentials.user_id,
                partition_key=credentials.user_id
            )
        except Exception:
            return {"success": False, "error": "User ID o Password errati (Utente non trovato)"}
        
        db_hash = user_document.get("password_hash")
        
        if verify_password(credentials.password, db_hash):
            token = create_access_token(
                user_id=credentials.user_id,
                email=f"{credentials.user_id}@azienda.com",
                name=credentials.user_id,
                is_global_admin=False,
            )
            return {"success": True, "access_token": token, "user_id": credentials.user_id}
        
        return {"success": False, "error": "User ID o Password errati"}
    except Exception as e:
        return {"success": False, "error": str(e)}