import streamlit as st
from mistralai import Mistral
from detoxify import Detoxify
import re
import pandas as pd
import matplotlib.pyplot as plt
import tiktoken
from io import StringIO



# ------------------ CONFIG ------------------
API_KEY = "rCNHWqxVouTaUudluW7B1qx45kfNi5zS"
st.set_page_config(page_title="AI Guardrails Q&A", layout="wide")
st.title("🛡️ AI Guardrails Q&A with RAGAS + Cost Guardrails")

# ------------------ INIT MISTRAL ------------------
client = Mistral(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📤 Upload PDF document", type=["pdf"])
if uploaded_file and "file_uploaded" not in st.session_state:
    with st.spinner("📤 Uploading to Mistral for OCR..."):
        uploaded_pdf = client.files.upload(
            file={"file_name": uploaded_file.name, "content": uploaded_file.read()},
            purpose="ocr"
        )
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
        st.session_state.file_uploaded = True
        st.session_state.signed_url = signed_url.url
    st.success("✅ File uploaded and processed!")

# ------------------ GUARDRAIL FUNCTIONS ------------------

def gr_s_001_output_moderation(text):
    try:
        scores = Detoxify('original').predict(text)
        high_risk_labels = ["toxicity", "insult", "hate", "threat", "identity_attack", "severe_toxicity"]
        high_risk = any(scores.get(label, 0) > 0.4 for label in high_risk_labels)
        moderate_risk = any(0.2 < scores.get(label, 0) <= 0.4 for label in high_risk_labels)
        if high_risk:
            reasons = [f"{label}: {round(scores[label], 2)}" for label in high_risk_labels if scores[label] > 0.4]
            return 40, "fail", f"Severe toxicity - {', '.join(reasons)}"
        elif moderate_risk:
            reasons = [f"{label}: {round(scores[label], 2)}" for label in high_risk_labels if 0.2 < scores[label] <= 0.4]
            return 70, "warn", f"Moderate toxicity - {', '.join(reasons)}"
        return 100, "pass", "No toxic content detected"
    except Exception as e:
        return 60, "warn", f"Toxicity check failed: {e}"

def gr_q_001_hallucination_detection(text):
    hallucination_signals = ["i don't know", "as an ai", "i cannot", "no information available", "i am unable", "based on my training"]
    grounding_signals = ["according to", "source:", "as per", "the document states", "from the text"]
    if any(phrase in text.lower() for phrase in hallucination_signals):
        return 50, "fail", "Likely hallucinated response"
    elif not any(signal in text.lower() for signal in grounding_signals):
        return 70, "warn", "No strong grounding signal"
    return 100, "pass", "Grounded in source"

def gr_s_005_pii_redaction(text):
    patterns = {
        "Email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "Phone": r"\b(?:\+?\d{1,3})?[-.\s]??(?:\(?\d{3}\)?)[-.\s]??\d{3}[-.\s]??\d{4}\b",
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "Credit Card": r"\b(?:\d[ -]*?){13,16}\b",
    }
    detected = [label for label, pattern in patterns.items() if re.search(pattern, text)]
    return (40, "fail", f"PII found: {', '.join(set(detected))}") if detected else (100, "pass", "No PII detected")

def gr_s_006_prompt_injection_detection(text):
    injection_keywords = ["ignore previous", "disregard instructions", "pretend to", "you are now", "begin roleplay", "act as"]
    return (50, "fail", "Detected possible injection pattern") if any(k in text.lower() for k in injection_keywords) else (100, "pass", "No suspicious patterns")

def gr_q_005_factual_consistency(text):
    strong_grounding = any(phrase in text.lower() for phrase in ["according to", "from the document", "as stated in", "based on the text"])
    hallucination_clues = ["not mentioned", "cannot determine", "not in the text"]
    if any(clue in text.lower() for clue in hallucination_clues):
        return 50, "fail", "Low consistency - likely ungrounded"
    elif not strong_grounding:
        return 70, "warn", "No grounding evidence in phrasing"
    return 100, "pass", "Answer consistent with source"

def gr_c_002_token_budget(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(text))
    if token_count > 500:
        return 50, "fail", f"Too many tokens: {token_count}"
    elif token_count > 350:
        return 75, "warn", f"Token count approaching limit: {token_count}"
    return 100, "pass", f"Token usage acceptable: {token_count}"

def gr_c_009_response_length(text):
    char_len = len(text)
    redundancy_ratio = len(set(text.split())) / len(text.split()) if text.split() else 1
    if char_len > 2000:
        return 40, "fail", f"Response too long: {char_len} characters"
    elif char_len > 1500 or redundancy_ratio < 0.5:
        return 70, "warn", f"Possible verbosity or repetition"
    return 100, "pass", "Length and clarity OK"

def gr_s_002_bias_detection(text):
    if any(word in text.lower() for word in ["always", "never", "everyone", "no one", "clearly"]):
        return 70, "warn", "Potential bias in generalizing language"
    return 100, "pass", "No obvious biased phrasing"

def gr_s_004_data_leakage_detection(text):
    leakage_keywords = ["training data", "sample document", "demo content"]
    return (50, "fail", "Potential reference to training data") if any(k in text.lower() for k in leakage_keywords) else (100, "pass", "No leakage detected")

def gr_c_001_prompt_length(text):
    words = len(text.split())
    if words > 300:
        return 60, "warn", f"Prompt long: {words} words"
    return 100, "pass", f"Prompt length OK: {words} words"

def gr_q_004_controllability(text):
    if any(term in text.lower() for term in ["neutral", "formal", "concise"]):
        return 100, "pass", "Appears to respect tone/intention"
    return 70, "warn", "Missing explicit controllability cues"


def gr_q_006_readability_check(text):
    """Use basic Flesch–Kincaid score to estimate readability"""
    try:
        from textstat import flesch_reading_ease
        score = flesch_reading_ease(text)
        if score < 30:
            return 60, "warn", f"Very hard to read: Score {score}"
        elif score < 60:
            return 80, "warn", f"Fairly difficult: Score {score}"
        return 100, "pass", f"Readable: Score {score}"
    except Exception as e:
        return 70, "warn", f"Readability tool error: {e}"


# ------------------ GUARDRAIL REGISTRY ------------------
guardrails = [
    {"id": "GR-S-001", "name": "Output Moderation", "area": "Security", "func": gr_s_001_output_moderation},
    {"id": "GR-Q-001", "name": "Hallucination Detection", "area": "Quality", "func": gr_q_001_hallucination_detection},
    {"id": "GR-S-005", "name": "PII Redaction", "area": "Security", "func": gr_s_005_pii_redaction},
    {"id": "GR-S-006", "name": "Prompt Injection Detection", "area": "Security", "func": gr_s_006_prompt_injection_detection},
    {"id": "GR-Q-005", "name": "Factual Consistency", "area": "Quality", "func": gr_q_005_factual_consistency},
    {"id": "GR-C-002", "name": "Token Budget", "area": "Cost", "func": gr_c_002_token_budget},
    {"id": "GR-C-009", "name": "Response Length", "area": "Cost", "func": gr_c_009_response_length},
    {"id": "GR-S-002", "name": "Bias Detection", "area": "Quality", "func": gr_s_002_bias_detection},
    {"id": "GR-S-004", "name": "Data Leakage", "area": "Security", "func": gr_s_004_data_leakage_detection},
    {"id": "GR-C-001", "name": "Prompt Length", "area": "Cost", "func": gr_c_001_prompt_length},
    {"id": "GR-Q-004", "name": "Controllability", "area": "Quality", "func": gr_q_004_controllability},
    {"id": "GR-Q-006", "name": "Readability Check", "area": "Quality", "func": gr_q_006_readability_check},
]

def evaluate_guardrails(text):
    results = []
    for gr in guardrails:
        score, status, comment = gr["func"](text)
        results.append({
            "Guardrail ID": gr["id"],
            "Name": gr["name"],
            "Area": gr["area"],
            "Score": score,
            "StatusRaw": status,
            "Comment": comment
        })
    df = pd.DataFrame(results)
    final_score = int(df["Score"].mean())
    return df, final_score

# ------------------ ASK QUESTION ------------------
if st.session_state.get("file_uploaded"):
    user_question = st.text_input("💬 Ask a question about the document")

    if user_question:
        with st.spinner("🤖 Generating response..."):
            try:
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_question},
                        {"type": "document_url", "document_url": st.session_state.signed_url}
                    ]
                }]
                response = client.chat.complete(model="mistral-small-latest", messages=messages)
                response_text = response.choices[0].message.content

                st.success("✅ Response:")
                st.text_area("AI Response", response_text, height=300)
                st.download_button("📄 Download Response", response_text, file_name="ai_response.txt")

                df_guardrails, final_score = evaluate_guardrails(response_text)

                emoji_map = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
                df_guardrails["Status"] = df_guardrails["StatusRaw"].map(lambda x: f"{emoji_map.get(x, '❓')} {x.capitalize()}")

                st.markdown("### 🧪 Guardrails Evaluation Breakdown")
                st.dataframe(df_guardrails.drop(columns="StatusRaw"), use_container_width=True)

                for _, row in df_guardrails.iterrows():
                    with st.expander(f"ℹ️ {row['Name']} ({row['Status']})"):
                        st.write(row["Comment"])

                st.markdown(f"### 🧮 Final Guardrails Score: `{final_score}/100`")
                if final_score < 70:
                    st.warning("⚠️ Final score is low. Review recommended.")
                elif final_score >= 90:
                    st.success("✅ Excellent safety and quality.")
                else:
                    st.info("ℹ️ Acceptable, but not optimal.")

                # Charts
                st.markdown("### 📊 Visual Summary")

                # Pie Chart
                fig1, ax1 = plt.subplots()
                df_counts = df_guardrails['StatusRaw'].value_counts()
                ax1.pie(df_counts, labels=df_counts.index.str.capitalize(), autopct='%1.1f%%', startangle=90)
                ax1.axis('equal')
                st.pyplot(fig1)

                # Bar Chart
                fig2, ax2 = plt.subplots()
                sorted_df = df_guardrails.sort_values(by="Score", ascending=True)
                colors = ['green' if s == 'pass' else 'orange' if s == 'warn' else 'red' for s in sorted_df['StatusRaw']]
                ax2.barh(sorted_df["Name"], sorted_df["Score"], color=colors)
                ax2.set_title("Guardrail Scores")
                ax2.set_xlabel("Score")
                st.pyplot(fig2)

                # Metrics
                cols = st.columns(3)
                cols[0].metric("✅ Passed", df_counts.get("pass", 0))
                cols[1].metric("⚠️ Warnings", df_counts.get("warn", 0))
                cols[2].metric("❌ Failed", df_counts.get("fail", 0))

                # Download CSV Report
                csv_data = df_guardrails.drop(columns="StatusRaw").to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Guardrail Report", csv_data, "guardrail_report.csv", "text/csv")

            except Exception as e:
                st.error(f"❌ Error: {e}")
else:
    st.info("📁 Please upload a document to get started.")
