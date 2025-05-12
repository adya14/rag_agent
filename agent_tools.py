# agent_tools.py

import mysql.connector
from mysql.connector import Error
import os # For reading environment variables
from datetime import datetime, timedelta # For date handling in search

# --- Database Connection Function ---
def create_db_connection():
    """
    Creates a database connection using credentials from environment variables.
    Returns the connection object or None if connection fails.
    """
    connection = None
    # Read credentials from environment variables
    # Provide defaults for host and port if not set in .env
    db_host = os.environ.get("DB_HOST", "localhost")
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_port = os.environ.get("DB_PORT", "3306") # Default MySQL port

    # Basic check if essential variables were loaded
    if not all([db_host, db_name, db_user]): # db_password can be empty for some local setups
         print("CRITICAL ERROR in create_db_connection: DB_HOST, DB_NAME, or DB_USER not found in environment variables. Check .env file and ensure main.py loads it.")
         return None

    try:
        print(f"Attempting to connect to DB: mysql://{db_user}@{db_host}:{db_port}/{db_name}")
        connection = mysql.connector.connect(
            host=db_host,
            port=int(db_port),    # Ensure port is an integer
            database=db_name,
            user=db_user,
            password=db_password
        )
        print("MySQL Database connection successful!")
        return connection
    except ValueError as verr: # Handles error if DB_PORT is not a valid number
        print(f"Configuration Error in create_db_connection: DB_PORT '{db_port}' is not a valid integer. {verr}")
        return None
    except Error as err:
        print(f"Error connecting to DB in create_db_connection: '{err}'")
        # Log connection details attempted (excluding password for security in logs)
        print(f"Attempted connection details (excluding password): host={db_host}, port={db_port}, user={db_user}, database={db_name}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in create_db_connection: {e}")
        return None

# --- Tool Function to Search Documents ---
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
    conn = create_db_connection() # Call the updated connection function
    results = [] # Default to empty list

    if conn is None:
        print("Database connection failed in search_federal_documents, cannot perform search.")
        return results # Return empty list if connection failed

    cursor = None # Initialize cursor to None to ensure it's defined for finally block
    try:
        cursor = conn.cursor(dictionary=True) # Use dictionary=True for easier result handling

        sql_query_parts = ["SELECT document_number, title, agency, publication_date, document_url, content FROM federal_documents WHERE 1=1"]
        params = [] # Use parameterized queries to prevent SQL injection

        if query:
            sql_query_parts.append("AND (title LIKE %s OR content LIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])
        if agency:
            sql_query_parts.append("AND agency LIKE %s")
            params.append(f"%{agency}%")

        # Validate and add date parameters
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d') # Validate format
                sql_query_parts.append("AND publication_date >= %s")
                params.append(start_date)
            except ValueError:
                print(f"Invalid start_date format: {start_date}. Ignoring.")
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d') # Validate format
                sql_query_parts.append("AND publication_date <= %s")
                params.append(end_date)
            except ValueError:
                print(f"Invalid end_date format: {end_date}. Ignoring.")

        # Add limit (ensure it's an integer)
        try:
            limit_int = int(limit)
            if limit_int <= 0: # Prevent non-positive limits
                limit_int = 10 # Default to 10 if invalid
            sql_query_parts.append("LIMIT %s")
            params.append(limit_int)
        except ValueError:
            print(f"Invalid limit value: {limit}. Defaulting to 10.")
            sql_query_parts.append("LIMIT %s")
            params.append(10)


        final_sql_query = " ".join(sql_query_parts)
        print(f"Executing SQL: {final_sql_query} with params: {params}")

        cursor.execute(final_sql_query, params)
        fetched_results = cursor.fetchall()
        print(f"Found {len(fetched_results)} documents from database.")

        # Convert date/datetime objects to strings for JSON serialization if needed by the LLM
        for row in fetched_results:
            for key, value in row.items():
                if isinstance(value, (datetime, datetime.date)): # Check for both date and datetime
                    row[key] = value.isoformat()
            results.append(row)

    except Error as err:
        print(f"Error executing search query in search_federal_documents: '{err}'")
        # results will remain empty or partially filled if error occurs mid-fetch
    except Exception as e:
        print(f"An unexpected error occurred in search_federal_documents: {e}")
    finally:
        # Ensure cursor and connection are closed even if errors occur
        if cursor:
            cursor.close()
            print("Database cursor closed.")
        if conn and conn.is_connected(): # Check if connection object exists and is connected
            conn.close()
            print("Database connection closed.")

    return results

# You can add other tool functions here if needed, following a similar pattern.
