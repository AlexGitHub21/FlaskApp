import datetime
import asyncio
import aiohttp
from flask import Flask, render_template, url_for, flash, jsonify, request, redirect
from forms import TestForm
from Config import Configuration
from extensions import db
from models import Tests


app = Flask(__name__, static_folder='static')
app.config.from_object(Configuration) #загружаем всю конфигурацию

db.init_app(app)

hour = datetime.datetime.now().hour
gretting = 'Good Morning' if hour < 12 else 'Good Afternoon'
menu = ['Добавить(сохранить) свой тест', 'Получить ответ к тесту', 'Изменить тест', 'Удалить тест']


def handle_test_form_submission(form, test=None):
    if len(form.number_seats.data.split()) != form.number_rows.data:
        flash(f'Для каждого ряда {form.number_rows.data} дб описано число мест {len(form.number_seats.data.split())}')
        return False
    elif len(form.visitor_preferences.data.split()) != form.number_visitors.data:
        flash(f'Для каждого посетителя {form.number_visitors.data} дб добавлены предпочтения {len(form.visitor_preferences.data.split())}')
        return False

    if not test:
        # создание нового теста
        test = Tests(
            number_rows=form.number_rows.data,
            number_seats=form.number_seats.data,
            number_visitors=form.number_visitors.data,
            visitor_preferences=form.visitor_preferences.data,
            answer=None
        )
        db.session.add(test)
    else:
        # изменение существующего теста
        test.number_rows = form.number_rows.data
        test.number_seats = form.number_seats.data
        test.number_visitors = form.number_visitors.data
        test.visitor_preferences = form.visitor_preferences.data
    db.session.commit()
    # отправляем запрос к микросервису асинхронно Для получения ответа
    asyncio.run(call_microservice_async(test.id))

    flash(f'Тест успешно {"обновлен" if test else "добавлен"}')
    if test.answer:
        flash(f'Ответ к тесту: {test.answer}')
    return True


@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html', title='Главная страница сайта', curr_greeting=gretting, menu=menu)


@app.route('/add_edit_tests', methods=['GET', 'POST'])
def test():
    #передаем экземпляр класса TestForm
    form = TestForm()
    if form.validate_on_submit():
        if handle_test_form_submission(form):
            return redirect(url_for('test'))

    tests = Tests.query.order_by(Tests.id.asc()).all()
    # tests = Tests.query.all()
    return render_template('add_edit_tests.html', title='Добавление теста', form=form, tests=tests)


@app.route('/list_tests')
def list_tests():
    tests = Tests.query.order_by(Tests.id.asc()).all()
    # tests = Tests.query.all()
    form = TestForm()
    return render_template('list_tests.html', title='Список тестов', form=form, tests=tests)


@app.route('/get_answer', methods=['POST'])
def get_answer():
    data = request.get_json()
    test_id = data.get('test_id')

    test = Tests.query.filter_by(id=test_id).first()
    if test:
        if not test.answer:
            # отправляем запрос к микросервису асинхронно
            asyncio.run(call_microservice_async(test.id))

        response = {'answer': test.answer}
    else:
        response = {'error': 'Тест не найден'}
    return jsonify(response)


@app.route('/delete_test', methods=['POST'])
def delete_test():
    data = request.get_json()
    test_id = data.get('test_id')
    test = Tests.query.filter_by(id=test_id).first()

    if test:
        db.session.delete(test)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Тест удалён'})
    else:
        return jsonify({'status': 'error', 'message': 'Тест не найден'}), 404


async def call_microservice_async(test_id):
    test = db.session.get(Tests, test_id)
    if not test:
        return

    url = 'http://localhost:5001/tests/calculate' #путь до микросервиса
    data = {
        'number_rows': test.number_rows,
        'number_seats': test.number_seats,
        'number_visitors': test.number_visitors,
        'visitor_preferences': test.visitor_preferences
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    test.answer = result.get('result')
                    db.session.commit()
                else:
                    print(f'Ошибка: {response.status}')
        except Exception as e:
            print(f'Ошибка соединения с микросервисом: {e}')


@app.route('/change_test/<int:test_id>', methods=['GET', 'POST'])
def change_test(test_id):
    test = db.session.get(Tests, test_id)

    if not test:
        return render_template('page404.html', title="Страница не найдена")

    if request.method == 'GET':
        form = TestForm(obj=test)
    else:
        form = TestForm(request.form)

    if form.validate_on_submit():
        if handle_test_form_submission(form, test):
            return redirect(url_for('test'))

    tests = Tests.query.order_by(Tests.id.asc()).all()
    return render_template('add_edit_tests.html', title='Изменение теста', form=form, tests=tests)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=Configuration.DEBUG)
