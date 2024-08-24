from collections import defaultdict
from functools import partial
from typing import List, Tuple

from flask import Flask, render_template, redirect, request
import json
from pathlib import Path

import environ
from diskcache import Index

import core
from core import get_categories, get_questions_id, get_questions_count

env = environ.Env()

BASE_DIR = Path(__file__).resolve(strict=True).parent

READ_DOT_ENV_FILE = env.bool("READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

IS_BLACKOUT = env.bool('IS_BLACKOUT', default=False)

app = Flask(__name__)

data_path = Path(__file__).parent / 'data'
db_path = data_path / r"cb-digital-questions.json"
with db_path.open(encoding='utf-8') as fp:
    questions = json.load(fp)

with (data_path / r"lookup.json").open(encoding='utf-8') as fp:
    filter_data = json.load(fp)

    for k, v in [('mathLiveItems', 'math'), ('readingLiveItems', 'english')]:
        filter_data[v] = filter_data[k]
        del filter_data[k]


question_id_map = {}
# categories = {}
# categories_questions_id = defaultdict(list)
# categories_counts = defaultdict(int)
# categories_first_question_id = {}
module_count = defaultdict(int)
terms = {}


for q_id, q in questions.items():
    question_id_map[q['questionId']] = q_id


for q_id, q_meta in questions.items():
    if q_meta['module'] not in terms:
        terms[q_meta['module']] = q_meta['module'].title()

    if q_meta['primary_class_cd'] not in terms:
        terms[q_meta['primary_class_cd']] = q_meta['primary_class_cd_desc']

    if q_meta['skill_cd'] not in terms:
        terms[q_meta['skill_cd']] = q_meta['skill_desc']

    if q_meta['difficulty'] not in terms:
        terms[q_meta['difficulty']] = {'E': 'Easy', 'M': 'Medium', 'H': 'Hard'}[q_meta['difficulty']]


def load_categories():
    global categories

    # q_filter_cd = {
    #     'all': 'A',
    #     'bluebook': 'BO',
    #     'non': 'NB',
    # }

    for q_id, q_meta in questions.items():
        # q_difficulty = q_meta['difficulty']
        # q_active = ['all']
        # q_active.append('bluebook-only' if q_id in filter_data[q_meta['module']] else 'non-bluebook')

        # question keys
        # module -> class -> skill -> difficulty -> active

        # keys = {
        #     'module': q_meta['module'][0].upper(),
        #     'difficulty': q_difficulty,
        #     'class': q_meta['primary_class_cd'],
        #     'skill': q_meta['skill_cd'],
        #     'active': ['all'] + ['bluebook-only' if q_id in filter_data[q_meta['module']] else 'non-bluebook']
        # }
        #
        # key_module = q_meta['module'][0].upper()
        # key_module__difficulty = key_module + '-' + q_difficulty
        # key_class = key_module + '-' + q_meta['primary_class_cd']
        # key_class__difficulty = key_class + '-' + q_difficulty
        # key_skill = key_class + '-' + q_meta['skill_cd']
        # key_skill__difficulty = key_skill + '-' + q_difficulty
        # keys = [
        #     ['module'],
        #     ['module', 'difficulty'],
        #     ['module', 'difficulty', 'active'],
        #     ['module', 'active'],
        # ]

        # Maybe legacy code
        # if q_meta['primary_class_cd'] not in categories:
        #     categories[q_meta['primary_class_cd']] = {
        #         'id': q_meta['primary_class_cd'],
        #         'name': q_meta['primary_class_cd_desc'],
        #         'count': 0,
        #         'categories': {},
        #         'questions_id': [],
        #         'module': q_meta['module'],
        #     }
        #
        # # Legacy code
        # if q_meta['skill_cd'] not in categories[q_meta['primary_class_cd']]['categories']:
        #     categories[q_meta['primary_class_cd']]['categories'][q_meta['skill_cd']] = {
        #         'id': q_meta['skill_cd'],
        #         'name': q_meta['skill_desc'],
        #         'count': 0,
        #         'questions_id': []
        #     }
        #
        # # Legacy code
        # categories[q_meta['primary_class_cd']]['count'] += 1
        # categories[q_meta['primary_class_cd']]['categories'][q_meta['skill_cd']]['count'] += 1
        #
        # module_count[q_meta['module']] += 1
        #
        # # for key in [key_module, key_module__difficulty, key]
        #
        # categories_questions_id[key_class].append([q_id, q_meta['questionId']])
        # categories_counts[key_class] += 1
        #
        # if key_class not in categories_first_question_id:
        #     categories_first_question_id[key_class] = q_meta['questionId']
        #
        # categories_questions_id[key_skill].append([q_id, q_meta['questionId']])
        # categories_counts[key_skill] += 1
        #
        # if key_skill not in categories_first_question_id:
        #     categories_first_question_id[key_skill] = q_meta['questionId']

        # categories[q_meta['primary_class_cd']]['questions_id'].append([q_id, q_meta['questionId']])
        # categories[q_meta['primary_class_cd']]['categories'][q_meta['skill_cd']]['questions_id'].append([q_id, q_meta['questionId']])
        pass


# load_categories()


@app.context_processor
def utility_processor():
    return dict(
        get_key=core.get_key,
        parse_key=core.parse_key,
        IS_BLACKOUT=IS_BLACKOUT
    )


@app.route("/")
def index():
    return redirect("/categories")


@app.route("/categories", defaults={'q_filter': ''})
@app.route("/categories/<q_filter>/")
def categories_page(q_filter):
    categories = get_categories(q_filter)
    module_count = {c['module']: c['module_count'] for c in categories}
    module_first_question_id = {c['module']: c['module_first_question_id'] for c in categories}
    filter_dict = core.parse_key(q_filter)
    # print(module_count)
    cat_get_key = partial(core.get_key, **filter_dict, module=None, only_key=['active', 'difficulty'])

    return render_template(
        'categories.html', 
        categories=categories, 
        # categories_first_question_id=questions_id(q_filter),
        module_count=module_count,
        module_first_question_id=module_first_question_id,
        terms=terms,
        filter_dict=filter_dict,
        filter_s=q_filter,
        cat_get_key=cat_get_key
    )


# @app.route('/question/<question_id>')
# def question_page(question_id):
#     if question_id not in question_id_map:
#         return "Question not found", 404
# 
#     question_id = question_id_map[question_id]
#     question = questions[question_id]
# 
#     # questions_id: List[List[str, str]] = categories[question['primary_class_cd']]['categories'][question['skill_cd']]['questions_id']
#     category = question['primary_class_cd'] + '-' + question['skill_cd']
#     questions_id: List[List[str, str]] = categories_questions_id[category]
# 
#     question_index = [d[0] for d in questions_id].index(question_id)
#     next_question_id = None
#     if question_index < len(questions_id) - 1:
#         next_question_id = questions_id[question_index + 1][1]
# 
#     questions_count = categories[question['primary_class_cd']]['categories'][question['skill_cd']]['count']
#     current_question_number = question_index + 1
# 
#     return render_template('question.html',
#        question=question,
#        next_question_id=next_question_id,
#        questions_count=questions_count,
#        current_question_number=current_question_number,
#        category=category
#     )


@app.route('/question/<q_filter>/<question_id>')
def question_page(q_filter, question_id):
    if question_id not in question_id_map:
        return "Question not found", 404

    filter_dict = core.parse_key(q_filter)

    question_id = question_id_map[question_id]
    question = questions[question_id]

    questions_id: List[Tuple[str, str]] = get_questions_id(q_filter)

    # print(q_filter, question_id, len(questions_id), questions_id)

    try:
        question_index = [d[0] for d in questions_id].index(question_id)
    except ValueError:
        # print('Question not found in filter', question_id, q_filter)
        question_index = None

    next_question_id = None
    if question_index is not None and question_index < len(questions_id) - 1:
        next_question_id = questions_id[question_index + 1][1]

    questions_count = get_questions_count(q_filter)
    current_question_number = None
    if question_index is not None and question_index >= 0:
        current_question_number = question_index + 1

    return render_template(
        'question.html',
        question=question,
        next_question_id=next_question_id,
        questions_count=questions_count,
        current_question_number=current_question_number,
        questions_id=[[i + 1, q[1], questions[q[0]]['difficulty']] for i, q in enumerate(questions_id)],
        category='',  # TODO
        terms=terms,
        filter_dict=filter_dict,
        filter_s=q_filter,
    )


# @app.route('/question/<category>/<question_id>')
# def question_cat_page(category, question_id):
#     if category not in categories_questions_id:
#         return "Category not found", 404
#
#     if question_id not in question_id_map:
#         return "Question not found", 404
#
#     question_id = question_id_map[question_id]
#     question = questions[question_id]
#
#     questions_id: List[List[str, str]] = categories_questions_id[category]
#
#     # print(questions_id)
#
#     question_index = [d[0] for d in questions_id].index(question_id)
#     next_question_id = None
#     if question_index < len(questions_id) - 1:
#         next_question_id = questions_id[question_index + 1][1]
#
#     # questions_count = categories[question['primary_class_cd']]['categories'][question['skill_cd']]['count']
#     questions_count = categories_counts[category]
#     current_question_number = question_index + 1
#
#     return render_template(
#         'question.html',
#         question=question,
#         next_question_id=next_question_id,
#         questions_count=questions_count,
#         current_question_number=current_question_number,
#         questions_id=[[i + 1, q[1], questions[q[0]]['difficulty']] for i, q in enumerate(questions_id)],
#         category=category,
#     )
