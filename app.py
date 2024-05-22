from collections import defaultdict
from typing import List

from flask import Flask, render_template
import json
from pathlib import Path
from diskcache import Index

app = Flask(__name__)

db_path = Path(__file__).parent / Path(r"data/cb-digital-questions.json")
with db_path.open(encoding='utf-8') as fp:
    questions = json.load(fp)


question_id_map = {}
categories = {}
categories_questions_id = defaultdict(list)
categories_counts = defaultdict(int)
categories_first_question_id = {}
module_count = defaultdict(int)

for q_id, q in questions.items():
    question_id_map[q['questionId']] = q_id


def load_categories():
    global categories

    for q_id, q_meta in questions.items():
        if q_meta['primary_class_cd'] not in categories:
            categories[q_meta['primary_class_cd']] = {
                'id': q_meta['primary_class_cd'],
                'name': q_meta['primary_class_cd_desc'],
                'count': 0,
                'categories': {},
                'questions_id': [],
                'module': q_meta['module'],
            }

        if q_meta['skill_cd'] not in categories[q_meta['primary_class_cd']]['categories']:
            categories[q_meta['primary_class_cd']]['categories'][q_meta['skill_cd']] = {
                'id': q_meta['skill_cd'],
                'name': q_meta['skill_desc'],
                'count': 0,
                'questions_id': []
            }

        categories[q_meta['primary_class_cd']]['count'] += 1
        categories[q_meta['primary_class_cd']]['categories'][q_meta['skill_cd']]['count'] += 1

        categories_questions_id[q_meta['primary_class_cd']].append([q_id, q_meta['questionId']])
        categories_counts[q_meta['primary_class_cd']] += 1
        categories_questions_id[q_meta['primary_class_cd'] + '-' + q_meta['skill_cd']].append([q_id, q_meta['questionId']])
        categories_counts[q_meta['primary_class_cd'] + '-' + q_meta['skill_cd']] += 1
        if q_meta['primary_class_cd'] not in categories_first_question_id:
            categories_first_question_id[q_meta['primary_class_cd']] = q_meta['questionId']

        module_count[q_meta['module']] += 1

        if (q_meta['primary_class_cd'] + '-' + q_meta['skill_cd']) not in categories_first_question_id:
            categories_first_question_id[q_meta['primary_class_cd'] + '-' + q_meta['skill_cd']] = q_meta['questionId']

        # categories[q_meta['primary_class_cd']]['questions_id'].append([q_id, q_meta['questionId']])
        # categories[q_meta['primary_class_cd']]['categories'][q_meta['skill_cd']]['questions_id'].append([q_id, q_meta['questionId']])


load_categories()

@app.route("/")
def index():
    # redirect
    return categories_page()
    # return "<p>Hello, World!</p>"


@app.route("/categories")
def categories_page():
    return render_template('categories.html', categories=categories, categories_first_question_id=categories_first_question_id, module_count=module_count)


@app.route('/question/<question_id>')
def question_page(question_id):
    if question_id not in question_id_map:
        return "Question not found", 404

    question_id = question_id_map[question_id]
    question = questions[question_id]

    # questions_id: List[List[str, str]] = categories[question['primary_class_cd']]['categories'][question['skill_cd']]['questions_id']
    category = question['primary_class_cd'] + '-' + question['skill_cd']
    questions_id: List[List[str, str]] = categories_questions_id[category]

    question_index = [d[0] for d in questions_id].index(question_id)
    next_question_id = None
    if question_index < len(questions_id) - 1:
        next_question_id = questions_id[question_index + 1][1]

    questions_count = categories[question['primary_class_cd']]['categories'][question['skill_cd']]['count']
    current_question_number = question_index + 1

    return render_template('question.html',
       question=question,
       next_question_id=next_question_id,
       questions_count=questions_count,
       current_question_number=current_question_number,
       category=category
    )


@app.route('/question/<category>/<question_id>')
def question_cat_page(category, question_id):
    if category not in categories_questions_id:
        return "Category not found", 404

    if question_id not in question_id_map:
        return "Question not found", 404

    question_id = question_id_map[question_id]
    question = questions[question_id]

    questions_id: List[List[str, str]] = categories_questions_id[category]

    print(questions_id)

    question_index = [d[0] for d in questions_id].index(question_id)
    next_question_id = None
    if question_index < len(questions_id) - 1:
        next_question_id = questions_id[question_index + 1][1]

    # questions_count = categories[question['primary_class_cd']]['categories'][question['skill_cd']]['count']
    questions_count = categories_counts[category]
    current_question_number = question_index + 1

    return render_template('question.html',
       question=question,
       next_question_id=next_question_id,
       questions_count=questions_count,
       current_question_number=current_question_number,
       questions_id=[[i + 1, q[1], questions[q[0]]['difficulty']] for i, q in enumerate(questions_id)],
       category=category,
    )