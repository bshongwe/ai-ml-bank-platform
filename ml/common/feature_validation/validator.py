"""
Feature Validation
Schema validation, quality checks, anomaly detection.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class FeatureValidator:
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def validate(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate features against schema."""
        errors = []
        errors.extend(self._check_schema(data))
        errors.extend(self._check_nulls(data))
        errors.extend(self._check_ranges(data))
        errors.extend(self._check_types(data))
        return len(errors) == 0, errors

    def _check_schema(self, data: pd.DataFrame) -> List[str]:
        """Check required columns exist."""
        errors = []
        required_cols = set(self.schema.get('required_columns', []))
        missing_cols = required_cols - set(data.columns)
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
        return errors

    def _check_nulls(self, data: pd.DataFrame) -> List[str]:
        """Check for unexpected nulls."""
        errors = []
        for col in self.schema.get('non_nullable', []):
            if col in data.columns and data[col].isnull().any():
                null_count = data[col].isnull().sum()
                errors.append(f"{col} has {null_count} null values")
        return errors

    def _check_ranges(self, data: pd.DataFrame) -> List[str]:
        """Check numeric ranges."""
        errors = []
        for col, bounds in self.schema.get('ranges', {}).items():
            if col in data.columns:
                min_val, max_val = bounds
                out_of_range = (
                    (data[col] < min_val) | (data[col] > max_val)
                ).sum()
                if out_of_range > 0:
                    errors.append(
                        f"{col} has {out_of_range} out-of-range values"
                    )
        return errors

    def _check_types(self, data: pd.DataFrame) -> List[str]:
        """Check data types."""
        errors = []
        for col, expected_type in self.schema.get('types', {}).items():
            if col in data.columns:
                if not pd.api.types.is_dtype_equal(
                    data[col].dtype, expected_type
                ):
                    errors.append(
                        f"{col} type mismatch: expected {expected_type}, "
                        f"got {data[col].dtype}"
                    )
        return errors

if __name__ == '__main__':
    schema = {
        'required_columns': ['feature1', 'feature2'],
        'non_nullable': ['feature1'],
        'ranges': {'feature1': (0, 100)},
        'types': {'feature1': 'float64'}
    }
    validator = FeatureValidator(schema)
    test_data = pd.DataFrame({
        'feature1': [1.0, 2.0, 150.0],
        'feature2': [10, 20, 30]
    })
    is_valid, errors = validator.validate(test_data)
    print(f"Valid: {is_valid}")
    for error in errors:
        print(f"  - {error}")
