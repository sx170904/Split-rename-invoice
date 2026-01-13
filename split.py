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
                lines = [line.strip() for line in page_text.split('\n')]

                # 1. Extract Invoice Number (Example: IN3048)
                invoice_no_match = re.search(r"INVOICE\s*NO\s*[:\s]*(\w+)", page_text, re.IGNORECASE)
                invoice_no = invoice_no_match.group(1) if invoice_no_match else "UnknownInvoice"

                # 2. Extract Schedule Date & Format (Example: 02FEBRUARY2023)
                schedule_match = re.search(r"Schedule[:\s]*([^\n]+)", page_text, re.IGNORECASE)
                schedule_date = "NoDate"
                if schedule_match:
                    raw_date = schedule_match.group(1).strip()
                    # Remove ALL spaces and slashes as requested
                    schedule_date = re.sub(r"[\s/]+", "", raw_date)

                # 3. Extract Client Name (Line directly below "INVOICE")
                client_name = "UnknownClient"
                for idx, line in enumerate(lines):
                    if line.strip().upper() == "INVOICE":
                        # Check if there is a line after "INVOICE"
                        if idx + 1 < len(lines):
                            potential_name = lines[idx+1].strip()
                            # Ensure we don't accidentally grab a label like "ATTN" or "DATE"
                            if not any(label in potential_name.upper() for label in ["ATTN", "DATE", "NO :", "TEL"]):
                                client_name = potential_name
                                break
                
                # Sanitize client name for filename (remove invalid chars, keep spaces as underscores)
                client_name = "".join(c for c in client_name if c.isalnum() or c == ' ').strip()
                client_name = client_name.replace(" ", "_")

                # ----------------- Create individual PDF -----------------
                pdf_writer = PyPDF2.PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[i])
                pdf_bytes = BytesIO()
                pdf_writer.write(pdf_bytes)

                # ----------------- Final Filename -----------------
                # Format: <InvoiceNo>_<ScheduleDate>_<ClientName>.pdf
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