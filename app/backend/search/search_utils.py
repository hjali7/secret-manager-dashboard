from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Query
from sqlalchemy import or_, and_, desc, asc
from datetime import datetime

class SearchFilter:
    def __init__(self, query: Query):
        self.query = query
        self.filters = []
        self.sort_by = None
        self.sort_order = None

    def add_filter(self, field: str, operator: str, value: Any) -> 'SearchFilter':
        """Add a filter condition"""
        if operator == "eq":
            self.filters.append(getattr(self.query.model, field) == value)
        elif operator == "neq":
            self.filters.append(getattr(self.query.model, field) != value)
        elif operator == "gt":
            self.filters.append(getattr(self.query.model, field) > value)
        elif operator == "gte":
            self.filters.append(getattr(self.query.model, field) >= value)
        elif operator == "lt":
            self.filters.append(getattr(self.query.model, field) < value)
        elif operator == "lte":
            self.filters.append(getattr(self.query.model, field) <= value)
        elif operator == "like":
            self.filters.append(getattr(self.query.model, field).like(f"%{value}%"))
        elif operator == "ilike":
            self.filters.append(getattr(self.query.model, field).ilike(f"%{value}%"))
        elif operator == "in":
            self.filters.append(getattr(self.query.model, field).in_(value))
        return self

    def add_date_range(self, field: str, start_date: Optional[datetime] = None, 
                      end_date: Optional[datetime] = None) -> 'SearchFilter':
        """Add date range filter"""
        if start_date:
            self.filters.append(getattr(self.query.model, field) >= start_date)
        if end_date:
            self.filters.append(getattr(self.query.model, field) <= end_date)
        return self

    def add_sort(self, field: str, order: str = "asc") -> 'SearchFilter':
        """Add sorting"""
        self.sort_by = field
        self.sort_order = order
        return self

    def apply(self) -> Query:
        """Apply all filters and sorting"""
        if self.filters:
            self.query = self.query.filter(and_(*self.filters))
        
        if self.sort_by:
            sort_field = getattr(self.query.model, self.sort_by)
            if self.sort_order == "desc":
                self.query = self.query.order_by(desc(sort_field))
            else:
                self.query = self.query.order_by(asc(sort_field))
        
        return self.query

def apply_search_filters(query: Query, filters: Dict[str, Any]) -> Query:
    """Apply search filters from a dictionary"""
    search = SearchFilter(query)
    
    for field, conditions in filters.items():
        if isinstance(conditions, dict):
            for operator, value in conditions.items():
                search.add_filter(field, operator, value)
        else:
            search.add_filter(field, "eq", conditions)
    
    return search.apply() 