# create_schemas.py
import os
import psycopg2
from dotenv import load_dotenv
import time # Import time for potential retries (good for Docker startup)

# Load environment variables (important if you're using .env for DB credentials)
load_dotenv()

# --- Configuration for the script ---
# Tables that might exist in the 'public' schema and should be dropped
# because they will be recreated in specific schemas.
TABLES_TO_DROP_FROM_PUBLIC = [
    'members',
    'votings',
    # Add any other table names here that your Django app will move
    # from 'public' to a custom schema (e.g., 'auth_user' if you move it)
    # Be cautious with adding Django's built-in tables unless you really
    # intend to manage them within your custom schemas.
    # For now, members and votings are sufficient based on your models.
]

# Schemas that need to be created
SCHEMAS_TO_CREATE = ['parliament', 'analysis'] # Add any other schemas you need


def setup_database():
    db_name = os.getenv('POSTGRES_DB')
    db_user = os.getenv('POSTGRES_USER')
    db_password = os.getenv('POSTGRES_PASSWORD')
    db_host = os.getenv('POSTGRES_HOST', 'db') # 'db' is default for Docker compose
    db_port = os.getenv('POSTGRES_PORT', '5432')

    conn = None
    max_retries = 10 # Number of times to retry connection
    retry_delay = 3  # Seconds to wait between retries

    for attempt in range(max_retries):
        try:
            # Connect to the PostgreSQL database
            conn = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            conn.autocommit = True # Auto-commit changes
            cursor = conn.cursor()

            # --- Drop Existing Tables from 'public' Schema ---
            print("\nAttempting to drop problematic tables from 'public' schema...")
            for table_name in TABLES_TO_DROP_FROM_PUBLIC:
                drop_table_sql = f'DROP TABLE IF EXISTS public."{table_name}" CASCADE;'
                print(f"Executing: {drop_table_sql}")
                cursor.execute(drop_table_sql)
                print(f"Table public.\"{table_name}\" ensured to be dropped.")

            # --- Create Schemas ---
            print("\nAttempting to create necessary PostgreSQL schemas...")
            for schema_name in SCHEMAS_TO_CREATE:
                # Use IF NOT EXISTS to prevent errors if schema already exists
                create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema_name};"
                print(f"Executing: {create_schema_sql}")
                cursor.execute(create_schema_sql)
                print(f"Schema '{schema_name}' ensured to exist.")

            cursor.close()
            print("\nDatabase setup finished successfully.")
            return # Exit function on success

        except psycopg2.OperationalError as e:
            # This specific error usually means the DB isn't ready/reachable
            print(f"Database not ready (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"Exiting: Failed to connect to database after {max_retries} attempts.")
                exit(1) # Exit with error code if connection fails
        except psycopg2.Error as e:
            print(f"Error during database setup: {e}")
            exit(1) # Exit with error code for other DB errors
        finally:
            if conn:
                conn.close()
                print("Database connection closed.")

if __name__ == "__main__":
    setup_database()