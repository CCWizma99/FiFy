import sqlite3
import os
from pathlib import Path
from vector_db.schema import create_collection
from backend.utils.logger import get_logger

logger = get_logger("reset_system")

def reset_database():
    db_path = Path("data/job_status.db")
    if not db_path.exists():
        logger.info("Database file not found, skipping reset.")
        return

    logger.info("Clearing SQLite database tables...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear jobs and hashes, but keep target_sites for easy restart
        cursor.execute("DELETE FROM scrape_jobs")
        cursor.execute("DELETE FROM url_hashes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('scrape_jobs')")
        
        conn.commit()
        conn.close()
        logger.info("Successfully cleared scrape_jobs and url_hashes.")
    except Exception as e:
        logger.error(f"Error resetting database: {e}")

def clear_logs():
    log_files = [
        Path("logs/fify.log"),
        Path("data/dead_letter.log")
    ]
    
    for log_file in log_files:
        if log_file.exists():
            logger.info(f"Truncating log file: {log_file}")
            with open(log_file, "w") as f:
                f.write("")
        else:
            logger.info(f"Log file not found: {log_file}")

def main():
    logger.info("Starting system reset...")
    
    # 1. Reset Qdrant
    logger.info("Resetting Qdrant collection...")
    try:
        create_collection(recreate=True)
        logger.info("Qdrant collection reset successfully.")
    except Exception as e:
        logger.error(f"Error resetting Qdrant: {e}")
    
    # 2. Reset SQLite
    reset_database()
    
    # 3. Clear Logs
    clear_logs()
    
    logger.info("System reset complete. You can now start the services for a fresh start.")

if __name__ == "__main__":
    main()
