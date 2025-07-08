from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from db.database import DatabaseHandler
from fetching.new_pools import GeckoTerminalAPI
from services.token_updater import TokenUpdater
import time
import schedule
import pandas as pd
import threading
from typing import Dict
import uvicorn
from rugcheck import RugcheckAPI  # Add this import at the top
import asyncio

app = FastAPI()

# 1. First, add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Define API routes BEFORE static files
@app.get("/api/tokens")
async def get_tokens():
    try:
        db = DatabaseHandler()
        tokens = db.get_all_tokens()
        # Sort tokens by created_at before returning
        sorted_tokens = sorted(
            tokens, 
            key=lambda x: x['created_at'], 
            reverse=True
        )
        # Add debug logging
        print("Sample token data:", tokens[0] if tokens else "No tokens")
        return {"tokens": sorted_tokens}
    except Exception as e:
        print(f"Error in get_tokens: {str(e)}")
        return {"error": str(e)}

@app.get("/api/test")
async def test_endpoint():
    return {"status": "ok", "message": "API is working"}

@app.get("/api/db-status")
async def db_status():
    try:
        db = DatabaseHandler()
        count = len(db.get_all_tokens())
        return {
            "status": "connected",
            "token_count": count
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Add these global variables after existing imports
session_active = True
scheduler_thread = None
scheduler_lock = threading.Lock()

# Add these new endpoints before the static file mounting
@app.post("/api/session/stop")
async def stop_session():
    global session_active, scheduler_thread
    with scheduler_lock:
        session_active = False
        if scheduler_thread and scheduler_thread.is_alive():
            scheduler_thread = None
    return {"active": False, "status": "stopped"}

@app.post("/api/session/start")
async def start_session():
    global session_active, scheduler_thread
    with scheduler_lock:
        session_active = True
        if not scheduler_thread or not scheduler_thread.is_alive():
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
    return {"active": True, "status": "started"}

@app.get("/api/session/status")
async def get_session_status():
    return {"active": session_active}

# Add this new endpoint with the other API endpoints
@app.post("/api/database/clear")
async def clear_database():
    try:
        db = DatabaseHandler()
        db.clear_database()  # We'll add this method next
        return {"status": "success", "message": "Database cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add this new endpoint with other API routes
@app.get("/api/tokens/{token_address}/rugcheck")
async def get_token_rugcheck(token_address: str):
    try:
        rugcheck = RugcheckAPI()
        
        # Add delay between requests to avoid rate limiting
        await asyncio.sleep(1)
        
        try:
            report = rugcheck.get_token_report(token_address)
            
            # Validate report structure
            if not isinstance(report, dict):
                print(f"Invalid report format for {token_address}: {report}")
                raise HTTPException(status_code=503, detail="Invalid API response format")
            
            # Extract token data with safe fallbacks
            token_data = report.get("token", {}) or {}
            total_supply = int(token_data.get("supply", 1))
            decimals = int(token_data.get("decimals", 0))
            total_supply_ui = total_supply / (10 ** decimals)
            
            # Process risks with validation
            risks = report.get("risks", []) or []
            filtered_risks = [
                risk for risk in risks 
                if isinstance(risk, dict) and 
                risk.get('name') not in ["Low Liquidity", "Low amount of LP Providers"]
            ]
            
            # Process insider networks with validation
            insider_networks = report.get("insiderNetworks", []) or []
            processed_networks = []
            
            for network in insider_networks:
                if isinstance(network, dict):
                    token_amount = int(network.get("tokenAmount", 0))
                    processed_networks.append({
                        "type": network.get("type", "Unknown"),
                        "token_amount": token_amount / (10 ** decimals),
                        "token_percentage": (token_amount / total_supply * 100) if total_supply > 0 else 0,
                        "distributed_to": network.get("activeAccounts", 0)
                    })
            
            return {
                "risks": filtered_risks,
                "creator_tokens": report.get("creatorTokens", []) or [],
                "insider_networks": processed_networks
            }
            
        except Exception as e:
            print(f"Rugcheck API error for {token_address}: {str(e)}")
            raise HTTPException(
                status_code=503, 
                detail=f"Rugcheck API error: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in rugcheck endpoint for {token_address}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

# 3. Mount static files AFTER API routes
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("frontend/dist/index.html")

@app.on_event("startup")
async def startup_event():
    global scheduler_thread
    print("Starting application...")
    # Initial runs
    fetch_new_tokens()
    update_existing_tokens()
    
    # Schedule tasks
    schedule.every(5).seconds.do(fetch_new_tokens)
    schedule.every(1).minutes.do(update_existing_tokens)
    
    # Start scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

def fetch_new_tokens():
    """Fetch and store new tokens"""
    db = DatabaseHandler()
    api = GeckoTerminalAPI()
    
    # Get new pools data
    new_pools_df = api.get_new_pools()
    
    # Add each new pool to database
    for _, pool in new_pools_df.iterrows():
        db.add_token(pool)

def update_existing_tokens():
    """Update existing token information"""
    try:
        print("Starting token update cycle...")
        updater = TokenUpdater()
        db = DatabaseHandler()
        
        # Get all tokens that need updating
        all_tokens = db.get_all_tokens()
        current_time = pd.Timestamp.now(tz='UTC')
        
        for token in all_tokens:
            try:
                # Convert last_updated to timestamp
                last_updated = pd.to_datetime(token['last_updated'])
                
                # Calculate time difference in minutes
                time_diff = (current_time - last_updated).total_seconds() / 60
                
                # Update if token is older than 5 minutes
                if time_diff > 3:
                    print(f"Updating token: {token['name']} ({token['address']})")
                    updater.update_token(token['address'])
                    time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"Error updating token {token.get('name', 'unknown')}: {str(e)}")
                continue
        
        print("Token update cycle completed")
    except Exception as e:
        print(f"Error in update cycle: {str(e)}")

# Background task to run the scheduler
def run_scheduler():
    global session_active
    while True:
        if not session_active:
            time.sleep(1)
            continue
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects $PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port)
