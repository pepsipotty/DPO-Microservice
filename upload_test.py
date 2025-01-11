import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceKey.json")
firebase_admin.initialize_app(cred, {
    "storageBucket": "dpo-frontend.firebasestorage.app"
})

# Upload a file to the storage bucket
def upload_to_bucket(local_file_path, remote_file_name):
    try:
        bucket = storage.bucket()
        blob = bucket.blob(remote_file_name)
        blob.upload_from_filename(local_file_path)
        print(f"File {local_file_path} uploaded to {remote_file_name}")
    except Exception as e:
        print(f"Error uploading file: {e}")

# Test the function
if __name__ == "__main__":
    # Replace with the local file path you want to upload
    local_file_path = "test.txt"
    # Replace with the name you want the file to have in the bucket
    remote_file_name = "test.txt"

    # Create a test file to upload
    with open(local_file_path, "w") as f:
        f.write("This is a test upload!")

    # Upload the file
    upload_to_bucket(local_file_path, remote_file_name)