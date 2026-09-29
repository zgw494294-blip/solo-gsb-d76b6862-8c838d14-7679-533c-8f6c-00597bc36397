from fastapi import FastAPI

from app.models import AssignmentRequest, AssignmentResponse
from app.solver import solve_tracks

app = FastAPI(
    title="Offline Dialogue Subtitle Track Allocation API",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/assign", response_model=AssignmentResponse)
def assign_tracks(request: AssignmentRequest) -> AssignmentResponse:
    return solve_tracks(request)
