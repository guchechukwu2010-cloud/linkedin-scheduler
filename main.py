from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from fastapi import HTTPException


# Load environment variables
load_dotenv()

# Import database and scheduler
from database import SessionLocal, engine, Base, User, Campaign, ConnectionLog
from linkedin_api import LinkedInAPI
from scheduler import scheduler_manager

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinkedIn Scheduler Pro")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Templates
templates = Jinja2Templates(directory="templates")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Login/Register
@app.post("/login")
async def login(email: str = Form(...), db: Session = Depends(get_db)):
    # Simple auth for MVP
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Set user in session (simplified for MVP)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="user_id", value=str(user.id))
    return response

# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse(url="/")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).all()
    
    # Get stats
    total_requests = db.query(ConnectionLog).join(Campaign).filter(Campaign.user_id == user.id).count()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "campaigns": campaigns,
        "total_requests": total_requests
    })

# Create Campaign
@app.post("/campaigns/create")
async def create_campaign(
    request: Request,
    name: str = Form(...),
    search_query: str = Form(...),
    message_template: str = Form(...),
    daily_limit: int = Form(20),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Create campaign
    campaign = Campaign(
        user_id=int(user_id),
        name=name,
        search_query=search_query,
        message_template=message_template,
        daily_limit=daily_limit
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Schedule it
    scheduler_manager.schedule_campaign(campaign.id, int(user_id))
    
    return RedirectResponse(url="/dashboard", status_code=302)

# Connect LinkedIn
@app.get("/connect-linkedin")
async def connect_linkedin():
    """Redirect to LinkedIn OAuth"""
    # LinkedIn OAuth URL (you'll need to set this up)
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "your_client_id")
    redirect_uri = "http://localhost:8000/linkedin-callback"
    scope = "r_liteprofile%20r_emailaddress%20w_member_social"
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
    
    return RedirectResponse(url=auth_url)

# LinkedIn callback
@app.get("/linkedin-callback")
async def linkedin_callback(code: str, request: Request, db: Session = Depends(get_db)):
    """Handle LinkedIn OAuth callback"""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse(url="/")
    
    # TODO: Exchange code for access token
    # For MVP, we'll use a mock token
    access_token = "mock_access_token_12345"
    
    # Save to user
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user:
        user.linkedin_access_token = access_token
        db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=302)

# API endpoints for frontend
@app.get("/api/stats")
async def get_stats(user_id: int, db: Session = Depends(get_db)):
    """Get user statistics"""
    campaigns = db.query(Campaign).filter(Campaign.user_id == user_id).all()
    total_requests = db.query(ConnectionLog).join(Campaign).filter(Campaign.user_id == user_id).count()
    
    return {
        "campaigns_count": len(campaigns),
        "total_requests": total_requests,
        "active_campaigns": len([c for c in campaigns if c.status == "active"])
    }

@app.get("/api/campaigns/{campaign_id}/logs")
async def get_campaign_logs(campaign_id: int, db: Session = Depends(get_db)):
    """Get logs for a campaign"""
    logs = db.query(ConnectionLog).filter(ConnectionLog.campaign_id == campaign_id).order_by(ConnectionLog.sent_at.desc()).limit(50).all()
    return {"logs": [
        {
            "profile_url": log.profile_url,
            "message": log.message_sent,
            "status": log.status,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None
        } for log in logs
    ]}

# ===== FIXED PART - THIS MUST BE AT THE BOTTOM =====
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 LinkedIn Scheduler Pro")
    print("=" * 50)
    print("Starting server on http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)