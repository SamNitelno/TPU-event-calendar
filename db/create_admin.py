"""Create an administrator or reset a password without passing secrets in shell history."""

import argparse
import getpass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.auth import hash_password, token_hash
from db.database import engine
from db.models import AdminSession, LoginAttempt, User


def main():
    parser = argparse.ArgumentParser(description="Создать администратора календаря")
    parser.add_argument("username", help="Логин (от 3 до 64 символов)")
    parser.add_argument("--reset-password", action="store_true", help="Сменить пароль существующего администратора")
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not 3 <= len(username) <= 64:
        raise SystemExit("Логин должен содержать от 3 до 64 символов")
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == username))
        if user and not args.reset_password:
            raise SystemExit("Администратор уже существует. Для смены пароля добавьте --reset-password")
        if not user and args.reset_password:
            raise SystemExit("Администратор не найден")
        password = getpass.getpass("Пароль (не меньше 12 символов): ")
        if len(password) < 12 or len(password) > 1024 or password != getpass.getpass("Повторите пароль: "):
            raise SystemExit("Пароли должны совпадать и содержать от 12 до 1024 символов")
        if user:
            user.password_hash = hash_password(password)
            db.execute(delete(AdminSession).where(AdminSession.user_id == user.id))
        else:
            db.add(User(username=username, password_hash=hash_password(password)))
        db.execute(delete(LoginAttempt).where(LoginAttempt.key == token_hash(username)))
        db.commit()
    print("Администратор сохранён. Пароль и сессии в вывод не попадают.")


if __name__ == "__main__":
    main()
