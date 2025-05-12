import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os

def create_db_connection():
    connection = None
    try:
        # Fetch credentials from environment variables
        db_host = os.environ.get("DB_HOST")
        db_name = os.environ.get("DB_NAME")
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")

        # Check if any environment variable is missing (optional but good for debugging)
        if not all([db_host, db_name, db_user, db_password]):
            print("Error: One or more database environment variables are not set.")
            # You can log this to PythonAnywhere's error logs
            # For example:
            if not db_host: print("DB_HOST is not set")
            if not db_name: print("DB_NAME is not set")
            if not db_user: print("DB_USER is not set")
            # Avoid printing the password, even if it's missing
            if not db_password: print("DB_PASSWORD is not set")
            return None

        connection = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        # print("Database connection successful for tool") # Optional: for debugging, remove in production
        return connection
    except Error as err:
        print(f"Error connecting to DB for tool: '{err}'")
        # Log the host used to help debug connection issues on PythonAnywhere
        print(f"Attempted to connect to DB_HOST: {os.environ.get('DB_HOST')}")
        return None

def search_federal_documents(query: str = None, agency: str = None, start_date: str = None, end_date: str = None, limit: int = 10):
    """
    Searches the federal documents database based on various criteria.

    Args:
        query (str, optional): Keywords to search in title or content. Defaults to None.
        agency (str, optional): Filter by agency name. Defaults to None.
        start_date (str, optional): Start date for publication date filter (YYYY-MM-DD). Defaults to None.
        end_date (str, optional): End date for publication date filter (YYYY-MM-DD). Defaults to None.
        limit (int, optional): Maximum number of results to return. Defaults to 10.

    Returns:
        list: A list of dictionaries, where each dictionary represents a matching document.
              Returns an empty list if no results or an error occurs.
    """
    conn = create_db_connection()
    results = []
    if conn is None:
        return results # Return empty list if DB connection fails

    cursor = conn.cursor(dictionary=True) # Return results as dictionaries

    sql_query = "SELECT document_number, title, agency, publication_date, document_url FROM federal_documents WHERE 1=1"
    params = []

    if query:
        sql_query += " AND (title LIKE %s OR content LIKE %s)"
        params.append(f"%{query}%")
        params.append(f"%{query}%")
    if agency:
        sql_query += " AND agency LIKE %s"
        params.append(f"%{agency}%")
    if start_date:
        try:
            datetime.strptime(start_date, '%Y-%m-%d') # Validate date format
            sql_query += " AND publication_date >= %s"
            params.append(start_date)
        except ValueError:
            print(f"Invalid start_date format: {start_date}")
    if end_date:
        try:
            datetime.strptime(end_date, '%Y-%m-%d') # Validate date format
            sql_query += " AND publication_date <= %s"
            params.append(end_date)
        except ValueError:
            print(f"Invalid end_date format: {end_date}")

    sql_query += f" LIMIT {limit}" # Limit results

    try:
        cursor.execute(sql_query, params)
        results = cursor.fetchall()
    except Error as err:
        print(f"Error executing search query: '{err}'")
    finally:
        cursor.close()
        conn.close()

    return results

# Example of another tool function (if needed)
# def get_document_details(document_number: str):
#     """
#     Retrieves details for a specific federal document by its document number.
#     """
#     conn = create_db_connection()
#     details = None
#     if conn is None:
#         return details
#     cursor = conn.cursor(dictionary=True)
#     sql_query = "SELECT * FROM federal_documents WHERE document_number = %s LIMIT 1"
#     try:
#         cursor.execute(sql_query, (document_number,))
#         details = cursor.fetchone()
#     except Error as err:
#         print(f"Error fetching document details: '{err}'")
#     finally:
#         cursor.close()
#         conn.close()
#     return details