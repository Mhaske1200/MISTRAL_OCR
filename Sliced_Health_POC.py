import streamlit as st
from mistralai import Mistral
import pandas as pd

# ------------------ CONFIG ------------------
API_KEY = "uPfVIl67PTwvqiEFLFFfDjjbXQsCqjLB"

FIELDS = {
    "1": {
        "field_name": "provider_name",
        "query": "What is the name of provider",
        "keywords": [
            "Agreement", "Amendment", "Attatchment C", "Authorized Signature",
            "Hospital Agreement", "Hospital Participation Agreement", "Notice of Amendment"
        ]
    },
    "2": {
        "field_name": "effective_date",
        "query": "What is effective date",
        "keywords": [
            "effective date", "signed date", "Amendment", "notice of amendment"
        ]
    },
    "3": {
        "field_name": "termination_date",
        "query": "What is termination date",
        "keywords": [
            "termination", "termination date", "term and termination",
            "termination without cause", "termination for cause", "term for breach"
        ]
    },
    "4": {
        "field_name": "fee_schedule_name",
        "query": "What is the name of fee schedule",
        "keywords": ["WEB SITE", "http://", "URL"]
    },
    "5": {
        "field_name": "inpatient_services",
        "query": "Inpatient Services in Compensation Schedule",
        "keywords": [
            "Per Diem", "All Other Inpatient Services", "Admission Type", "Per Unit",
            "Base Compensation Schedule", "Billing Codes", "Revenue code", "CPT codes", "rates"
        ]
    },
    "6": {
        "field_name": "outpatient_services",
        "query": "Outpatient Services in Compensation Schedule",
        "keywords": [
            "Per Diem", "Outpatient Diagnostic and Therapeutic Services",
            "Outpatient Surgery Services", "Outpatient Rehabilitation Services",
            "Outpatient Mental Health Services", "Outpatient Substance Abuse Services",
            "Outpatient Dialysis Services", "Outpatient Chemotherapy Services",
            "Outpatient Radiation Therapy Services", "Outpatient Cardiac Rehabilitation Services",
            "Outpatient Pulmonary Rehabilitation Services", "Outpatient Physical Therapy Services",
            "Outpatient Occupational Therapy Services", "All Other Outpatient Services",
            "Admission Type", "Per Unit", "Base Compensation Schedule",
            "Multiple Procedure Percent of Allowed", "Billing Codes", "Contracted Rate",
            "Revenue codes", "CPT codes", "rates"
        ]
    },
    "7": {
        "field_name": "payor_name",
        "query": "What is the name of payor",
        "keywords": [
            "Agreement", "Amendment", "Authorized Signature", "Hospital Agreement",
            "Hospital Participation Agreement", "Notice of Amendment"
        ]
    },
    "8": {
        "field_name": "provider_location",
        "query": "What is the location of provider",
        "keywords": [
            "to Hospital at", "Hospital at", "Address", "location", "Authorized Signature",
            "Attatchment C", "Provider Number", "Provider Name", "National Provider Identification"
        ]
    },
    "9": {
        "field_name": "initial_contract_term",
        "query": "What is the initial contract term",
        "keywords": [
            "termination", "termination date", "term and termination",
            "termination without cause", "termination for cause", "term for breach"
        ]
    },
    "10": {
        "field_name": "facilities",
        "query": "What are hospital/provider listings",
        "keywords": [
            "to Hospital at", "Hospital at", "Address", "location", "Attatchment C",
            "Provider Number", "Provider Name", "National Provider Identification",
            "Service and Billing Location Form", "Billing Name"
        ]
    }
}

# ------------------ APP SETUP ------------------
st.set_page_config(page_title="Mistral Auto Q&A", layout="wide")
st.title("📄 Structured Field Extraction from PDF using Mistral")

st.write("Upload a PDF contract and extract key data points using predefined queries and keywords.")

client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📤 Upload PDF file", type=["pdf"])

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

        # Save state
        st.session_state.file_uploaded = True
        st.session_state.file_id = uploaded_pdf.id
        st.session_state.signed_url = signed_url.url

    st.success("✅ Document uploaded successfully!")

# ------------------ FIELD QUERY PROCESSING ------------------
if st.session_state.get("file_uploaded"):
    if st.button("🔍 Extract Fields"):
        results = []

        with st.spinner("🧠 Extracting data for all fields..."):
            for fid, field in FIELDS.items():
                try:
                    query = field["query"]
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": query},
                                {"type": "document_url", "document_url": st.session_state.signed_url}
                            ]
                        }
                    ]
                    response = client.chat.complete(
                        model="mistral-small-latest",
                        messages=messages
                    )
                    answer = response.choices[0].message.content
                    results.append({"Field": field["field_name"], "Answer": answer})

                except Exception as e:
                    results.append({"Field": field["field_name"], "Answer": f"Error: {e}"})

        # Display results in a table
        df = pd.DataFrame(results)
        st.success("✅ Extraction complete!")
        st.dataframe(df, use_container_width=True)
