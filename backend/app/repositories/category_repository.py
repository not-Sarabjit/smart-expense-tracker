from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from app.models.category import Category
from app.models.user import User


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_for_user(self, user_id: int) -> list[Category]:
        '''
        Takes user ID to fetch all the categories available for a user ( Custom and Default )
        '''

        statement = select(Category).where(or_(Category.user_id == user_id, Category.user_id == None))
        return self.db.scalars(statement).all()

    def get_by_id(self, id: int) -> Category | None:
        '''
        Takes category id to get the Category.
        '''

        statement = select(Category).where(Category.id == id)
        return self.db.scalars(statement).first()

    def create(self, name: str, category_type: str, user_id: int) -> Category:
        '''
        Takes name, category_type and user id to create a new custom category for the user
        '''
        category = Category(name = name, category_type = category_type, user_id = user_id)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)

        return category

    def update(self, category: Category, **kwargs) -> Category:
        '''
        Takes in an existing category object and key, val pairs to update. Returns the updated category object
        '''
        for key, val in kwargs.items():
            setattr(category, key, val)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        '''
        Takes category object and delets the category ( Only Custom )
        '''
        
        self.db.delete(category)
        self.db.commit()