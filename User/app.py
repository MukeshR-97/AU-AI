import streamlit as st
import boto3
import os
from fpdf import FPDF
from io import BytesIO
import re

# ---------- AWS Configuration ----------
aws_region = "us-east-1"
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
    try:
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
    except UnicodeEncodeError:
        pdf_bytes = pdf.output(dest='S').encode('utf-8', errors='replace')
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)
    return pdf_output

# ---------- Unit Extractor ----------
def extract_units_from_knowledge_base(subject):
    input_query = {
    "text": f"""
You are an academic assistant. Your task is to extract the **exact chapter or units** from a textbook for the subject "{subject}".

Focus ONLY on extracting chapters or units from the following sections:
- Table of Contents
- Contents
- Brief Contents
- Detailed Contents

Ignore all other parts of the textbook, including:
- Preface
- Acknowledgements
- Appendices
- Lab Manuals
- Interview Questions
- Index
- Summaries or overviews

Extraction rules:
1. Do not modify, paraphrase, or rephrase any chapter titles.
2. Return titles exactly as written — including numbering, punctuation, special characters, and formatting (e.g., capitalization).
3. Include ALL chapters or units, even if there are more than 16.
4. The output must be a **plain numbered list** and contain **no explanations** or commentary.

Output format:
1. [Exact title as written in the source]
2. [Exact title as written in the source]
3. [Exact title as written in the source]
...

Important:
- Do not guess or infer missing titles.
- Do not skip titles unless they fall under the “Ignore” section above.
- Return only the list of chapter titles — no additional headings, descriptions, or formatting.

Begin extraction below:
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
        st.error(f"Error extracting units: {str(e)}")
        return []

# ---------- Question Generator ----------
def generate_exam_questions(subject, selected_units, part_a_count, part_b_count, part_c_count, bloom_distribution_text):
    input_query = {
    "text": f'''
You are an expert academic assistant.

Generate a **university-level question paper** based on the syllabus for the subject: "{subject}".

Follow **Anna University exam format**, strictly adhering to these rules:

---
**INSTRUCTIONS:**
- Use ONLY these selected chapters/units:
{', '.join(selected_units)}

- Follow this structure:
  • Part A: {part_a_count} questions, 2 marks each  
  • Part B: {part_b_count} questions, 6 marks each  
  • Part C: {part_c_count} questions, 10 marks each

- Spread the questions evenly across the selected units.

- Use this Bloom’s Taxonomy distribution:
{bloom_distribution_text}

---
**FORMATTING RULES (STRICT):**

Use **this exact layout** with **clear spacing and numbering**:

Part A (2 marks each)  
1. Question one text  
2. Question two text  
...  

Part B (6 marks each)  
1. Question one text  
2. Question two text  
...

Part C (10 marks each)  
1. Question one text  
...

Important:
- Each section must begin **exactly** with the header: `Part A (2 marks each)` / `Part B (6 marks each)` / `Part C (10 marks each)`
- Each question must appear on its own line and be clearly numbered.
- Add **one empty line between questions** for readability.
- Do **not** merge questions into paragraphs.
- Use LaTeX formatting for any mathematical expressions.

---
Return only the formatted question paper as plain text. Do **not** include explanations, context, or additional instructions.
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
        st.error(f"Error generating questions: {str(e)}")
        return ""

# ---------- Answer Generator ----------
def generate_answers_for_questions(subject, questions_text, knowledge_base_id, model_arn):
    input_query = {
        "text": f'''
You are an expert academician.

Using the uploaded textbook material for "{subject}", generate a detailed answer key for the following exam questions.

Instructions:
- Keep answers clear, precise, and concise.
- Organize answer sections the same as question sections (Part A, Part B, Part C).
- Maintain the same question numbering.
- Use LaTeX formatting where needed.

Questions:
{questions_text}

Output:
- ONLY answers clearly organized by parts and numbering.
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
        st.error(f"Error generating answers: {str(e)}")
        return ""

# ---------- Streamlit App ----------
def main():
    st.set_page_config(page_title="Question Paper and Answer Key Generator", layout="wide")

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
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.title("AI-Driven University Question Paper & Answer Key Generator")

    generate = False
    if "units" not in st.session_state:
        st.session_state.units = []
    if "units_fetched" not in st.session_state:
        st.session_state.units_fetched = False
    if "paper" not in st.session_state:
        st.session_state.paper = ""
    if "answers" not in st.session_state:
        st.session_state.answers = ""

    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.header("Input Settings")

        subject = st.text_input("Enter Subject Name")

        if subject and not st.session_state.units_fetched:
            if st.button("Extract Chapters/Units"):
                with st.spinner("Fetching chapters from knowledge base..."):
                    units = extract_units_from_knowledge_base(subject)
                    if units:
                        st.session_state.units = units
                        st.session_state.units_fetched = True
                        st.success("Units extracted successfully.")
                    else:
                        st.warning("No units found.")

        selected_units = []
        if st.session_state.units:
            st.subheader("Select Chapters/Units")
            for i, unit in enumerate(st.session_state.units):
                col1, col2 = st.columns([6, 1])
                col1.markdown(f'<div class="unit-box">{unit}</div>', unsafe_allow_html=True)
                if col2.checkbox("Select", key=f"unit_{i}", label_visibility="collapsed"):
                    selected_units.append(unit)

            st.subheader("Define Question Structure")
            part_a = st.number_input("Part A (2 marks)", 1, 20, 10)
            part_b = st.number_input("Part B (6 marks)", 1, 20, 5)
            part_c = st.number_input("Part C (10 marks)", 0, 10, 2)

            st.subheader("Bloom’s Taxonomy Distribution (%)")
            bloom_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
            bloom_distribution = {}
            total_percentage = 0

            for level in bloom_levels:
                bloom_distribution[level] = st.number_input(f"{level} (%)", min_value=0, max_value=100, value=0)
                total_percentage += bloom_distribution[level]

            generate = st.button("Generate Question Paper")

    with right_col:
        st.header("Generated Output")

        if generate:
            if not selected_units:
                st.error("Please select at least one unit.")
            elif total_percentage != 100:
                st.error("Bloom's percentages must total 100%.")
            else:
                bloom_distribution_text = "\n".join([f"{level}: {percentage}%" for level, percentage in bloom_distribution.items()])
                with st.spinner("Generating question paper..."):
                    questions = generate_exam_questions(subject, selected_units, part_a, part_b, part_c, bloom_distribution_text)
                    if questions:
                        if not questions.strip().startswith("Part A"):
                            st.warning("Output may not follow standard format.")
                        st.session_state.paper = questions

        if st.session_state.paper:
            st.subheader("Question Paper")
            st.text_area("Question Paper", st.session_state.paper, height=400, max_chars=3000)

            if st.button("Download Question Paper as PDF"):
                st.download_button(
                    label="Download PDF",
                    data=convert_text_to_pdf(subject, st.session_state.paper),
                    file_name=f"{subject}_Question_Paper.pdf",
                    mime="application/pdf"
                )

        if st.session_state.paper:
            if st.button("Generate Answer Key"):
                with st.spinner("Generating answers..."):
                    answers = generate_answers_for_questions(subject, st.session_state.paper, knowledge_base_id, model_arn)
                    st.session_state.answers = answers

        if st.session_state.answers:
            st.subheader("Answer Key")
            st.text_area("Answer Key", st.session_state.answers, height=400)

            st.download_button(
                label="Download Answer Key PDF",
                data=convert_text_to_pdf(subject, st.session_state.answers),
                file_name=f"{subject}_Answer_Key.pdf",
                mime="application/pdf"
            )

    st.markdown("---")
    st.markdown("Make sure you have valid AWS credentials configured.")

if __name__ == "__main__":
    main()
