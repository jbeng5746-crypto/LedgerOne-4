"""
Reusable Streamlit UI components for bulk upload functionality.
Provides consistent upload interface across all modules.
"""
import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import tempfile
import os

def render_upload_widget(
    title: str,
    entity_type: str,
    get_template_fn: Callable,
    process_upload_fn: Callable,
    column_help: Optional[Dict[str, str]] = None,
    extra_options: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Reusable upload widget for any entity type.
    
    Args:
        title: Widget title (e.g., "Vendor Upload")
        entity_type: Type of entity being uploaded
        get_template_fn: Function to get upload template
        process_upload_fn: Function to process the upload
        column_help: Optional help text for columns
        extra_options: Additional upload options
    
    Returns:
        Upload result dictionary or None if no upload processed
    """
    
    st.subheader(f"📁 {title}")
    
    # Create tabs for different upload actions
    template_tab, upload_tab, history_tab = st.tabs(["📋 Template", "⬆️ Upload", "📊 History"])
    
    with template_tab:
        st.write(f"Download the {entity_type} template to see the required format and sample data.")
        
        try:
            template_df = get_template_fn()
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button(f"📥 Download {title} Template", key=f"download_{entity_type}"):
                    # Convert to CSV for download
                    csv = template_df.to_csv(index=False)
                    st.download_button(
                        label=f"💾 Save Template as CSV",
                        data=csv,
                        file_name=f"{entity_type}_template.csv",
                        mime="text/csv",
                        key=f"save_{entity_type}_template"
                    )
            
            with col2:
                st.metric("Template Columns", len(template_df.columns))
            
            # Show template preview
            st.write("**Template Preview:**")
            st.dataframe(template_df, use_container_width=True)
            
            # Show column help if provided
            if column_help:
                with st.expander("📖 Column Descriptions"):
                    for col, help_text in column_help.items():
                        st.write(f"**{col}**: {help_text}")
                        
        except Exception as e:
            st.error(f"Error generating template: {str(e)}")
    
    with upload_tab:
        st.write(f"Upload your {entity_type} data using CSV, Excel, or JSON format.")
        
        # File upload
        uploaded_file = st.file_uploader(
            f"Choose {entity_type} file",
            type=['csv', 'xlsx', 'xls', 'json'],
            key=f"upload_{entity_type}_file"
        )
        
        if uploaded_file is not None:
            preview_df = None
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Load and preview data
                if uploaded_file.name.endswith('.csv'):
                    preview_df = pd.read_csv(tmp_file_path)
                elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                    preview_df = pd.read_excel(tmp_file_path)
                elif uploaded_file.name.endswith('.json'):
                    with open(tmp_file_path, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            preview_df = pd.DataFrame(data)
                        else:
                            preview_df = pd.DataFrame([data])
                
                if preview_df is not None:
                    st.success(f"✅ File loaded: {len(preview_df)} rows, {len(preview_df.columns)} columns")
                
                    # Show data preview
                    with st.expander("👀 Data Preview", expanded=True):
                        st.dataframe(preview_df.head(10), use_container_width=True)
                
                    # Column mapping interface
                    st.write("**Map your columns to the required fields:**")
                    
                    template_df = get_template_fn()
                    required_fields = list(template_df.columns)
                    uploaded_columns = list(preview_df.columns)
                
                col_mappings = []
                mapping_cols = st.columns(3)
                
                with mapping_cols[0]:
                    st.write("**Your Columns**")
                with mapping_cols[1]:
                    st.write("**Maps To**")
                with mapping_cols[2]:
                    st.write("**Transform**")
                
                for i, uploaded_col in enumerate(uploaded_columns):
                    with mapping_cols[0]:
                        st.text(uploaded_col)
                    
                    with mapping_cols[1]:
                        # Auto-match similar column names
                        auto_match = None
                        for req_field in required_fields:
                            if (uploaded_col.lower().replace('_', ' ') == req_field.lower().replace('_', ' ') or
                                uploaded_col.lower() in req_field.lower() or
                                req_field.lower() in uploaded_col.lower()):
                                auto_match = req_field
                                break
                        
                        selected_field = st.selectbox(
                            "Field",
                            ["(skip)"] + required_fields,
                            index=required_fields.index(auto_match) + 1 if auto_match else 0,
                            key=f"map_{entity_type}_{i}"
                        )
                    
                    with mapping_cols[2]:
                        transform = st.selectbox(
                            "Transform",
                            ["none", "upper", "lower", "strip", "date", "number"],
                            key=f"transform_{entity_type}_{i}"
                        )
                    
                    if selected_field != "(skip)":
                        col_mappings.append({
                            'source': uploaded_col,
                            'target': selected_field,
                            'transform': transform if transform != "none" else None
                        })
                
                # Upload options
                st.write("**Upload Options:**")
                options_cols = st.columns(3)
                
                with options_cols[0]:
                    upload_mode = st.selectbox(
                        "Upload Mode",
                        ["append", "upsert", "replace"],
                        index=1,  # Default to upsert
                        help="Append: Add new records. Upsert: Add/update records. Replace: Replace all data.",
                        key=f"mode_{entity_type}"
                    )
                
                # Entity-specific options
                extra_upload_options = {}
                if extra_options:
                    with options_cols[1]:
                        for opt_name, opt_config in extra_options.items():
                            if opt_config['type'] == 'checkbox':
                                extra_upload_options[opt_name] = st.checkbox(
                                    opt_config['label'],
                                    value=opt_config.get('default', False),
                                    help=opt_config.get('help', ''),
                                    key=f"{opt_name}_{entity_type}"
                                )
                            elif opt_config['type'] == 'text':
                                extra_upload_options[opt_name] = st.text_input(
                                    opt_config['label'],
                                    value=opt_config.get('default', ''),
                                    help=opt_config.get('help', ''),
                                    key=f"{opt_name}_{entity_type}"
                                )
                
                # Process upload button
                if st.button(f"🚀 Process {title}", key=f"process_{entity_type}", type="primary"):
                    if not col_mappings:
                        st.error("Please map at least one column to proceed.")
                    else:
                        with st.spinner(f"Processing {entity_type} upload..."):
                            try:
                                # Call the processing function
                                result = process_upload_fn(
                                    file_path=tmp_file_path,
                                    column_mappings=col_mappings,
                                    mode=upload_mode,
                                    **extra_upload_options
                                )
                                
                                # Clean up temp file
                                os.unlink(tmp_file_path)
                                
                                # Display results
                                if result.get('success'):
                                    st.success(f"✅ {title} completed successfully!")
                                    
                                    # Show metrics
                                    metrics_cols = st.columns(4)
                                    upload_result = result.get('upload_result', {})
                                    
                                    with metrics_cols[0]:
                                        st.metric("Total Rows", upload_result.get('total_rows', 0))
                                    with metrics_cols[1]:
                                        st.metric("Processed", upload_result.get('processed_rows', 0))
                                    with metrics_cols[2]:
                                        st.metric("Errors", upload_result.get('error_rows', 0))
                                    with metrics_cols[3]:
                                        if 'vendor_stats' in result:
                                            stats = result['vendor_stats']
                                        elif 'employee_stats' in result:
                                            stats = result['employee_stats']
                                        elif 'transaction_stats' in result:
                                            stats = result['transaction_stats']
                                        else:
                                            stats = result.get('repository_result', {})
                                        
                                        st.metric("Total Records", stats.get('total', stats.get('created', 0) + stats.get('updated', 0)))
                                    
                                    # Show warnings if any
                                    warnings = upload_result.get('warnings', [])
                                    if warnings:
                                        with st.expander("⚠️ Warnings"):
                                            for warning in warnings:
                                                st.warning(warning)
                                    
                                    # Show errors if any
                                    row_errors = upload_result.get('row_errors', [])
                                    if row_errors:
                                        with st.expander(f"❌ Row Errors ({len(row_errors)})"):
                                            for error in row_errors[:10]:  # Show first 10 errors
                                                st.error(f"Row {error['row']}: {', '.join(error['errors'])}")
                                    
                                    # Entity-specific result displays
                                    if 'deduplication_report' in result and result['deduplication_report']:
                                        report = result['deduplication_report']
                                        with st.expander("🔍 Deduplication Report"):
                                            st.write(f"Duplicates found: {report.get('duplicates_found', 0)}")
                                            st.write(f"Duplicates merged: {report.get('duplicates_merged', 0)}")
                                    
                                    if 'payroll_calculations' in result and result['payroll_calculations']:
                                        calc = result['payroll_calculations']
                                        with st.expander("💰 Payroll Summary"):
                                            summary_cols = st.columns(3)
                                            with summary_cols[0]:
                                                st.metric("Employees", calc.get('total_employees', 0))
                                            with summary_cols[1]:
                                                st.metric("Gross Pay", f"KES {calc.get('totals', {}).get('gross', 0):,.2f}")
                                            with summary_cols[2]:
                                                st.metric("Net Pay", f"KES {calc.get('totals', {}).get('net', 0):,.2f}")
                                    
                                    return result
                                    
                                else:
                                    st.error(f"❌ {title} failed!")
                                    upload_result = result.get('upload_result', {})
                                    errors = upload_result.get('errors', [])
                                    for error in errors:
                                        st.error(error)
                                    
                                    return result
                                    
                            except Exception as e:
                                # Clean up temp file on error
                                if os.path.exists(tmp_file_path):
                                    os.unlink(tmp_file_path)
                                st.error(f"Error processing upload: {str(e)}")
                                return None
                        
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
    
    with history_tab:
        st.write(f"Recent {entity_type} upload history and statistics.")
        
        try:
            # This would be implemented by each manager
            st.info("Upload history will be displayed here.")
            
        except Exception as e:
            st.error(f"Error loading history: {str(e)}")
    
    return None

def render_bulk_operations_sidebar():
    """Render bulk operations sidebar with quick stats and actions."""
    
    with st.sidebar:
        st.header("📊 Bulk Operations")
        
        # Quick stats (placeholder)
        st.metric("Total Uploads Today", "12")
        st.metric("Records Processed", "1,247")
        st.metric("Success Rate", "98.5%")
        
        st.divider()
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        
        if st.button("📥 Download All Templates", help="Download templates for all entity types"):
            st.info("Feature coming soon!")
        
        if st.button("📈 View Upload Analytics", help="View detailed upload analytics"):
            st.info("Feature coming soon!")
        
        if st.button("🔄 Refresh Data", help="Refresh all cached data"):
            st.cache_data.clear()
            st.success("Cache cleared!")
        
        st.divider()
        
        # Recent activity (placeholder)
        st.subheader("🕐 Recent Activity")
        activity_items = [
            "Vendors uploaded (15 min ago)",
            "Payroll processed (1 hour ago)",
            "Transactions reconciled (2 hours ago)"
        ]
        
        for item in activity_items:
            st.text(f"• {item}")

def render_upload_dashboard():
    """Render comprehensive upload dashboard with all entity types."""
    
    st.title("📁 Bulk Data Management")
    st.write("Upload and manage data across all modules with templates, validation, and audit trails.")
    
    # Entity type selector
    entity_tabs = st.tabs([
        "👥 Vendors", 
        "🏢 Employees", 
        "💳 Transactions", 
        "💰 Payroll",
        "📊 Chart of Accounts",
        "🏛️ Tax Configs"
    ])
    
    return entity_tabs