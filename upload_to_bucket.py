import firebase_admin
from firebase_admin import credentials, storage
import os
import shutil
from pathlib import Path

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceKey.json")
firebase_admin.initialize_app(cred, {
    "storageBucket": "dpo-frontend.firebasestorage.app"
})

def trigger_policy_upload(policy_path: str, file_name: str, cleanup_after_upload: bool = True):
    """
    Upload policy file to Firebase Storage and optionally clean up training artifacts.
    
    Args:
        policy_path: Path to the policy.pt file to upload
        file_name: Name to use in Firebase Storage
        cleanup_after_upload: Whether to clean up training artifacts after successful upload
        
    Returns:
        tuple: (success: bool, firebase_url: str) - success status and Firebase download URL
    """
    try:
        # Get the Firebase Storage bucket
        bucket = storage.bucket()

        # Define the full path in the bucket using the custom file name
        blob = bucket.blob(f"policies/{file_name}")

        # Upload the file from the local file system
        blob.upload_from_filename(policy_path)

        # Get the Firebase download URL
        firebase_url = f"https://firebasestorage.googleapis.com/v0/b/dpo-frontend.firebasestorage.app/o/policies%2F{file_name}?alt=media"
        
        print(f"Successfully uploaded {policy_path} to Firebase Storage as {file_name}.")
        
        # Create success marker file with Firebase URL
        policy_file = Path(policy_path)
        success_marker = policy_file.parent / ".upload_success"
        success_marker.write_text(firebase_url)
        print(f"Created upload success marker: {success_marker}")
        
        # Perform cleanup after successful upload
        if cleanup_after_upload:
            cleanup_training_artifacts(policy_path)
            
        return True, firebase_url
        
    except Exception as e:
        print(f"Error uploading {policy_path}: {e}")
        return False, ""


def cleanup_training_artifacts(policy_path: str):
    """
    Clean up training artifacts after successful upload to save disk space.
    
    Removes:
    - optimizer.pt (large, only needed for resuming training)
    - scheduler.pt (small, only needed for resuming training)
    - Optionally the entire LATEST directory
    
    Preserves:
    - Model cache files (reusable across training runs)
    - Failed upload directories (for debugging)
    
    Args:
        policy_path: Path to the uploaded policy.pt file
    """
    try:
        policy_file = Path(policy_path)
        latest_dir = policy_file.parent
        
        # Only clean up if this is a LATEST directory (safety check)
        if latest_dir.name != "LATEST":
            print(f"Skipping cleanup: {latest_dir} is not a LATEST directory")
            return
            
        print(f"Starting cleanup of training artifacts in {latest_dir}")
        
        # Remove optimizer.pt (usually largest file, 3-11GB)
        optimizer_file = latest_dir / "optimizer.pt"
        if optimizer_file.exists():
            os.remove(optimizer_file)
            print(f"Deleted optimizer.pt ({optimizer_file})")
            
        # Remove scheduler.pt (small but not needed)
        scheduler_file = latest_dir / "scheduler.pt"
        if scheduler_file.exists():
            os.remove(scheduler_file)
            print(f"Deleted scheduler.pt ({scheduler_file})")
            
        # Optionally remove the policy.pt as well since it's uploaded
        if policy_file.exists():
            os.remove(policy_file)
            print(f"Deleted local policy.pt ({policy_file})")
            
        # Check if LATEST directory is now empty (except for .upload_success marker)
        remaining_files = [f for f in latest_dir.glob("*") if f.name != ".upload_success"]
        if not remaining_files:
            # Only remove directory if no success marker exists
            success_marker = latest_dir / ".upload_success"
            if not success_marker.exists():
                latest_dir.rmdir()
                print(f"Removed empty LATEST directory ({latest_dir})")
                
                # Check if parent experiment directory is empty and remove it
                experiment_dir = latest_dir.parent
                remaining_items = list(experiment_dir.glob("*"))
                if not remaining_items:
                    experiment_dir.rmdir()
                    print(f"Removed empty experiment directory ({experiment_dir})")
            else:
                print(f"Keeping LATEST directory with upload success marker")
        else:
            print(f"LATEST directory contains {len(remaining_files)} remaining files, keeping directory")
            
        print("✅ Cleanup completed successfully")
        
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}")
        print("Upload was successful, but cleanup failed. Manual cleanup may be needed.")