import sqlite3
from datetime import datetime
import pytz
import threading
from contextlib import contextmanager
import pandas as pd

class DatabaseHandler:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.local = threading.local()
        self.create_tables()  # Create tables on initialization
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = sqlite3.connect('tokens.db', timeout=20)  # Added timeout
        try:
            yield connection
        finally:
            connection.close()
    
    def create_tables(self):
        with self.get_connection() as conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                address TEXT PRIMARY KEY,
                name TEXT,
                created_at TEXT,
                first_seen TEXT,
                fdv_usd REAL,
                reserve_in_usd REAL,
                transactions_24h INTEGER,
                volume_24h REAL,
                last_updated TEXT,
                mint_authority BOOLEAN,
                freeze_authority BOOLEAN,
                top_10_holders REAL,
                gt_score REAL,
                top_holder REAL,
                top_20_holders REAL,
                mint_address TEXT,
                is_honeypot BOOLEAN,
                entropy_score REAL
            )
            ''')
            conn.commit()

    def parse_datetime(self, dt_str):
        """Parse datetime string to UTC datetime object"""
        try:
            if isinstance(dt_str, datetime):
                return dt_str.astimezone(pytz.UTC).isoformat()
            elif isinstance(dt_str, str):
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return dt.astimezone(pytz.UTC).isoformat()
            return datetime.now(pytz.UTC).isoformat()
        except Exception as e:
            print(f"Error parsing datetime: {e}")
            return datetime.now(pytz.UTC).isoformat()

    def add_token(self, token_data):
        try:
            with self.get_connection() as conn:
                # Ensure proper timezone handling for created_at
                try:
                    created_at = pd.to_datetime(token_data['created_at'])
                    if created_at.tzinfo is None:
                        created_at = created_at.tz_localize('UTC')
                    created_at = created_at.isoformat()
                except (ValueError, TypeError):
                    created_at = pd.Timestamp.now(tz='UTC').isoformat()
                
                current_time = datetime.now(pytz.UTC).isoformat()
                
                # Ensure top_holder and top_20_holders are floats
                top_holder = float(token_data.get('top_holder', 0))
                top_20_holders = float(token_data.get('top_20_holders', 0))
                
                conn.execute('''
                INSERT OR IGNORE INTO tokens 
                (address, name, created_at, first_seen, fdv_usd, reserve_in_usd, 
                 transactions_24h, volume_24h, last_updated, mint_authority, 
                 freeze_authority, top_10_holders, gt_score, top_holder, 
                 top_20_holders, mint_address, entropy_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(token_data['address']),
                    str(token_data['name']),
                    created_at,
                    current_time,
                    float(token_data.get('fdv_usd', 0) or 0),
                    float(token_data.get('reserve_in_usd', 0) or 0),
                    int(token_data.get('transactions_24h', 0) or 0),
                    float(token_data.get('volume_24h', 0) or 0),
                    current_time,
                    bool(token_data.get('mint_authority', False)),
                    bool(token_data.get('freeze_authority', False)),
                    float(token_data.get('top_10_holders', 0) or 0),
                    float(token_data.get('gt_score', 0) or 0),
                    top_holder,
                    top_20_holders,
                    str(token_data.get('mint_address', '')),
                    float(token_data.get('entropy_score', 0) or 0)
                ))
                conn.commit()
        except Exception as e:
            print(f"Error adding token to database: {e}")
            print(f"Token data: {token_data}")

    def get_all_tokens(self):
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    address, name, created_at, fdv_usd, reserve_in_usd,
                    transactions_24h, volume_24h, last_updated, mint_authority,
                    freeze_authority, top_10_holders, gt_score, top_holder,
                    top_20_holders, mint_address, entropy_score
                FROM tokens
            ''')
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_all_addresses(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT address FROM tokens')
            return [row[0] for row in cursor.fetchall()]

    def update_token(self, address, update_data):
        """Update token data in database"""
        try:
            with self.get_connection() as conn:
                # Create the update SQL dynamically based on provided data
                update_fields = []
                values = []
                
                for key, value in update_data.items():
                    update_fields.append(f"{key} = ?")
                    values.append(value)
                
                # Add address to values for WHERE clause
                values.append(address)
                
                # Construct and execute update query
                update_sql = f"""
                    UPDATE tokens 
                    SET {', '.join(update_fields)}
                    WHERE address = ?
                """
                
                conn.execute(update_sql, values)
                conn.commit()
                print(f"Successfully updated token in database: {address}")
        except Exception as e:
            print(f"Error updating token in database: {address}, {str(e)}")

    def delete_token(self, address):
        """Delete a token from the database"""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM tokens WHERE address = ?', (address,))
                conn.commit()
        except Exception as e:
            print(f"Error deleting token {address}: {e}")

    def clear_database(self):
        """Clear all records from the tokens table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tokens")
                conn.commit()
        except Exception as e:
            print(f"Error clearing database: {e}")
            raise e