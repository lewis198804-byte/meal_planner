import shutil
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

#---------------------code dealing with backup for recipe DB-----------------------




jobstore = {
    'default': SQLAlchemyJobStore(url='sqlite:///database.db')
}
scheduler = BackgroundScheduler()
scheduler.configure(jobstores=jobstore)


def backup_recipe_db():
    print("scheduled print command")


def start_scheduler():
    scheduler.start()

def turnOffBackups():
    scheduler.remove_all_jobs()
    print("backup job removed")
    if scheduler.running:
        scheduler.shutdown()
        print("scheduler shutdown")
    
def getNextBackupTime():
    backupJob = scheduler.get_job("backup_job")
    return backupJob.next_run_time.ctime()

def turn_on_backups(interval):
    scheduler.add_job(backup_recipe_db, "interval", days=interval,id="backup_job", replace_existing=True)
    start_scheduler()
    backupJob = scheduler.get_job("backup_job")
    
    return backupJob.next_run_time.ctime()
    

    
def schedulerStatus():
    return scheduler.state


