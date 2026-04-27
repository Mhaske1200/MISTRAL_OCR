import streamlit as st
from mistralai import Mistral
import pandas as pd
import time

# ------------------ CONFIG ------------------
API_KEY = "uPfVIl67PTwvqiEFLFFfDjjbXQsCqjLB"  # Replace with your actual API key

FIELDS = {
    "1": {"field_name": "provider_name", "query": "What is the name of provider"},
    "2": {"field_name": "effective_date", "query": "What is effective date"},
    "3": {"field_name": "termination_date", "query": "What is termination date"},
    "4": {"field_name": "fee_schedule_name", "query": "What is the name of fee schedule"},
    "5": {"field_name": "inpatient_services", "query": "Inpatient Services in Compensation Schedule"},
    "6": {"field_name": "outpatient_services", "query": "Outpatient Services in Compensation Schedule"},
    "7": {"field_name": "payor_name", "query": "What is the name of payor"},
    "8": {"field_name": "provider_location", "query": "What is the location of provider"},
    "9": {"field_name": "initial_contract_term", "query": "What is the initial contract term"},
    "10": {"field_name": "facilities", "query": "What are hospital/provider listings"}
}

# ------------------ PROMPTS ------------------

general_prompt_template = '''
You are an AI assistant specialized in extracting structured information from text. Using the document provided, answer the query by extracting the relevant field and its value. Ensure the response is in JSON format, containing only the requested field and its value.

### Query:
{query}

### Rules:
1. Extract the field name and its value accurately from the document.
2. If the field is not explicitly mentioned, respond with: 
{{
    "{field_name}": "Field not found"
}}
3. Ensure the output is a valid JSON object containing the field name as the key and its corresponding value as the value.
'''

inpatient_services_prompt_template = f"""
You are an expert in extracting structured data from documents. Below is a context from a legal document 
that describes rules and payment methods for various categories of services. Your task is to extract the 
"Inpatient Services" category and its associated rules in the specified JSON format.

### JSON Format:
{{
    "category": "Inpatient Services",
    "schedule_name": "<Table Heading>",
    "rules": [
        {{
            "rule_type": "<'rule' or 'default'>",
            "rule_name": "<Exact name of the rule>",
            "pay_method": "<Payment method>",
            "pay_value": "<Payment value>",
            "pay_source": "Charge",
            "circuit_breaker": false,
            "multiple_procedure_percent": [],
            "code": [
                {{
                    "primary": "<Type of Code>",
                    "primary_code": "<Number Range Colon Separated>"
                }}
            ]
        }}
    ]
}}

### Example:
If the context contains the following information:
"Inpatient Services include Medical procedures paid at $800 per diem, Surgical procedures paid at $1150 per diem, and all other inpatient services paid at 80% of eligible charges."

The expected JSON output should be:
{{
    "category": "Inpatient Services",
    "schedule_name": "",
    "rules": [
        {{
            "rule_type": "rule",
            "rule_name": "Medical",
            "pay_method": "Per Diem",
            "pay_value": "$800",
            "pay_source": "Charge",
            "circuit_breaker": false,
            "multiple_procedure_percent": [
                {{
                    "key": "Primary",
                    "value": "100%"
                }},
                {{
                    "key": "Secondary",
                    "value": "50%"
                }},
                {{
                    "key": "Subsequent",
                    "value": "25%"
                }}
            ],
            "code": [
                {{
                    "primary": "Rev Code",
                    "primary_code": "100-101:110-111:113:117:120-121:123:127:130-131:133:137:139-141:143:147:149-151:153:157:159-160:164:169"
                }}
            ]
        }},
        {{
            "rule_type": "rule",
            "rule_name": "Surgical",
            "pay_method": "Per Diem",
            "pay_value": "$1150",
            "pay_source": "Charge",
            "circuit_breaker": false,
            "multiple_procedure_percent": [],
            "code": [
                {{
                    "primary": "",
                    "primary_code": ""
                }}
            ]
        }},
        {{
            "rule_type": "default",
            "rule_name": "All Other Inpatient Services",
            "pay_method": "Percent of Eligible Charge",
            "pay_value": "80%",
            "pay_source": "Charge",
            "circuit_breaker": false,
            "multiple_procedure_percent": [],
            "code": [
                {{
                    "primary": "",
                    "primary_code": ""
                }}
            ]
        }}
    ]
}}

### Additional Instructions:
- **STRICTLY** use only the provided document for extraction. **Do not use elements from the example.**
- Use the provided Example and JSON Format only as a reference to understand the expected structure and formatting.
- Do not copy any specific values from the Example or predefined JSON Format.
- Focus only on extracting data for the "Inpatient Services" category.
- Use "rule" for specific, named procedures and "default" for fallback rules or generic descriptions.
- Preserve the exact wording for `rule_name`, `pay_method`, and `pay_value` as it appears in the context.
- Replace "pay_source" with "Charge" for all rules.
- If `pay_method` is "Case Rate", set `circuit_breaker` to `true` else `false`.
- Ensure the JSON is valid and includes all rules associated with "Inpatient Services".
- The output must strictly match the specified JSON format and maintain consistency.

Provide the extracted JSON for the "Inpatient Services" category below:
"""

