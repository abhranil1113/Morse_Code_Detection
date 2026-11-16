from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_connection import get_db
from app.modules.calibrations.schemas import CalibrationSave, CalibrationResponse
from app.modules.calibrations.service import CalibrationService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/calibrations", tags=["Vision Calibrations"])


@router.post(
    "",
    response_model=CalibrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Save user webcam calibration profile",
    description="Saves or updates personalized Eye Aspect Ratio (EAR) thresholds, blink duration limits, and model version for a specific camera device."
)
async def save_calibration(
    payload: CalibrationSave,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CalibrationService(db)
    return await service.save_calibration(payload, user_id=current_user.id)


@router.get(
    "",
    response_model=CalibrationResponse,
    summary="Get user webcam calibration profile",
    description="Fetches the personalized calibration parameters for the authenticated user and given device key."
)
async def get_calibration(
    device_key: str = Query(..., description="Unique webcam or camera identifier string"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CalibrationService(db)
    return await service.get_calibration(user_id=current_user.id, device_key=device_key)
