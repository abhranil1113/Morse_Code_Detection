import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.vision_calibration import VisionCalibration


class CalibrationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_and_device(
        self,
        user_id: uuid.UUID,
        device_key: str
    ) -> Optional[VisionCalibration]:
        result = await self.db.execute(
            select(VisionCalibration).where(
                VisionCalibration.user_id == user_id,
                VisionCalibration.device_key == device_key
            )
        )
        return result.scalar_one_or_none()

    async def upsert_calibration(
        self,
        user_id: uuid.UUID,
        device_key: str,
        calibration_data: dict,
        model_version: str
    ) -> VisionCalibration:
        existing = await self.get_by_user_and_device(user_id, device_key)
        now = datetime.now(timezone.utc)
        if existing:
            existing.calibration_data = calibration_data
            existing.model_version = model_version
            existing.calibrated_at = now
            existing.updated_at = now
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            new_calib = VisionCalibration(
                id=uuid.uuid4(),
                user_id=user_id,
                device_key=device_key,
                calibration_data=calibration_data,
                model_version=model_version,
                calibrated_at=now
            )
            self.db.add(new_calib)
            await self.db.flush()
            await self.db.refresh(new_calib)
            return new_calib
