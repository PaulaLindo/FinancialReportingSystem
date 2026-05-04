"""
Period Management Service
Business logic for financial period management and workflow operations
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import asdict

from models.period_models import (
    period_model, FinancialPeriod, PeriodStatus, PeriodUrgency
)
from models.supabase_auth_models import supabase_auth

# Set up logging
logger = logging.getLogger(__name__)


class PeriodManagementService:
    """Service for managing financial periods and workflow operations"""
    
    def __init__(self):
        self.model = period_model

    def create_financial_period(self, period_data: Dict[str, Any], created_by: str) -> FinancialPeriod:
        """Create a new financial period with validation"""
        try:
            # Validate required fields
            required_fields = ['name', 'start_date', 'end_date', 'due_date', 'required_uploads']
            for field in required_fields:
                if field not in period_data or not period_data[field]:
                    raise ValueError(f"Required field '{field}' is missing or empty")
            
            # Validate dates
            start_date = self._parse_date(period_data['start_date'])
            end_date = self._parse_date(period_data['end_date'])
            due_date = self._parse_date(period_data['due_date'])
            
            if start_date >= end_date:
                raise ValueError("Start date must be before end date")
            
            if due_date < end_date:
                raise ValueError("Due date must be on or after end date")
            
            # Validate required uploads
            if not isinstance(period_data['required_uploads'], int) or period_data['required_uploads'] < 1:
                raise ValueError("Required uploads must be a positive integer")
            
            # Prepare period data
            full_period_data = {
                **period_data,
                'created_by': created_by,
                'description': period_data.get('description', ''),
                'status': PeriodStatus.DRAFT.value,
                'urgency': PeriodUrgency.NORMAL.value,
                'uploaded_count': 0,
                'metadata': {}
            }
            
            # Create period
            period = self.model.create_period(full_period_data)
            logger.info(f"Created financial period: {period.name} ({period.id})")
            
            return period
            
        except Exception as e:
            logger.error(f"Error creating financial period: {str(e)}")
            raise Exception(f"Failed to create financial period: {str(e)}")

    def get_available_periods_for_upload(self) -> List[FinancialPeriod]:
        """Get periods that are open for uploads"""
        try:
            # Get open periods
            open_periods = self.model.get_open_periods()
            
            # Filter by current date (period should be active)
            from datetime import timezone
            now = datetime.now(timezone.utc)
            available_periods = []
            
            for period in open_periods:
                try:
                    start_date = self._parse_date(period.start_date)
                    end_date = self._parse_date(period.end_date)
                    
                    # Check if current date is within period range
                    if start_date <= now <= end_date:
                        available_periods.append(period)
                        
                except Exception as e:
                    logger.warning(f"Error parsing dates for period {period.id}: {str(e)}")
                    continue
            
            return available_periods
            
        except Exception as e:
            logger.error(f"Error getting available periods: {str(e)}")
            raise Exception(f"Failed to get available periods: {str(e)}")

    def validate_upload_for_period(self, period_id: str) -> Tuple[bool, str]:
        """Validate if upload is allowed for a period"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                return False, "Period not found"
            
            # Check if period is open
            if period.status != PeriodStatus.OPEN.value:
                return False, f"Period is {period.status}. Uploads not allowed."
            
            # Check if period is within date range
            now = datetime.now()
            try:
                start_date = self._parse_date(period.start_date)
                end_date = self._parse_date(period.end_date)
                
                if not (start_date <= now <= end_date):
                    return False, "Current date is outside the period date range"
                    
            except Exception:
                return False, "Invalid period dates"
            
            # Check if upload limit reached
            if period.uploaded_count >= period.required_uploads:
                return False, f"Upload limit reached ({period.required_uploads} uploads)"
            
            return True, "Upload allowed"
            
        except Exception as e:
            logger.error(f"Error validating upload for period: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def record_upload_for_period(self, period_id: str, upload_info: Dict[str, Any]) -> FinancialPeriod:
        """Record an upload for a period"""
        try:
            # Validate upload first
            can_upload, message = self.validate_upload_for_period(period_id)
            if not can_upload:
                raise Exception(message)
            
            # Record upload
            upload_date = upload_info.get('upload_date', datetime.now().isoformat())
            period = self.model.increment_upload_count(period_id, upload_date)
            
            # Check if period should be closed (reached upload limit)
            if period.uploaded_count >= period.required_uploads:
                logger.info(f"Period {period.name} reached upload limit, auto-closing")
                period = self.model.close_period(period_id)
            
            logger.info(f"Recorded upload for period {period.name}: {period.uploaded_count}/{period.required_uploads}")
            
            return period
            
        except Exception as e:
            logger.error(f"Error recording upload for period: {str(e)}")
            raise Exception(f"Failed to record upload: {str(e)}")

    def remove_upload_from_period(self, period_id: str) -> FinancialPeriod:
        """Remove an upload from a period (for deleted/cancelled uploads)"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            # Decrement upload count
            period = self.model.decrement_upload_count(period_id)
            
            # If period was closed and uploads were removed, reopen it
            if period.status == PeriodStatus.CLOSED.value and period.uploaded_count < period.required_uploads:
                logger.info(f"Period {period.name} has available slots, reopening")
                period = self.model.open_period(period_id)
            
            logger.info(f"Removed upload from period {period.name}: {period.uploaded_count}/{period.required_uploads}")
            
            return period
            
        except Exception as e:
            logger.error(f"Error removing upload from period: {str(e)}")
            raise Exception(f"Failed to remove upload: {str(e)}")

    def open_period_for_uploads(self, period_id: str) -> FinancialPeriod:
        """Open a period for uploads"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            if period.status == PeriodStatus.OPEN.value:
                logger.warning(f"Period {period.name} is already open")
                return period
            
            # Validate period dates
            now = datetime.now()
            try:
                start_date = self._parse_date(period.start_date)
                end_date = self._parse_date(period.end_date)
                
                if not (start_date <= now <= end_date):
                    raise Exception("Cannot open period: current date is outside period range")
                    
            except Exception as e:
                raise Exception(f"Invalid period dates: {str(e)}")
            
            period = self.model.open_period(period_id)
            logger.info(f"Opened period {period.name} for uploads")
            
            return period
            
        except Exception as e:
            logger.error(f"Error opening period: {str(e)}")
            raise Exception(f"Failed to open period: {str(e)}")

    def close_period(self, period_id: str) -> FinancialPeriod:
        """Close a period"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            if period.status == PeriodStatus.CLOSED.value:
                logger.warning(f"Period {period.name} is already closed")
                return period
            
            period = self.model.close_period(period_id)
            logger.info(f"Closed period {period.name}")
            
            return period
            
        except Exception as e:
            logger.error(f"Error closing period: {str(e)}")
            raise Exception(f"Failed to close period: {str(e)}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for finance clerks"""
        try:
            # Get open periods
            open_periods = self.model.get_open_periods()
            
            # Get available periods (within date range)
            available_periods = self.get_available_periods_for_upload()
            
            # Calculate stats
            stats = {
                'open_periods': len(open_periods),
                'available_periods': len(available_periods),
                'total_periods': len(self.model.get_all_periods()),
                'urgent_periods': len([p for p in open_periods if p.is_urgent]),
                'overdue_periods': len([p for p in open_periods if p.is_overdue])
            }
            
            # Format periods for dashboard
            formatted_periods = []
            for period in open_periods:
                period_data = period.to_dict()
                
                # Add upload availability info
                period_data['can_upload'] = period in available_periods
                period_data['upload_slots_remaining'] = max(0, period.required_uploads - period.uploaded_count)
                
                formatted_periods.append(period_data)
            
            return {
                'periods': formatted_periods,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            raise Exception(f"Failed to get dashboard data: {str(e)}")

    def update_period_urgency(self) -> Dict[str, int]:
        """Update urgency flags for all periods"""
        try:
            updated_count = self.model.update_urgency_flags()
            
            logger.info(f"Updated urgency flags for {updated_count} periods")
            
            return {
                'updated_periods': updated_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating period urgency: {str(e)}")
            raise Exception(f"Failed to update period urgency: {str(e)}")

    def get_period_summary(self, period_id: str) -> Dict[str, Any]:
        """Get detailed summary of a period"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            # Get upload validation
            can_upload, upload_message = self.validate_upload_for_period(period_id)
            
            # Build summary
            summary = {
                **period.to_dict(),
                'can_upload': can_upload,
                'upload_message': upload_message,
                'upload_slots_remaining': max(0, period.required_uploads - period.uploaded_count),
                'is_past_due': period.is_overdue,
                'days_overdue': max(0, -period.days_remaining) if period.is_overdue else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting period summary: {str(e)}")
            raise Exception(f"Failed to get period summary: {str(e)}")

    def create_sample_periods(self, created_by: str) -> List[FinancialPeriod]:
        """Create sample financial periods for testing/demo"""
        try:
            sample_periods = []
            now = datetime.now()
            
            # Create current month period (open)
            current_start = now.replace(day=1)
            current_end = (current_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            current_due = current_end + timedelta(days=7)
            
            current_period = self.create_financial_period({
                'name': f"{now.strftime('%B %Y')} Financial Period",
                'description': f"Monthly financial reporting for {now.strftime('%B %Y')}",
                'start_date': current_start.isoformat(),
                'end_date': current_end.isoformat(),
                'due_date': current_due.isoformat(),
                'required_uploads': 3
            }, created_by)
            
            # Open the current period
            current_period = self.open_period_for_uploads(current_period.id)
            sample_periods.append(current_period)
            
            # Create next month period (draft)
            next_start = current_end + timedelta(days=1)
            next_end = (next_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            next_due = next_end + timedelta(days=7)
            
            next_period = self.create_financial_period({
                'name': f"{(now + timedelta(days=32)).strftime('%B %Y')} Financial Period",
                'description': f"Monthly financial reporting for {(now + timedelta(days=32)).strftime('%B %Y')}",
                'start_date': next_start.isoformat(),
                'end_date': next_end.isoformat(),
                'due_date': next_due.isoformat(),
                'required_uploads': 3
            }, created_by)
            
            sample_periods.append(next_period)
            
            # Create previous month period (closed)
            prev_start = (current_start - timedelta(days=1)).replace(day=1)
            prev_end = current_start - timedelta(days=1)
            prev_due = prev_end + timedelta(days=7)
            
            prev_period = self.create_financial_period({
                'name': f"{(now - timedelta(days=32)).strftime('%B %Y')} Financial Period",
                'description': f"Monthly financial reporting for {(now - timedelta(days=32)).strftime('%B %Y')}",
                'start_date': prev_start.isoformat(),
                'end_date': prev_end.isoformat(),
                'due_date': prev_due.isoformat(),
                'required_uploads': 2
            }, created_by)
            
            # Close the previous period
            prev_period = self.close_period(prev_period.id)
            sample_periods.append(prev_period)
            
            logger.info(f"Created {len(sample_periods)} sample periods")
            
            return sample_periods
            
        except Exception as e:
            logger.error(f"Error creating sample periods: {str(e)}")
            raise Exception(f"Failed to create sample periods: {str(e)}")

    def _parse_date(self, date_string: str) -> datetime:
        """Parse date string to datetime object"""
        try:
            # Handle ISO format with timezone
            if 'T' in date_string:
                if 'Z' in date_string:
                    return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(date_string)
            else:
                # Handle simple date format
                return datetime.strptime(date_string, '%Y-%m-%d')
        except Exception as e:
            raise ValueError(f"Invalid date format: {date_string}")


# Create global period management service instance
period_management_service = PeriodManagementService()
