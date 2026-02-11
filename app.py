import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import zipfile

# --- CONFIGURATION ---
# Define the font to use (Arial is standard)
FONT_FAMILY = 'Arial'

def generate_pdf(dataframe, filename):
    """Generates a PDF object from the dataframe slice."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font(FONT_FAMILY, size=8)
    
    # Simple table logic
    col_width = 280 / len(dataframe.columns)
    line_height = 6

    for index, row in dataframe.iterrows():
        for cell in row:
            txt = str(cell) if pd.notna(cell) else ""
            # Clean text to prevent encoding errors
            txt = txt.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(col_width, line_height, txt=txt[:25], border=0)
        pdf.ln(line_height)
    
    return pdf

def find_visit_number(df_slice):
    """Scans the slice to find the Visit Number."""
    for r_idx, row in df_slice.iterrows():
        for c_idx, cell_value in enumerate(row):
            if isinstance(cell_value, str) and "Visit" in cell_value:
                # Look at the next few cells to find the number
                for offset in range(1, 6):
                    if c_idx + offset < len(row):
                        val = row.iloc[c_idx + offset]
                        if pd.notna(val) and str(val).strip() != "":
                            return str(val).strip()
    return "Unknown_Visit"

# --- MAIN WEB APP ---
st.title("🏥 Invoice Splitter Tool")
st.write("Upload the bulk invoice file to separate it into individual PDFs named by Visit Number.")

uploaded_file = st.file_uploader("Upload CSV or Excel", type=['csv', 'xlsx'])

if uploaded_file is not None:
    if st.button("Process Invoices"):
        with st.spinner('Reading file and splitting invoices...'):
            # Load Data
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, header=None, skip_blank_lines=False)
                else:
                    df = pd.read_excel(uploaded_file, header=None)
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.stop()

            # Identify split points (searching for 'Andalusia Hospitals Smouha')
            # You can change this keyword if the header changes
            mask = df.apply(lambda row: row.astype(str).str.contains('Andalusia Hospitals Smouha', case=False).any(), axis=1)
            start_indices = df.index[mask].tolist()
            start_indices.append(len(df)) # End of file marker

            # Prepare ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                progress_bar = st.progress(0)
                total_invoices = len(start_indices) - 1
                
                for i in range(total_invoices):
                    # Update progress bar
                    progress_bar.progress((i + 1) / total_invoices)
                    
                    # Slice Data
                    start = start_indices[i]
                    end = start_indices[i+1]
                    invoice_df = df.iloc[start:end].copy()
                    
                    # Get Filename
                    visit_num = find_visit_number(invoice_df)
                    safe_name = "".join([c for c in visit_num if c.isalnum() or c in ('-','_')])
                    if not safe_name: safe_name = f"Invoice_{i}"
                    
                    # Generate PDF in memory
                    pdf = generate_pdf(invoice_df, safe_name)
                    pdf_bytes = pdf.output(dest='S').encode('latin-1') # Output to string buffer
                    
                    # Add to ZIP
                    zip_file.writestr(f"{safe_name}.pdf", pdf_bytes)

            st.success(f"Done! Found {total_invoices} invoices.")
            
            # Create Download Button
            st.download_button(
                label="📥 Download All Invoices (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="Split_Invoices.zip",
                mime="application/zip"
            )