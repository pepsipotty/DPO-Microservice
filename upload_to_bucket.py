import firebase_admin
from firebase_admin import credentials, storage
import os

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceKey.json")
firebase_admin.initialize_app(cred, {
    "storageBucket": "dpo-frontend.firebasestorage.app"
})

def trigger_policy_upload(policy_path: str, file_name: str):

    try:
        # Get the Firebase Storage bucket
        bucket = storage.bucket()

        # Define the full path in the bucket using the custom file name
        blob = bucket.blob(f"policies/{file_name}")

        # Upload the file from the local file system
        blob.upload_from_filename(policy_path)

        print(f"Successfully uploaded {policy_path} to Firebase Storage as {file_name}.")
    except Exception as e:
        print(f"Error uploading {policy_path}: {e}")