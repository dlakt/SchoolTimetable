
from flask import Flask, render_template, request, jsonify
import json
import os
import random

app = Flask(__name__)

def load_data():
    path = 'data/school_data.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'subjects_by_grade': {}, 'classrooms': []}

data = load_data()

def get_teacher_name(teacher_id):
    for teacher in data.get('teachers', []):
        if teacher['id'] == teacher_id:
            return teacher['name']
    return f"Учитель {teacher_id}"

def get_classroom_for_subject(subject):
    classrooms = data.get('classrooms', [])
    subject_classroom = {
        'Физика': 'physics', 'Химия': 'chemistry', 'Информатика': 'computer',
        'Физкультура': 'sport', 'Математика': 'math', 'Алгебра': 'math', 'Геометрия': 'math'
    }
    required_type = subject_classroom.get(subject, 'regular')
    for room in classrooms:
        if room.get('type') == required_type:
            return room.get('name', 'Кабинет')
    for room in classrooms:
        if room.get('type') == 'regular':
            return room.get('name', 'Кабинет')
    return "Кабинет"

def generate_timetable_for_grade(grade):
    grade_str = str(grade)
    subjects = data.get('subjects_by_grade', {}).get(grade_str, [])
    
    if not subjects:
        return generate_test_timetable()
    
    all_lessons = []
    for subject in subjects:
        for i in range(subject.get('hours', 0)):
            all_lessons.append({
                'name': subject.get('name', 'Урок'),
                'teacher_id': subject.get('teacher_id', 1),
                'teacher_name': get_teacher_name(subject.get('teacher_id', 1))
            })
    
    random.shuffle(all_lessons)
    days = 6
    lessons_per_day = 6
    
    timetable = []
    for day in range(days):
        day_schedule = []
        for lesson in range(lessons_per_day):
            day_schedule.append(None)
        timetable.append(day_schedule)
    
    hard_subjects = ['Алгебра', 'Геометрия', 'Математика', 'Физика', 'Русский язык', 'Английский язык']
    
    for subject in all_lessons:
        if subject['name'] in hard_subjects:
            placed = False
            for day in range(days):
                for lesson in range(3):
                    if timetable[day][lesson] is None:
                        timetable[day][lesson] = {
                            'subject': subject['name'],
                            'teacher_name': subject['teacher_name'],
                            'classroom': get_classroom_for_subject(subject['name'])
                        }
                        placed = True
                        break
                if placed:
                    break
    
    for subject in all_lessons:
        if subject['name'] not in hard_subjects:
            placed = False
            for day in range(days):
                for lesson in range(lessons_per_day):
                    if timetable[day][lesson] is None:
                        timetable[day][lesson] = {
                            'subject': subject['name'],
                            'teacher_name': subject['teacher_name'],
                            'classroom': get_classroom_for_subject(subject['name'])
                        }
                        placed = True
                        break
                if placed:
                    break
    
    return timetable

def generate_test_timetable():
    timetable = []
    subjects = ['Математика', 'Русский язык', 'Литература', 'История', 'Английский', 'Физкультура']
    teachers = ['Иванова М.А.', 'Петров С.В.', 'Сидорова Е.П.', 'Козлов Д.Н.', 'Новикова О.В.', 'Морозов И.А.']
    classrooms = ['101', '102', '103', '104', '105', '201']
    
    for day in range(6):
        day_schedule = []
        for lesson in range(6):
            if lesson < 5:
                day_schedule.append({
                    'subject': subjects[lesson % len(subjects)],
                    'teacher_name': teachers[lesson % len(teachers)],
                    'classroom': classrooms[lesson % len(classrooms)]
                })
            else:
                day_schedule.append(None)
        timetable.append(day_schedule)
    return timetable

def get_total_hours(grade):
    grade_str = str(grade)
    subjects = data.get('subjects_by_grade', {}).get(grade_str, [])
    total = sum(s.get('hours', 0) for s in subjects)
    return total if total > 0 else 30

# ВАЖНО: Классы объявлены ГЛОБАЛЬНО и доступны
CLASSES_LIST = [
    {'id': 1, 'name': '5А класс', 'grade': 5},
    {'id': 2, 'name': '5Б класс', 'grade': 5},
    {'id': 3, 'name': '6А класс', 'grade': 6},
    {'id': 4, 'name': '6Б класс', 'grade': 6},
    {'id': 5, 'name': '7А класс', 'grade': 7},
    {'id': 6, 'name': '7Б класс', 'grade': 7},
    {'id': 7, 'name': '8А класс', 'grade': 8},
    {'id': 8, 'name': '8Б класс', 'grade': 8},
    {'id': 9, 'name': '9А класс', 'grade': 9},
    {'id': 10, 'name': '9Б класс', 'grade': 9}
]

@app.route('/')
def index():
    print(f"Отправляем классы: {CLASSES_LIST}")
    return render_template('index.html', classes=CLASSES_LIST)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        req_data = request.get_json()
        print(f"Получен запрос: {req_data}")
        
        class_id = req_data.get('class_id')
        # Преобразуем в число, если пришло строкой
        if isinstance(class_id, str):
            class_id = int(class_id)
        
        print(f"Ищем класс с ID: {class_id} (тип: {type(class_id)})")
        
        # Поиск класса
        class_info = None
        for c in CLASSES_LIST:
            if c['id'] == class_id:
                class_info = c
                break
        
        if not class_info:
            print(f"КЛАСС НЕ НАЙДЕН! ID={class_id}")
            return jsonify({'success': False, 'error': f'Класс с ID {class_id} не найден'})
        
        print(f"Найден класс: {class_info}")
        
        timetable = generate_timetable_for_grade(class_info['grade'])
        total_hours = get_total_hours(class_info['grade'])
        
        return jsonify({
            'success': True,
            'timetable': timetable,
            'total_hours': total_hours
        })
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate_all', methods=['POST'])
def generate_all():
    return jsonify({'success': True})

@app.route('/timetable/<int:class_id>')
def timetable_page(class_id):
    print(f"Запрос страницы расписания для класса {class_id}")
    
    class_info = None
    for c in CLASSES_LIST:
        if c['id'] == class_id:
            class_info = c
            break
    
    if not class_info:
        return f"Класс с ID {class_id} не найден", 404
    
    timetable = generate_timetable_for_grade(class_info['grade'])
    total_hours = get_total_hours(class_info['grade'])
    
    return render_template('timetable.html', 
                         timetable=timetable, 
                         class_info=class_info,
                         total_hours=total_hours)

@app.route('/help')
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    print("=" * 50)
    print("Школьное расписание")
    print("=" * 50)
    print("Доступные классы:")
    for c in CLASSES_LIST:
        print(f"  ID {c['id']}: {c['name']} ({c['grade']} класс)")
    print("=" * 50)
    print("Сервер запущен: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
