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
import itertools

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
        data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE: load_hpv_prevalence,
        data_keys.CERVICAL_CANCER.BCC_PREVALENCE: load_cervical_cancer_prevalence,
        data_keys.CERVICAL_CANCER.BCC_PREVALENCE_WITH_HRHPV: load_cervical_cancer_prevalence,
        data_keys.CERVICAL_CANCER.PREVALENCE: load_cervical_cancer_prevalence,
        data_keys.CERVICAL_CANCER.PREVALENCE_WITH_HRHPV: load_cervical_cancer_prevalence,
        data_keys.CERVICAL_CANCER.HRHPV_INCIDENCE_RATE: load_hpv_incidence_rate,
        data_keys.CERVICAL_CANCER.BCC_HPV_POS_INCIDENCE_RATE: load_bcc_incidence_rate,
        data_keys.CERVICAL_CANCER.BCC_HPV_NEG_INCIDENCE_RATE: load_bcc_incidence_rate,
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


def load_hpv_prevalence(key: str, location: str) -> pd.DataFrame:
    """Computes hpv prevalence values for key at location."""
    if key == data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE:
        return _load_hrhpv_raw(paths.HRHPV_PREVALENCE_PATH)
    else:
        raise ValueError(f'Unrecognized key {key}')


def load_cervical_cancer_prevalence(key: str, location: str) -> pd.DataFrame:
    """Computes cervical cancer prevalence values for key at location."""
    if key in [data_keys.CERVICAL_CANCER.BCC_PREVALENCE,
               data_keys.CERVICAL_CANCER.BCC_PREVALENCE_WITH_HRHPV,
               data_keys.CERVICAL_CANCER.RAW_BCC_PREVALENCE]:
        # base bcc prevalence is incidence_c432 times mean sojourn time
        raw_incidence_rate = _transform_raw_data(location, paths.RAW_INCIDENCE_RATE_DATA_PATH, False)
        cervical_cancer_incidence_rate = _expand_age_bins(raw_incidence_rate)
        base_prevalence = cervical_cancer_incidence_rate * data_values.BCC_MEAN_SOJOURN_TIME
    elif key in [data_keys.CERVICAL_CANCER.PREVALENCE,
                 data_keys.CERVICAL_CANCER.PREVALENCE_WITH_HRHPV,
                 data_keys.CERVICAL_CANCER.RAW_ICC_PREVALENCE]:
        # base icc prevalence is prevalence directly from forecast data source
        raw_base_prevalence = _transform_raw_data(location, paths.RAW_PREVALENCE_DATA_PATH, False)
        base_prevalence = _expand_age_bins(raw_base_prevalence)
    else:
        raise ValueError(f'Unrecognized key {key}')

    if key in [data_keys.CERVICAL_CANCER.RAW_BCC_PREVALENCE, data_keys.CERVICAL_CANCER.RAW_ICC_PREVALENCE]:
        prevalence = base_prevalence
    else:
        # Get RR and PAF due to HRHPV
        hrhpv_prevalence = load_hpv_prevalence(data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE, location)
        hrhpv_rr = load_rr_hrhpv(hrhpv_prevalence.columns)
        paf = load_paf(hrhpv_prevalence, hrhpv_rr)

        if key in [data_keys.CERVICAL_CANCER.BCC_PREVALENCE, data_keys.CERVICAL_CANCER.PREVALENCE]:
            # Prev(CC, S_hrHPV) = prev * {1 - PAF * [RR / (RR-1)])}
            prevalence = base_prevalence * (1 - (paf * hrhpv_rr / (hrhpv_rr - 1)))
        else:
            # Prev(CC, C_hrHPV) = prev * PAF * [RR / (RR-1)]
            prevalence = base_prevalence * paf * hrhpv_rr / (hrhpv_rr - 1)

    return prevalence


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


def load_hpv_incidence_rate(key: str, location: str) -> pd.DataFrame:
    """Computes hpv prevalence values for key at location."""
    if key == data_keys.CERVICAL_CANCER.HRHPV_INCIDENCE_RATE:
        return _load_hrhpv_raw(paths.HRHPV_INCIDENCE_PATH)
    else:
        raise ValueError(f'Unrecognized key {key}')


