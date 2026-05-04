"""
Period Management Models
Handles financial period creation, management, and workflow state tracking
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from supabase import create_client, Client
from models.supabase_auth_models import supabase_auth


class PeriodStatus(Enum):
    """Period status enumeration"""
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class PeriodUrgency(Enum):
    """Period urgency enumeration"""
    NORMAL = "normal"
    URGENT = "urgent"
    OVERDUE = "overdue"


@dataclass
class FinancialPeriod:
    """Financial period data model"""
    id: str
    name: str
    description: str
    start_date: str
    end_date: str
    due_date: str
    status: str
    urgency: str
    required_uploads: int
    uploaded_count: int
    created_by: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

    def __post_init__(self):
        """Post-initialization processing"""
        if isinstance(self.start_date, datetime):
            self.start_date = self.start_date.isoformat()
        if isinstance(self.end_date, datetime):
            self.end_date = self.end_date.isoformat()
        if isinstance(self.due_date, datetime):
            self.due_date = self.due_date.isoformat()
        if isinstance(self.created_at, datetime):
            self.created_at = self.created_at.isoformat()
        if isinstance(self.updated_at, datetime):
            self.updated_at = self.updated_at.isoformat()

    @property
    def is_urgent(self) -> bool:
        """Check if period is urgent"""
        if self.urgency == PeriodUrgency.URGENT.value:
            return True
        
        # Auto-calculate urgency based on due date
        try:
            from datetime import timezone
            due_date = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_until_due = (due_date - now).days
            return days_until_due <= 7  # Urgent if due within 7 days
        except:
            return False

    @property
    def is_overdue(self) -> bool:
        """Check if period is overdue"""
        try:
            from datetime import timezone
            due_date = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return now > due_date
        except:
            return False

    @property
    def days_remaining(self) -> int:
        """Calculate days remaining until due date"""
        try:
            from datetime import timezone
            due_date = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_remaining = (due_date - now).days
            return max(0, days_remaining)
        except:
            return 0

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.required_uploads == 0:
            return 0.0
        return min(100.0, (self.uploaded_count / self.required_uploads) * 100)

    @property
    def last_upload(self) -> Optional[str]:
        """Get last upload date from metadata"""
        return self.metadata.get('last_upload')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Add computed properties
        data['is_urgent'] = self.is_urgent
        data['is_overdue'] = self.is_overdue
        data['days_remaining'] = self.days_remaining
        data['completion_percentage'] = self.completion_percentage
        data['last_upload'] = self.last_upload
        return data


class PeriodModel:
    """Period management model with database operations"""
    
    def __init__(self):
        self.client = supabase_auth.client
        self.table_name = "financial_periods"

    def create_period(self, period_data: Dict[str, Any]) -> FinancialPeriod:
        """Create a new financial period"""
        try:
            # Generate ID if not provided
            if 'id' not in period_data:
                period_data['id'] = str(uuid.uuid4())
            
            # Set timestamps
            now = datetime.now().isoformat()
            period_data['created_at'] = now
            period_data['updated_at'] = now
            
            # Set default values
            period_data.setdefault('status', PeriodStatus.DRAFT.value)
            period_data.setdefault('urgency', PeriodUrgency.NORMAL.value)
            period_data.setdefault('uploaded_count', 0)
            period_data.setdefault('metadata', {})
            
            # Insert into database
            result = self.client.table(self.table_name).insert(period_data).execute()
            
            if result.data:
                return FinancialPeriod(**result.data[0])
            else:
                raise Exception("Failed to create period")
                
        except Exception as e:
            raise Exception(f"Error creating period: {str(e)}")

    def get_period(self, period_id: str) -> Optional[FinancialPeriod]:
        """Get a specific period by ID"""
        try:
            result = self.client.table(self.table_name).select('*').eq('id', period_id).execute()
            
            if result.data:
                return FinancialPeriod(**result.data[0])
            return None
            
        except Exception as e:
            raise Exception(f"Error getting period: {str(e)}")

    def get_all_periods(self) -> List[FinancialPeriod]:
        """Get all periods"""
        try:
            result = self.client.table(self.table_name).select('*').order('created_at', desc=True).execute()
            
            periods = []
            for period_data in result.data:
                periods.append(FinancialPeriod(**period_data))
            
            return periods
            
        except Exception as e:
            raise Exception(f"Error getting all periods: {str(e)}")

    def get_open_periods(self) -> List[FinancialPeriod]:
        """Get all open periods"""
        try:
            result = self.client.table(self.table_name).select('*').eq('status', PeriodStatus.OPEN.value).order('due_date').execute()
            
            periods = []
            for period_data in result.data:
                periods.append(FinancialPeriod(**period_data))
            
            return periods
            
        except Exception as e:
            raise Exception(f"Error getting open periods: {str(e)}")

    def get_periods_by_status(self, status: PeriodStatus) -> List[FinancialPeriod]:
        """Get periods by status"""
        try:
            result = self.client.table(self.table_name).select('*').eq('status', status.value).order('created_at', desc=True).execute()
            
            periods = []
            for period_data in result.data:
                periods.append(FinancialPeriod(**period_data))
            
            return periods
            
        except Exception as e:
            raise Exception(f"Error getting periods by status: {str(e)}")

    def update_period(self, period_id: str, update_data: Dict[str, Any]) -> FinancialPeriod:
        """Update a period"""
        try:
            # Set updated timestamp
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Update in database
            result = self.client.table(self.table_name).update(update_data).eq('id', period_id).execute()
            
            if result.data:
                return FinancialPeriod(**result.data[0])
            else:
                raise Exception("Period not found or update failed")
                
        except Exception as e:
            raise Exception(f"Error updating period: {str(e)}")

    def open_period(self, period_id: str) -> FinancialPeriod:
        """Open a period for uploads"""
        return self.update_period(period_id, {
            'status': PeriodStatus.OPEN.value,
            'urgency': PeriodUrgency.NORMAL.value
        })

    def close_period(self, period_id: str) -> FinancialPeriod:
        """Close a period"""
        return self.update_period(period_id, {
            'status': PeriodStatus.CLOSED.value
        })

    def archive_period(self, period_id: str) -> FinancialPeriod:
        """Archive a period"""
        return self.update_period(period_id, {
            'status': PeriodStatus.ARCHIVED.value
        })

    def increment_upload_count(self, period_id: str, upload_date: Optional[str] = None) -> FinancialPeriod:
        """Increment upload count for a period"""
        try:
            # Get current period
            period = self.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            # Update upload count and last upload
            update_data = {
                'uploaded_count': period.uploaded_count + 1,
                'metadata': {
                    **period.metadata,
                    'last_upload': upload_date or datetime.now().isoformat()
                }
            }
            
            return self.update_period(period_id, update_data)
            
        except Exception as e:
            raise Exception(f"Error incrementing upload count: {str(e)}")

    def decrement_upload_count(self, period_id: str) -> FinancialPeriod:
        """Decrement upload count for a period"""
        try:
            # Get current period
            period = self.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            # Update upload count (don't go below 0)
            new_count = max(0, period.uploaded_count - 1)
            update_data = {
                'uploaded_count': new_count
            }
            
            return self.update_period(period_id, update_data)
            
        except Exception as e:
            raise Exception(f"Error decrementing upload count: {str(e)}")

    def delete_period(self, period_id: str) -> bool:
        """Delete a period"""
        try:
            result = self.client.table(self.table_name).delete().eq('id', period_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            raise Exception(f"Error deleting period: {str(e)}")

    def get_period_stats(self) -> Dict[str, int]:
        """Get period statistics"""
        try:
            # Get all periods
            all_periods = self.get_all_periods()
            
            # Calculate stats
            stats = {
                'total_periods': len(all_periods),
                'open_periods': len([p for p in all_periods if p.status == PeriodStatus.OPEN.value]),
                'closed_periods': len([p for p in all_periods if p.status == PeriodStatus.CLOSED.value]),
                'draft_periods': len([p for p in all_periods if p.status == PeriodStatus.DRAFT.value]),
                'urgent_periods': len([p for p in all_periods if p.is_urgent]),
                'overdue_periods': len([p for p in all_periods if p.is_overdue])
            }
            
            return stats
            
        except Exception as e:
            raise Exception(f"Error getting period stats: {str(e)}")

    def update_urgency_flags(self) -> int:
        """Update urgency flags for all periods based on due dates"""
        try:
            updated_count = 0
            all_periods = self.get_all_periods()
            
            for period in all_periods:
                if period.status == PeriodStatus.OPEN.value:
                    # Determine new urgency
                    if period.is_overdue:
                        new_urgency = PeriodUrgency.OVERDUE.value
                    elif period.is_urgent:
                        new_urgency = PeriodUrgency.URGENT.value
                    else:
                        new_urgency = PeriodUrgency.NORMAL.value
                    
                    # Update if urgency changed
                    if period.urgency != new_urgency:
                        self.update_period(period.id, {'urgency': new_urgency})
                        updated_count += 1
            
            return updated_count
            
        except Exception as e:
            raise Exception(f"Error updating urgency flags: {str(e)}")


# Create global period model instance
period_model = PeriodModel()
