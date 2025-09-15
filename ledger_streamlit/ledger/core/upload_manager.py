"""
Unified Upload Manager for bulk data processing across all modules.
Provides consistent pipeline: load -> map -> validate -> transform -> upsert.
"""
import pandas as pd
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from .schemas import SchemaRegistry
from .audit import AuditLogger

@dataclass
class UploadResult:
    """Result of upload operation with detailed metrics and errors."""
    batch_id: str
    success: bool
    total_rows: int
    processed_rows: int
    error_rows: int
    warnings: List[str]
    errors: List[str]
    row_errors: List[Dict[str, Any]]
    file_hash: str
    timestamp: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class ColumnMapping:
    """Maps uploaded columns to schema fields."""
    source_column: str
    target_field: str
    transform: Optional[str] = None  # 'upper', 'lower', 'strip', 'date', 'number'

class UploadManager:
    """
    Unified upload manager handling CSV/Excel/JSON files with validation,
    transformation, and tenant-aware data persistence.
    """
    
    def __init__(self, tenant_id: str, entity_type: str):
        self.tenant_id = tenant_id
        self.entity_type = entity_type
        self.schema_registry = SchemaRegistry()
        self.audit_logger = AuditLogger(tenant_id)
        
        # Setup directories
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
        self.staging_dir = self.data_dir / "staging"
        self.entity_dir = self.data_dir / entity_type
        
        for dir_path in [self.staging_dir, self.entity_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for the entity type."""
        return self.schema_registry.get_schema(self.entity_type)
    
    def generate_template(self) -> pd.DataFrame:
        """Generate CSV template from schema."""
        schema = self.get_schema()
        properties = schema.get('properties', {})
        
        # Create empty DataFrame with schema fields as columns
        columns = []
        sample_data = {}
        
        for field, field_schema in properties.items():
            if field_schema.get('type') == 'object':
                continue  # Skip complex objects in templates
                
            columns.append(field)
            
            # Add sample/example data
            if 'example' in field_schema:
                sample_data[field] = field_schema['example']
            elif field_schema.get('type') == 'string':
                sample_data[field] = f"Sample {field}"
            elif field_schema.get('type') in ['number', 'integer']:
                sample_data[field] = 100.0
            elif field_schema.get('type') == 'boolean':
                sample_data[field] = True
            else:
                sample_data[field] = ""
        
        # Return template with one sample row
        template_df = pd.DataFrame([sample_data])
        return template_df.reindex(columns=columns)  # Ensure column order
    
    def load_file(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Load data from CSV, Excel, or JSON file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif file_ext == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        df = pd.DataFrame(data)
                    else:
                        df = pd.DataFrame([data])
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error loading file: {str(e)}")
    
    def calculate_file_hash(self, file_path: Union[str, Path]) -> str:
        """Calculate MD5 hash of file to detect duplicates."""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def map_columns(self, df: pd.DataFrame, mappings: List[ColumnMapping]) -> pd.DataFrame:
        """Apply column mappings and transformations."""
        mapped_df = df.copy()
        
        # Apply mappings
        column_map = {m.source_column: m.target_field for m in mappings}
        mapped_df = mapped_df.rename(columns=column_map)
        
        # Apply transformations
        for mapping in mappings:
            if mapping.target_field in mapped_df.columns and mapping.transform:
                col = mapping.target_field
                
                if mapping.transform == 'upper':
                    mapped_df[col] = mapped_df[col].astype(str).str.upper()
                elif mapping.transform == 'lower':
                    mapped_df[col] = mapped_df[col].astype(str).str.lower()
                elif mapping.transform == 'strip':
                    mapped_df[col] = mapped_df[col].astype(str).str.strip()
                elif mapping.transform == 'date':
                    mapped_df[col] = pd.to_datetime(mapped_df[col], errors='coerce')
                elif mapping.transform == 'number':
                    mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce')
        
        return mapped_df
    
    def validate_data(self, df: pd.DataFrame) -> tuple[List[Dict], List[str]]:
        """Validate data against schema. Returns (row_errors, warnings)."""
        schema = self.get_schema()
        required_fields = schema.get('required', [])
        properties = schema.get('properties', {})
        
        row_errors = []
        warnings = []
        
        for idx, row in df.iterrows():
            row_errors_for_row = []
            
            # Check required fields
            for field in required_fields:
                field_value = row.get(field)
                if field not in df.columns or pd.isna(field_value) or str(field_value if field_value is not None else '').strip() == '':
                    row_errors_for_row.append(f"Missing required field: {field}")
            
            # Check field types and constraints
            for field, value in row.items():
                if field in properties and not pd.isna(value):
                    field_schema = properties[field]
                    
                    # Type validation
                    field_type = field_schema.get('type')
                    if field_type == 'number' and not isinstance(value, (int, float)):
                        try:
                            float(value)
                        except ValueError:
                            row_errors_for_row.append(f"{field}: must be a number")
                    
                    # Length constraints
                    if field_type == 'string' and isinstance(value, str):
                        max_length = field_schema.get('maxLength')
                        if max_length and len(value) > max_length:
                            row_errors_for_row.append(f"{field}: exceeds maximum length {max_length}")
                        
                        min_length = field_schema.get('minLength')
                        if min_length and len(value) < min_length:
                            row_errors_for_row.append(f"{field}: below minimum length {min_length}")
                    
                    # Pattern validation
                    pattern = field_schema.get('pattern')
                    if pattern and isinstance(value, str):
                        import re
                        if not re.match(pattern, value):
                            row_errors_for_row.append(f"{field}: does not match required pattern")
            
            if row_errors_for_row:
                row_errors.append({
                    'row': idx + 1,
                    'errors': row_errors_for_row,
                    'data': row.to_dict()
                })
        
        # Add warnings for missing optional fields
        for field in properties:
            if field not in df.columns:
                warnings.append(f"Optional field '{field}' not found in data")
        
        return row_errors, warnings
    
    def process_upload(
        self, 
        file_path: Union[str, Path],
        mappings: List[ColumnMapping],
        mode: str = 'append',  # 'append', 'upsert', 'replace'
        transform_fn: Optional[Callable] = None
    ) -> UploadResult:
        """
        Complete upload pipeline: load -> map -> validate -> transform -> stage.
        Returns detailed result with metrics and errors.
        """
        
        batch_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        file_hash = self.calculate_file_hash(file_path)
        
        try:
            # Check for duplicate uploads
            if self.audit_logger.is_duplicate_upload(file_hash):
                return UploadResult(
                    batch_id=batch_id,
                    success=False,
                    total_rows=0,
                    processed_rows=0,
                    error_rows=0,
                    warnings=[],
                    errors=["File already uploaded (duplicate detected)"],
                    row_errors=[],
                    file_hash=file_hash,
                    timestamp=timestamp
                )
            
            # Load and process data
            df = self.load_file(file_path)
            total_rows = len(df)
            
            if total_rows == 0:
                return UploadResult(
                    batch_id=batch_id,
                    success=False,
                    total_rows=0,
                    processed_rows=0,
                    error_rows=0,
                    warnings=[],
                    errors=["File is empty"],
                    row_errors=[],
                    file_hash=file_hash,
                    timestamp=timestamp
                )
            
            # Apply column mappings
            mapped_df = self.map_columns(df, mappings)
            
            # Apply custom transformation if provided
            if transform_fn:
                mapped_df = transform_fn(mapped_df)
            
            # Validate data
            row_errors, warnings = self.validate_data(mapped_df)
            error_rows = len(row_errors)
            processed_rows = total_rows - error_rows
            
            # Save to staging if any rows are valid
            if processed_rows > 0:
                # Filter out error rows for staging
                error_indices = [err['row'] - 1 for err in row_errors]
                valid_df = mapped_df.drop(index=error_indices)
                
                # Save to staging
                staging_file = self.staging_dir / f"{self.tenant_id}_{self.entity_type}_{batch_id}.json"
                staging_data = {
                    'batch_id': batch_id,
                    'entity_type': self.entity_type,
                    'tenant_id': self.tenant_id,
                    'mode': mode,
                    'timestamp': timestamp,
                    'file_hash': file_hash,
                    'data': valid_df.to_dict('records')
                }
                
                with open(staging_file, 'w') as f:
                    json.dump(staging_data, f, indent=2, default=str)
            
            # Log upload attempt
            self.audit_logger.log_upload(
                entity_type=self.entity_type,
                batch_id=batch_id,
                file_hash=file_hash,
                mode=mode,
                total_rows=total_rows,
                processed_rows=processed_rows,
                error_rows=error_rows,
                success=processed_rows > 0
            )
            
            return UploadResult(
                batch_id=batch_id,
                success=processed_rows > 0,
                total_rows=total_rows,
                processed_rows=processed_rows,
                error_rows=error_rows,
                warnings=warnings,
                errors=[],
                row_errors=row_errors,
                file_hash=file_hash,
                timestamp=timestamp
            )
            
        except Exception as e:
            # Log failed upload
            self.audit_logger.log_upload(
                entity_type=self.entity_type,
                batch_id=batch_id,
                file_hash=file_hash,
                mode=mode,
                total_rows=0,
                processed_rows=0,
                error_rows=0,
                success=False,
                error_message=str(e)
            )
            
            return UploadResult(
                batch_id=batch_id,
                success=False,
                total_rows=0,
                processed_rows=0,
                error_rows=0,
                warnings=[],
                errors=[str(e)],
                row_errors=[],
                file_hash=file_hash,
                timestamp=timestamp
            )