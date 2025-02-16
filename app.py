from flask import Flask, request, jsonify
import mysql.connector
import requests
import re

app = Flask(__name__)

# MySQL Configuration
db_config = {
    "host": "localhost",
    "user": "gptuser",
    "password": "gptuser",
    "database": "GPTEMPLOYEE"
}

# Google Gemini API Configuration
GOOGLE_API_KEY = "AIzaSyDnq62qZL4QR8nAiJdYDSjT3dpCEXQZ0SU"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GOOGLE_API_KEY}"

# Define the correct schema
TABLE_SCHEMA = """
Database: GPTEMPLOYEE
Tables:
- employees(id, name, department_id, salary, hire_date, email, phone, manager_id, project_id)
- departments(id, name, location)
- projects(id, name, budget, start_date, end_date)
- salaries(id, employee_id, salary, date_updated)
- attendances(id, employee_id, check_in, check_out)
"""

def clean_sql_query(sql_query):
    """Remove markdown formatting and unnecessary words from Gemini's SQL response."""
    sql_query = sql_query.strip()

    # Remove markdown-style SQL formatting
    sql_query = re.sub(r"```sql\s*([\s\S]+?)\s*```", r"\1", sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r"```([\s\S]+?)```", r"\1", sql_query, flags=re.IGNORECASE)

    # Remove unwanted text
    sql_query = re.sub(r"^Here is the SQL query:\s*", "", sql_query, flags=re.IGNORECASE)
    
    return sql_query.strip()

def convert_to_sql(nl_query):
    """Send natural language query to Google Gemini API and get both actual & optimized SQL queries."""
    prompt = f"""
    {TABLE_SCHEMA}

    Convert the following natural language query into:
    1️⃣ **Actual Query** – A simple SQL query that a beginner might write.
       - Can use `WHERE IN` instead of `JOIN`
       - Can include `SELECT *` instead of selecting specific columns
       - Can use **nested subqueries** for filtering

    2️⃣ **Optimized Query** – A performance-enhanced version of the Actual Query.
       - Use **explicit JOINs** instead of `WHERE IN`
       - Select **only necessary columns** instead of `SELECT *`
       - **Avoid nested subqueries** when possible

    ### Example 1:
    💬 **Query:** "Show details of all HR employees."
    ✅ **Actual Query:**
    ```sql
    SELECT * FROM employees WHERE department_id IN (SELECT id FROM departments WHERE name = 'HR');
    ```
    ✅ **Optimized Query:**
    ```sql
    SELECT e.id, e.name, d.name AS department, e.salary
    FROM employees e
    JOIN departments d ON e.department_id = d.id
    WHERE d.name = 'HR';
    ```

    ### Example 2:
    💬 **Query:** "Show employees working on AI Development."
    ✅ **Actual Query:**
    ```sql
    SELECT * FROM employees WHERE project_id IN (SELECT id FROM projects WHERE name = 'AI Development');
    ```
    ✅ **Optimized Query:**
    ```sql
    SELECT e.id, e.name, d.name AS department, e.salary
    FROM employees e
    JOIN departments d ON e.department_id = d.id
    JOIN projects p ON e.project_id = p.id
    WHERE p.name = 'AI Development';
    ```

    ---
    
    Now, generate both the Actual Query and Optimized Query for this user request:

    💬 **Query:** {nl_query}

    **Format:**
    Actual Query: <Beginner-Friendly SQL>
    Optimized Query: <Performance-Tuned SQL>
    """

    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(GEMINI_API_URL, json=payload)
        response_data = response.json()

        # Check if API call was successful
        if response.status_code != 200:
            return None, None, f"API error: {response_data}"

        # Extract SQL queries
        sql_queries = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # Extract actual and optimized SQL queries
        queries = re.findall(r"Actual Query:\s*(.*?)\s*Optimized Query:\s*(.*)", sql_queries, re.DOTALL)
        
        if not queries:
            return None, None, "API did not return valid SQL queries."

        actual_sql = clean_sql_query(queries[0][0])
        optimized_sql = clean_sql_query(queries[0][1])

        return actual_sql, optimized_sql, None

    except Exception as e:
        return None, None, str(e)

@app.route('/query', methods=['POST'])
def handle_query():
    """Receive query from frontend, generate actual & optimized SQL, execute and return results"""
    data = request.json
    nl_query = data.get("query")

    # Convert NL to SQL (Actual & Optimized)
    actual_sql, optimized_sql, error = convert_to_sql(nl_query)
    if error:
        return jsonify({"error": error, "actual_query": actual_sql, "optimized_query": optimized_sql}), 500

    # Execute Optimized SQL Query
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(optimized_sql)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({
            "natural_language_query": nl_query,
            "actual_query": actual_sql,
            "optimized_query": optimized_sql,
            "results": results
        })
    except Exception as e:
        return jsonify({
            "error": f"SQL Execution Error: {str(e)}",
            "actual_query": actual_sql,
            "optimized_query": optimized_sql
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
