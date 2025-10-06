"""Base repository with common CRUD operations."""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Type, TypeVar

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Query

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Generic repository providing common database operations."""

    def __init__(self, db: SQLAlchemy, model: Type[ModelType]) -> None:
        """Initialize repository with database session and model class.

        Args:
            db: SQLAlchemy database instance
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Retrieve a single record by primary key.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return self.db.session.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieve all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        return self.db.session.query(self.model).offset(skip).limit(limit).all()

    def get_by_filter(self, **filters: Any) -> List[ModelType]:
        """Retrieve records matching filter criteria.

        Args:
            **filters: Field-value pairs to filter by

        Returns:
            List of matching model instances
        """
        return self.db.session.query(self.model).filter_by(**filters).all()

    def get_one_by_filter(self, **filters: Any) -> Optional[ModelType]:
        """Retrieve single record matching filter criteria.

        Args:
            **filters: Field-value pairs to filter by

        Returns:
            Model instance or None if not found
        """
        return self.db.session.query(self.model).filter_by(**filters).first()

    def create(self, instance: Optional[ModelType] = None, **data: Any) -> ModelType:
        """Create a new record.

        Args:
            instance: Model instance to add (if provided, data kwargs are ignored)
            **data: Field-value pairs for the new record (if instance not provided)

        Returns:
            Created model instance
        """
        if instance is None:
            instance = self.model(**data)  # type: ignore
        self.db.session.add(instance)
        return instance

    def update(self, instance: ModelType, **data: Any) -> ModelType:
        """Update an existing record.

        Args:
            instance: Model instance to update
            **data: Field-value pairs to update

        Returns:
            Updated model instance
        """
        for field, value in data.items():
            setattr(instance, field, value)
        return instance

    def delete(self, instance: ModelType) -> None:
        """Delete a record.

        Args:
            instance: Model instance to delete
        """
        self.db.session.delete(instance)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.session.rollback()

    def flush(self) -> None:
        """Flush pending changes without committing."""
        self.db.session.flush()

    def query(self) -> Query:
        """Get a query object for advanced queries.

        Returns:
            SQLAlchemy Query object
        """
        return self.db.session.query(self.model)
