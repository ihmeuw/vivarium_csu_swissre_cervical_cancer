"""Loads, standardizes and validates input data for the simulation.

Abstract the extract and transform pieces of the artifact ETL.
The intent here is to provide a uniform interface around this portion
of artifact creation. The value of this interface shows up when more
complicated data needs are part of the project. See the BEP project
for an example.

`BEP <https://github.com/ihmeuw/vivarium_gates_bep/blob/master/src/vivarium_gates_bep/data/loader.py>`_

.. admonition::

   No logging is done here. Logging is done in vivarium inputs itself and forwarded.
"""
from pathlib import Path

from gbd_mapping import causes, risk_factors, covariates
import numpy as np
import pandas as pd
from vivarium.framework.artifact import EntityKey
from vivarium_gbd_access import gbd
from vivarium_inputs import interface, utilities, utility_data, globals as vi_globals
from vivarium_inputs.mapping_extension import alternative_risk_factors

from vivarium_csu_swissre_cervical_cancer import paths, globals as project_globals


ARTIFACT_INDEX_COLUMNS = [
    'location',
    'sex',
    'age_start',
    'age_end',
    'year_start',
    'year_end',
    'draw',
]


def get_data(lookup_key: str, location: str) -> pd.DataFrame:
    """Retrieves data from an appropriate source.

    Parameters
    ----------
    lookup_key
        The key that will eventually get put in the artifact with
        the requested data.
    location
        The location to get data for.

    Returns
    -------
        The requested data.

    """
    mapping = {
        project_globals.POPULATION.STRUCTURE: load_population_structure,
        project_globals.POPULATION.AGE_BINS: load_age_bins,
        project_globals.POPULATION.DEMOGRAPHY: load_demographic_dimensions,
        project_globals.POPULATION.TMRLE: load_theoretical_minimum_risk_life_expectancy,
        project_globals.POPULATION.ACMR: load_acmr,
    }
    return mapping[lookup_key](lookup_key, location)


def load_population_structure(key: str, location: str) -> pd.DataFrame:
    def get_row(sex, year):
        return {
            'location': location,
            'sex': sex,
            'age_start': 0,
            'age_end': 95,
            'year_start': year,
            'year_end': year + 1,
            'value': 100,
        }

    # TODO there is an issue in vivarium_public_health.population.data_transformations.assign_demographic_proportions()
    #   where this fails if there is only one provided year
    return pd.DataFrame([
        get_row('Female', 2019),
        get_row('Female', 2020)
    ]).set_index(['location', 'sex', 'age_start', 'age_end', 'year_start', 'year_end'])


def load_age_bins(key: str, location: str) -> pd.DataFrame:
    return interface.get_age_bins()


def load_demographic_dimensions(key: str, location: str) -> pd.DataFrame:
    return pd.DataFrame([
        {
            'location': location,
            'sex': 'Female',
            'age_start': 0,
            'age_end': 95,
            'year_start': 2019,
            'year_end': 2020,
        },
    ]).set_index(['location', 'sex', 'age_start', 'age_end', 'year_start', 'year_end'])


def load_theoretical_minimum_risk_life_expectancy(key: str, location: str) -> pd.DataFrame:
    return interface.get_theoretical_minimum_risk_life_expectancy()


def load_standard_data(key: str, location: str) -> pd.DataFrame:
    key = EntityKey(key)
    entity = get_entity(key)
    return interface.get_measure(entity, key.measure, location)


def load_metadata(key: str, location: str):
    key = EntityKey(key)
    entity = get_entity(key)
    metadata = entity[key.measure]
    if hasattr(metadata, 'to_dict'):
        metadata = metadata.to_dict()
    return metadata


def load_acmr(key: str, location: str) -> pd.DataFrame:
    return _transform_raw_data(location, paths.RAW_ACMR_DATA_PATH, True)


