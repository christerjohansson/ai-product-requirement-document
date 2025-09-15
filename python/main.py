#!/usr/bin/env python3
"""
Daily Log Entry Script

This script adds formatted log entries to docs-wip.md at midnight Stockholm time
and commits/pushes changes to the Git Development branch.

Features:
- Timezone-aware logging (Stockholm time)
- SSH key authentication for Git operations
- Configurable via config.json
- Scheduler for daily execution
- One-time execution mode for testing
"""

import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pytz
import schedule


class Config:
    """Configuration management for the daily log script."""
    
    DEFAULT_CONFIG = {
        "git_username": "christerjohansson",
        "git_email": "christer.johansson@stenungsund.nu",
        "ssh_key_file": "synology_key",
        "repository_url": "git@github.com:christerjohansson/ai-product-requirement-document.git"
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, str]:
        """Load configuration from config.json file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error reading config file: {e}")
                print("Creating default config.json file...")
        
        # Create default config file
        self._create_default_config()
        return self.DEFAULT_CONFIG
    
    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.DEFAULT_CONFIG, f, indent=4)
        print(f"Created {self.config_path} - Please update it with your actual credentials")
    
    def get(self, key: str) -> str:
        """Get a configuration value."""
        return self.config.get(key, self.DEFAULT_CONFIG.get(key, ""))


class GitManager:
    """Handles Git operations with SSH authentication."""
    
    def __init__(self, config: Config):
        self.config = config
        self.git_branch = "Development"
        self.git_remote = "origin"
        self.docs_file = "../docs/docs-wip.md"
    
    def setup_credentials(self) -> bool:
        """Configure Git with credentials and SSH."""
        try:
            subprocess.run(["git", "config", "user.name", self.config.get("git_username")], check=True)
            subprocess.run(["git", "config", "user.email", self.config.get("git_email")], check=True)
            print("Git credentials configured successfully")
            
            if not self._setup_ssh_agent():
                print("Failed to setup SSH agent")
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error configuring Git credentials: {e}")
            return False
    
    def _setup_ssh_agent(self) -> bool:
        """Set up SSH agent with the configured key for Git authentication."""
        script_dir = Path(__file__).parent
        ssh_key_path = script_dir / self.config.get("ssh_key_file")
        
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
    
    def commit_and_push(self) -> bool:
        """Commit changes and push to Development branch."""
        try:
            # Change to the project root directory
            script_dir = Path(__file__).parent
            project_root = script_dir.parent
            os.chdir(project_root)
            
            # Check if we're in a git repository
            result = subprocess.run(["git", "status"], capture_output=True, text=True)
            if result.returncode != 0:
                print("Not in a Git repository")
                return False
            
            # Switch to Development branch (create if doesn't exist)
            self._ensure_branch_exists()
            
            # Add the docs file
            subprocess.run(["git", "add", "docs/docs-wip.md"], check=True)
            
            # Check if there are changes to commit
            result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
            if result.returncode == 0:
                print("No changes to commit")
                return True
            
            # Commit and push changes
            self._commit_changes()
            self._push_to_remote()
            
            print(f"Successfully committed and pushed to {self.git_branch} branch")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during Git operations: {e}")
            return False
    
    def _ensure_branch_exists(self) -> None:
        """Ensure the Development branch exists and switch to it."""
        try:
            subprocess.run(["git", "checkout", self.git_branch], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Branch doesn't exist, create it
            subprocess.run(["git", "checkout", "-b", self.git_branch], check=True, capture_output=True)
    
    def _commit_changes(self) -> None:
        """Commit the changes with a timestamped message."""
        stockholm_time = LogEntryGenerator.get_stockholm_time()
        commit_message = f"Daily log entry - {stockholm_time.strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
    
    def _push_to_remote(self) -> None:
        """Push changes to the remote repository."""
        # Set up remote URL for SSH authentication
        subprocess.run(["git", "remote", "set-url", self.git_remote, self.config.get("repository_url")], check=True)
        subprocess.run(["git", "push", self.git_remote, self.git_branch], check=True)


class LogEntryGenerator:
    """Generates and manages log entries."""
    
    @staticmethod
    def get_stockholm_time() -> datetime:
        """Get current time in Stockholm timezone."""
        stockholm_tz = pytz.timezone('Europe/Stockholm')
        return datetime.now(stockholm_tz)
    
    @staticmethod
    def generate_order_number() -> int:
        """Generate a random order number."""
        return random.randint(100, 999)
    
    @classmethod
    def create_log_entry(cls) -> str:
        """Create a formatted log entry."""
        stockholm_time = cls.get_stockholm_time()
        date_str = stockholm_time.strftime("%Y%m%d")
        time_str = stockholm_time.strftime("%H:%M")
        order_num = cls.generate_order_number()
        
        return f"{date_str} | {time_str} | Status: Log entry is entered successfully. | Order: {order_num}\n"


class FileManager:
    """Handles file operations for log entries."""
    
    def __init__(self, docs_file: str = "../docs/docs-wip.md"):
        self.docs_file = docs_file
    
    def append_to_docs_file(self, log_entry: str) -> bool:
        """Append log entry to docs-wip.md file."""
        try:
            # Get the absolute path to the docs file
            script_dir = Path(__file__).parent
            docs_path = script_dir / self.docs_file
            
            # Create the file if it doesn't exist
            docs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append the log entry
            with open(docs_path, 'a', encoding='utf-8') as file:
                file.write(log_entry)
            
            print(f"Log entry added to {docs_path}")
            return True
        except Exception as e:
            print(f"Error writing to docs file: {e}")
            return False


class DailyLogScheduler:
    """Main scheduler class that orchestrates the daily log task."""
    
    def __init__(self):
        self.config = Config()
        self.git_manager = GitManager(self.config)
        self.file_manager = FileManager()
        self._validate_ssh_key()
    
    def _validate_ssh_key(self) -> None:
        """Validate that the SSH key file exists."""
        script_dir = Path(__file__).parent
        ssh_key_path = script_dir / self.config.get("ssh_key_file")
        if not ssh_key_path.exists():
            print(f"Warning: SSH key file '{self.config.get('ssh_key_file')}' not found in {script_dir}")
            print("Please ensure the SSH key file is present for Git authentication")
    
    def daily_log_task(self) -> None:
        """Main task to run daily at midnight."""
        print(f"Running daily log task at {LogEntryGenerator.get_stockholm_time()}")
        
        # Generate and append log entry
        log_entry = LogEntryGenerator.create_log_entry()
        print(f"Generated log entry: {log_entry.strip()}")
        
        if self.file_manager.append_to_docs_file(log_entry):
            # Commit and push to Git
            if self.git_manager.commit_and_push():
                print("Daily log task completed successfully")
            else:
                print("Daily log task completed but Git operations failed")
        else:
            print("Daily log task failed - could not write to file")
    
    def run_scheduler(self) -> None:
        """Run the scheduler continuously."""
        print("Starting daily log scheduler...")
        print("Scheduled to run at midnight Stockholm time")
        
        # Schedule the task for midnight Stockholm time
        schedule.every().day.at("00:00").do(self.daily_log_task)
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_once(self) -> None:
        """Run the task once for testing."""
        print("Running task once for testing...")
        if self.git_manager.setup_credentials():
            self.daily_log_task()
        else:
            print("Failed to setup Git credentials")



def main() -> None:
    """Main entry point for the daily log script."""
    scheduler = DailyLogScheduler()
    
    # Setup Git credentials
    if not scheduler.git_manager.setup_credentials():
        print("Failed to setup Git credentials. Please check configuration.")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        scheduler.run_once()
    else:
        try:
            scheduler.run_scheduler()
        except KeyboardInterrupt:
            print("\nScheduler stopped by user")
        except Exception as e:
            print(f"Scheduler error: {e}")


if __name__ == "__main__":
    main()