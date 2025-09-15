"""
Audit logging for upload operations and data changes.
Tracks all import activities with detailed metrics and error logging.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class AuditLogger:
    """Audit logger for tracking upload operations and data changes."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        
        # Setup audit directory
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
        self.audit_dir = self.data_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Audit files
        self.uploads_log = self.audit_dir / f"{tenant_id}_uploads.jsonl"
        self.changes_log = self.audit_dir / f"{tenant_id}_changes.jsonl"
        self.hashes_file = self.audit_dir / f"{tenant_id}_file_hashes.json"
    
    def log_upload(
        self,
        entity_type: str,
        batch_id: str,
        file_hash: str,
        mode: str,
        total_rows: int,
        processed_rows: int,
        error_rows: int,
        success: bool,
        user_id: Optional[str] = None,
        filename: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log upload operation with detailed metrics."""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'tenant_id': self.tenant_id,
            'entity_type': entity_type,
            'batch_id': batch_id,
            'file_hash': file_hash,
            'mode': mode,
            'total_rows': total_rows,
            'processed_rows': processed_rows,
            'error_rows': error_rows,
            'success': success,
            'user_id': user_id,
            'filename': filename,
            'error_message': error_message
        }
        
        # Append to uploads log
        with open(self.uploads_log, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')
        
        # Update file hashes registry
        self._update_file_hash(file_hash, batch_id, entity_type)
    
    def log_data_change(
        self,
        entity_type: str,
        operation: str,  # 'create', 'update', 'delete'
        entity_id: str,
        changes: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Log individual data changes for audit trail."""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'tenant_id': self.tenant_id,
            'entity_type': entity_type,
            'operation': operation,
            'entity_id': entity_id,
            'changes': changes,
            'user_id': user_id
        }
        
        # Append to changes log
        with open(self.changes_log, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')
    
    def is_duplicate_upload(self, file_hash: str) -> bool:
        """Check if file has already been uploaded."""
        if not self.hashes_file.exists():
            return False
        
        try:
            with open(self.hashes_file, 'r') as f:
                hashes = json.load(f)
                return file_hash in hashes
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def _update_file_hash(self, file_hash: str, batch_id: str, entity_type: str):
        """Update file hashes registry."""
        hashes = {}
        
        if self.hashes_file.exists():
            try:
                with open(self.hashes_file, 'r') as f:
                    hashes = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                hashes = {}
        
        hashes[file_hash] = {
            'batch_id': batch_id,
            'entity_type': entity_type,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.hashes_file, 'w') as f:
            json.dump(hashes, f, indent=2, default=str)
    
    def get_upload_history(self, days: int = 30, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get upload history for the last N days."""
        if not self.uploads_log.exists():
            return []
        
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        history = []
        
        try:
            with open(self.uploads_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            if entity_type is None or entry.get('entity_type') == entity_type:
                                history.append(entry)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except FileNotFoundError:
            return []
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        return history
    
    def get_upload_stats(self, entity_type: Optional[str] = None) -> Dict[str, Any]:
        """Get upload statistics summary."""
        history = self.get_upload_history(days=90, entity_type=entity_type)
        
        if not history:
            return {
                'total_uploads': 0,
                'successful_uploads': 0,
                'failed_uploads': 0,
                'total_rows_processed': 0,
                'total_error_rows': 0,
                'last_upload': None
            }
        
        successful = [h for h in history if h.get('success')]
        failed = [h for h in history if not h.get('success')]
        
        return {
            'total_uploads': len(history),
            'successful_uploads': len(successful),
            'failed_uploads': len(failed),
            'total_rows_processed': sum(h.get('processed_rows', 0) for h in history),
            'total_error_rows': sum(h.get('error_rows', 0) for h in history),
            'last_upload': history[0]['timestamp'] if history else None,
            'entity_breakdown': self._get_entity_breakdown(history)
        }
    
    def _get_entity_breakdown(self, history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of uploads by entity type."""
        breakdown = {}
        for entry in history:
            entity_type = entry.get('entity_type', 'unknown')
            breakdown[entity_type] = breakdown.get(entity_type, 0) + 1
        return breakdown
    
    def get_change_history(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Get change history for specific entity."""
        if not self.changes_log.exists():
            return []
        
        changes = []
        
        try:
            with open(self.changes_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if (entry.get('entity_type') == entity_type and 
                            entry.get('entity_id') == entity_id):
                            changes.append(entry)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            return []
        
        # Sort by timestamp (newest first)
        changes.sort(key=lambda x: x['timestamp'], reverse=True)
        return changes