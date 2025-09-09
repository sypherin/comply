import pytest
from app.models.schemas import validate_headers, REQUIRED_HEADERS, normalize_status_values

def test_validate_headers_ok():
    cols = REQUIRED_HEADERS.copy()
    validate_headers(cols)

def test_validate_headers_missing():
    cols = REQUIRED_HEADERS.copy()
    cols.remove('Org')
    with pytest.raises(ValueError):
        validate_headers(cols)

@pytest.mark.parametrize('val,expected', [
    ('Complete','Completed'),
    ('completed','Completed'),
    ('Done','Completed'),
    ('In Progress','In Progress'),
    ('Not Started','Not Started'),
    ('unknown','unknown'),
])
def test_normalize_status_values(val, expected):
    assert normalize_status_values(val) == expected
