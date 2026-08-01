from fastapi import APIRouter
router=APIRouter(prefix="/knowledge",tags=["Knowledge"])
@router.get("/health")
async def health():
    return {"module":"knowledge","status":"UP"}
