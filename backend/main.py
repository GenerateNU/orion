from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.race_controller import router as race_router


app = FastAPI(title="orion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tell FastAPI to use the router we created in the race_controller.py file.
app.include_router(race_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
