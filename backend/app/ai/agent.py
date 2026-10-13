import os

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from app.ai.schema import get_database_schema
from app.ai.tools import execute_readonly_sql


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

DATABASE_SCHEMA = get_database_schema()
print(DATABASE_SCHEMA)
SYSTEM_PROMPT = f"""
You are an AI assistant that answers questions about a MySQL database.

The database schema is already provided below.

Your job:

1. Understand the user's question.
2. Generate ONE SQL query that directly answers the question.
3. Call execute_readonly_sql exactly once.
4. Analyze the returned result.
5. Give the user a concise natural-language answer.

IMPORTANT RULES:

- Generate exactly ONE SQL query.
- Call execute_readonly_sql at most once.
- Never call execute_readonly_sql a second time.
- Never use SHOW TABLES.
- Never query information_schema.
- Never inspect the database schema using SQL.
- The schema below is authoritative.
- Do not guess tables or columns that aren't in the schema.
- Only use SELECT or WITH queries.
- Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.
- Do not verify your query with another query.
- Do not perform exploratory queries.
- Do not make multiple queries to "double check" an answer.

DATABASE SCHEMA:

{DATABASE_SCHEMA}
"""


execute_sql_declaration = types.FunctionDeclaration(
    name="execute_readonly_sql",
    description="""
Execute exactly one read-only SQL query against the MySQL database.

The complete database schema has already been provided.
Do not use this tool for schema discovery.
Do not query information_schema.
Do not use SHOW TABLES.
Generate one query that directly answers the user's question.
""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "sql": types.Schema(
                type=types.Type.STRING,
                description="One read-only SELECT or WITH SQL query."
            )
        },
        required=["sql"]
    )
)


database_tool = types.Tool(
    function_declarations=[
        execute_sql_declaration
    ]
)


database_tool = types.Tool(
    function_declarations=[
        execute_sql_declaration
    ]
)


def ask_database(question: str):

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=question
                )
            ]
        )
    ]

    try:

        # ------------------------------------------------
        # Gemini request #1
        # Decide the SQL query
        # ------------------------------------------------

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[database_tool]
            )
        )

        function_calls = []

        for part in response.candidates[0].content.parts:

            if part.function_call:
                function_calls.append(
                    part.function_call
                )

        # No tool call means Gemini answered directly.
        if not function_calls:
            return response.text

        # ------------------------------------------------
        # HARD LIMIT: exactly ONE database query
        # ------------------------------------------------

        if len(function_calls) > 1:
            return (
                "I couldn't safely process that request because "
                "the AI attempted multiple database queries."
            )

        function_call = function_calls[0]

        if function_call.name != "execute_readonly_sql":
            return "The AI requested an unsupported database operation."

        sql = function_call.args.get("sql")

        if not sql:
            return "The AI did not generate a SQL query."

        print("\nGemini generated SQL:")
        print(sql)

        # ------------------------------------------------
        # Execute SQL
        # ------------------------------------------------

        try:

            result = execute_readonly_sql(sql)

        except Exception as e:

            print("\nSQL ERROR:")
            print(str(e))

            return (
                "I couldn't execute the generated database query. "
                f"Database error: {str(e)}"
            )

        # ------------------------------------------------
        # Gemini request #2
        # Explain result
        # ------------------------------------------------

        contents.append(
            response.candidates[0].content
        )

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name=function_call.name,
                        response={
                            "result": result
                        }
                    )
                ]
            )
        )

        final_response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )

        return final_response.text

    except ClientError as e:

        if getattr(e, "code", None) == 429:

            return (
                "Gemini's free-tier request limit has been reached. "
                "Please wait a little before trying again."
            )

        print("\nGemini API ERROR:")
        print(str(e))

        return (
            "There was a problem communicating with Gemini. "
            "Please try again."
        )

    except Exception as e:

        print("\nUNEXPECTED ERROR:")
        print(str(e))

        return (
            "An unexpected error occurred while processing your request."
        )