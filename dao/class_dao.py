from typing import List, Optional
import sqlite3


def list_classes_with_counts(conn: sqlite3.Connection) -> List[sqlite3.Row]:
	return conn.execute(
		"""
		SELECT c.id,
			   c.type,
			   c.level,
			   c.group_number,
			   c.status,
			   COUNT(e.student_id) AS student_count
		FROM classes c
		LEFT JOIN enrollments e ON e.class_id = c.id
		GROUP BY c.id, c.type, c.level, c.group_number, c.status
		ORDER BY c.id DESC
		"""
	).fetchall()


def create_class(
	conn: sqlite3.Connection,
	*,
	class_type: str,
	level: str,
	group_number: int,
	status: str = "active",
) -> int:
	cursor = conn.execute(
		"""
		INSERT INTO classes (type, level, group_number, status)
		VALUES (?, ?, ?, ?)
		""",
		(class_type.strip(), level.strip(), int(group_number), status.strip()),
	)
	return cursor.lastrowid


def get_class_by_id(conn: sqlite3.Connection, class_id: int) -> Optional[sqlite3.Row]:
	return conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
