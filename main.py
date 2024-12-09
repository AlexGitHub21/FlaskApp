import datetime
import asyncio
import aiohttp
from flask import Flask, render_template, url_for, flash, jsonify, request, redirect, session
from forms import TestForm, RegistForm, LoginForm
from Config import Configuration
from extensions import db
from models import Test, User
from flask_principal import Principal, Permission, RoleNeed, PermissionDenied, identity_loaded, Identity, identity_changed, UserNeed
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from UserLogin import UserLogin


app = Flask(__name__, static_folder='static')
principal = Principal(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
#указываем функцию-обработчик для ее вызова при несанкционированном доступе к защищенной от неавторизованных пользователей странице
#перенаправляем пользователя на страницу авторизации, если он неаворизован но хочет зайти на закрытые страницы
login_manager.login_view = 'login'
login_manager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
login_manager.session_protection = "strong"
app.config.from_object(Configuration) #загружаем всю конфигурацию

db.init_app(app)

#определение ролей
admin_permission = Permission(RoleNeed('admin'))
user_permission = Permission(RoleNeed('user'))

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
        test = Test(
            number_rows=form.number_rows.data,
            number_seats=form.number_seats.data,
            number_visitors=form.number_visitors.data,
            visitor_preferences=form.visitor_preferences.data,
            answer=None,
            user_id=current_user.get_id()
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

    flash(f'Тест успешно {"добавлен" if test else "обновлен"}')
    if test.answer:
        flash(f'Ответ к тесту: {test.answer}')
    return True


def addUser(login, hpsw, role):
    user = db.session.query(User).filter_by(login=login).first()
    if user:
        return False
    else:
        user = User(
            login=login,
            psw=hpsw,
            role_type=role,
        )
        db.session.add(user)
        db.session.commit()
        return True


@login_manager.user_loader
def load_user(user_id):
    return User.getUser(user_id)


@app.route('/')
def start():
    if current_user.is_authenticated:
        logout_user()
    return render_template('start_page.html', title='Стартовая страница сайта')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    reg_form = RegistForm()
    if reg_form.validate_on_submit():
        session.pop('_flashes', None)
        hash = generate_password_hash(reg_form.psw.data)
        role = 'user'
        res = addUser(reg_form.login.data, hash, role)
        if res:
            flash("Вы успешно зарегистрированы", "success")
            return render_template('registration.html', reg_form=reg_form, title='Регистрация', success=True)
        else:
            flash("Такой пользователь уже зарегистрирован", "error")
    return render_template('registration.html', reg_form=reg_form, title='Регистрация')


@app.route('/index')
@login_required
def index():
    return render_template('index.html', title='Главная страница сайта', curr_greeting=gretting, menu=menu)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("start"))


@app.route("/login", methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login = form.login.data
        user = User.query.filter_by(login=login).first()
        if user and check_password_hash(user.psw, form.psw.data):
            #create() используется при создании объекта в момент авторизации пользователя
            userlogin = UserLogin().create(user)
            login_user(userlogin)
            # Обновляем идентичность пользователя
            identity_changed.send(app, identity=Identity(user.id))
            #Теперь пользователь авторизован
            return redirect(url_for('index'))

        flash("Неверная пара логин/пароль", "error")

    return render_template("login.html", form=form, title="Авторизация")


#настройка события identity_loaded, для авт.привязки роли, указанной в БД
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    if current_user.is_authenticated:
        # Устанавливаем текщего польователя как идентифицированного
        identity.user = current_user

        # Установка идентификатора пользователя
        identity.provides.add(UserNeed(current_user.get_id()))
        # Добавление роли пользователя
        if current_user.role_type == 'admin':
            identity.provides.add(RoleNeed('admin'))
        elif current_user.role_type == 'user':
            identity.provides.add(RoleNeed('user'))


# Обработчик ошибки PermissionDenied
@app.errorhandler(PermissionDenied)
def handle_permission_denied(error):
    flash("У вас нет прав для доступа к странице.", "error")
    return redirect(url_for('login'))


@app.route('/add_edit_tests', methods=['GET', 'POST'])
@login_required
@user_permission.require()
def add_test():
    #передаем экземпляр класса TestForm
    form = TestForm()
    if form.validate_on_submit():
        if handle_test_form_submission(form):
            return redirect(url_for('add_test'))

    tests = Test.query.filter_by(user_id=current_user.get_id()).order_by(Test.id.asc()).all()
    return render_template('add_edit_tests.html', title='Добавить тест', form=form, tests=tests)


@app.route('/list_tests')
@login_required
def list_tests():
    if current_user.role_type == 'user':
        tests = Test.query.filter_by(user_id=current_user.get_id()).order_by(Test.id.asc()).all()
    else:
        tests = Test.query.order_by(Test.id.asc()).all()

    form = TestForm()
    return render_template('list_tests.html', title='Список тестов', form=form, tests=tests)


@app.route('/get_answer', methods=['POST'])
@login_required
def get_answer():
    data = request.get_json()
    test_id = data.get('test_id')

    test = Test.query.filter_by(id=test_id).first()
    if test:
        if not test.answer:
            # отправляем запрос к микросервису асинхронно
            asyncio.run(call_microservice_async(test.id))

        response = {'answer': test.answer}
    else:
        response = {'error': 'Тест не найден'}
    return jsonify(response)


@app.route('/delete_test', methods=['POST'])
@login_required
def delete_test():
    data = request.get_json()
    test_id = data.get('test_id')
    test = Test.query.filter_by(id=test_id).first()

    if test:
        db.session.delete(test)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Тест удалён'})
    else:
        return jsonify({'status': 'error', 'message': 'Тест не найден'}), 404


async def call_microservice_async(test_id):
    test = db.session.get(Test, test_id)
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
@login_required
@user_permission.require()
def change_test(test_id):
    # test = Test.query.filter_by(id=test_id, user_id=current_user.get_id()).first()
    test = db.session.get(Test, test_id)

    if not test:
        return render_template('page404.html', title="Страница не найдена")

    if request.method == 'GET':
        form = TestForm(obj=test)
    else:
        form = TestForm(request.form)

    if form.validate_on_submit():
        if handle_test_form_submission(form, test):
            return redirect(url_for('add_test'))

    # tests = Test.query.order_by(Test.id.asc()).all()
    tests = Test.query.filter_by(user_id=current_user.get_id()).order_by(Test.id.asc()).all()
    return render_template('add_edit_tests.html', title='Изменение теста', form=form, tests=tests, active_test=test_id)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # db.drop_all()
    app.run(debug=Configuration.DEBUG)



# import datetime
# import asyncio
# import aiohttp
# from flask import Flask, render_template, url_for, flash, jsonify, request, redirect, session
# from forms import TestForm, RegistForm, LoginForm
# from Config import Configuration
# from extensions import db
# from models import Test, User
# from werkzeug.security import generate_password_hash, check_password_hash
# from UserLogin import UserLogin
#
#
# app = Flask(__name__, static_folder='static')
# app.config.from_object(Configuration) #загружаем всю конфигурацию
# db.init_app(app)
#
#
# hour = datetime.datetime.now().hour
# gretting = 'Good Morning' if hour < 12 else 'Good Afternoon'
# menu = ['Добавить(сохранить) свой тест', 'Получить ответ к тесту', 'Изменить тест', 'Удалить тест']
#
#
# def handle_test_form_submission(form, test=None):
#     if len(form.number_seats.data.split()) != form.number_rows.data:
#         flash(f'Для каждого ряда {form.number_rows.data} дб описано число мест {len(form.number_seats.data.split())}')
#         return False
#     elif len(form.visitor_preferences.data.split()) != form.number_visitors.data:
#         flash(f'Для каждого посетителя {form.number_visitors.data} дб добавлены предпочтения {len(form.visitor_preferences.data.split())}')
#         return False
#
#     if not test:
#         # создание нового теста
#         test = Test(
#             number_rows=form.number_rows.data,
#             number_seats=form.number_seats.data,
#             number_visitors=form.number_visitors.data,
#             visitor_preferences=form.visitor_preferences.data,
#             answer=None
#         )
#         db.session.add(test)
#     else:
#         # изменение существующего теста
#         test.number_rows = form.number_rows.data
#         test.number_seats = form.number_seats.data
#         test.number_visitors = form.number_visitors.data
#         test.visitor_preferences = form.visitor_preferences.data
#     db.session.commit()
#     # отправляем запрос к микросервису асинхронно Для получения ответа
#     asyncio.run(call_microservice_async(test.id))
#
#     flash(f'Тест успешно {"обновлен" if test else "добавлен"}')
#     if test.answer:
#         flash(f'Ответ к тесту: {test.answer}')
#     return True
#
#
# def addUser(login, hpsw, role):
#     user = db.session.query(User).filter_by(login=login).first()
#     if user:
#         return False
#     else:
#         # создание нового пользователя
#         user = User(
#             login=login,
#             psw=hpsw,
#             role_type=role,
#         )
#         db.session.add(user)
#         db.session.commit()
#         return True
#
#
# @app.route('/')
# def start():
#     return render_template('start_page.html', title='Стартовая страница сайта')
#
#
# @app.route('/registration', methods=['GET', 'POST'])
# def registration():
#     reg_form = RegistForm()
#     if reg_form.validate_on_submit():
#         session.pop('_flashes', None)
#
#         hash = generate_password_hash(reg_form.psw.data)
#         role = 'user'
#         res = addUser(reg_form.login.data, hash, role)
#         if res:
#             flash("Вы успешно зарегистрированы", "success")
#             return render_template('registration.html', reg_form=reg_form, title='Регистрация', success=True)
#         else:
#             flash("Такой пользователь уже зарегистрирован", "error")
#     return render_template('registration.html', reg_form=reg_form, title='Регистрация')
#
#
# @app.route('/index')
# def index():
#     return render_template('index.html',title='Главная страница сайта', curr_greeting=gretting, menu=menu)
#
#
# @app.route("/login", methods=["POST", "GET"])
# def login():
#     form = LoginForm()
#     if form.validate_on_submit():
#         login = form.login.data
#         user = User.query.filter_by(login=login).first()
#         if user and check_password_hash(user.psw, form.psw.data):
#             session['user_id'] = user.id
#             session['login'] = user.login
#             session['role'] = user.role_type
#             return redirect(url_for('index'))
#
#         flash("Неверная пара логин/пароль", "error")
#
#     return render_template("login.html", form=form, title="Авторизация")
#
#
# def redirectToIndex():
#     flash('Доступ к странице запрещен', 'error')
#     return redirect(url_for('index'))
#
#
# @app.route('/logout')
# def logout():
#     session.clear() #очищаем сессию полностью
#     return redirect(url_for("index"))
#
#
# @app.route('/add_edit_tests', methods=['GET', 'POST'])
# def test():
#     #передаем экземпляр класса TestForm
#     form = TestForm()
#     if session.get('role') == 'user':
#         if form.validate_on_submit():
#             if handle_test_form_submission(form):
#                 return redirect(url_for('test'))
#
#         tests = Test.query.order_by(Test.id.asc()).all()
#         return render_template('add_edit_tests.html', title='Добавление теста', form=form, tests=tests)
#     else:
#
#         redirectToIndex()
#
#
# @app.route('/list_tests')
# def list_tests():
#     if session.get('role') != 'user' and session.get('role') != 'admin':
#         redirectToIndex()
#     else:
#         tests = Test.query.order_by(Test.id.asc()).all()
#         form = TestForm()
#         return render_template('list_tests.html', title='Список тестов', form=form, tests=tests)
#
#
# @app.route('/get_answer', methods=['POST'])
# def get_answer():
#     if session.get('role') != 'user' and session.get('role') != 'admin':
#         redirectToIndex()
#     else:
#         data = request.get_json()
#         test_id = data.get('test_id')
#
#         test = Test.query.filter_by(id=test_id).first()
#         if test:
#             if not test.answer:
#                 # отправляем запрос к микросервису асинхронно
#                 asyncio.run(call_microservice_async(test.id))
#
#             response = {'answer': test.answer}
#         else:
#             response = {'error': 'Тест не найден'}
#         return jsonify(response)
#
#
# @app.route('/delete_test', methods=['POST'])
# def delete_test():
#     if session.get('role') != 'user' and session.get('role') != 'admin':
#         redirectToIndex()
#     else:
#         data = request.get_json()
#         test_id = data.get('test_id')
#         test = Test.query.filter_by(id=test_id).first()
#         if test:
#             db.session.delete(test)
#             db.session.commit()
#             return jsonify({'status': 'success', 'message': 'Тест удалён'})
#         else:
#             return render_template('page404.html', title="Страница не найдена")
#
#
# async def call_microservice_async(test_id):
#     test = db.session.get(Test, test_id)
#     if not test:
#         return
#
#     url = 'http://localhost:5001/tests/calculate' #путь до микросервиса
#     data = {
#         'number_rows': test.number_rows,
#         'number_seats': test.number_seats,
#         'number_visitors': test.number_visitors,
#         'visitor_preferences': test.visitor_preferences
#     }
#
#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.post(url, json=data) as response:
#                 if response.status == 200:
#                     result = await response.json()
#                     test.answer = result.get('result')
#                     db.session.commit()
#                 else:
#                     print(f'Ошибка: {response.status}')
#         except Exception as e:
#             print(f'Ошибка соединения с микросервисом: {e}')
#
#
# @app.route('/change_test/<int:test_id>', methods=['GET', 'POST'])
# def change_test(test_id):
#     if session.get('role') != 'user' and session.get('role') != 'admin':
#         redirectToIndex()
#     else:
#         test = db.session.get(Test, test_id)
#         if not test:
#             return render_template('page404.html', title="Страница не найдена")
#
#         if request.method == 'GET':
#             form = TestForm(obj=test)
#         else:
#             form = TestForm(request.form)
#
#         if form.validate_on_submit():
#             if handle_test_form_submission(form, test):
#                 return redirect(url_for('test'))
#
#         tests = Test.query.order_by(Test.id.asc()).all()
#         return render_template('add_edit_tests.html', title='Изменение теста', form=form, tests=tests)
#
#
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=Configuration.DEBUG)
