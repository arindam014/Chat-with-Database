from app.ai.tools import execute_readonly_sql
from fastapi import FastAPI
from app.api.chat import router as chat_router

from app.database import engine

app = FastAPI(
    title="AI Database Chat API"
)

app.include_router(
    chat_router,
    prefix="/api"
)

@app.get("/")
def root():
    return {
        "message": "AI Database Chat API is running"
    }


@app.get("/test-db")
def test_database():
    sql = """
          SELECT city, \
                 COUNT(*) AS customer_count
          FROM customers
          GROUP BY city \
          """

    return execute_readonly_sql(sql)