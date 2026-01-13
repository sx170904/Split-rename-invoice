import streamlit as st
import PyPDF2
import pdfplumber
import re
from io import BytesIO
import zipfile

# ----------------- Streamlit Page Setup -----------------
st.set_page_config(page_title="Invoice Splitter", layout="wide")
st.title("📄 Invoice Splitter & Renamer")
st.markdown("Upload a PDF to split and rename based on: **<InvoiceNo>_<ScheduleDate>_<ClientName>**")

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
                lines = [line.strip() for line in page_text.split('\n')]

                # 1. Extract Invoice Number (Example: IN3048)
                invoice_no_match = re.search(r"INVOICE\s*NO\s*[:\s]*(\w+)", page_text, re.IGNORECASE)
                invoice_no = invoice_no_match.group(1) if invoice_no_match else "UnknownInvoice"

                # 2. Extract Schedule Date (Example: 02 FEBRUARY 2023 or 20/12/2023)
                # This looks for "Schedule:" and captures the text until the end of that line
                schedule_match = re.search(r"Schedule[:\s]*([^\n]+)", page_text, re.IGNORECASE)
                schedule_date = "NoDate"
                if schedule_match:
                    raw_date = schedule_match.group(1).strip()
                    # Sanitize date (remove slashes and extra spaces for filename safety)
                    schedule_date = re.sub(r"[\s/]+", "_", raw_date)

                # 3. Extract Client Name (Fixed for Quotation No)
                # This Regex captures everything between ATIN/ATTN and the next major label (QUOTATION/TEL)
                client_name = "UnknownClient"
                attn_pattern = re.search(r"(?:ATT?N)[:\s]*(.*?)(?=QUOTATION|TEL|PAYMENT|\n|$)", page_text, re.IGNORECASE | re.DOTALL)
                
                if attn_pattern:
                    client_name = attn_pattern.group(1).strip()
                    # Remove any leftover quotes or commas from PDF artifacts
                    client_name = client_name.replace('"', '').replace(',', '').strip()

                # Clean client name for safe filename
                client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '_')).strip()
                client_name = client_name.replace(" ", "_")

                # ----------------- Create individual PDF for this page -----------------
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