outpatient_services_prompt_template = f"""
You are an expert in extracting structured data from documents. Below is a context from a legal document 
that describes rules and payment methods for various categories of services. Your task is to extract the 
"Outpatient Services" category and its associated rules in the specified JSON format.

### JSON Format:
{{
    "category": "Outpatient Services",
    "schedule_name": "<Table Heading>",
    "rules": [
        {{
            "rule_type": "<'rule' or 'default'>",
            "rule_name": "<Exact name of the rule>",
            "pay_method": "<Payment method>",
            "pay_value": "<Payment value>",
            "pay_source": "Fee Schedule",
            "circuit_breaker": true,
            "multiple_procedure_percent": [
                {{
                    "key": "Primary",
                    "value": "100%"
                }},
                {{
                    "key": "Secondary",
                    "value": "50%"
                }},
                {{
                    "key": "Subsequent",
                    "value": "25%"
                }}
            ],
            "code": [
                {{
                    "primary": "<Type of Code>",
                    "primary_code": "<Number Range Colon Separated>"
                }}
            ]
        }}
    ]
}}

### Example:
If the context contains the following information:
"Outpatient Services include Cardiac Cath Lab procedures paid at a Case Rate of 120% and all other outpatient services paid at 80% of eligible charges."

The expected JSON output should be:
{{
    "category": "Outpatient Services",
    "schedule_name": "Base Compensation Schedule Year : 2013",
    "rules": [
        {{
            "rule_type": "rule",
            "rule_name": "Cardiac Cath Lab procedures",
            "pay_method": "Case Rate",
            "pay_value": "120%",
            "pay_source": "Fee Schedule",
            "circuit_breaker": true,
            "multiple_procedure_percent": [
                {{
                    "key": "Primary",
                    "value": "100%"
                }},
                {{
                    "key": "Secondary",
                    "value": "50%"
                }},
                {{
                    "key": "Subsequent",
                    "value": "25%"
                }}
            ],
            "code": [
                {{
                    "primary": "Rev Code",
                    "primary_code": "100-101:110-111:113:117:120-121:123:127:130-131:133:137:139-141:143:147:149-151:153:157:159-160:164:169"
                }}
            ]
        }},
        {{
            "rule_type": "rule",
            "rule_name": "Radiation Therapy",
            "pay_method": "Per Unit",
            "pay_value": "214%",
            "pay_source": "Fee Schedule",
            "circuit_breaker": true,
            "multiple_procedure_percent": [],
            "code": [
                {{
                    "primary": "",
                    "primary_code": ""
                }}
            ]
        }},
        {{
            "rule_type": "default",
            "rule_name": "All Other Outpatient Services",
            "pay_method": "Percent of Eligible Charge",
            "pay_value": "80%",
            "pay_source": "Fee Schedule",
            "circuit_breaker": true,
            "multiple_procedure_percent": [],
            "code": [
                {{
                    "primary": "",
                    "primary_code": ""
                }}
            ]
        }}
    ]
}}

### Additional Instructions:
- **STRICTLY** use only the provided document for extraction. **Do not use elements from the example.**
- Use the provided Example and JSON Format only as a reference to understand the expected structure and formatting.
- Do not copy any specific values from the Example or predefined JSON Format.
- Focus only on extracting data for the "Outpatient Services" category.
- Use "rule" for specific, named procedures and "default" for fallback rules or generic descriptions.
- Preserve the exact wording for `rule_name`, `pay_method`, and `pay_value` as it appears in the context.
- Replace "pay_source" with "Fee Schedule" for all rules.
- If `pay_method` is "Case Rate", set `circuit_breaker` to `true` else `false`.
- Ensure the JSON is valid and includes all rules associated with "Outpatient Services".
- The output must strictly match the specified JSON format and maintain consistency.

Provide the extracted JSON for the "Outpatient Services" category below:
"""


def get_system_prompt(field_name, query):
    if field_name == "inpatient_services":
        return inpatient_services_prompt_template
    elif field_name == "outpatient_services":
        return outpatient_services_prompt_template
    else:
        return general_prompt_template.replace("{query}", query).replace("{field_name}", field_name)

# ------------------ STREAMLIT SETUP ------------------

st.set_page_config(page_title="Mistral Auto Q&A", layout="wide")
st.title("📄 Structured Field Extraction from PDF using Mistral")
st.write("Upload a PDF contract and extract key data points using predefined queries and prompts.")

client = Mistral(api_key=API_KEY)
uploaded_file = st.file_uploader("📤 Upload PDF file", type=["pdf"])

if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("📤 Uploading and analyzing document..."):
        uploaded_pdf = client.files.upload(
            file={"file_name": uploaded_file.name, "content": uploaded_file.read()},
            purpose="ocr"
        )
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
        st.session_state.file_uploaded = True
        st.session_state.file_id = uploaded_pdf.id
        st.session_state.signed_url = signed_url.url
    st.success("✅ Document uploaded successfully!")

if st.session_state.get("file_uploaded"):
    if st.button("🔍 Extract Fields"):
        results = []
        with st.spinner("🧠 Extracting data for all fields..."):
            for fid, field in FIELDS.items():
                try:
                    query = field["query"]
                    field_name = field["field_name"]
                    system_prompt = get_system_prompt(field_name, query)

                    messages = [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
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

                    results.append({
                        "Field": field_name,
                        "Answer": response.choices[0].message.content.strip()
                    })

                    time.sleep(5)

                except Exception as e:
                    results.append({
                        "Field": field["field_name"],
                        "Answer": f"Error: {e}"
                    })

        df = pd.DataFrame(results)
        st.success("✅ Extraction complete!")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name='extracted_fields.csv',
            mime='text/csv'
        )

else:
    st.info("📁 Please upload a document to get started.")
