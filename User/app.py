import streamlit as st
import boto3
import os
from fpdf import FPDF
from io import BytesIO
import re

# ---------- AWS Configuration ----------
aws_region = "us-east-1"
bucket_name = os.getenv("BUCKET_NAME")
knowledge_base_id = "NRQ5XMNDMI"
model_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=aws_region)

# ---------- Enhanced PDF converter ----------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, self.title, align="C", ln=1)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def convert_text_to_pdf(subject, text):
    pdf = PDF()
    pdf.set_title(subject)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        clean = line.replace("•", "-").replace("–", "-").replace("“", "\"").replace("”", "\"").replace("’", "'")
        pdf.multi_cell(0, 10, clean)
    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)
    return pdf_output

# ---------- Fix formatting ----------
def fix_section_formatting(exam_text):
    return re.sub(r'\s*(Part [ABC] \(\d+ marks.*?\))', r'\n\n\1\n', exam_text).strip()

# ---------- Extract units ----------
def extract_units_from_knowledge_base(subject):
    input_query = {
       "text": f"""
You are an academic assistant trained to extract information **exactly as written** from textbooks, scans, or PDFs.

Your task is to extract and return the full list of **chapter or unit titles in the exact order, wording, and formatting** as shown in **{subject}**.

Focus only on sections labeled:
- **Contents**
- **Table of Contents**
- **Brief Contents**
- **Extended Chapter Material**
- Or any clearly numbered list of chapters/units

Ignore sections like:
- Preface
- Appendices
- Lab manuals
- Interview questions
- Index (unless it lists chapters)

Extraction Rules:
- Return the chapter or unit titles **in the exact order, wording, and formatting** as shown in **{subject}**
- **Do NOT** rewrite, summarize, interpret, or change the chapter names
- **Do NOT** add topics that are not explicitly listed
- **Do NOT** merge or split titles
- **Do NOT** skip any chapters — return all, even if there are more than 16

Output format:
1. [Exact title from source]  
2. [Exact title from source]  
...  
N. [Exact title from source]

Final output:
**Only return the list of chapters or units, exactly as shown in the textbook {subject}, without any changes, additions, or explanations.**
"""
    }

    query = {
        "input": input_query,
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": model_arn
            }
        }
    }

    try:
        response = bedrock_agent_runtime.retrieve_and_generate(**query)
        full_text = response.get('output', {}).get('text', "")
        raw_units = re.findall(r"\d+\.\s+.+", full_text)
        return [unit.strip() for unit in raw_units if unit.strip()]
    except Exception as e:
        st.error(f"❌ Error extracting units: {str(e)}")
        return []

# ---------- Generate Questions ----------
def generate_exam_questions(subject, selected_units, part_a_count, part_b_count, part_c_count):
    input_query = {
        "text": f'''
Based on the syllabus/study material for "{subject}", generate a university exam following the Anna University format.

Instructions:
- Strictly include:
  • Part A: {part_a_count} questions (2 marks each)
  • Part B: {part_b_count} questions (6 marks each)
  • Part C: {part_c_count} questions (10 marks each)
- Spread questions across all the selected units and Bloom's Taxonomy levels.
- Do NOT include answers.
- Use LaTeX formatting only where absolutely necessary (e.g., equations, symbols, protocols).
- Each section must start on a new line with the header format:
  Part A (2 marks each)
  Part B (6 marks each)
  Part C (10 marks each)

Use ONLY the following selected chapters/units:
{', '.join(selected_units)}

Return ONLY the formatted exam content as plain text. Do not include explanations, code, markdown, or JSON.
'''
    }

    query = {
        "input": input_query,
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": model_arn
            }
        }
    }

    try:
        response = bedrock_agent_runtime.retrieve_and_generate(**query)
        return response.get('output', {}).get('text', "").strip()
    except Exception as e:
        st.error(f"❌ Error generating questions: {str(e)}")
        return ""

# ---------- Streamlit UI ----------
def main():
    st.set_page_config(page_title="🎓 Question Paper Generator", layout="centered")

    st.markdown("""
        <style>
        .centered-title {
            font-size: 36px !important;
            text-align: center;
            margin-bottom: 30px;
            font-weight: bold;
            color: #004085;
        }
        .stButton>button {
            width: 100%;
        }
        .unit-box {
            background-color: #f0f8ff;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 6px;
            font-weight: 500;
        }
        .footer {
            text-align:center;
            margin-top: 50px;
            font-size: 13px;
            color: #999;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="centered-title">📘 AI-Driven University Question Paper Generator</div>', unsafe_allow_html=True)

    if "units" not in st.session_state:
        st.session_state.units = []
    if "units_fetched" not in st.session_state:
        st.session_state.units_fetched = False

    subject = st.text_input("📚 Enter Subject Name")

    if subject and not st.session_state.units_fetched:
        if st.button("🔍 Extract Chapters/Units"):
            with st.spinner("Fetching chapters from knowledge base..."):
                units = extract_units_from_knowledge_base(subject)
                if units:
                    st.session_state.units = units
                    st.session_state.units_fetched = True
                    st.success("✅ Units extracted successfully!")
                else:
                    st.warning("⚠️ No units found.")

    if st.session_state.units:
        st.markdown("### 📦 Select Chapters/Units")
        selected_units = []

        for i, unit in enumerate(st.session_state.units):
            col1, col2 = st.columns([6, 1])
            col1.markdown(f'<div class="unit-box">{unit}</div>', unsafe_allow_html=True)
            if col2.checkbox("Select", key=f"unit_{i}", label_visibility="collapsed"):
                selected_units.append(unit)

        if selected_units:
            st.markdown("### ✍️ Define Question Structure")
            with st.form("question_form"):
                col1, col2, col3 = st.columns(3)
                part_a = col1.number_input("Part A (2 marks)", 1, 20, 10)
                part_b = col2.number_input("Part B (6 marks)", 1, 20, 5)
                part_c = col3.number_input("Part C (10 marks)", 0, 10, 2)
                generate = st.form_submit_button("🚀 Generate Question Paper")

            if generate:
                with st.spinner("Generating paper..."):
                    paper = generate_exam_questions(subject, selected_units, part_a, part_b, part_c)
                    paper = fix_section_formatting(paper)

                if paper:
                    st.success("✅ Paper generated successfully!")
                    st.markdown("### 📝 Preview")
                    st.text_area("Generated Exam", paper, height=500)

                    pdf = convert_text_to_pdf(subject, paper)
                    st.download_button(
                        label="📥 Download as PDF",
                        data=pdf,
                        file_name=f"{subject.replace(' ', '_')}_Exam.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("👉 Please select at least one chapter/unit to proceed.")

    st.markdown('<div class="footer">© 2025 ExamGenAI • Powered by AWS Bedrock</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
