import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional, Union, Tuple

class DatabaseManagerAgent:
    """
    Agent for managing database operations (mock implementation).
    """
    def __init__(self, db_path: str = ":memory:"):
        self.logger = logging.getLogger("DatabaseManagerAgent")
        self.db_path = db_path
        self.connection = None
        self.connect()
        
    def __enter__(self):
        """Support for context manager pattern with 'with' statement"""
        if not self.connection:
            self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context manager"""
        self.disconnect()
        return False  # Don't suppress exceptions

    def connect(self):
        """Connect to the database"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.logger.info(f"Connected to database at {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed")

    def run_query(self, query: str, params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None) -> Dict[str, Any]:
        """
        Execute an SQL query and return the results
        
        Args:
            query: SQL query string
            params: Optional parameters for parameterized queries (dict, list, or tuple)
            
        Returns:
            Dictionary with query results or error information
        """
        self.logger.info(f"Running query: {query}")
        
        # Ensure connection is valid
        if self.connection is None:
            if not self.connect() or self.connection is None:
                self.logger.error("Database connection is None after connect()")
                return {"success": False, "error": "Database connection failed"}
        
        cursor = None
        try:
            if self.connection is None:
                self.logger.error("Database connection lost before query execution")
                return {"success": False, "error": "Database connection lost"}
            cursor = self.connection.cursor()
            
            # Execute the query with or without parameters
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            # Check if this is a SELECT query
            if query.strip().upper().startswith("SELECT"):
                # Fetch all rows and convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = []
                
                for row in rows:
                    result.append({columns[i]: row[i] for i in range(len(columns))})
                    
                self.logger.info(f"Query returned {len(result)} rows")
                return {
                    "success": True,
                    "rows": result,
                    "row_count": len(result)
                }
            else:
                # For non-SELECT queries, commit changes and return row count
                self.connection.commit()
                row_count = cursor.rowcount
                self.logger.info(f"Query affected {row_count} rows")
                return {
                    "success": True,
                    "affected_rows": row_count
                }
                
        except Exception as e:
            # Rollback transaction on error for non-SELECT queries
            if self.connection and not query.strip().upper().startswith("SELECT"):
                try:
                    self.connection.rollback()
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed: {rollback_error}")
                    
            self.logger.error(f"Query execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Close cursor if it was created
            if cursor:
                cursor.close()

    def create_table(self, table_name: str, columns: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create a new table in the database
        
        Args:
            table_name: Name of the table to create
            columns: List of column definitions [{"name": "id", "type": "INTEGER PRIMARY KEY"}, ...]
            
        Returns:
            Success or error information
        """
        try:
            # Build the CREATE TABLE statement
            column_defs = ", ".join([f"{col['name']} {col['type']}" for col in columns])
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
            
            return self.run_query(query)
            
        except Exception as e:
            self.logger.error(f"Table creation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def health_check(self) -> bool:
        """
        Check if the database connection is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to execute a simple query to check connection
            if not self.connection:
                if not self.connect():
                    return False
            
            cursor = None
            try:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
            finally:
                if cursor:
                    cursor.close()
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
            
    def __del__(self):
        """Destructor to ensure connection is closed when object is destroyed"""
        self.disconnect()
