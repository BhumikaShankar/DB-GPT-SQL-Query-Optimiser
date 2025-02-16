import streamlit as st
import requests

# Flask Backend URL
BACKEND_URL = "http://127.0.0.1:5000/query"

# Apply dark theme styling
st.markdown(
    """
    <style>
    body {
        background-color: #121212;
        color: white;
    }
    .stTextInput, .stTextArea, .stSelectbox, .stButton>button {
        background-color: #333;
        color: white;
    }
    .stCodeBlock {
        background-color: #1E1E1E;
        color: #00FF00;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title(" Welcome to DB-GPT The SQL Query Optimizer")

st.divider()

# Natural Language Query Input
nl_query = st.text_area("📝 Enter your natural language query:", "Show all employees in HR department")

if st.button("Generate SQL & Execute"):
    if nl_query:
        with st.spinner(text="⏳ In progress... Generating and executing SQL query. Please wait!"):
            response = requests.post(BACKEND_URL, json={"query": nl_query})
        
        if response.status_code == 200:
            data = response.json()

            st.divider()
            
            st.subheader(" **Actual SQL Query**")
            st.code(data["actual_query"], language="sql")

            st.divider()
            st.subheader(" **Optimized SQL Query**")
            st.code(data["optimized_query"], language="sql")

            st.divider()

            st.subheader(" **Query Results**")
            if data["results"]:
                st.dataframe(data["results"])
            else:
                st.write("⚠ No results found.")
        else:
            st.error(f"❌ Error: {response.json().get('error', 'Unknown error')}")
