import streamlit as st
from mistralai import Mistral
import pandas as pd
import json
import time
import io
import re

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
st.set_page_config(page_title="Genzeon PDF Field Extractor", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for professional styling
st.markdown("""
    <style>
        /* Main background */
        .main {
            padding-top: 2rem;
        }
        
        /* Header styling */
        .header-container {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .header-text h1 {
            color: white;
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }
        
        .header-text p {
            color: rgba(255,255,255,0.9);
            margin: 5px 0 0 0;
            font-size: 1.1em;
        }
        
        .logo-container img {
            max-height: 100px;
            object-fit: contain;
        }
        
        /* Card styling */
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            transform: translateY(-2px);
        }
        
        /* Info/Success/Warning boxes */
        .info-box {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            border-left: 5px solid #667eea;
            border-radius: 8px;
            padding: 15px 20px;
            margin: 15px 0;
        }
        
        /* Selectbox styling */
        .stSelectbox, .stFileUploader {
            margin: 15px 0;
        }
        
        /* Progress bar enhancement */
        .stProgress > div > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Table styling */
        .stDataframe {
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* Metric cards */
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# Header with Logo
col_logo, col_title = st.columns([1, 4])

with col_logo:
    try:
        st.image("GENZEON_LOGO.png", width=100)
    except FileNotFoundError:
        st.warning("Logo not found")

with col_title:
    st.markdown("""
        ### 📄 Genzeon PDF Field Extractor
        ##### Intelligent Document Analysis & Data Extraction
    """)

st.markdown("---")

client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
st.subheader("🔧 Configuration", divider="blue")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📄 Upload Document")
    uploaded_file = st.file_uploader("Select PDF file", type=["pdf"], label_visibility="collapsed")

with col2:
    st.markdown("#### 📂 Select Type")
    selected_case_type = st.selectbox("Choose case type", list(FIELD_MAPPINGS.keys()), label_visibility="collapsed")

if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("📤 Uploading and analyzing document..."):
        try:
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

            st.success("Document uploaded successfully!", icon="✅")
        except Exception as e:
            st.error(f"❌ Error uploading document: {e}")
            st.stop()


# ------------------ HELPER FUNCTIONS ------------------
def parse_json_response(response_text):
    """
    Extract JSON from API response and parse it into a clean dictionary.
    Handles cases where JSON might be embedded in markdown code blocks.
    """
    try:
        # Try to find JSON in markdown code blocks first
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
        
        # Try parsing directly
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If parsing fails, return None (will be handled as error)
        return None


def generate_extraction_prompt(doc_name, fields_dict):
    """Generate a prompt for field extraction."""
    lines = [
        f'You are an expert assistant specializing in document analysis.',
        f'Extract the following fields from the "{doc_name}" section of the document.\n',
        f'Return ONLY a valid JSON object with the field names as keys and extracted values as values.',
        f'If a field is not found, use null for that field.\n',
        f'Fields to extract:\n'
    ]
    
    for i, (field_name, keywords) in enumerate(fields_dict.items(), 1):
        lines.append(f"{i}. {field_name}: {', '.join(keywords)}")
    
    lines.append(f"\nReturn the response in this exact JSON format:")
    lines.append("{")
    for field_name in fields_dict:
        lines.append(f'  "{field_name}": "<value or null>",')
    # Remove trailing comma from last item
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    
    return "\n".join(lines)


def extract_doc_categories(signed_url):
    """Extract document categories and page numbers."""
    prompt = "Analyze the document structure. Provide a list of all document sections/categories along with their approximate page numbers in a clear format."
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


def extract_fields(doc_name, fields_dict, signed_url):
    """
    Extract fields from a document section and return parsed data.
    """
    prompt = generate_extraction_prompt(doc_name, fields_dict)
    
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
        response_text = response.choices[0].message.content
        
        # Parse JSON from response
        parsed_data = parse_json_response(response_text)
        
        if parsed_data is None:
            return None, f"Failed to parse response: {response_text}"
        
        return parsed_data, None
    except Exception as e:
        return None, str(e)


def sanitize_sheet_name(sheet_name):
    """
    Remove invalid Excel sheet name characters: []:<>*?/\
    Also limit to 31 characters (Excel limit).
    """
    invalid_chars = r'[\[\]:*?/\\<>]'
    sanitized = re.sub(invalid_chars, '', sheet_name)
    return sanitized[:31]


def create_excel_with_separate_sheets(extraction_results, category_info):
    """
    Create an Excel file with separate sheets for each document.
    Each sheet contains Field | Value pairs.
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Define formatting
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'valign': 'top',
            'text_wrap': True
        })
        
        null_format = workbook.add_format({
            'border': 1,
            'italic': True,
            'bg_color': '#F2F2F2',
            'valign': 'top',
            'text_wrap': True
        })
        
        # Sheet 1: Document Categories
        try:
            category_lines = [line for line in category_info.strip().split("\n") if line.strip()]
            category_df = pd.DataFrame({"Document Structure": category_lines})
        except Exception as e:
            category_df = pd.DataFrame({"Raw Output": [category_info]})
        
        category_df.to_excel(writer, sheet_name="Document Structure", index=False)
        worksheet = writer.sheets["Document Structure"]
        worksheet.set_column('A:A', 80)
        
        # Sheet 2+: Each extracted document
        for doc_name, extracted_data in extraction_results:
            if extracted_data is None:
                # Error case
                error_df = pd.DataFrame({"Status": ["Error during extraction"]})
                safe_sheet_name = sanitize_sheet_name(doc_name)
                error_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            else:
                # Convert extracted data to Field | Value DataFrame
                rows = []
                for field_name, field_value in extracted_data.items():
                    rows.append({
                        "Field": field_name,
                        "Value": field_value if field_value is not None else "N/A"
                    })
                
                df = pd.DataFrame(rows)
                
                # Write to sheet
                safe_sheet_name = sanitize_sheet_name(doc_name)
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False, startrow=0)
                
                # Format the sheet
                worksheet = writer.sheets[safe_sheet_name]
                worksheet.set_column('A:A', 35)  # Field column
                worksheet.set_column('B:B', 60)  # Value column
                
                # Write headers with formatting
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Write data with formatting
                for row_num, row_data in enumerate(df.values, 1):
                    for col_num, (col_name, cell_value) in enumerate(zip(df.columns, row_data)):
                        if cell_value == "N/A":
                            worksheet.write(row_num, col_num, cell_value, null_format)
                        else:
                            worksheet.write(row_num, col_num, cell_value, cell_format)
    
    output.seek(0)
    return output


