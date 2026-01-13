import streamlit as st
import PyPDF2
import pdfplumber
import re
from io import BytesIO
import zipfile

# ----------------- Streamlit Page Setup -----------------
st.set_page_config(page_title="Invoice Splitter", layout="wide")
st.title("📄 Invoice Splitter & Renamer")
st.markdown("""
Upload a PDF containing multiple invoices.  
The app will split each invoice into a separate PDF and rename it in the format:

**<InvoiceNo>_<ScheduleDate>_<ClientName>**
""")

# ----------------- File Upload -----------------
uploaded_file = st.file_uploader("Upload your PDF file", type="pdf")

if uploaded_file is not None:
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)
    st.write(f"Total pages in PDF: {total_pages}")

    # Prepare ZIP in memory
    zip_buffer = BytesIO()
    processed_count = 0

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for i in range(total_pages):
            # Extract text from the page
            with pdfplumber.open(uploaded_file) as pdf:
                page_text = pdf.pages[i].extract_text() or ""

            # ----------------- Extract Invoice Number -----------------
            invoice_no_match = re.search(r"Invoice No[:\s]*([\w-]+)", page_text, re.IGNORECASE)
            invoice_no = invoice_no_match.group(1) if invoice_no_match else None

            # ----------------- Extract Schedule Date -----------------
            schedule_match = re.search(r"Scheduled[:\s]*([\d/-]+)", page_text, re.IGNORECASE)
            schedule_date = schedule_match.group(1) if schedule_match else None

            # ----------------- Extract Client Name -----------------
            client_name = None
            for line in page_text.split("\n"):
                line_clean = line.strip()
                if line_clean.upper().startswith("ATTN") or "ATTN" in line_clean.upper():
                    # Extract after "ATTN :" or "ATTN:"
                    parts = line_clean.split(":")
                    if len(parts) > 1:
                        client_name = parts[1].strip()
                        # Remove any invalid filename characters except @
                        client_name = ''.join(c for c in client_name if c.isalnum() or c in [' ', '@'])
                        break

            # Skip if any info missing
            if not invoice_no or not schedule_date or not client_name:
                st.warning(f"Skipped page {i+1}: Missing invoice info")
                continue

            # ----------------- Create new PDF in memory -----------------
            pdf_writer = PyPDF2.PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[i])
            pdf_bytes = BytesIO()
            pdf_writer.write(pdf_bytes)

            # ----------------- Add to ZIP -----------------
            output_filename = f"{invoice_no}_{schedule_date}_{client_name}.pdf"
            zip_file.writestr(output_filename, pdf_bytes.getvalue())
            processed_count += 1
            st.write(f"✅ Processed page {i+1}: {output_filename}")

    # ----------------- Finish -----------------
    if processed_count > 0:
        st.success(f"All done! {processed_count} invoices processed.")
        st.download_button(
            label="📥 Download All Invoices as ZIP",
            data=zip_buffer.getvalue(),
            file_name="invoices.zip",
            mime="application/zip"
        )
    else:
        st.error("No invoices processed. Please check your PDF and invoice layout.")
