from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session as DBSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, File as FileModel
from app.schemas import FilesListResponse, FileDetailResponse, FileItem

router = APIRouter()


def _to_file_item(f: FileModel) -> FileItem:
    return FileItem(
        id=str(f.id),
        ownerId=str(f.owner_id),
        fileName=f.file_name,
        mimeType=f.mime_type,
        sizeBytes=f.size_bytes,
        uploadedAt=f.uploaded_at.isoformat() + "Z",
    )


@router.get("/files", response_model=FilesListResponse)
def list_files(current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    files = db.query(FileModel).filter(FileModel.owner_id == current_user.id).all()
    return FilesListResponse(files=[_to_file_item(f) for f in files])


@router.get("/files/{file_id}", response_model=FileDetailResponse)
def get_file(file_id: str, current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    f = db.query(FileModel).filter(FileModel.id == file_id).first()

    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if f.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this file")

    return FileDetailResponse(file=_to_file_item(f))


@router.get("/files/{file_id}/download")
def download_file(file_id: str, current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    f = db.query(FileModel).filter(FileModel.id == file_id).first()

    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if f.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this file")

    return PlainTextResponse(f.content or f"(mock content for {f.file_name})")