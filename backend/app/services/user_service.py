from app.repositories.user_repository import UserRepository
from app.core.exceptions import (
    UserNotFoundException,
    EmailAlreadyExistsException,
)

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_profile(self, user_id: int):

        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return user

    def update_profile(
            self,
            user_id: int,
            first_name: str | None = None,
            last_name: str | None = None,
            email: str | None = None
            ):
        '''
        Updates any of first_name, last_name and email if provided with user_id
        '''

        user = self.user_repository.get_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        updates = {}

        if first_name is not None and first_name != user.first_name:
            updates['first_name'] = first_name

        if last_name is not None and user.last_name != last_name:
            updates['last_name'] = last_name

        if email and user.email != email:

            if self.user_repository.get_by_email(email):
                raise EmailAlreadyExistsException()
            
            updates['email'] = email

        if updates:
            user = self.user_repository.update(user, updates)

        return user