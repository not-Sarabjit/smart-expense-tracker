from app.repositories.category_repository import CategoryRepository
from app.models.category import Category




class CategoryService:
    def __init__(self, category_repository: CategoryRepository):
        self.category_repository = category_repository


    def list_category(self, user_id: int) -> list[Category]:

        '''
        Fetches all the available categories for a user
        '''
        return self.category_repository.get_all_for_user(user_id)

    def get_category(self, user_id: int, category_id: int) :
        '''
        Gets a category by category_id
        '''
        category = self.category_repository.get_by_id(category_id)

        if not category:
            raise ValueError('Category does not exist')

        if category.user_id != None and category.user_id != user_id:
            raise ValueError('Category does not exist for this user')

        return category

    def create_category(self, user_id: int, name: str, category_type: str ) -> Category:

        # Validation for null names
        name = name.strip()
        if not name:
            raise ValueError('Category Name cannot be empty')

        available_categories = self.list_category(user_id)

        for category in available_categories:
            if category.name.lower() == name.lower() and category.category_type == category_type:
                raise ValueError('Category already exists')
            

        new_category = self.category_repository.create(name = name, category_type = category_type, user_id = user_id )
        return new_category

    def update_category(self, user_id: int, category_id : int, name: str | None = None, category_type: str | None = None) -> Category:

        category = self.category_repository.get_by_id(category_id)

        if not category:
            raise ValueError('Category does not exist')

        if category.user_id != user_id:
            raise ValueError('Cannot update default Category')

        updates = {}

        # Name validation
        if name is not None:
            name = name.strip()
            
            if name == '':
                raise ValueError('Name cannot be empty')
            
            if name != category.name:
                updates['name'] = name

        if category_type is not None:
            if category_type != category.category_type:
                updates['category_type'] = category_type

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
            if (
                cat.name.lower() == name_check.lower()
                and cat.category_type == category_type_check
                ):
                raise ValueError("Category already exists")

        category = self.category_repository.update(category=category, **updates)

        return category
            
        

    def delete_category(self, user_id: int, category_id: int):

        category = self.category_repository.get_by_id(category_id)

        if not category:
            raise ValueError('Category does not exist')

        if category.user_id != user_id:
            raise ValueError('Cannot delete default categories')

        self.category_repository.delete(category=category)        
