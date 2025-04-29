import streamlit as st 
import boto3
import os
from fpdf import FPDF
from io import BytesIO
import re

# ---------- AWS Configuration ----------
aws_region = "us-east-1"
bucket_name = os.getenv("BUCKET_NAME")  # Optional if you use S3 for something
knowledge_base_id = "NRQ5XMNDMI"
model_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
model_arn2 = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=aws_region)

# ---------- PDF Generator ----------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, self.title, align="C", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def convert_text_to_pdf(subject, text, title="Document"):
    pdf = PDF()
    pdf.set_title(title)
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

# ---------- Formatting Helper ----------
def fix_section_formatting(exam_text):
    return re.sub(r'\s*(Part [ABC] \(\d+ marks.*?\))', r'\n\n\1\n', exam_text).strip()

# ---------- Unit Extractor ----------
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

Ignore sections like:
- Preface
- Appendices
- Lab manuals
- Interview questions
- Index

Rules:
- Return the titles **exactly as shown** — no changes.
- No summarization or interpretation.
- List ALL chapters/units even if there are more than 16.

Output format:
1. [Exact title]  
2. [Exact title]  
... 

Only return the list — no explanations.
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

# ---------- Question Generator ----------
def generate_exam_questions(subject, selected_units, part_a_count, part_b_count, part_c_count, bloom_distribution_text):
    input_query = {
        "text": f'''
Based on the syllabus/study material for "{subject}", generate a university exam paper following Anna University format.

Instructions:
- Strictly include:
  • Part A: {part_a_count} questions (2 marks each)
  • Part B: {part_b_count} questions (6 marks each)
  • Part C: {part_c_count} questions (10 marks each)
- Use ONLY the following selected chapters/units:
{', '.join(selected_units)}
- Spread questions according to this Bloom’s Taxonomy complexity distribution:
{bloom_distribution_text}
- Ensure each Bloom's level is distributed exactly as per the percentages provided for each part.
- Distribute Bloom levels properly across all sections (A, B, C).
- DO NOT provide answers.
- Each section must start on a new line with the header format:
  Part A (2 marks each)
  Part B (6 marks each)
  Part C (10 marks each)
- Use LaTeX formatting ONLY if necessary (for formulas/symbols).

Output:
- ONLY the formatted question paper as plain text.
- No extra explanations, markdown, or JSON.
'''
    }

    query = {
        "input": input_query,
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": model_arn2
            }
        }
    }

    try:
        response = bedrock_agent_runtime.retrieve_and_generate(**query)
        return response.get('output', {}).get('text', "").strip()
    except Exception as e:
        st.error(f"❌ Error generating questions: {str(e)}")
        return ""

# ---------- Answer Generator ----------
import streamlit as st

def generate_answers_for_questions(subject, questions_text, knowledge_base_id, model_arn):
    input_query = {
        "text": f'''
    You are an expert academician.

    Using the **uploaded textbook material** for "{subject}", generate a detailed answer key for the following exam questions.

    Instructions:
    - Keep answers clear, precise, and concise.
    - Organize answer sections the same as question sections (Part A, Part B, Part C).
    - Maintain the same question numbering.
    - Use LaTeX formatting where needed (math, equations, etc.).

    Follow this format for answers:

    Part A: Short Answer Questions

    [Question 1]
    Answer: [Short answer here]

    [Question 2]
    Answer: [Short answer here]

    etc...

    Part B: Long Answer Questions

    [Question 6]
    Answer: [Answer here]

    [Question 7]
    Answer: [Answer here]

    etc...

    Part C: Application-Based Questions

    [Question 10]
    Answer: [Answer here]

    etc...

    Questions:
    {questions_text}

    Output:
    - ONLY answers clearly organized by parts and numbering.
    - Every answer must start with a new line.
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
        # Call to Bedrock to retrieve and generate the answers
        response = bedrock_agent_runtime.retrieve_and_generate(**query)
        
        # Extract and return the generated output text
        return response.get('output', {}).get('text', "").strip()
    except Exception as e:
        # Error handling if the API call fails
        st.error(f"❌ Error generating answers: {str(e)}")
        return ""  # Return an empty string or handle it as needed

# ---------- Streamlit Frontend ----------
def main():
    st.set_page_config(page_title="🎓 Question Paper Generator + Answer Key", layout="wide")

    st.markdown(""" 
        <style>
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
            margin-top: 30px;
            font-size: 13px;
            color: #999;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📘 AI-Driven University Question Paper & Answer Key Generator")

    if "units" not in st.session_state:
        st.session_state.units = []
    if "units_fetched" not in st.session_state:
        st.session_state.units_fetched = False
    if "paper" not in st.session_state:
        st.session_state.paper = ""
    if "answers" not in st.session_state:
        st.session_state.answers = ""

    left_col, right_col = st.columns([1.2, 1.8])

    with left_col:
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

    with right_col:
        if "units" in st.session_state and st.session_state.units:
            st.markdown("### ✍️ Define Question Structure")

            with st.form("question_form"):
                col1, col2, col3 = st.columns(3)
                part_a = col1.number_input("Part A (2 marks)", 1, 20, 10)
                part_b = col2.number_input("Part B (6 marks)", 1, 20, 5)
                part_c = col3.number_input("Part C (10 marks)", 0, 10, 2)

                st.markdown("### 🧠 Bloom’s Taxonomy Distribution (%)")
                bloom_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
                bloom_distribution = {}
                total_percentage = 0

                for level in bloom_levels:
                    bloom_distribution[level] = st.number_input(f"{level} (%)", min_value=0, max_value=100, value=0)
                    total_percentage += bloom_distribution[level]

                generate = st.form_submit_button("🚀 Generate Question Paper")

            if generate:
                if not selected_units:
                    st.error("❌ Please select at least one unit from the left panel.")
                elif total_percentage != 100:
                    st.error("❌ Bloom's Taxonomy percentages must sum to 100%.")
                else:
                    bloom_distribution_text = "\n".join([f"{level}: {percentage}%" for level, percentage in bloom_distribution.items()])
                    with st.spinner("Generating question paper..."):
                        questions = generate_exam_questions(subject, selected_units, part_a, part_b, part_c, bloom_distribution_text)
                        if questions:
                            st.session_state.paper = questions

            if st.session_state.paper:
                st.markdown("### 📑 Generated Question Paper")
                st.text_area("Question Paper", st.session_state.paper, height=400, max_chars=3000)

                download_button = st.button("💾 Download Question Paper")
                if download_button:
                    st.download_button(
                        label="Download Question Paper as PDF",
                        data=convert_text_to_pdf(subject, st.session_state.paper),
                        file_name=f"{subject}_Question_Paper.pdf",
                        mime="application/pdf"
                    )

            if st.session_state.paper:
                st.markdown("### 🧑‍🏫 Generate Answer Key")

                generate_answer = st.button("🚀 Generate Answer Key")
                if generate_answer:
                    with st.spinner("Generating answers..."):
                        answers = generate_answers_for_questions(subject, st.session_state.paper)
                        st.session_state.answers = answers

                if st.session_state.answers:
                    st.markdown("### 📝 Generated Answer Key")
                    st.text_area("Answer Key", st.session_state.answers, height=400)

                    st.download_button(
                        label="Download Answer Key as PDF",
                        data=convert_text_to_pdf(subject, st.session_state.answers),
                        file_name=f"{subject}_Answer_Key.pdf",
                        mime="application/pdf"
                    )

    st.markdown("### 💡 Notes: Please make sure you have valid AWS credentials.")
    st.markdown('<p class="footer">Built with ❤️ by Your Dev Team</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
