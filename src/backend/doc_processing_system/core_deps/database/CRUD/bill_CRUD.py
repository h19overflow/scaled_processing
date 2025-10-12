from .base_repository import BaseRepository
from ..models import BillModel
from ..connection_manager import ConnectionManager
from datetime import datetime
from ..models import BillStatus
class BillCRUD(BaseRepository):
    """CRUD operations for bill entities."""
    
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__(connection_manager)
        self.model = BillModel
    def create(self, document_name: str,
               issue_date: datetime,
               due_date: datetime, amount_due:
                   float, status: BillStatus,
                   extracted_jsonb: dict, version: int) -> str:
        """Create a new bill."""
        with self.connection_manager.get_session() as session:
            bill = BillModel(document_name=document_name,
                           issue_date=issue_date,
                           due_date=due_date,
                           amount_due=amount_due,
                           status=status,
                           extracted_jsonb=extracted_jsonb,
                           version=version)
            session.add(bill)
            session.flush()  # Flush to get the ID without committing
            bill_id = str(bill.id)  # Get ID while session is still active
            return bill_id
            # Context manager will commit on exit
    def get_bill_by_id(self, bill_id: str) -> BillModel:
        """Get a bill by ID."""
        with self.connection_manager.get_session() as session:
            return session.query(BillModel).filter(BillModel.id == bill_id).first()
    
    def get_bill_by_document_name(self, document_name: str) -> str | None:
        """Get a bill ID by document name. Returns bill_id or None if not found."""
        with self.connection_manager.get_session() as session:
            bill = session.query(BillModel).filter(BillModel.document_name == document_name).first()
            if bill:
                return str(bill.id)  # Access ID while session is active
            return None