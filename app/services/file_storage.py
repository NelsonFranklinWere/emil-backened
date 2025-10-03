import os
import uuid
from fastapi import UploadFile
from app.config import settings

class FileStorageService:
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.max_file_size = settings.max_file_size
        
        # Create upload directories if they don't exist
        os.makedirs(os.path.join(self.upload_dir, "resumes"), exist_ok=True)
        os.makedirs(os.path.join(self.upload_dir, "reports"), exist_ok=True)
    
    def save_uploaded_file(self, file: UploadFile, file_type: str = "resumes") -> str:
        """Save uploaded file and return file path"""
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".bin"
        filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(self.upload_dir, file_type, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            if len(content) > self.max_file_size:
                raise ValueError(f"File size exceeds maximum allowed size of {self.max_file_size} bytes")
            buffer.write(content)
        
        return file_path
    
    def get_file_url(self, file_path: str) -> str:
        """Generate URL for accessing the file"""
        if not file_path or not os.path.exists(file_path):
            return ""
        
        relative_path = os.path.relpath(file_path, self.upload_dir)
        return f"{settings.app_url}/uploads/{relative_path}"
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False