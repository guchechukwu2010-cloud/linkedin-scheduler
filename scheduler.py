from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import time
from database import SessionLocal, Campaign, ConnectionLog, User
from linkedin_api import LinkedInAPI

class SchedulerManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        print("Scheduler started")
    
    def schedule_campaign(self, campaign_id: int, user_id: int, cron_expression: str = "0 9 * * *"):
        """Schedule a campaign to run daily at 9 AM"""
        
        def run_campaign():
            db = SessionLocal()
            try:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                user = db.query(User).filter(User.id == user_id).first()
                
                if not campaign or not user or campaign.status != "active":
                    return
                
                # Get LinkedIn API client
                api = LinkedInAPI(user.linkedin_access_token)
                
                # Search for people
                profiles = api.search_people(campaign.search_query, limit=campaign.daily_limit)
                
                # Send connection requests
                for profile in profiles[:campaign.daily_limit]:
                    # Personalize message
                    message = campaign.message_template.replace(
                        "{firstName}", profile.get("firstName", "")
                    ).replace(
                        "{headline}", profile.get("headline", "")
                    )
                    
                    # Send request
                    success = api.send_connection_request(profile["id"], message)
                    
                    # Log it
                    log = ConnectionLog(
                        campaign_id=campaign_id,
                        profile_url=profile.get("profileUrl", ""),
                        message_sent=message,
                        status="sent" if success else "failed",
                        sent_at=datetime.utcnow()
                    )
                    db.add(log)
                
                db.commit()
                print(f"Campaign {campaign_id} executed successfully")
                
            except Exception as e:
                print(f"Error executing campaign {campaign_id}: {e}")
            finally:
                db.close()
        
        # Add job to scheduler
        self.scheduler.add_job(
            run_campaign,
            CronTrigger.from_crontab(cron_expression),
            id=f"campaign_{campaign_id}"
        )
        print(f"Campaign {campaign_id} scheduled with cron: {cron_expression}")
    
    def remove_campaign(self, campaign_id: int):
        """Remove a campaign from scheduler"""
        job_id = f"campaign_{campaign_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            print(f"Campaign {campaign_id} removed from scheduler")

# Global scheduler instance
scheduler_manager = SchedulerManager()