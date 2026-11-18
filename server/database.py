"""
Database manager for SQLite3 message history, users, rooms, and audit logs.
Thread-safe, uses WAL mode, parameterized queries, and automatic migrations.
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages SQLite database connections, schema creation, and queries."""

    def __init__(self, db_path: str = "data/connect.db", default_room: str = "general"):
        self.db_path = db_path
        self.default_room = default_room
        self._lock = threading.Lock()
        
        # Ensure parent directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys and row factory."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def init_db(self) -> None:
        """Initializes tables and seeds default room if needed."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Rooms table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room_name TEXT UNIQUE NOT NULL COLLATE NOCASE,
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
                    );
                """)
                
                # Messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room_id INTEGER NOT NULL,
                        sender_id INTEGER NOT NULL,
                        message_content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
                        FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                """)
                
                # Index for quick history lookup
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_room_id_id 
                    ON messages(room_id, id);
                """)
                
                # Audit logs table (no sensitive data)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        event_type TEXT NOT NULL,
                        ip_address TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
                    );
                """)
                
                # Seed default room
                cursor.execute("SELECT id FROM rooms WHERE room_name = ? COLLATE NOCASE;", (self.default_room,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO rooms (room_name, created_by) VALUES (?, NULL);",
                        (self.default_room,)
                    )
                conn.commit()
        logger.info(f"Database initialized at {self.db_path} (Default room: #{self.default_room})")

    # ==================== User Operations ====================

    def create_user(self, username: str, password_hash: str, salt: str) -> Optional[int]:
        """
        Creates a new user record.
        Returns the new user ID, or None if username already exists.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?);",
                        (username.strip(), password_hash, salt)
                    )
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
            except Exception as e:
                logger.error(f"Error creating user {username}: {e}")
                return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves user by username (case-insensitive)."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, username, password_hash, salt, created_at FROM users WHERE username = ? COLLATE NOCASE;",
                        (username.strip(),)
                    )
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
            except Exception as e:
                logger.error(f"Error fetching user {username}: {e}")
                return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves user by ID."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, username, created_at FROM users WHERE id = ?;",
                        (user_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
            except Exception as e:
                logger.error(f"Error fetching user ID {user_id}: {e}")
                return None

    # ==================== Room Operations ====================

    def create_room(self, room_name: str, created_by_id: Optional[int] = None) -> Optional[int]:
        """
        Creates a new room.
        Returns the new room ID, or None if room already exists.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO rooms (room_name, created_by) VALUES (?, ?);",
                        (room_name.strip(), created_by_id)
                    )
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
            except Exception as e:
                logger.error(f"Error creating room {room_name}: {e}")
                return None

    def get_room_by_name(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves room record by name (case-insensitive)."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, room_name, created_by, created_at FROM rooms WHERE room_name = ? COLLATE NOCASE;",
                        (room_name.strip(),)
                    )
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
            except Exception as e:
                logger.error(f"Error fetching room {room_name}: {e}")
                return None

    def get_all_rooms(self) -> List[Dict[str, Any]]:
        """Returns list of all rooms with creator username."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT r.id, r.room_name, r.created_at, u.username AS created_by_username
                        FROM rooms r
                        LEFT JOIN users u ON r.created_by = u.id
                        ORDER BY r.id ASC;
                    """)
                    return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error listing rooms: {e}")
                return []

    # ==================== Message Operations ====================

    def save_message(
        self,
        room_name: str,
        sender_username: str,
        content: str,
        timestamp: Optional[str] = None
    ) -> Optional[int]:
        """
        Saves a message to the database.
        Returns the inserted message ID, or None on failure.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Fetch room ID
                    cursor.execute("SELECT id FROM rooms WHERE room_name = ? COLLATE NOCASE;", (room_name.strip(),))
                    room_row = cursor.fetchone()
                    if not room_row:
                        return None
                    room_id = room_row["id"]
                    
                    # Fetch sender ID
                    cursor.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE;", (sender_username.strip(),))
                    sender_row = cursor.fetchone()
                    if not sender_row:
                        return None
                    sender_id = sender_row["id"]
                    
                    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    
                    cursor.execute(
                        "INSERT INTO messages (room_id, sender_id, message_content, timestamp) VALUES (?, ?, ?, ?);",
                        (room_id, sender_id, content, ts)
                    )
                    conn.commit()
                    return cursor.lastrowid
            except Exception as e:
                logger.error(f"Error saving message in room {room_name}: {e}")
                return None

    def get_room_messages(
        self,
        room_name: str,
        limit: int = 50,
        before_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent messages for a room in chronological order.
        Supports pagination via before_id (for loading older messages).
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Get room ID
                    cursor.execute("SELECT id FROM rooms WHERE room_name = ? COLLATE NOCASE;", (room_name.strip(),))
                    room_row = cursor.fetchone()
                    if not room_row:
                        return []
                    room_id = room_row["id"]
                    
                    if before_id:
                        query = """
                            SELECT m.id, r.room_name, u.username AS sender, m.message_content AS content, m.timestamp
                            FROM messages m
                            JOIN rooms r ON m.room_id = r.id
                            JOIN users u ON m.sender_id = u.id
                            WHERE m.room_id = ? AND m.id < ?
                            ORDER BY m.id DESC
                            LIMIT ?;
                        """
                        cursor.execute(query, (room_id, before_id, limit))
                    else:
                        query = """
                            SELECT m.id, r.room_name, u.username AS sender, m.message_content AS content, m.timestamp
                            FROM messages m
                            JOIN rooms r ON m.room_id = r.id
                            JOIN users u ON m.sender_id = u.id
                            WHERE m.room_id = ?
                            ORDER BY m.id DESC
                            LIMIT ?;
                        """
                        cursor.execute(query, (room_id, limit))
                        
                    rows = cursor.fetchall()
                    # Return in chronological order (oldest first in the retrieved batch)
                    messages = [dict(row) for row in reversed(rows)]
                    return messages
            except Exception as e:
                logger.error(f"Error retrieving messages for room {room_name}: {e}")
                return []

    # ==================== Audit Operations ====================

    def log_audit_event(self, user_id: Optional[int], event_type: str, ip_address: Optional[str] = None) -> None:
        """Logs security and connection events without sensitive credentials."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO audit_logs (user_id, event_type, ip_address) VALUES (?, ?, ?);",
                        (user_id, event_type, ip_address)
                    )
                    conn.commit()
            except Exception as e:
                logger.error(f"Error logging audit event {event_type}: {e}")
