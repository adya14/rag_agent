import requests
from datetime import datetime, timedelta
import requests
from datetime import datetime, timedelta
import mysql.connector # <-- Add this import
from mysql.connector import Error # <-- Add this import

def fetch_federal_register_data(date_フィルター):
    # Replace with actual Federal Registry API endpoint and parameters
    base_url = "https://www.federalregister.gov/api/v1/documents.json"
    # Example: Fetch documents published today
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d') # Example: Last 7 days
    params = {
        'conditions[publication_date][gte]': start_date,
        'conditions[publication_date][lte]': end_date,
        'per_page': 1000 # Adjust based on API limits
    }
    all_documents = []
    page = 1
    while True:
        params['page'] = page
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()
            documents = data.get('results', [])
            if not documents:
                break
            all_documents.extend(documents)
            if data.get('count', 0) <= page * data.get('per_page', 0): # Simple check for more pages
                 break # Basic check, refer to actual API docs for pagination
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            break # Or implement retry logic
    return all_documents
def process_document_data(document):
      # Extract and format data according to your table schema
      processed_data = {
          'id': document.get('document_number'), # Using document_number as ID example
          'document_number': document.get('document_number'),
          'title': document.get('title'),
          'agency': document.get('agencies', [{}])[0].get('name') if document.get('agencies') else None,
          'publication_date': document.get('publication_date'),
          'document_url': document.get('html_url'),
          'content': document.get('abstract') # Or fetch full content if API allows and you need it
      }
      return processed_data

def fetch_federal_register_data(date_フィルター):
    # Replace with actual Federal Registry API endpoint and parameters
    base_url = "https://www.federalregister.gov/api/v1/documents.json"
    # Example: Fetch documents published today
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d') # Example: Last 7 days
    params = {
        'conditions[publication_date][gte]': start_date,
        'conditions[publication_date][lte]': end_date,
        'per_page': 1000 # Adjust based on API limits
    }
    all_documents = []
    page = 1
    while True:
        params['page'] = page
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()
            documents = data.get('results', [])
            if not documents:
                break
            all_documents.extend(documents)
            if data.get('count', 0) <= page * data.get('per_page', 0): # Simple check for more pages
                 break # Basic check, refer to actual API docs for pagination
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            break # Or implement retry logic
    return all_documents

def process_document_data(document):
      # Extract and format data according to your table schema
      processed_data = {
          'id': document.get('document_number'), # Using document_number as ID example
          'document_number': document.get('document_number'),
          'title': document.get('title'),
          'agency': document.get('agencies', [{}])[0].get('name') if document.get('agencies') else None,
          'publication_date': document.get('publication_date'),
          'document_url': document.get('html_url'),
          'content': document.get('abstract') # Or fetch full content if API allows and you need it
      }
      return processed_data

def create_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost", # e.g., "localhost"
            database="rag_data_db",
            user="root",
            password="Adya@#123"
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")
    return connection
def insert_document(connection, document_data):
    # Ensure column names match your table and dictionary keys
    query = """
    INSERT INTO federal_documents (document_number, title, agency, publication_date, document_url, content)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    title = VALUES(title), agency = VALUES(agency), publication_date = VALUES(publication_date), document_url = VALUES(document_url), content = VALUES(content);
    """
    values = (
        # Ensure the order of values matches the order of columns
        document_data.get('document_number'), # Use document_number here as the key
        document_data.get('title'),
        document_data.get('agency'),
        document_data.get('publication_date'),
        document_data.get('document_url'),
        document_data.get('content')
    )
    try:
        cursor = connection.cursor()
        cursor.execute(query, values)
        connection.commit()
        # print(f"Record inserted/updated: {document_data.get('document_number')}")
    except Error as err:
        print(f"Error: '{err}' inserting data for {document_data.get('document_number')}")

if __name__ == "__main__":
      conn = create_db_connection()
      if conn:
          # Fetch data for the last 7 days as an example
          raw_data = fetch_federal_register_data(date_フィルター="last_week") # Adjust date_filter logic in fetch function
          print(f"Fetched {len(raw_data)} documents.")
          for doc in raw_data:
              processed_doc = process_document_data(doc)
              insert_document(conn, processed_doc)
          conn.close()
          print("Data pipeline finished.")
      else:
          print("Failed to connect to database. Pipeline aborted.")