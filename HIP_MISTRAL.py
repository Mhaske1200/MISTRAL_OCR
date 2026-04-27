
import streamlit as st
from mistralai import Mistral
import pandas as pd
import json
import time
import io

# ------------------ CONFIG ------------------
API_KEY = "rCNHWqxVouTaUudluW7B1qx45kfNi5zS"

# Load field mappings
with open("HIP/dme_field_mapping.json", "r") as f:
    dme_mapping = json.load(f)
with open("HIP/snf_field_mapping.json", "r") as f:
    snf_mapping = json.load(f)

# Merge both case types into one structure
FIELD_MAPPINGS = {**dme_mapping, **snf_mapping}

# ------------------ APP SETUP ------------------
st.set_page_config(page_title="Mistral PDF Field Extractor", layout="wide")
st.title("📄 Structured Field Extraction from PDF using Mistral")
st.write("Upload a PDF contract and extract structured fields by document section.")

client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📤 Upload PDF file", type=["pdf"])
selected_case_type = st.selectbox("📂 Select Case Type", list(FIELD_MAPPINGS.keys()))

if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("📤 Uploading and analyzing document..."):
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

    st.success("✅ Document uploaded successfully!")

# ------------------ EXTRACT FIELDS ------------------
def generate_prompt(doc_name, fields_dict):
    lines = [f'You are an expert assistant. Extract the following fields from the document section named "{doc_name}".\n']
    for i, (field_name, keywords) in enumerate(fields_dict.items(), 1):
        lines.append(f"{i}. Field: {field_name}")
        lines.append(f"   Keywords: {', '.join(keywords)}\n")
    lines.append("Please return the extracted values in this format:")
    lines.append("{")
    for field_name in fields_dict:
        lines.append(f'  "{field_name}": "<value>",')
    lines.append("}")
    return "\n".join(lines)



def extract_doc_categories(signed_url):
    prompt = "Give me document category along with page numbers that belong to the category in tabular form"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "document_url", "document_url": signed_url}
            ]
        }
    ]
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error fetching categories: {e}"


# ------------------ PROCESS ------------------
if st.session_state.get("file_uploaded"):
    if st.button("🔍 Extract Fields from All Documents"):
        results = []
        start_time = time.time()  # Start timing

        st.subheader("📑 Document Categories and Page Numbers")
        with st.spinner("🔍 Analyzing document structure..."):
            category_info = extract_doc_categories(st.session_state.signed_url)
            st.code(category_info)

        with st.spinner("🧠 Extracting fields for all documents..."):
            document_mapping = FIELD_MAPPINGS[selected_case_type]
            for doc_name, fields in document_mapping.items():
                prompt = generate_prompt(doc_name, fields)
                print("PRINTING PROMPT :: ",prompt)
                try:
                    messages = [
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
                    answer = response.choices[0].message.content
                    print("PRINTING RESPONSE :: ", answer)
                    results.append({"Document Name": doc_name, "Extracted Fields": answer})
                    time.sleep(5)
                except Exception as e:
                    results.append({"Document Name": doc_name, "Extracted Fields": f"Error: {e}"})

        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time

        df = pd.DataFrame(results)
        st.success(f"✅ Extraction complete in {elapsed_time:.2f} seconds!")
        st.dataframe(df, use_container_width=True)

        # Download button
        # csv = df.to_csv(index=False).encode('utf-8')
        # st.download_button(
        #     label="⬇️ Download Results as CSV",
        #     data=csv,
        #     file_name="extracted_fields.csv",
        #     mime="text/csv"
        # )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: Extracted Fields
            df.to_excel(writer, sheet_name="Extracted Fields", index=False)

            # Sheet 2: Document Categories (parse to a DataFrame if tabular)
            try:
                # Attempt to parse tabular content using pandas
                category_lines = [line for line in category_info.strip().split("\n") if "|" in line]
                if category_lines:
                    headers = [h.strip() for h in category_lines[0].split("|") if h.strip()]
                    rows = [[cell.strip() for cell in line.split("|") if cell.strip()] for line in category_lines[1:]]
                    category_df = pd.DataFrame(rows, columns=headers)
                else:
                    # Fallback to simple raw content if parsing fails
                    category_df = pd.DataFrame({"Raw Output": [category_info]})
            except Exception as e:
                category_df = pd.DataFrame({"Parsing Error": [str(e)]})

            category_df.to_excel(writer, sheet_name="Document Categories", index=False)


        st.download_button(
            label="⬇️ Download Results as Excel",
            data=output,
            file_name="extracted_fields.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
