import streamlit as st
from mistralai import Mistral
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ------------------ CONFIG ------------------
# Hardcoded API Key (replace with your actual key)
API_KEY = "rCNHWqxVouTaUudluW7B1qx45kfNi5zS"

# Streamlit page config
st.set_page_config(page_title="OCR Q&A", layout="wide")
st.title("📄 Document Q&A")
st.write("Upload a PDF once and ask questions about its content.")

# ------------------ INIT MISTRAL ------------------
client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📤 Upload PDF document", type=["pdf"])

if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("📤 Uploading to Mistral for OCR..."):
        uploaded_pdf = client.files.upload(
            file={
                "file_name": uploaded_file.name,
                "content": uploaded_file.read()
            },
            purpose="ocr"
        )
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

        # Save in session
        st.session_state.file_uploaded = True
        st.session_state.file_id = uploaded_pdf.id
        st.session_state.signed_url = signed_url.url

    st.success("✅ File uploaded and processed!")

# ------------------ ASK QUESTIONS ------------------
if st.session_state.get("file_uploaded"):
    user_question = st.text_input("💬 Ask a question about the document")

    if user_question:
        with st.spinner("🤖 Generating response..."):
            try:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_question},
                            {"type": "document_url", "document_url": st.session_state.signed_url}
                        ]
                    }
                ]

                response = client.chat.complete(
                    model="mistral-small-latest",
                    messages=messages
                )

                st.success("✅ Response:")
                st.markdown(response.choices[0].message.content)

                response_text = response.choices[0].message.content
                # Generate PDF in memory
                pdf_buffer = BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=letter)
                width, height = letter

                # Basic word wrapping for longer responses
                lines = response_text.split('\n')
                y = height - 40
                for line in lines:
                    for part in line.split('\n'):
                        if y < 40:
                            c.showPage()
                            y = height - 40
                        c.drawString(40, y, part[:1000])  # drawString has a character width limit
                        y -= 15

                c.save()
                pdf_buffer.seek(0)

                # Streamlit download button
                st.download_button(
                    label="📥 Download Response as PDF",
                    data=pdf_buffer,
                    file_name="response.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error: {e}")

else:
    st.info("📁 Please upload a document to get started.")
