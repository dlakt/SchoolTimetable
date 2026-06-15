АРХИТЕКТУРА ПРОГРАММЫ (покажите схему)
text
SchoolTimetable/
│
├── app.py                 # Главный сервер (Flask)
├── timetable_solver.py    # Алгоритм расписания
├── data/
│   └── school_data.json   # Данные (учителя, классы, предметы)
└── templates/
    ├── base.html          # Общий шаблон
    ├── index.html         # Главная страница
    ├── timetable.html     # Страница расписания
    └── help.html          # Справка

Запуск программы

bash
python app.py


Главная страница (http://127.0.0.1:5000)
