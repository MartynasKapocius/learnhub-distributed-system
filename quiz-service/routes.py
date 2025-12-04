import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Quiz, QuizSubmission, db
from services.course_validator import CourseValidator
from services.message_publisher import MessagePublisher

logger = logging.getLogger(__name__)

quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'quiz-service'}), 200


@quiz_bp.route('/quiz/<course_id>', methods=['GET'])
@jwt_required()
def get_quiz(course_id):
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} requesting quiz for course {course_id}")

        # Validate course exists
        course_validator = CourseValidator(current_app.config['COURSE_SERVICE_URL'])
        is_valid = course_validator.validate_course_exists(course_id)

        if not is_valid:
            return jsonify({'error': 'Course not found or validation failed'}), 404

        # Get or create quiz
        quiz = Quiz.query.filter_by(course_id=course_id).first()

        if not quiz:
            quiz = create_default_quiz(course_id)
            db.session.add(quiz)
            db.session.commit()

        response_data = {
            'quiz_id': str(quiz.id),
            'course_id': quiz.course_id,
            'title': quiz.title,
            'questions': quiz.questions
        }

        logger.info(f"Quiz retrieved successfully for course {course_id}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting quiz for course {course_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@quiz_bp.route('/quiz/submit', methods=['POST'])
@jwt_required()
def submit_quiz():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data or 'quiz_id' not in data or 'answers' not in data:
            return jsonify({'error': 'Missing quiz_id or answers'}), 400

        quiz_id = int(data['quiz_id'])
        answers = data['answers']

        logger.info(f"User {user_id} submitting quiz {quiz_id}")

        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return jsonify({'error': 'Quiz not found'}), 404

        # Calculate score
        score = calculate_quiz_score(quiz, answers)

        # Store submission
        submission = QuizSubmission(
            user_id=user_id,
            quiz_id=quiz_id,
            course_id=quiz.course_id,
            answers=answers,
            score=score
        )

        db.session.add(submission)
        db.session.commit()

        # Publish event
        try:
            publisher = MessagePublisher(current_app.config['RABBITMQ_URL'])
            event_data = {
                'event_type': 'quiz_submitted',
                'user_id': user_id,
                'course_id': quiz.course_id,
                'quiz_id': quiz_id,
                'score': score,
                'timestamp': datetime.utcnow().isoformat()
            }
            publisher.publish_quiz_event(event_data)
            logger.info(f"Quiz submission event published for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to publish quiz event: {str(e)}")

        response_data = {
            'submission_id': str(submission.id),
            'score': score,
            'total_questions': len(quiz.questions),
            'percentage': round((score / len(quiz.questions)) * 100, 2)
        }

        logger.info(f"Quiz submitted successfully by user {user_id}, score: {score}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error submitting quiz: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


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
                'correct_answer': 3
            },
            {
                'id': 2,
                'question': 'Which keyword is used to define a function in Python?',
                'options': ['function', 'def', 'func', 'define'],
                'correct_answer': 1
            },
            {
                'id': 3,
                'question': 'What is the correct way to create a list in Python?',
                'options': ['list = {}', 'list = []', 'list = ()', 'list = <>'],
                'correct_answer': 1
            },
            {
                'id': 4,
                'question': 'How do you start building projects in Python?',
                'options': ['Learn syntax first', 'Start with fundamentals', 'Jump into frameworks',
                            'Copy existing code'],
                'correct_answer': 1
            },
            {
                'id': 5,
                'question': 'What is indentation used for in Python?',
                'options': ['Decoration', 'Code blocks', 'Comments', 'Variables'],
                'correct_answer': 1
            },
            {
                'id': 6,
                'question': 'Which data type is mutable in Python?',
                'options': ['String', 'Tuple', 'List', 'Integer'],
                'correct_answer': 2
            },
            {
                'id': 7,
                'question': 'What does "building projects today" mean for beginners?',
                'options': ['Advanced projects only', 'Start with simple scripts', 'Enterprise applications',
                            'Complex algorithms'],
                'correct_answer': 1
            },
            {
                'id': 8,
                'question': 'Python fundamentals include understanding what?',
                'options': ['Variables and functions', 'Machine learning only', 'Web frameworks only',
                            'Database design'],
                'correct_answer': 0
            },
            {
                'id': 9,
                'question': 'What makes Python good for absolute beginners?',
                'options': ['Complex syntax', 'Readable syntax', 'No documentation', 'Requires compilation'],
                'correct_answer': 1
            },
            {
                'id': 10,
                'question': 'The best way to master Python fundamentals is to?',
                'options': ['Read only', 'Practice coding', 'Watch videos only', 'Memorize syntax'],
                'correct_answer': 1
            }
        ]
    elif 'react' in course_id.lower() or 'frontend' in course_id.lower():
        quiz.questions = [
            {
                'id': 1,
                'question': 'What is React primarily used for?',
                'options': ['Backend development', 'Frontend development', 'Database management',
                            'Server configuration'],
                'correct_answer': 1
            },
            {
                'id': 2,
                'question': 'React applications are described as what type?',
                'options': ['Static', 'High-performance', 'Low-performance', 'Backend-only'],
                'correct_answer': 1
            },
            {
                'id': 3,
                'question': 'What does "modern web applications" mean in React context?',
                'options': ['Old techniques', 'Current best practices', 'Outdated methods', 'Server-side only'],
                'correct_answer': 1
            },
            {
                'id': 4,
                'question': 'React is used for building what kind of web applications?',
                'options': ['Simple static pages', 'Modern, high-performance apps', 'Basic HTML sites',
                            'Text-only pages'],
                'correct_answer': 1
            },
            {
                'id': 5,
                'question': 'What is JSX in React?',
                'options': ['A database', 'JavaScript XML', 'A server', 'A CSS framework'],
                'correct_answer': 1
            },
            {
                'id': 6,
                'question': 'Frontend development with React focuses on?',
                'options': ['Server logic', 'User interfaces', 'Database queries', 'Network protocols'],
                'correct_answer': 1
            },
            {
                'id': 7,
                'question': 'High-performance in React means?',
                'options': ['Slow rendering', 'Fast, efficient UIs', 'Large file sizes', 'Complex setup'],
                'correct_answer': 1
            },
            {
                'id': 8,
                'question': 'Modern React development emphasizes?',
                'options': ['Old browsers only', 'Component-based architecture', 'Inline styles only',
                            'Table-based layouts'],
                'correct_answer': 1
            },
            {
                'id': 9,
                'question': 'React applications are built using?',
                'options': ['Only HTML', 'Components and state', 'Only CSS', 'Only JavaScript'],
                'correct_answer': 1
            },
            {
                'id': 10,
                'question': 'The goal of frontend React development is to?',
                'options': ['Build modern, efficient web applications', 'Replace all backends', 'Eliminate JavaScript',
                            'Avoid user interaction'],
                'correct_answer': 0
            }
        ]
    elif 'data' in course_id.lower() or 'visualization' in course_id.lower():
        quiz.questions = [
            {
                'id': 1,
                'question': 'What is data analysis primarily used for?',
                'options': ['Web design', 'Extracting insights from data', 'Writing code', 'Database storage'],
                'correct_answer': 1
            },
            {
                'id': 2,
                'question': 'Data visualization helps with?',
                'options': ['Hiding data patterns', 'Presenting insights clearly', 'Storing more data',
                            'Writing reports'],
                'correct_answer': 1
            },
            {
                'id': 3,
                'question': 'Pandas is primarily used for?',
                'options': ['Web development', 'Data manipulation', 'Image processing', 'Audio editing'],
                'correct_answer': 1
            },
            {
                'id': 4,
                'question': 'Matplotlib is a tool for?',
                'options': ['Data visualization', 'Web scraping', 'Database management', 'File compression'],
                'correct_answer': 0
            },
            {
                'id': 5,
                'question': 'Powerful data insights come from?',
                'options': ['Ignoring patterns', 'Analyzing and visualizing data', 'Collecting more data',
                            'Random guessing'],
                'correct_answer': 1
            },
            {
                'id': 6,
                'question': 'Data analysis helps businesses make?',
                'options': ['Random decisions', 'Data-driven decisions', 'Quick decisions', 'Expensive decisions'],
                'correct_answer': 1
            },
            {
                'id': 7,
                'question': 'Visualization makes data more?',
                'options': ['Complicated', 'Understandable', 'Hidden', 'Confusing'],
                'correct_answer': 1
            },
            {
                'id': 8,
                'question': 'Learning data analysis involves understanding?',
                'options': ['Only statistics', 'Data patterns and tools', 'Only programming', 'Only mathematics'],
                'correct_answer': 1
            },
            {
                'id': 9,
                'question': 'The goal of data visualization is to?',
                'options': ['Make data harder to understand', 'Communicate insights effectively', 'Hide information',
                            'Complicate analysis'],
                'correct_answer': 1
            },
            {
                'id': 10,
                'question': 'Data analysis and visualization together provide?',
                'options': ['Confusion', 'Powerful insights', 'More complexity', 'Less understanding'],
                'correct_answer': 1
            }
        ]
    else:
        # Generic fallback for unknown courses
        quiz.questions = [
            {
                'id': i,
                'question': f'Question {i} about this course topic?',
                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                'correct_answer': i % 4
            } for i in range(1, 11)
        ]

    return quiz


def calculate_quiz_score(quiz, answers):
    score = 0
    questions = quiz.questions

    for question in questions:
        question_id = str(question['id'])
        if question_id in answers:
            user_answer = answers[question_id]
            correct_answer = question['correct_answer']
            if user_answer == correct_answer:
                score += 1

    return score