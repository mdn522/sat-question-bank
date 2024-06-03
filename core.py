import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple
from peewee import SqliteDatabase, Model, CharField, IntegerField, BooleanField, fn
import os

lru_cache_maxsize = 1024


# DB Connect
db = SqliteDatabase('data/index.db')
db.connect()


class Question(Model):
    q_id = CharField(unique=True)
    questionId = CharField(unique=True)
    skill_cd = CharField()
    score_band_range_cd = IntegerField()
    uId = CharField()
    program = CharField()
    external_id = CharField(null=True)
    primary_class_cd = CharField()
    difficulty = CharField()
    module = CharField()
    active = BooleanField()

    class Meta:
        database = db


@lru_cache(maxsize=lru_cache_maxsize)
def group_list():
    return [q.primary_class_cd for q in Question.select(Question.primary_class_cd).distinct().order_by(Question.primary_class_cd)]


@lru_cache(maxsize=lru_cache_maxsize)
def skill_list():
    return [q.skill_cd for q in Question.select(Question.skill_cd).distinct().order_by(Question.skill_cd)]


def get_key(
        module: str,
        group: Optional[str] = None,
        skill: Optional[str] = None,
        difficulty: Optional[Union[str, List[str]]] = None,
        active: Optional[str] = None,
        only_key: Optional[List[str]] = None,
        **kwargs
) -> str:
    # TODO rename primary_class_cd, skill_cd
    if module is None:
        module = 'all'

    if module not in ['english', 'math']:
        pass

    if group is None:
        group = 'all'

    if skill is None:
        skill = 'all'

    if difficulty is None:
        difficulty = 'all'

    if type(difficulty) == str and difficulty != 'all':
        difficulty = [difficulty]

    if type(difficulty) == list:
        difficulty_new = []
        for diff in difficulty:
            if diff in ['E', 'M', 'H']:
                difficulty_new.append({'E': 'easy', 'M': 'medium', 'H': 'hard'}[diff])

        difficulty = difficulty_new

        difficulty = ','.join(difficulty)

    if active is None:
        active = 'all'
    elif active in [0, 1]:
        active = {0: 'non', 1: 'bluebook'}[active]

    key_list = [
        (module, 'module'),
        (group, 'group'),
        (skill, 'skill'),
        (difficulty, 'difficulty'),
        (active, 'active'),
    ]
    result = []
    for key in key_list:
        if only_key is not None and key[1] not in only_key:
            continue
        result.append(f"{key[1]}:{key[0]}")

    return '-'.join(result)
    # return f"module:{module}-class:{primary_class_cd}-skill:{skill_cd}-difficulty:{difficulty}-active:{active}"


def parse_key(key: str) -> Dict[str, Any]:
    filters_s = key.split('-')
    filter_dict = {}

    for filter_kv in filters_s:
        if not filter_kv or ':' not in filter_kv:
            continue

        filter_k, filter_v = filter_kv.split(':')
        if filter_k not in ['module', 'group', 'skill', 'difficulty', 'active']:
            continue

        if filter_k == 'module' and filter_v in ['english', 'math']:
            filter_dict[filter_k] = filter_v

        if filter_k == 'group' and filter_v in group_list():
            filter_dict[filter_k] = filter_v

        if filter_k == 'skill' and filter_v in skill_list():
            filter_dict[filter_k] = filter_v

        if filter_k == 'difficulty':
            filter_dict[filter_k] = []
            filter_v = filter_v.split(',')
            for v in filter_v:
                if v not in ['easy', 'medium', 'hard']:
                    continue
                filter_dict[filter_k].append({'easy': 'E', 'medium': 'M', 'hard': 'H'}[v])

            if len(filter_dict[filter_k]) == 3:
                filter_dict[filter_k] = 'all'
            if len(filter_dict[filter_k]) == 0:
                del filter_dict[filter_k]

        # print(filter_k, filter_v)
        if filter_k == 'active' and filter_v in ['bluebook', 'non']:
            filter_dict[filter_k] = {'bluebook': 1, 'non': 0}[filter_v]

    # print('filter_dict', filter_dict)
    return filter_dict


