from fastapi import FastAPI
from typing import List
import logging

# Configure logging for DrTrace
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cross-Language Example Backend")

# In-memory user store
users: dict = {}
next_user_id = 1

@app.on_event("startup")
async def startup_event():
    logger.info("API backend starting up")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API backend shutting down")

@app.get("/health")
async def health_check():
    logger.debug("Health check requested")
    return {"status": "healthy"}

@app.post("/api/users")
async def create_user(name: str):
    global next_user_id
    logger.info(f"Creating user with name: {name}")
    
    # Validate input
    if not name or len(name) < 1:
        logger.warning(f"Invalid name provided: {name}")
        return {"error": "Name must not be empty"}, 400
    
    user_id = next_user_id
    users[user_id] = {"id": user_id, "name": name}
    next_user_id += 1
    
    logger.info(f"User created successfully: id={user_id}, name={name}")
    return {"id": user_id, "name": name}

@app.get("/api/users")
async def list_users():
    logger.debug(f"Listing {len(users)} users")
    return {"users": list(users.values())}

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    logger.debug(f"Fetching user: id={user_id}")
    
    if user_id not in users:
        logger.warning(f"User not found: id={user_id}")
        return {"error": "User not found"}, 404
    
    logger.debug(f"User found: {users[user_id]}")
    return users[user_id]

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, name: str):
    logger.info(f"Updating user: id={user_id}, new_name={name}")
    
    if user_id not in users:
        logger.warning(f"Cannot update non-existent user: id={user_id}")
        return {"error": "User not found"}, 404
    
    users[user_id]["name"] = name
    logger.info(f"User updated: id={user_id}, new_name={name}")
    return users[user_id]

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    logger.info(f"Deleting user: id={user_id}")
    
    if user_id not in users:
        logger.warning(f"Cannot delete non-existent user: id={user_id}")
        return {"error": "User not found"}, 404
    
    deleted = users.pop(user_id)
    logger.info(f"User deleted: id={user_id}, name={deleted['name']}")
    return {"message": "User deleted", "user": deleted}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server on http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
