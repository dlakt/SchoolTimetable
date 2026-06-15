"""
Алгоритм составления школьного расписания
Использует жадный алгоритм с эвристиками для оптимального распределения
"""

import copy
import random
from datetime import datetime

class TimetableSolver:
    def __init__(self, data):
        self.data = data
        self.settings = data['settings']
        self.days = self.settings['days_per_week']
        self.lessons_per_day = self.settings['lessons_per_day']
        self.total_slots = self.days * self.lessons_per_day
        
        # Хранилище расписаний
        self.timetables = {}
        
        # Отслеживание занятости
        self.teacher_schedule = {}  # {teacher_id: {(day, lesson): subject}}
        self.classroom_schedule = {}  # {classroom_id: {(day, lesson): class_id}}
        
    def generate_timetable(self, class_id):
        """
        Генерация расписания для конкретного класса
        """
        class_info = next((c for c in self.data['classes'] if c['id'] == class_id), None)
        if not class_info:
            return {'timetable': [], 'stats': {'error': 'Класс не найден'}}
        
        # Получаем предметы для этого класса
        subjects = self._get_subjects_for_class(class_info)
        
        # Создаем расписание
        timetable = self._create_empty_timetable()
        
        # Сортируем предметы по приоритету (сложные предметы в первой половине дня)
        subjects = self._prioritize_subjects(subjects)
        
        # Жадное распределение
        for subject in subjects:
            hours_needed = subject['hours_per_week']
            placed = 0
            
            # Пытаемся поставить предмет в разные слоты
            for day in range(self.days):
                for lesson in range(self.lessons_per_day):
                    if placed >= hours_needed:
                        break
                    
                    if timetable[day][lesson] is None:
                        # Проверяем возможность поставить урок
                        if self._can_place_lesson(class_id, subject, day, lesson):
                            timetable[day][lesson] = {
                                'subject': subject['name'],
                                'teacher_id': subject['teacher_id'],
                                'teacher_name': self._get_teacher_name(subject['teacher_id']),
                                'classroom': self._get_best_classroom(subject['name']),
                                'day': day,
                                'lesson': lesson
                            }
                            
                            # Запоминаем занятость
                            self._mark_occupied(class_id, subject, day, lesson, timetable[day][lesson]['classroom'])
                            placed += 1
            
            # Если не удалось поставить все часы
            if placed < hours_needed:
                return {'timetable': [], 'stats': {
                    'error': f'Не удалось разместить предмет {subject["name"]}',
                    'placed': placed,
                    'needed': hours_needed
                }}
        
        # Вычисляем статистику
        stats = self._calculate_stats(timetable, class_info)
        
        # Сохраняем расписание
        self.timetables[class_id] = timetable
        
        return {
            'timetable': timetable,
            'stats': stats
        }
    
    def generate_all_timetables(self):
        """
        Генерация расписаний для всех классов
        """
        results = {}
        
        for class_info in self.data['classes']:
            # Сбрасываем занятость для каждого класса
            self._reset_schedules()
            result = self.generate_timetable(class_info['id'])
            results[class_info['id']] = {
                'class_name': class_info['name'],
                'success': 'error' not in result['stats'],
                'stats': result['stats']
            }
        
        return results
    
    def get_timetable(self, class_id):
        """
        Получить расписание для класса
        """
        if class_id not in self.timetables:
            self.generate_timetable(class_id)
        return self.timetables.get(class_id, [])
    
    def _get_subjects_for_class(self, class_info):
        """
        Получает список предметов для класса с учетом параллелей
        """
        subjects = []
        grade = class_info['grade']
        
        for subject in self.data['subjects']:
            # Проверяем, подходит ли предмет для этого класса
            if 'grades' in subject:
                if grade in subject['grades']:
                    subjects.append(copy.deepcopy(subject))
            else:
                # Предмет для всех классов
                subjects.append(copy.deepcopy(subject))
        
        return subjects
    
    def _prioritize_subjects(self, subjects):
        """
        Сортирует предметы по приоритету:
        - Сложные предметы (математика, физика, языки) - выше
        - Предметы с большим количеством часов - выше
        """
        priority_map = {
            'Математика': 10, 'Алгебра': 10, 'Русский язык': 9, 'Физика': 9,
            'Английский язык': 8, 'Химия': 8, 'История': 7, 'Литература': 7,
            'Биология': 6, 'Информатика': 6, 'География': 5, 'Обществознание': 5,
            'Физкультура': 3, 'ИЗО': 2, 'Музыка': 2, 'Труд': 2
        }
        
        for subject in subjects:
            priority = priority_map.get(subject['name'], 5)
            # Добавляем бонус за количество часов
            priority += subject['hours_per_week'] / 5
            subject['priority'] = priority
        
        subjects.sort(key=lambda x: x['priority'], reverse=True)
        return subjects
    
    def _create_empty_timetable(self):
        """
        Создает пустое расписание
        """
        return [[None for _ in range(self.lessons_per_day)] for _ in range(self.days)]
    
    def _can_place_lesson(self, class_id, subject, day, lesson):
        """
        Проверяет, можно ли поставить урок в указанный слот
        """
        # Проверка: учитель не занят
        teacher_key = (day, lesson)
        if subject['teacher_id'] in self.teacher_schedule:
            if teacher_key in self.teacher_schedule[subject['teacher_id']]:
                return False
        
        # Проверка: не слишком поздно для сложных предметов
        if lesson >= 4 and subject['priority'] > 7:  # После 5-го урока
            return False
        
        # Проверка: нет "окон" (предыдущий или следующий урок не пуст)
        # Это проверка будет позже, при оптимизации
        
        return True
    
    def _get_best_classroom(self, subject_name):
        """
        Выбирает подходящий кабинет для предмета
        """
        # Определяем тип кабинета для предмета
        classroom_type_map = {
            'Физика': 'physics',
            'Химия': 'chemistry',
            'Информатика': 'computer',
            'Физкультура': 'sport'
        }
        
        required_type = classroom_type_map.get(subject_name, 'regular')
        
        # Ищем свободный кабинет нужного типа
        for classroom in self.data['classrooms']:
            if classroom['type'] == required_type:
                return classroom['name']
        
        # Если нет специального, берем обычный
        for classroom in self.data['classrooms']:
            if classroom['type'] == 'regular':
                return classroom['name']
        
        return "Кабинет"
    
    def _mark_occupied(self, class_id, subject, day, lesson, classroom):
        """
        Отмечает занятость учителя и кабинета
        """
        # Отмечаем занятость учителя
        if subject['teacher_id'] not in self.teacher_schedule:
            self.teacher_schedule[subject['teacher_id']] = {}
        self.teacher_schedule[subject['teacher_id']][(day, lesson)] = subject['name']
        
        # Отмечаем занятость кабинета
        if classroom not in self.classroom_schedule:
            self.classroom_schedule[classroom] = {}
        self.classroom_schedule[classroom][(day, lesson)] = class_id
    
    def _reset_schedules(self):
        """
        Сбрасывает расписания занятости
        """
        self.teacher_schedule = {}
        self.classroom_schedule = {}
    
    def _get_teacher_name(self, teacher_id):
        """
        Получает имя учителя по ID
        """
        teacher = next((t for t in self.data['teachers'] if t['id'] == teacher_id), None)
        return teacher['name'] if teacher else f"Учитель {teacher_id}"
    
    def _calculate_stats(self, timetable, class_info):
        """
        Вычисляет статистику расписания
        """
        stats = {
            'total_lessons': 0,
            'windows': 0,  # "окна" в расписании
            'hard_subjects_morning': 0,  # Сложные предметы в первой половине
            'days_with_windows': 0,
            'quality_score': 0
        }
        
        hard_subjects = ['Математика', 'Алгебра', 'Физика', 'Русский язык', 'Английский язык']
        
        for day in range(self.days):
            day_lessons = []
            windows_in_day = 0
            
            for lesson in range(self.lessons_per_day):
                if timetable[day][lesson]:
                    stats['total_lessons'] += 1
                    day_lessons.append(True)
                    
                    # Проверяем, сложный ли предмет в первой половине
                    if lesson < 3 and timetable[day][lesson]['subject'] in hard_subjects:
                        stats['hard_subjects_morning'] += 1
                else:
                    day_lessons.append(False)
            
            # Подсчет "окон" (пустых уроков между занятиями)
            first_lesson = -1
            last_lesson = -1
            
            for i, has_lesson in enumerate(day_lessons):
                if has_lesson:
                    if first_lesson == -1:
                        first_lesson = i
                    last_lesson = i
            
            if first_lesson != -1:
                for i in range(first_lesson, last_lesson + 1):
                    if not day_lessons[i]:
                        windows_in_day += 1
                        stats['windows'] += 1
            
            if windows_in_day > 0:
                stats['days_with_windows'] += 1
        
        # Вычисляем оценку качества (0-100)
        # Штраф за окна
        window_penalty = min(50, stats['windows'] * 10)
        
        # Бонус за сложные предметы в первой половине
        morning_bonus = min(30, stats['hard_subjects_morning'] * 5)
        
        stats['quality_score'] = max(0, min(100, 70 - window_penalty + morning_bonus))
        
        # Добавляем информацию о классе
        stats['class_name'] = class_info['name']
        stats['student_count'] = class_info['student_count']
        
        return stats