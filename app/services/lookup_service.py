"""Lookup service - business logic for lookup data management."""

from __future__ import annotations

from typing import Dict, List, Optional

from flask_sqlalchemy import SQLAlchemy

from app.models import LookupData
from app.repositories import LookupRepository


class LookupService:
    """Service for lookup data business logic."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize lookup service.

        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
        self.lookup_repo = LookupRepository(db)

    def get_lookup_by_field(
        self, field: str, active_only: bool = True
    ) -> List[LookupData]:
        """Get lookup data for a specific field.

        Args:
            field: Field name (Organization, LOB, Environment, etc.)
            active_only: Return only active values

        Returns:
            List of lookup data
        """
        return self.lookup_repo.get_by_field(field, active_only)

    def get_all_lookups(self, active_only: bool = True) -> Dict[str, List[LookupData]]:
        """Get all lookup data grouped by field.

        Args:
            active_only: Return only active values

        Returns:
            Dictionary mapping field name to lookup data list
        """
        return self.lookup_repo.get_all_by_field_grouped(active_only)

    def get_organizations(self, active_only: bool = True) -> List[LookupData]:
        """Get all organizations.

        Args:
            active_only: Return only active organizations

        Returns:
            List of organization lookup data
        """
        return self.lookup_repo.get_organizations(active_only)

    def get_lobs(self, active_only: bool = True) -> List[LookupData]:
        """Get all Lines of Business.

        Args:
            active_only: Return only active LOBs

        Returns:
            List of LOB lookup data
        """
        return self.lookup_repo.get_lobs(active_only)

    def get_environments(self, active_only: bool = True) -> List[LookupData]:
        """Get all environments.

        Args:
            active_only: Return only active environments

        Returns:
            List of environment lookup data
        """
        return self.lookup_repo.get_environments(active_only)

    def create_lookup(
        self, field: str, value: str, abbreviation: str, is_active: bool = True
    ) -> LookupData:
        """Create a new lookup value.

        Args:
            field: Field name
            value: Display value
            abbreviation: Short abbreviation
            is_active: Whether the lookup is active

        Returns:
            Created lookup data

        Raises:
            ValueError: If value or abbreviation already exists
        """
        # Check for duplicates
        if self.lookup_repo.value_exists(field, value):
            raise ValueError(f"Value '{value}' already exists for field '{field}'")

        if self.lookup_repo.abbreviation_exists(field, abbreviation):
            raise ValueError(
                f"Abbreviation '{abbreviation}' already exists for field '{field}'"
            )

        lookup = LookupData(
            field=field, value=value, abbreviation=abbreviation, is_active=is_active
        )

        created = self.lookup_repo.create(lookup)
        self.lookup_repo.commit()
        return created

    def update_lookup(
        self,
        lookup_id: int,
        value: Optional[str] = None,
        abbreviation: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> LookupData:
        """Update an existing lookup value.

        Args:
            lookup_id: ID of lookup to update
            value: New display value
            abbreviation: New abbreviation
            is_active: New active status

        Returns:
            Updated lookup data

        Raises:
            ValueError: If lookup not found or duplicate detected
        """
        lookup = self.lookup_repo.get_by_id(lookup_id)
        if not lookup:
            raise ValueError(f"Lookup {lookup_id} not found")

        # Check for duplicates if updating value or abbreviation
        if value and value != lookup.value:
            if self.lookup_repo.value_exists(lookup.field, value):
                raise ValueError(
                    f"Value '{value}' already exists for field '{lookup.field}'"
                )
            lookup.value = value

        if abbreviation and abbreviation != lookup.abbreviation:
            if self.lookup_repo.abbreviation_exists(lookup.field, abbreviation):
                raise ValueError(
                    f"Abbreviation '{abbreviation}' already exists for field '{lookup.field}'"
                )
            lookup.abbreviation = abbreviation

        if is_active is not None:
            lookup.is_active = is_active

        self.lookup_repo.commit()
        return lookup

    def delete_lookup(self, lookup_id: int) -> bool:
        """Delete (deactivate) a lookup value.

        Args:
            lookup_id: ID of lookup to delete

        Returns:
            True if successful, False otherwise
        """
        return self.lookup_repo.deactivate_lookup(lookup_id)

    def activate_lookup(self, lookup_id: int) -> bool:
        """Activate a previously deactivated lookup value.

        Args:
            lookup_id: ID of lookup to activate

        Returns:
            True if successful, False otherwise
        """
        return self.lookup_repo.activate_lookup(lookup_id)

    def get_lookup_fields(self) -> List[str]:
        """Get list of all distinct lookup fields.

        Returns:
            List of field names
        """
        return self.lookup_repo.get_all_fields()