def _load_em_from_meid(location, meid, measure):
    location_id = utility_data.get_location_id(location)
    data = gbd.get_modelable_entity_draws(meid, location_id)
    data = data[data.measure_id == vi_globals.MEASURES[measure]]
    data = utilities.normalize(data, fill_value=0)
    data = data.filter(vi_globals.DEMOGRAPHIC_COLUMNS + vi_globals.DRAW_COLUMNS)
    data = utilities.reshape(data)
    data = utilities.scrub_gbd_conventions(data, location)
    data = utilities.split_interval(data, interval_column='age', split_column_prefix='age')
    data = utilities.split_interval(data, interval_column='year', split_column_prefix='year')
    return utilities.sort_hierarchical_data(data)


# TODO - add project-specific data functions here
def _transform_raw_data(location: str, data_path: Path, is_log_data: bool) -> pd.DataFrame:
    processed_data = _transform_raw_data_preliminary(data_path, is_log_data)
    processed_data['location'] = location

    # Weight the covered provinces
    processed_data['value'] = (sum(processed_data[province] * weight for province, weight
                                   in project_globals.SWISSRE_LOCATION_WEIGHTS.items())
                               / sum(project_globals.SWISSRE_LOCATION_WEIGHTS.values()))

    processed_data = (
        processed_data
        # Remove province columns
        .drop([province for province in project_globals.SWISSRE_LOCATION_WEIGHTS.keys()], axis=1)
        # Set index to final columns and unstack with draws as columns
        .reset_index()
        .set_index(ARTIFACT_INDEX_COLUMNS)
        .unstack()
    )

    # Simplify column index and rename draw columns
    processed_data.columns = [c[1] for c in processed_data.columns]
    processed_data = processed_data.rename(columns={col: f'draw_{col}' for col in processed_data.columns})
    return processed_data


def _transform_raw_data_preliminary(data_path: Path, is_log_data: bool = False) -> pd.DataFrame:
    """Transforms data to a form with draws in the index and raw locations as columns"""
    raw_data: pd.DataFrame = pd.read_hdf(data_path)
    age_bins = gbd.get_age_bins().set_index('age_group_id')
    locations = gbd.get_location_ids().set_index('location_id')

    # Transform raw data from log space to linear space
    log_value_column = raw_data.columns[0]
    raw_data['value'] = np.exp(raw_data[log_value_column]) if is_log_data else raw_data[log_value_column]

    processed_data = (
        raw_data
        .reset_index()
        # Set index to match age_bins and join
        .set_index('age_group_id')
        .join(age_bins, how='left')
        .reset_index()
        # Set index to match location and join
        .set_index('location_id')
        .join(locations, how='left')
        .reset_index()
        .rename(columns={
            'age_group_years_start': 'age_start',
            'age_group_years_end': 'age_end',
            'year_id': 'year_start',
            'location_name': 'location',
        })
    )

    # Filter locations down to the regions covered by SwissRE
    swissre_locations_mask = processed_data['location'].isin(project_globals.SWISSRE_LOCATION_WEIGHTS)
    processed_data = processed_data[swissre_locations_mask]

    # Add year end column and create sex column with strings rather than ids
    processed_data['year_end'] = processed_data['year_start'] + 1
    processed_data['sex'] = processed_data['sex_id'].apply(lambda x: 'Male' if x == 1 else 'Female')

    # Drop unneeded columns
    processed_data = processed_data.drop(
        ['age_group_id', 'age_group_name', 'location_id', log_value_column, 'sex_id'], axis=1
    )

    # Make draw column numeric
    processed_data['draw'] = pd.to_numeric(processed_data['draw'])

    # Set index and unstack data with locations as columns
    processed_data = (
        processed_data
        .set_index(ARTIFACT_INDEX_COLUMNS)
        .unstack(level=0)
    )

    # Simplify column index and add back location column
    processed_data.columns = [c[1] for c in processed_data.columns]
    return processed_data


def get_entity(key: str):
    # Map of entity types to their gbd mappings.
    type_map = {
        'cause': causes,
        'covariate': covariates,
        'risk_factor': risk_factors,
        'alternative_risk_factor': alternative_risk_factors
    }
    key = EntityKey(key)
    return type_map[key.type][key.name]
