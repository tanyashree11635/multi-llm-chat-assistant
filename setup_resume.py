"""Setup script to initialize resume data for the chatbot."""
from pathlib import Path

def setup_resume_data():
    """Create data directory and sample resume template."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    resume_path = data_dir / "resume.txt"

    if not resume_path.exists():
        sample_resume = """RESUME - Tanya Shree Verma

CONTACT INFORMATION:
Email: tanyashreeverma@gmail.com
Phone: +91-XXXXXXXXXX
LinkedIn: linkedin.com/in/tanyashreeverma
GitHub: github.com/tanyashree11635
Portfolio: tanyashreeverma.github.io

PROFESSIONAL SUMMARY:
AI / Data Analyst / Software Professional with experience in data analysis, automation, machine learning, and cloud-based solutions. Skilled in transforming complex datasets into business insights, building scalable applications, and developing modern AI-powered tools. Proficient in Python, SQL, and cloud technologies with strong problem-solving abilities.

EDUCATION:
Bachelor's Degree in Computer Science / Relevant Field
India

TECHNICAL SKILLS:
Programming Languages: Python, SQL, JavaScript
Frameworks & Libraries: Pandas, NumPy, Streamlit, React
Tools & Technologies: Git, GitHub, Power BI, Tableau, Docker
Cloud Platforms: AWS, Azure, GCP
Databases: MySQL, PostgreSQL, SQL Server
AI/ML Tools: OpenAI API, Gemini API, Machine Learning
Business Tools: JIRA, Confluence

PROFESSIONAL EXPERIENCE:

Software / Data Analyst | Amazon | India
- Worked on operational analytics, reporting, and workflow automation.
- Improved data accuracy and process efficiency using dashboards and reporting tools.
- Collaborated with multiple teams to streamline operations.
- Supported business decisions through data-driven insights.

PROJECTS:

Multi LLM Chat Assistant | Python + Streamlit + OpenAI + Gemini
- Developed an AI chatbot supporting multiple LLM providers.
- Built interactive Streamlit frontend with chat session management.
- Integrated OpenAI GPT and Google Gemini APIs.
- Implemented modular backend architecture and secure configuration handling.

CERTIFICATIONS:
- AWS Fundamentals
- Python for Data Science
- AI / ML Fundamentals

LANGUAGES:
- English: Fluent
- Hindi: Fluent
"""
        resume_path.write_text(sample_resume, encoding="utf-8")
        print(f"✅ Created resume template at {resume_path}")
        print("📝 Your personalized resume has been initialized for the chatbot!")
        print(f"   Location: {resume_path.absolute()}")
    else:
        print(f"ℹ️ Resume already exists at {resume_path}")
        print("   You can edit it to update your information.")

if __name__ == "__main__":
    setup_resume_data()
