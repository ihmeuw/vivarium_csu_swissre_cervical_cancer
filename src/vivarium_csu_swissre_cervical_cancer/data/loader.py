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

import numpy as np
import pandas as pd
from gbd_mapping import causes, risk_factors, covariates
from vivarium.framework.artifact import EntityKey
from vivarium_gbd_access import gbd
from vivarium_inputs import interface, utilities as vi_utils, utility_data, globals as vi_globals
from vivarium_inputs.mapping_extension import alternative_risk_factors

from vivarium_csu_swissre_cervical_cancer import paths, data_keys, data_values, utilities, metadata

ARTIFACT_INDEX_COLUMNS = [
    'location',
    'sex',
    'age_start',
    'age_end',
    'year_start',
    'year_end'
]

# TODO: get final number (this is temporary)
BCC_DURATION = 14.5


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
        data_keys.POPULATION.STRUCTURE: load_population_structure,
        data_keys.POPULATION.AGE_BINS: load_age_bins,
        data_keys.POPULATION.DEMOGRAPHY: load_demographic_dimensions,
        data_keys.POPULATION.TMRLE: load_theoretical_minimum_risk_life_expectancy,
        data_keys.POPULATION.ACMR: load_acmr,

        # data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE: load_hrhpv_prevalence,
        data_keys.CERVICAL_CANCER.BCC_PREVALENCE: load_prevalence,
        data_keys.CERVICAL_CANCER.PREVALENCE: load_prevalence,
        # data_keys.CERVICAL_CANCER.HRHPV_INCIDENCE_RATE: ,
        data_keys.CERVICAL_CANCER.BCC_HPV_POS_INCIDENCE_RATE: load_incidence_rate,
        data_keys.CERVICAL_CANCER.BCC_HPV_NEG_INCIDENCE_RATE: load_incidence_rate,
        data_keys.CERVICAL_CANCER.INCIDENCE_RATE: load_incidence_rate,
        data_keys.CERVICAL_CANCER.DISABILITY_WEIGHT: load_disability_weight,
        data_keys.CERVICAL_CANCER.EMR: load_emr,
        data_keys.CERVICAL_CANCER.CSMR: load_csmr,
        data_keys.CERVICAL_CANCER.RESTRICTIONS: load_metadata
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


def load_prevalence(key: str, location: str) -> pd.DataFrame:
    """Computes prevalence values for key at location."""
    base_prevalence = _transform_raw_data(location, paths.RAW_PREVALENCE_DATA_PATH, False)
    if key == data_keys.CERVICAL_CANCER.BCC_PREVALENCE:
        # Read from CSV, data from model document
        prev_ratio = pd.read_csv(paths.BCC_PREVALENCE_RATIO_PATH)
        prev_ratio["age_start"], prev_ratio["age_end"] = [pd.to_numeric(col) for col in
                                                          prev_ratio["age_group"].str.split("_to_").str]
        prev_ratio = prev_ratio.set_index(['age_start', 'age_end'])
        base_prevalence = base_prevalence.reset_index().set_index([
            'age_start', 'age_end', 'location', 'sex', 'year_start', 'year_end'
        ])
        base_prevalence = (
            base_prevalence
            .multiply(prev_ratio['prevalence_ratio'], axis=0)
            .reset_index()
            .set_index(ARTIFACT_INDEX_COLUMNS)
        )
        return base_prevalence
    elif key == data_keys.CERVICAL_CANCER.PREVALENCE:
        prev_ratio = 1
        return base_prevalence * prev_ratio
    else:
        raise ValueError(f'Unrecognized key {key}')


def load_prevalence_hrhpv(artifact_idx) -> pd.DataFrame:
    df = pd.read_hdf(paths.HRHPV_PREVALENCE_PATH)
    df = df.set_index(artifact_idx)
    return df


