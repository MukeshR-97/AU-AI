import os
import time
import re
import boto3
import streamlit as st

# AWS Configuration
BUCKET_NAME = os.getenv("BUCKET_NAME")
AWS_REGION = "us-east-1"
KNOWLEDGE_BASE_ID = "NRQ5XMNDMI"
DATA_SOURCE_ID = "O4TBZ8VRDB"

# Check essential environment variables
if not BUCKET_NAME:
    st.error("❌ Environment variable 'BUCKET_NAME' is not set.")
    st.stop()

# AWS Clients
s3_client = boto3.client("s3", region_name=AWS_REGION)
bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)

# Temp folder
FOLDER_PATH = "/tmp/"

# Save uploaded file locally
def save_uploaded_file(uploaded_file, save_path):
    try:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    except Exception as e:
        st.error(f"❌ Error saving file: {e}")

# Upload to S3
def upload_file_to_s3(local_path, s3_key):
    try:
        s3_client.upload_file(Filename=local_path, Bucket=BUCKET_NAME, Key=s3_key)
        st.success("✅ File successfully uploaded to S3!")
    except Exception as e:
        st.error(f"❌ Error uploading file to S3: {e}")
        raise

# Wait for ongoing job to complete
def wait_for_ongoing_job_to_complete():
    while True:
        response = bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            maxResults=1
        )
        jobs = response.get("ingestionJobSummaries", [])
        if not jobs:
            return True

        status = jobs[0].get("status")
        if status in ["COMPLETE", "FAILED"]:
            return True
        elif status in ["IN_PROGRESS", "STARTING"]:
            time.sleep(10)
        else:
            return False

# Start ingestion
def sync_knowledge_base():
    if wait_for_ongoing_job_to_complete():
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID
        )
        return response["ingestionJob"]["ingestionJobId"]
    else:
        return None

# Track ingestion job
def track_ingestion_job(job_id):
    while True:
        response = bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            ingestionJobId=job_id
        )
        status = response["ingestionJob"]["status"]
        yield status
        if status in ["COMPLETE", "FAILED"]:
            break
        time.sleep(10)

# Streamlit UI
def main():
    st.title("📂 Admin Panel - Upload & Sync Syllabus with Bedrock")

    # Debug UI
    st.write("✅ Streamlit UI loaded successfully.")

    uploaded_file = st.file_uploader("📄 Upload Syllabus PDF", type="pdf")
    subject_name_input = st.text_input("📘 Enter Subject Name (no spaces)", "")

    # Sanitize subject name
    subject_name = re.sub(r"[^a-zA-Z0-9_-]", "_", subject_name_input.strip())

    if uploaded_file and subject_name:
        if uploaded_file.type != "application/pdf":
            st.error("❌ Please upload a PDF file.")
            return

        syllabus_filename = f"{subject_name}.pdf"
        local_path = os.path.join(FOLDER_PATH, syllabus_filename)

        with st.spinner("🔄 Saving and uploading file..."):
            save_uploaded_file(uploaded_file, local_path)
            s3_key = f"knowledgebase/{subject_name}/{syllabus_filename}"
            upload_file_to_s3(local_path, s3_key)

            # Clean up local file
            if os.path.exists(local_path):
                os.remove(local_path)

        st.info("📡 Starting ingestion with Bedrock Knowledge Base...")
        job_id = sync_knowledge_base()

        if job_id:
            with st.status("🔄 Syncing with Bedrock...", expanded=True) as status_box:
                for state in track_ingestion_job(job_id):
                    status_box.update(label=f"📡 Ingestion Status: `{state}`", state="running")
                if state == "COMPLETE":
                    status_box.update(label="✅ Ingestion Complete!", state="complete")
                else:
                    status_box.update(label=f"❌ Ingestion Failed (Status: {state})", state="error")
        else:
            st.error("❌ Could not start ingestion. Another job might still be running. Please try again shortly.")

# Entry point
if __name__ == "__main__":
    main()
