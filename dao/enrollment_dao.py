from typing import List
import sqlite3


def list_students_in_class(conn: sqlite3.Connection, class_id: int) -> List[sqlite3.Row]:
	return conn.execute(
		"""
		SELECT s.id,
			   s.student_number,
			   s.legal_name,
			   s.display_name,
			   s.gender,
			   e.enrolled_at
		FROM enrollments e
		JOIN students s ON s.id = e.student_id
		WHERE e.class_id = ?
		ORDER BY s.student_number
		""",
		(class_id,),
	).fetchall()


def list_available_students_for_class(conn: sqlite3.Connection, class_id: int) -> List[sqlite3.Row]:
	return conn.execute(
		"""
		SELECT s.id,
			   s.student_number,
			   s.legal_name,
			   s.display_name,
			   s.gender
		FROM students s
		WHERE NOT EXISTS (
			SELECT 1
			FROM enrollments e
			WHERE e.class_id = ?
			  AND e.student_id = s.id
		)
		ORDER BY s.student_number
		""",
		(class_id,),
	).fetchall()


def enroll_student(conn: sqlite3.Connection, class_id: int, student_id: int) -> None:
	cursor = conn.execute(
		"""
		INSERT OR IGNORE INTO enrollments (student_id, class_id)
		VALUES (?, ?)
		""",
		(student_id, class_id),
	)

	if cursor.rowcount > 0:
		_insert_enrollment_log(
			conn,
			student_id=student_id,
			class_id=class_id,
			event_type='JOIN',
			operator_id='system',
			reason=None,
			source='web',
			request_id=None,
		)


def remove_student(conn: sqlite3.Connection, class_id: int, student_id: int) -> None:
	cursor = conn.execute(
		"""
		DELETE FROM enrollments
		WHERE class_id = ?
		  AND student_id = ?
		""",
		(class_id, student_id),
	)

	if cursor.rowcount > 0:
		_insert_enrollment_log(
			conn,
			student_id=student_id,
			class_id=class_id,
			event_type='LEAVE',
			operator_id='system',
			reason=None,
			source='web',
			request_id=None,
		)


def enroll_student_with_log(
	conn: sqlite3.Connection,
	*,
	class_id: int,
	student_id: int,
	operator_id: str,
	reason: str = None,
	source: str = 'web',
	request_id: str = None,
) -> bool:
	cursor = conn.execute(
		"""
		INSERT OR IGNORE INTO enrollments (student_id, class_id)
		VALUES (?, ?)
		""",
		(student_id, class_id),
	)

	created = cursor.rowcount > 0
	if created:
		_insert_enrollment_log(
			conn,
			student_id=student_id,
			class_id=class_id,
			event_type='JOIN',
			operator_id=operator_id,
			reason=reason,
			source=source,
			request_id=request_id,
		)
	return created


def remove_student_with_log(
	conn: sqlite3.Connection,
	*,
	class_id: int,
	student_id: int,
	operator_id: str,
	reason: str = None,
	source: str = 'web',
	request_id: str = None,
) -> bool:
	cursor = conn.execute(
		"""
		DELETE FROM enrollments
		WHERE class_id = ?
		  AND student_id = ?
		""",
		(class_id, student_id),
	)

	removed = cursor.rowcount > 0
	if removed:
		_insert_enrollment_log(
			conn,
			student_id=student_id,
			class_id=class_id,
			event_type='LEAVE',
			operator_id=operator_id,
			reason=reason,
			source=source,
			request_id=request_id,
		)
	return removed


def list_enrollment_logs_by_class(
	conn: sqlite3.Connection,
	class_id: int,
	limit: int = 50,
) -> List[sqlite3.Row]:
	return conn.execute(
		"""
		SELECT id,
			   student_id,
			   class_id,
			   event_type,
			   event_time,
			   operator_id,
			   reason,
			   source,
			   request_id,
			   student_number_snapshot,
			   student_name_snapshot
		FROM enrollment_logs
		WHERE class_id = ?
		ORDER BY id DESC
		LIMIT ?
		""",
		(class_id, limit),
	).fetchall()


def _insert_enrollment_log(
	conn: sqlite3.Connection,
	*,
	student_id: int,
	class_id: int,
	event_type: str,
	operator_id: str,
	reason: str,
	source: str,
	request_id: str,
) -> None:
	student = conn.execute(
		"""
		SELECT student_number, legal_name
		FROM students
		WHERE id = ?
		""",
		(student_id,),
	).fetchone()

	student_number_snapshot = student['student_number'] if student else None
	student_name_snapshot = student['legal_name'] if student else None

	conn.execute(
		"""
		INSERT INTO enrollment_logs (
			student_id,
			class_id,
			event_type,
			operator_id,
			reason,
			source,
			request_id,
			student_number_snapshot,
			student_name_snapshot
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
		""",
		(
			student_id,
			class_id,
			event_type,
			operator_id,
			reason,
			source,
			request_id,
			student_number_snapshot,
			student_name_snapshot,
		),
	)
