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
        data_keys.CERVICAL_CANCER.HRHPV_REMISSION_RATE: load_hrhpv_remission,
        data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE: load_prevalence,
        data_keys.CERVICAL_CANCER.BCC_PREVALENCE: load_prevalence,
        data_keys.CERVICAL_CANCER.BCC_PREVALENCE_WITH_HRHPV: load_prevalence,
        data_keys.CERVICAL_CANCER.PREVALENCE: load_prevalence,
        data_keys.CERVICAL_CANCER.PREVALENCE_WITH_HRHPV: load_prevalence,
        data_keys.CERVICAL_CANCER.HRHPV_INCIDENCE_RATE: load_incidence_rate,
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
        }
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
    md = entity[key.measure]
    if hasattr(md, 'to_dict'):
        md = md.to_dict()
    return md


def load_acmr(key: str, location: str) -> pd.DataFrame:
    return _transform_raw_data(location, paths.RAW_ACMR_DATA_PATH, True)


def load_prevalence(key: str, location: str) -> pd.DataFrame:
    """Computes prevalence values for key at location."""
    base_prevalence = _transform_raw_data(location, paths.RAW_PREVALENCE_DATA_PATH, False)
    hrhpv_prev = _load_hrhpv_raw(paths.HRHPV_PREVALENCE_PATH)
    hrhpv_rr = load_rr_hrhpv(base_prevalence.columns)
    if key in [data_keys.CERVICAL_CANCER.BCC_PREVALENCE, data_keys.CERVICAL_CANCER.BCC_PREVALENCE_WITH_HRHPV]:
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
        prev_bcc_without_hrhpv = base_prevalence / (hrhpv_rr + 1)
        if key == data_keys.CERVICAL_CANCER.BCC_PREVALENCE:
            return _expand_age_bins(prev_bcc_without_hrhpv)
        else:  # BCC with HRHPV
            prev_bcc_with_hrhpv = base_prevalence - prev_bcc_without_hrhpv
            return _expand_age_bins(prev_bcc_with_hrhpv)
    elif key in [data_keys.CERVICAL_CANCER.PREVALENCE, data_keys.CERVICAL_CANCER.PREVALENCE_WITH_HRHPV]:
        prev_icc_without_hrhpv = base_prevalence / (hrhpv_rr + 1)
        if key == data_keys.CERVICAL_CANCER.PREVALENCE:
            return _expand_age_bins(prev_icc_without_hrhpv)
        else:  # ICC with HRHPV
            prev_icc_with_hrhpv = base_prevalence - prev_icc_without_hrhpv
            return _expand_age_bins(prev_icc_with_hrhpv)
    elif key == data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE:
        return hrhpv_prev
    else:
        raise ValueError(f'Unrecognized key {key}')


def load_rr_hrhpv(columns) -> pd.Series:
    """Get random variables based on distribution for RR hrHPV, columns should be those in the prevalence df"""
    per_draw_rr = pd.Series(
        [utilities.get_lognormal_random_variable(*data_values.RR_HRHPV_PARAMS, x) for x in range(0, 1000)],
        index=columns)
    return per_draw_rr


def load_hrhpv_remission(key: str, location: str) -> pd.DataFrame:
    if key == data_keys.CERVICAL_CANCER.HRHPV_REMISSION_RATE:
        return _load_hrhpv_raw(paths.HRHPV_REMISSION_PATH)
    else:
        raise ValueError(f'Unrecognized key {key}')


def load_paf(prev, rr) -> pd.DataFrame:
    """Calculates Population Attributable Fraction (PAF): prev×(RR−1)/prev×(RR−1)+1"""
    # Calculate PAF: prev_hrHPV×(RR_hrHPV−1)/prev_hrHPV×(RR_hrHPV−1)+1
    rr_minus_one = rr - 1
    num = prev.multiply(rr_minus_one, axis=1)
    return num / (num + 1)


def load_incidence_rate(key: str, location: str) -> pd.DataFrame:
    """Get the incidence rate given a key."""
    bcc_prevalence = (load_prevalence(data_keys.CERVICAL_CANCER.BCC_PREVALENCE, location)
                      + load_prevalence(data_keys.CERVICAL_CANCER.BCC_PREVALENCE_WITH_HRHPV, location))
    if key == data_keys.CERVICAL_CANCER.INCIDENCE_RATE:
        # i_ICC = (incidence_c432/prev_BCC)
        incidence_rate = _transform_raw_data(location, paths.RAW_INCIDENCE_RATE_DATA_PATH, False)
        incidence_rate = _expand_age_bins(incidence_rate)
        incidence_rate = incidence_rate / bcc_prevalence
    elif key == data_keys.CERVICAL_CANCER.HRHPV_INCIDENCE_RATE:
        return _load_hrhpv_raw(paths.HRHPV_INCIDENCE_PATH)
    else:
        hrhpv_prevalence = load_prevalence(data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE, location)
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
            prev_c432 = _expand_age_bins(prev_c432)
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
    return _expand_age_bins(_transform_raw_data(location, paths.RAW_MORTALITY_DATA_PATH, False))


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


# project-specific data functions
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


def _expand_age_bins(df: pd.DataFrame, index_col=ARTIFACT_INDEX_COLUMNS, prev_age_bin_sz=5) -> pd.DataFrame:
    """Expands granularity of age bin to 1-year age bins from prev_age_bin_sz-sized age bins."""
    df = df.reset_index()
    final_df = pd.DataFrame(columns=df.columns)
    for i in range(0, prev_age_bin_sz):
        tmp = df.copy()
        tmp["age_start"] = tmp["age_start"] + i
        tmp["age_end"] = tmp["age_start"] + 1
        final_df = final_df.append(tmp)
        del tmp
    # handle tail edge case
    last_age_bin_start = max(final_df["age_start"])
    final_df.loc[final_df["age_start"] == last_age_bin_start, "age_end"] = 125.0
    final_df = final_df.set_index(index_col)
    return final_df


def _load_hrhpv_raw(path) -> pd.DataFrame:
    df = pd.read_hdf(path)
    df = df.set_index(ARTIFACT_INDEX_COLUMNS)
    return df


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
