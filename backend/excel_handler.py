import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

def save_data_to_excel(data_list, output_dir):
    if not data_list:
        return None

    # create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"google_maps_data_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)

    # Convert to DataFrame
    df = pd.DataFrame(data_list)
    
    # Reorder/Ensure columns exist
    expected_cols = ['name', 'phone', 'email', 'facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'website', 'address', 'rating', 'reviews', 'category', 'hours', 'files_url']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "N/A"
            
    # Select and rename for export
    export_df = df[expected_cols].copy()
    export_df.columns = ['Name', 'Phone', 'Email', 'Facebook', 'Instagram', 'Twitter', 'LinkedIn', 'YouTube', 'TikTok', 'Website', 'Address', 'Rating', 'Reviews', 'Category', 'Hours', 'Map URL']

    # Export to Excel
    export_df.to_excel(filepath, index=False, sheet_name='Business Data')

    # Formatting with openpyxl
    wb = load_workbook(filepath)
    ws = wb['Business Data']

    # Bold headers
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Auto-size columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter # Get the column name
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        if adjusted_width > 50: # Cap width
            adjusted_width = 50
        ws.column_dimensions[column].width = adjusted_width

    # Summary sheet
    ws_summary = wb.create_sheet('Summary')
    ws_summary['A1'] = 'Total Records Scraped'
    ws_summary['B1'] = len(data_list)
    ws_summary['A2'] = 'Scrape Date'
    ws_summary['B2'] = timestamp

    wb.save(filepath)
    return filepath
