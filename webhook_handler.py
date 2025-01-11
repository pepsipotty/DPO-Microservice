from fastapi import FastAPI, HTTPException
import os
import subprocess
import json
import firebase_admin
from firebase_admin import credentials

app = FastAPI()
cred = credentials.Certificate("serviceKey.json")
firebase_admin.initialize_app(cred, {
    "storageBucket": "dpo-frontend.firebasestorage.app"
})


@app.post("/trigger-finetune")
async def trigger_finetune(data: dict):
    try:
        # Step 1: Save the dataset from the POST body
        dataset_path = "/app/data/dataset.json"
        os.makedirs("/app/data", exist_ok=True)  # Ensure the directory exists

        with open(dataset_path, "w") as f:
            json.dump(data["dataset"], f)

        # Step 2: Run the fine-tuning command
        command = [
            "python", 
            "train.py",
            "model=pythia28",
            "datasets=[novalto]",  # Hardcoded to use the `novalto` dataset handler
            "loss=dpo",
            "loss.beta=0.1",
            f"exp_name={data['communityId']}"
        ]
        subprocess.run(command, check=True)

        # Step 3: Verify that fine-tuning completed and `policy.pt` was generated
        policy_path = f".cache/root/{data['communityId']}/LATEST/policy.pt"
        if not os.path.exists(policy_path):
            raise HTTPException(status_code=500, detail="Fine-tuning failed: policy.pt not found")

        # Step 4: Delete the dataset file after successful training
        os.remove(dataset_path)

        return {"status": "success", "policy_path": policy_path}

    except Exception as e:
        # Ensure dataset file is cleaned up even in case of failure
        if os.path.exists(dataset_path):
            os.remove(dataset_path)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")