from flask import Flask, render_template, request, jsonify
import json
import os
import random
from collections import defaultdict

app = Flask(__name__)

def load_data():
    path = 'data/school_data.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

data = load_data()

# Настройки
MAX_WINDOWS_PER_DAY = data.get('settings', {}).get('max_windows_per_day', 2)
SATURDAY_LESSONS = data.get('settings', {}).get('saturday_lessons', 3)  # до какого урока
SATURDAY_MAX = data.get('settings', {}).get('saturday_max_lessons', 2)  # максимум уроков в субботу

# Строим словари
subject_to_teacher = {}
teacher_room = {}
teacher_subjects = {}

for teacher in data.get('teachers', []):
    teacher_id = teacher['id']
    teacher_room[teacher_id] = teacher.get('room', 'Кабинет')
    teacher_subjects[teacher_id] = teacher.get('subjects', [])
    for subject in teacher.get('subjects', []):
        subject_to_teacher[subject] = teacher_id

def get_teacher_for_subject(subject_name):
    teacher_id = subject_to_teacher.get(subject_name)
    if teacher_id:
        for teacher in data.get('teachers', []):
            if teacher['id'] == teacher_id:
                return teacher
    return None

def get_teacher_name(teacher_id):
    for teacher in data.get('teachers', []):
        if teacher['id'] == teacher_id:
            return teacher['name']
    return f"Учитель {teacher_id}"

def count_windows_in_day(day_timetable):
    """Подсчитывает количество окон в одном дне"""
    windows = 0
    lessons = day_timetable
    first_lesson = -1
    last_lesson = -1
    
    for i, lesson in enumerate(lessons):
        if lesson is not None:
            if first_lesson == -1:
                first_lesson = i
            last_lesson = i
    
    if first_lesson != -1:
        for i in range(first_lesson, last_lesson + 1):
            if lessons[i] is None:
                windows += 1
    
    return windows

def generate_timetable_for_class(class_id):
    """Генерирует расписание для одного класса с ограничениями"""
    
    class_info = None
    for c in data.get('classes', []):
        if c['id'] == class_id:
            class_info = c
            break
    
    if not class_info:
        return []
    
    grade = class_info['grade']
    grade_str = str(grade)
    subjects_data = data.get('subjects_by_grade', {}).get(grade_str, [])
    
    if not subjects_data:
        return []
    
    days = data.get('settings', {}).get('days_per_week', 6)
    lessons_per_day = data.get('settings', {}).get('lessons_per_day', 6)
    
    # Суббота: только 3 урока
    saturday_limit = SATURDAY_LESSONS  # 3 урока (1-3)
    saturday_max = SATURDAY_MAX  # максимум 2 урока в субботу
    
    timetable = [[None for _ in range(lessons_per_day)] for _ in range(days)]
    
    all_lessons = []
    for subject in subjects_data:
        subject_name = subject['name']
        hours = subject['hours']
        teacher = get_teacher_for_subject(subject_name)
        if not teacher:
            continue
        for _ in range(hours):
            all_lessons.append({
                'name': subject_name,
                'teacher_id': teacher['id'],
                'teacher_name': teacher['name'],
                'room': teacher.get('room', 'Кабинет')
            })
    
    random.shuffle(all_lessons)
    hard_subjects = ['Алгебра', 'Геометрия', 'Математика', 'Физика', 'Русский язык', 'Английский язык']
    
    # Сначала сложные предметы (только в первые 3 урока)
    for lesson_data in all_lessons[:]:
        if lesson_data['name'] in hard_subjects:
            placed = False
            for day in range(days):
                if day == 5:  # Суббота
                    continue  # В субботу сложные предметы не ставим
                for lesson in range(3):
                    if timetable[day][lesson] is None:
                        timetable[day][lesson] = lesson_data
                        all_lessons.remove(lesson_data)
                        placed = True
                        break
                if placed:
                    break
    
    # Остальные предметы
    for lesson_data in all_lessons[:]:
        placed = False
        day_order = list(range(days))
        random.shuffle(day_order)
        
        for day in day_order:
            # Суббота: только 1-3 уроки и не более 2 уроков
            if day == 5:
                # Проверяем, сколько уже уроков в субботу
                saturday_count = sum(1 for l in range(saturday_limit) if timetable[5][l] is not None)
                if saturday_count >= saturday_max:
                    continue
                # Суббота: только уроки 0-2 (1-3 уроки)
                allowed_lessons = range(saturday_limit)
            else:
                allowed_lessons = range(lessons_per_day)
            
            # Проверяем, не было ли такого же предмета вчера
            same_subject_yesterday = False
            if day > 0:
                for lesson in range(lessons_per_day):
                    if timetable[day-1][lesson] and timetable[day-1][lesson]['name'] == lesson_data['name']:
                        same_subject_yesterday = True
                        break
            
            if same_subject_yesterday:
                continue
            
            lesson_order = list(allowed_lessons)
            random.shuffle(lesson_order)
            
            for lesson in lesson_order:
                if timetable[day][lesson] is None:
                    if lesson_data['name'] == 'Физкультура' and lesson == 0:
                        continue
                    if lesson_data['name'] in hard_subjects and lesson == lessons_per_day - 1:
                        continue
                    
                    # Проверяем, не будет ли больше 2 окон в этом дне
                    test_timetable = timetable[day].copy()
                    test_timetable[lesson] = lesson_data
                    if count_windows_in_day(test_timetable) > MAX_WINDOWS_PER_DAY:
                        continue
                    
                    timetable[day][lesson] = lesson_data
                    all_lessons.remove(lesson_data)
                    placed = True
                    break
            if placed:
                break
    
    # Если остались нераспределенные уроки
    for lesson_data in all_lessons:
        for day in range(days):
            if day == 5:
                saturday_count = sum(1 for l in range(saturday_limit) if timetable[5][l] is not None)
                if saturday_count >= saturday_max:
                    continue
                allowed_lessons = range(saturday_limit)
            else:
                allowed_lessons = range(lessons_per_day)
            
            for lesson in allowed_lessons:
                if timetable[day][lesson] is None:
                    # Проверяем окна
                    test_timetable = timetable[day].copy()
                    test_timetable[lesson] = lesson_data
                    if count_windows_in_day(test_timetable) > MAX_WINDOWS_PER_DAY:
                        continue
                    timetable[day][lesson] = lesson_data
                    break
            if timetable[day][lesson] == lesson_data:
                break
    
    return timetable

