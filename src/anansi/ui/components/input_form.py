"""Teacher lesson input form (Streamlit)."""

from typing import Any, TypedDict

import streamlit as st


class LessonFormData(TypedDict):
    """Payload returned when the user submits the lesson form."""

    topic: str
    country: str
    grade: int
    language: str
    audience: str
    extra_context: dict[str, Any]


def render_input_form() -> LessonFormData | None:
    """Render the form; return structured data on submit, else ``None``."""
    with st.form("lesson_form"):
        topic = st.text_input("Topic", "")
        country = st.selectbox(
            "Country",
            ["Kenya", "Nigeria", "Ghana", "Senegal", "Cameroon"],
        )
        grade = st.number_input("Grade", min_value=1, max_value=12, value=5)
        language = st.selectbox(
            "Instruction Language", ["English", "Swahili", "French"]
        )
        audience = st.selectbox(
            "Audience",
            options=["kid", "adult", "general"],
            format_func=lambda x: {"kid": "Kids", "adult": "Adults", "general": "General"}.get(
                x, x
            ),
            index=0,
        )
        extra_context_text = st.text_area(
            "Extra context (optional, paragraph text)",
            value="",
            height=150,
            placeholder="Add any background or instructions...",
        )

        submitted = st.form_submit_button("Generate Lesson")
        if submitted:
            extra: dict[str, Any] = (
                {"notes": extra_context_text} if extra_context_text else {}
            )
            return LessonFormData(
                topic=topic,
                country=country,
                grade=int(grade),
                language=language,
                audience=str(audience),
                extra_context=extra,
            )
    return None
