import streamlit as st
import PyPDF2
import pdfplumber
import re
from io import BytesIO
import zipfile

# ----------------- Streamlit Page Setup -----------------
st.set_page_config(page_title="Invoice Splitter", layout="wide")
st.title("📄 Invoice Splitter & Renamer")

# ----------------- File Upload -----------------
uploaded_file = st.file_uploader("Upload your PDF file", type="pdf")

if uploaded_file is not None:
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)
    st.write(f"Total pages in PDF: {total_pages}")

    zip_buffer = BytesIO()
    processed_count = 0

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        with pdfplumber.open(uploaded_file) as pdf:
            for i in range(total_pages):
                page = pdf.pages[i]
                page_text = page.extract_text() or ""
                lines = [line.strip() for line in page_text.split('\n')]

                # 1. Extract Invoice Number (Example: IN3048)
                invoice_no_match = re.search(r"INVOICE\s*NO\s*[:\s]*(\w+)", page_text, re.IGNORECASE)
                invoice_no = invoice_no_match.group(1) if invoice_no_match else "UnknownInvoice"

                # 2. Extract Schedule Date & Format (Requested: 02FEBRUARY2023)
                schedule_match = re.search(r"Schedule[:\s]*([^\n]+)", page_text, re.IGNORECASE)
                schedule_date = "NoDate"
                if schedule_match:
                    raw_date = schedule_match.group(1).strip()
                    # Remove ALL spaces and slashes as requested
                    schedule_date = re.sub(r"[\s/]+", "", raw_date)

                # 3. Extract Client Name (Flexible logic for text near 'INVOICE' header)
                client_name = "UnknownClient"
                # Locate 'INVOICE' and 'INVOICE NO' to find the text between them
                try:
                    # Capture everything between 'INVOICE' and 'INVOICE NO'
                    # Your PDF often has: INVOICE \n Client Name \n INVOICE NO
                    name_pattern = re.search(r"INVOICE\s+(.*?)\s+INVOICE\s*NO", page_text, re.IGNORECASE | re.DOTALL)
                    if name_pattern:
                        # Take the first line of the captured group
                        client_name = name_pattern.group(1).split('\n')[0].strip()
                    
                    # Fallback: if client_name is empty or too short, look for the line after 'INVOICE'
                    if client_name == "UnknownClient" or len(client_name) < 2:
                        for idx, line in enumerate(lines):
                            if "INVOICE" == line.upper():
                                if idx + 1 < len(lines):
                                    client_name = lines[idx+1].strip()
                                    break
                except Exception:
                    pass
                
                # Sanitize client name for filename
                client_name = "".join(c for c in client_name if c.isalnum() or c == ' ').strip()
                client_name = client_name.replace(" ", "_")

                # ----------------- Create individual PDF -----------------
                pdf_writer = PyPDF2.PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[i])
                pdf_bytes = BytesIO()
                pdf_writer.write(pdf_bytes)

                # ----------------- Final Filename -----------------
                output_filename = f"{invoice_no}_{schedule_date}_{client_name}.pdf"
                zip_file.writestr(output_filename, pdf_bytes.getvalue())
                processed_count += 1
                st.write(f"✅ Processed page {i+1}: {output_filename}")

    # ----------------- Download Button -----------------
    if processed_count > 0:
        st.success(f"Processing complete! {processed_count} invoices renamed.")
        st.download_button(
            label="📥 Download All Invoices as ZIP",
            data=zip_buffer.getvalue(),
            file_name="split_invoices.zip",
            mime="application/zip"
        )