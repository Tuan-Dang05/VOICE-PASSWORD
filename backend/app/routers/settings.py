from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_algorithm_config, require_admin
from ..models import User
from ..schemas import AlgorithmConfigOut, AlgorithmConfigUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AlgorithmConfigOut)
def read_settings(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return get_algorithm_config(db)


@router.put("", response_model=AlgorithmConfigOut)
def update_settings(payload: AlgorithmConfigUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    config = get_algorithm_config(db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return config

