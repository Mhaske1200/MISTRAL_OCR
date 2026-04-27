import streamlit as st
from mistralai import Mistral
import os
from deep_translator import GoogleTranslator


# ------------------ CONFIG ------------------
# Hardcoded API Key (replace with your actual key)
API_KEY = "uPfVIl67PTwvqiEFLFFfDjjbXQsCqjLB"



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
uploaded_file = st.file_uploader("📤 Upload PDF document", type=["pdf"])

if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("📤 Uploading for OCR..."):
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
                            {"type": "document_url", "document_url": st.session_state.signed_url}
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
                    st.write("Debug: 💭 Query translated to English:", query_translated)
                    st.write("Debug: 🤖 Answer translated to English:", answer_translated)

                st.success("✅ Response:")
                st.markdown(response.choices[0].message.content)

            except Exception as e:
                st.error(f"❌ Error: {e}")

else:
    st.info("📁 Please upload a document to get started.")
