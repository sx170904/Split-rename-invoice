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
        # Use pdfplumber for the whole file to avoid reopening it in the loop
        with pdfplumber.open(uploaded_file) as pdf:
            for i in range(total_pages):
                page_text = pdf.pages[i].extract_text() or ""
                lines = [line.strip() for line in page_text.split('\n')]

                # 1. Extract Invoice Number (Format: IN3048)
                invoice_no_match = re.search(r"INVOICE\s*NO\s*[:\s]*(\w+)", page_text, re.IGNORECASE)
                invoice_no = invoice_no_match.group(1) if invoice_no_match else "UnknownInvoice"

                # 2. Extract Schedule Date (Format: 02 FEBRUARY 2023 or 20/12/2023)
                # Looks for "Schedule:" and captures the date following it
                schedule_match = re.search(r"Schedule[:\s]*([\w\d\s/-]+)", page_text, re.IGNORECASE)
                schedule_date = "NoDate"
                if schedule_match:
                    # Clean up the date string (remove leading/trailing spaces)
                    schedule_date = schedule_match.group(1).strip().split('\n')[0]
                    # Replace spaces/slashes with underscores for valid filename
                    schedule_date = re.sub(r"[\s/]+", "_", schedule_date)

                # 3. Extract Client Name (ATTN field)
                client_name = "UnknownClient"
                for idx, line in enumerate(lines):
                    if "ATTN" in line.upper():
                        # If "ATTN :" is followed by text on the same line
                        if ":" in line:
                            parts = line.split(":")
                            if len(parts) > 1 and parts[1].strip():
                                client_name = parts[1].strip()
                                break
                        # If the name is on the next line (sometimes happens in PDF parsing)
                        if idx + 1 < len(lines):
                            client_name = lines[idx+1].strip()
                            break
                
                # Sanitize client name for filename
                client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '_')).strip()
                client_name = client_name.replace(" ", "_")

                # ----------------- Create new PDF -----------------
                pdf_writer = PyPDF2.PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[i])
                pdf_bytes = BytesIO()
                pdf_writer.write(pdf_bytes)

                # ----------------- Add to ZIP -----------------
                output_filename = f"{invoice_no}_{schedule_date}_{client_name}.pdf"
                zip_file.writestr(output_filename, pdf_bytes.getvalue())
                processed_count += 1
                st.write(f"✅ Processed page {i+1}: {output_filename}")

    # ----------------- Download -----------------
    if processed_count > 0:
        st.success(f"All done! {processed_count} invoices processed.")
        st.download_button(
            label="📥 Download All Invoices as ZIP",
            data=zip_buffer.getvalue(),
            file_name="split_invoices.zip",
            mime="application/zip"
        )