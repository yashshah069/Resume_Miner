import streamlit as st
from utils1 import parse_resume, calculate_match_score
from io import StringIO

def app():
    st.set_page_config(page_title='Resume Miner', page_icon=':clipboard:', layout='wide')
    st.title('Resume Miner & Job Matcher :sleuth_or_spy:')

    # Create two columns for layout
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Upload Resumes")
        uploaded_files = st.file_uploader('Upload resumes in PDF or DOCX format :arrow_up_small:',
                                        type=['pdf', 'docx'], accept_multiple_files=True)

    with col2:
        st.header("Job Description")
        jd_input_type = st.radio("Choose input method:", 
                                ["Paste Job Description", "Upload Job Description File"])
        
        if jd_input_type == "Paste Job Description":
            job_description = st.text_area("Paste the job description here:", height=200)
        else:
            jd_file = st.file_uploader("Upload job description (PDF/DOCX)", 
                                      type=['pdf', 'docx'])
            if jd_file:
                try:
                    job_description = parse_resume([jd_file])[0]['text']
                except Exception as e:
                    st.error(f'Error parsing job description: {e}')
                    job_description = None
            else:
                job_description = None

    # Process resumes and calculate match scores
    if uploaded_files and job_description:
        st.markdown("---")
        st.header("Analysis Results")
        
        for uploaded_file in uploaded_files:
            try:
                st.info(f'Processing: {uploaded_file.name}')
                with st.spinner('Analyzing resume... :mag_right::hourglass_flowing_sand:'):
                    # Parse resume
                    result = parse_resume([uploaded_file])
                    
                    for index, row in result.iterrows():
                        # Calculate match score
                        match_score, feedback = calculate_match_score(row, job_description)
                        
                        # Create a container for each resume
                        st.markdown(f"### Resume Analysis: {row['name']}")
                        
                        # Create three columns for basic info
                        info_col1, info_col2, info_col3 = st.columns([1, 1, 1])
                        
                        with info_col1:
                            st.markdown(f'**Email:** {row["email"]} :envelope_with_arrow:')
                        with info_col2:
                            st.markdown(f'**Match Score:** {match_score}/10 :dart:')
                        with info_col3:
                            st.progress(match_score/10)
                        
                        # Display feedback in tabs
                        tabs = st.tabs(["Feedback", "Skills", "Summary"])
                        
                        with tabs[0]:  # Feedback tab
                            for category, suggestions in feedback.items():
                                st.markdown(f"**{category}:**")
                                for suggestion in suggestions:
                                    st.markdown(f"- {suggestion}")
                        
                        with tabs[1]:  # Skills tab
                            skills_cols = st.columns(3)
                            skills_list = row["skills_list"].split(',')
                            for i, skill in enumerate(skills_list):
                                skills_cols[i % 3].markdown(f'* {skill.strip()}')
                        
                        with tabs[2]:  # Summary tab
                            st.markdown(row["summary"])
                        
                        st.markdown("---")  # Add separator between resumes

            except Exception as e:
                st.error(f'Error: Unable to process the resume - {e}')

    elif uploaded_files:
        st.warning('Please provide a job description to calculate match scores.')
    elif job_description:
        st.warning('Please upload resumes to analyze.')

if __name__ == '__main__':
    app()