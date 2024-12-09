from models import User


class UserLogin:
    def fromDB(self, user_id):
        user = User.getUser(user_id)
        if not user:
            print("Пользователь не найден")
            return None
        self.__user = user
        return self

    def create(self, user):
        self.__user = user
        return self

    @property
    def is_authenticated(self):
        return True

    @property
    def role_type(self):
        return self.__user.role_type

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.__user.id)

