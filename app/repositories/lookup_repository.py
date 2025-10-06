"""Lookup repository for database operations on lookup tables."""

from __future__ import annotations

from typing import Dict, List, Optional

from flask_sqlalchemy import SQLAlchemy

from app.models import LookupData
from app.repositories.base_repository import BaseRepository


class LookupRepository(BaseRepository[LookupData]):
    """Repository for LookupData entity operations."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize lookup repository.

        Args:
            db: SQLAlchemy database instance
        """
        super().__init__(db, LookupData)

    def get_by_field(self, field: str, active_only: bool = True) -> List[LookupData]:
        """Get all lookup values for a specific field.

        Args:
            field: Field name (Organization, LOB, Environment, etc.)
            active_only: Return only active lookup values

        Returns:
            List of lookup data
        """
        query = self.query().filter_by(field=field)
        if active_only:
            query = query.filter_by(is_active=True)

        return query.all()

    def get_by_value(self, field: str, value: str) -> Optional[LookupData]:
        """Get specific lookup by field and value.

        Args:
            field: Field name
            value: Value to search for

        Returns:
            LookupData instance or None
        """
        return self.get_one_by_filter(field=field, value=value)

    def get_by_abbreviation(
        self, field: str, abbreviation: str
    ) -> Optional[LookupData]:
        """Get specific lookup by field and abbreviation.

        Args:
            field: Field name
            abbreviation: Abbreviation to search for

        Returns:
            LookupData instance or None
        """
        return self.get_one_by_filter(field=field, abbreviation=abbreviation)

    def value_exists(self, field: str, value: str) -> bool:
        """Check if a lookup value exists.

        Args:
            field: Field name
            value: Value to check

        Returns:
            True if exists, False otherwise
        """
        return self.get_by_value(field, value) is not None

    def abbreviation_exists(self, field: str, abbreviation: str) -> bool:
        """Check if an abbreviation exists for a field.

        Args:
            field: Field name
            abbreviation: Abbreviation to check

        Returns:
            True if exists, False otherwise
        """
        return self.get_by_abbreviation(field, abbreviation) is not None

    def get_organizations(self, active_only: bool = True) -> List[LookupData]:
        """Get all organizations.

        Args:
            active_only: Return only active organizations

        Returns:
            List of organization lookup data
        """
        return self.get_by_field("Organization", active_only)

    def get_lobs(self, active_only: bool = True) -> List[LookupData]:
        """Get all Lines of Business.

        Args:
            active_only: Return only active LOBs

        Returns:
            List of LOB lookup data
        """
        return self.get_by_field("LOB", active_only)

    def get_environments(self, active_only: bool = True) -> List[LookupData]:
        """Get all environments.

        Args:
            active_only: Return only active environments

        Returns:
            List of environment lookup data
        """
        return self.get_by_field("Environment", active_only)

    def get_all_fields(self) -> List[str]:
        """Get list of all distinct fields in lookup data.

        Returns:
            List of field names
        """
        return [
            row[0] for row in self.db.session.query(LookupData.field).distinct().all()
        ]

    def get_all_by_field_grouped(
        self, active_only: bool = True
    ) -> Dict[str, List[LookupData]]:
        """Get all lookup data grouped by field.

        Args:
            active_only: Return only active lookup values

        Returns:
            Dictionary mapping field name to list of lookup data
        """
        fields = self.get_all_fields()
        result: Dict[str, List[LookupData]] = {}

        for field in fields:
            result[field] = self.get_by_field(field, active_only)

        return result

    def deactivate_lookup(self, lookup_id: int) -> bool:
        """Deactivate a lookup value (soft delete).

        Args:
            lookup_id: ID of lookup to deactivate

        Returns:
            True if successful, False otherwise
        """
        lookup = self.get_by_id(lookup_id)
        if lookup:
            lookup.is_active = False
            self.commit()
            return True
        return False

    def activate_lookup(self, lookup_id: int) -> bool:
        """Activate a previously deactivated lookup value.

        Args:
            lookup_id: ID of lookup to activate

        Returns:
            True if successful, False otherwise
        """
        lookup = self.get_by_id(lookup_id)
        if lookup:
            lookup.is_active = True
            self.commit()
            return True
        return False
