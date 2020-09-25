import click
import pandas as pd
import numpy as np

from typing import NamedTuple, Union, List
from pathlib import Path
from loguru import logger
from scipy.stats import truncnorm

from vivarium.framework.randomness import get_hash

from vivarium_csu_swissre_cervical_cancer import metadata as md


class TruncnormDist:
    """Defines an instance of a truncated normal distribution.
    Parameters
    ----------
    mean
        mean of truncnorm distribution
    sd
        standard deviation of truncnorm distribution
    lower
        lower bound of truncnorm distribution
    upper
        upper bound of truncnorm distribution
    Returns
    -------
        An object with parameters for scipy.stats.truncnorm
    """

    def __init__(self, name, mean, sd, lower=0.0, upper=1.0, key=None):
        self.name = name
        self.a = (lower - mean) / sd if sd else 0
        self.b = (upper - mean) / sd if sd else 0
        self.mean = mean
        self.sd = sd
        self.key = key if key else name

    def get_random_variable(self, draw: int) -> float:
        """Gets a single random draw from a truncated normal distribution.
        Parameters
        ----------
        draw
            Draw for this simulation
        Returns
        -------
            The random variate from the truncated normal distribution.
        """
        # Handle degenerate distribution
        if not self.sd:
            return self.mean

        np.random.seed(get_hash(f'{self.key}_draw_{draw}'))
        return truncnorm.rvs(self.a, self.b, self.mean, self.sd)

    def ppf(self, quantiles: pd.Series) -> pd.Series:
        return truncnorm(self.a, self.b, self.mean, self.sd).ppf(quantiles)


def len_longest_location() -> int:
    """Returns the length of the longest location in the project.

    Returns
    -------
       Length of the longest location in the project.
    """
    return len(max(md.LOCATIONS, key=len))


def sanitize_location(location: str):
    """Cleans up location formatting for writing and reading from file names.

    Parameters
    ----------
    location
        The unsanitized location name.

    Returns
    -------
        The sanitized location name (lower-case with white-space and
        special characters removed.

    """
    # FIXME: Should make this a reversible transformation.
    return location.replace(" ", "_").replace("'", "_").lower()


def delete_if_exists(*paths: Union[Path, List[Path]], confirm=False):
    paths = paths[0] if isinstance(paths[0], list) else paths
    existing_paths = [p for p in paths if p.exists()]
    if existing_paths:
        if confirm:
            # Assumes all paths have the same root dir
            root = existing_paths[0].parent
            names = [p.name for p in existing_paths]
            click.confirm(f"Existing files {names} found in directory {root}. Do you want to delete and replace?",
                          abort=True)
        for p in existing_paths:
            logger.info(f'Deleting artifact at {str(p)}.')
            p.unlink()

