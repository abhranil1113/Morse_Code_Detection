import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.calibrations.schemas import CalibrationSave, CalibrationResponse
from app.modules.calibrations.repository import CalibrationRepository


class CalibrationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CalibrationRepository(db)

    async def save_calibration(
        self,
        calib_in: CalibrationSave,
        user_id: uuid.UUID
    ) -> CalibrationResponse:
        calib = await self.repo.upsert_calibration(
            user_id=user_id,
            device_key=calib_in.device_key,
            calibration_data=calib_in.calibration_data,
            model_version=calib_in.model_version or "1.0.0"
        )
        return CalibrationResponse(
            id=str(calib.id),
            user_id=str(calib.user_id),
            device_key=calib.device_key,
            calibration_data=calib.calibration_data,
            model_version=calib.model_version,
            calibrated_at=calib.calibrated_at
        )

    async def get_calibration(
        self,
        user_id: uuid.UUID,
        device_key: str
    ) -> CalibrationResponse:
        calib = await self.repo.get_by_user_and_device(user_id=user_id, device_key=device_key)
        if not calib:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calibration not found for this user and device"
            )
        return CalibrationResponse(
            id=str(calib.id),
            user_id=str(calib.user_id),
            device_key=calib.device_key,
            calibration_data=calib.calibration_data,
            model_version=calib.model_version,
            calibrated_at=calib.calibrated_at
        )
