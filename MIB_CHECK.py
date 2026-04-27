import streamlit as st
from mistralai import Mistral
import xml.etree.ElementTree as ET

# ------------------ CONFIG ------------------
API_KEY = "uPfVIl67PTwvqiEFLFFfDjjbXQsCqjLB"  # Replace with your actual API key
st.set_page_config(page_title="Mistral XML Q&A", layout="wide")
st.title("🗂️ Mistral XML Document Q&A")
st.write("Upload an XML file and ask questions about its content using the Mistral API.")

# ------------------ INIT MISTRAL ------------------
client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📤 Upload XML document", type=["xml"])

if uploaded_file and "xml_content" not in st.session_state:
    try:
        with st.spinner("📄 Parsing XML..."):
            tree = ET.parse(uploaded_file)
            root = tree.getroot()

            def extract_text(elem):
                """Recursively extract text from XML."""
                text = elem.text or ""
                for child in elem:
                    text += extract_text(child)
                return text

            full_text = extract_text(root).strip()
            st.session_state.xml_content = full_text

        st.success("✅ XML parsed successfully!")

    except Exception as e:
        st.error(f"❌ Failed to parse XML: {e}")

# ------------------ ASK QUESTIONS ------------------
if st.session_state.get("xml_content"):
    user_question = st.text_input("💬 Ask a question about the XML content")

    if user_question:
        with st.spinner("🤖 Generating response..."):
            try:
                messages = [
                    {"role": "user", "content": f"Document content:\n{st.session_state.xml_content}\n\nQuestion:\n{user_question}"}
                ]

                response = client.chat.complete(
                    model="mistral-small-latest",
                    messages=messages
                )

                st.success("✅ Response:")
                st.markdown(response.choices[0].message.content)

            except Exception as e:
                st.error(f"❌ Error: {e}")

else:
    st.info("📁 Please upload an XML document to get started.")