def calculate_quality(timetable):
    if not timetable:
        return {'score': 0, 'total_lessons': 0, 'windows': 0, 'days_with_windows': 0, 
                'hard_in_morning': 0, 'total_hard': 0, 'level': 'Нет данных'}
    
    days = len(timetable)
    lessons_per_day = len(timetable[0]) if days > 0 else 0
    hard_subjects = ['Алгебра', 'Геометрия', 'Математика', 'Физика', 'Русский язык', 'Английский язык']
    
    total_lessons = 0
    windows = 0
    hard_in_morning = 0
    total_hard = 0
    days_with_windows = 0
    consecutive_duplicates = 0
    
    for day in range(days):
        day_lessons = []
        prev_subject = None
        day_windows = 0
        
        for lesson in range(lessons_per_day):
            if timetable[day][lesson] is not None:
                total_lessons += 1
                day_lessons.append(True)
                subject = timetable[day][lesson].get('name', '')
                if subject in hard_subjects:
                    total_hard += 1
                    if lesson < 3:
                        hard_in_morning += 1
                if prev_subject == subject:
                    consecutive_duplicates += 1
                prev_subject = subject
            else:
                day_lessons.append(False)
                prev_subject = None
        
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
                    day_windows += 1
                    windows += 1
            if day_windows > 0:
                days_with_windows += 1
    
    quality_score = 100
    quality_score -= min(40, windows * 8)
    quality_score -= days_with_windows * 3
    if total_hard > 0:
        morning_ratio = hard_in_morning / total_hard
        quality_score += morning_ratio * 20
    quality_score -= consecutive_duplicates * 5
    
    empty_days = 0
    for day in range(days):
        empty = all(timetable[day][lesson] is None for lesson in range(lessons_per_day))
        if empty:
            empty_days += 1
    quality_score -= empty_days * 15
    
    # Бонус за соблюдение ограничений
    if windows <= MAX_WINDOWS_PER_DAY * days:
        quality_score += 5
    
    quality_score = max(0, min(100, quality_score))
    
    return {
        'score': round(quality_score),
        'total_lessons': total_lessons,
        'windows': windows,
        'days_with_windows': days_with_windows,
        'hard_in_morning': hard_in_morning,
        'total_hard': total_hard,
        'consecutive_duplicates': consecutive_duplicates,
        'level': 'Отлично' if quality_score >= 80 else 'Хорошо' if quality_score >= 60 else 'Средне' if quality_score >= 40 else 'Требует улучшения'
    }