def key_to_query_filter(key: str):
    filter_dict = parse_key(key)

    where = []
    for k, v in filter_dict.items():
        # print('key_to_query_filter', k, v)
        if k == 'module':
            where.append(Question.module == v)
        if k == 'group':
            where.append(Question.primary_class_cd == v)
        if k == 'skill':
            where.append(Question.skill_cd == v)
        if k == 'difficulty':
            if v == 'all':
                continue
            else:
                where.append(Question.difficulty.in_(v))
        if k == 'active':
            # print('active', v)
            where.append(Question.active == v)
    # print('where', where)
    return where


def get_categories(key: str = '') -> List[Any]:
    filter_dict = parse_key(key)
    filter_dict = {k: v for k, v in filter_dict.items() if k in ['active', 'difficulty']}
    key = get_key(module=None, **filter_dict)

    # print('get_categories', key)

    @lru_cache(maxsize=lru_cache_maxsize)
    def get(key):
        # print('get key', key)
        where = key_to_query_filter(key) or [None]

        question_module_counts = (
            Question.select(
                Question.module,
                fn.COUNT().alias('count'),
                Question.questionId.alias('first_question_id'),
            )
            .where(*where)
            .order_by(Question.module)
            .group_by(Question.module)
        )

        question_group_counts = (
            Question.select(
                Question.module,
                Question.primary_class_cd,
                fn.COUNT().alias('count'),
                Question.questionId.alias('first_question_id')
            )
            .where(*where)
            .order_by(Question.module, Question.primary_class_cd)
            .group_by(Question.primary_class_cd)
        )

        question_skill_counts = (
            Question.select(
                Question.module,
                Question.primary_class_cd,
                Question.skill_cd,
                fn.COUNT().alias('count'),
                Question.questionId.alias('first_question_id')
            )
            .where(*where)
            .order_by(Question.module, Question.primary_class_cd, Question.skill_cd)
            .group_by(Question.primary_class_cd, Question.skill_cd)
        )

        # merge the results
        question_module_counts = list(question_module_counts)
        question_group_counts = list(question_group_counts)
        question_skill_counts = list(question_skill_counts)
        # combine the results side by side

        # Loop through the results
        cat_module = {}
        cat_group = {}
        cat_skill = {}
        cats = []

        for question in question_module_counts:
            # print(f"Module: {question.module}, Count: {question.count}")
            cat_module[question.module] = {
                'count': question.count,
                'first_question_id': question.first_question_id,
            }

        for question in question_group_counts:
            # print(f"Module: {question.module}, Class: {question.primary_class_cd}, Count: {question.count}")
            cat_group[question.primary_class_cd] = {
                'count': question.count,
                'first_question_id': question.first_question_id,
            }

        for question in question_skill_counts:
            # print(f"Module: {question.module}, Class: {question.primary_class_cd}, Skill: {question.skill_cd}, Count: {question.count}")
            cat_skill[question.skill_cd] = {
                'count': question.count,
                'first_question_id': question.first_question_id,
            }
            cats.append({
                'module': question.module,
                'module_count': cat_module[question.module]['count'],
                'module_first_question_id': cat_module[question.module]['first_question_id'],

                'group': question.primary_class_cd,
                'group_count': cat_group[question.primary_class_cd]['count'],
                'group_first_question_id': cat_group[question.primary_class_cd]['first_question_id'],

                'skill': question.skill_cd,
                'skill_count': cat_skill[question.skill_cd]['count'],
                'skill_first_question_id': cat_skill[question.skill_cd]['first_question_id'],
            })

        return cats

    return get(key)


@lru_cache(maxsize=lru_cache_maxsize)
def get_questions_id(filter_s: str = '') -> List[Tuple[str, str]]:
    query = Question.select(Question.questionId, Question.uId).where(
        *(key_to_query_filter(filter_s) or [None])
    )
    return [(q.uId, q.questionId) for q in query]


@lru_cache(maxsize=lru_cache_maxsize)
def get_questions_count(filter_s: str = '') -> int:
    return Question.select(Question.questionId).where(
        *(key_to_query_filter(filter_s) or [None])
    ).count()
