import os
import time
import logging
import mysql.connector
from datetime import datetime, timedelta
from fastapi import Request

from typing import Optional, List, Dict
from dotenv import load_dotenv
from mysql.connector import Error

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnectionError(Exception):
    """Custom exception for database connection failures"""

    pass

def get_db_connection(
    max_retries: int = 12,  # 12 retries = 1 minute total (12 * 5 seconds)
    retry_delay: int = 5,  # 5 seconds between retries
) -> mysql.connector.MySQLConnection:
    """Create database connection with retry mechanism."""
    connection: Optional[mysql.connector.MySQLConnection] = None
    attempt = 1
    last_error = None

    while attempt <= max_retries:
        try:
            connection = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=os.getenv("MYSQL_DATABASE"),
            )

            # Test the connection
            connection.ping(reconnect=True, attempts=1, delay=0)
            logger.info("Database connection established successfully")
            return connection

        except Error as err:
            last_error = err
            logger.warning(
                f"Connection attempt {attempt}/{max_retries} failed: {err}. "
                f"Retrying in {retry_delay} seconds..."
            )

            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

            if attempt == max_retries:
                break

            time.sleep(retry_delay)
            attempt += 1

    raise DatabaseConnectionError(
        f"Failed to connect to database after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


async def setup_database(initial_users: list = None, initial_devices: list = None):
    """Creates user and session tables and populates initial user data if provided."""
    connection = None
    cursor = None

    # Define table schemas
    table_schemas = {
        "users": """
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fullname VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                location VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "sessions": """
            CREATE TABLE sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id INT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """,
        "devices": """
            CREATE TABLE devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                serial VARCHAR(255) NOT NULL UNIQUE,
                user_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """
    }

    try:
        # Get database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Drop and recreate tables one by one
        for table_name in ["sessions", "devices", "users"]:
            logger.info(f"Dropping table {table_name} if exists...")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            connection.commit()

        # Recreate tables one by one
        for table_name, create_query in table_schemas.items():

            try:
                # Create table
                logger.info(f"Creating table {table_name}...")
                cursor.execute(create_query)
                connection.commit()
                logger.info(f"Table {table_name} created successfully")

            except Error as e:
                logger.error(f"Error creating table {table_name}: {e}")
                raise

        # Insert initial users if provided
        if initial_users:
            try:
                insert_query = """
                    INSERT INTO users (fullname, username, password, location) 
                    VALUES (%s, %s, %s, %s) 
                    ON DUPLICATE KEY UPDATE username=username
                """
                for user in initial_users:
                    cursor.execute(insert_query, (user["fullname"], user["username"], user["password"], user["location"]))
                connection.commit()
                logger.info(f"Inserted {len(initial_users)} initial users")

            except Error as e:
                logger.error(f"Error inserting initial users: {e}")
                raise

        # Insert initial devices if provided
        if initial_devices:
            try:
                # Fetch user IDs to correctly link devices
                cursor.execute("SELECT id, username FROM users")
                user_map = {row[1]: row[0] for row in cursor.fetchall()}  # Map usernames to user IDs

                insert_device_query = """
                    INSERT INTO devices (name, serial, user_id)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE serial=serial
                """
                for device in initial_devices:
                    user_id = user_map.get(device["username"])  # Get user_id from username
                    if user_id:
                        cursor.execute(insert_device_query, (device["name"], device["serial"], user_id))
                    else:
                        logger.warning(f"Skipping device {device['name']} - User {device['username']} not found")

                connection.commit()
                logger.info(f"Inserted {len(initial_devices)} initial devices")

            except Error as e:
                logger.error(f"Error inserting initial devices: {e}")
                raise

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            logger.info("Database connection closed")


# Database utility functions for user and session management
async def get_user_by_username(username: str) -> Optional[dict]:
    """Retrieve user from database by username."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, fullname, username, password, location FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """
    Retrieve user from database by ID.

    Args:
        user_id: The ID of the user to retrieve

    Returns:
        Optional[dict]: User data if found, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


SESSION_DURATION = timedelta(minutes=30)

async def create_session(user_id: int, session_id: str) -> bool:
    """Create a new session in the database."""
    connection = None
    cursor = None
    try:
        expires_at = datetime.utcnow() + SESSION_DURATION
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id, expires_at) VALUES (%s, %s, %s)",
            (session_id, user_id, expires_at)
        )
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session from database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT *
            FROM sessions s
            WHERE s.id = %s
        """,
            (session_id,),
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def delete_session(session_id: str) -> bool:
    """Delete a session from the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()






async def create_user(fullname: str, username: str, password: str, location: str) -> bool:
    """Creates a new user and saves to the database without password hashing."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (fullname, username, password, location) VALUES (%s, %s, %s, %s)",
            (fullname, username, password, location)
        )
        connection.commit()
        return True
    except Error as e:
        logger.error(f"Error inserting new user: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



















async def get_user_by_session(session_id: str) -> Optional[dict]:
    """Retrieve user information based on session ID."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT u.id, u.fullname, u.username, u.location
            FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.id = %s AND s.expires_at > NOW()
        """
        cursor.execute(query, (session_id,))
        user = cursor.fetchone()

        if user:
            print(f"✅ Found user {user['username']} for session {session_id}")  # Debugging
        else:
            print(f"❌ No user found for session {session_id}")  # Debugging

        return user

    except mysql.connector.Error as e:
        print(f"❌ Error retrieving user from session: {e}")
        return None

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



async def get_devices_by_user_id(user_id: int) -> List[Dict]:
    """Retrieve all devices associated with a given user ID."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = "SELECT id, name, serial FROM devices WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        devices = cursor.fetchall()

        print(f"✅ Retrieved {len(devices)} devices for user ID {user_id}")  # Debugging
        return devices

    except mysql.connector.Error as e:
        print(f"❌ Error retrieving devices: {e}")
        return []

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def create_device(user_id: int, name: str, serial: str):
    """Insert a new device into the database for the given user."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = "INSERT INTO devices (name, serial, user_id) VALUES (%s, %s, %s)"
        cursor.execute(query, (name, serial, user_id))
        connection.commit()
        print(f"✅ Device {name} added for user ID {user_id}")  # Debugging

    except mysql.connector.Error as e:
        print(f"❌ Error adding device: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


