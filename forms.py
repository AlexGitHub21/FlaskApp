from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, EmailField, PasswordField
from wtforms.validators import DataRequired, NumberRange, regexp, ValidationError, InputRequired, EqualTo


class TestForm(FlaskForm):
    number_rows = IntegerField("Количество рядов в кинозале: ", validators=[DataRequired(), NumberRange(min=1, max=10000)])
    number_seats = StringField("Количество мест в каждом ряду (через пробел пожалуйста): ", validators=[DataRequired()])
    number_visitors = IntegerField("Количество посетителей кинотеатра: ", validators=[DataRequired(), NumberRange(min=1, max=10000)])
    visitor_preferences = StringField("Предпочтения посетителей, где 0 - посетитель хочет сесть ближе к экрану, 1 - посетитель хочет сесть дальше от экрана: ", validators=[DataRequired(), regexp('^(?:0|1)(?:\s(?:0|1))*$', message='Разрешено вводить только 0 или 1')])
    submit = SubmitField("Сохранить тест в базе данных")

    def validate_number_seats(self, number_seats):
        seats = number_seats.data.split()
        if not all(c.isdigit() for c in ''.join(seats)):
            raise ValidationError("Поле должно содержать только числа и пробелы.")

        seats_int = [int(s) for s in seats]
        if not all(1 <= s <= 100000 for s in seats_int):
            raise ValidationError("Значения должны быть в диапазоне от 1 до 100000.")


class RegistForm(FlaskForm):
    login = StringField("Логин: ", validators=[DataRequired()])
    psw = PasswordField("Пароль: ", validators=[DataRequired()])
    confirm_psw = PasswordField("Подтверждение пароля: ", validators=[DataRequired(), EqualTo('psw', message='Пароли должны совпадать')])
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    login = StringField("Логин: ", validators=[DataRequired()])
    psw = PasswordField("Пароль: ", validators=[DataRequired()])
    submit = SubmitField("Войти")

#валидации на стороне сервера