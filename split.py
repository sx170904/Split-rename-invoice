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
                page_text = pdf.pages[i].extract_text() or ""
                
                # 1. Extract Invoice Number (e.g., IN3048)
                invoice_no_match = re.search(r"INVOICE\s*NO\s*[:\s]*(\w+)", page_text, re.IGNORECASE)
                invoice_no = invoice_no_match.group(1) if invoice_no_match else "UnknownInvoice"

                # 2. Extract Schedule Date & Format (e.g., 02FEBRUARY2023)
                schedule_match = re.search(r"Schedule[:\s]*([^\n]+)", page_text, re.IGNORECASE)
                schedule_date = "NoDate"
                if schedule_match:
                    raw_date = schedule_match.group(1).strip()
                    # Remove spaces and slashes within the date
                    schedule_date = re.sub(r"[\s/]+", "", raw_date)

                # 3. Extract Client Name (The text right below "INVOICE")
                client_name = "UnknownClient"
                # Look for text between 'INVOICE' and 'INVOICE NO'
                name_pattern = re.search(r"INVOICE\s+(.*?)\s+INVOICE\s*NO", page_text, re.IGNORECASE | re.DOTALL)
                
                if name_pattern:
                    raw_name = name_pattern.group(1).split('\n')[0].strip()
                    # Remove all non-alphanumeric characters from the name (No spaces, no underscores)
                    client_name = re.sub(r"[^a-zA-Z0-9]+", "", raw_name)
                
                # ----------------- Create individual PDF -----------------
                pdf_writer = PyPDF2.PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[i])
                pdf_bytes = BytesIO()
                pdf_writer.write(pdf_bytes)

                # ----------------- Final Filename -----------------
                # Format: <InvoiceNo>_<ScheduleDate>_<ClientNameWithoutSpaces>.pdf
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