from enum import Enum


class CategoryFilter(str, Enum):
    SCIENCE = 'Наука'
    EDUCATION = 'Образование'
    STUDENTS = 'Студентам'
    CAMPUS = 'Кампус'
    ALL = 'ВСЕ'


class SourceFilter(str, Enum):
    ITMO = 'ИТМО'
    HSE = 'НИУ ВШЭ'
    ALL = 'ВСЕ'
