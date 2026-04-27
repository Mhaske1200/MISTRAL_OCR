import streamlit as st
from mistralai import Mistral
import os
from deep_translator import GoogleTranslator


# ------------------ CONFIG ------------------
# Hardcoded API Key (replace with your actual key)
API_KEY = "VoqQ28FJ7kAGs3edB8YAl6woI2hURQg9"



# Streamlit page config
st.set_page_config(page_title="Arabic Multi-Document Q&A", layout="wide")
# Display company logo if available.
logo_path = "GENZEON_LOGO.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=200)
st.title("Arabic Multi-Document Q&A Chat Interface")
st.markdown("Upload PDF documents to build a knowledge base and ask questions based on the uploaded content.")

# ------------------ INIT MISTRAL ------------------
client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_files = st.file_uploader("📤 Upload PDF documents", type=["pdf"], accept_multiple_files=True)

# Initialize session state to store uploaded file data
if "file_data" not in st.session_state:
    st.session_state.file_data = []

# Process uploaded files
if uploaded_files:
    for uploaded_file in uploaded_files:
        # Prevent duplicate uploads
        if uploaded_file.name not in [f.get("file_name") for f in st.session_state.file_data]:
            with st.spinner(f"📤 Uploading {uploaded_file.name} for OCR..."):
                try:
                    uploaded_pdf = client.files.upload(
                        file={
                            "file_name": uploaded_file.name,
                            "content": uploaded_file.read()
                        },
                        purpose="ocr"
                    )
                    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

                    if uploaded_pdf and signed_url:
                        st.session_state.file_data.append({
                            "file_id": uploaded_pdf.id,
                            "signed_url": signed_url.url,
                            "file_name": uploaded_file.name
                        })
                        st.success(f"✅ {uploaded_file.name} uploaded and processed!")
                    else:
                        st.warning(f"⚠️ Failed to retrieve data for {uploaded_file.name}")

                except Exception as e:
                    st.error(f"❌ Error uploading {uploaded_file.name}: {e}")


# ------------------ ASK QUESTIONS ------------------
if st.session_state.get("file_data"):  # Safe check
    user_question = st.text_input("💬 Ask a question about the document")

    if user_question:
        with st.spinner("🤖 Generating response..."):
            try:
                prompt = f"السؤال: {user_question}"
                messages = [
                    {
                        "role": "system",
                        "content": "أنت مساعد ذكي تجيب فقط باللغة العربية، ومتخصص في قراءة وفهم المستندات بجميع أنواعها."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            *[
                                {"type": "document_url", "document_url": doc["signed_url"]}
                                for doc in st.session_state.file_data
                            ]
                        ]
                    }
                ]

                response = client.chat.complete(
                    model="mistral-small-latest",
                    messages=messages
                )

                answer = response.choices[0].message.content.strip()

                # Debug translations using deep-translator:
                translator = GoogleTranslator(source='auto', target='en')
                query_translated = translator.translate(user_question)
                answer_translated = translator.translate(answer)

                with st.expander("Debug Translations"):
                    st.write("💭 Query (EN):", query_translated)
                    st.write("🤖 Answer (EN):", answer_translated)

                st.success("✅ Response:")
                st.markdown(answer)

            except Exception as e:
                st.error(f"❌ Error generating response: {e}")
else:
    st.info("📁 Please upload a document to get started.")
