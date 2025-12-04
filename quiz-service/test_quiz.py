import unittest
import sqlite3
import os
import tempfile


class TestQuiz(unittest.TestCase):

    def setUp(self):
        self.db_file = tempfile.mktemp() + '.db'
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()

        # Create tables directly
        cursor.execute('''
            CREATE TABLE quizzes (
                id INTEGER PRIMARY KEY,
                course_id TEXT,
                title TEXT,
                questions_json TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE quiz_submissions (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                quiz_id INTEGER,
                course_id TEXT,
                answers_json TEXT,
                score INTEGER
            )
        ''')

        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_file)

    def test_database_setup(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('quizzes', tables)
        self.assertIn('quiz_submissions', tables)

    def test_insert_quiz(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO quizzes (course_id, title, questions_json) VALUES (?, ?, ?)",
            ('test-course', 'Test Quiz', '[{"id": 1, "question": "Test?"}]')
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM quizzes")
        quiz = cursor.fetchone()
        self.assertEqual(quiz[1], 'test-course')

    def test_insert_submission(self):
        cursor = self.conn.cursor()

        # Insert quiz first
        cursor.execute(
            "INSERT INTO quizzes (course_id, title, questions_json) VALUES (?, ?, ?)",
            ('test-course', 'Test Quiz', '[{"id": 1}]')
        )

        # Insert submission
        cursor.execute(
            "INSERT INTO quiz_submissions (user_id, quiz_id, course_id, answers_json, score) VALUES (?, ?, ?, ?, ?)",
            ('user123', 1, 'test-course', '{"1": 0}', 1)
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM quiz_submissions")
        submission = cursor.fetchone()
        self.assertEqual(submission[1], 'user123')


if __name__ == '__main__':
    unittest.main()