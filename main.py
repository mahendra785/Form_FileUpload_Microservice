from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import uuid
from google.cloud import storage
import uvicorn  # <-- for running via main()

# Load env vars
load_dotenv()

app = FastAPI()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000",],
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Cloud setup
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
bucket_name = os.getenv("BUCKET_NAME")

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client["uploads"]
collection = db["files"]

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), filetype: str = Form(...)):
    try:
        contents = await file.read()
        print("File received:", file.filename)

        filename = f"{uuid.uuid4()}_{file.filename}"

        # Upload to GCS
        print("Uploading to GCS...")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(contents, content_type=file.content_type)

        file_url = blob.public_url

        print("File uploaded to:", file_url)

        # Store metadata in DB
        doc = {
            "filename": file.filename,
            "stored_as": filename,
            "filetype": filetype,
            "url": file_url,
            "content_type": file.content_type,
        }
        collection.insert_one(doc)
        print("Metadata saved to MongoDB")

        return JSONResponse({"url": file_url, "message": "File uploaded successfully."})

    except Exception as e:
        print("❌ Upload failed:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})




# Main function to run the app
def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()