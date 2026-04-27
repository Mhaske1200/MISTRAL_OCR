import streamlit as st
from mistralai import Mistral
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ------------------ CONFIG ------------------
API_KEY = "VoqQ28FJ7kAGs3edB8YAl6woI2hURQg9"  # Replace with your actual Mistral API key

st.set_page_config(page_title="Manufacturing BOM Extractor", layout="wide")
st.title("🏭 Manufacturing BOM Extractor")
st.write("Upload a manufacturing document (e.g., technical drawings, BOM lists, specifications) and choose a task below.")

# ------------------ INIT MISTRAL ------------------
client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📤 Upload a PDF document", type=["pdf"])

if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("🔄 Uploading document to for processing..."):
        uploaded_pdf = client.files.upload(
            file={
                "file_name": uploaded_file.name,
                "content": uploaded_file.read()
            },
            purpose="ocr"
        )
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

        st.session_state.file_uploaded = True
        st.session_state.file_id = uploaded_pdf.id
        st.session_state.signed_url = signed_url.url

    st.success("✅ Document uploaded and ready!")

# ------------------ PROMPTS ------------------
PROMPTS = {
    "summarize": "Summarize this manufacturing document. Focus on the purpose of the document, type of information it contains, and key sections.",
    "extract_bom": "Extract the full Bill of Materials (BOM) from this manufacturing document. Include item numbers, part names, quantities, materials, and other relevant fields in a table format if possible.",
    "explain_table": "Explain the document content in detail and convert it into a structured table. Categorize the data if applicable, and describe each section meaningfully."
}

SYSTEM_PROMPT = """
You are an expert assistant in manufacturing document analysis. Your role is to extract, interpret, and explain Bill of Materials (BOM) and technical data clearly and concisely. Prefer structured formats (like tables) whenever possible.
"""

# ------------------ TASK BUTTONS ------------------
if st.session_state.get("file_uploaded"):
    st.subheader("🧠 Choose an Operation")

    col1, col2, col3 = st.columns(3)
    trigger = None

    with col1:
        if st.button("📝 Summarize Document"):
            trigger = "summarize"
    with col2:
        if st.button("📦 Extract BOM"):
            trigger = "extract_bom"
    with col3:
        if st.button("📊 Explain Details in Table"):
            trigger = "explain_table"

    # ------------------ TASK EXECUTION ------------------
    if trigger:
        st.info(f"Running: {trigger.replace('_', ' ').title()}")
        with st.spinner("🤖 Processing ..."):
            try:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPTS[trigger]},
                            {"type": "document_url", "document_url": st.session_state.signed_url}
                        ]
                    }
                ]

                response = client.chat.complete(
                    model="mistral-small-latest",
                    messages=messages
                )
                response_text = response.choices[0].message.content

                st.success("✅ Output:")
                st.markdown(response_text)

                # ------------------ DOWNLOAD AS PDF ------------------
                pdf_buffer = BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=letter)
                width, height = letter

                lines = response_text.split('\n')
                y = height - 40
                for line in lines:
                    if y < 40:
                        c.showPage()
                        y = height - 40
                    c.drawString(40, y, line[:1000])
                    y -= 15

                c.save()
                pdf_buffer.seek(0)

                st.download_button(
                    label="📥 Download Result as PDF",
                    data=pdf_buffer,
                    file_name=f"{trigger}_output.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error: {e}")

else:
    st.info("📁 Please upload a manufacturing PDF document to begin.")
