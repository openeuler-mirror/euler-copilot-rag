from pkgutil import ModuleInfo, walk_packages
from types import ModuleType
from typing import Iterable

from tests import fixtures


def _get_packages_in_module(module: ModuleType) -> Iterable[ModuleInfo]:
    return walk_packages(module.__path__, prefix=module.__name__ + '.')


def _get_package_paths_in_module(module: ModuleType) -> Iterable[str]:
    return [package.name for package in _get_packages_in_module(module)]


pytest_plugins = _get_package_paths_in_module(fixtures)

