#!/usr/bin/env python3
"""
Daily Log Entry Script
Adds formatted log entries to docs-wip.md at midnight Stockholm time
and commits/pushes changes to Git Development branch.
"""

import os
import sys
import subprocess
import schedule
import time
from datetime import datetime
import pytz
import random
import json
from pathlib import Path

# Configuration
DOCS_FILE = "../docs/docs-wip.md"
GIT_BRANCH = "Development"
GIT_REMOTE = "origin"

def load_config():
    """Load configuration from config.json file"""
    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    
    # Default configuration
    default_config = {
        "git_username": "christerjohansson",
        "git_email": "christer.johansson@stenungsund.nu",
        "ssh_key_file": "masterKey",
        "repository_url": "git@github.com:christerjohansson/ai-product-requirement-document.git"
    }
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading config file: {e}")
            print("Creating default config.json file...")
    
    # Create default config file
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=4)
    print(f"Created {config_file} - Please update it with your actual credentials")
    return default_config

# Load configuration
config = load_config()
GIT_USERNAME = config["git_username"]
GIT_EMAIL = config["git_email"]
SSH_KEY_FILE = config["ssh_key_file"]
REPOSITORY_URL = config["repository_url"]

# Validate SSH key file exists
script_dir = Path(__file__).parent
ssh_key_path = script_dir / SSH_KEY_FILE
if not ssh_key_path.exists():
    print(f"Warning: SSH key file '{SSH_KEY_FILE}' not found in {script_dir}")
    print("Please ensure the SSH key file is present for Git authentication")

def setup_ssh_agent():
    """Set up SSH agent with the master key for Git authentication"""
    script_dir = Path(__file__).parent
    ssh_key_path = script_dir / SSH_KEY_FILE
    
    if not ssh_key_path.exists():
        print(f"SSH key file {ssh_key_path} not found")
        return False
    
    try:
        # Set proper permissions on SSH key (required for SSH)
        os.chmod(ssh_key_path, 0o600)
        
        # Set up SSH environment variables for Git
        ssh_command = f'ssh -i "{ssh_key_path}" -o StrictHostKeyChecking=no'
        os.environ['GIT_SSH_COMMAND'] = ssh_command
        
        print(f"SSH agent configured with key: {ssh_key_path}")
        return True
    except Exception as e:
        print(f"Error setting up SSH agent: {e}")
        return False

def setup_git_credentials():
    """Configure Git with credentials and SSH"""
    try:
        subprocess.run(["git", "config", "user.name", GIT_USERNAME], check=True)
        subprocess.run(["git", "config", "user.email", GIT_EMAIL], check=True)
        print("Git credentials configured successfully")
        
        # Set up SSH for Git operations
        if not setup_ssh_agent():
            print("Failed to setup SSH agent")
            return False
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error configuring Git credentials: {e}")
        return False

def get_stockholm_time():
    """Get current time in Stockholm timezone"""
    stockholm_tz = pytz.timezone('Europe/Stockholm')
    return datetime.now(stockholm_tz)

def generate_order_number():
    """Generate a random order number"""
    return random.randint(100, 999)

def create_log_entry():
    """Create formatted log entry"""
    stockholm_time = get_stockholm_time()
    date_str = stockholm_time.strftime("%Y%m%d")
    time_str = stockholm_time.strftime("%H:%M")
    order_num = generate_order_number()
    
    log_entry = f"{date_str} | {time_str} | Status: Log entry is entered successfully. | Order: {order_num}\n"
    return log_entry

def append_to_docs_file(log_entry):
    """Append log entry to docs-wip.md file"""
    try:
        # Get the absolute path to the docs file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        docs_path = os.path.join(script_dir, DOCS_FILE)
        
        # Create the file if it doesn't exist
        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
        
        # Append the log entry
        with open(docs_path, 'a', encoding='utf-8') as file:
            file.write(log_entry)
        
        print(f"Log entry added to {docs_path}")
        return True
    except Exception as e:
        print(f"Error writing to docs file: {e}")
        return False

def git_commit_and_push():
    """Commit changes and push to Development branch"""
    try:
        # Change to the project root directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        os.chdir(project_root)
        
        # Check if we're in a git repository
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Not in a Git repository")
            return False
        
        # Switch to Development branch (create if doesn't exist)
        try:
            subprocess.run(["git", "checkout", GIT_BRANCH], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Branch doesn't exist, create it
            subprocess.run(["git", "checkout", "-b", GIT_BRANCH], check=True, capture_output=True)
        
        # Add the docs file
        subprocess.run(["git", "add", "docs/docs-wip.md"], check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode == 0:
            print("No changes to commit")
            return True
        
        # Commit changes
        stockholm_time = get_stockholm_time()
        commit_message = f"Daily log entry - {stockholm_time.strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Push to remote using SSH
        # Set up remote URL for SSH authentication
        subprocess.run(["git", "remote", "set-url", GIT_REMOTE, REPOSITORY_URL], check=True)
        subprocess.run(["git", "push", GIT_REMOTE, GIT_BRANCH], check=True)
        
        print(f"Successfully committed and pushed to {GIT_BRANCH} branch")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during Git operations: {e}")
        return False

def daily_log_task():
    """Main task to run daily at midnight"""
    print(f"Running daily log task at {get_stockholm_time()}")
    
    # Generate and append log entry
    log_entry = create_log_entry()
    print(f"Generated log entry: {log_entry.strip()}")
    
    if append_to_docs_file(log_entry):
        # Commit and push to Git
        if git_commit_and_push():
            print("Daily log task completed successfully")
        else:
            print("Daily log task completed but Git operations failed")
    else:
        print("Daily log task failed - could not write to file")

def run_scheduler():
    """Run the scheduler"""
    print("Starting daily log scheduler...")
    print("Scheduled to run at midnight Stockholm time")
    
    # Schedule the task for midnight Stockholm time
    schedule.every().day.at("00:00").do(daily_log_task)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def run_once():
    """Run the task once for testing"""
    print("Running task once for testing...")
    setup_git_credentials()
    daily_log_task()

if __name__ == "__main__":
    # Setup Git credentials
    if not setup_git_credentials():
        print("Failed to setup Git credentials. Please check configuration.")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\nScheduler stopped by user")
        except Exception as e:
            print(f"Scheduler error: {e}")