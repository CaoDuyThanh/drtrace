import sys
from pathlib import Path
import pytest

# Ensure project root is on import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.version_downgrade import (
	downgrade_major,
	downgrade_minor,
	downgrade_patch,
	parse_version,
	format_version,
	validate_version_bounds,
)


class TestVersionDowngrade:
	def test_downgrade_major(self):
		assert downgrade_major(2, 3, 1) == (1, 0, 0)
		assert downgrade_major(5, 10, 20) == (4, 0, 0)

	def test_downgrade_minor(self):
		assert downgrade_minor(2, 3, 1) == (2, 2, 0)
		assert downgrade_minor(5, 10, 20) == (5, 9, 0)

	def test_downgrade_patch(self):
		assert downgrade_patch(2, 3, 1) == (2, 3, 0)
		assert downgrade_patch(5, 10, 20) == (5, 10, 19)

	def test_downgrade_major_to_zero(self):
		assert downgrade_major(1, 0, 0) == (0, 0, 0)

	def test_downgrade_minor_rollover(self):
		assert downgrade_minor(0, 1, 0) == (0, 0, 0)

	def test_downgrade_patch_rollover(self):
		assert downgrade_patch(0, 0, 1) == (0, 0, 0)

	def test_downgrade_patch_cascade_to_minor(self):
		# When patch is 0 and minor > 0, decrement minor
		assert downgrade_patch(1, 1, 0) == (1, 0, 0)
		assert downgrade_patch(2, 3, 0) == (2, 2, 0)

	def test_downgrade_minor_cascade_to_major(self):
		# When minor is 0 and major > 0, decrement major
		assert downgrade_minor(1, 0, 0) == (0, 0, 0)
		assert downgrade_minor(2, 0, 5) == (1, 0, 0)

	def test_downgrade_patch_cannot_cascade_below_zero(self):
		# At 0.0.0, cannot downgrade patch
		with pytest.raises(ValueError, match="Cannot downgrade patch from 0.0.0"):
			downgrade_patch(0, 0, 0)

	def test_downgrade_minor_cannot_cascade_below_zero(self):
		# At 0.0.X, cannot downgrade minor
		with pytest.raises(ValueError, match="Cannot downgrade minor from 0.0.5"):
			downgrade_minor(0, 0, 5)

	def test_downgrade_major_cannot_go_below_zero(self):
		# At 0.X.X, cannot downgrade major
		with pytest.raises(ValueError, match="Cannot downgrade major from 0.5.1"):
			downgrade_major(0, 5, 1)
		assert validate_version_bounds(0, 0, 0) is True
		assert validate_version_bounds(-1, 0, 0) is False
		assert validate_version_bounds(0, -1, 0) is False
		assert validate_version_bounds(0, 0, -1) is False


class TestVersionParsing:
	def test_parse_version(self):
		assert parse_version("2.3.1") == (2, 3, 1)
		assert parse_version("0.0.0") == (0, 0, 0)
		assert parse_version("10.20.30") == (10, 20, 30)

	def test_parse_invalid_version(self):
		with pytest.raises(ValueError):
			parse_version("1.2")
		with pytest.raises(ValueError):
			parse_version("1.2.a")

	def test_format_version(self):
		assert format_version(2, 3, 1) == "2.3.1"
		assert format_version(0, 0, 0) == "0.0.0"

	def test_round_trip_major(self):
		original = "2.3.1"
		major, minor, patch = parse_version(original)
		n_major, _, _ = downgrade_major(major, minor, patch)
		new_version = format_version(n_major, 0, 0)
		assert new_version == "1.0.0"
 