def old_load_prevalence_hrhpv(artifact_idx) -> pd.DataFrame:
    # TODO: Update this for Nicole Y's updates per Slack (https://ihme.slack.com/archives/GTH3RKQM6/p1602028173125200)
    """Get hrhpv prevalence mapping"""
    lookup_prev = pd.DataFrame({"group": ["<25", "25-45", ">45"]})
    for i in range(0, 1000):
        lookup_prev[f"draw_{i}"] = lookup_prev["group"].apply(
            lambda x: data_values.PREV_DISTS_HPV[x].get_random_variable(i)
        )
    lookup_prev = lookup_prev.set_index("group")

    def find_prev_group(age_end):
        if (age_end < 25):
            return lookup_prev.at["<25", f"draw_{i}"]
        elif (age_end <= 45):
            return lookup_prev.at["25-45", f"draw_{i}"]
        else:
            return lookup_prev.at[">45", f"draw_{i}"]

    prev_dist = pd.DataFrame(index=artifact_idx)
    prev_dist = prev_dist.reset_index()
    for i in range(0, 1000):
        prev_dist[f"draw_{i}"] = prev_dist["age_end"].apply(find_prev_group)
    return prev_dist.set_index(ARTIFACT_INDEX_COLUMNS)


def load_rr_hrhpv(columns) -> pd.Series:
    """Get random variables based on distribution for RR hrHPV, columns should be those in the prevalence df"""
    per_draw_rr = pd.Series([utilities.get_lognormal_random_variable(*data_values.RR_HRHPV_PARAMS, x) for x in range(0, 1000)], index=columns)
    return per_draw_rr


def load_paf(prev, rr) -> pd.DataFrame:
    # Calculates PAF: prev_hrHPV×(RR_hrHPV−1)/prev_hrHPV×(RR_hrHPV−1)+1
    rr_minus_one = rr - 1
    num = prev.multiply(rr_minus_one, axis=1)
    return num / (num + 1)


def load_incidence_rate(key: str, location: str):
    """Get the incidence rate given a key."""
    bcc_prevalence = load_prevalence(data_keys.CERVICAL_CANCER.BCC_PREVALENCE,
                                     location)  # TODO: optimization: check artifact for this instead of rebuilding
    if key == data_keys.CERVICAL_CANCER.INCIDENCE_RATE:
        # i_ICC = (incidence_c432/prev_BCC)
        incidence_rate = _transform_raw_data(location, paths.RAW_INCIDENCE_RATE_DATA_PATH, False)
        incidence_rate = incidence_rate / bcc_prevalence
    else:
        hrhpv_prevalence = load_prevalence_hrhpv(bcc_prevalence.index)
        hrhpv_rr = load_rr_hrhpv(bcc_prevalence.columns)
        paf = load_paf(hrhpv_prevalence, hrhpv_rr)
        if key == data_keys.CERVICAL_CANCER.BCC_HPV_POS_INCIDENCE_RATE:
            # incidence rate = (((prev_BCC/DURATION_BCC)×(1−PAF)×RR_hrHPV)/prev_hrHPV)
            incidence_rate = (bcc_prevalence / BCC_DURATION) * (1 - paf) * hrhpv_rr
            incidence_rate = incidence_rate / hrhpv_prevalence
        elif key == data_keys.CERVICAL_CANCER.BCC_HPV_NEG_INCIDENCE_RATE:
            # incidence rate = ((prev_BCC/DURATION_BCC)×(1−PAF)) / prev_susceptible
            # prev_susceptible = 1 - (prev_hrHPV + prev_BCC + prev_c432)
            prev_c432 = _transform_raw_data(location, paths.RAW_PREVALENCE_DATA_PATH, False)
            incidence_rate = (bcc_prevalence / BCC_DURATION) * (1 - paf)
            incidence_rate = incidence_rate / (1 - (hrhpv_prevalence + bcc_prevalence + prev_c432))
        else:
            raise ValueError(f'Unrecognized key {key}')

    return incidence_rate


