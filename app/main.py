# app/main.py

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.tasks import update_labels_and_image_address  # import from tasks

app = FastAPI()

allow_origins = ["https://doorfront.org/"]

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageRequest(BaseModel):
    image_id: str

    class Config:
        allow_population_by_field_name = True

@app.get("/")
def root():
    return {"message": "FastAPI server is running"}

@app.post("/add-exactCoordinates-and-address")
async def add_coordinates_and_address(request: ImageRequest, background_tasks: BackgroundTasks):
    image_id = request.image_id
    
    # No ObjectId validation; accept any string
    if not image_id:
        raise HTTPException(status_code=400, detail="image_id cannot be empty")

    background_tasks.add_task(update_labels_and_image_address, image_id)

    return {
        "image_id": image_id,
        "message": "Label coordinate and address update started in background"
    }

print("✅ app/main.py is running!")
