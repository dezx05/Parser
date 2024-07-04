from fake_useragent import UserAgent
import requests
import json

# Словари для сопоставления 'name' и 'id'
employment_dict = {
    "Полная занятость": "full",
    "Частичная занятость": "part",
    "Проектная работа": "project",
    "Волонтерство": "volunteer",
    "Стажировка": "probation"
}

experience_dict = {
    "Нет опыта": "noExperience",
    "От 1 года до 3 лет": "between1And3",
    "От 3 до 6 лет": "between3And6",
    "Более 6 лет": "moreThan6"
}

schedule_dict = {
    "Полный день": "fullDay",
    "Сменный график": "shift",
    "Гибкий график": "flexible",
    "Удаленная работа": "remote",
    "Вахтовый метод": "flyInFlyOut"
}

def get_vacancies(text, employment_name, experience_name, schedule_name):
    url = "https://api.hh.ru/vacancies"
    user_agent = UserAgent().random
    # Получение 'id' из 'name'
    employment_id = employment_dict.get(employment_name)
    experience_id = experience_dict.get(experience_name)
    schedule_id = schedule_dict.get(schedule_name)

    params = {
        "text": text,
        "area": 1,
        "page": 1,
        "per_page": 100,
        "only_with_salary": True,
        "employment": employment_id,
        "schedule": schedule_id,
        "experience": experience_id
    }
    headers = {
        "User-Agent": user_agent
    }

    response = requests.get(url, params=params, headers=headers)
    vacancies = []
    if response.status_code == 200:
        data = response.content.decode()
        json_data = json.loads(data)
        vacancies = json_data['items']
    return vacancies