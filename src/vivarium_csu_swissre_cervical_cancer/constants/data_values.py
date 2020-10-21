from typing import NamedTuple

from vivarium_csu_swissre_cervical_cancer.utilities import TruncnormDist

REMISSION_RATE = 0.1

# BCC duration: "temporarily use 14.5 years"
BCC_DURATION = 14.5

# use numpy normal get random variable
# from: https://vivarium-research.readthedocs.io/en/latest/gbd2017_models/causes/neoplasms/cervical_cancer/
#   cervical_cancer_cause_model.html?highlight=cervical%20cancer
# relative risk of developing BCC for hrHPV infected women versus without HPV infection = 16.2 (95%CI 9.6 to 27.3)
# mean, stddev, key
# Lets start with log-normal, since the CI is so asymmetric - Abie
RR_HRHPV_PARAMS = (16.2, 4.425, "rr_hrhpv_dist")

DAYS_UNTIL_NEXT_ANNUAL = TruncnormDist('days_until_next_annual', 364.0, 156.0, 100.0, 700.0)
DAYS_UNTIL_NEXT_BIENNIAL = TruncnormDist('days_until_next_biennial', 728.0, 156.0, 200.0, 1400.0)


###########################################
# Screening and Treatment Model Constants #
###########################################

PROBABILITY_ATTENDING_SCREENING_KEY = 'probability_attending_screening'
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER = 1.89
# RAMP_UP_START = datetime(2021, 1, 1)
# RAMP_UP_END = datetime(2030, 1, 1)

ATTENDED_LAST_SCREENING = 'attended_last_screening'
PREVIOUS_SCREENING_DATE = 'previous_screening_date'
NEXT_SCREENING_DATE = 'next_screening_date'


class __Screening(NamedTuple):
    # TODO: need stddev for COTEST_CC_SENSITIVITY
    COTEST_CC_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_cc_sensitivity', 0.591, 0.0)
    COTEST_CC_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_cc_specificity', 1.0, 0.0)

    # TODO: need stddev for COTEST_HPV_SENSITIVITY, info for COTEST_HPV_SPECIFICITY (assuming 100% for now)
    COTEST_HPV_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 0.591, 0.0)
    COTEST_HPV_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_hpv_specificity', 1.0, 0.0)

    # CYTOLOGY_SENSITIVITY ~ 65.9% (95% CI 54.9 to 75.3)
    CYTOLOGY_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 0.659, 0.051)
    CYTOLOGY_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 1.0, 0.0)

    REMISSION_SENSITIVITY: TruncnormDist = TruncnormDist('remission_sensitivity', 1.0, 0.0)
    REMISSION_SPECIFICITY: TruncnormDist = TruncnormDist('remission_specificity', 1.0, 0.0)

    BASE_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_base', 0.3, 0.003,
                                                   key=PROBABILITY_ATTENDING_SCREENING_KEY)
    START_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_attended_prev', 0.397, 0.00397,
                                                                  key=PROBABILITY_ATTENDING_SCREENING_KEY)
    START_NOT_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_not_attended_prev', 0.258,
                                                                      0.00258, key=PROBABILITY_ATTENDING_SCREENING_KEY)
    END_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('end_attendance_attended_prev', 0.782, 0.00782,
                                                                key=PROBABILITY_ATTENDING_SCREENING_KEY)
    END_NOT_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('end_attendance_not_attended_prev', 0.655, 0.00655,
                                                                    key=PROBABILITY_ATTENDING_SCREENING_KEY)

    @property
    def name(self):
        return 'screening_result'

    @property
    def log_name(self):
        return 'screening result'


SCREENING = __Screening()