# ------------------ MAIN PROCESSING ------------------
if st.session_state.get("file_uploaded"):
    st.subheader("⚙️ Extraction Controls", divider="blue")
    
    col_extract, col_reset = st.columns([3, 1])
    
    with col_extract:
        extract_button = st.button("🚀 Extract Fields from All Documents", use_container_width=True, type="primary")
    
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    if extract_button:
        extraction_results = []
        start_time = time.time()
        
        # Step 1: Extract document categories
        st.subheader("📊 Analysis Progress", divider="blue")
        
        category_placeholder = st.container()
        with category_placeholder:
            st.info("📊 Analyzing document structure...")
            with st.spinner("🔍 Identifying document sections..."):
                category_info = extract_doc_categories(st.session_state.signed_url)
            
            with st.expander("📋 Document Structure Details", expanded=True):
                st.text(category_info)
        
        # Step 2: Extract fields for each document
        st.subheader("🧠 Field Extraction", divider="blue")
        
        progress_bar = st.progress(0, text="Starting extraction...")
        status_container = st.container()
        
        document_mapping = FIELD_MAPPINGS[selected_case_type]
        total_docs = len(document_mapping)
        
        for idx, (doc_name, fields) in enumerate(document_mapping.items()):
            progress_text = f"Processing {idx + 1}/{total_docs}: {doc_name}"
            progress_bar.progress((idx + 1) / total_docs, text=progress_text)
            
            with st.spinner(f"⏳ Processing {doc_name}..."):
                parsed_data, error = extract_fields(doc_name, fields, st.session_state.signed_url)
                extraction_results.append((doc_name, parsed_data))
                
                if error:
                    st.warning(f"⚠️ {doc_name}: {error}")
            
            time.sleep(2)  # Rate limiting
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Step 3: Success message and Excel generation
        st.subheader("📥 Results & Download", divider="green")
        
        col_success, col_time = st.columns([2, 1])
        
        with col_success:
            st.success(f"✅ Extraction complete!", icon="✅")
        
        with col_time:
            st.info(f"⏱️ Time: {elapsed_time:.2f}s")
        
        with st.spinner("📝 Generating Excel file..."):
            excel_file = create_excel_with_separate_sheets(extraction_results, category_info)
        
        st.download_button(
            label="⬇️ Download Results as Excel",
            data=excel_file,
            file_name="Progeny_Extracted_Fields.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # Display summary
        st.subheader("📋 Extraction Summary", divider="blue")
        
        summary_data = {
            "📄 Document": [doc_name for doc_name, _ in extraction_results],
            "✓ Status": ["✅ Success" if data is not None else "❌ Error" for _, data in extraction_results]
        }
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Additional stats
        successful = sum(1 for _, data in extraction_results if data is not None)
        failed = len(extraction_results) - successful
        
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            st.metric("Total Documents", len(extraction_results))
        
        with col_s2:
            st.metric("Successful", successful, delta="✅")
        
        with col_s3:
            st.metric("Failed", failed, delta="❌" if failed > 0 else "✅")
