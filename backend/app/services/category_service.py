from app.core.exceptions import (
    CategoryAccessDeniedException,
    CategoryAlreadyExistsException,
    CategoryInUseException,
    CategoryNotFoundException,
)
from app.core.logging import get_logger
from app.database.unit_of_work import UnitOfWork
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository

logger = get_logger(__name__)


class CategoryService:
    def __init__(self, category_repository: CategoryRepository, uow: UnitOfWork):
        self.category_repository = category_repository
        self.uow = uow

    def list_category(self, user_id: int) -> list[Category]:
        """
        Fetches all the available categories for a user
        """
        return self.category_repository.get_all_for_user(user_id)

    def get_category(self, user_id: int, category_id: int):
        """
        Gets a category by category_id
        """
        category = self.category_repository.get_by_id(category_id)

        if not category:
            raise CategoryNotFoundException()

        if category.user_id is not None and category.user_id != user_id:
            raise CategoryAccessDeniedException()

        return category

    def create_category(self, user_id: int, name: str, category_type: str) -> Category:

        available_categories = self.list_category(user_id)

        for category in available_categories:
            if category.name.lower() == name.lower() and category.category_type == category_type:
                raise CategoryAlreadyExistsException()

        with self.uow:
            category = self.category_repository.create(
                name=name, category_type=category_type, user_id=user_id
            )
        logger.info("category.created", category_id=category.id)
        return category

    def update_category(
        self,
        user_id: int,
        category_id: int,
        name: str | None = None,
        category_type: str | None = None,
    ) -> Category:

        category = self.category_repository.get_by_id(category_id)

        if not category:
            raise CategoryNotFoundException()

        if category.user_id != user_id:
            raise CategoryAccessDeniedException()

        updates = {}

        if name is not None:
            updates["name"] = name

        if category_type is not None:
            updates["category_type"] = category_type

        if not updates:
            return category

        ## Duplicate check
        name_check = updates.get("name", category.name)
        category_type_check = updates.get(
            "category_type",
            category.category_type,
        )

        all_categories = self.list_category(user_id)
        for cat in all_categories:
            if cat.id == category_id:
                continue
            if cat.name.lower() == name_check.lower() and cat.category_type == category_type_check:
                raise CategoryAlreadyExistsException()

        with self.uow:
            return self.category_repository.update(category=category, **updates)

    def delete_category(self, user_id: int, category_id: int):
        """
        Deletes a custom category. Refuses (409) while any transaction still uses it, so a delete
        can never silently take transactions with it.
        """

        category = self.category_repository.get_by_id(category_id)

        if not category:
            raise CategoryNotFoundException()

        if category.user_id != user_id:
            raise CategoryAccessDeniedException()

        in_use = self.category_repository.count_transactions(category_id)
        if in_use:
            logger.info("category.delete_blocked", category_id=category_id, transactions=in_use)
            raise CategoryInUseException(
                f"Category is used by {in_use} transaction(s). Move or delete them first."
            )

        with self.uow:
            self.category_repository.delete(category=category)
        logger.info("category.deleted", category_id=category_id)
