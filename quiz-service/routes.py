import logging
import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Quiz
from services.course_validator import CourseValidator
from services.message_publisher import MessagePublisher
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

quiz_bp = Blueprint('quiz', __name__)

def calculate_quiz_score(quiz, answers):
    score = 0
    i = 0
    for q in quiz["questions"]:
        correct = q["answer_index"]
        if int(answers[i]) == correct:
            score += 1
        i += 1
    return score

def save_quiz_submission(db, user_id, quiz_id, course_id, answers, score):

    submission_id = str(uuid.uuid4())

    db.execute(
        """
        INSERT INTO quiz_submissions 
        (id, user_id, quiz_id, course_id, answers_json, score)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            submission_id,
            user_id,
            quiz_id,
            course_id,
            json.dumps(answers),
            score,
        ]
    )

    return submission_id


@quiz_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'quiz-service'}), 200


@quiz_bp.route('/quiz/<course_id>', methods=['GET'])
@jwt_required()
def get_quiz(course_id):
    try:
        user_id = get_jwt_identity()
        print(user_id)
        logger.info(f"User {user_id} requesting quiz for course {course_id}")

        # -----------------------------------------------------------
        # 1. Validate that the course actually exists in Course Service
        # -----------------------------------------------------------
        # course_validator = CourseValidator(current_app.config['COURSE_SERVICE_URL'])
        # is_valid = course_validator.validate_course_exists(course_id)

        # if not is_valid:
        #     # If Course Service does not find the course, return 404
        #     return jsonify({'error': 'Course not found or validation failed'}), 404

        # Get Turso database client
        db = current_app.db
        
        # -----------------------------------------------------------
        # 2. Check if a quiz already exists for this course in the DB
        # -----------------------------------------------------------
        result = db.execute(
            "SELECT id, course_id, title, questions_json FROM quizzes WHERE course_id = ?",
            [course_id]
        )
        row = result.rows[0] if result.rows else None

        # -----------------------------------------------------------
        # 3. If no quiz exists yet → Automatically create a default quiz
        # -----------------------------------------------------------
        if not row:
            quiz = create_default_quiz(course_id)

            # Insert newly created quiz into Turso
            db.execute(
                "INSERT INTO quizzes (course_id, title, questions_json) VALUES (?, ?, ?)",
                [
                    quiz["course_id"],
                    quiz["title"],
                    json.dumps(quiz["questions"])  # Store questions as JSON text
                ]
            )

            # Query again to retrieve the inserted quiz record
            result = db.execute(
                "SELECT id, course_id, title, questions_json FROM quizzes WHERE course_id = ?",
                [course_id]
            )
            row = result.rows[0]

        # -----------------------------------------------------------
        # 4. Build the final JSON response for the client
        # -----------------------------------------------------------
        response_data = {
            "quiz_id": row["id"],
            "course_id": row["course_id"],
            "title": row["title"],
            "questions": json.loads(row["questions_json"])  # Convert JSON string back to list
        }

        logger.info(f"Quiz retrieved successfully for course {course_id}")
        return jsonify(response_data), 200

    except Exception as e:
        # Catch-all error logging for debugging
        logger.error(f"Error getting quiz for course {course_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@quiz_bp.route('/quiz/submit', methods=['POST'])
def submit_quiz():
    try:
        data = request.get_json()
        quiz = data["quiz"]
        answers = data["answers"]

        print(quiz, data["user_id"])

        # 1. count the score
        score = calculate_quiz_score(quiz, answers)

        # 2. save to turso
        submission_id = save_quiz_submission(
            db=current_app.db,
            user_id=data["user_id"],
            quiz_id=quiz["quiz_id"],
            course_id=quiz["course_id"],
            answers=answers,
            score=score
        )

        # Publish event
        try:
            publisher = MessagePublisher(current_app.config['RABBITMQ_URL'])
            event_data = {
                'event_type': 'quiz_submitted',
                'user_id': data["user_id"],
                'course_id': quiz["course_id"],
                'quiz_id': quiz["quiz_id"],
                'score': score,
                'timestamp': datetime.utcnow().isoformat()
            }
            publisher.publish_quiz_event(event_data)
            logger.info(f"Quiz submission event published for user {data['user_id']}")
        except Exception as e:
            logger.error(f"Failed to publish quiz event: {str(e)}")

        return jsonify({
            "submission_id": submission_id,
            "score": score,
            "total_questions": len(quiz["questions"]),
            "percentage": round((score / len(quiz["questions"])) * 100, 2)
        }), 200

    except Exception as e:
        logger.error(f"Error submitting quiz: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def create_default_quiz(course_id):
    quiz = Quiz()
    quiz.course_id = course_id
    quiz.title = f'Quiz for Course {course_id}'

    # Course-specific questions based on your data
    if 'python' in course_id.lower() or 'beginner' in course_id.lower():
        quiz.questions = [
            {
                'id': 1,
                'question': 'What is Python primarily used for?',
                'options': ['Web development', 'Data analysis', 'Automation', 'All of the above'],
                'answer_index': 3
            },
            {
                'id': 2,
                'question': 'Which keyword is used to define a function in Python?',
                'options': ['function', 'def', 'func', 'define'],
                'answer_index': 1
            },
            {
                'id': 3,
                'question': 'What is the correct way to create a list in Python?',
                'options': ['list = {}', 'list = []', 'list = ()', 'list = <>'],
                'answer_index': 1
            },
            {
                'id': 4,
                'question': 'How do you start building projects in Python?',
                'options': ['Learn syntax first', 'Start with fundamentals', 'Jump into frameworks',
                            'Copy existing code'],
                'answer_index': 1
            },
            {
                'id': 5,
                'question': 'What is indentation used for in Python?',
                'options': ['Decoration', 'Code blocks', 'Comments', 'Variables'],
                'answer_index': 1
            },
            {
                'id': 6,
                'question': 'Which data type is mutable in Python?',
                'options': ['String', 'Tuple', 'List', 'Integer'],
                'answer_index': 2
            },
            {
                'id': 7,
                'question': 'What does "building projects today" mean for beginners?',
                'options': ['Advanced projects only', 'Start with simple scripts', 'Enterprise applications',
                            'Complex algorithms'],
                'answer_index': 1
            },
            {
                'id': 8,
                'question': 'Python fundamentals include understanding what?',
                'options': ['Variables and functions', 'Machine learning only', 'Web frameworks only',
                            'Database design'],
                'answer_index': 0
            },
            {
                'id': 9,
                'question': 'What makes Python good for absolute beginners?',
                'options': ['Complex syntax', 'Readable syntax', 'No documentation', 'Requires compilation'],
                'answer_index': 1
            },
            {
                'id': 10,
                'question': 'The best way to master Python fundamentals is to?',
                'options': ['Read only', 'Practice coding', 'Watch videos only', 'Memorize syntax'],
                'answer_index': 1
            }
        ]
    elif 'react' in course_id.lower() or 'frontend' in course_id.lower():
        quiz.questions = [
            {
                'id': 1,
                'question': 'What is React primarily used for?',
                'options': ['Backend development', 'Frontend development', 'Database management',
                            'Server configuration'],
                'answer_index': 1
            },
            {
                'id': 2,
                'question': 'React applications are described as what type?',
                'options': ['Static', 'High-performance', 'Low-performance', 'Backend-only'],
                'answer_index': 1
            },
            {
                'id': 3,
                'question': 'What does "modern web applications" mean in React context?',
                'options': ['Old techniques', 'Current best practices', 'Outdated methods', 'Server-side only'],
                'answer_index': 1
            },
            {
                'id': 4,
                'question': 'React is used for building what kind of web applications?',
                'options': ['Simple static pages', 'Modern, high-performance apps', 'Basic HTML sites',
                            'Text-only pages'],
                'answer_index': 1
            },
            {
                'id': 5,
                'question': 'What is JSX in React?',
                'options': ['A database', 'JavaScript XML', 'A server', 'A CSS framework'],
                'answer_index': 1
            },
            {
                'id': 6,
                'question': 'Frontend development with React focuses on?',
                'options': ['Server logic', 'User interfaces', 'Database queries', 'Network protocols'],
                'answer_index': 1
            },
            {
                'id': 7,
                'question': 'High-performance in React means?',
                'options': ['Slow rendering', 'Fast, efficient UIs', 'Large file sizes', 'Complex setup'],
                'answer_index': 1
            },
            {
                'id': 8,
                'question': 'Modern React development emphasizes?',
                'options': ['Old browsers only', 'Component-based architecture', 'Inline styles only',
                            'Table-based layouts'],
                'answer_index': 1
            },
            {
                'id': 9,
                'question': 'React applications are built using?',
                'options': ['Only HTML', 'Components and state', 'Only CSS', 'Only JavaScript'],
                'answer_index': 1
            },
            {
                'id': 10,
                'question': 'The goal of frontend React development is to?',
                'options': ['Build modern, efficient web applications', 'Replace all backends', 'Eliminate JavaScript',
                            'Avoid user interaction'],
                'answer_index': 0
            }
        ]
    elif 'data' in course_id.lower() or 'visualization' in course_id.lower():
        quiz.questions = [
            {
                'id': 1,
                'question': 'What is data analysis primarily used for?',
                'options': ['Web design', 'Extracting insights from data', 'Writing code', 'Database storage'],
                'answer_index': 1
            },
            {
                'id': 2,
                'question': 'Data visualization helps with?',
                'options': ['Hiding data patterns', 'Presenting insights clearly', 'Storing more data',
                            'Writing reports'],
                'answer_index': 1
            },
            {
                'id': 3,
                'question': 'Pandas is primarily used for?',
                'options': ['Web development', 'Data manipulation', 'Image processing', 'Audio editing'],
                'answer_index': 1
            },
            {
                'id': 4,
                'question': 'Matplotlib is a tool for?',
                'options': ['Data visualization', 'Web scraping', 'Database management', 'File compression'],
                'answer_index': 0
            },
            {
                'id': 5,
                'question': 'Powerful data insights come from?',
                'options': ['Ignoring patterns', 'Analyzing and visualizing data', 'Collecting more data',
                            'Random guessing'],
                'answer_index': 1
            },
            {
                'id': 6,
                'question': 'Data analysis helps businesses make?',
                'options': ['Random decisions', 'Data-driven decisions', 'Quick decisions', 'Expensive decisions'],
                'answer_index': 1
            },
            {
                'id': 7,
                'question': 'Visualization makes data more?',
                'options': ['Complicated', 'Understandable', 'Hidden', 'Confusing'],
                'answer_index': 1
            },
            {
                'id': 8,
                'question': 'Learning data analysis involves understanding?',
                'options': ['Only statistics', 'Data patterns and tools', 'Only programming', 'Only mathematics'],
                'answer_index': 1
            },
            {
                'id': 9,
                'question': 'The goal of data visualization is to?',
                'options': ['Make data harder to understand', 'Communicate insights effectively', 'Hide information',
                            'Complicate analysis'],
                'answer_index': 1
            },
            {
                'id': 10,
                'question': 'Data analysis and visualization together provide?',
                'options': ['Confusion', 'Powerful insights', 'More complexity', 'Less understanding'],
                'answer_index': 1
            }
        ]
    else:
        # Generic fallback for unknown courses
        quiz.questions = [
            {
                'id': i,
                'question': f'Question {i} about this course topic?',
                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                'answer_index': i % 4
            } for i in range(1, 11)
        ]

    return quiz


# def calculate_quiz_score(quiz, answers):
#     score = 0
#     questions = quiz.questions

#     for question in questions:
#         question_id = str(question['id'])
#         if question_id in answers:
#             user_answer = answers[question_id]
#             answer_index = question['answer_index']
#             if user_answer == answer_index:
#                 score += 1

#     return score