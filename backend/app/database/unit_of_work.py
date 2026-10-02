from sqlalchemy.orm import Session


class UnitOfWork:
    """
    Owns the transaction boundary for one Session.

    Repositories only flush(); a service wraps its writes in ``with self.uow:``
    and the block commits on success or rolls back on any exception, so several
    writes succeed or fail together.

    Blocks can nest (a service method that uses the UoW may be called from
    another one that already opened it): only the outermost block commits, and
    an exception anywhere rolls back the whole outer transaction.
    """

    def __init__(self, db: Session):
        self.db = db
        self._depth = 0

    def __enter__(self) -> "UnitOfWork":
        self._depth += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._depth -= 1
        if exc_type is not None:
            # Roll back at the first level the error passes through; outer levels
            # see the same exception and the session is already clean.
            self.rollback()
            return False
        if self._depth == 0:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
        return False

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
