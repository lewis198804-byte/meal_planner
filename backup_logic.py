import shutil
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timezone
import sqlite3
#---------------------code dealing with backup for recipe DB-----------------------



now = datetime.now(timezone.utc)


jobstore = {
    'default': SQLAlchemyJobStore(url='sqlite:///database.db')
}
scheduler = BackgroundScheduler(timezone=timezone.utc)
scheduler.configure(jobstores=jobstore)


def backup_recipe_db():
    print("scheduled print command")


def start_scheduler():

    scheduler.start()
    backupJob = scheduler.get_job("backup_job")
    
    if backupJob.next_run_time < now:
        #backup time has already passed, reset job with new backup time. could have occurred by the program being offline for 
        #extended period of time and missing a backup job. 
        con = sqlite3.connect("database.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        grabFreq = cur.execute("SELECT backup_frequency FROM settings")
        freqRes = grabFreq.fetchone()
        scheduler.add_job(backup_recipe_db, "interval", days=freqRes['backup_freq'],id="backup_job", replace_existing=True)
        con.close()
    else:
        pass
        #backup time is in the future so no need to do anything

def turnOffBackups():
    scheduler.remove_all_jobs()
    print("backup job removed")
    if scheduler.running:
        scheduler.shutdown()
        print("scheduler shutdown")
    
def getNextBackupTime():
    backupJob = scheduler.get_job("backup_job")
    return backupJob.next_run_time.ctime()

def turn_on_backups(interval:int):
    scheduler.add_job(backup_recipe_db, "interval", days=interval,id="backup_job", replace_existing=True)
    if scheduler.state is 0:
        start_scheduler()
    backupJob = scheduler.get_job("backup_job")
    return backupJob.next_run_time
    

    
def schedulerStatus():
    backupJob = scheduler.get_job("backup_job")

    if backupJob is not None:
        con = sqlite3.connect("database.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT next_run_time FROM apscheduler_jobs WHERE id = ?",("backup_job",))
        nextRes = cur.fetchone()
        nextBackup = datetime.fromtimestamp(nextRes['next_run_time']).isoformat()
      
        
        con.close()
    else:
        nextBackup = "No Backup scheduled"
    backupDeets = {"scheduler_status": scheduler.state, "next_backup": nextBackup}
    return backupDeets


