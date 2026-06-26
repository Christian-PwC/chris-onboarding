# src/routers/profile.py
from fastapi import APIRouter, Depends
from datetime import datetime
from src.models.schemas import ProfileUpdateRequest
from src.dependencies.auth import get_current_user
from src.services.cosmos_connector import cosmos_connector  

DATABASE_NAME = "users"
USER_CONTAINER_NAME = "users_list"

router = APIRouter(
    tags=["User Profile"]
)

@router.post("/update_profile")
def update_profile(data: ProfileUpdateRequest, current_user: str = Depends(get_current_user)):
    try:
        user_id = current_user
        
        user_document = cosmos_connector.get_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item_id=user_id,
            partition_key=user_id
        )
        
        user_document["favorite_movies"] = data.favorite_movies
        user_document["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        cosmos_connector.upsert_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item=user_document
        )
        return {"success": True, "message": "Profilo aggiornato con successo"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/get_profile")
def get_profile(current_user: str = Depends(get_current_user)):
    try:
        user_id = current_user
        
        user_document = cosmos_connector.get_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item_id=user_id,
            partition_key=user_id
        )
        
        fav_movies = user_document.get("favorite_movies", [])
        return {
            "success": True, 
            "favorite_movies": fav_movies
        }
    except Exception as e:
        return {
            "success": False, 
            "favorite_movies": [], 
            "error": str(e)
        }