def load_disability_weight(key: str, location: str):
    """Loads disability weights, weighting by subnational location for
    invasive cervical cancer"""
    if key == data_keys.CERVICAL_CANCER.DISABILITY_WEIGHT:
        location_weighted_disability_weight = 0
        for swissre_location, location_weight in data_keys.SWISSRE_LOCATION_WEIGHTS.items():
            prevalence_disability_weight = 0
            total_sequela_prevalence = 0
            for sequela in causes.cervical_cancer.sequelae:
                # Get prevalence and disability weight for location and sequela
                prevalence = interface.get_measure(sequela, 'prevalence', swissre_location)
                prevalence = prevalence.reset_index()
                prevalence["location"] = metadata.LOCATIONS[0]
                prevalence = prevalence.set_index(ARTIFACT_INDEX_COLUMNS)
                disability_weight = interface.get_measure(sequela, 'disability_weight', swissre_location)
                disability_weight = disability_weight.reset_index()
                disability_weight["location"] = metadata.LOCATIONS[0]
                disability_weight = disability_weight.set_index(ARTIFACT_INDEX_COLUMNS)
                # Apply prevalence weight
                prevalence_disability_weight += prevalence * disability_weight
                total_sequela_prevalence += prevalence

            # Calculate disability weight and apply location weight
            disability_weight = prevalence_disability_weight / total_sequela_prevalence
            disability_weight = disability_weight.fillna(0)  # handle NaNs from dividing by 0 prevalence
            location_weighted_disability_weight += disability_weight * location_weight
        disability_weight = location_weighted_disability_weight / sum(data_keys.SWISSRE_LOCATION_WEIGHTS.values())
        return disability_weight
    else:
        raise ValueError(f'Unrecognized key {key}')


def load_emr(key: str, location: str):
    return (
            load_csmr(data_keys.CERVICAL_CANCER.CSMR, location)
            / load_prevalence(data_keys.CERVICAL_CANCER.PREVALENCE, location)
    )


def load_csmr(key: str, location: str):
    return _transform_raw_data(location, paths.RAW_MORTALITY_DATA_PATH, False)


# def load_hrhpv_prevalence(key: str, location: str) -> pd.DataFrame:
#     # Create df with 1000 random vals like above
#     # index == age_bins, 1000 cols for 1000 draws
#     # XXX : where we stopped 9/25
#     # TODO: use data_keys.PREV_DISTS_HPV for each GBD age bin
#     # use load_age_bins
#     age_bins_df = load_age_bins(key, location)
#     [data_keys.PREV_DISTS_HPV["<25"].get_random_variable(x) for x in range(0, 1000)]
#     return 0.19  # TODO: update SWAG with real value/calculation


def _load_em_from_meid(location, meid, measure):
    location_id = utility_data.get_location_id(location)
    data = gbd.get_modelable_entity_draws(meid, location_id)
    data = data[data.measure_id == vi_globals.MEASURES[measure]]
    data = vi_utils.normalize(data, fill_value=0)
    data = data.filter(vi_globals.DEMOGRAPHIC_COLUMNS + vi_globals.DRAW_COLUMNS)
    data = vi_utils.reshape(data)
    data = vi_utils.scrub_gbd_conventions(data, location)
    data = vi_utils.split_interval(data, interval_column='age', split_column_prefix='age')
    data = vi_utils.split_interval(data, interval_column='year', split_column_prefix='year')
    return vi_utils.sort_hierarchical_data(data)


# TODO - add project-specific data functions here
def _transform_raw_data(location: str, data_path: Path, is_log_data: bool) -> pd.DataFrame:
    processed_data = _transform_raw_data_preliminary(data_path, is_log_data)
    processed_data['location'] = location

    # Weight the covered provinces
    processed_data['value'] = (sum(processed_data[province] * weight for province, weight
                                   in data_keys.SWISSRE_LOCATION_WEIGHTS.items())
                               / sum(data_keys.SWISSRE_LOCATION_WEIGHTS.values()))

    processed_data = (
        processed_data
            # Remove province columns
            .drop([province for province in data_keys.SWISSRE_LOCATION_WEIGHTS.keys()], axis=1)
            # Set index to final columns and unstack with draws as columns
            .reset_index()
            .set_index(ARTIFACT_INDEX_COLUMNS + ["draw"])
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
    swissre_locations_mask = processed_data['location'].isin(data_keys.SWISSRE_LOCATION_WEIGHTS)
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
            .set_index(ARTIFACT_INDEX_COLUMNS + ["draw"])
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
