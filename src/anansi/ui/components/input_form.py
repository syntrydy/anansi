import streamlit as st

def render_input_form():
    """Render input form and return dict if submitted."""
    with st.form("lesson_form"):
        topic = st.text_input("Topic", "")
        country = st.selectbox("Country", ["Kenya", "Nigeria", "Ghana", "Senegal", "Cameroon"])
        grade = st.number_input("Grade", min_value=1, max_value=12, value=5)
        language = st.selectbox("Instruction Language", ["English", "Swahili", "French"])
        extra_context = st.text_area(
            "Extra context (optional, paragraph text)",
            value="",
            height=150,
            placeholder="Add any background or instructions..."
        )

        submitted = st.form_submit_button("Generate Lesson")
        if submitted:
            return {
                "topic": topic,
                "country": country,
                "grade": grade,
                "language": language,
                "extra_context": extra_context,
            }
    return None