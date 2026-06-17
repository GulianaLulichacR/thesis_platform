from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Enum
from sqlalchemy.sql import func
import enum
from typing import Any, Optional
from app.database import Base

class ThesisStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Thesis(Base):
    __tablename__ = "thesis"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    ai_analysis_status = Column(Enum(ThesisStatus), default=ThesisStatus.PENDING)
    citation_check_status = Column(Enum(ThesisStatus), default=ThesisStatus.PENDING)
    
    raw_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    ai_analysis_result = Column(JSON, nullable=True)
    citation_check_result = Column(JSON, nullable=True)
    
    def to_dict(self) -> dict[str, Any]:
        # FIX: Extraer valores antes de usarlos en condicionales
        uploaded_at_value = self.uploaded_at
        ai_status_value = self.ai_analysis_status
        cit_status_value = self.citation_check_status
        
        return {
            "id": self.id,
            "title": self.title,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "uploaded_at": uploaded_at_value.isoformat() if uploaded_at_value is not None else None,
            "ai_analysis_status": ai_status_value.value if ai_status_value is not None else "pending",
            "citation_check_status": cit_status_value.value if cit_status_value is not None else "pending",
            "metadata_json": self.metadata_json,
        }