# Генерация расписаний для всех классов
def generate_all_timetables():
    all_timetables = {}
    all_quality = {}
    
    for class_info in data.get('classes', []):
        class_id = class_info['id']
        timetable = generate_timetable_for_class(class_id)
        quality = calculate_quality(timetable)
        total_hours = sum(s.get('hours', 0) for s in data.get('subjects_by_grade', {}).get(str(class_info['grade']), []))
        
        all_timetables[class_id] = {
            'timetable': timetable,
            'quality': quality,
            'total_hours': total_hours,
            'class_info': class_info
        }
    
    return all_timetables

print("⏳ Генерация расписаний для всех классов...")
print(f"📌 Ограничения: максимум {MAX_WINDOWS_PER_DAY} окна в день, суббота - до {SATURDAY_LESSONS} урока, не более {SATURDAY_MAX} уроков")

ALL_TIMETABLES = generate_all_timetables()
print(f"✅ Готово! Сгенерировано расписаний: {len(ALL_TIMETABLES)}")

avg_quality = 0
for class_id, data_item in ALL_TIMETABLES.items():
    avg_quality += data_item['quality']['score']
if len(ALL_TIMETABLES) > 0:
    avg_quality /= len(ALL_TIMETABLES)
print(f"📊 Среднее качество: {avg_quality:.1f}%")

CLASSES_LIST = data.get('classes', [])

@app.route('/')
def index():
    return render_template('index.html', classes=CLASSES_LIST)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        req_data = request.get_json()
        class_id = req_data.get('class_id')
        if isinstance(class_id, str):
            class_id = int(class_id)
        
        if class_id in ALL_TIMETABLES:
            result = ALL_TIMETABLES[class_id]
            return jsonify({
                'success': True,
                'timetable': result['timetable'],
                'total_hours': result['total_hours'],
                'quality': result['quality'],
                'class_info': result['class_info']
            })
        else:
            return jsonify({'success': False, 'error': 'Класс не найден'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate_all', methods=['POST'])
def generate_all():
    try:
        results = {}
        for class_id, data_item in ALL_TIMETABLES.items():
            results[class_id] = {
                'class_name': data_item['class_info']['name'],
                'total_hours': data_item['total_hours'],
                'quality_score': data_item['quality']['score'],
                'quality_level': data_item['quality']['level'],
                'windows': data_item['quality']['windows']
            }
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/timetable/<int:class_id>')
def timetable_page(class_id):
    class_info = None
    for c in CLASSES_LIST:
        if c['id'] == class_id:
            class_info = c
            break
    
    if not class_info:
        return f"Класс с ID {class_id} не найден", 404
    
    result = ALL_TIMETABLES.get(class_id)
    if not result:
        return "Расписание не сгенерировано", 404
    
    return render_template('timetable.html', 
                         timetable=result['timetable'], 
                         class_info=result['class_info'],
                         total_hours=result['total_hours'],
                         quality=result['quality'])

@app.route('/help')
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    print("=" * 60)
    print("🏫 ШКОЛЬНОЕ РАСПИСАНИЕ (с ограничениями)")
    print("=" * 60)
    print(f"📌 Максимум окон в день: {MAX_WINDOWS_PER_DAY}")
    print(f"📌 Суббота: только 1-{SATURDAY_LESSONS} уроки")
    print(f"📌 Суббота: максимум {SATURDAY_MAX} урока")
    print("\n📊 Результаты генерации:")
    for class_id, data_item in ALL_TIMETABLES.items():
        q = data_item['quality']
        print(f"  {data_item['class_info']['name']}: {q['score']}% ({q['level']}) - {q['windows']} окон")
    
    print("\n" + "=" * 60)
    print("Сервер: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)
