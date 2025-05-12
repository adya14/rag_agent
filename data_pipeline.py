# data_pipeline.py

import requests
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import os # <--- Added import for os to read environment variables

# --- Database Connection Function (Copied from agent_tools.py best practice) ---
def create_db_connection():
    connection = None
    # Read credentials from environment variables
    db_host = os.environ.get("DB_HOST", "localhost")
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_port = os.environ.get("DB_PORT", "3306")

    if not all([db_host, db_name, db_user]):
         print("Warning: DB_HOST, DB_NAME, or DB_USER not found in environment variables for data_pipeline. Check .env file.")
         # db_password can be empty for some local setups

    try:
        print(f"Pipeline attempting to connect to DB: mysql://{db_user}@{db_host}:{db_port}/{db_name}")
        connection = mysql.connector.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )
        # This print statement will confirm connection success from this specific function
        # It was already in your log, so the previous run must have used a similar connection.
        # We are making it explicit here for clarity and robustness.
        print("Pipeline MySQL Database connection successful!")
        return connection
    except ValueError as verr:
        print(f"Error in pipeline DB connection: DB_PORT '{db_port}' is not a valid integer. {verr}")
        return None
    except Error as err:
        print(f"Error in pipeline DB connection: '{err}'")
        print(f"Pipeline attempted connection details: host={db_host}, port={db_port}, user={db_user}, database={db_name}")
        return None

# --- API Fetching Function (Modified for 2025 data) ---
def fetch_federal_register_data(): # Removed date_filter argument as it was not used
    base_url = "https://www.federalregister.gov/api/v1/documents.json"
    
    # MODIFIED: Fetch documents for the year 2025 up to the current date
    start_date_str = '2025-01-01'
    # Ensure current_date is also in YYYY-MM-DD for consistency if comparing
    current_date_obj = datetime.now()
    # If current_date_obj is before 2025-01-01, this would fetch nothing.
    # If current_date_obj is within 2025, it fetches up to current_date_obj.
    # If current_date_obj is after 2025, it will fetch all of 2025.
    
    # For the specific requirement "only the 2025 dataset" when running IN 2025:
    # We want from Jan 1, 2025 up to the current date of 2025.
    # If the script were run in 2026, and you only wanted 2025 data, end_date_str would be '2025-12-31'
    
    end_date_str = current_date_obj.strftime('%Y-%m-%d')
    
    # If today's date is past 2025, and you ONLY want 2025 data, you'd use:
    # if current_date_obj.year > 2025:
    #    end_date_str = '2025-12-31'

    print(f"Fetching documents from {start_date_str} to {end_date_str}")

    params = {
        'conditions[publication_date][gte]': start_date_str,
        'conditions[publication_date][lte]': end_date_str,
        'per_page': 1000, # API might limit this, common values are 50, 100, or 1000
        # You can add more conditions here if needed, e.g., for specific document types
        # 'conditions[type][]': 'RULE',
        # 'conditions[type][]': 'EXECUTIVE ORDER', # Check API for exact filter key
    }
    
    all_documents = []
    page = 1
    max_pages = 10 # Safety break for development to avoid too many API calls accidentally
    
    while True:
        if page > max_pages: # Safety break
            print(f"Reached max_pages limit ({max_pages}). Stopping fetch.")
            break
            
        params['page'] = page
        try:
            print(f"Fetching page {page} with params: {params}")
            response = requests.get(base_url, params=params, timeout=30) # Added timeout
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()
            
            current_page_documents = data.get('results', [])
            if not current_page_documents:
                print("No more documents found on this page or subsequent pages.")
                break # No more documents
            
            all_documents.extend(current_page_documents)
            print(f"Fetched {len(current_page_documents)} documents from page {page}. Total so far: {len(all_documents)}")

            # Check if there are more pages - API dependent logic
            # The example API has 'count' and 'total_pages' or 'next_page_url'
            # Simple check: if results are less than per_page, it's likely the last page
            if len(current_page_documents) < params['per_page']:
                print("Fetched less than 'per_page' documents, assuming last page.")
                break
            
            # More robust check if API provides total_pages or next_page_url
            if 'total_pages' in data and page >= data['total_pages']:
                 print("Reached total_pages reported by API.")
                 break
            if 'next_page_url' in data and not data['next_page_url']: # If next_page_url is null/empty
                 print("API indicates no next page.")
                 break

            page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from API: {e}")
            break # Stop fetching on error
        except ValueError as e: # Includes JSONDecodeError
            print(f"Error decoding JSON response from API: {e}")
            break
            
    return all_documents

# --- Data Processing Function (Assumed mostly correct from your snippet) ---
def process_document_data(document_json):
    # Extract relevant fields. Adjust based on actual API response structure.
    # Ensure all keys accessed with .get() to avoid KeyErrors if a field is missing.
    return {
        'document_number': document_json.get('document_number'),
        'title': document_json.get('title'),
        'agency': ", ".join([agency.get('name', '') for agency in document_json.get('agencies', []) if agency.get('name')]), # Example for multiple agencies
        'publication_date': document_json.get('publication_date'),
        'document_url': document_json.get('html_url'), # Assuming html_url is the link
        'content': document_json.get('abstract') or document_json.get('full_text_xml_url') # Prefer abstract, fallback or decide strategy
        # Consider fetching full text if abstract is not enough and a full_text_xml_url is provided
    }

# --- Database Insertion Function (Assumed mostly correct from your snippet) ---
def insert_document(connection, document_data):
    # Using document_number as PRIMARY KEY, so ON DUPLICATE KEY UPDATE is good
    query = """
    INSERT INTO federal_documents (document_number, title, agency, publication_date, document_url, content)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    title = VALUES(title), agency = VALUES(agency), publication_date = VALUES(publication_date), document_url = VALUES(document_url), content = VALUES(content);
    """
    values = (
        document_data.get('document_number'),
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
        # print(f"Record inserted/updated: {document_data.get('document_number')}") # Keep this commented if too verbose
    except Error as err:
        print(f"Database Error: '{err}' while inserting data for {document_data.get('document_number')}")
    except Exception as e:
        print(f"An unexpected error occurred during DB insert: {e} for {document_data.get('document_number')}")


# --- Main Execution Block ---
if __name__ == "__main__":
    # Ensure .env is loaded if running this script directly and .env is in the same directory
    # This is important if DB credentials are ONLY in .env
    from dotenv import load_dotenv
    load_dotenv()
    
    conn = create_db_connection() # Uses the function defined in this file
    
    if conn:
        print("Starting data pipeline to fetch Federal Register documents for 2025...")
        # Fetch data for 2025 (Jan 1, 2025 up to current date in 2025)
        raw_data = fetch_federal_register_data()
        
        if raw_data:
            print(f"Fetched a total of {len(raw_data)} documents from the API.")
            inserted_count = 0
            for doc in raw_data:
                if doc.get('document_number'): # Ensure there's a document number before processing
                    processed_doc = process_document_data(doc)
                    insert_document(conn, processed_doc)
                    inserted_count +=1
                else:
                    print(f"Skipping document due to missing document_number: {doc.get('title', 'N/A')}")
            print(f"Attempted to insert/update {inserted_count} documents.")
        else:
            print("No documents fetched from the API. Check API parameters or connection.")
            
        if conn.is_connected():
            conn.close()
            print("Pipeline database connection closed.")
        print("Data pipeline finished.")
    else:
        print("Data pipeline could not connect to the database. Aborting.")