def load_bcc_incidence_rate(key: str, location: str) -> pd.DataFrame:
    """Get the bcc incidence rate given a key."""

    raw_bcc_incidence_rate = _transform_raw_data(location, paths.RAW_INCIDENCE_RATE_DATA_PATH, False)
    cervical_cancer_incidence_rate = _expand_age_bins(raw_bcc_incidence_rate)
    base_bcc_incidence_rate = shift_incidence_rate(cervical_cancer_incidence_rate, data_values.BCC_MEAN_SOJOURN_TIME)

    if key == data_keys.CERVICAL_CANCER.RAW_BCC_INCIDENCE_RATE:
        incidence_rate = base_bcc_incidence_rate
    else:
        # Get RR and PAF due to HRHPV
        hrhpv_prevalence = load_hpv_prevalence(data_keys.CERVICAL_CANCER.HRHPV_PREVALENCE, location)
        hrhpv_rr = load_rr_hrhpv(hrhpv_prevalence.columns)
        paf = load_paf(hrhpv_prevalence, hrhpv_rr)

        if key == data_keys.CERVICAL_CANCER.BCC_HPV_POS_INCIDENCE_RATE:
            incidence_rate = base_bcc_incidence_rate * (1 - paf) * hrhpv_rr
        elif key == data_keys.CERVICAL_CANCER.BCC_HPV_NEG_INCIDENCE_RATE:
            incidence_rate = base_bcc_incidence_rate * (1 - paf)
        else:
            raise ValueError(f'Unrecognized key {key}')

    return incidence_rate


def shift_incidence_rate(incidence_rate: pd.DataFrame, shift: int) -> pd.DataFrame:
    incidence_rate = incidence_rate.reset_index()
    incidence_rate['age_start'] = incidence_rate['age_start'] - shift
    incidence_rate = incidence_rate.loc[incidence_rate['age_start'] >= 15, :]
    incidence_rate['age_end'] = incidence_rate['age_end'].apply(lambda x: x - shift if x != 125 else 100 - shift)

    df = pd.DataFrame([{'age_start': age * 1.0, 'year_start': year} for (age, year) in
                       itertools.product(range(100 - shift, 100), range(1990, 2041))])
    df['location'] = 'SwissRE Coverage'
    df['sex'] = 'Female'
    df['age_end'] = df['age_start'].apply(lambda x: x + 1 if x != 99 else 125)
    df['year_end'] = df['year_start'] + 1

    draws = df.apply(lambda row: incidence_rate.loc[
        (incidence_rate['age_start'] == (99.0 - shift)) & (incidence_rate['year_start'] == row['year_start']),
        [f'draw_{i}' for i in range(0, 1000)]].values[0], axis=1)
    draws = pd.concat([pd.Series([row[i] for row in draws], name=f'draw_{i}') for i in range(0, 1000)], axis=1)
    df = pd.concat([df, draws], axis=1)
    df = df.set_index(ARTIFACT_INDEX_COLUMNS).reset_index()

    incidence_rate = pd.concat([incidence_rate, df]).set_index(ARTIFACT_INDEX_COLUMNS)
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
            / _expand_age_bins(_transform_raw_data(location, paths.RAW_PREVALENCE_DATA_PATH, False))
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
    raw_data: pd.DataFrame = pd.read_csv(data_path)
    age_bins = gbd.get_age_bins().set_index('age_group_name')

    processed_data = raw_data[raw_data['location_id'].isin(data_keys.SWISSRE_LOCATION_WEIGHTS)]
    processed_data = (
        processed_data
        .set_index('age_group_id')
        .join(age_bins, how='left')
        .reset_index()
        .rename(columns={
            'age_group_years_start': 'age_start',
            'age_group_years_end': 'age_end',
            'year_id': 'year_start',
            'sex_id': 'sex',
            'location_id': 'location',
        })
    )

    processed_data = processed_data[(processed_data['age_start'] >= data_values.YOUNGEST_SIMULANT_AGE)
                                    & (processed_data['age_end'] >= data_values.YOUNGEST_SIMULANT_AGE)]

    # Add year end column
    processed_data['year_end'] = processed_data['year_start'] + 1

    # Drop unneeded columns
    processed_data = processed_data[ARTIFACT_INDEX_COLUMNS + ['draw', 'noised_forecast']]

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
    df = pd.read_csv(path)
    del df['Unnamed: 0']
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
